"""Engagement model: the authorization record required before any agent is allowed
to point at a target outside CyberFactory's own generated-app sandbox.

No scan or exploit attempt against an external host/URL may run without a matching,
unexpired Engagement that was explicitly confirmed by a human. This is enforced in
orchestrator.py, not just documented here — build_target_plan() raises if called
without one.
"""
from __future__ import annotations

import ipaddress
import re
import time
import uuid
from dataclasses import dataclass
from urllib.parse import urlparse


class EngagementError(ValueError):
    pass


# Hosts/ranges that are never acceptable as "external" engagement targets, even with
# a confirmation checkbox: they're either loopback/own-sandbox (use the sandbox path
# instead) or obviously-shared infrastructure rather than something a user "owns or
# is authorized to test".
_DISALLOWED_HOST_PATTERNS = [
    re.compile(r"^(169\.254\.|metadata\.google\.internal|169\.254\.169\.254)"),
]


@dataclass
class Engagement:
    id: str
    target: str  # host, IP, or URL
    authorized_by: str  # free-text identity/statement the user supplied
    scope_notes: str  # e.g. "web app on port 8080 only, no other hosts in range"
    confirmed: bool
    created_at: float

    def is_valid(self, max_age_seconds: int = 8 * 3600) -> bool:
        return self.confirmed and (time.time() - self.created_at) < max_age_seconds


_ENGAGEMENTS: dict[str, Engagement] = {}


def _normalize_target(target: str) -> str:
    target = target.strip()
    if not target:
        raise EngagementError("Target must not be empty.")
    parsed = urlparse(target if "://" in target else f"//{target}")
    host = parsed.hostname or target
    for pattern in _DISALLOWED_HOST_PATTERNS:
        if pattern.search(host):
            raise EngagementError(f"Target '{host}' is not permitted (blocked infra/metadata host).")
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_loopback:
            raise EngagementError(
                "Loopback targets should use the built-in sandbox path, not an "
                "external engagement record."
            )
    except ValueError:
        pass  # not a literal IP, that's fine
    return target


def create_engagement(target: str, authorized_by: str, scope_notes: str, confirmed: bool) -> Engagement:
    """Record a per-run authorization. `confirmed` must reflect an explicit,
    affirmative human action in the UI (a checkbox the user actively ticks),
    never a default."""
    normalized = _normalize_target(target)
    if not authorized_by.strip():
        raise EngagementError("You must state who is authorizing this test (e.g. 'I own this host').")
    if not confirmed:
        raise EngagementError("Engagement was not explicitly confirmed by a human.")

    eng = Engagement(
        id=uuid.uuid4().hex[:10],
        target=normalized,
        authorized_by=authorized_by.strip(),
        scope_notes=scope_notes.strip(),
        confirmed=confirmed,
        created_at=time.time(),
    )
    _ENGAGEMENTS[eng.id] = eng
    return eng


def get_engagement(engagement_id: str) -> Engagement | None:
    eng = _ENGAGEMENTS.get(engagement_id)
    if eng is None or not eng.is_valid():
        return None
    return eng
