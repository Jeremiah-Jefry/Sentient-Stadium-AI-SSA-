"""FastAPI dependency injection for the Digital Twin module."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.digital_twin.repositories.edge_repository import EdgeRepository
from app.features.digital_twin.repositories.entity_repository import EntityRepository
from app.features.digital_twin.repositories.event_repository import EventRepository
from app.features.digital_twin.repositories.venue_repository import VenueRepository
from app.features.digital_twin.repositories.version_repository import VersionRepository
from app.features.digital_twin.repositories.zone_repository import ZoneRepository
from app.features.digital_twin.services.entity_service import EntityService
from app.features.digital_twin.services.event_service import EventService
from app.features.digital_twin.services.spatial_service import SpatialService
from app.features.digital_twin.services.zone_service import ZoneService
from app.shared.database import get_db_session


def get_entity_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> EntityRepository:
    return EntityRepository(session)


def get_zone_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ZoneRepository:
    return ZoneRepository(session)


def get_venue_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> VenueRepository:
    return VenueRepository(session)


def get_edge_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> EdgeRepository:
    return EdgeRepository(session)


def get_event_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> EventRepository:
    return EventRepository(session)


def get_version_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> VersionRepository:
    return VersionRepository(session)


def get_entity_service(
    entity_repo: Annotated[EntityRepository, Depends(get_entity_repository)],
    event_repo: Annotated[EventRepository, Depends(get_event_repository)],
    version_repo: Annotated[VersionRepository, Depends(get_version_repository)],
) -> EntityService:
    return EntityService(entity_repo, event_repo, version_repo)


def get_zone_service(
    zone_repo: Annotated[ZoneRepository, Depends(get_zone_repository)],
    venue_repo: Annotated[VenueRepository, Depends(get_venue_repository)],
) -> ZoneService:
    return ZoneService(zone_repo, venue_repo)


def get_spatial_service(
    entity_repo: Annotated[EntityRepository, Depends(get_entity_repository)],
    edge_repo: Annotated[EdgeRepository, Depends(get_edge_repository)],
) -> SpatialService:
    return SpatialService(entity_repo, edge_repo)


def get_event_service(
    event_repo: Annotated[EventRepository, Depends(get_event_repository)],
) -> EventService:
    return EventService(event_repo)
