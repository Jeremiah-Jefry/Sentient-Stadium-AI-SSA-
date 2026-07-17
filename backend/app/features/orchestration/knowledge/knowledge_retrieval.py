from __future__ import annotations

import logging
from uuid import UUID, uuid4

from app.features.orchestration.models.enums import KnowledgeCategory
from app.shared.result import Failure, Result, Success

logging = logging.getLogger(__name__)


class KnowledgeRetrieval:
    def __init__(self) -> None:
        self._index = self._build_knowledge_index()

    async def retrieve(
        self,
        query: str,
        categories: list[KnowledgeCategory] | None = None,
        limit: int = 10,
    ) -> Result[list[dict]]:
        query_lower = query.lower()
        candidates: list[dict] = []

        for entry in self._index:
            if categories and entry["category"] not in [c.value for c in categories]:
                continue
            candidates.append(entry)

        ranked = self._rank_results(query_lower, candidates)
        return Success(value=ranked[:limit])

    async def get_safety_sop(
        self,
        zone_type: str,
        incident_type: str,
    ) -> Result[dict | None]:
        query = f"{zone_type} {incident_type}"
        results = await self.retrieve(
            query=query,
            categories=[KnowledgeCategory.SAFETY_SOP],
            limit=1,
        )
        if isinstance(results, Failure):
            return Success(value=None)
        items = results.value
        return Success(value=items[0] if items else None)

    async def get_emergency_procedure(self, emergency_type: str) -> Result[dict | None]:
        results = await self.retrieve(
            query=emergency_type,
            categories=[KnowledgeCategory.EMERGENCY_PROCEDURE],
            limit=1,
        )
        if isinstance(results, Failure):
            return Success(value=None)
        items = results.value
        return Success(value=items[0] if items else None)

    async def get_accessibility_guidelines(self, zone_id: UUID) -> Result[dict | None]:
        results = await self.retrieve(
            query=str(zone_id),
            categories=[KnowledgeCategory.ACCESSIBILITY_POLICY],
            limit=1,
        )
        if isinstance(results, Failure):
            return Success(value=None)
        items = results.value
        return Success(value=items[0] if items else None)

    async def get_operational_rules(self, venue_id: UUID) -> Result[dict | None]:
        results = await self.retrieve(
            query=str(venue_id),
            categories=[KnowledgeCategory.VENUE_RULE],
            limit=1,
        )
        if isinstance(results, Failure):
            return Success(value=None)
        items = results.value
        return Success(value=items[0] if items else None)

    def _rank_results(self, query: str, results: list[dict]) -> list[dict]:
        category_priority: dict[str, float] = {
            KnowledgeCategory.SAFETY_SOP.value: 1.0,
            KnowledgeCategory.EMERGENCY_PROCEDURE.value: 0.95,
            KnowledgeCategory.MEDICAL_GUIDANCE.value: 0.9,
            KnowledgeCategory.ACCESSIBILITY_POLICY.value: 0.85,
            KnowledgeCategory.VENUE_RULE.value: 0.8,
            KnowledgeCategory.VOLUNTEER_MANUAL.value: 0.75,
            KnowledgeCategory.OPERATIONAL_DOC.value: 0.7,
            KnowledgeCategory.HISTORICAL_INCIDENT.value: 0.6,
        }

        scored: list[tuple[dict, float]] = []
        query_tokens = set(query.split())

        for entry in results:
            keyword_score = 0.0
            title_lower = entry.get("title", "").lower()
            content_lower = entry.get("content", "").lower()
            tags = entry.get("tags", [])

            for token in query_tokens:
                if token in title_lower:
                    keyword_score += 2.0
                if token in content_lower:
                    keyword_score += 1.0
                if any(token in tag.lower() for tag in tags):
                    keyword_score += 1.5

            category_score = category_priority.get(entry.get("category", ""), 0.5)
            total_score = keyword_score * category_score
            scored.append((entry, total_score))

        scored.sort(key=lambda x: x[1], reverse=True)

        ranked: list[dict] = []
        for entry, score in scored:
            result_entry = dict(entry)
            result_entry["relevance_score"] = round(score, 4)
            ranked.append(result_entry)

        return ranked

    def _build_knowledge_index(self) -> list[dict]:
        return [
            {
                "id": str(uuid4()),
                "title": "Crowd Management SOP - Gate Operations",
                "category": KnowledgeCategory.SAFETY_SOP.value,
                "tags": ["crowd", "gate", "entry", "capacity", "flow"],
                "content": (
                    "Section 4.1: Gate operations must maintain"
                    " a throughput of at least "
                    "2,000 entries per hour. When crowd density"
                    " exceeds 85% capacity at any gate, "
                    "redirect flow to adjacent gates. Activate"
                    " overflow protocol when gate queue "
                    "exceeds 200 persons. Deploy additional"
                    " scanners at 90% capacity threshold."
                ),
                "source": "FIFA WC 2026 Operations Manual v3.2",
                "version": "4.1",
                "last_reviewed": "2026-06-15",
            },
            {
                "id": str(uuid4()),
                "title": "Crowd Management SOP - Emergency Exit Procedures",
                "category": KnowledgeCategory.SAFETY_SOP.value,
                "tags": ["crowd", "emergency", "exit", "evacuation", "safety"],
                "content": (
                    "Section 4.3: Emergency exits must remain"
                    " unobstructed at all times. "
                    "Maximum clearance zone is 3 meters from"
                    " any emergency exit. When activated, "
                    "emergency exits must be fully opened"
                    " within 15 seconds. Volunteer marshals "
                    "must be positioned at each emergency exit"
                    " within 30 seconds of activation."
                ),
                "source": "FIFA WC 2026 Operations Manual v3.2",
                "version": "4.3",
                "last_reviewed": "2026-06-15",
            },
            {
                "id": str(uuid4()),
                "title": "Crowd Management SOP - Halftime Surge Protocol",
                "category": KnowledgeCategory.SAFETY_SOP.value,
                "tags": ["crowd", "halftime", "surge", "concourse", "flow"],
                "content": (
                    "Section 4.5: Halftime typically produces"
                    " a 40-60% increase in concourse "
                    "foot traffic within the first 5 minutes."
                    " Pre-deploy marshals to high-traffic "
                    "concourse areas 3 minutes before halftime."
                    " Activate additional concession "
                    "capacity. Monitor bathroom queue lengths"
                    " and redirect if wait exceeds 5 minutes."
                ),
                "source": "FIFA WC 2026 Operations Manual v3.2",
                "version": "4.5",
                "last_reviewed": "2026-06-15",
            },
            {
                "id": str(uuid4()),
                "title": "Full Stadium Evacuation Procedure",
                "category": KnowledgeCategory.EMERGENCY_PROCEDURE.value,
                "tags": ["evacuation", "emergency", "fire", "bomb", "threat", "assembly"],
                "content": (
                    "EP-2026-01: Full evacuation target time"
                    " is 8 minutes for 50,000 capacity. "
                    "Phase 1 (0-2 min): PA announcement,"
                    " emergency lighting activation. "
                    "Phase 2 (2-5 min): Gate-by-gate"
                    " controlled release,"
                    " volunteer-guided flow. "
                    "Phase 3 (5-8 min): Sweep and verify"
                    " clearance. Assembly points at "
                    "predetermined locations 200m from"
                    " venue perimeter."
                ),
                "source": "FIFA WC 2026 Emergency Protocol",
                "version": "2026-01",
                "last_reviewed": "2026-05-20",
            },
            {
                "id": str(uuid4()),
                "title": "Medical Emergency Response Procedure",
                "category": KnowledgeCategory.EMERGENCY_PROCEDURE.value,
                "tags": ["medical", "emergency", "first_responder", "ambulance", "triage"],
                "content": (
                    "EP-2026-03: Medical emergency response"
                    " requires dispatch within 60 seconds. "
                    "First responder must arrive within"
                    " 3 minutes for code green,"
                    " 1 minute for code red. "
                    "Triage categories: Immediate (red),"
                    " Delayed (yellow), Minor (green),"
                    " Expectant (black). "
                    "Nearest medical station must be"
                    " notified via radio channel 3."
                ),
                "source": "FIFA WC 2026 Emergency Protocol",
                "version": "2026-03",
                "last_reviewed": "2026-05-20",
            },
            {
                "id": str(uuid4()),
                "title": "Severe Weather Emergency Procedure",
                "category": KnowledgeCategory.EMERGENCY_PROCEDURE.value,
                "tags": ["weather", "lightning", "severe", "shelter", "evacuation"],
                "content": (
                    "EP-2026-05: Lightning detected within"
                    " 10 miles triggers shelter protocol. "
                    "All outdoor activities suspended."
                    " Spectators directed to interior"
                    " concourse areas. "
                    "Match暂停 if lightning within 6 miles."
                    " Severe weather watch requires"
                    " continuous monitoring. Wind advisory"
                    " at 50mph triggers structural assessment"
                    " of temporary installations."
                ),
                "source": "FIFA WC 2026 Emergency Protocol",
                "version": "2026-05",
                "last_reviewed": "2026-05-20",
            },
            {
                "id": str(uuid4()),
                "title": "Fire Emergency Response Procedure",
                "category": KnowledgeCategory.EMERGENCY_PROCEDURE.value,
                "tags": ["fire", "smoke", "sprinkler", "evacuation"],
                "content": (
                    "EP-2026-02: Smoke detection triggers"
                    " automatic sprinkler activation"
                    " in affected zone. "
                    "Evacuation radius of 50m from fire"
                    " source. Fire wardens must confirm"
                    " clear within 2 minutes. "
                    "If fire spreads beyond single zone,"
                    " escalate to full evacuation"
                    " protocol EP-2026-01. "
                    "Never use elevators during"
                    " fire emergency."
                ),
                "source": "FIFA WC 2026 Emergency Protocol",
                "version": "2026-02",
                "last_reviewed": "2026-05-20",
            },
            {
                "id": str(uuid4()),
                "title": "Wheelchair Accessible Seating Guidelines",
                "category": KnowledgeCategory.ACCESSIBILITY_POLICY.value,
                "tags": ["wheelchair", "accessibility", "seating", "companion", "elevator"],
                "content": (
                    "AP-101: Minimum 0.5% of total seating"
                    " must be wheelchair accessible"
                    " with companion seating. "
                    "Accessible seats must provide"
                    " equivalent sightlines to standard"
                    " seating. "
                    "Elevator access must serve all"
                    " accessible seating areas. "
                    "Maximum wait time for elevator"
                    " assistance: 3 minutes. Staff must"
                    " be trained in wheelchair transfer"
                    " assistance."
                ),
                "source": "FIFA Accessibility Standards 2026",
                "version": "1.0",
                "last_reviewed": "2026-04-10",
            },
            {
                "id": str(uuid4()),
                "title": "Visual Impairment Support Guidelines",
                "category": KnowledgeCategory.ACCESSIBILITY_POLICY.value,
                "tags": ["visual", "blind", "audio_description", "guide_dog", "tactile"],
                "content": (
                    "AP-102: Audio description service must"
                    " be available for all matches. "
                    "Tactile wayfinding paths must be"
                    " installed at all major concourse"
                    " intersections. "
                    "Guide dogs must be permitted in all"
                    " seating areas. Staff must offer"
                    " arm-guided navigation upon request."
                    " Large-print programs available at"
                    " information desks."
                ),
                "source": "FIFA Accessibility Standards 2026",
                "version": "1.0",
                "last_reviewed": "2026-04-10",
            },
            {
                "id": str(uuid4()),
                "title": "Hearing Aid and Loop System Guidelines",
                "category": KnowledgeCategory.ACCESSIBILITY_POLICY.value,
                "tags": ["hearing", "loop", "sign_language", "caption", "assistive"],
                "content": (
                    "AP-103: Induction hearing loop coverage"
                    " required in all enclosed areas. "
                    "Sign language interpreters must be"
                    " available at information desks. "
                    "Real-time captioning must be displayed"
                    " on scoreboards. Emergency announcements"
                    " must include visual text display."
                    " Vibration alerts available for"
                    " deaf spectators."
                ),
                "source": "FIFA Accessibility Standards 2026",
                "version": "1.0",
                "last_reviewed": "2026-04-10",
            },
            {
                "id": str(uuid4()),
                "title": "Volunteer Greeting and Direction Standards",
                "category": KnowledgeCategory.VOLUNTEER_MANUAL.value,
                "tags": ["volunteer", "greeting", "direction", "customer_service", "information"],
                "content": (
                    "VM-201: Volunteers must greet every"
                    " spectator within 3 meters of their"
                    " station. Maximum response time for"
                    " direction requests: 15 seconds."
                    " Volunteers must know routes to all"
                    " major amenities within their zone."
                    " Use the 3-step direction method: "
                    "acknowledge, orient, confirm."
                    " Multi-language support required at"
                    " minimum 4 languages."
                ),
                "source": "FIFA WC 2026 Volunteer Handbook",
                "version": "2.0",
                "last_reviewed": "2026-06-01",
            },
            {
                "id": str(uuid4()),
                "title": "Volunteer Emergency Response Protocol",
                "category": KnowledgeCategory.VOLUNTEER_MANUAL.value,
                "tags": ["volunteer", "emergency", "response", "radio", "dispatch"],
                "content": (
                    "VM-203: Upon detecting an emergency,"
                    " volunteers must: 1) Ensure personal"
                    " safety, 2) Notify dispatch on radio"
                    " channel 1, 3) Begin guiding spectators"
                    " to safety, 4) Do not attempt medical"
                    " intervention unless certified."
                    " All volunteers must complete annual"
                    " emergency response training."
                    " Radio check required every 15 minutes"
                    " during events."
                ),
                "source": "FIFA WC 2026 Volunteer Handbook",
                "version": "2.0",
                "last_reviewed": "2026-06-01",
            },
            {
                "id": str(uuid4()),
                "title": "Venue Capacity Rules and Regulations",
                "category": KnowledgeCategory.VENUE_RULE.value,
                "tags": ["capacity", "standing", "seating", "limit", "compliance"],
                "content": (
                    "VR-101: Maximum venue capacity as certified by local authority is absolute. "
                    "No standing in seated areas except designated standing zones. "
                    "Standing zones must have 4.5 square meters per person minimum. "
                    "Real-time occupancy monitoring required at all entry points. "
                    "Capacity exceeded by more than 1% triggers automatic gate closure."
                ),
                "source": "FIFA WC 2026 Venue Regulations",
                "version": "1.0",
                "last_reviewed": "2026-03-15",
            },
            {
                "id": str(uuid4()),
                "title": "Prohibited Items Policy",
                "category": KnowledgeCategory.VENUE_RULE.value,
                "tags": ["prohibited", "banned", "weapons", "drone", "alcohol"],
                "content": (
                    "VR-103: Prohibited items include:"
                    " weapons of any kind, glass bottles,"
                    " drugs, fireworks, laser pointers,"
                    " drones, professional cameras with"
                    " detachable lenses, "
                    "large flags (>2m), musical instruments,"
                    " and outside food/beverages. "
                    "Bag policy: clear bags only, maximum"
                    " 12x6x12 inches. "
                    "Violations result in ejection and"
                    " potential arrest."
                ),
                "source": "FIFA WC 2026 Venue Regulations",
                "version": "1.0",
                "last_reviewed": "2026-03-15",
            },
            {
                "id": str(uuid4()),
                "title": "Heat Exhaustion Response Protocol",
                "category": KnowledgeCategory.MEDICAL_GUIDANCE.value,
                "tags": ["heat", "exhaustion", "dehydration", "cooling", "medical"],
                "content": (
                    "MG-301: Heat exhaustion indicators:"
                    " heavy sweating, weakness,"
                    " cold/clammy skin, fast/weak pulse,"
                    " nausea, fainting."
                    " Immediate response: move to shaded"
                    " area, apply cold compresses,"
                    " provide fluids (water or electrolytes),"
                    " loosen clothing. "
                    "If vomiting occurs or symptoms persist"
                    " beyond 15 minutes,"
                    " escalate to code red medical. "
                    "Prevention: ensure hydration stations"
                    " are within 100m of all seating areas."
                ),
                "source": "FIFA WC 2026 Medical Guidelines",
                "version": "1.0",
                "last_reviewed": "2026-04-01",
            },
            {
                "id": str(uuid4()),
                "title": "Cardiac Event Response Protocol",
                "category": KnowledgeCategory.MEDICAL_GUIDANCE.value,
                "tags": ["cardiac", "aed", "cpr", "heart", "defibrillator"],
                "content": (
                    "MG-302: Cardiac event indicators:"
                    " chest pain, shortness of breath,"
                    " collapse, no pulse."
                    " Immediate response: call code red,"
                    " begin CPR, retrieve nearest AED. "
                    "AED must be applied within 3 minutes."
                    " Continue CPR until medical team"
                    " arrives. "
                    "AED locations: every 200m throughout"
                    " venue, marked with green cross signs."
                    " All volunteers must be CPR/AED"
                    " certified."
                ),
                "source": "FIFA WC 2026 Medical Guidelines",
                "version": "1.0",
                "last_reviewed": "2026-04-01",
            },
            {
                "id": str(uuid4()),
                "title": "Allergic Reaction Response Protocol",
                "category": KnowledgeCategory.MEDICAL_GUIDANCE.value,
                "tags": ["allergic", "anaphylaxis", "epipen", "reaction", "medical"],
                "content": (
                    "MG-303: Mild allergic reaction: hives,"
                    " localized swelling, itching. "
                    "Provide antihistamine if available,"
                    " monitor for 30 minutes. "
                    "Severe reaction (anaphylaxis):"
                    " difficulty breathing,"
                    " throat swelling, rapid pulse. "
                    "Administer EpiPen if available,"
                    " call code red immediately. "
                    "EpiPen locations: all medical stations"
                    " and select volunteer posts."
                ),
                "source": "FIFA WC 2026 Medical Guidelines",
                "version": "1.0",
                "last_reviewed": "2026-04-01",
            },
            {
                "id": str(uuid4()),
                "title": "Historical Incident - 2025 Quarter Final Crowd Surge",
                "category": KnowledgeCategory.HISTORICAL_INCIDENT.value,
                "tags": ["historical", "crowd", "surge", "lesson", "section_204"],
                "content": (
                    "HI-2025-04: During the 2025 quarter"
                    " final, a crowd surge occurred in"
                    " Section 204 at halftime. "
                    "12 minor injuries reported."
                    " Root cause: insufficient exit"
                    " capacity for Section 204 combined"
                    " with delayed marshal deployment. "
                    "Lessons learned: pre-deploy marshals"
                    " 3 minutes before halftime at"
                    " high-density sections, "
                    "open overflow gates when density"
                    " exceeds 75%."
                ),
                "source": "FIFA Incident Database",
                "version": "2025-04",
                "last_reviewed": "2025-12-01",
            },
            {
                "id": str(uuid4()),
                "title": "Historical Incident - 2025 Group Stage Medical Delay",
                "category": KnowledgeCategory.HISTORICAL_INCIDENT.value,
                "tags": ["historical", "medical", "delay", "response_time", "lesson"],
                "content": (
                    "HI-2025-07: Medical response to a"
                    " cardiac event in Section 108 was"
                    " delayed by 4 minutes due to radio"
                    " communication failure on channel 3. "
                    "Patient outcome: positive after"
                    " bystander CPR. "
                    "Lessons learned: maintain backup"
                    " communication protocol, ensure all"
                    " medical teams have redundant radio"
                    " channels, quarterly radio drills"
                    " required."
                ),
                "source": "FIFA Incident Database",
                "version": "2025-07",
                "last_reviewed": "2025-12-01",
            },
            {
                "id": str(uuid4()),
                "title": "Photography and Media Policy",
                "category": KnowledgeCategory.VENUE_RULE.value,
                "tags": ["photography", "media", "camera", "press", "broadcast"],
                "content": (
                    "VR-105: Spectator personal photography"
                    " permitted with mobile phones and"
                    " small cameras. "
                    "Professional cameras with detachable"
                    " lenses require media accreditation. "
                    "Drone photography strictly prohibited."
                    " Media personnel must remain in"
                    " designated zones. "
                    "Live streaming by spectators permitted"
                    " for personal use only,"
                    " no commercial use."
                ),
                "source": "FIFA WC 2026 Venue Regulations",
                "version": "1.0",
                "last_reviewed": "2026-03-15",
            },
        ]
