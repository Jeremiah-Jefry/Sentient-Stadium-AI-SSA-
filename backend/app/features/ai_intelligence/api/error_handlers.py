"""Error handlers for AI Intelligence Engine module exceptions."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.features.ai_intelligence.exceptions import (
    ConfidenceError,
    ContextResolutionError,
    DecisionError,
    ExplainabilityError,
    IntelligenceError,
    KnowledgeRetrievalError,
    ModelNotAvailableError,
    PipelineStageError,
    PredictionError,
    RiskAssessmentError,
    SimulationError,
)


def register_ai_intelligence_error_handlers(app: FastAPI) -> None:
    """Register all AI intelligence exception handlers on the FastAPI application."""

    @app.exception_handler(PredictionError)
    async def handle_prediction_error(
        request: Request, exc: PredictionError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(RiskAssessmentError)
    async def handle_risk_assessment_error(
        request: Request, exc: RiskAssessmentError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(DecisionError)
    async def handle_decision_error(
        request: Request, exc: DecisionError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(SimulationError)
    async def handle_simulation_error(
        request: Request, exc: SimulationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(ExplainabilityError)
    async def handle_explainability_error(
        request: Request, exc: ExplainabilityError,
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

    @app.exception_handler(ConfidenceError)
    async def handle_confidence_error(
        request: Request, exc: ConfidenceError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(PipelineStageError)
    async def handle_pipeline_stage_error(
        request: Request, exc: PipelineStageError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(ModelNotAvailableError)
    async def handle_model_not_available(
        request: Request, exc: ModelNotAvailableError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(ContextResolutionError)
    async def handle_context_resolution_error(
        request: Request, exc: ContextResolutionError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(IntelligenceError)
    async def handle_intelligence_error(
        request: Request, exc: IntelligenceError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )
