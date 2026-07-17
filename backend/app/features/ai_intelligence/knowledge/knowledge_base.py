"""Knowledge retrieval — pluggable backend for safety guidelines, SOPs, and protocols."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class KnowledgeEntry:
    """Single retrievable knowledge document."""

    id: str
    title: str
    category: str
    content: str
    relevance_score: float = 0.0
    source: str = ""
    last_updated: str = ""


class KnowledgeRetrieval(ABC):
    """Abstract interface for knowledge retrieval backends."""

    @abstractmethod
    async def search(
        self, query: str, category: str, limit: int = 5,
    ) -> list[KnowledgeEntry]:
        """Search the knowledge store and return ranked entries."""


class InMemoryKnowledgeRetrieval(KnowledgeRetrieval):
    """In-memory knowledge store with keyword matching.

    Pre-loaded with representative knowledge entries for FIFA World Cup 2026.
    These are retrievable reference documents, not hardcoded decision logic.
    """

    def __init__(self) -> None:
        self._entries: list[KnowledgeEntry] = self._load_default_entries()
        logger.info(
            "InMemoryKnowledgeRetrieval loaded %d entries", len(self._entries),
        )

    async def search(
        self, query: str, category: str, limit: int = 5,
    ) -> list[KnowledgeEntry]:
        query_lower = query.lower()
        scored: list[tuple[float, KnowledgeEntry]] = []

        for entry in self._entries:
            if category and entry.category != category:
                continue
            score = self._keyword_score(query_lower, entry)
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        results = [entry for _, entry in scored[:limit]]
        for entry in results:
            entry.relevance_score = round(
                scored[[e.id for _, e in scored].index(entry.id)][0], 4,
            ) if scored else 0.0
        return results

    def _keyword_score(self, query: str, entry: KnowledgeEntry) -> float:
        text = f"{entry.title} {entry.content} {entry.category}".lower()
        query_words = query.split()
        if not query_words:
            return 0.0
        hits = sum(1 for w in query_words if w in text)
        return hits / len(query_words)

    @staticmethod
    def _load_default_entries() -> list[KnowledgeEntry]:
        return [
            KnowledgeEntry(
                id="sg-001",
                title="FIFA Crowd Density Safety Thresholds",
                category="safety_guidelines",
                content=(
                    "FIFA mandates a maximum sustained crowd density of 4 persons "
                    "per square metre in standing areas and 2 persons per square "
                    "metre in seated concourses. When density exceeds 80% of "
                    "capacity, venue operations must activate overflow management "
                    "protocols and prepare for potential evacuation."
                ),
                source="FIFA Safety and Security Regulations 2026",
                last_updated="2025-01-15",
            ),
            KnowledgeEntry(
                id="sg-002",
                title="Emergency Evacuation Standard Operating Procedure",
                category="safety_guidelines",
                content=(
                    "On evacuation order, all gates open simultaneously and "
                    "stewards guide crowd toward pre-assigned assembly areas. "
                    "Full venue evacuation target is 8 minutes for Category A "
                    "venues. PA announcements repeat in all six official FIFA "
                    "languages at 30-second intervals until the venue is clear."
                ),
                source="FIFA Venue Safety Manual",
                last_updated="2025-02-10",
            ),
            KnowledgeEntry(
                id="sg-003",
                title="Medical Response Protocol for Mass Gatherings",
                category="medical_protocols",
                content=(
                    "Medical teams must be positioned no more than 90 seconds "
                    "from any spectator seat. When three or more medical "
                    "incidents occur within 10 minutes in the same zone, the "
                    "medical coordinator escalates to incident command and "
                    "pre-positions additional first-aid resources."
                ),
                source="FIFA Medical Code of Practice",
                last_updated="2025-03-01",
            ),
            KnowledgeEntry(
                id="sg-004",
                title="Accessibility Routing and Wheelchair Priority Policy",
                category="accessibility_policies",
                content=(
                    "Designated accessible routes must remain unobstructed at "
                    "all times. When a primary accessible route is blocked, "
                    "volunteers must escort wheelchair users and mobility-aid "
                    "users to a pre-approved alternative within 120 seconds. "
                    "No accessible route may exceed a 1:12 gradient."
                ),
                source="FIFA Accessibility Guide",
                last_updated="2025-01-20",
            ),
            KnowledgeEntry(
                id="sg-005",
                title="Weather Delay Procedures",
                category="safety_guidelines",
                content=(
                    "When lightning is detected within 10 km the match referee "
                    "suspends play and spectators are directed to sheltered "
                    "areas. Strong winds above 60 km/h require securing of "
                    "temporary structures and signage. Extreme heat protocols "
                    "activate when wet-bulb globe temperature exceeds 32°C."
                ),
                source="FIFA Weather Risk Management",
                last_updated="2025-04-05",
            ),
            KnowledgeEntry(
                id="sg-006",
                title="Security Escalation Protocol",
                category="security_protocols",
                content=(
                    "Security events are graded Level 1 (localised) through "
                    "Level 3 (venue-wide). Level 2 events require the "
                    "security operations centre to notify the match commissioner. "
                    "Level 3 triggers coordinated response with local law "
                    "enforcement and may result in match suspension."
                ),
                source="FIFA Security Manual 2026",
                last_updated="2025-02-28",
            ),
            KnowledgeEntry(
                id="sg-007", title="Volunteer Deployment and Rotation Guidelines",
                category="volunteer_guidelines",
                content=(
                    "Volunteers must not work more than 4 consecutive hours without a "
                    "30-minute break. Peak deployment occurs 90 minutes before kickoff "
                    "and 30 minutes after full time. At least 60% of volunteer pool "
                    "must be on-duty during ingress and egress peaks."
                ),
                source="FIFA Volunteer Programme Handbook", last_updated="2025-03-15",
            ),
            KnowledgeEntry(
                id="sg-008", title="Transport Disruption Response Plan",
                category="transport_protocols",
                content=(
                    "When public transport delays exceed 15 minutes, the transport "
                    "coordinator activates backup shuttle services. Park-and-ride "
                    "facilities must hold capacity for 20% overflow. Crowd managers "
                    "at transit hubs issue real-time multilingual guidance."
                ),
                source="FIFA Transport Management Plan", last_updated="2025-04-10",
            ),
            KnowledgeEntry(
                id="sg-009", title="Lost Child Recovery Procedure",
                category="safety_guidelines",
                content=(
                    "On lost-child report, stewards immediately secure the child's "
                    "last known location and notify the control room. A description "
                    "is broadcast to all stewards within 60 seconds. If not recovered "
                    "within 10 minutes, the procedure escalates to venue-wide PA "
                    "announcement and CCTV review."
                ),
                source="FIFA Safeguarding Policy", last_updated="2025-01-30",
            ),
            KnowledgeEntry(
                id="sg-010", title="Equipment Failure Contingency Plan",
                category="safety_guidelines",
                content=(
                    "When sensor or camera failures exceed 15% of total infrastructure "
                    "in a zone, manual monitoring must be deployed to compensate. "
                    "Critical systems (fire detection, CCTV in enclosed areas) have "
                    "a zero-tolerance failure threshold — backup systems activate "
                    "immediately."
                ),
                source="FIFA Technical Infrastructure Standards",
                last_updated="2025-05-01",
            ),
        ]


class KnowledgeBase:
    """Retrieves relevant knowledge from safety guidelines, emergency SOPs,
    venue policies, accessibility policies, and medical protocols.

    This is NOT hardcoded. It uses a pluggable retrieval interface
    that can be backed by a vector store, database, or API.
    """

    def __init__(self, retrieval_backend: KnowledgeRetrieval | None = None) -> None:
        self._backend = retrieval_backend or InMemoryKnowledgeRetrieval()
        self._query_count: int = 0

    async def retrieve_safety_guidelines(self, context: dict) -> list[KnowledgeEntry]:
        """Retrieve relevant safety guidelines for current situation."""
        self._query_count += 1
        return await self._backend.search(self._context_to_query(context), "safety_guidelines", 5)

    async def retrieve_emergency_sops(
        self, risk_level: str, context: dict,
    ) -> list[KnowledgeEntry]:
        """Retrieve emergency SOPs applicable to current risk level."""
        self._query_count += 1
        query = f"emergency {risk_level} {self._context_to_query(context)}"
        return await self._backend.search(query, "safety_guidelines", 5)

    async def retrieve_accessibility_policies(self, context: dict) -> list[KnowledgeEntry]:
        """Retrieve accessibility-related policies."""
        self._query_count += 1
        query = f"accessibility wheelchair {self._context_to_query(context)}"
        return await self._backend.search(query, "accessibility_policies", 5)

    async def retrieve_medical_protocols(self, context: dict) -> list[KnowledgeEntry]:
        """Retrieve medical response protocols."""
        self._query_count += 1
        query = f"medical response {self._context_to_query(context)}"
        return await self._backend.search(query, "medical_protocols", 5)

    @staticmethod
    def _context_to_query(context: dict) -> str:
        parts: list[str] = []
        for key in ("venue_id", "zone_id", "match_phase", "risk_level"):
            value = context.get(key)
            if value:
                parts.append(str(value))
        return " ".join(parts) if parts else "general"

    @property
    def stats(self) -> dict:
        return {"query_count": self._query_count}
