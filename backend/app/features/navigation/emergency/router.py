"""Emergency routing engine — specialized routing for emergency scenarios.

Handles fire, medical, evacuation, security, lost child, crowd crush,
equipment failure, chemical hazard, power outage, and flooding scenarios.
Each scenario applies unique edge weight penalties and path selection rules.
"""

from __future__ import annotations

import uuid

from app.features.navigation.exceptions import EmergencyRoutingError
from app.features.navigation.graph.graph_manager import NavigationGraph
from app.features.navigation.graph.models import PathResult, WeightContext
from app.features.navigation.models.enums import EmergencyType
from app.features.navigation.pathfinding.algorithm import AlgorithmRegistry

EMERGENCY_EDGE_PENALTIES: dict[EmergencyType, dict[str, float]] = {
    EmergencyType.FIRE: {"stairs": 0.2, "escalator": 0.3, "elevator": 0.1},
    EmergencyType.MEDICAL: {"stairs": 0.5, "escalator": 0.4, "elevator": 0.8},
    EmergencyType.EVACUATION: {"stairs": 0.3, "escalator": 0.2, "elevator": 0.1},
    EmergencyType.SECURITY: {},
    EmergencyType.LOST_CHILD: {"stairs": 0.6, "escalator": 0.5, "elevator": 0.9},
    EmergencyType.CROWD_CRUSH: {"walking": 0.3},
    EmergencyType.EQUIPMENT_FAILURE: {},
    EmergencyType.CHEMICAL_HAZARD: {"walking": 0.5},
    EmergencyType.POWER_OUTAGE: {
        "escalator": 0.9, "elevator": 0.9,
    },
    EmergencyType.FLOODING: {"walking": 0.7, "ramp": 0.5},
}

EMERGENCY_DESTINATION_TYPES: dict[EmergencyType, set[str]] = {
    EmergencyType.FIRE: {"emergency_exit", "exit"},
    EmergencyType.MEDICAL: {"medical_room", "first_aid_post", "aed"},
    EmergencyType.EVACUATION: {"emergency_exit", "exit"},
    EmergencyType.SECURITY: {"security_checkpoint", "command_center"},
    EmergencyType.LOST_CHILD: {"information_desk", "command_center"},
    EmergencyType.CROWD_CRUSH: {"emergency_exit", "exit"},
    EmergencyType.EQUIPMENT_FAILURE: {"command_center"},
    EmergencyType.CHEMICAL_HAZARD: {"emergency_exit", "exit"},
    EmergencyType.POWER_OUTAGE: {"emergency_exit", "exit"},
    EmergencyType.FLOODING: {"emergency_exit", "exit"},
}


class EmergencyRouter:
    """Computes emergency-specific routes with scenario-appropriate penalties."""

    def __init__(
        self,
        graph: NavigationGraph,
        registry: AlgorithmRegistry,
    ) -> None:
        self._graph = graph
        self._registry = registry

    def compute_emergency_route(
        self,
        start: uuid.UUID,
        emergency_type: EmergencyType,
        ctx: WeightContext | None = None,
        destination_id: uuid.UUID | None = None,
    ) -> PathResult:
        """Compute optimal emergency route.

        If destination_id is provided, routes to that specific node.
        Otherwise routes to nearest appropriate facility.
        """
        weight_ctx = ctx or WeightContext(emergency_active=True)
        weight_ctx.emergency_active = True

        if emergency_type == EmergencyType.EVACUATION:
            weight_ctx.crowd_density = 0.0

        algo = self._registry.select(self._graph.node_count)

        if destination_id:
            try:
                return algo.find_path(
                    self._graph, start, destination_id, weight_ctx,
                )
            except Exception as exc:
                raise EmergencyRoutingError(
                    message=f"Emergency route to {destination_id} failed: {exc}",
                    details={"emergency_type": emergency_type.value},
                ) from exc

        dest_types = EMERGENCY_DESTINATION_TYPES.get(
            emergency_type, {"emergency_exit", "exit"},
        )
        result = self._graph.find_nearest(start, dest_types, weight_ctx)
        if result is None:
            raise EmergencyRoutingError(
                message=f"No {emergency_type.value} destination reachable",
                details={"start": str(start)},
            )

        target_node, _dist = result
        try:
            return algo.find_path(
                self._graph, start, target_node.node_id, weight_ctx,
            )
        except Exception as exc:
            raise EmergencyRoutingError(
                message=f"Emergency route failed: {exc}",
                details={"emergency_type": emergency_type.value},
            ) from exc

    def compute_evacuation_routes(
        self,
        zone_node_ids: list[uuid.UUID],
        ctx: WeightContext | None = None,
    ) -> dict[str, PathResult]:
        """Compute evacuation routes for multiple starting positions.

        Raises EmergencyRoutingError if any node has no reachable exit.
        """
        weight_ctx = ctx or WeightContext(emergency_active=True)
        results: dict[str, PathResult] = {}

        algo = self._registry.select(self._graph.node_count)
        exit_types = {"emergency_exit", "exit"}

        for node_id in zone_node_ids:
            nearest = self._graph.find_nearest(
                node_id, exit_types, weight_ctx,
            )
            if nearest is None:
                raise EmergencyRoutingError(
                    message=(
                        f"No exit reachable from node {node_id}"
                    ),
                    details={"node_id": str(node_id)},
                )

            target, _dist = nearest
            route = algo.find_path(
                self._graph, node_id, target.node_id, weight_ctx,
            )
            results[str(node_id)] = route

        return results
