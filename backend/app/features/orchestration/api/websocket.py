"""WebSocket handler for real-time orchestration progress streaming."""

from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

from app.features.orchestration.api.deps import get_streaming_manager

logger = logging.getLogger(__name__)

MAX_CONNECTIONS_PER_CLIENT = 3
MAX_TOTAL_CONNECTIONS = 200
PING_INTERVAL_SECONDS = 30
PONG_TIMEOUT_SECONDS = 10
MAX_MESSAGE_BYTES = 4096


class OrchestrationConnectionManager:
    """Manages WebSocket connections for live orchestration progress updates."""

    def __init__(self) -> None:
        self._execution_connections: dict[UUID, list[WebSocket]] = {}
        self._all_connections: list[WebSocket] = []
        self._connection_tasks: dict[WebSocket, asyncio.Task[None]] = {}

    async def connect(self, websocket: WebSocket) -> bool:
        if len(self._all_connections) >= MAX_TOTAL_CONNECTIONS:
            await websocket.close(code=4029, reason="Connection limit reached")
            return False

        await websocket.accept()
        self._all_connections.append(websocket)
        self._start_heartbeat(websocket)
        logger.info(
            "Orchestration WS client connected (total=%d)",
            len(self._all_connections),
        )
        return True

    def disconnect(self, websocket: WebSocket) -> None:
        task = self._connection_tasks.pop(websocket, None)
        if task and not task.done():
            task.cancel()

        if websocket in self._all_connections:
            self._all_connections.remove(websocket)
        for _, conns in self._execution_connections.items():
            if websocket in conns:
                conns.remove(websocket)

    def subscribe_execution(self, websocket: WebSocket, execution_id: UUID) -> None:
        if execution_id not in self._execution_connections:
            self._execution_connections[execution_id] = []
        if websocket not in self._execution_connections[execution_id]:
            self._execution_connections[execution_id].append(websocket)

    def unsubscribe_execution(self, websocket: WebSocket, execution_id: UUID) -> None:
        conns = self._execution_connections.get(execution_id, [])
        if websocket in conns:
            conns.remove(websocket)

    async def broadcast_to_execution(self, execution_id: UUID, event: dict) -> None:
        dead: list[WebSocket] = []
        for ws in self._execution_connections.get(execution_id, []):
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._execution_connections[execution_id].remove(ws)

    async def send_to_client(self, websocket: WebSocket, event: dict) -> None:
        try:
            await websocket.send_json(event)
        except Exception:
            self.disconnect(websocket)

    def _start_heartbeat(self, websocket: WebSocket) -> None:
        task = asyncio.create_task(self._heartbeat_loop(websocket))
        self._connection_tasks[websocket] = task

    async def _heartbeat_loop(self, websocket: WebSocket) -> None:
        try:
            while True:
                await asyncio.sleep(PING_INTERVAL_SECONDS)
                try:
                    await asyncio.wait_for(
                        websocket.send_json({"type": "ping"}),
                        timeout=PONG_TIMEOUT_SECONDS,
                    )
                except (TimeoutError, Exception):
                    logger.info(
                        "Heartbeat failed for Orchestration WS, disconnecting",
                    )
                    self.disconnect(websocket)
                    await websocket.close(code=4000, reason="Heartbeat timeout")
                    break
        except asyncio.CancelledError:
            pass

    @property
    def active_connections(self) -> int:
        return len(self._all_connections)


orchestration_ws_manager = OrchestrationConnectionManager()


async def orchestration_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time orchestration progress streaming.

    Protocol:
    - Client connects to /ws/orchestration?execution_id=<uuid>&token=<jwt>
    - Client sends JSON to subscribe:
      {"action": "subscribe_execution", "execution_id": "..."}
    - Client sends JSON to unsubscribe:
      {"action": "unsubscribe_execution", "execution_id": "..."}
    - Client sends {"action": "cancel", "execution_id": "..."} to cancel.
    - Server pushes: progress, agent_status, partial_result, complete events.
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    from app.features.auth.services.token_service import TokenService

    token_service = TokenService()
    payload = token_service.verify_access_token(token)
    if payload is None:
        await websocket.close(code=4003, reason="Invalid or expired token")
        return

    connected = await orchestration_ws_manager.connect(websocket)
    if not connected:
        return

    execution_id_param = websocket.query_params.get("execution_id")
    if execution_id_param:
        try:
            execution_id = UUID(execution_id_param)
            orchestration_ws_manager.subscribe_execution(websocket, execution_id)
            await websocket.send_json({
                "status": "subscribed",
                "execution_id": str(execution_id),
            })
        except ValueError:
            await websocket.send_json({"error": "Invalid execution_id format"})

    _streaming_mgr = get_streaming_manager()

    try:
        while True:
            raw = await websocket.receive_text()
            if len(raw.encode("utf-8")) > MAX_MESSAGE_BYTES:
                await websocket.send_json({"error": "Message too large"})
                continue

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
                continue

            action = msg.get("action")

            if action == "subscribe_execution":
                exec_id_str = msg.get("execution_id")
                if exec_id_str:
                    try:
                        exec_uuid = UUID(exec_id_str)
                        orchestration_ws_manager.subscribe_execution(websocket, exec_uuid)
                        await websocket.send_json({
                            "status": "subscribed",
                            "type": "execution",
                            "execution_id": exec_id_str,
                        })
                    except ValueError:
                        await websocket.send_json({"error": "Invalid execution_id"})
                else:
                    await websocket.send_json({"error": "execution_id required"})

            elif action == "unsubscribe_execution":
                exec_id_str = msg.get("execution_id")
                if exec_id_str:
                    try:
                        exec_uuid = UUID(exec_id_str)
                        orchestration_ws_manager.unsubscribe_execution(websocket, exec_uuid)
                        await websocket.send_json({
                            "status": "unsubscribed",
                            "type": "execution",
                            "execution_id": exec_id_str,
                        })
                    except ValueError:
                        await websocket.send_json({"error": "Invalid execution_id"})

            elif action == "cancel":
                exec_id_str = msg.get("execution_id")
                if exec_id_str:
                    await websocket.send_json({
                        "status": "cancel_requested",
                        "execution_id": exec_id_str,
                    })
                    await orchestration_ws_manager.broadcast_to_execution(
                        UUID(exec_id_str),
                        {
                            "type": "cancel_requested",
                            "execution_id": exec_id_str,
                        },
                    )

            else:
                await websocket.send_json({
                    "error": f"Unknown action: {action}",
                })

    except WebSocketDisconnect:
        orchestration_ws_manager.disconnect(websocket)
        logger.info(
            "Orchestration WS client disconnected (total=%d)",
            orchestration_ws_manager.active_connections,
        )
