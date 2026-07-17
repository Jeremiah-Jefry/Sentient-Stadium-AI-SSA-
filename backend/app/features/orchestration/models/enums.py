"""Domain enums for the Orchestration Engine module."""

from __future__ import annotations

import enum


class RequestType(str, enum.Enum):
    """Origin of an orchestration request."""

    VOLUNTEER_REQUEST = "volunteer_request"
    ADMIN_REQUEST = "admin_request"
    SYSTEM_EVENT = "system_event"
    REALTIME_EVENT = "realtime_event"
    PREDICTION_TRIGGER = "prediction_trigger"
    EMERGENCY = "emergency"
    ACCESSIBILITY_REQUEST = "accessibility_request"
    NAVIGATION_REQUEST = "navigation_request"


class IntentType(str, enum.Enum):
    """Classified intent driving the orchestration pipeline."""

    CROWD_MANAGEMENT = "crowd_management"
    NAVIGATION = "navigation"
    EMERGENCY_RESPONSE = "emergency_response"
    ACCESSIBILITY = "accessibility"
    MEDICAL = "medical"
    RESOURCE_ALLOCATION = "resource_allocation"
    INFORMATION_QUERY = "information_query"
    INCIDENT_RESPONSE = "incident_response"
    EVACUATION = "evacuation"
    WEATHER_ADVISORY = "weather_advisory"
    SECURITY = "security"
    OPERATIONAL = "operational"


class ExecutionStrategy(str, enum.Enum):
    """How execution steps are dispatched across agents."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    DYNAMIC = "dynamic"
    MIXED = "mixed"


class ExecutionStatus(str, enum.Enum):
    """Lifecycle state of an orchestration execution."""

    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    AGGREGATING = "aggregating"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class AgentStatus(str, enum.Enum):
    """Operational state of a registered agent."""

    AVAILABLE = "available"
    BUSY = "busy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    ERROR = "error"
    WARMING_UP = "warming_up"


class StepStatus(str, enum.Enum):
    """Lifecycle state of an individual execution step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ConflictResolutionStrategy(str, enum.Enum):
    """Strategy for resolving multi-agent output conflicts."""

    PRIORITY_BASED = "priority_based"
    VOTING = "voting"
    EVIDENCE_WEIGHTED = "evidence_weighted"
    HUMAN_OVERRIDE = "human_override"
    CONFIDENCE_BASED = "confidence_based"
    NEWEST_WINS = "newest_wins"


class SafetyLevel(str, enum.Enum):
    """Safety classification of an orchestration decision."""

    SAFE = "safe"
    WARNING = "warning"
    DANGEROUS = "dangerous"
    CRITICAL = "critical"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"


class MemoryType(str, enum.Enum):
    """Category of memory stored by the orchestration engine."""

    CONVERSATION = "conversation"
    VOLUNTEER = "volunteer"
    INCIDENT = "incident"
    OPERATIONAL = "operational"
    SEMANTIC = "semantic"
    LONG_TERM = "long_term"
    SHORT_TERM = "short_term"
    SESSION = "session"


class KnowledgeCategory(str, enum.Enum):
    """Domain classification for knowledge base entries."""

    SAFETY_SOP = "safety_sop"
    EMERGENCY_PROCEDURE = "emergency_procedure"
    VENUE_RULE = "venue_rule"
    VOLUNTEER_MANUAL = "volunteer_manual"
    ACCESSIBILITY_POLICY = "accessibility_policy"
    MEDICAL_GUIDANCE = "medical_guidance"
    HISTORICAL_INCIDENT = "historical_incident"
    OPERATIONAL_DOC = "operational_doc"


class ReasoningStage(str, enum.Enum):
    """Phase of the cognitive reasoning loop."""

    OBSERVE = "observe"
    THINK = "think"
    PLAN = "plan"
    EXECUTE = "execute"
    CRITIQUE = "critique"
    IMPROVE = "improve"
    VALIDATE = "validate"
    EXPLAIN = "explain"


class StreamingEventType(str, enum.Enum):
    """Type of event emitted over the streaming channel."""

    PROGRESS = "progress"
    AGENT_STATUS = "agent_status"
    PARTIAL_RESULT = "partial_result"
    REASONING_UPDATE = "reasoning_update"
    CONFIDENCE_UPDATE = "confidence_update"
    ERROR = "error"
    COMPLETE = "complete"


class UserRole(str, enum.Enum):
    """Role of the user or system initiating an orchestration request."""

    VOLUNTEER = "volunteer"
    COORDINATOR = "coordinator"
    ADMIN = "admin"
    SYSTEM = "system"
    EMERGENCY_LEAD = "emergency_lead"
