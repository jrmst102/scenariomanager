"""WebSocket routes for real-time status updates."""

import json
import logging
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.auth.login_manager import decode_jwt

router = APIRouter()
logger = logging.getLogger(__name__)

# Active connections per problem
_connections: Dict[str, Set[WebSocket]] = {}


@router.websocket("/ws/problems/{problem_id}/status")
async def problem_status_ws(websocket: WebSocket, problem_id: str):
    """WebSocket endpoint for real-time participant status updates.

    Requires JWT authentication via query parameter or cookie.
    """
    # Authenticate
    token = websocket.query_params.get("token") or websocket.cookies.get("session")
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    try:
        payload = decode_jwt(token)
        if "userId" not in payload:
            await websocket.close(code=4001, reason="Invalid authentication")
            return
    except Exception:
        await websocket.close(code=4001, reason="Invalid authentication")
        return

    await websocket.accept()

    # Register connection
    if problem_id not in _connections:
        _connections[problem_id] = set()
    _connections[problem_id].add(websocket)

    try:
        while True:
            # Keep connection alive, listen for pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        _connections[problem_id].discard(websocket)
        if not _connections[problem_id]:
            del _connections[problem_id]


async def broadcast_status(problem_id: str, event: dict) -> None:
    """Broadcast a status update to all connected clients for a problem."""
    if problem_id not in _connections:
        return
    message = json.dumps(event)
    disconnected = set()
    for ws in _connections[problem_id]:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.add(ws)
    _connections[problem_id] -= disconnected
