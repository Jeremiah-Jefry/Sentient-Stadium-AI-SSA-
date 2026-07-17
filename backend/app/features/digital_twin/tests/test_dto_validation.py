"""Unit tests for Pydantic DTO validation."""

import pytest
from pydantic import ValidationError

from app.features.digital_twin.dto.entity_requests import (
    CreateEntityRequest,
    UpdateEntityRequest,
    SearchEntityRequest,
)
from app.features.digital_twin.dto.zone_requests import CreateVenueRequest, CreateZoneRequest
from app.features.digital_twin.dto.spatial_requests import (
    NearbySearchRequest,
    PathfindingRequest,
    CreateEdgeRequest,
)


class TestCreateEntityRequest:
    def test_valid(self) -> None:
        req = CreateEntityRequest(
            name="Gate A1",
            entity_type="gate",
            venue_id="00000000-0000-0000-0000-000000000001",
            coordinates_lat=40.0,
            coordinates_lon=-74.0,
        )
        assert req.name == "Gate A1"
        assert req.max_capacity == 0

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateEntityRequest(
                name="",
                entity_type="gate",
                venue_id="00000000-0000-0000-0000-000000000001",
                coordinates_lat=40.0,
                coordinates_lon=-74.0,
            )

    def test_latitude_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            CreateEntityRequest(
                name="Gate A1",
                entity_type="gate",
                venue_id="00000000-0000-0000-0000-000000000001",
                coordinates_lat=91.0,
                coordinates_lon=-74.0,
            )

    def test_longitude_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            CreateEntityRequest(
                name="Gate A1",
                entity_type="gate",
                venue_id="00000000-0000-0000-0000-000000000001",
                coordinates_lat=40.0,
                coordinates_lon=181.0,
            )

    def test_negative_capacity_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateEntityRequest(
                name="Gate A1",
                entity_type="gate",
                venue_id="00000000-0000-0000-0000-000000000001",
                coordinates_lat=40.0,
                coordinates_lon=-74.0,
                current_capacity=-1,
            )


class TestUpdateEntityRequest:
    def test_partial_update(self) -> None:
        req = UpdateEntityRequest(name="Updated Name")
        assert req.name == "Updated Name"
        assert req.entity_type is None

    def test_empty_update(self) -> None:
        req = UpdateEntityRequest()
        assert req.model_dump(exclude_none=True) == {}


class TestSearchEntityRequest:
    def test_defaults(self) -> None:
        req = SearchEntityRequest()
        assert req.page == 1
        assert req.page_size == 20

    def test_custom_pagination(self) -> None:
        req = SearchEntityRequest(page=5, page_size=50)
        assert req.page == 5
        assert req.page_size == 50

    def test_page_size_exceeds_max(self) -> None:
        with pytest.raises(ValidationError):
            SearchEntityRequest(page_size=101)


class TestCreateVenueRequest:
    def test_valid(self) -> None:
        req = CreateVenueRequest(
            name="MetLife Stadium",
            coordinates_lat=40.8135,
            coordinates_lon=-74.0745,
        )
        assert req.timezone == "UTC"

    def test_empty_name(self) -> None:
        with pytest.raises(ValidationError):
            CreateVenueRequest(name="", coordinates_lat=40.0, coordinates_lon=-74.0)


class TestNearbySearchRequest:
    def test_valid(self) -> None:
        req = NearbySearchRequest(latitude=40.0, longitude=-74.0)
        assert req.radius_meters == 500.0
        assert req.limit == 20

    def test_radius_exceeds_max(self) -> None:
        with pytest.raises(ValidationError):
            NearbySearchRequest(latitude=40.0, longitude=-74.0, radius_meters=11000)

    def test_limit_exceeds_max(self) -> None:
        with pytest.raises(ValidationError):
            NearbySearchRequest(latitude=40.0, longitude=-74.0, limit=101)


class TestCreateEdgeRequest:
    def test_valid(self) -> None:
        req = CreateEdgeRequest(
            from_entity_id="00000000-0000-0000-0000-000000000001",
            to_entity_id="00000000-0000-0000-0000-000000000002",
            venue_id="00000000-0000-0000-0000-000000000003",
        )
        assert req.edge_type == "walking"
        assert req.weight == 1.0
        assert req.is_bidirectional is True

    def test_zero_weight_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateEdgeRequest(
                from_entity_id="00000000-0000-0000-0000-000000000001",
                to_entity_id="00000000-0000-0000-0000-000000000002",
                venue_id="00000000-0000-0000-0000-000000000003",
                weight=0.0,
            )
