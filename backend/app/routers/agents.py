"""Agent Thought & Activity Stream (WebSocket) + Human-in-the-Loop approval gate,
plus the engagement-gated pipeline endpoints."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .. import workspace
from ..agents import engagement as engagement_mod
from ..agents import orchestrator
from ..stream_hub import hub

router = APIRouter(tags=["agents"])


@router.websocket("/ws/agent-stream")
async def agent_stream(ws: WebSocket) -> None:
    await hub.connect(ws)
    try:
        while True:
            # Client -> server messages are approval responses:
            # {"type": "approval_response", "id": "...", "approved": true}
            msg = await ws.receive_json()
            if msg.get("type") == "approval_response":
                hub.resolve_approval(msg["id"], bool(msg.get("approved")))
    except WebSocketDisconnect:
        hub.disconnect(ws)


class EngagementRequest(BaseModel):
    target: str
    authorized_by: str
    scope_notes: str = ""
    confirmed: bool


@router.post("/engagements")
async def create_engagement(req: EngagementRequest):
    """Must be called with confirmed=true reflecting an explicit human
    checkbox click in the UI before any external pipeline can run."""
    try:
        eng = engagement_mod.create_engagement(
            target=req.target,
            authorized_by=req.authorized_by,
            scope_notes=req.scope_notes,
            confirmed=req.confirmed,
        )
    except engagement_mod.EngagementError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"engagement_id": eng.id, "target": eng.target}


@router.post("/apps/{app_id}/scan")
async def scan_sandbox_app(app_id: str):
    ws = workspace.get_workspace(app_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="app not found")
    asyncio.create_task(orchestrator.run_sandbox_pipeline(ws))
    return {"app_id": app_id, "status": "pipeline started"}


class ExternalScanRequest(BaseModel):
    engagement_id: str


@router.post("/engagements/{engagement_id}/scan")
async def scan_external_target(engagement_id: str):
    eng = engagement_mod.get_engagement(engagement_id)
    if eng is None:
        raise HTTPException(status_code=400, detail="No valid, confirmed engagement found for that id.")
    asyncio.create_task(orchestrator.run_external_pipeline(eng))
    return {"engagement_id": engagement_id, "target": eng.target, "status": "pipeline started"}
