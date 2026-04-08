import pytest

from backend.services.routes import RoutesService


class _DummyResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def json(self):
        return self._payload


def test_fetch_routes_osrm_success(monkeypatch):
    payload = {
        "routes": [
            {"distance": 10000, "duration": 900, "geometry": "poly_opt"},
            {"distance": 12000, "duration": 1080, "geometry": "poly_alt1"},
            {"distance": 13000, "duration": 1200, "geometry": "poly_alt2"},
        ]
    }

    def _fake_get(*args, **kwargs):
        return _DummyResponse(payload)

    monkeypatch.setattr("backend.services.routes.requests.get", _fake_get)

    routes = RoutesService.fetch_routes(12.9, 77.5, 12.97, 77.59, alternatives=2)

    assert len(routes) == 3
    assert routes[0]["route_type"] == "optimal"
    assert routes[1]["route_type"] == "alternative_1"
    assert routes[2]["route_type"] == "alternative_2"
    assert routes[0]["source"] == "osrm"


def test_fetch_routes_fallback_when_osrm_fails(monkeypatch):
    def _fake_get(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr("backend.services.routes.requests.get", _fake_get)

    routes = RoutesService.fetch_routes(12.9, 77.5, 12.97, 77.59, alternatives=2)

    assert len(routes) == 3
    assert routes[0]["source"] == "fallback"
    assert routes[0]["route_type"] == "optimal"
    assert routes[1]["route_type"] == "alternative_1"


def test_predict_delay_profile_contract():
    result = RoutesService.predict_delay_profile(
        db=None,
        trip_id="trip-1",
        hour_of_day=8,
        day_of_week=1,
        distance_km=15,
        weather_condition="rain",
    )

    assert result["trip_id"] == "trip-1"
    assert "predicted_delay_minutes" in result
    assert "delay_probability" in result
    assert "severity" in result
    assert "confidence" in result
    assert "model_version" in result
    assert "inference_ms" in result
    assert result["model_version"] == "heuristic-v1"
    assert result["inference_ms"] >= 1
