"""Engine B: hot-reload server spawning + self-healing compiler loop."""
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import AsyncIterator, Callable, Awaitable

from . import config
from .ollama_client import OllamaClient, parse_fenced_files
from .workspace import AppWorkspace, write_files

LogFn = Callable[[str], Awaitable[None]]

_RUNNING_PROCS: dict[str, asyncio.subprocess.Process] = {}


async def npm_install(ws: AppWorkspace, log: LogFn) -> tuple[bool, str]:
    await log(f"[{ws.app_id}] running npm install...")
    proc = await asyncio.create_subprocess_exec(
        "npm", "install",
        cwd=str(ws.path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    out = await proc.stdout.read()
    await proc.wait()
    text = out.decode(errors="replace")
    ok = proc.returncode == 0
    await log(text[-4000:])
    return ok, text


async def typecheck(ws: AppWorkspace, log: LogFn) -> tuple[bool, str]:
    """Run `tsc --noEmit` as the compile-error catcher (fast, no server needed)."""
    await log(f"[{ws.app_id}] type-checking...")
    proc = await asyncio.create_subprocess_exec(
        "npx", "tsc", "--noEmit",
        cwd=str(ws.path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    out = await proc.stdout.read()
    await proc.wait()
    text = out.decode(errors="replace")
    ok = proc.returncode == 0
    return ok, text


def _guess_failing_file(ws: AppWorkspace, error_text: str) -> Path | None:
    for line in error_text.splitlines():
        line = line.strip()
        if line.startswith("src/") and (".ts" in line or ".tsx" in line):
            candidate = ws.path / line.split("(")[0].split(":")[0].strip()
            if candidate.exists():
                return candidate
    return None


async def self_heal_loop(ws: AppWorkspace, log: LogFn) -> bool:
    """Up to MAX_SELF_HEAL_ATTEMPTS: typecheck -> on failure, ask the coder model
    to rewrite the offending file -> retry."""
    client = OllamaClient()
    for attempt in range(1, config.MAX_SELF_HEAL_ATTEMPTS + 1):
        ok, output = await typecheck(ws, log)
        if ok:
            await log(f"[{ws.app_id}] compile clean (attempt {attempt}).")
            return True

        await log(f"[{ws.app_id}] compile FAILED (attempt {attempt}/{config.MAX_SELF_HEAL_ATTEMPTS}):\n{output[-2000:]}")
        failing_file = _guess_failing_file(ws, output)
        if failing_file is None:
            await log(f"[{ws.app_id}] could not identify failing file from error output; stopping self-heal.")
            return False

        current_contents = failing_file.read_text()
        rel_path = str(failing_file.relative_to(ws.path))
        try:
            repaired = await client.repair_code(rel_path, current_contents, output[-3000:])
        except Exception as exc:  # noqa: BLE001
            await log(f"[{ws.app_id}] repair model call failed: {exc}")
            return False

        files = parse_fenced_files(repaired)
        if rel_path in files:
            write_files(ws.path, {rel_path: files[rel_path]})
            await log(f"[{ws.app_id}] applied model-suggested fix to {rel_path}.")
        else:
            await log(f"[{ws.app_id}] repair response did not contain a usable fix for {rel_path}.")
            return False

    await log(f"[{ws.app_id}] exhausted {config.MAX_SELF_HEAL_ATTEMPTS} self-heal attempts.")
    return False


async def start_dev_server(ws: AppWorkspace, log: LogFn) -> None:
    if ws.app_id in _RUNNING_PROCS:
        await log(f"[{ws.app_id}] dev server already running.")
        return
    await log(f"[{ws.app_id}] starting dev server on port {ws.port}...")
    proc = await asyncio.create_subprocess_exec(
        "npm", "run", "dev",
        cwd=str(ws.path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    _RUNNING_PROCS[ws.app_id] = proc
    ws.status = "running"

    async def _pump() -> None:
        assert proc.stdout is not None
        async for line in proc.stdout:
            await log(line.decode(errors="replace").rstrip())

    asyncio.create_task(_pump())


def stop_dev_server(ws: AppWorkspace) -> None:
    proc = _RUNNING_PROCS.pop(ws.app_id, None)
    if proc and proc.returncode is None:
        proc.terminate()
    ws.status = "stopped"
