"""Workspace Scaffolder (Engine A).

Provisions a clean app directory under generated-apps/app-<uuid>/, populates
boilerplate, and tracks per-app metadata (assigned port, state) in memory.
"""
from __future__ import annotations

import uuid
import socket
from dataclasses import dataclass, field
from pathlib import Path

from . import config
from .templates.vite_boilerplate import render_boilerplate


@dataclass
class AppWorkspace:
    app_id: str
    path: Path
    port: int
    prompt_history: list[str] = field(default_factory=list)
    status: str = "scaffolded"  # scaffolded -> installing -> running -> error


_REGISTRY: dict[str, AppWorkspace] = {}


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def _allocate_port() -> int:
    low, high = config.DEV_SERVER_PORT_RANGE
    used = {ws.port for ws in _REGISTRY.values()}
    for port in range(low, high):
        if port not in used and _port_is_free(port):
            return port
    raise RuntimeError("No free dev server ports available in configured range")


def create_workspace(initial_prompt: str) -> AppWorkspace:
    app_id = f"app-{uuid.uuid4().hex[:8]}"
    app_dir = config.GENERATED_APPS_DIR / app_id
    app_dir.mkdir(parents=True, exist_ok=False)

    port = _allocate_port()
    files = render_boilerplate(app_name=app_id, port=port)
    write_files(app_dir, files)

    ws = AppWorkspace(app_id=app_id, path=app_dir, port=port)
    ws.prompt_history.append(initial_prompt)
    _REGISTRY[app_id] = ws
    return ws


def write_files(root: Path, files: dict[str, str]) -> list[str]:
    """Write a {relative_path: contents} map under root, creating dirs as needed."""
    written = []
    for rel_path, contents in files.items():
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents)
        written.append(rel_path)
    return written


def get_workspace(app_id: str) -> AppWorkspace | None:
    return _REGISTRY.get(app_id)


def list_workspaces() -> list[AppWorkspace]:
    return list(_REGISTRY.values())
