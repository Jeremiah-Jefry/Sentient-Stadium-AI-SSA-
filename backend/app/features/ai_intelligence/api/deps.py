"""Dependency injection for AI Intelligence Engine module."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.ai_intelligence.confidence.confidence_engine import (
    ConfidenceEngine,
)
from app.features.ai_intelligence.context.match_context import MatchContextTracker
from app.features.ai_intelligence.context.spatial_reasoning import SpatialReasoner
from app.features.ai_intelligence.engine.pipeline import IntelligencePipeline
from app.features.ai_intelligence.explainability.explainability_engine import (
    ExplainabilityEngine,
)
from app.features.ai_intelligence.knowledge.knowledge_base import KnowledgeBase
from app.features.ai_intelligence.prediction.prediction_engine import (
    PredictionEngine,
)
from app.features.ai_intelligence.repositories.decision_repository import (
    DecisionRepository,
)
from app.features.ai_intelligence.repositories.outcome_repository import (
    OutcomeRepository,
)
from app.features.ai_intelligence.repositories.prediction_repository import (
    PredictionRepository,
)
from app.features.ai_intelligence.repositories.risk_repository import RiskRepository
from app.features.ai_intelligence.risk.risk_engine import RiskEngine
from app.features.ai_intelligence.services.intelligence_service import (
    IntelligenceService,
)
from app.features.ai_intelligence.services.monitoring_service import MonitoringService
from app.features.ai_intelligence.services.observation_service import (
    ObservationService,
)
from app.features.event_streaming.engine.event_bus import EventBus
from app.shared.database import get_db_session

# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------
_event_bus = EventBus()
_risk_engine = RiskEngine()
_prediction_engine = PredictionEngine()
_confidence_engine = ConfidenceEngine()
_explainability_engine = ExplainabilityEngine()
_knowledge_base = KnowledgeBase()
_match_context = MatchContextTracker()
_spatial_reasoner = SpatialReasoner()
_observation_service = ObservationService(
    match_context=_match_context,
    spatial_reasoner=_spatial_reasoner,
)
_monitoring_service = MonitoringService()


def get_event_bus() -> EventBus:
    return _event_bus


def get_risk_engine() -> RiskEngine:
    return _risk_engine


def get_prediction_engine() -> PredictionEngine:
    return _prediction_engine


def get_confidence_engine() -> ConfidenceEngine:
    return _confidence_engine


def get_explainability_engine() -> ExplainabilityEngine:
    return _explainability_engine


def get_knowledge_base() -> KnowledgeBase:
    return _knowledge_base


def get_match_context() -> MatchContextTracker:
    return _match_context


def get_spatial_reasoner() -> SpatialReasoner:
    return _spatial_reasoner


def get_observation_service() -> ObservationService:
    return _observation_service


def get_monitoring_service() -> MonitoringService:
    return _monitoring_service


# ---------------------------------------------------------------------------
# Per-request repositories (require database session)
# ---------------------------------------------------------------------------

async def get_prediction_repo(
    session: AsyncSession = Depends(get_db_session),
) -> PredictionRepository:
    return PredictionRepository(session)


async def get_risk_repo(
    session: AsyncSession = Depends(get_db_session),
) -> RiskRepository:
    return RiskRepository(session)


async def get_decision_repo(
    session: AsyncSession = Depends(get_db_session),
) -> DecisionRepository:
    return DecisionRepository(session)


async def get_outcome_repo(
    session: AsyncSession = Depends(get_db_session),
) -> OutcomeRepository:
    return OutcomeRepository(session)


# ---------------------------------------------------------------------------
# Composed service singletons
# ---------------------------------------------------------------------------

def _build_pipeline() -> IntelligencePipeline:
    return IntelligencePipeline(
        risk_engine=_risk_engine,
        prediction_engine=_prediction_engine,
        confidence_engine=_confidence_engine,
        explainability_engine=_explainability_engine,
        knowledge_base=_knowledge_base,
        match_context=_match_context,
        spatial_reasoner=_spatial_reasoner,
    )


_pipeline = _build_pipeline()

# IntelligenceService requires per-request repos; expose a factory.
def _make_intelligence_service(
    prediction_repo: PredictionRepository,
    risk_repo: RiskRepository,
    decision_repo: DecisionRepository,
    outcome_repo: OutcomeRepository,
) -> IntelligenceService:
    return IntelligenceService(
        pipeline=_pipeline,
        event_bus=_event_bus,
        prediction_repo=prediction_repo,
        risk_repo=risk_repo,
        decision_repo=decision_repo,
        outcome_repo=outcome_repo,
    )


async def get_intelligence_service(
    prediction_repo: PredictionRepository = Depends(get_prediction_repo),
    risk_repo: RiskRepository = Depends(get_risk_repo),
    decision_repo: DecisionRepository = Depends(get_decision_repo),
    outcome_repo: OutcomeRepository = Depends(get_outcome_repo),
) -> IntelligenceService:
    return _make_intelligence_service(
        prediction_repo, risk_repo, decision_repo, outcome_repo,
    )
