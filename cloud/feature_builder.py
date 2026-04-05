"""Build model-ready features from raw trip input."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from typing import Any

from scripts.predict_delay import CATEGORICAL_DEFAULTS, FEATURE_COLUMNS, NUMERIC_DEFAULTS


@dataclass
class FeatureBuildResult:
    features: dict[str, Any]
    assumptions: list[str]


class DelayFeatureBuilder:
    """Converts raw trip request data into the 24 LightGBM feature columns."""

    def __init__(self) -> None:
        self.numeric_defaults = dict(NUMERIC_DEFAULTS)
        self.categorical_defaults = dict(CATEGORICAL_DEFAULTS)

    def build(self, raw: dict[str, Any]) -> FeatureBuildResult:
        assumptions: list[str] = []

        timestamp, timestamp_note = self._resolve_timestamp(raw)
        if timestamp_note:
            assumptions.append(timestamp_note)

        dt = datetime.utcfromtimestamp(timestamp)

        call_type = self._first_value(raw, ["CALL_TYPE", "call_type"], self.categorical_defaults["CALL_TYPE"])
        day_type = self._first_value(raw, ["DAY_TYPE", "day_type"], self._infer_day_type(dt))

        origin_lat = self._required_float(raw, ["origin_lat", "pickup_lat", "lat"], "origin_lat")
        origin_lon = self._required_float(raw, ["origin_lon", "pickup_lon", "lon", "lng", "pickup_lng"], "origin_lon")

        dest_lat = self._optional_float(raw, ["dest_lat", "destination_lat"])
        dest_lon = self._optional_float(raw, ["dest_lon", "destination_lon", "destination_lng"])

        straight_line_distance_km = self._optional_float(raw, ["straight_line_distance_km"])
        if straight_line_distance_km is None:
            if dest_lat is not None and dest_lon is not None:
                straight_line_distance_km = self._haversine_km(origin_lat, origin_lon, dest_lat, dest_lon)
            else:
                straight_line_distance_km = self.numeric_defaults["straight_line_distance_km"]
                assumptions.append("Used default straight_line_distance_km because destination coordinates were missing")

        speed_median = self._optional_float(raw, ["speed_median"])
        if speed_median is None:
            speed_median = self.numeric_defaults["speed_median"]
            assumptions.append("Used default speed_median")

        expected_time = self._optional_float(raw, ["expected_time"])
        if expected_time is None:
            expected_time = self._estimate_expected_time_seconds(straight_line_distance_km, speed_median)
            assumptions.append("Estimated expected_time from distance and median speed")

        historical_delay_rate = self._optional_float(raw, ["historical_delay_rate"])
        if historical_delay_rate is None:
            historical_delay_rate = self._optional_float(raw, ["origin_delay_rate", "driver_delay_rate"])
        if historical_delay_rate is None:
            historical_delay_rate = self.numeric_defaults["historical_delay_rate"]
            assumptions.append("Used default historical_delay_rate")

        travel_p50 = self._optional_float(raw, ["travel_p50"])
        if travel_p50 is None:
            travel_p50 = expected_time
            assumptions.append("Approximated travel_p50 from expected_time")

        travel_p90 = self._optional_float(raw, ["travel_p90"])
        if travel_p90 is None:
            travel_p90 = expected_time * 1.35
            assumptions.append("Approximated travel_p90 from expected_time")

        driver_delay_rate = self._optional_float(raw, ["driver_delay_rate"])
        if driver_delay_rate is None:
            driver_delay_rate = historical_delay_rate
            assumptions.append("Used historical_delay_rate as driver_delay_rate fallback")

        driver_speed_median = self._optional_float(raw, ["driver_speed_median"])
        if driver_speed_median is None:
            driver_speed_median = speed_median
            assumptions.append("Used speed_median as driver_speed_median fallback")

        origin_delay_rate = self._optional_float(raw, ["origin_delay_rate"])
        if origin_delay_rate is None:
            origin_delay_rate = historical_delay_rate
            assumptions.append("Used historical_delay_rate as origin_delay_rate fallback")

        temperature_2m = self._first_numeric(raw, ["temperature_2m", "temperature"], self.numeric_defaults["temperature_2m"], assumptions, "Used default temperature_2m")
        precipitation = self._first_numeric(raw, ["precipitation", "rain_mm"], self.numeric_defaults["precipitation"], assumptions, "Used default precipitation")
        windspeed_10m = self._first_numeric(raw, ["windspeed_10m", "wind_speed", "wind_kph"], self.numeric_defaults["windspeed_10m"], assumptions, "Used default windspeed_10m")

        features = {
            "CALL_TYPE": str(call_type),
            "ORIGIN_CALL": self._first_numeric(raw, ["ORIGIN_CALL", "origin_call"], self.numeric_defaults["ORIGIN_CALL"], assumptions, "Used default ORIGIN_CALL"),
            "ORIGIN_STAND": self._first_numeric(raw, ["ORIGIN_STAND", "origin_stand"], self.numeric_defaults["ORIGIN_STAND"], assumptions, "Used default ORIGIN_STAND"),
            "TAXI_ID": self._first_numeric(raw, ["TAXI_ID", "taxi_id", "driver_id"], self.numeric_defaults["TAXI_ID"], assumptions, "Used default TAXI_ID"),
            "TIMESTAMP": float(timestamp),
            "DAY_TYPE": str(day_type),
            "expected_time": float(expected_time),
            "hour": float(dt.hour),
            "weekday": float(dt.weekday()),
            "origin_lon": float(origin_lon),
            "origin_lat": float(origin_lat),
            "straight_line_distance_km": float(straight_line_distance_km),
            "historical_delay_rate": float(historical_delay_rate),
            "speed_median": float(speed_median),
            "travel_p50": float(travel_p50),
            "travel_p90": float(travel_p90),
            "driver_delay_rate": float(driver_delay_rate),
            "driver_speed_median": float(driver_speed_median),
            "origin_lat_grid": float(round(origin_lat, 2)),
            "origin_lon_grid": float(round(origin_lon, 2)),
            "origin_delay_rate": float(origin_delay_rate),
            "temperature_2m": float(temperature_2m),
            "precipitation": float(precipitation),
            "windspeed_10m": float(windspeed_10m),
        }

        missing = [column for column in FEATURE_COLUMNS if column not in features]
        if missing:
            raise ValueError(f"Failed to build required features: {missing}")

        return FeatureBuildResult(features=features, assumptions=sorted(set(assumptions)))

    def _resolve_timestamp(self, raw: dict[str, Any]) -> tuple[int, str | None]:
        timestamp_value = self._optional_float(raw, ["TIMESTAMP", "timestamp", "pickup_timestamp"])
        if timestamp_value is not None:
            return int(timestamp_value), None

        datetime_value = self._first_value(raw, ["pickup_datetime", "datetime"], None)
        if datetime_value:
            dt = datetime.fromisoformat(str(datetime_value).replace("Z", "+00:00"))
            return int(dt.timestamp()), "Derived TIMESTAMP from pickup_datetime"

        return int(self.numeric_defaults["TIMESTAMP"]), "Used default TIMESTAMP"

    def _infer_day_type(self, dt: datetime) -> str:
        return "A" if dt.weekday() < 5 else "B"

    def _estimate_expected_time_seconds(self, distance_km: float, speed_kmh: float) -> float:
        safe_speed = max(speed_kmh, 8.0)
        return max((distance_km / safe_speed) * 3600.0 * 1.15, 180.0)

    def _required_float(self, raw: dict[str, Any], keys: list[str], field_name: str) -> float:
        value = self._optional_float(raw, keys)
        if value is None:
            raise ValueError(f"Missing required field: {field_name}")
        return float(value)

    def _optional_float(self, raw: dict[str, Any], keys: list[str]) -> float | None:
        for key in keys:
            if key in raw and raw[key] is not None and raw[key] != "":
                return float(raw[key])
        return None

    def _first_value(self, raw: dict[str, Any], keys: list[str], default: Any) -> Any:
        for key in keys:
            if key in raw and raw[key] is not None and raw[key] != "":
                return raw[key]
        return default

    def _first_numeric(
        self,
        raw: dict[str, Any],
        keys: list[str],
        default: float,
        assumptions: list[str],
        note: str,
    ) -> float:
        value = self._optional_float(raw, keys)
        if value is None:
            assumptions.append(note)
            return float(default)
        return float(value)

    def _haversine_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius_km = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lon2 - lon1)

        a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
        return radius_km * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))