"""Routing profiles — per-user-type optimization rules and constraints.

Each profile defines:
- Objective weight vector (travel time vs safety vs accessibility vs crowd)
- Allowed edge types
- Accessibility requirements
- Special routing rules
"""

from __future__ import annotations

from dataclasses import dataclass

from app.features.navigation.models.enums import (
    GraphEdgeType,
    ObjectiveWeight,
    RoutingProfile,
)


@dataclass(frozen=True, slots=True)
class ProfileConfig:
    """Immutable routing configuration for a specific user profile."""

    profile: RoutingProfile
    objective_weights: dict[ObjectiveWeight, float]
    allowed_edge_types: set[str]
    requires_accessibility: bool = False
    prefer_elevators: bool = False
    prefer_ramps: bool = False
    avoid_stairs: bool = False
    avoid_escalators: bool = False
    max_crowd_exposure: float = 1.0
    priority_boost_emergency: bool = False
    priority_boost_medical: bool = False
    prefer_staff_only: bool = False
    prefer_emergency_exits: bool = False
    max_floor_change: int = 99


DEFAULT_WEIGHTS: dict[ObjectiveWeight, float] = {
    ObjectiveWeight.TRAVEL_TIME: 0.4,
    ObjectiveWeight.SAFETY: 0.2,
    ObjectiveWeight.ACCESSIBILITY: 0.1,
    ObjectiveWeight.CROWD_EXPOSURE: 0.15,
    ObjectiveWeight.WALKING_DISTANCE: 0.1,
    ObjectiveWeight.RISK: 0.05,
}

ALL_WALKING_EDGES = {
    GraphEdgeType.WALKING.value,
    GraphEdgeType.WHEELCHAIR.value,
    GraphEdgeType.EMERGENCY.value,
    GraphEdgeType.STAFF_ONLY.value,
    GraphEdgeType.ESCALATOR.value,
    GraphEdgeType.ELEVATOR.value,
    GraphEdgeType.RAMP.value,
    GraphEdgeType.STAIRS.value,
}

PROFILE_CONFIGS: dict[RoutingProfile, ProfileConfig] = {
    RoutingProfile.SPECTATOR: ProfileConfig(
        profile=RoutingProfile.SPECTATOR,
        objective_weights={
            ObjectiveWeight.TRAVEL_TIME: 0.45,
            ObjectiveWeight.SAFETY: 0.15,
            ObjectiveWeight.CROWD_EXPOSURE: 0.2,
            ObjectiveWeight.WALKING_DISTANCE: 0.15,
            ObjectiveWeight.ACCESSIBILITY: 0.05,
        },
        allowed_edge_types=ALL_WALKING_EDGES - {GraphEdgeType.STAFF_ONLY.value},
    ),
    RoutingProfile.VOLUNTEER: ProfileConfig(
        profile=RoutingProfile.VOLUNTEER,
        objective_weights={
            ObjectiveWeight.TRAVEL_TIME: 0.3,
            ObjectiveWeight.SAFETY: 0.2,
            ObjectiveWeight.VOLUNTEER_PRIORITY: 0.25,
            ObjectiveWeight.CROWD_EXPOSURE: 0.15,
            ObjectiveWeight.WALKING_DISTANCE: 0.1,
        },
        allowed_edge_types=ALL_WALKING_EDGES,
        prefer_staff_only=True,
    ),
    RoutingProfile.WHEELCHAIR_USER: ProfileConfig(
        profile=RoutingProfile.WHEELCHAIR_USER,
        objective_weights={
            ObjectiveWeight.TRAVEL_TIME: 0.2,
            ObjectiveWeight.SAFETY: 0.15,
            ObjectiveWeight.ACCESSIBILITY: 0.45,
            ObjectiveWeight.WALKING_DISTANCE: 0.15,
            ObjectiveWeight.CROWD_EXPOSURE: 0.05,
        },
        allowed_edge_types={
            GraphEdgeType.WALKING.value,
            GraphEdgeType.WHEELCHAIR.value,
            GraphEdgeType.ELEVATOR.value,
            GraphEdgeType.RAMP.value,
        },
        requires_accessibility=True,
        prefer_elevators=True,
        prefer_ramps=True,
        avoid_stairs=True,
        avoid_escalators=True,
        max_crowd_exposure=0.6,
    ),
    RoutingProfile.BLIND_USER: ProfileConfig(
        profile=RoutingProfile.BLIND_USER,
        objective_weights={
            ObjectiveWeight.TRAVEL_TIME: 0.2,
            ObjectiveWeight.SAFETY: 0.35,
            ObjectiveWeight.ACCESSIBILITY: 0.3,
            ObjectiveWeight.CROWD_EXPOSURE: 0.1,
            ObjectiveWeight.WALKING_DISTANCE: 0.05,
        },
        allowed_edge_types={
            GraphEdgeType.WALKING.value,
            GraphEdgeType.WHEELCHAIR.value,
            GraphEdgeType.ELEVATOR.value,
        },
        requires_accessibility=True,
        prefer_elevators=True,
        max_crowd_exposure=0.5,
    ),
    RoutingProfile.HEARING_IMPAIRED: ProfileConfig(
        profile=RoutingProfile.HEARING_IMPAIRED,
        objective_weights={
            ObjectiveWeight.TRAVEL_TIME: 0.35,
            ObjectiveWeight.SAFETY: 0.25,
            ObjectiveWeight.ACCESSIBILITY: 0.2,
            ObjectiveWeight.CROWD_EXPOSURE: 0.1,
            ObjectiveWeight.WALKING_DISTANCE: 0.1,
        },
        allowed_edge_types=ALL_WALKING_EDGES - {GraphEdgeType.STAFF_ONLY.value},
        prefer_emergency_exits=True,
    ),
    RoutingProfile.MEDICAL_TEAM: ProfileConfig(
        profile=RoutingProfile.MEDICAL_TEAM,
        objective_weights={
            ObjectiveWeight.TRAVEL_TIME: 0.5,
            ObjectiveWeight.SAFETY: 0.1,
            ObjectiveWeight.MEDICAL_PRIORITY: 0.3,
            ObjectiveWeight.CROWD_EXPOSURE: 0.05,
            ObjectiveWeight.WALKING_DISTANCE: 0.05,
        },
        allowed_edge_types=ALL_WALKING_EDGES,
        priority_boost_medical=True,
        prefer_staff_only=True,
    ),
    RoutingProfile.SECURITY_TEAM: ProfileConfig(
        profile=RoutingProfile.SECURITY_TEAM,
        objective_weights={
            ObjectiveWeight.TRAVEL_TIME: 0.4,
            ObjectiveWeight.SAFETY: 0.3,
            ObjectiveWeight.VOLUNTEER_PRIORITY: 0.15,
            ObjectiveWeight.CROWD_EXPOSURE: 0.1,
            ObjectiveWeight.WALKING_DISTANCE: 0.05,
        },
        allowed_edge_types=ALL_WALKING_EDGES,
        prefer_staff_only=True,
        prefer_emergency_exits=True,
    ),
    RoutingProfile.VIP: ProfileConfig(
        profile=RoutingProfile.VIP,
        objective_weights={
            ObjectiveWeight.TRAVEL_TIME: 0.35,
            ObjectiveWeight.SAFETY: 0.25,
            ObjectiveWeight.CROWD_EXPOSURE: 0.3,
            ObjectiveWeight.WALKING_DISTANCE: 0.1,
        },
        allowed_edge_types=ALL_WALKING_EDGES - {GraphEdgeType.STAFF_ONLY.value},
        max_crowd_exposure=0.3,
    ),
    RoutingProfile.MAINTENANCE_CREW: ProfileConfig(
        profile=RoutingProfile.MAINTENANCE_CREW,
        objective_weights={
            ObjectiveWeight.TRAVEL_TIME: 0.5,
            ObjectiveWeight.WALKING_DISTANCE: 0.3,
            ObjectiveWeight.SAFETY: 0.1,
            ObjectiveWeight.CROWD_EXPOSURE: 0.1,
        },
        allowed_edge_types=ALL_WALKING_EDGES,
        prefer_staff_only=True,
    ),
    RoutingProfile.CLEANING_CREW: ProfileConfig(
        profile=RoutingProfile.CLEANING_CREW,
        objective_weights={
            ObjectiveWeight.TRAVEL_TIME: 0.5,
            ObjectiveWeight.WALKING_DISTANCE: 0.3,
            ObjectiveWeight.SAFETY: 0.1,
            ObjectiveWeight.CROWD_EXPOSURE: 0.1,
        },
        allowed_edge_types=ALL_WALKING_EDGES,
        prefer_staff_only=True,
    ),
    RoutingProfile.ADMINISTRATOR: ProfileConfig(
        profile=RoutingProfile.ADMINISTRATOR,
        objective_weights=DEFAULT_WEIGHTS,
        allowed_edge_types=ALL_WALKING_EDGES,
    ),
}


def get_profile_config(profile: RoutingProfile) -> ProfileConfig:
    """Retrieve routing profile configuration. Raises if not found."""
    config = PROFILE_CONFIGS.get(profile)
    if config is None:
        raise KeyError(f"Unknown routing profile: {profile}")
    return config
