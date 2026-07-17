"""Sensor API routes — registration, query, and health endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.features.event_streaming.api.deps import get_sensor_fusion_service, get_sensor_repo
from app.features.event_streaming.dto.event_requests import (
    RegisterSensorRequest,
)
from app.features.event_streaming.dto.event_responses import SensorHealthResponse, SensorResponse
from app.features.event_streaming.models.sensor import SensorRegistry
from app.features.event_streaming.repositories.sensor_repository import SensorRepository
from app.features.event_streaming.services.sensor_fusion_service import SensorFusionService
from app.shared.result import Success

router = APIRouter(prefix="/sensors", tags=["Sensors"])


@router.post("/", response_model=SensorResponse, status_code=status.HTTP_201_CREATED)
async def register_sensor(
    req: RegisterSensorRequest,
    sensor_repo: SensorRepository = Depends(get_sensor_repo),
) -> SensorResponse:
    """Register a new sensor in the registry."""
    sensor = SensorRegistry(
        name=req.name,
        description=req.description,
        sensor_type=req.sensor_type,
        venue_id=uuid.UUID(req.venue_id),
        entity_id=uuid.UUID(req.entity_id) if req.entity_id else None,
        zone_id=uuid.UUID(req.zone_id) if req.zone_id else None,
        coordinates_lat=req.coordinates_lat,
        coordinates_lon=req.coordinates_lon,
        indoor_x=req.indoor_x,
        indoor_y=req.indoor_y,
        floor_number=req.floor_number,
        reading_interval_ms=req.reading_interval_ms,
        accuracy=req.accuracy,
        range_meters=req.range_meters,
        firmware_version=req.firmware_version,
        metadata_json=req.metadata_json,
    )
    result = await sensor_repo.create(sensor)
    if not isinstance(result, Success):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Failed to register sensor")

    s = result.value
    return SensorResponse(
        id=str(s.id), name=s.name, description=s.description,
        sensor_type=s.sensor_type, venue_id=str(s.venue_id),
        entity_id=str(s.entity_id) if s.entity_id else None,
        zone_id=str(s.zone_id) if s.zone_id else None,
        coordinates_lat=s.coordinates_lat, coordinates_lon=s.coordinates_lon,
        indoor_x=s.indoor_x, indoor_y=s.indoor_y, floor_number=s.floor_number,
        is_active=s.is_active, is_calibrated=s.is_calibrated,
        last_calibration_at=s.last_calibration_at,
        reading_interval_ms=s.reading_interval_ms,
        accuracy=s.accuracy, range_meters=s.range_meters,
        firmware_version=s.firmware_version, metadata_json=s.metadata_json,
        created_at=str(s.created_at), updated_at=str(s.updated_at),
    )


@router.get("/health/{venue_id}", response_model=SensorHealthResponse)
async def get_sensor_health(
    venue_id: str,
    sensor_repo: SensorRepository = Depends(get_sensor_repo),
) -> SensorHealthResponse:
    """Get aggregated sensor health for a venue."""
    venue_uuid = uuid.UUID(venue_id)
    count_result = await sensor_repo.count_by_venue(venue_uuid)
    active_result = await sensor_repo.get_active_by_venue(venue_uuid)

    counts = (
        count_result.value
        if isinstance(count_result, Success)
        else {"active": 0, "inactive": 0}
    )
    sensors = active_result.value if isinstance(active_result, Success) else []

    by_type: dict[str, dict[str, int]] = {}
    for s in sensors:
        t = s.sensor_type
        if t not in by_type:
            by_type[t] = {"active": 0, "inactive": 0}
        by_type[t]["active"] += 1

    return SensorHealthResponse(
        total_sensors=counts.get("active", 0) + counts.get("inactive", 0),
        active_sensors=counts.get("active", 0),
        inactive_sensors=counts.get("inactive", 0),
        calibrated_sensors=sum(1 for s in sensors if s.is_calibrated),
        by_type=by_type,
    )


@router.get("/fusion-status/{venue_id}")
async def get_fusion_status(
    venue_id: str,
    zone_id: str | None = Query(None),
    fusion_service: SensorFusionService = Depends(get_sensor_fusion_service),
) -> dict:
    """Get current sensor fusion status for a zone."""
    if zone_id:
        return fusion_service.get_zone_status(zone_id)
    return fusion_service.stats
