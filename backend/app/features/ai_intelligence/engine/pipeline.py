"""8-stage reasoning pipeline orchestrator for the intelligence engine."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from app.features.ai_intelligence.confidence.confidence_engine import ConfidenceEngine
from app.features.ai_intelligence.context.match_context import MatchContextTracker
from app.features.ai_intelligence.context.spatial_reasoning import SpatialReasoner
from app.features.ai_intelligence.engine.context import IntelligenceContext
from app.features.ai_intelligence.engine.stage_1_assessment import Stage1Assessment
from app.features.ai_intelligence.engine.stage_2_behaviour import Stage2Behaviour
from app.features.ai_intelligence.engine.stage_3_prediction import Stage3Prediction
from app.features.ai_intelligence.engine.stage_4_risk import Stage4Risk
from app.features.ai_intelligence.engine.stage_5_simulation import Stage5Simulation
from app.features.ai_intelligence.engine.stage_6_decision import Stage6Decision
from app.features.ai_intelligence.engine.stage_7_explain import Stage7Explain
from app.features.ai_intelligence.engine.stage_8_publish import Stage8Publish
from app.features.ai_intelligence.explainability.explainability_engine import ExplainabilityEngine
from app.features.ai_intelligence.knowledge.knowledge_base import KnowledgeBase
from app.features.ai_intelligence.prediction.prediction_engine import PredictionEngine
from app.features.ai_intelligence.risk.risk_engine import RiskEngine

logger = logging.getLogger(__name__)

CRITICAL_STOP_STAGES: frozenset[str] = frozenset({"risk"})
MAX_STAGE_WARNINGS: int = 3


class IntelligencePipeline:
    """8-stage reasoning pipeline.

    Stages:
        1. assessment  — Realtime Situation Assessment
        2. behaviour   — Crowd Behaviour Analysis
        3. prediction  — Short-Term Prediction
        4. risk        — Risk Scoring
        5. simulation  — Intervention Simulation
        6. decision    — Decision Selection
        7. explain     — Explainable AI
        8. publish     — Publish Recommendation
    """

    def __init__(
        self,
        risk_engine: RiskEngine,
        prediction_engine: PredictionEngine,
        confidence_engine: ConfidenceEngine,
        explainability_engine: ExplainabilityEngine,
        knowledge_base: KnowledgeBase,
        match_context: MatchContextTracker,
        spatial_reasoner: SpatialReasoner,
    ) -> None:
        self._stage1 = Stage1Assessment(match_context)
        self._stage2 = Stage2Behaviour(spatial_reasoner)
        self._stage3 = Stage3Prediction(prediction_engine)
        self._stage4 = Stage4Risk(risk_engine)
        self._stage5 = Stage5Simulation()
        self._stage6 = Stage6Decision()
        self._stage7 = Stage7Explain(explainability_engine, knowledge_base)
        self._stage8 = Stage8Publish()

        self._stages: list[tuple[str, Callable[[IntelligenceContext], Awaitable[None]]]] = [
            ("assessment", self._stage1.execute),
            ("behaviour", self._stage2.execute),
            ("prediction", self._stage3.execute),
            ("risk", self._stage4.execute),
            ("simulation", self._stage5.execute),
            ("decision", self._stage6.execute),
            ("explain", self._stage7.execute),
            ("publish", self._stage8.execute),
        ]
        logger.info(
            "IntelligencePipeline initialised with %d stages", len(self._stages),
        )

    async def process(self, ctx: IntelligenceContext) -> IntelligenceContext:
        """Run the full 8-stage pipeline, timing each stage and accumulating errors."""
        ctx.pipeline_start_ms = time.monotonic() * 1000
        logger.info(
            "Pipeline started: venue=%s zone=%s",
            ctx.venue_id, ctx.zone_id,
        )

        for stage_name, stage_fn in self._stages:
            stage_start = time.monotonic()
            try:
                await stage_fn(ctx)
            except Exception as exc:
                elapsed = (time.monotonic() - stage_start) * 1000
                ctx.stage_timings[stage_name] = round(elapsed, 2)
                error_msg = f"[{stage_name}] {type(exc).__name__}: {exc}"
                ctx.record_error(stage_name, str(exc))
                logger.exception(
                    "Pipeline stage '%s' failed after %.1fms", stage_name, elapsed,
                )
                if stage_name in CRITICAL_STOP_STAGES:
                    logger.critical(
                        "Critical stage '%s' failed — aborting pipeline", stage_name,
                    )
                    break
            else:
                elapsed = (time.monotonic() - stage_start) * 1000
                ctx.stage_timings[stage_name] = round(elapsed, 2)

        total_ms = (time.monotonic() * 1000) - ctx.pipeline_start_ms
        logger.info(
            "Pipeline completed in %.1fms: errors=%d published=%s",
            total_ms, len(ctx.errors), ctx.published,
        )
        return ctx
