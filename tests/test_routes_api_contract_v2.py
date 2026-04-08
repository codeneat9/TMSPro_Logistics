from backend.services.routes import RoutesService


def test_get_route_options_success(client, monkeypatch):
    sample = [
        {
            "route_type": "optimal",
            "distance_km": 12.2,
            "duration_minutes": 24,
            "polyline": "poly1",
            "source": "osrm",
        },
        {
            "route_type": "alternative_1",
            "distance_km": 13.1,
            "duration_minutes": 28,
            "polyline": "poly2",
            "source": "osrm",
        },
    ]

    def _fake_fetch(**kwargs):
        return sample

    monkeypatch.setattr(RoutesService, "fetch_routes", staticmethod(_fake_fetch))

    response = client.get(
        "/api/routes",
        params={
            "origin": "12.90,77.50",
            "destination": "12.97,77.59",
            "alternatives": 1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["optimal"]["route_type"] == "optimal"
    assert len(body["alternatives"]) == 1


def test_get_route_options_bad_coordinates(client):
    response = client.get(
        "/api/routes",
        params={
            "origin": "invalid",
            "destination": "12.97,77.59",
        },
    )

    assert response.status_code == 400


def test_predict_delay_contract_fields(client):
    response = client.post(
        "/api/routes/predict-delay",
        params={
            "trip_id": "trip-a",
            "hour_of_day": 8,
            "day_of_week": 1,
            "distance_km": 15.0,
            "weather_condition": "rain",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "predicted_delay_minutes" in body
    assert "delay_probability" in body
    assert "severity" in body
    assert "confidence" in body
    assert "model_version" in body
    assert "inference_ms" in body
