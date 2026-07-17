"""Tests for ReasoningEngine — 8-stage cognitive pipeline, observe/think/plan stages."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.features.orchestration.knowledge.knowledge_retrieval import KnowledgeRetrieval
from app.features.orchestration.memory.memory_manager import MemoryManager
from app.features.orchestration.models.enums import (
    IntentType,
    ReasoningStage,
    RequestType,
    UserRole,
)
from app.features.orchestration.reasoning.reasoning_engine import ReasoningEngine


class _FakeRequest:
    def __init__(
        self,
        query: str = "How do I manage crowd flow?",
        request_type: RequestType = RequestType.VOLUNTEER_REQUEST,
        intent: IntentType | None = IntentType.CROWD_MANAGEMENT,
        priority: int = 5,
        venue_id: UUID | None = None,
        zone_id: UUID | None = None,
        user_role: UserRole = UserRole.VOLUNTEER,
        constraints: list[str] | None = None,
    ) -> None:
        self.request_id = uuid4()
        self.request_type = request_type
        self.intent = intent
        self.query = query
        self.priority = priority
        self.venue_id = venue_id
        self.zone_id = zone_id
        self.user_role = user_role
        self.constraints = constraints or []


@pytest.fixture
def engine() -> ReasoningEngine:
    return ReasoningEngine(
        knowledge_retrieval=KnowledgeRetrieval(),
        memory_manager=MemoryManager(),
    )


class TestReasoningEngine:

    @pytest.mark.asyncio
    async def test_reasoning_pipeline_stages(self, engine: ReasoningEngine) -> None:
        request = _FakeRequest()
        context = {
            "sensor_data": {"crowd_density": 0.72},
            "crowd_data": {"density_percent": 72},
        }
        obs = await engine.observe(request, context)
        think = await engine.think(obs, context)
        plan = await engine.plan(think, context)
        execute = await engine.execute_plan(plan, context)
        critique = await engine.critique({}, plan)
        improve = await engine.improve(critique)
        validate = await engine.validate(improve, context)
        stages = [obs, think, plan, execute, critique, improve, validate]
        assert len(stages) == 7
        for stage in stages:
            assert 0.0 <= stage.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_observe_stage(self, engine: ReasoningEngine) -> None:
        request = _FakeRequest(query="Where is the nearest exit?")
        context = {"sensor_data": {"temp": 30.0}}
        obs = await engine.observe(request, context)
        assert obs.stage == ReasoningStage.OBSERVE
        assert obs.confidence > 0.0
        facts = obs.output["facts"]
        assert facts["query"] == "Where is the nearest exit?"
        assert facts["request_type"] == RequestType.VOLUNTEER_REQUEST.value
        assert facts["intent"] == IntentType.CROWD_MANAGEMENT.value

    @pytest.mark.asyncio
    async def test_think_stage(self, engine: ReasoningEngine) -> None:
        request = _FakeRequest()
        context = {"crowd_data": {"density_percent": 90}}
        obs = await engine.observe(request, context)
        think = await engine.think(obs, context)
        assert think.stage == ReasoningStage.THINK
        assert think.confidence > 0.0
        patterns = think.output["patterns"]
        anomalies = think.output["anomalies"]
        assert isinstance(patterns, list)
        assert isinstance(anomalies, list)

    @pytest.mark.asyncio
    async def test_think_detects_high_density(self, engine: ReasoningEngine) -> None:
        request = _FakeRequest(intent=IntentType.CROWD_MANAGEMENT)
        context = {"crowd_data": {"density_percent": 92}}
        obs = await engine.observe(request, context)
        think = await engine.think(obs, context)
        anomaly_types = [a["type"] for a in think.output["anomalies"]]
        assert "high_density" in anomaly_types

    @pytest.mark.asyncio
    async def test_think_detects_emergency_urgency(self, engine: ReasoningEngine) -> None:
        request = _FakeRequest(intent=IntentType.EMERGENCY_RESPONSE, priority=9)
        context = {}
        obs = await engine.observe(request, context)
        think = await engine.think(obs, context)
        pattern_types = [p["type"] for p in think.output["patterns"]]
        assert "urgency" in pattern_types

    @pytest.mark.asyncio
    async def test_plan_stage(self, engine: ReasoningEngine) -> None:
        request = _FakeRequest()
        context = {}
        obs = await engine.observe(request, context)
        think = await engine.think(obs, context)
        plan = await engine.plan(think, context)
        assert plan.stage == ReasoningStage.PLAN
        assert plan.confidence > 0.0
        assert "strategies" in plan.output
        assert "primary_strategy" in plan.output
        assert plan.output["strategy_count"] >= 1

    @pytest.mark.asyncio
    async def test_plan_critical_emergency(self, engine: ReasoningEngine) -> None:
        request = _FakeRequest(intent=IntentType.EMERGENCY_RESPONSE, priority=10)
        context = {}
        obs = await engine.observe(request, context)
        think = await engine.think(obs, context)
        plan = await engine.plan(think, context)
        primary = plan.output["primary_strategy"]
        assert primary["priority"] == "critical"
        assert "activate_emergency_protocol" in primary["actions"]

    @pytest.mark.asyncio
    async def test_critique_stage(self, engine: ReasoningEngine) -> None:
        request = _FakeRequest()
        context = {}
        obs = await engine.observe(request, context)
        think = await engine.think(obs, context)
        plan = await engine.plan(think, context)
        critique = await engine.critique({}, plan)
        assert critique.stage == ReasoningStage.CRITIQUE
        assert "gaps" in critique.output
        assert "risks" in critique.output

    @pytest.mark.asyncio
    async def test_improve_stage(self, engine: ReasoningEngine) -> None:
        request = _FakeRequest()
        context = {}
        obs = await engine.observe(request, context)
        think = await engine.think(obs, context)
        plan = await engine.plan(think, context)
        critique = await engine.critique({}, plan)
        improve = await engine.improve(critique)
        assert improve.stage == ReasoningStage.IMPROVE
        assert "suggestions" in improve.output

    @pytest.mark.asyncio
    async def test_validate_stage(self, engine: ReasoningEngine) -> None:
        request = _FakeRequest()
        context = {"accessibility_needs": ["wheelchair"]}
        obs = await engine.observe(request, context)
        think = await engine.think(obs, context)
        plan = await engine.plan(think, context)
        critique = await engine.critique({}, plan)
        improve = await engine.improve(critique)
        validate = await engine.validate(improve, context)
        assert validate.stage == ReasoningStage.VALIDATE
        assert validate.output["is_valid"] is True

    @pytest.mark.asyncio
    async def test_explain_stage(self, engine: ReasoningEngine) -> None:
        request = _FakeRequest()
        context = {}
        obs = await engine.observe(request, context)
        think = await engine.think(obs, context)
        plan = await engine.plan(think, context)
        execute = await engine.execute_plan(plan, context)
        critique = await engine.critique({}, plan)
        improve = await engine.improve(critique)
        validate = await engine.validate(improve, context)
        stages = [obs, think, plan, execute, critique, improve, validate]
        explain = await engine.explain(stages, uuid4(), request.request_id)
        assert explain.stage == ReasoningStage.EXPLAIN
        assert "pipeline" in explain.output
        assert explain.confidence > 0.0

    @pytest.mark.asyncio
    async def test_reasoning_with_agent_outputs(self, engine: ReasoningEngine) -> None:
        request = _FakeRequest()
        context = {}
        agent_outputs = {
            uuid4(): {"action": "crowd_management", "status": "completed", "confidence": 0.88},
        }
        obs = await engine.observe(request, context)
        think = await engine.think(obs, context)
        plan = await engine.plan(think, context)
        critique = await engine.critique(agent_outputs, plan)
        assert critique.confidence > 0.0
        assert len(critique.output.get("executed", [])) >= 1
