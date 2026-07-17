from __future__ import annotations

import logging
import statistics
from typing import Any
from uuid import UUID

from app.features.orchestration.reasoning.reasoning_engine import (
    ReasoningChain,
    ReasoningStageResult,
)

logging = logging.getLogger(__name__)


class ReasoningChainManager:

    def __init__(self) -> None:
        self._chains: dict[UUID, ReasoningChain] = {}
        self._request_index: dict[UUID, list[UUID]] = {}

    async def create_chain(self, request_id: UUID) -> ReasoningChain:
        chain = ReasoningChain(
            chain_id=UUID(int=0),
            request_id=request_id,
        )
        self._chains[chain.chain_id] = chain
        self._request_index.setdefault(request_id, []).append(chain.chain_id)
        logging.debug("Created reasoning chain %s for request %s", chain.chain_id, request_id)
        return chain

    async def add_stage(
        self,
        chain: ReasoningChain,
        stage: ReasoningStageResult,
    ) -> ReasoningChain:
        updated_stages = list(chain.stages)
        updated_stages.append(stage)

        updated = ReasoningChain(
            chain_id=chain.chain_id,
            request_id=chain.request_id,
            stages=updated_stages,
            overall_confidence=chain.overall_confidence,
            total_duration_ms=chain.total_duration_ms,
            conclusion=chain.conclusion,
            summary=chain.summary,
        )

        self._chains[chain.chain_id] = updated
        logging.debug(
            "Added stage %s to chain %s (total: %d)",
            stage.stage.value, chain.chain_id, len(updated_stages),
        )
        return updated

    async def finalize(self, chain: ReasoningChain) -> ReasoningChain:
        if not chain.stages:
            return chain

        confidences = [s.confidence for s in chain.stages]
        durations = [s.duration_ms for s in chain.stages]

        overall_confidence = statistics.mean(confidences) if confidences else 0.0
        total_duration = sum(durations)

        stage_names = [s.stage.value for s in chain.stages]
        pipeline = " -> ".join(stage_names)
        conclusion = {
            "stages_completed": len(chain.stages),
            "stage_names": stage_names,
            "confidence_stdev": statistics.stdev(confidences) if len(confidences) > 1 else 0.0,
        }

        summary = (
            f"Completed {len(chain.stages)}-stage reasoning pipeline: {pipeline}. "
            f"Overall confidence: {overall_confidence:.2%}."
        )

        finalized = ReasoningChain(
            chain_id=chain.chain_id,
            request_id=chain.request_id,
            stages=chain.stages,
            overall_confidence=round(overall_confidence, 4),
            total_duration_ms=round(total_duration, 2),
            conclusion=conclusion,
            summary=summary,
        )

        self._chains[chain.chain_id] = finalized
        logging.info(
            "Finalized chain %s: confidence=%.3f, stages=%d, duration=%.1fms",
            chain.chain_id, overall_confidence, len(chain.stages), total_duration,
        )
        return finalized

    def get_chain(self, chain_id: UUID) -> ReasoningChain | None:
        return self._chains.get(chain_id)

    def get_chains_for_request(self, request_id: UUID) -> list[ReasoningChain]:
        chain_ids = self._request_index.get(request_id, [])
        return [self._chains[cid] for cid in chain_ids if cid in self._chains]

    def store_chain(self, chain: ReasoningChain) -> None:
        self._chains[chain.chain_id] = chain
        self._request_index.setdefault(chain.request_id, []).append(chain.chain_id)

    def get_stats(self) -> dict[str, Any]:
        total_chains = len(self._chains)
        if total_chains == 0:
            return {
                "total_chains": 0,
                "avg_confidence": 0.0,
                "avg_stages": 0.0,
                "avg_duration_ms": 0.0,
                "confidence_distribution": {},
            }

        confidences = [c.overall_confidence for c in self._chains.values()]
        stage_counts = [len(c.stages) for c in self._chains.values()]
        durations = [c.total_duration_ms for c in self._chains.values()]

        buckets = {"high": 0, "medium": 0, "low": 0}
        for conf in confidences:
            if conf >= 0.8:
                buckets["high"] += 1
            elif conf >= 0.5:
                buckets["medium"] += 1
            else:
                buckets["low"] += 1

        return {
            "total_chains": total_chains,
            "avg_confidence": round(statistics.mean(confidences), 4),
            "avg_stages": round(statistics.mean(stage_counts), 1),
            "avg_duration_ms": round(statistics.mean(durations), 2),
            "confidence_distribution": buckets,
        }
