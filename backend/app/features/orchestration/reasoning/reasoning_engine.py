from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from app.features.orchestration.knowledge.knowledge_retrieval import KnowledgeRetrieval
from app.features.orchestration.memory.memory_manager import MemoryManager
from app.features.orchestration.reasoning.reasoning_types import (
    ReasoningChain,
    ReasoningStageResult,
)
from app.shared.result import Failure, Result, Success

logging = logging.getLogger(__name__)

_STAGES = ["observe", "think", "plan", "execute", "critique", "improve", "validate", "explain"]


class ReasoningEngine:

    def __init__(self, knowledge_retrieval: KnowledgeRetrieval, memory_manager: MemoryManager) -> None:
        self._knowledge = knowledge_retrieval
        self._memory = memory_manager

    async def reason(self, request: Any, context: dict[str, Any], agent_outputs: dict[UUID, dict[str, Any]] | None = None) -> Result[ReasoningChain]:
        start = time.monotonic()
        chain_id = UUID(int=0)
        try:
            stages = await self._pipeline(request, context, agent_outputs, chain_id)
            conf = sum(s.confidence for s in stages) / len(stages) if stages else 0.0
            chain = ReasoningChain(
                chain_id=chain_id, request_id=request.request_id, stages=stages,
                overall_confidence=conf, total_duration_ms=sum(s.duration_ms for s in stages),
                conclusion=self._conclusion(stages), summary=self._summary(stages, conf),
            )
            logging.info("Reasoning chain done in %.1fms confidence=%.3f", (time.monotonic() - start) * 1000, conf)
            return Success(value=chain)
        except Exception as exc:
            logging.exception("Reasoning pipeline failed")
            return Failure(error_code="REASONING_PIPELINE_FAILED", message=str(exc), details={"request_id": str(request.request_id)})

    async def _pipeline(self, request: Any, context: dict[str, Any], agent_outputs: dict[UUID, dict[str, Any]] | None, chain_id: UUID) -> list[ReasoningStageResult]:
        o = await self.observe(request, context)
        t = await self.think(o, context)
        p = await self.plan(t, context)
        e = await self.execute_plan(p, context)
        c = await self.critique(agent_outputs or {}, p)
        i = await self.improve(c)
        v = await self.validate(i, context)
        stages = [o, t, p, e, c, i, v]
        stages.append(await self.explain(stages, chain_id, request.request_id))
        return stages

    async def observe(self, request: Any, context: dict[str, Any]) -> ReasoningStageResult:
        s = time.monotonic()
        facts = {"query": request.query, "request_type": request.request_type.value, "intent": request.intent.value if request.intent else None, "priority": request.priority, "venue_id": str(request.venue_id) if request.venue_id else None, "zone_id": str(request.zone_id) if request.zone_id else None, "user_role": request.user_role.value, "constraints": request.constraints}
        ctx = dict(context)
        kres = await self._knowledge.retrieve(query=request.query, limit=5)
        kitems = kres.value if isinstance(kres, Success) else []
        conf = 0.5 + (0.2 if kitems else 0) + (0.1 if ctx.get("sensor_data") else 0) + (0.1 if ctx.get("crowd_data") else 0) + (0.1 if facts["intent"] else 0)
        return ReasoningStageResult(stage="observe", output={"facts": facts, "context": ctx, "knowledge_items": kitems}, confidence=min(conf, 1.0), duration_ms=(time.monotonic() - s) * 1000, evidence=[{"type": "facts", "data": facts}])

    async def think(self, obs: ReasoningStageResult, context: dict[str, Any]) -> ReasoningStageResult:
        s = time.monotonic()
        facts, kitems = obs.output.get("facts", {}), obs.output.get("knowledge_items", [])
        intent, priority = facts.get("intent"), facts.get("priority", 5)
        patterns, anomalies, rels = [], [], []
        if intent == "emergency_response":
            patterns.append({"type": "urgency", "severity": "critical" if priority >= 8 else "high"})
        if intent == "crowd_management" and context.get("crowd_data", {}).get("density_percent", 0) > 85:
            anomalies.append({"type": "high_density", "severity": "high"})
        if intent == "accessibility" and not context.get("accessibility_needs"):
            anomalies.append({"type": "missing_data", "severity": "medium"})
        for item in kitems:
            rels.append({"type": "knowledge_match", "category": item.get("category", ""), "relevance": item.get("relevance_score", 0.0)})
        conf = max(0.1, min(obs.confidence - 0.1 * len(anomalies) + 0.05 * len(patterns), 1.0))
        return ReasoningStageResult(stage="think", output={"patterns": patterns, "anomalies": anomalies, "relationships": rels}, confidence=conf, duration_ms=(time.monotonic() - s) * 1000, evidence=[{"type": "patterns", "data": patterns}])

    async def plan(self, analysis: ReasoningStageResult, context: dict[str, Any]) -> ReasoningStageResult:
        s = time.monotonic()
        pats, anoms = analysis.output.get("patterns", []), analysis.output.get("anomalies", [])
        crit, high = any(x.get("severity") == "critical" for x in pats), any(x.get("severity") == "high" for x in anoms)
        if crit:
            primary = {"name": "emergency_immediate_response", "priority": "critical", "actions": ["activate_emergency_protocol", "notify_emergency_services", "clear_affected_area"]}
            strats = [primary, {"name": "emergency_escalation", "priority": "high", "actions": ["escalate_to_incident_commander"]}]
        elif high:
            primary = {"name": "active_monitoring", "priority": "high", "actions": ["increase_monitoring", "deploy_resources"]}
            strats = [primary, {"name": "preventive_redirect", "priority": "medium", "actions": ["redirect_crowd_flow"]}]
        else:
            primary = {"name": "standard_response", "priority": "normal", "actions": ["provide_information", "monitor_situation"]}
            strats = [primary]
        conf = max(0.1, min(analysis.confidence + (0.1 if primary else 0) + (0.05 if len(strats) > 1 else 0), 1.0))
        return ReasoningStageResult(stage="plan", output={"strategies": strats, "primary_strategy": primary, "strategy_count": len(strats)}, confidence=conf, duration_ms=(time.monotonic() - s) * 1000, evidence=[{"type": "strategies", "data": strats}])

    async def execute_plan(self, plan: ReasoningStageResult, context: dict[str, Any]) -> ReasoningStageResult:
        s = time.monotonic()
        primary = plan.output.get("primary_strategy")
        return ReasoningStageResult(stage="execute", output={"delegated": True, "reason": "Handled by PipelineExecutor", "strategy": primary.get("name") if primary else None}, confidence=plan.confidence, duration_ms=(time.monotonic() - s) * 1000, evidence=[{"type": "delegation", "data": {"executor": "PipelineExecutor"}}])

    async def critique(self, ex_result: dict[UUID, dict[str, Any]], plan: ReasoningStageResult) -> ReasoningStageResult:
        s = time.monotonic()
        planned = plan.output.get("primary_strategy", {}).get("actions", [])
        execd, failed, gaps, risks = [], [], [], []
        for _aid, out in ex_result.items():
            a, st = out.get("action", ""), out.get("status", "unknown")
            if a:
                (execd if st == "completed" else failed).append(a)
        for a in planned:
            if a not in execd:
                gaps.append({"type": "unfulfilled", "action": a})
        if failed:
            risks.append({"type": "execution_failure", "actions": failed})
        if not ex_result:
            risks.append({"type": "no_data"})
        gr = len(gaps) / max(len(planned), 1)
        fr = len(failed) / max(len(execd) + len(failed), 1)
        conf = max(0.1, min(plan.confidence - gr * 0.3 - fr * 0.4, 1.0))
        return ReasoningStageResult(stage="critique", output={"executed": execd, "failed": failed, "gaps": gaps, "risks": risks, "gap_ratio": gr, "failure_ratio": fr}, confidence=conf, duration_ms=(time.monotonic() - s) * 1000, evidence=[{"type": "gaps", "data": gaps}])

    async def improve(self, crit: ReasoningStageResult) -> ReasoningStageResult:
        s = time.monotonic()
        suggs = [{"type": "gap_fix", "action": g.get("action", ""), "priority": "high"} for g in crit.output.get("gaps", [])]
        for _r in crit.output.get("risks", []):
            suggs.append({"type": "failure_recovery", "suggestion": "Activate fallback or escalate", "priority": "critical"})
        if not suggs:
            suggs.append({"type": "no_improvements", "priority": "low"})
        conf = max(0.1, min(crit.confidence - (0.15 if any(x.get("priority") == "critical" for x in suggs) else 0), 1.0))
        return ReasoningStageResult(stage="improve", output={"suggestions": suggs, "count": len(suggs)}, confidence=conf, duration_ms=(time.monotonic() - s) * 1000, evidence=[{"type": "suggestions", "data": suggs}])

    async def validate(self, improve: ReasoningStageResult, context: dict[str, Any]) -> ReasoningStageResult:
        s = time.monotonic()
        blockers = ["block", "remove", "disable", "shut"]
        viols, valid = [], []
        for sg in improve.output.get("suggestions", []):
            text = str(sg).lower()
            bad = context.get("accessibility_needs") and any(b in text for b in blockers)
            (viols if bad else valid).append({"type": "accessibility_violation", "suggestion": sg} if bad else sg)
        conf = max(0.1, min(improve.confidence - 0.2 * len(viols), 1.0))
        return ReasoningStageResult(stage="validate", output={"validated": valid, "violations": viols, "is_valid": len(viols) == 0}, confidence=conf, duration_ms=(time.monotonic() - s) * 1000, evidence=[{"type": "validated", "data": valid}])

    async def explain(self, stages: list[ReasoningStageResult], chain_id: UUID, request_id: UUID) -> ReasoningStageResult:
        s = time.monotonic()
        conf = sum(st.confidence for st in stages) / len(stages) if stages else 0.0
        findings, recs = [], []
        for st in stages:
            if st.stage == "think":
                findings.extend([p.get("description", "") for p in st.output.get("patterns", [])])
                findings.extend([a.get("description", "") for a in st.output.get("anomalies", [])])
            if st.stage == "improve":
                recs.extend([x.get("suggestion", "") for x in st.output.get("suggestions", [])])
        expl = {"chain_id": str(chain_id), "request_id": str(request_id), "confidence": conf, "pipeline": " -> ".join(_STAGES), "findings": findings, "recommendations": recs}
        return ReasoningStageResult(stage="explain", output=expl, confidence=conf, duration_ms=(time.monotonic() - s) * 1000, evidence=[{"type": "explanation", "data": expl}])

    @staticmethod
    def _conclusion(stages: list[ReasoningStageResult]) -> dict[str, Any]:
        c: dict[str, Any] = {"stages": len(stages), "names": [s.stage.value for s in stages]}
        for s in stages:
            if s.stage == "plan":
                p = s.output.get("primary_strategy")
                if p:
                    c["primary_strategy"] = p.get("name")
            if s.stage == "validate":
                c["is_valid"] = s.output.get("is_valid", False)
            if s.stage == "critique":
                c["gap_ratio"] = s.output.get("gap_ratio", 0.0)
        return c

    @staticmethod
    def _summary(stages: list[ReasoningStageResult], conf: float) -> str:
        if not stages:
            return "No reasoning stages completed."
        return f"Completed {len(stages)}-stage pipeline: {' -> '.join(s.stage.value for s in stages)}. Confidence: {conf:.2%}."
