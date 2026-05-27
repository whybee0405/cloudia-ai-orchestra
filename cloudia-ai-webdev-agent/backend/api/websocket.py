"""
WebSocket endpoint for real-time project pipeline events.

Each project has its own connection channel. The operator GUI subscribes to
``/ws/projects/{project_id}`` and receives JSON events as pipeline stages
complete, gates open, or tasks fail.

Event shapes:
    {"event": "task_started",   "agent": "content_agent", "task_id": 3}
    {"event": "task_completed", "agent": "content_agent", "task_id": 3, "cost_usd": 0.0034}
    {"event": "gate_created",   "gate": "content_review", "gate_id": 1}
    {"event": "task_failed",    "agent": "wp_builder",    "error": "REST API auth failed"}

``send_project_event`` is async and is called from async FastAPI context.
``send_project_event_sync`` is a safe wrapper for Celery task (sync) context.
"""

from __future__ import annotations

import asyncio
from typing import Optional

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

log = structlog.get_logger()

router = APIRouter()

# Active WebSocket connections per project_id.
# Key: project_id, Value: list of connected WebSocket instances.
_connections: dict[int, list[WebSocket]] = {}


async def send_project_event(project_id: int, event: dict) -> None:
    """Push a JSON event to all connected clients for a project.

    Dead connections are removed from the pool silently. WebSocket failures
    must never propagate up to the calling pipeline task.

    Args:
        project_id: The project whose subscribers should receive the event.
        event:      A JSON-serialisable dict with at minimum an ``"event"`` key.
    """
    connections = _connections.get(project_id, [])
    if not connections:
        return

    dead: list[WebSocket] = []
    for ws in list(connections):
        try:
            await ws.send_json(event)
        except Exception as exc:
            log.debug(
                "ws_send_failed",
                project_id=project_id,
                error=str(exc),
            )
            dead.append(ws)

    for ws in dead:
        try:
            connections.remove(ws)
        except ValueError:
            pass  # Already removed by a concurrent disconnect


def send_project_event_sync(project_id: int, event: dict) -> None:
    """Sync wrapper for Celery tasks — never raises.

    Attempts to push the event to connected WebSocket clients from a
    synchronous context (Celery worker). If no event loop exists, one is
    created. If anything goes wrong, the error is logged but not re-raised
    so that WebSocket failures never crash the pipeline.

    Args:
        project_id: Target project ID.
        event:      JSON-serialisable event dict.
    """
    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # No current event loop — create a new one (Celery worker thread)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # We're inside an async context already — schedule as a task
            loop.create_task(send_project_event(project_id, event))
        else:
            loop.run_until_complete(send_project_event(project_id, event))
    except Exception as exc:
        # WebSocket failures must never crash the pipeline
        log.debug(
            "ws_sync_send_failed",
            project_id=project_id,
            error=str(exc),
        )


@router.websocket("/ws/projects/{project_id}")
async def project_websocket(websocket: WebSocket, project_id: int) -> None:
    """WebSocket endpoint for real-time project event streaming.

    Clients connect here and receive JSON events as the pipeline executes.
    They can send ``"ping"`` messages to keep the connection alive; the server
    echoes back ``{"event": "pong"}``.

    No authentication is enforced on this endpoint — it relies on the
    project_id being non-guessable in practice (internal tool). If stronger
    isolation is needed, pass a short-lived token as a query parameter.
    """
    await websocket.accept()
    _connections.setdefault(project_id, []).append(websocket)
    log.info("ws_connected", project_id=project_id)

    try:
        while True:
            data = await websocket.receive_text()
            if data.strip().lower() == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        log.info("ws_disconnected", project_id=project_id)
    except Exception as exc:
        log.warning("ws_error", project_id=project_id, error=str(exc))
    finally:
        conns = _connections.get(project_id, [])
        try:
            conns.remove(websocket)
        except ValueError:
            pass
