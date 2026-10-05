"""Phase 1: workspace + compilation endpoints (Engine A + Engine B)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import compiler, workspace
from ..ollama_client import OllamaClient, parse_fenced_files
from ..stream_hub import hub

router = APIRouter(prefix="/apps", tags=["apps"])


class CreateAppRequest(BaseModel):
    prompt: str


class PromptUpdateRequest(BaseModel):
    prompt: str


@router.post("")
async def create_app(req: CreateAppRequest):
    client = OllamaClient()
    guard = await client.check_intent(req.prompt)
    if not guard["safe"]:
        raise HTTPException(status_code=400, detail=f"Prompt blocked by intent guard: {guard['raw']}")

    ws = workspace.create_workspace(req.prompt)
    await hub.log(f"[{ws.app_id}] workspace scaffolded at {ws.path}")

    asyncio.create_task(_install_and_run(ws.app_id))
    return {"app_id": ws.app_id, "port": ws.port, "status": ws.status}


async def _install_and_run(app_id: str) -> None:
    ws = workspace.get_workspace(app_id)
    if ws is None:
        return
    ws.status = "installing"
    ok, _ = await compiler.npm_install(ws, hub.log)
    if not ok:
        ws.status = "error"
        await hub.log(f"[{app_id}] npm install failed.")
        return
    healed = await compiler.self_heal_loop(ws, hub.log)
    if not healed:
        ws.status = "error"
        return
    await compiler.start_dev_server(ws, hub.log)


@router.get("")
async def list_apps():
    return [
        {"app_id": ws.app_id, "port": ws.port, "status": ws.status}
        for ws in workspace.list_workspaces()
    ]


@router.get("/{app_id}")
async def get_app(app_id: str):
    ws = workspace.get_workspace(app_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="app not found")
    return {
        "app_id": ws.app_id,
        "port": ws.port,
        "status": ws.status,
        "prompt_history": ws.prompt_history,
    }


@router.post("/{app_id}/prompt")
async def update_app(app_id: str, req: PromptUpdateRequest):
    """Component Generator Module: structure a prompt, get back one or more
    files from the coder model, write them, and re-run the self-heal loop."""
    ws = workspace.get_workspace(app_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="app not found")

    client = OllamaClient()
    guard = await client.check_intent(req.prompt)
    if not guard["safe"]:
        raise HTTPException(status_code=400, detail=f"Prompt blocked by intent guard: {guard['raw']}")

    ws.prompt_history.append(req.prompt)
    await hub.log(f"[{app_id}] generating code for prompt: {req.prompt}")

    structured_prompt = (
        f"Project: Vite + React + TypeScript + Tailwind app (src/ directory).\n"
        f"Request: {req.prompt}\n"
        "Output the full contents of every file you create or modify."
    )
    response = await client.generate_code(structured_prompt)
    files = parse_fenced_files(response)
    if not files:
        raise HTTPException(status_code=502, detail="Model response contained no parseable files.")

    written = workspace.write_files(ws.path, files)
    await hub.log(f"[{app_id}] wrote files: {written}")

    healed = await compiler.self_heal_loop(ws, hub.log)
    return {"app_id": app_id, "files_written": written, "compiled": healed}


@router.post("/{app_id}/stop")
async def stop_app(app_id: str):
    ws = workspace.get_workspace(app_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="app not found")
    compiler.stop_dev_server(ws)
    return {"app_id": app_id, "status": ws.status}
