"""Volunteer task routing — assignment optimization and batch routing.

Given volunteer location, task priority, crowd conditions, and current
workload, generates optimal assignment routes with batch optimization.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.features.navigation.exceptions import RouteNotFoundError
from app.features.navigation.graph.graph_manager import NavigationGraph
from app.features.navigation.graph.models import PathResult, WeightContext
from app.features.navigation.pathfinding.algorithm import AlgorithmRegistry


@dataclass(slots=True)
class VolunteerTask:
    """A pending task requiring volunteer assignment."""

    task_id: str
    task_type: str
    priority: int
    location_id: uuid.UUID
    required_capabilities: list[str] = field(default_factory=list)
    max_response_time_seconds: float = 300.0
    estimated_duration_seconds: float = 600.0


@dataclass(slots=True)
class VolunteerState:
    """Current state of a volunteer for assignment optimization."""

    volunteer_id: str
    current_location_id: uuid.UUID
    current_workload: float = 0.0
    completed_tasks_today: int = 0
    capabilities: list[str] = field(default_factory=list)
    energy_level: float = 1.0


@dataclass(slots=True)
class AssignmentResult:
    """Result of volunteer-task assignment optimization."""

    volunteer_id: str
    task_id: str
    route: PathResult
    estimated_arrival_seconds: float = 0.0
    utility_score: float = 0.0
    reasoning: str = ""


class VolunteerRouter:
    """Optimizes volunteer task assignments with batch routing."""

    def __init__(
        self,
        graph: NavigationGraph,
        registry: AlgorithmRegistry,
    ) -> None:
        self._graph = graph
        self._registry = registry

    def compute_assignment(
        self,
        volunteer: VolunteerState,
        task: VolunteerTask,
        ctx: WeightContext | None = None,
    ) -> AssignmentResult | None:
        """Compute optimal route for a volunteer to a task."""
        weight_ctx = ctx or WeightContext()

        algo = self._registry.select(self._graph.node_count)
        try:
            route = algo.find_path(
                self._graph,
                volunteer.current_location_id,
                task.location_id,
                weight_ctx,
            )
        except (RouteNotFoundError, Exception):
            return None

        utility = self._compute_utility(volunteer, task, route)
        reasoning = self._build_reasoning(volunteer, task, route, utility)

        return AssignmentResult(
            volunteer_id=volunteer.volunteer_id,
            task_id=task.task_id,
            route=route,
            estimated_arrival_seconds=route.total_time_seconds,
            utility_score=utility,
            reasoning=reasoning,
        )

    def compute_batch_assignments(
        self,
        volunteers: list[VolunteerState],
        tasks: list[VolunteerTask],
        ctx: WeightContext | None = None,
    ) -> list[AssignmentResult]:
        """Optimize assignments across multiple volunteers and tasks.

        Uses greedy utility maximization: iteratively assign the
        highest-utility volunteer-task pair until all tasks are covered
        or no volunteers remain.
        """
        remaining_tasks = list(tasks)
        assigned_tasks: set[str] = set()
        results: list[AssignmentResult] = []
        available_volunteers = {v.volunteer_id: v for v in volunteers}

        while remaining_tasks and available_volunteers:
            best_assignment: AssignmentResult | None = None
            best_vid: str = ""
            best_tid: str = ""

            for vid, vol in available_volunteers.items():
                for task in remaining_tasks:
                    if task.task_id in assigned_tasks:
                        continue
                    assignment = self.compute_assignment(vol, task, ctx)
                    if assignment and (
                        best_assignment is None
                        or assignment.utility_score > best_assignment.utility_score
                    ):
                        best_assignment = assignment
                        best_vid = vid
                        best_tid = task.task_id

            if best_assignment is None:
                break

            results.append(best_assignment)
            assigned_tasks.add(best_tid)
            remaining_tasks = [t for t in remaining_tasks if t.task_id not in assigned_tasks]
            available_volunteers.pop(best_vid, None)

        return results

    def _compute_utility(
        self,
        volunteer: VolunteerState,
        task: VolunteerTask,
        route: PathResult,
    ) -> float:
        time_factor = max(0, 1.0 - route.total_time_seconds / task.max_response_time_seconds)
        priority_factor = task.priority / 5.0
        workload_factor = 1.0 - volunteer.current_workload
        capability_match = 1.0
        if task.required_capabilities:
            matched = sum(
                1 for c in task.required_capabilities
                if c in volunteer.capabilities
            )
            capability_match = matched / len(task.required_capabilities)

        return (
            time_factor * 0.3
            + priority_factor * 0.3
            + workload_factor * 0.2
            + capability_match * 0.2
        )

    def _build_reasoning(
        self,
        volunteer: VolunteerState,
        task: VolunteerTask,
        route: PathResult,
        utility: float,
    ) -> str:
        return (
            f"Volunteer {volunteer.volunteer_id} -> Task {task.task_id}: "
            f"{route.total_time_seconds:.0f}s travel, "
            f"utility {utility:.2f}"
        )
