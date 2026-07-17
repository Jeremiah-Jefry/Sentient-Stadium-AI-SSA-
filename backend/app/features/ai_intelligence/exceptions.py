"""Domain-specific exception hierarchy for the AI Intelligence Engine module."""

from __future__ import annotations


class IntelligenceError(Exception):
    """Base exception for all AI intelligence errors."""

    def __init__(self, message: str, error_code: str, details: dict | None = None) -> None:
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class PredictionError(IntelligenceError):
    """Raised when a prediction generation or retrieval operation fails."""

    def __init__(
        self,
        message: str = "Prediction failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(message=message, error_code="PREDICTION_FAILED", details=details)


class RiskAssessmentError(IntelligenceError):
    """Raised when risk scoring or assessment computation fails."""

    def __init__(
        self,
        message: str = "Risk assessment failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(message=message, error_code="RISK_ASSESSMENT_FAILED", details=details)


class DecisionError(IntelligenceError):
    """Raised when an autonomous decision cannot be reached or persisted."""

    def __init__(
        self,
        message: str = "Decision error",
        details: dict | None = None,
    ) -> None:
        super().__init__(message=message, error_code="DECISION_ERROR", details=details)


class SimulationError(IntelligenceError):
    """Raised when a simulation run fails or produces invalid results."""

    def __init__(
        self,
        message: str = "Simulation failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(message=message, error_code="SIMULATION_FAILED", details=details)


class ExplainabilityError(IntelligenceError):
    """Raised when an explanation cannot be generated for an AI output."""

    def __init__(
        self,
        message: str = "Explainability error",
        details: dict | None = None,
    ) -> None:
        super().__init__(message=message, error_code="EXPLAINABILITY_FAILED", details=details)


class KnowledgeRetrievalError(IntelligenceError):
    """Raised when knowledge base or historical data retrieval fails."""

    def __init__(
        self,
        message: str = "Knowledge retrieval failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=message, error_code="KNOWLEDGE_RETRIEVAL_FAILED", details=details,
        )


class ConfidenceError(IntelligenceError):
    """Raised when confidence computation or validation fails."""

    def __init__(
        self,
        message: str = "Confidence computation failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(message=message, error_code="CONFIDENCE_FAILED", details=details)


class PipelineStageError(IntelligenceError):
    """Raised when an intelligence pipeline stage encounters a failure."""

    def __init__(
        self,
        stage: str = "",
        message: str = "Pipeline stage failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=f"Stage '{stage}': {message}",
            error_code="INTELLIGENCE_PIPELINE_STAGE_FAILED",
            details=details,
        )


class ModelNotAvailableError(IntelligenceError):
    """Raised when a required ML or statistical model is not loaded or registered."""

    def __init__(
        self,
        model_name: str = "model",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=f"Model '{model_name}' not available",
            error_code="MODEL_NOT_AVAILABLE",
            details=details,
        )


class ContextResolutionError(IntelligenceError):
    """Raised when venue or zone context cannot be resolved for a request."""

    def __init__(
        self,
        message: str = "Context resolution failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=message, error_code="CONTEXT_RESOLUTION_FAILED", details=details,
        )
