"""WebSocket handler for real-time intelligence updates."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

MAX_CONNECTIONS_PER_CLIENT = 5
MAX_TOTAL_CONNECTIONS = 500
PING_INTERVAL_SECONDS = 30
PONG_TIMEOUT_SECONDS = 10
MAX_MESSAGE_BYTES = 4096


class IntelligenceConnectionManager:
    """Manages WebSocket connections for live intelligence updates.

    Supports per-venue subscriptions for risk updates, new predictions,
    and intervention recommendations.
    """

    def __init__(self) -> None:
        self._venue_connections: dict[str, list[WebSocket]] = defaultdict(list)
        self._all_connections: list[WebSocket] = []
        self._connection_tasks: dict[WebSocket, asyncio.Task[None]] = {}

    async def connect(self, websocket: WebSocket) -> bool:
        """Accept a new WebSocket connection. Returns False if at capacity."""
        if len(self._all_connections) >= MAX_TOTAL_CONNECTIONS:
            await websocket.close(code=4029, reason="Connection limit reached")
            return False

        await websocket.accept()
        self._all_connections.append(websocket)
        self._start_heartbeat(websocket)
        logger.info(
            "Intelligence WS client connected (total=%d)",
            len(self._all_connections),
        )
        return True

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a disconnected WebSocket and cancel its heartbeat."""
        task = self._connection_tasks.pop(websocket, None)
        if task and not task.done():
            task.cancel()

        if websocket in self._all_connections:
            self._all_connections.remove(websocket)
        for conns in self._venue_connections.values():
            if websocket in conns:
                conns.remove(websocket)

    def subscribe_venue(self, websocket: WebSocket, venue_id: str) -> None:
        """Subscribe a client to intelligence updates for a venue."""
        if websocket not in self._venue_connections[venue_id]:
            self._venue_connections[venue_id].append(websocket)

    def unsubscribe_venue(self, websocket: WebSocket, venue_id: str) -> None:
        """Unsubscribe a client from venue updates."""
        if websocket in self._venue_connections.get(venue_id, []):
            self._venue_connections[venue_id].remove(websocket)

    async def broadcast_to_venue(self, venue_id: str, event: dict) -> None:
        """Send an event to all clients subscribed to a venue."""
        dead: list[WebSocket] = []
        for ws in self._venue_connections.get(venue_id, []):
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._venue_connections[venue_id].remove(ws)

    async def broadcast_risk_update(
        self, venue_id: str, risk_data: dict,
    ) -> None:
        """Broadcast a risk update to venue subscribers."""
        await self.broadcast_to_venue(venue_id, {
            "type": "risk_update",
            "venue_id": venue_id,
            "data": risk_data,
        })

    async def broadcast_prediction(
        self, venue_id: str, prediction_data: dict,
    ) -> None:
        """Broadcast a new prediction to venue subscribers."""
        await self.broadcast_to_venue(venue_id, {
            "type": "new_prediction",
            "venue_id": venue_id,
            "data": prediction_data,
        })

    async def broadcast_recommendation(
        self, venue_id: str, recommendation_data: dict,
    ) -> None:
        """Broadcast an intervention recommendation to venue subscribers."""
        await self.broadcast_to_venue(venue_id, {
            "type": "recommendation",
            "venue_id": venue_id,
            "data": recommendation_data,
        })

    def _start_heartbeat(self, websocket: WebSocket) -> None:
        """Start a periodic ping task for a WebSocket connection."""
        task = asyncio.create_task(self._heartbeat_loop(websocket))
        self._connection_tasks[websocket] = task

    async def _heartbeat_loop(self, websocket: WebSocket) -> None:
        """Send periodic pings and disconnect on pong timeout."""
        try:
            while True:
                await asyncio.sleep(PING_INTERVAL_SECONDS)
                try:
                    await asyncio.wait_for(
                        websocket.send_json({"type": "ping"}),
                        timeout=PONG_TIMEOUT_SECONDS,
                    )
                except (asyncio.TimeoutError, Exception):
                    logger.info("Heartbeat failed for Intelligence WS, disconnecting")
                    self.disconnect(websocket)
                    await websocket.close(code=4000, reason="Heartbeat timeout")
                    break
        except asyncio.CancelledError:
            pass

    @property
    def active_connections(self) -> int:
        return len(self._all_connections)


intelligence_ws_manager = IntelligenceConnectionManager()


async def intelligence_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time intelligence updates.

    Requires JWT authentication via query parameter token=<jwt>.
    Protocol:
    - Client connects to /ws/intelligence?token=<jwt>
    - Client sends JSON to subscribe:
      {"action": "subscribe_venue", "venue_id": "..."}
    - Client sends JSON to unsubscribe:
      {"action": "unsubscribe_venue", "venue_id": "..."}
    - Server pushes: risk_update, new_prediction, recommendation events.
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

    connected = await intelligence_ws_manager.connect(websocket)
    if not connected:
        return

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
            if action == "subscribe_venue":
                venue_id = msg.get("venue_id")
                if venue_id:
                    intelligence_ws_manager.subscribe_venue(websocket, venue_id)
                    await websocket.send_json({
                        "status": "subscribed",
                        "type": "venue",
                        "venue_id": venue_id,
                    })
            elif action == "unsubscribe_venue":
                venue_id = msg.get("venue_id")
                if venue_id:
                    intelligence_ws_manager.unsubscribe_venue(websocket, venue_id)
                    await websocket.send_json({
                        "status": "unsubscribed",
                        "type": "venue",
                        "venue_id": venue_id,
                    })
            else:
                await websocket.send_json({
                    "error": f"Unknown action: {action}",
                })

    except WebSocketDisconnect:
        intelligence_ws_manager.disconnect(websocket)
        logger.info(
            "Intelligence WS client disconnected (total=%d)",
            intelligence_ws_manager.active_connections,
        )
