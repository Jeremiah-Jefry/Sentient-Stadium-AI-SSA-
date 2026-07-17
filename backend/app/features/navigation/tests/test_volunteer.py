"""Tests for volunteer task routing and batch assignment."""

from __future__ import annotations

import uuid

from app.features.navigation.graph.graph_manager import NavigationGraph
from app.features.navigation.graph.models import NavEdge, NavNode
from app.features.navigation.pathfinding.algorithm import AlgorithmRegistry
from app.features.navigation.volunteer.assignment import (
    VolunteerRouter,
    VolunteerState,
    VolunteerTask,
)


def _uid() -> uuid.UUID:
    return uuid.uuid4()


def _build_graph() -> tuple[NavigationGraph, list[uuid.UUID]]:
    graph = NavigationGraph()
    nodes = []
    for i in range(5):
        nid = _uid()
        nodes.append(nid)
        graph.add_node(NavNode(
            node_id=nid, name=f"Node {i}",
            entity_type="corridor",
            lat=0.0, lon=float(i) * 0.0001,
        ))
    for i in range(4):
        graph.add_edge(NavEdge(
            from_id=nodes[i], to_id=nodes[i + 1],
            edge_type="walking", base_weight=1.0,
            distance_meters=100.0,
        ))
    return graph, nodes


class TestVolunteerRouter:
    def test_compute_assignment(self) -> None:
        graph, nodes = _build_graph()
        registry = AlgorithmRegistry()
        router = VolunteerRouter(graph, registry)

        volunteer = VolunteerState(
            volunteer_id="v1",
            current_location_id=nodes[0],
        )
        task = VolunteerTask(
            task_id="t1",
            task_type="info_desk",
            priority=3,
            location_id=nodes[4],
        )
        result = router.compute_assignment(volunteer, task)
        assert result is not None
        assert result.volunteer_id == "v1"
        assert result.task_id == "t1"
        assert result.utility_score > 0

    def test_compute_batch_assignments(self) -> None:
        graph, nodes = _build_graph()
        registry = AlgorithmRegistry()
        router = VolunteerRouter(graph, registry)

        volunteers = [
            VolunteerState(volunteer_id="v1", current_location_id=nodes[0]),
            VolunteerState(volunteer_id="v2", current_location_id=nodes[2]),
        ]
        tasks = [
            VolunteerTask(task_id="t1", task_type="info", priority=3, location_id=nodes[4]),
            VolunteerTask(task_id="t2", task_type="medical", priority=5, location_id=nodes[3]),
        ]
        results = router.compute_batch_assignments(volunteers, tasks)
        assert len(results) == 2
        assigned_vids = {r.volunteer_id for r in results}
        assert len(assigned_vids) == 2

    def test_assignment_result_has_reasoning(self) -> None:
        graph, nodes = _build_graph()
        registry = AlgorithmRegistry()
        router = VolunteerRouter(graph, registry)

        volunteer = VolunteerState(
            volunteer_id="v1", current_location_id=nodes[0],
        )
        task = VolunteerTask(
            task_id="t1", task_type="info", priority=3, location_id=nodes[4],
        )
        result = router.compute_assignment(volunteer, task)
        assert len(result.reasoning) > 0
