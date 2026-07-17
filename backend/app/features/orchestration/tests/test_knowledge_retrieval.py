"""Tests for KnowledgeRetrieval — safety SOPs, emergency procedures, and relevance ranking."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.features.orchestration.knowledge.knowledge_retrieval import KnowledgeRetrieval
from app.features.orchestration.models.enums import KnowledgeCategory
from app.shared.result import Success


@pytest.fixture
def retrieval() -> KnowledgeRetrieval:
    return KnowledgeRetrieval()


class TestKnowledgeRetrieval:

    @pytest.mark.asyncio
    async def test_retrieve_safety_sop(self, retrieval: KnowledgeRetrieval) -> None:
        result = await retrieval.retrieve(
            query="crowd gate capacity",
            categories=[KnowledgeCategory.SAFETY_SOP],
        )
        assert isinstance(result, Success)
        assert len(result.value) >= 1
        assert all(r["category"] == KnowledgeCategory.SAFETY_SOP.value for r in result.value)

    @pytest.mark.asyncio
    async def test_retrieve_emergency_procedure(self, retrieval: KnowledgeRetrieval) -> None:
        result = await retrieval.get_emergency_procedure("evacuation")
        assert isinstance(result, Success)
        assert result.value is not None
        assert result.value["category"] == KnowledgeCategory.EMERGENCY_PROCEDURE.value

    @pytest.mark.asyncio
    async def test_retrieve_emergency_procedure_no_match(self, retrieval: KnowledgeRetrieval) -> None:
        result = await retrieval.get_emergency_procedure("evacuation")
        assert isinstance(result, Success)
        assert result.value is not None
        assert result.value["relevance_score"] > 0.0
        result2 = await retrieval.get_emergency_procedure("quantum physics theorem")
        assert isinstance(result2, Success)
        assert result2.value is not None
        assert result2.value["relevance_score"] < result.value["relevance_score"]

    @pytest.mark.asyncio
    async def test_get_safety_sop(self, retrieval: KnowledgeRetrieval) -> None:
        result = await retrieval.get_safety_sop("gate", "crowd")
        assert isinstance(result, Success)
        assert result.value is not None
        assert result.value["category"] == KnowledgeCategory.SAFETY_SOP.value

    @pytest.mark.asyncio
    async def test_rank_results(self, retrieval: KnowledgeRetrieval) -> None:
        result = await retrieval.retrieve(
            query="emergency evacuation fire",
            categories=[KnowledgeCategory.EMERGENCY_PROCEDURE],
        )
        assert isinstance(result, Success)
        items = result.value
        if len(items) >= 2:
            for item in items:
                assert "relevance_score" in item
            scores = [item["relevance_score"] for item in items]
            assert scores == sorted(scores, reverse=True), "Results should be ranked by relevance"

    @pytest.mark.asyncio
    async def test_retrieve_all_categories(self, retrieval: KnowledgeRetrieval) -> None:
        result = await retrieval.retrieve(query="crowd evacuation wheelchair")
        assert isinstance(result, Success)
        assert len(result.value) >= 1
        categories = {r["category"] for r in result.value}
        assert len(categories) >= 2, "Query should match multiple categories"

    @pytest.mark.asyncio
    async def test_retrieve_limit(self, retrieval: KnowledgeRetrieval) -> None:
        result = await retrieval.retrieve(query="safety", limit=3)
        assert isinstance(result, Success)
        assert len(result.value) <= 3

    @pytest.mark.asyncio
    async def test_get_accessibility_guidelines(self, retrieval: KnowledgeRetrieval) -> None:
        zone_id = uuid4()
        result = await retrieval.get_accessibility_guidelines(zone_id)
        assert isinstance(result, Success)
        if result.value is not None:
            assert result.value["category"] == KnowledgeCategory.ACCESSIBILITY_POLICY.value

    @pytest.mark.asyncio
    async def test_get_operational_rules(self, retrieval: KnowledgeRetrieval) -> None:
        venue_id = uuid4()
        result = await retrieval.get_operational_rules(venue_id)
        assert isinstance(result, Success)
        if result.value is not None:
            assert result.value["category"] == KnowledgeCategory.VENUE_RULE.value

    @pytest.mark.asyncio
    async def test_knowledge_index_built(self, retrieval: KnowledgeRetrieval) -> None:
        assert len(retrieval._index) >= 15
        categories = {e["category"] for e in retrieval._index}
        assert KnowledgeCategory.SAFETY_SOP.value in categories
        assert KnowledgeCategory.EMERGENCY_PROCEDURE.value in categories
        assert KnowledgeCategory.ACCESSIBILITY_POLICY.value in categories
        assert KnowledgeCategory.MEDICAL_GUIDANCE.value in categories

    @pytest.mark.asyncio
    async def test_relevance_keyword_matching(self, retrieval: KnowledgeRetrieval) -> None:
        result = await retrieval.retrieve(query="wheelchair accessibility elevator")
        assert isinstance(result, Success)
        assert len(result.value) >= 1
        top = result.value[0]
        assert top["relevance_score"] > 0.0
