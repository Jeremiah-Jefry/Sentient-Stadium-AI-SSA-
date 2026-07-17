"""WebSocket handler for real-time event streaming."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

MAX_CONNECTIONS_PER_CLIENT = 5
MAX_TOTAL_CONNECTIONS = 1000
PING_INTERVAL_SECONDS = 30
PONG_TIMEOUT_SECONDS = 10


class EventStreamConnectionManager:
    """Manages WebSocket connections for the event streaming platform.

    Supports per-venue, per-category, and per-entity subscriptions.
    Includes heartbeat ping/pong, connection limits, and proper unsubscription.
    """

    def __init__(self) -> None:
        self._venue_connections: dict[str, list[WebSocket]] = defaultdict(list)
        self._entity_connections: dict[str, list[WebSocket]] = defaultdict(list)
        self._category_connections: dict[str, list[WebSocket]] = defaultdict(list)
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
        logger.info("Event stream client connected (total=%d)", len(self._all_connections))
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
        for conns in self._entity_connections.values():
            if websocket in conns:
                conns.remove(websocket)
        for conns in self._category_connections.values():
            if websocket in conns:
                conns.remove(websocket)

    def subscribe_venue(self, websocket: WebSocket, venue_id: str) -> None:
        if websocket not in self._venue_connections[venue_id]:
            self._venue_connections[venue_id].append(websocket)

    def subscribe_entity(self, websocket: WebSocket, entity_id: str) -> None:
        if websocket not in self._entity_connections[entity_id]:
            self._entity_connections[entity_id].append(websocket)

    def subscribe_category(self, websocket: WebSocket, category: str) -> None:
        if websocket not in self._category_connections[category]:
            self._category_connections[category].append(websocket)

    def unsubscribe_venue(self, websocket: WebSocket, venue_id: str) -> None:
        if websocket in self._venue_connections.get(venue_id, []):
            self._venue_connections[venue_id].remove(websocket)

    def unsubscribe_entity(self, websocket: WebSocket, entity_id: str) -> None:
        if websocket in self._entity_connections.get(entity_id, []):
            self._entity_connections[entity_id].remove(websocket)

    def unsubscribe_category(self, websocket: WebSocket, category: str) -> None:
        if websocket in self._category_connections.get(category, []):
            self._category_connections[category].remove(websocket)

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

    async def broadcast_to_entity(self, entity_id: str, event: dict) -> None:
        """Send an event to all clients subscribed to a specific entity."""
        dead: list[WebSocket] = []
        for ws in self._entity_connections.get(entity_id, []):
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._entity_connections[entity_id].remove(ws)

    async def broadcast_to_category(self, category: str, event: dict) -> None:
        """Send an event to all clients subscribed to a category."""
        dead: list[WebSocket] = []
        for ws in self._category_connections.get(category, []):
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._category_connections[category].remove(ws)

    async def broadcast_all(self, event: dict) -> None:
        """Send an event to all connected clients."""
        dead: list[WebSocket] = []
        for ws in self._all_connections:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._all_connections.remove(ws)

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
                    logger.info("Heartbeat failed for WebSocket, disconnecting")
                    self.disconnect(websocket)
                    await websocket.close(code=4000, reason="Heartbeat timeout")
                    break
        except asyncio.CancelledError:
            pass

    @property
    def active_connections(self) -> int:
        return len(self._all_connections)


event_stream_manager = EventStreamConnectionManager()


async def event_stream_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time event streaming.

    Requires JWT authentication via query parameter token=<jwt>.
    Protocol:
    - Client connects to /ws/events?token=<jwt>
    - Client sends JSON to subscribe:
      {"action": "subscribe_venue", "venue_id": "..."}
      {"action": "subscribe_category", "category": "crowd"}
      {"action": "subscribe_entity", "entity_id": "..."}
    - Client sends JSON to unsubscribe:
      {"action": "unsubscribe_venue", "venue_id": "..."}
    - Server pushes events as they occur.
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

    connected = await event_stream_manager.connect(websocket)
    if not connected:
        return

    max_message_bytes = 4096

    try:
        while True:
            raw = await websocket.receive_text()
            if len(raw.encode("utf-8")) > max_message_bytes:
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
                    event_stream_manager.subscribe_venue(websocket, venue_id)
                    await websocket.send_json({
                        "status": "subscribed", "type": "venue", "venue_id": venue_id,
                    })
            elif action == "subscribe_category":
                category = msg.get("category")
                if category:
                    event_stream_manager.subscribe_category(websocket, category)
                    await websocket.send_json({
                        "status": "subscribed", "type": "category", "category": category,
                    })
            elif action == "subscribe_entity":
                entity_id = msg.get("entity_id")
                if entity_id:
                    event_stream_manager.subscribe_entity(websocket, entity_id)
                    await websocket.send_json({
                        "status": "subscribed", "type": "entity", "entity_id": entity_id,
                    })
            elif action == "unsubscribe_venue":
                venue_id = msg.get("venue_id")
                if venue_id:
                    event_stream_manager.unsubscribe_venue(websocket, venue_id)
                    await websocket.send_json({
                        "status": "unsubscribed", "type": "venue", "venue_id": venue_id,
                    })
            elif action == "unsubscribe_entity":
                entity_id = msg.get("entity_id")
                if entity_id:
                    event_stream_manager.unsubscribe_entity(websocket, entity_id)
                    await websocket.send_json({
                        "status": "unsubscribed", "type": "entity", "entity_id": entity_id,
                    })
            elif action == "unsubscribe_category":
                category = msg.get("category")
                if category:
                    event_stream_manager.unsubscribe_category(websocket, category)
                    await websocket.send_json({
                        "status": "unsubscribed", "type": "category", "category": category,
                    })
            else:
                await websocket.send_json({"error": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        event_stream_manager.disconnect(websocket)
        logger.info(
            "Event stream client disconnected (total=%d)",
            event_stream_manager.active_connections,
        )
