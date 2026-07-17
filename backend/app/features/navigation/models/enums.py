"""Navigation domain enums — routing profiles, route types, weight factors."""

from __future__ import annotations

import enum


class RoutingProfile(str, enum.Enum):
    """Independent routing profiles with unique optimization rules."""

    SPECTATOR = "spectator"
    VOLUNTEER = "volunteer"
    WHEELCHAIR_USER = "wheelchair_user"
    BLIND_USER = "blind_user"
    HEARING_IMPAIRED = "hearing_impaired"
    MEDICAL_TEAM = "medical_team"
    SECURITY_TEAM = "security_team"
    VIP = "vip"
    MAINTENANCE_CREW = "maintenance_crew"
    CLEANING_CREW = "cleaning_crew"
    ADMINISTRATOR = "administrator"


class RouteType(str, enum.Enum):
    """Functional classification of computed routes."""

    FASTEST = "fastest"
    SAFEST = "safest"
    LEAST_CROWDED = "least_crowded"
    ACCESSIBLE = "accessible"
    EMERGENCY = "emergency"
    VOLUNTEER_ASSIGNMENT = "volunteer_assignment"
    MEDICAL_RESPONSE = "medical_response"
    VIP = "vip"
    MAINTENANCE = "maintenance"
    EVACUATION = "evacuation"
    DELIVERY = "delivery"


class EmergencyType(str, enum.Enum):
    """Emergency scenario classifications for specialized routing."""

    FIRE = "fire"
    MEDICAL = "medical"
    EVACUATION = "evacuation"
    SECURITY = "security"
    LOST_CHILD = "lost_child"
    CROWD_CRUSH = "crowd_crush"
    EQUIPMENT_FAILURE = "equipment_failure"
    CHEMICAL_HAZARD = "chemical_hazard"
    POWER_OUTAGE = "power_outage"
    FLOODING = "flooding"


class EdgeWeightFactor(str, enum.Enum):
    """Factors that dynamically modify edge traversal weights."""

    BASE_DISTANCE = "base_distance"
    CROWD_DENSITY = "crowd_density"
    WALKING_SPEED = "walking_speed"
    WEATHER = "weather"
    ESCALATOR_STATUS = "escalator_status"
    ELEVATOR_STATUS = "elevator_status"
    EMERGENCY_STATUS = "emergency_status"
    ACCESSIBILITY = "accessibility"
    MAINTENANCE = "maintenance"
    SECURITY_RESTRICTION = "security_restriction"
    MEDICAL_INCIDENT = "medical_incident"
    CLEANING = "cleaning"
    TEMPORARY_CLOSURE = "temporary_closure"
    RISK_SCORE = "risk_score"
    PREDICTED_CONGESTION = "predicted_congestion"
    WAITING_TIME = "waiting_time"
    ENERGY_COST = "energy_cost"


class ObjectiveWeight(str, enum.Enum):
    """Multi-objective optimization weight categories."""

    TRAVEL_TIME = "travel_time"
    SAFETY = "safety"
    ACCESSIBILITY = "accessibility"
    CROWD_EXPOSURE = "crowd_exposure"
    WALKING_DISTANCE = "walking_distance"
    RISK = "risk"
    VOLUNTEER_PRIORITY = "volunteer_priority"
    MEDICAL_PRIORITY = "medical_priority"
    EMERGENCY_PRIORITY = "emergency_priority"
    ENERGY_COST = "energy_cost"
    ROUTE_RELIABILITY = "route_reliability"


class SpatialQueryType(str, enum.Enum):
    """Types of spatial proximity queries."""

    NEAREST_EXIT = "nearest_exit"
    NEAREST_AED = "nearest_aed"
    NEAREST_MEDICAL_ROOM = "nearest_medical_room"
    NEAREST_VOLUNTEER = "nearest_volunteer"
    NEAREST_RESTROOM = "nearest_restroom"
    NEAREST_WHEELCHAIR_STATION = "nearest_wheelchair_station"
    NEAREST_INFORMATION_DESK = "nearest_information_desk"
    NEAREST_SECURITY_OFFICER = "nearest_security_officer"
    NEARBY_CROWD_DENSITY = "nearby_crowd_density"
    NEARBY_INCIDENTS = "nearby_incidents"
    NEARBY_HAZARDS = "nearby_hazards"
    NEARBY_ACCESSIBLE_ROUTES = "nearby_accessible_routes"


class ReplanTrigger(str, enum.Enum):
    """Conditions that trigger automatic route recalculation."""

    GATE_CLOSURE = "gate_closure"
    CROWD_SURGE = "crowd_surge"
    MEDICAL_INCIDENT = "medical_incident"
    WEATHER_CHANGE = "weather_change"
    SECURITY_RESTRICTION = "security_restriction"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"
    ESCALATOR_DOWN = "escalator_down"
    ELEVATOR_DOWN = "elevator_down"
    EMERGENCY_DECLARED = "emergency_declared"


class GraphEdgeType(str, enum.Enum):
    """Extended edge types beyond Module 2's base types for navigation."""

    WALKING = "walking"
    WHEELCHAIR = "wheelchair"
    EMERGENCY = "emergency"
    STAFF_ONLY = "staff_only"
    RESTRICTED = "restricted"
    MAINTENANCE = "maintenance"
    ESCALATOR = "escalator"
    ELEVATOR = "elevator"
    RAMP = "ramp"
    STAIRS = "stairs"
