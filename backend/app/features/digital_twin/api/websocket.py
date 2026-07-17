"""WebSocket handler for real-time entity state updates."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections import defaultdict

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time entity state streaming.

    Supports per-venue and per-entity subscriptions.
    Clients receive state change events as JSON messages.
    """

    def __init__(self) -> None:
        self._venue_connections: dict[str, list[WebSocket]] = defaultdict(list)
        self._entity_connections: dict[str, list[WebSocket]] = defaultdict(list)
        self._all_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self._all_connections.append(websocket)
        logger.info("WebSocket client connected (total=%d)", len(self._all_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a disconnected WebSocket."""
        if websocket in self._all_connections:
            self._all_connections.remove(websocket)
        for venue_conns in self._venue_connections.values():
            if websocket in venue_conns:
                venue_conns.remove(websocket)
        for entity_conns in self._entity_connections.values():
            if websocket in entity_conns:
                entity_conns.remove(websocket)

    def subscribe_venue(self, websocket: WebSocket, venue_id: str) -> None:
        """Subscribe to all events for a venue."""
        self._venue_connections[venue_id].append(websocket)

    def subscribe_entity(self, websocket: WebSocket, entity_id: str) -> None:
        """Subscribe to events for a specific entity."""
        self._entity_connections[entity_id].append(websocket)

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

    @property
    def active_connections(self) -> int:
        return len(self._all_connections)


manager = ConnectionManager()


async def digital_twin_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint handler for digital twin real-time updates.

    Requires JWT authentication via query parameter token=<jwt>.
    Protocol:
    - Client connects to /ws/digital-twin?token=<jwt>
    - Client sends JSON messages to subscribe:
      {"action": "subscribe_venue", "venue_id": "..."}
      {"action": "subscribe_entity", "entity_id": "..."}
      {"action": "unsubscribe_venue", "venue_id": "..."}
    - Server pushes events as they occur.
    """
    # Authenticate via query parameter token
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    # Verify JWT token
    from app.features.auth.services.token_service import TokenService

    token_service = TokenService()
    payload = token_service.verify_access_token(token)
    if payload is None:
        await websocket.close(code=4003, reason="Invalid or expired token")
        return

    await manager.connect(websocket)
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
                    manager.subscribe_venue(websocket, venue_id)
                    await websocket.send_json({
                        "status": "subscribed", "type": "venue", "venue_id": venue_id,
                    })
            elif action == "subscribe_entity":
                entity_id = msg.get("entity_id")
                if entity_id:
                    manager.subscribe_entity(websocket, entity_id)
                    await websocket.send_json({
                        "status": "subscribed", "type": "entity", "entity_id": entity_id,
                    })
            elif action in ("unsubscribe_venue", "unsubscribe_entity"):
                await websocket.send_json({"status": "unsubscribed", "action": action})
            else:
                await websocket.send_json({"error": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected (total=%d)", manager.active_connections)
