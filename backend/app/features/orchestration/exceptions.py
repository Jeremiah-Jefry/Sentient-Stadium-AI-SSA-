"""Domain-specific exception hierarchy for the Orchestration Engine module."""

from __future__ import annotations


class OrchestrationError(Exception):
    """Base exception for all orchestration errors."""

    def __init__(self, message: str, error_code: str, details: dict | None = None) -> None:
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class PlannerError(OrchestrationError):
    """Raised when the planner fails to generate or validate an execution plan."""

    def __init__(
        self,
        message: str = "Planning failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(message=message, error_code="PLANNER_FAILED", details=details)


class AgentExecutionError(OrchestrationError):
    """Raised when an agent fails to execute its assigned step."""

    def __init__(
        self,
        agent_id: str = "",
        message: str = "Agent execution failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=f"Agent '{agent_id}': {message}",
            error_code="AGENT_EXECUTION_FAILED",
            details=details,
        )


class ToolExecutionError(OrchestrationError):
    """Raised when a tool invocation fails or returns invalid results."""

    def __init__(
        self,
        tool_id: str = "",
        message: str = "Tool execution failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=f"Tool '{tool_id}': {message}",
            error_code="TOOL_EXECUTION_FAILED",
            details=details,
        )


class ConflictResolutionError(OrchestrationError):
    """Raised when conflicting agent outputs cannot be resolved."""

    def __init__(
        self,
        message: str = "Conflict resolution failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=message, error_code="CONFLICT_RESOLUTION_FAILED", details=details,
        )


class SafetyViolationError(OrchestrationError):
    """Raised when an action violates safety constraints or requires human review."""

    def __init__(
        self,
        message: str = "Safety violation detected",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=message, error_code="SAFETY_VIOLATION", details=details,
        )


class MemoryOperationError(OrchestrationError):
    """Raised when a memory read, write, or retrieval operation fails."""

    def __init__(
        self,
        message: str = "Memory operation failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=message, error_code="MEMORY_OPERATION_FAILED", details=details,
        )


class KnowledgeRetrievalError(OrchestrationError):
    """Raised when knowledge base or SOP retrieval fails."""

    def __init__(
        self,
        message: str = "Knowledge retrieval failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=message, error_code="KNOWLEDGE_RETRIEVAL_FAILED", details=details,
        )


class ReasoningError(OrchestrationError):
    """Raised when the reasoning engine produces an invalid or incomplete output."""

    def __init__(
        self,
        message: str = "Reasoning failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=message, error_code="REASONING_FAILED", details=details,
        )


class ConfidenceError(OrchestrationError):
    """Raised when confidence scoring or aggregation fails."""

    def __init__(
        self,
        message: str = "Confidence computation failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=message, error_code="CONFIDENCE_FAILED", details=details,
        )


class ExplanationError(OrchestrationError):
    """Raised when an explanation cannot be generated for an orchestration decision."""

    def __init__(
        self,
        message: str = "Explanation generation failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=message, error_code="EXPLANATION_FAILED", details=details,
        )


class StreamingError(OrchestrationError):
    """Raised when the streaming channel fails or disconnects unexpectedly."""

    def __init__(
        self,
        message: str = "Streaming error",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=message, error_code="STREAMING_FAILED", details=details,
        )


class AgentRegistryError(OrchestrationError):
    """Raised when agent registration, lookup, or deregistration fails."""

    def __init__(
        self,
        message: str = "Agent registry error",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=message, error_code="AGENT_REGISTRY_FAILED", details=details,
        )


class ToolRegistryError(OrchestrationError):
    """Raised when tool registration, lookup, or deregistration fails."""

    def __init__(
        self,
        message: str = "Tool registry error",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=message, error_code="TOOL_REGISTRY_FAILED", details=details,
        )


class PipelineError(OrchestrationError):
    """Raised when an orchestration pipeline stage encounters a failure."""

    def __init__(
        self,
        stage: str = "",
        message: str = "Pipeline stage failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=f"Stage '{stage}': {message}",
            error_code="PIPELINE_STAGE_FAILED",
            details=details,
        )


class ContextGatheringError(OrchestrationError):
    """Raised when context assembly from multiple sources fails."""

    def __init__(
        self,
        message: str = "Context gathering failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=message, error_code="CONTEXT_GATHERING_FAILED", details=details,
        )
