"""
Delay prediction inference pipeline.
Loads the trained LightGBM model and produces delay predictions from raw trip input.

Usage (standalone):
    python scripts/predict_delay.py

Usage (imported):
    from scripts.predict_delay import DelayPredictor
    predictor = DelayPredictor()
    result = predictor.predict({...})
"""

import json
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd

# ─── Paths ────────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent
_MODELS_DIR = _ROOT / "models"

MODEL_PATH = _MODELS_DIR / "lightgbm_delay_model.txt"
METRICS_PATH = _MODELS_DIR / "metrics.json"

# ─── Feature policy (must match training exactly) ─────────────────────────────
FEATURE_COLUMNS = [
    "CALL_TYPE",
    "ORIGIN_CALL",
    "ORIGIN_STAND",
    "TAXI_ID",
    "TIMESTAMP",
    "DAY_TYPE",
    "expected_time",
    "hour",
    "weekday",
    "origin_lon",
    "origin_lat",
    "straight_line_distance_km",
    "historical_delay_rate",
    "speed_median",
    "travel_p50",
    "travel_p90",
    "driver_delay_rate",
    "driver_speed_median",
    "origin_lat_grid",
    "origin_lon_grid",
    "origin_delay_rate",
    "temperature_2m",
    "precipitation",
    "windspeed_10m",
]

CATEGORICAL_COLUMNS = ["CALL_TYPE", "DAY_TYPE"]

# Threshold tuned on validation F1 during training
DEFAULT_THRESHOLD = 0.52

# Numeric column defaults (median-like safe fallbacks for missing values)
NUMERIC_DEFAULTS: dict[str, float] = {
    "ORIGIN_CALL": 0.0,
    "ORIGIN_STAND": 0.0,
    "TAXI_ID": 0.0,
    "TIMESTAMP": 0.0,
    "expected_time": 600.0,
    "hour": 12.0,
    "weekday": 2.0,
    "origin_lon": -8.61,
    "origin_lat": 41.15,
    "straight_line_distance_km": 3.0,
    "historical_delay_rate": 0.35,
    "speed_median": 25.0,
    "travel_p50": 600.0,
    "travel_p90": 900.0,
    "driver_delay_rate": 0.35,
    "driver_speed_median": 25.0,
    "origin_lat_grid": 41.15,
    "origin_lon_grid": -8.61,
    "origin_delay_rate": 0.35,
    "temperature_2m": 18.0,
    "precipitation": 0.0,
    "windspeed_10m": 5.0,
}

CATEGORICAL_DEFAULTS: dict[str, str] = {
    "CALL_TYPE": "C",
    "DAY_TYPE": "A",
}


class DelayPredictor:
    """
    Loads the trained LightGBM model once and exposes a predict() method.

    predict() accepts a dict or list of dicts with raw trip features
    and returns delay probability and binary label for each trip.
    """

    def __init__(
        self,
        model_path: Path = MODEL_PATH,
        metrics_path: Path = METRICS_PATH,
        threshold: float | None = None,
    ) -> None:
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model not found at {model_path}. "
                "Download lightgbm_delay_model.txt from Kaggle and place it in models/"
            )

        self._model = lgb.Booster(model_file=str(model_path))

        # Load threshold from metrics file if not explicitly provided
        if threshold is not None:
            self._threshold = float(threshold)
        elif metrics_path.exists():
            with open(metrics_path, encoding="utf-8") as f:
                meta = json.load(f)
            self._threshold = float(meta.get("best_threshold", DEFAULT_THRESHOLD))
        else:
            self._threshold = DEFAULT_THRESHOLD

        print(f"Model loaded  — best_iteration: {self._model.num_trees()}")
        print(f"Threshold     — {self._threshold:.2f}")

    def _build_dataframe(self, input_data: dict | list[dict]) -> pd.DataFrame:
        """Convert raw input dict(s) to a properly typed feature DataFrame."""
        rows = input_data if isinstance(input_data, list) else [input_data]
        df = pd.DataFrame(rows)

        # Ensure all expected columns exist, fill missing with defaults
        for col in FEATURE_COLUMNS:
            if col not in df.columns:
                if col in CATEGORICAL_DEFAULTS:
                    df[col] = CATEGORICAL_DEFAULTS[col]
                else:
                    df[col] = NUMERIC_DEFAULTS.get(col, 0.0)

        df = df[FEATURE_COLUMNS].copy()

        # Numeric columns: coerce and fill NaN
        numeric_cols = [c for c in FEATURE_COLUMNS if c not in CATEGORICAL_COLUMNS]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].fillna(NUMERIC_DEFAULTS.get(col, 0.0))

        # Categorical columns: string and fill NaN
        for col in CATEGORICAL_COLUMNS:
            df[col] = df[col].astype("string").fillna(CATEGORICAL_DEFAULTS.get(col, "__missing__"))
            df[col] = df[col].astype("category")

        return df

    def predict(self, input_data: dict | list[dict]) -> list[dict[str, Any]]:
        """
        Predict delay for one or more trips.

        Args:
            input_data: A single dict or list of dicts with trip features.
                        Unknown/missing fields are filled with safe defaults.

        Returns:
            List of result dicts:
            {
                "delay_probability": float,   # 0.0–1.0
                "is_delayed": int,            # 1 = delayed, 0 = on-time
                "confidence": str,            # "high" / "medium" / "low"
                "threshold_used": float,
            }
        """
        df = self._build_dataframe(input_data)
        probabilities = self._model.predict(df, num_iteration=self._model.best_iteration)

        results = []
        for prob in probabilities:
            is_delayed = int(prob >= self._threshold)
            # Confidence bands
            distance = abs(prob - self._threshold)
            if distance >= 0.20:
                confidence = "high"
            elif distance >= 0.10:
                confidence = "medium"
            else:
                confidence = "low"

            results.append(
                {
                    "delay_probability": round(float(prob), 4),
                    "is_delayed": is_delayed,
                    "confidence": confidence,
                    "threshold_used": self._threshold,
                }
            )

        return results if isinstance(input_data, list) else results[0]

    def predict_batch_df(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Predict from a raw DataFrame (e.g., loaded from CSV).
        Returns the input DataFrame with 3 extra columns appended.
        """
        df_features = self._build_dataframe(df_raw.to_dict(orient="records"))
        probabilities = self._model.predict(df_features, num_iteration=self._model.best_iteration)

        result_df = df_raw.copy()
        result_df["delay_probability"] = probabilities.round(4)
        result_df["is_delayed"] = (probabilities >= self._threshold).astype(int)
        result_df["confidence"] = [
            "high" if abs(p - self._threshold) >= 0.20
            else "medium" if abs(p - self._threshold) >= 0.10
            else "low"
            for p in probabilities
        ]
        return result_df


# ─── Quick smoke test when run directly ───────────────────────────────────────
if __name__ == "__main__":
    predictor = DelayPredictor()

    print("\n--- Single trip prediction ---")
    single_trip = {
        "CALL_TYPE": "C",
        "DAY_TYPE": "A",
        "ORIGIN_CALL": None,
        "ORIGIN_STAND": None,
        "TAXI_ID": 20000589,
        "TIMESTAMP": 1372636858,
        "hour": 7,
        "weekday": 0,
        "origin_lon": -8.618643,
        "origin_lat": 41.141412,
        "straight_line_distance_km": 5.2,
        "expected_time": 780.0,
        "historical_delay_rate": 0.227,
        "speed_median": 22.5,
        "travel_p50": 660.0,
        "travel_p90": 980.0,
        "driver_delay_rate": 0.31,
        "driver_speed_median": 21.0,
        "origin_lat_grid": 41.14,
        "origin_lon_grid": -8.62,
        "origin_delay_rate": 0.226,
        "temperature_2m": 22.1,
        "precipitation": 0.0,
        "windspeed_10m": 2.5,
    }

    result = predictor.predict(single_trip)
    print(f"Delay probability : {result['delay_probability']:.4f}")
    print(f"Is delayed        : {'YES' if result['is_delayed'] else 'NO'}")
    print(f"Confidence        : {result['confidence']}")

    print("\n--- Batch prediction (3 trips) ---")
    batch = [
        {**single_trip, "hour": 8, "precipitation": 0.0},   # morning rush, dry
        {**single_trip, "hour": 17, "precipitation": 5.0},  # evening rush, rain
        {**single_trip, "hour": 14, "precipitation": 0.0},  # afternoon, dry
    ]
    batch_results = predictor.predict(batch)
    for i, r in enumerate(batch_results):
        print(f"Trip {i+1}: prob={r['delay_probability']:.3f}  delayed={r['is_delayed']}  conf={r['confidence']}")
