"""Error handlers for Orchestration Engine module exceptions."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.features.orchestration.exceptions import (
    AgentExecutionError,
    AgentRegistryError,
    ConfidenceError,
    ConflictResolutionError,
    ContextGatheringError,
    ExplanationError,
    KnowledgeRetrievalError,
    MemoryOperationError,
    OrchestrationError,
    PipelineError,
    PlannerError,
    ReasoningError,
    SafetyViolationError,
    StreamingError,
    ToolExecutionError,
    ToolRegistryError,
)


def register_orchestration_error_handlers(app: FastAPI) -> None:
    """Register all orchestration exception handlers on the FastAPI application."""

    @app.exception_handler(PlannerError)
    async def handle_planner_error(
        request: Request, exc: PlannerError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(AgentExecutionError)
    async def handle_agent_execution_error(
        request: Request, exc: AgentExecutionError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(ToolExecutionError)
    async def handle_tool_execution_error(
        request: Request, exc: ToolExecutionError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(ConflictResolutionError)
    async def handle_conflict_resolution_error(
        request: Request, exc: ConflictResolutionError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(SafetyViolationError)
    async def handle_safety_violation_error(
        request: Request, exc: SafetyViolationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(MemoryOperationError)
    async def handle_memory_operation_error(
        request: Request, exc: MemoryOperationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(KnowledgeRetrievalError)
    async def handle_knowledge_retrieval_error(
        request: Request, exc: KnowledgeRetrievalError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(ReasoningError)
    async def handle_reasoning_error(
        request: Request, exc: ReasoningError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(ConfidenceError)
    async def handle_confidence_error(
        request: Request, exc: ConfidenceError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(ExplanationError)
    async def handle_explanation_error(
        request: Request, exc: ExplanationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(StreamingError)
    async def handle_streaming_error(
        request: Request, exc: StreamingError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(AgentRegistryError)
    async def handle_agent_registry_error(
        request: Request, exc: AgentRegistryError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(ToolRegistryError)
    async def handle_tool_registry_error(
        request: Request, exc: ToolRegistryError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(PipelineError)
    async def handle_pipeline_error(
        request: Request, exc: PipelineError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(ContextGatheringError)
    async def handle_context_gathering_error(
        request: Request, exc: ContextGatheringError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(OrchestrationError)
    async def handle_orchestration_error(
        request: Request, exc: OrchestrationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )
