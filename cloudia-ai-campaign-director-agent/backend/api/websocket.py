import asyncio
import json
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from backend.db.session import SessionLocal
from backend.db.models import AgentTask, Campaign


def _serialize(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _task_snapshot(db: Session, campaign_id: int) -> list[dict]:
    tasks = (
        db.query(AgentTask)
        .filter(AgentTask.campaign_id == campaign_id)
        .order_by(AgentTask.pipeline_order)
        .all()
    )
    return [
        {
            "id": t.id,
            "agent_name": t.agent_name,
            "pipeline_order": t.pipeline_order,
            "status": t.status,
            "started_at": _serialize(t.started_at),
            "completed_at": _serialize(t.completed_at),
            "error": t.error,
            "retry_count": t.retry_count,
        }
        for t in tasks
    ]


async def pipeline_ws(websocket: WebSocket, campaign_id: int) -> None:
    await websocket.accept()

    db = SessionLocal()
    try:
        campaign = db.get(Campaign, campaign_id)
        if not campaign:
            await websocket.send_text(json.dumps({"error": "Campaign not found"}))
            await websocket.close(code=1008)
            return

        snapshot = _task_snapshot(db, campaign_id)
        await websocket.send_text(
            json.dumps({"event": "init", "campaign_id": campaign_id, "tasks": snapshot})
        )

        prev_statuses = {t["id"]: t["status"] for t in snapshot}

        while True:
            await asyncio.sleep(3)

            try:
                db.expire_all()
                current = _task_snapshot(db, campaign_id)
            except Exception:
                break

            changed = []
            current_map = {t["id"]: t for t in current}
            for task in current:
                prev = prev_statuses.get(task["id"])
                if prev != task["status"]:
                    changed.append(task)
                    prev_statuses[task["id"]] = task["status"]
            for tid in list(prev_statuses):
                if tid not in current_map:
                    del prev_statuses[tid]

            if changed:
                await websocket.send_text(
                    json.dumps(
                        {"event": "update", "campaign_id": campaign_id, "tasks": changed}
                    )
                )

            all_done = all(
                t["status"] in ("completed", "failed") for t in current
            )
            if all_done and current:
                await websocket.send_text(
                    json.dumps({"event": "pipeline_complete", "campaign_id": campaign_id})
                )
                break

    except WebSocketDisconnect:
        pass
    finally:
        db.close()
