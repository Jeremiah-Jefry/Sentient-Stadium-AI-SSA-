"""Digital twin schema - entities, zones, edges, events, versions.

Revision ID: 002_digital_twin
Revises: 001_initial
Create Date: 2026-07-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002_digital_twin"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enum types
    entity_type_enum = postgresql.ENUM(
        "gate", "entrance", "exit", "zone", "concourse", "corridor",
        "escalator", "elevator", "ramp", "staircase", "restroom",
        "medical_room", "food_court", "vendor", "security_checkpoint",
        "parking_area", "metro_station", "bus_stop", "shuttle_point",
        "camera", "iot_sensor", "volunteer_position", "crowd_cluster",
        "emergency_exit", "fire_extinguisher", "aed", "wheelchair_station",
        "cleaning_bin", "charging_station", "lost_and_found",
        "information_desk", "seating_block", "seating_row", "seat",
        "concession_stand", "first_aid_post", "command_center",
        "press_box", "vip_lounge", "luxury_box", "field", "stage",
        "barrier", "signage", "lighting", "speaker", "display_screen",
        "water_fountain", "wifi_access_point",
        name="dt_entitytype", create_type=False,
    )
    operational_status_enum = postgresql.ENUM(
        "operational", "degraded", "maintenance", "offline",
        "emergency", "closed", "temporary_closure",
        name="dt_operationalstatus", create_type=False,
    )
    entity_health_enum = postgresql.ENUM(
        "healthy", "warning", "critical", "unknown",
        name="dt_entityhealth", create_type=False,
    )
    accessibility_level_enum = postgresql.ENUM(
        "full", "partial", "none",
        name="dt_accessibilitylevel", create_type=False,
    )
    zone_type_enum = postgresql.ENUM(
        "stadium", "sector", "zone", "sub_zone", "gate",
        "checkpoint", "node", "floor", "level", "section", "area",
        name="dt_zonetype", create_type=False,
    )
    edge_type_enum = postgresql.ENUM(
        "walking", "wheelchair", "emergency", "staff_only",
        "restricted", "maintenance",
        name="dt_edgetype", create_type=False,
    )

    for e in [entity_type_enum, operational_status_enum, entity_health_enum,
              accessibility_level_enum, zone_type_enum, edge_type_enum]:
        e.create(op.get_bind(), checkfirst=True)

    # Venues table
    op.create_table(
        "dt_venues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("coordinates_lat", sa.Numeric(10, 7), nullable=False),
        sa.Column("coordinates_lon", sa.Numeric(10, 7), nullable=False),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="UTC"),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_dt_venues_name", "dt_venues", ["name"])

    # Zones table (hierarchical, self-referential)
    op.create_table(
        "dt_zones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("zone_type", zone_type_enum, nullable=False, server_default="zone"),
        sa.Column("level", sa.Integer, nullable=False, server_default="0"),
        sa.Column("parent_zone_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dt_zones.id", ondelete="SET NULL"), nullable=True),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dt_venues.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bounds_lat_min", sa.Numeric(10, 7), nullable=True),
        sa.Column("bounds_lat_max", sa.Numeric(10, 7), nullable=True),
        sa.Column("bounds_lon_min", sa.Numeric(10, 7), nullable=True),
        sa.Column("bounds_lon_max", sa.Numeric(10, 7), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_dt_zones_venue_id", "dt_zones", ["venue_id"])
    op.create_index("ix_dt_zones_parent_zone_id", "dt_zones", ["parent_zone_id"])
    op.create_index("ix_dt_zones_zone_type", "dt_zones", ["zone_type"])
    op.create_index("ix_dt_zones_level", "dt_zones", ["level"])

    # Entities table (core of the digital twin)
    op.create_table(
        "dt_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("entity_type", entity_type_enum, nullable=False),
        sa.Column("current_state", postgresql.JSONB, nullable=True),
        sa.Column("operational_status", operational_status_enum, nullable=False, server_default="operational"),
        sa.Column("current_health", entity_health_enum, nullable=False, server_default="healthy"),
        sa.Column("current_capacity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_capacity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("coordinates_lat", sa.Numeric(10, 7), nullable=False),
        sa.Column("coordinates_lon", sa.Numeric(10, 7), nullable=False),
        sa.Column("indoor_x", sa.Numeric(10, 3), nullable=True),
        sa.Column("indoor_y", sa.Numeric(10, 3), nullable=True),
        sa.Column("floor_number", sa.Integer, nullable=True),
        sa.Column("building_level", sa.Integer, nullable=True),
        sa.Column("accessibility_level", accessibility_level_enum, nullable=False, server_default="full"),
        sa.Column("accessibility_metadata", postgresql.JSONB, nullable=True),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dt_venues.id", ondelete="CASCADE"), nullable=False),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dt_zones.id", ondelete="SET NULL"), nullable=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dt_entities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_dt_entities_venue_id", "dt_entities", ["venue_id"])
    op.create_index("ix_dt_entities_zone_id", "dt_entities", ["zone_id"])
    op.create_index("ix_dt_entities_type", "dt_entities", ["entity_type"])
    op.create_index("ix_dt_entities_operational_status", "dt_entities", ["operational_status"])
    op.create_index("ix_dt_entities_parent_id", "dt_entities", ["parent_id"])
    op.create_index("ix_dt_entities_coords", "dt_entities", ["coordinates_lat", "coordinates_lon"])

    # Entity Components (ECS)
    op.create_table(
        "dt_entity_components",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dt_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_type", sa.String(50), nullable=False),
        sa.Column("component_data", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_dt_entity_components_entity_id", "dt_entity_components", ["entity_id"])
    op.create_index("ix_dt_entity_components_type", "dt_entity_components", ["entity_id", "component_type"], unique=True)

    # Edges (graph connections)
    op.create_table(
        "dt_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("from_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dt_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dt_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("edge_type", edge_type_enum, nullable=False, server_default="walking"),
        sa.Column("weight", sa.Numeric(10, 2), nullable=False, server_default="1.0"),
        sa.Column("is_bidirectional", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("accessibility_level", accessibility_level_enum, nullable=False, server_default="full"),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dt_venues.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_dt_edges_from_entity_id", "dt_edges", ["from_entity_id"])
    op.create_index("ix_dt_edges_to_entity_id", "dt_edges", ["to_entity_id"])
    op.create_index("ix_dt_edges_edge_type", "dt_edges", ["edge_type"])
    op.create_index("ix_dt_edges_venue_id", "dt_edges", ["venue_id"])

    # Entity Events (append-only log)
    op.create_table(
        "dt_entity_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dt_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("event_data", postgresql.JSONB, nullable=True),
        sa.Column("source", sa.String(100), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_dt_entity_events_entity_id", "dt_entity_events", ["entity_id"])
    op.create_index("ix_dt_entity_events_event_type", "dt_entity_events", ["event_type"])
    op.create_index("ix_dt_entity_events_created_at", "dt_entity_events", ["created_at"])
    op.create_index("ix_dt_entity_events_entity_type", "dt_entity_events", ["entity_id", "event_type"])

    # Entity Versions (immutable snapshots)
    op.create_table(
        "dt_entity_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dt_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("state_snapshot", postgresql.JSONB, nullable=False),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("change_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_dt_entity_versions_entity_id", "dt_entity_versions", ["entity_id"])
    op.create_index("ix_dt_entity_versions_entity_version", "dt_entity_versions", ["entity_id", "version"], unique=True)


def downgrade() -> None:
    op.drop_table("dt_entity_versions")
    op.drop_table("dt_entity_events")
    op.drop_table("dt_edges")
    op.drop_table("dt_entity_components")
    op.drop_table("dt_entities")
    op.drop_table("dt_zones")
    op.drop_table("dt_venues")

    for name in ["dt_edgetype", "dt_zonetype", "dt_accessibilitylevel",
                  "dt_entityhealth", "dt_operationalstatus", "dt_entitytype"]:
        postgresql.ENUM(name=name).drop(op.get_bind(), checkfirst=True)
