from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from app.features.orchestration.models.enums import MemoryType
from app.shared.result import Result, Success

logging = logging.getLogger(__name__)


class MemoryEntry:
    __slots__ = ("key", "data", "metadata", "memory_type", "created_at", "expires_at")

    def __init__(
        self,
        key: str,
        data: dict,
        metadata: dict,
        memory_type: MemoryType,
        ttl_seconds: float | None = None,
    ) -> None:
        self.key = key
        self.data = data
        self.metadata = metadata
        self.memory_type = memory_type
        self.created_at = time.monotonic()
        self.expires_at = self.created_at + ttl_seconds if ttl_seconds else None

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.monotonic() > self.expires_at

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "data": self.data,
            "metadata": self.metadata,
            "memory_type": self.memory_type.value,
            "created_at": self.created_at,
        }


class MemoryManager:
    def __init__(self) -> None:
        self._storage: dict[MemoryType, dict[str, MemoryEntry]] = {
            memory_type: {} for memory_type in MemoryType
        }

    async def store(
        self,
        memory_type: MemoryType,
        key: str,
        data: dict,
        metadata: dict | None = None,
        ttl_seconds: float | None = None,
    ) -> Result[None]:
        entry = MemoryEntry(
            key=key,
            data=data,
            metadata=metadata or {},
            memory_type=memory_type,
            ttl_seconds=ttl_seconds,
        )
        self._storage[memory_type][key] = entry
        logging.debug("Stored memory [%s] key=%s", memory_type.value, key)
        return Success(value=None)

    async def retrieve(self, memory_type: MemoryType, key: str) -> Result[dict | None]:
        store = self._storage.get(memory_type, {})
        entry = store.get(key)

        if entry is None:
            return Success(value=None)

        if entry.is_expired:
            del store[key]
            return Success(value=None)

        return Success(value=entry.to_dict())

    async def search(
        self,
        memory_type: MemoryType,
        query: str,
        limit: int = 10,
    ) -> Result[list[dict]]:
        store = self._storage.get(memory_type, {})
        query_lower = query.lower()
        matches: list[dict] = []

        for entry in store.values():
            if entry.is_expired:
                continue
            if self._matches_query(entry, query_lower):
                matches.append(entry.to_dict())
                if len(matches) >= limit:
                    break

        return Success(value=matches)

    async def get_conversation_history(
        self,
        session_id: str,
        limit: int = 50,
    ) -> Result[list[dict]]:
        store = self._storage.get(MemoryType.CONVERSATION, {})
        history: list[dict] = []

        for _key, entry in store.items():
            if entry.is_expired:
                continue
            if entry.data.get("session_id") == session_id:
                history.append(entry.to_dict())

        history.sort(key=lambda e: e.get("created_at", 0))
        return Success(value=history[-limit:])

    async def get_volunteer_context(self, volunteer_id: UUID) -> Result[dict]:
        store = self._storage.get(MemoryType.VOLUNTEER, {})
        key = str(volunteer_id)
        entry = store.get(key)

        if entry is None or entry.is_expired:
            return Success(value={
                "volunteer_id": str(volunteer_id),
                "historical_assignments": [],
                "preferences": {},
                "training_status": {},
            })

        return Success(value=entry.data)

    async def get_incident_context(self, incident_id: UUID) -> Result[dict]:
        store = self._storage.get(MemoryType.INCIDENT, {})
        key = str(incident_id)
        entry = store.get(key)

        if entry is None or entry.is_expired:
            return Success(value={
                "incident_id": str(incident_id),
                "related_incidents": [],
                "response_history": [],
                "lessons_learned": [],
            })

        return Success(value=entry.data)

    async def summarize_and_compress(
        self,
        memory_type: MemoryType,
        entries: list[dict],
    ) -> Result[dict]:
        if not entries:
            return Success(value={"summary": "No entries to summarize", "entry_count": 0})

        key_frequencies: dict[str, int] = {}
        all_data: list[dict] = []

        for entry in entries:
            data = entry.get("data", {})
            all_data.append(data)
            for key in data:
                key_frequencies[key] = key_frequencies.get(key, 0) + 1

        common_keys = sorted(key_frequencies.keys(), key=lambda k: key_frequencies[k], reverse=True)[:10]

        compressed: dict[str, Any] = {}
        for key in common_keys:
            values = [d.get(key) for d in all_data if key in d]
            if values:
                if isinstance(values[0], (str, int, float, bool)):
                    compressed[key] = values[-1]
                elif isinstance(values[0], list):
                    merged: list = []
                    for v in values:
                        if isinstance(v, list):
                            merged.extend(v)
                    compressed[key] = merged[-20:]
                elif isinstance(values[0], dict):
                    merged_dict: dict = {}
                    for v in values:
                        if isinstance(v, dict):
                            merged_dict.update(v)
                    compressed[key] = merged_dict

        compressed["entry_count"] = len(entries)
        compressed["compressed_at"] = time.monotonic()

        return Success(value=compressed)

    async def expire_old_entries(self, memory_type: MemoryType) -> int:
        store = self._storage.get(memory_type, {})
        expired_keys = [key for key, entry in store.items() if entry.is_expired]

        for key in expired_keys:
            del store[key]

        if expired_keys:
            logging.info(
                "Expired %d entries from %s memory", len(expired_keys), memory_type.value,
            )

        return len(expired_keys)

    async def get_operational_context(self, venue_id: UUID) -> Result[dict]:
        store = self._storage.get(MemoryType.OPERATIONAL, {})
        key = str(venue_id)
        entry = store.get(key)

        if entry is None or entry.is_expired:
            return Success(value={
                "venue_id": str(venue_id),
                "current_status": "normal",
                "active_incidents": [],
                "crowd_status": {},
                "resource_status": {},
            })

        return Success(value=entry.data)

    def _matches_query(self, entry: MemoryEntry, query_lower: str) -> bool:
        if query_lower in entry.key.lower():
            return True

        data_str = str(entry.data).lower()
        if query_lower in data_str:
            return True

        metadata_str = str(entry.metadata).lower()
        if query_lower in metadata_str:
            return True

        return False
