"""FastAPI backend for delay prediction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from cloud.feature_builder import DelayFeatureBuilder
from cloud.routing_api import router as routing_router
from cloud.dashboard_api import router as dashboard_router
from cloud.traffic_api import router as traffic_router
from cloud.mobile_sync_api import router as mobile_router
from scripts.predict_delay import DelayPredictor


app = FastAPI(
    title="Embedded TMS Delay Prediction API",
    version="1.0.0",
    description="Builds model features from raw trip data and predicts trip delay risk.",
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include routers
app.include_router(routing_router)
app.include_router(dashboard_router)
app.include_router(traffic_router)
app.include_router(mobile_router)

predictor = DelayPredictor()
feature_builder = DelayFeatureBuilder()


class PredictionRequest(BaseModel):
    pickup_lat: float = Field(..., description="Pickup latitude")
    pickup_lon: float = Field(..., description="Pickup longitude")
    pickup_timestamp: int | None = Field(None, description="Unix timestamp at trip start")
    pickup_datetime: str | None = Field(None, description="ISO datetime if timestamp is not supplied")
    destination_lat: float | None = Field(None, description="Destination latitude")
    destination_lon: float | None = Field(None, description="Destination longitude")
    call_type: str | None = Field(None, description="A/B/C style call type")
    day_type: str | None = Field(None, description="A/B/C day type")
    taxi_id: int | None = Field(None, description="Taxi identifier")
    driver_id: int | None = Field(None, description="Alias for taxi_id")
    origin_call: float | None = None
    origin_stand: float | None = None
    expected_time: float | None = Field(None, description="Expected trip duration in seconds")
    straight_line_distance_km: float | None = None
    historical_delay_rate: float | None = None
    speed_median: float | None = None
    travel_p50: float | None = None
    travel_p90: float | None = None
    driver_delay_rate: float | None = None
    driver_speed_median: float | None = None
    origin_delay_rate: float | None = None
    temperature_2m: float | None = None
    precipitation: float | None = None
    windspeed_10m: float | None = None


class BatchPredictionRequest(BaseModel):
    trips: list[PredictionRequest]


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "model_loaded": True,
        "threshold": predictor._threshold,
    }


@app.get("/")
def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/dashboard")
def dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "dashboard_prod.html")


@app.post("/predict")
def predict_trip(request: PredictionRequest) -> dict[str, Any]:
    try:
        raw_payload = request.model_dump(exclude_none=True)
        built = feature_builder.build(raw_payload)
        prediction = predictor.predict(built.features)
        return {
            "prediction": prediction,
            "features": built.features,
            "assumptions": built.assumptions,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}") from exc


@app.post("/predict/batch")
def predict_batch(request: BatchPredictionRequest) -> dict[str, Any]:
    try:
        feature_rows = []
        assumptions = []

        for trip in request.trips:
            built = feature_builder.build(trip.model_dump(exclude_none=True))
            feature_rows.append(built.features)
            assumptions.append(built.assumptions)

        predictions = predictor.predict(feature_rows)
        return {
            "predictions": predictions,
            "features": feature_rows,
            "assumptions": assumptions,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {exc}") from exc