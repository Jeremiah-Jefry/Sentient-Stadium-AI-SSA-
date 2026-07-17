"""Streaming pipeline stages — validate, deduplicate, normalize, enrich."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.features.event_streaming.models.event_type import ProcessingStatus

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PipelineContext:
    """Mutable context passed through pipeline stages."""

    event_id: str
    event_type: str
    category: str
    payload: dict
    venue_id: str | None = None
    entity_id: str | None = None
    zone_id: str | None = None
    priority: str = "normal"
    severity: str = "info"
    producer: str = ""
    captured_at: str = ""
    status: ProcessingStatus = ProcessingStatus.RECEIVED
    errors: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    start_time_ms: float = 0.0


class PipelineStage(ABC):
    """Abstract base class for pipeline processing stages."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of this pipeline stage."""

    @abstractmethod
    async def process(self, ctx: PipelineContext) -> PipelineContext:
        """Process the event context. May modify or reject the event."""


class ValidationStage(PipelineStage):
    """Validates event schema, required fields, and data constraints."""

    @property
    def name(self) -> str:
        return "validation"

    REQUIRED_FIELDS = {"event_id", "event_type", "category", "source", "captured_at"}

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        ctx.status = ProcessingStatus.VALIDATING

        missing = self.REQUIRED_FIELDS - set(ctx.metadata.get("original_fields", []))
        if missing:
            ctx.errors.append(f"Missing required fields: {missing}")
            ctx.status = ProcessingStatus.FAILED
            return ctx

        if not ctx.event_id or len(ctx.event_id) > 64:
            ctx.errors.append("Invalid event_id length")
            ctx.status = ProcessingStatus.FAILED
            return ctx

        if not ctx.event_type or len(ctx.event_type) > 100:
            ctx.errors.append("Invalid event_type length")
            ctx.status = ProcessingStatus.FAILED
            return ctx

        return ctx


class DeduplicationStage(PipelineStage):
    """Drops duplicate events based on event_id to prevent reprocessing."""

    DEFAULT_MAX_SIZE = 1_000_000

    def __init__(self, ttl_seconds: int = 300, max_size: int | None = None) -> None:
        self._seen: dict[str, float] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size or self.DEFAULT_MAX_SIZE

    @property
    def name(self) -> str:
        return "deduplication"

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        ctx.status = ProcessingStatus.DEDUPLICATING
        now = time.monotonic()

        self._evict_expired(now)
        self._evict_oldest_if_at_capacity()

        if ctx.event_id in self._seen:
            ctx.errors.append(f"Duplicate event_id: {ctx.event_id}")
            ctx.status = ProcessingStatus.FAILED
            return ctx

        self._seen[ctx.event_id] = now
        return ctx

    def _evict_expired(self, now: float) -> None:
        """Remove expired entries to bound memory usage."""
        expired = [eid for eid, ts in self._seen.items() if now - ts > self._ttl]
        for eid in expired:
            del self._seen[eid]

    def _evict_oldest_if_at_capacity(self) -> None:
        """Evict oldest entries when at capacity to prevent unbounded growth."""
        if len(self._seen) >= self._max_size:
            oldest_keys = sorted(self._seen, key=self._seen.get)[:self._max_size // 2]
            for key in oldest_keys:
                self._seen.pop(key, None)


class NormalizationStage(PipelineStage):
    """Normalizes field names, units, and timestamp formats."""

    TIMESTAMP_FIELDS = {"captured_at", "timestamp", "created_at", "updated_at"}

    @property
    def name(self) -> str:
        return "normalization"

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        ctx.status = ProcessingStatus.NORMALIZING

        ctx.category = ctx.category.lower().strip()
        ctx.event_type = ctx.event_type.lower().strip()
        ctx.priority = ctx.priority.lower().strip()
        ctx.severity = ctx.severity.lower().strip()

        self._normalize_payload(ctx)
        self._compute_checksum(ctx)
        return ctx

    def _normalize_payload(self, ctx: PipelineContext) -> None:
        """Recursively normalize string values in payload."""
        ctx.payload = self._normalize_dict(ctx.payload)

    @staticmethod
    def _normalize_dict(data: dict) -> dict:
        """Strip and lowercase string values in a dictionary."""
        normalized: dict = {}
        for key, value in data.items():
            if isinstance(value, str):
                normalized[key] = value.strip()
            elif isinstance(value, dict):
                normalized[key] = NormalizationStage._normalize_dict(value)
            else:
                normalized[key] = value
        return normalized

    @staticmethod
    def _compute_checksum(ctx: PipelineContext) -> None:
        """Compute SHA-256 checksum of the event payload for integrity verification."""
        raw = json.dumps(ctx.payload, sort_keys=True, default=str)
        ctx.metadata["checksum"] = hashlib.sha256(raw.encode()).hexdigest()


class EnrichmentStage(PipelineStage):
    """Enriches events with contextual metadata from external sources."""

    @property
    def name(self) -> str:
        return "enrichment"

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        ctx.status = ProcessingStatus.ENRICHING

        ctx.metadata["processed_at"] = time.time()
        ctx.metadata["pipeline_version"] = "1.0"
        ctx.metadata["enrichment_complete"] = True

        if ctx.venue_id is None and ctx.entity_id:
            ctx.metadata["needs_entity_lookup"] = True

        return ctx
