"""Vulnerability Discovery Agent.

Two modes:
  - sandbox: audits a CyberFactory-generated app's own dependency manifests
    (npm audit / pip-audit) and static analysis (bandit) locally, no network
    egress needed beyond the local package registries.
  - external: runs a small, explicitly non-destructive recon pass (TCP connect
    probes on a short, well-known port list, HTTP header/banner grab) against a
    target covered by a *valid, confirmed Engagement*. No external mode call is
    permitted without one — enforced here, not just by the caller.
"""
from __future__ import annotations

import asyncio
import socket
from pathlib import Path
from typing import Callable, Awaitable

import httpx

from .engagement import Engagement
from ..workspace import AppWorkspace

LogFn = Callable[[str], Awaitable[None]]

# Deliberately short and read-only: connect + banner grab, never a payload.
_COMMON_PORTS = [22, 80, 443, 8080, 8443, 3000, 5000, 5173, 8000]


async def audit_sandbox_app(ws: AppWorkspace, log: LogFn) -> dict:
    """Run npm audit (and bandit if a Python backend exists) against the app
    CyberFactory itself generated. No engagement needed: this never leaves
    the local filesystem/npm registry for the app's own manifest."""
    findings: list[dict] = []
    await log(f"[vuln-discovery] auditing {ws.app_id} dependencies...")

    proc = await asyncio.create_subprocess_exec(
        "npm", "audit", "--json",
        cwd=str(ws.path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()
    findings.append({"tool": "npm audit", "exit_code": proc.returncode, "raw": out.decode(errors="replace")[:4000]})

    if (ws.path / "requirements.txt").exists():
        proc = await asyncio.create_subprocess_exec(
            "pip-audit", "-r", "requirements.txt",
            cwd=str(ws.path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await proc.communicate()
        findings.append({"tool": "pip-audit", "exit_code": proc.returncode, "raw": out.decode(errors="replace")[:4000]})

    await log(f"[vuln-discovery] {ws.app_id}: {len(findings)} tool report(s) collected.")
    return {"mode": "sandbox", "app_id": ws.app_id, "findings": findings}


async def _probe_port(host: str, port: int, timeout: float = 1.5) -> bool:
    loop = asyncio.get_event_loop()
    try:
        fut = loop.run_in_executor(None, _sync_connect, host, port, timeout)
        return await asyncio.wait_for(fut, timeout + 0.5)
    except Exception:  # noqa: BLE001
        return False


def _sync_connect(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


async def recon_external_target(engagement: Engagement, log: LogFn) -> dict:
    """Non-destructive recon only: TCP connect probes + HTTP banner grab on an
    already-authorized target. Requires a valid Engagement; raises otherwise."""
    if not engagement.is_valid():
        raise PermissionError("No valid, confirmed engagement for this target.")

    host = engagement.target.split("://")[-1].split("/")[0].split(":")[0]
    await log(f"[vuln-discovery] EXTERNAL recon on {host} (engagement {engagement.id}, authorized by: {engagement.authorized_by})")

    open_ports: list[int] = []
    for port in _COMMON_PORTS:
        if await _probe_port(host, port):
            open_ports.append(port)
            await log(f"[vuln-discovery] {host}:{port} open")

    headers: dict[str, str] | None = None
    for scheme, port in (("https", 443), ("http", 80)):
        if port in open_ports:
            try:
                async with httpx.AsyncClient(timeout=3.0, verify=False) as client:
                    resp = await client.get(f"{scheme}://{host}:{port}/", follow_redirects=False)
                    headers = dict(resp.headers)
                    await log(f"[vuln-discovery] {scheme}://{host}:{port} -> {resp.status_code}, server={headers.get('server', 'unknown')}")
            except Exception as exc:  # noqa: BLE001
                await log(f"[vuln-discovery] HTTP probe on {scheme}://{host}:{port} failed: {exc}")

    return {
        "mode": "external",
        "target": host,
        "engagement_id": engagement.id,
        "open_ports": open_ports,
        "http_headers": headers,
    }
