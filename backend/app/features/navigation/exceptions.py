"""Navigation module exception hierarchy."""

from __future__ import annotations


class NavigationError(Exception):
    """Base exception for all navigation errors."""

    def __init__(
        self,
        message: str,
        error_code: str,
        details: dict | None = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class RouteNotFoundError(NavigationError):
    def __init__(self, details: dict | None = None) -> None:
        super().__init__(
            message="No route found between the specified locations",
            error_code="ROUTE_NOT_FOUND",
            details=details,
        )


class GraphNotLoadedError(NavigationError):
    def __init__(self, venue_id: str = "") -> None:
        super().__init__(
            message=f"Navigation graph not loaded for venue {venue_id}",
            error_code="GRAPH_NOT_LOADED",
            details={"venue_id": venue_id},
        )


class NodeNotFoundError(NavigationError):
    def __init__(self, node_id: str = "") -> None:
        super().__init__(
            message=f"Node '{node_id}' not found in navigation graph",
            error_code="NODE_NOT_FOUND",
            details={"node_id": node_id},
        )


class InvalidRoutingProfileError(NavigationError):
    def __init__(self, profile: str = "") -> None:
        super().__init__(
            message=f"Invalid routing profile: {profile}",
            error_code="INVALID_ROUTING_PROFILE",
            details={"profile": profile},
        )


class AccessibilityRouteError(NavigationError):
    def __init__(
        self,
        message: str = "No accessible route available",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="ACCESSIBILITY_ROUTE_ERROR",
            details=details,
        )


class EmergencyRoutingError(NavigationError):
    def __init__(
        self,
        message: str = "Emergency routing failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="EMERGENCY_ROUTING_ERROR",
            details=details,
        )


class ReplanningError(NavigationError):
    def __init__(self, message: str = "Replanning failed", details: dict | None = None) -> None:
        super().__init__(
            message=message,
            error_code="REPLANNING_ERROR",
            details=details,
        )


class SimulationError(NavigationError):
    def __init__(
        self,
        message: str = "Route simulation failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="SIMULATION_ERROR",
            details=details,
        )


class CacheCorruptionError(NavigationError):
    def __init__(self, details: dict | None = None) -> None:
        super().__init__(
            message="Route cache integrity check failed",
            error_code="CACHE_CORRUPTION",
            details=details,
        )


class ConcurrencyConflictError(NavigationError):
    def __init__(self, details: dict | None = None) -> None:
        super().__init__(
            message="Concurrent graph modification detected",
            error_code="CONCURRENCY_CONFLICT",
            details=details,
        )
