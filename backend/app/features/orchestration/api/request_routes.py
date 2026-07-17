"""Orchestration request API routes — execute, stream, query, and cancel."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.features.orchestration.api.deps import (
    get_decision_ledger_repo,
    get_execution_repo,
    get_orchestration_service,
)
from app.features.orchestration.dto.request import OrchestratorRequest
from app.features.orchestration.dto.response import (
    OrchestratorResponse,
)
from app.features.orchestration.repositories.decision_ledger_repository import (
    DecisionLedgerRepository,
)
from app.features.orchestration.repositories.execution_repository import (
    ExecutionRepository,
)
from app.shared.result import Success

if TYPE_CHECKING:
    from app.features.orchestration.services.orchestration_service import (
        OrchestrationService,
    )

router = APIRouter(prefix="/orchestration", tags=["Orchestration Requests"])


@router.post(
    "/execute",
    response_model=OrchestratorResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute an orchestration request",
    description="Submit a request to the orchestration engine for multi-agent processing.",
)
async def execute_orchestration(
    request: OrchestratorRequest,
    service: OrchestrationService = Depends(get_orchestration_service),
) -> OrchestratorResponse:
    result = await service.execute(request)
    if not isinstance(result, Success):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.message,
        )
    return OrchestratorResponse(**result.value)


@router.post(
    "/execute/streaming",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Execute with streaming",
    description="Submit a request and return a streaming session ID for real-time progress.",
)
async def execute_orchestration_streaming(
    request: OrchestratorRequest,
    service: OrchestrationService = Depends(get_orchestration_service),
) -> dict:
    result = await service.execute_streaming(request)
    if not isinstance(result, Success):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.message,
        )
    data = result.value
    return {
        "execution_id": str(data["execution_id"]),
        "stream_session_id": str(data["stream_session_id"]),
        "status": "accepted",
    }


@router.get(
    "/execution/{execution_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get execution details",
    description="Retrieve the current state and results of a specific orchestration execution.",
)
async def get_execution(
    execution_id: UUID,
    execution_repo: ExecutionRepository = Depends(get_execution_repo),
) -> dict:
    result = await execution_repo.get_by_id(execution_id)
    if not isinstance(result, Success):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve execution",
        )
    execution = result.value
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {execution_id} not found",
        )

    steps_result = await execution_repo.get_steps_by_execution_id(execution_id)
    steps = steps_result.value if isinstance(steps_result, Success) else []

    return {
        "id": str(execution.id),
        "request_id": str(execution.request_id),
        "status": execution.status,
        "strategy": execution.strategy,
        "recommendation": execution.recommendation,
        "confidence": execution.confidence,
        "reasoning": execution.reasoning,
        "evidence": execution.evidence,
        "agents_used": execution.agents_used,
        "alternatives": execution.alternatives,
        "explanation": execution.explanation,
        "total_duration_ms": execution.total_duration_ms,
        "steps_completed": execution.steps_completed,
        "steps_failed": execution.steps_failed,
        "steps": [
            {
                "id": str(s.id),
                "agent_id": str(s.agent_id) if s.agent_id else None,
                "action": s.action,
                "status": s.status,
                "duration_ms": s.duration_ms,
                "error_message": s.error_message,
            }
            for s in steps
        ],
        "created_at": execution.created_at.isoformat() if execution.created_at else None,
    }


@router.post(
    "/cancel/{execution_id}",
    status_code=status.HTTP_200_OK,
    summary="Cancel execution",
    description="Cancel a running orchestration execution.",
)
async def cancel_execution(
    execution_id: UUID,
    service: OrchestrationService = Depends(get_orchestration_service),
) -> dict:
    result = await service.cancel(execution_id)
    if not isinstance(result, Success):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.message,
        )
    return {"execution_id": str(execution_id), "status": "cancelled"}


@router.get(
    "/history",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get execution history",
    description="Retrieve paginated execution history with optional filters.",
)
async def get_execution_history(
    status_filter: str | None = Query(
        None, alias="status",
        description="Filter by execution status",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    execution_repo: ExecutionRepository = Depends(get_execution_repo),
) -> dict:
    if status_filter:
        result = await execution_repo.get_by_status(
            status=status_filter, page=page, page_size=page_size,
        )
    else:
        result = await execution_repo.get_recent(limit=page_size)

    if not isinstance(result, Success):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve execution history",
        )

    if status_filter:
        executions, total = result.value
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    else:
        executions = result.value
        total = len(executions)
        total_pages = 1

    items = [
        {
            "id": str(e.id),
            "request_id": str(e.request_id),
            "status": e.status,
            "recommendation": e.recommendation,
            "confidence": e.confidence,
            "total_duration_ms": e.total_duration_ms,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in executions
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get(
    "/decisions/{request_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get decision history for a request",
    description="Retrieve the decision ledger entries associated with a specific request.",
)
async def get_decision_history(
    request_id: UUID,
    decision_repo: DecisionLedgerRepository = Depends(get_decision_ledger_repo),
) -> dict:
    result = await decision_repo.get_by_request_id(request_id)
    if not isinstance(result, Success):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve decision history",
        )

    entries = result.value
    items = [
        {
            "id": str(e.id),
            "execution_id": str(e.execution_id),
            "request_id": str(e.request_id),
            "decision": e.decision,
            "reasoning": e.reasoning,
            "confidence": e.confidence,
            "agents_involved": e.agents_involved,
            "safety_level": e.safety_level,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]

    return {"items": items, "total": len(items)}
