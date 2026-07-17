"""Tests for the 8-stage pipeline context and orchestration."""
from __future__ import annotations

import pytest

from app.features.ai_intelligence.context.match_context import MatchContextTracker
from app.features.ai_intelligence.engine.context import (
    IntelligenceContext,
    RiskBundle,
    SimulatedIntervention,
    SituationAssessment,
)
from app.features.ai_intelligence.engine.stage_1_assessment import Stage1Assessment
from app.features.ai_intelligence.engine.stage_5_simulation import Stage5Simulation
from app.features.ai_intelligence.engine.stage_6_decision import Stage6Decision


class TestIntelligenceContext:
    """Tests for IntelligenceContext dataclass."""

    def test_context_initial_state(self) -> None:
        """New context should have all stage outputs as None."""
        ctx = IntelligenceContext(
            triggering_event="test_event",
            venue_id="venue-1",
        )
        assert ctx.situation is None
        assert ctx.behaviour is None
        assert ctx.predictions is None
        assert ctx.risk is None
        assert ctx.interventions == []
        assert ctx.decision is None
        assert ctx.intelligence is None
        assert ctx.published is False

    def test_context_stage_timings(self) -> None:
        """Context should track per-stage timing."""
        ctx = IntelligenceContext(
            triggering_event="test_event",
            venue_id="venue-1",
        )
        ctx.stage_timings["assessment"] = 12.5
        ctx.stage_timings["risk"] = 8.3
        assert ctx.stage_timings["assessment"] == 12.5
        assert ctx.stage_timings["risk"] == 8.3

    def test_context_error_accumulation(self) -> None:
        """Context should accumulate errors without crashing."""
        ctx = IntelligenceContext(
            triggering_event="test_event",
            venue_id="venue-1",
        )
        ctx.record_error("stage_1", "sensor timeout")
        ctx.record_error("stage_3", "model failed")
        assert len(ctx.errors) == 2
        assert "sensor timeout" in ctx.errors[0]
        assert "model failed" in ctx.errors[1]

    def test_has_critical_failure(self) -> None:
        """Should detect CRITICAL errors."""
        ctx = IntelligenceContext(
            triggering_event="test",
            venue_id="v-1",
        )
        assert ctx.has_critical_failure() is False
        ctx.record_error("risk", "CRITICAL: pipeline abort")
        assert ctx.has_critical_failure() is True

    def test_stage_failed(self) -> None:
        """Should detect errors for specific stages."""
        ctx = IntelligenceContext(
            triggering_event="test",
            venue_id="v-1",
        )
        ctx.record_error("prediction", "timeout")
        assert ctx.stage_failed("prediction") is True
        assert ctx.stage_failed("risk") is False

    def test_summary(self) -> None:
        """Summary should return serialisable dict."""
        ctx = IntelligenceContext(
            triggering_event="test",
            venue_id="v-1",
            zone_id="z-1",
        )
        summary = ctx.summary()
        assert summary["venue_id"] == "v-1"
        assert summary["zone_id"] == "z-1"
        assert summary["published"] is False
        assert summary["risk_level"] is None
        assert summary["decision"] is None
        assert summary["error_count"] == 0


class TestStage1Assessment:
    """Tests for Stage 1 — Realtime Situation Assessment."""

    @pytest.mark.asyncio
    async def test_extracts_density(self) -> None:
        """Should extract density from event payload."""
        match_ctx = MatchContextTracker()
        stage = Stage1Assessment(match_ctx)

        class FakeEvent:
            payload = {
                "density": 500,
                "capacity": 1000,
                "flow_rate": 75.0,
                "occupancy_percent": 50.0,
                "active_sensors": 10,
            }

        ctx = IntelligenceContext(
            triggering_event=FakeEvent(),
            venue_id="v-1",
        )
        await stage.execute(ctx)
        assert ctx.situation is not None
        assert ctx.situation.current_density == 500 / 1000

    @pytest.mark.asyncio
    async def test_includes_match_modifiers(self) -> None:
        """Should include match context modifiers."""
        match_ctx = MatchContextTracker()
        stage = Stage1Assessment(match_ctx)

        class FakeEvent:
            payload = {"density": 0, "capacity": 1}

        ctx = IntelligenceContext(
            triggering_event=FakeEvent(),
            venue_id="v-1",
        )
        await stage.execute(ctx)
        assert ctx.situation is not None
        assert isinstance(ctx.situation.behavior_modifiers, dict)
        assert "movement_intensity" in ctx.situation.behavior_modifiers

    @pytest.mark.asyncio
    async def test_handles_missing_payload(self) -> None:
        """Should handle event with no payload."""
        match_ctx = MatchContextTracker()
        stage = Stage1Assessment(match_ctx)

        class FakeEvent:
            payload = None

        ctx = IntelligenceContext(
            triggering_event=FakeEvent(),
            venue_id="v-1",
        )
        await stage.execute(ctx)
        assert ctx.situation is not None
        assert ctx.situation.current_density == 0.0

    @pytest.mark.asyncio
    async def test_occupancy_clamped(self) -> None:
        """Occupancy should be clamped to [0, 100]."""
        match_ctx = MatchContextTracker()
        stage = Stage1Assessment(match_ctx)

        class FakeEvent:
            payload = {"occupancy_percent": 150.0}

        ctx = IntelligenceContext(
            triggering_event=FakeEvent(),
            venue_id="v-1",
        )
        await stage.execute(ctx)
        assert ctx.situation.occupancy_percent == 100.0


class TestStage5Simulation:
    """Tests for Stage 5 — Intervention Simulation."""

    @pytest.mark.asyncio
    async def test_includes_do_nothing(self) -> None:
        """Simulation should always include DO_NOTHING baseline."""
        stage = Stage5Simulation()
        ctx = IntelligenceContext(
            triggering_event="test",
            venue_id="v-1",
            risk=RiskBundle(
                overall_risk_level="yellow",
                overall_risk_score=0.35,
                domain_risks={},
                risk_factors={},
                confidence=0.8,
            ),
            situation=SituationAssessment(
                venue_id="v-1",
                zone_id=None,
                current_density=0.5,
                flow_rate=50.0,
                occupancy_percent=50.0,
                active_sensors=10,
                recent_events=[],
                match_phase="first_half",
                behavior_modifiers={},
                timestamp=0.0,
            ),
        )
        await stage.execute(ctx)
        types = [i.intervention_type for i in ctx.interventions]
        assert "do_nothing" in types

    @pytest.mark.asyncio
    async def test_candidates_limited_by_risk(self) -> None:
        """Number of candidates should depend on risk level."""
        stage = Stage5Simulation()

        green_ctx = IntelligenceContext(
            triggering_event="test",
            venue_id="v-1",
            risk=RiskBundle(
                overall_risk_level="green",
                overall_risk_score=0.1,
                domain_risks={},
                risk_factors={},
                confidence=0.9,
            ),
            situation=SituationAssessment(
                venue_id="v-1", zone_id=None, current_density=0.1,
                flow_rate=50.0, occupancy_percent=10.0, active_sensors=10,
                recent_events=[], match_phase="first_half",
                behavior_modifiers={}, timestamp=0.0,
            ),
        )
        critical_ctx = IntelligenceContext(
            triggering_event="test",
            venue_id="v-1",
            risk=RiskBundle(
                overall_risk_level="critical",
                overall_risk_score=0.95,
                domain_risks={},
                risk_factors={},
                confidence=0.5,
            ),
            situation=SituationAssessment(
                venue_id="v-1", zone_id=None, current_density=0.95,
                flow_rate=50.0, occupancy_percent=95.0, active_sensors=10,
                recent_events=[], match_phase="second_half",
                behavior_modifiers={}, timestamp=0.0,
            ),
        )

        await stage.execute(green_ctx)
        await stage.execute(critical_ctx)
        assert len(critical_ctx.interventions) > len(green_ctx.interventions)

    @pytest.mark.asyncio
    async def test_no_risk_no_interventions(self) -> None:
        """Without risk data, no interventions should be generated."""
        stage = Stage5Simulation()
        ctx = IntelligenceContext(
            triggering_event="test",
            venue_id="v-1",
        )
        await stage.execute(ctx)
        assert ctx.interventions == []


class TestStage6Decision:
    """Tests for Stage 6 — Decision Selection."""

    @pytest.mark.asyncio
    async def test_selects_highest_utility(self) -> None:
        """Decision should select candidate with highest utility."""
        stage = Stage6Decision()

        ctx = IntelligenceContext(
            triggering_event="test",
            venue_id="v-1",
            risk=RiskBundle(
                overall_risk_level="red",
                overall_risk_score=0.8,
                domain_risks={},
                risk_factors={},
                confidence=0.9,
            ),
            interventions=[
                SimulatedIntervention(
                    intervention_type="reverse_flow",
                    strategy_params={},
                    simulated_risk_reduction=0.10,
                    simulated_confidence=0.40,
                    risk_before="red", risk_after="red",
                    evaluation_factors=[], side_effects=["a", "b"], resource_cost=0.80,
                ),
                SimulatedIntervention(
                    intervention_type="deploy_medical",
                    strategy_params={"team_count": 2},
                    simulated_risk_reduction=0.38,
                    simulated_confidence=0.80,
                    risk_before="red", risk_after="yellow",
                    evaluation_factors=[], side_effects=["reduced coverage"],
                    resource_cost=0.45,
                ),
            ],
        )
        await stage.execute(ctx)
        assert ctx.decision is not None
        assert ctx.decision.intervention_type == "deploy_medical"

    @pytest.mark.asyncio
    async def test_no_candidates_defaults_to_do_nothing(self) -> None:
        """Without candidates, should default to do_nothing."""
        stage = Stage6Decision()
        ctx = IntelligenceContext(
            triggering_event="test",
            venue_id="v-1",
        )
        await stage.execute(ctx)
        assert ctx.decision is not None
        assert ctx.decision.intervention_type == "do_nothing"

    @pytest.mark.asyncio
    async def test_decision_has_reasoning(self) -> None:
        """Decision should include reasoning."""
        stage = Stage6Decision()
        ctx = IntelligenceContext(
            triggering_event="test",
            venue_id="v-1",
            risk=RiskBundle(
                overall_risk_level="yellow",
                overall_risk_score=0.35,
                domain_risks={}, risk_factors={}, confidence=0.8,
            ),
            interventions=[
                SimulatedIntervention(
                    intervention_type="redirect_volunteers",
                    strategy_params={},
                    simulated_risk_reduction=0.22,
                    simulated_confidence=0.75,
                    risk_before="yellow", risk_after="green",
                    evaluation_factors=[], side_effects=[], resource_cost=0.20,
                ),
            ],
        )
        await stage.execute(ctx)
        assert "utility_score" in ctx.decision.reasoning
