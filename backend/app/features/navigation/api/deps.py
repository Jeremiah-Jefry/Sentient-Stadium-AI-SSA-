"""Navigation API dependencies — singleton graph and router wiring."""

from __future__ import annotations

import logging

from app.features.navigation.consumers.navigation_consumer import NavigationConsumer
from app.features.navigation.graph.dynamic_weights import DynamicWeightEngine
from app.features.navigation.graph.graph_manager import NavigationGraph
from app.features.navigation.pathfinding.algorithm import AlgorithmRegistry
from app.features.navigation.routing.router import NavigationRouter

logger = logging.getLogger(__name__)

_graph: NavigationGraph | None = None
_weight_engine: DynamicWeightEngine | None = None
_registry: AlgorithmRegistry | None = None
_router: NavigationRouter | None = None
_consumer: NavigationConsumer | None = None


def get_navigation_graph() -> NavigationGraph:
    global _graph
    if _graph is None:
        _graph = NavigationGraph()
    return _graph


def get_weight_engine() -> DynamicWeightEngine:
    global _weight_engine
    if _weight_engine is None:
        _weight_engine = DynamicWeightEngine()
    return _weight_engine


def get_algorithm_registry() -> AlgorithmRegistry:
    global _registry
    if _registry is None:
        _registry = AlgorithmRegistry()
    return _registry


def get_navigation_router() -> NavigationRouter:
    global _router
    if _router is None:
        _router = NavigationRouter(
            graph=get_navigation_graph(),
            weight_engine=get_weight_engine(),
            registry=get_algorithm_registry(),
        )
    return _router


def get_navigation_consumer() -> NavigationConsumer:
    global _consumer
    if _consumer is None:
        _consumer = NavigationConsumer(get_weight_engine())
    return _consumer
