"""Broadcast hub for the Agent Thought & Activity Stream, and the Human-in-the-Loop
approval gate. Both the compiler loop and the agent orchestrator log through this."""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field

from fastapi import WebSocket


@dataclass
class ApprovalRequest:
    id: str
    summary: str
    detail: str
    future: asyncio.Future = field(default_factory=asyncio.Future)


class StreamHub:
    def __init__(self) -> None:
        self._sockets: set[WebSocket] = set()
        self._pending: dict[str, ApprovalRequest] = {}

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._sockets.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._sockets.discard(ws)

    async def log(self, message: str) -> None:
        dead = []
        for ws in self._sockets:
            try:
                await ws.send_json({"type": "log", "message": message})
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def request_approval(self, summary: str, detail: str) -> bool:
        """Pause execution until a human approves/rejects via the dashboard.

        This is the hard-coded Human-in-the-Loop Security Gate: callers MUST
        await this before running any generated verification tool or patch.
        """
        req = ApprovalRequest(id=uuid.uuid4().hex[:8], summary=summary, detail=detail)
        self._pending[req.id] = req
        payload = {"type": "approval_request", "id": req.id, "summary": summary, "detail": detail}
        for ws in list(self._sockets):
            try:
                await ws.send_json(payload)
            except Exception:  # noqa: BLE001
                self.disconnect(ws)
        try:
            return await req.future
        finally:
            self._pending.pop(req.id, None)

    def resolve_approval(self, approval_id: str, approved: bool) -> bool:
        req = self._pending.get(approval_id)
        if req is None or req.future.done():
            return False
        req.future.set_result(approved)
        return True


hub = StreamHub()
