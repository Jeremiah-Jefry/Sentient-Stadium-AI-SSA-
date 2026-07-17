"""Tests for MemoryManager — storage, retrieval, search, TTL expiration, and conversation history."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from app.features.orchestration.memory.memory_manager import MemoryManager
from app.features.orchestration.models.enums import MemoryType
from app.shared.result import Success


@pytest.fixture
def manager() -> MemoryManager:
    return MemoryManager()


class TestMemoryManager:

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, manager: MemoryManager) -> None:
        await manager.store(
            MemoryType.OPERATIONAL, "zone_a_status",
            data={"crowd_density": 0.65, "status": "normal"},
            metadata={"source": "sensor"},
        )
        result = await manager.retrieve(MemoryType.OPERATIONAL, "zone_a_status")
        assert isinstance(result, Success)
        assert result.value is not None
        assert result.value["data"]["crowd_density"] == 0.65

    @pytest.mark.asyncio
    async def test_retrieve_not_found(self, manager: MemoryManager) -> None:
        result = await manager.retrieve(MemoryType.CONVERSATION, "nonexistent_key")
        assert isinstance(result, Success)
        assert result.value is None

    @pytest.mark.asyncio
    async def test_store_overwrites(self, manager: MemoryManager) -> None:
        await manager.store(MemoryType.INCIDENT, "inc_1", data={"severity": "low"})
        await manager.store(MemoryType.INCIDENT, "inc_1", data={"severity": "high"})
        result = await manager.retrieve(MemoryType.INCIDENT, "inc_1")
        assert result.value["data"]["severity"] == "high"

    @pytest.mark.asyncio
    async def test_search(self, manager: MemoryManager) -> None:
        await manager.store(MemoryType.OPERATIONAL, "gate_status", data={"gate": "A", "open": True})
        await manager.store(MemoryType.OPERATIONAL, "weather_update", data={"temp": 31.2})
        await manager.store(MemoryType.OPERATIONAL, "crowd_count", data={"zone": "B", "count": 5000})

        results = await manager.search(MemoryType.OPERATIONAL, "gate")
        assert isinstance(results, Success)
        assert len(results.value) >= 1
        assert any("gate" in r["key"].lower() for r in results.value)

    @pytest.mark.asyncio
    async def test_search_limit(self, manager: MemoryManager) -> None:
        for i in range(15):
            await manager.store(MemoryType.SHORT_TERM, f"item_{i}", data={"idx": i})

        results = await manager.search(MemoryType.SHORT_TERM, "item", limit=5)
        assert isinstance(results, Success)
        assert len(results.value) <= 5

    @pytest.mark.asyncio
    async def test_search_no_match(self, manager: MemoryManager) -> None:
        await manager.store(MemoryType.OPERATIONAL, "status", data={"ok": True})
        results = await manager.search(MemoryType.OPERATIONAL, "xyz_nonexistent")
        assert isinstance(results, Success)
        assert len(results.value) == 0

    @pytest.mark.asyncio
    async def test_ttl_expiration(self, manager: MemoryManager) -> None:
        await manager.store(
            MemoryType.SHORT_TERM, "ephemeral",
            data={"value": 42},
            ttl_seconds=0.01,
        )
        immediate = await manager.retrieve(MemoryType.SHORT_TERM, "ephemeral")
        assert immediate.value is not None

        await asyncio.sleep(0.05)
        expired = await manager.retrieve(MemoryType.SHORT_TERM, "ephemeral")
        assert expired.value is None

    @pytest.mark.asyncio
    async def test_expire_old_entries(self, manager: MemoryManager) -> None:
        await manager.store(MemoryType.SHORT_TERM, "old_1", data={}, ttl_seconds=0.01)
        await manager.store(MemoryType.SHORT_TERM, "old_2", data={}, ttl_seconds=0.01)
        await manager.store(MemoryType.SHORT_TERM, "keep", data={}, ttl_seconds=60.0)

        await asyncio.sleep(0.05)
        removed = await manager.expire_old_entries(MemoryType.SHORT_TERM)
        assert removed == 2
        result = await manager.retrieve(MemoryType.SHORT_TERM, "keep")
        assert result.value is not None

    @pytest.mark.asyncio
    async def test_conversation_history(self, manager: MemoryManager) -> None:
        session_id = "session_abc"
        await manager.store(MemoryType.CONVERSATION, "msg_1", data={"role": "user", "text": "hi", "session_id": session_id})
        await manager.store(MemoryType.CONVERSATION, "msg_2", data={"role": "agent", "text": "hello", "session_id": session_id})
        await manager.store(MemoryType.CONVERSATION, "msg_3", data={"role": "user", "text": "help", "session_id": session_id})

        history = await manager.get_conversation_history(session_id)
        assert isinstance(history, Success)
        assert len(history.value) == 3

    @pytest.mark.asyncio
    async def test_conversation_history_different_sessions(self, manager: MemoryManager) -> None:
        await manager.store(MemoryType.CONVERSATION, "s1_msg", data={"session_id": "s1", "text": "a"})
        await manager.store(MemoryType.CONVERSATION, "s2_msg", data={"session_id": "s2", "text": "b"})

        history = await manager.get_conversation_history("s1")
        assert len(history.value) == 1
        assert history.value[0]["data"]["session_id"] == "s1"

    @pytest.mark.asyncio
    async def test_volunteer_context(self, manager: MemoryManager) -> None:
        vid = uuid4()
        await manager.store(
            MemoryType.VOLUNTEER, str(vid),
            data={"assignments": 12, "success_rate": 0.96},
        )
        result = await manager.get_volunteer_context(vid)
        assert result.value["assignments"] == 12

    @pytest.mark.asyncio
    async def test_volunteer_context_not_found(self, manager: MemoryManager) -> None:
        result = await manager.get_volunteer_context(uuid4())
        assert result.value["historical_assignments"] == []

    @pytest.mark.asyncio
    async def test_incident_context(self, manager: MemoryManager) -> None:
        iid = uuid4()
        await manager.store(
            MemoryType.INCIDENT, str(iid),
            data={"severity": "high", "related": []},
        )
        result = await manager.get_incident_context(iid)
        assert result.value["severity"] == "high"

    @pytest.mark.asyncio
    async def test_summarize_and_compress(self, manager: MemoryManager) -> None:
        entries = [
            {"data": {"density": 0.6, "status": "normal"}},
            {"data": {"density": 0.7, "status": "elevated"}},
        ]
        result = await manager.summarize_and_compress(MemoryType.OPERATIONAL, entries)
        assert isinstance(result, Success)
        assert result.value["entry_count"] == 2

    @pytest.mark.asyncio
    async def test_summarize_empty(self, manager: MemoryManager) -> None:
        result = await manager.summarize_and_compress(MemoryType.OPERATIONAL, [])
        assert result.value["entry_count"] == 0
