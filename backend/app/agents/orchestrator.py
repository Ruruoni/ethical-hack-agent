"""Agent orchestrator: a small explicit state machine standing in for LangGraph.

Each node is an async (state) -> state function. The human-in-the-loop gate
(stream_hub.hub.request_approval) is awaited before any exploitation or patch
step — not optional, not bypassable from here.

Two pipelines:
  - run_sandbox_pipeline(ws):            discover -> [approve] -> confirm -> [approve] -> patch -> confirm
  - run_external_pipeline(engagement):   recon     -> [approve] -> confirm (passive only)
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..rag.chroma_store import ChromaStore
from ..stream_hub import hub
from ..workspace import AppWorkspace
from .engagement import Engagement
from . import vuln_discovery_agent, exploitation_agent, remediation_agent


@dataclass
class PipelineResult:
    steps: list[dict] = field(default_factory=list)

    def record(self, name: str, data: dict) -> None:
        self.steps.append({"step": name, "data": data})


async def run_sandbox_pipeline(ws: AppWorkspace) -> PipelineResult:
    result = PipelineResult()
    log = hub.log
    store = ChromaStore()

    discovery = await vuln_discovery_agent.audit_sandbox_app(ws, log)
    result.record("discovery", discovery)

    has_findings = any(
        r.get("exit_code") not in (0, None) for r in discovery.get("findings", [])
    )
    if not has_findings:
        await log(f"[orchestrator] no findings for {ws.app_id}; pipeline complete.")
        return result

    approved = await hub.request_approval(
        summary=f"Confirm findings for {ws.app_id} in an isolated container?",
        detail=str(discovery),
    )
    if not approved:
        await log(f"[orchestrator] human declined confirmation step for {ws.app_id}.")
        return result

    confirmation = await exploitation_agent.confirm_sandbox_finding(ws, log)
    result.record("confirmation", confirmation)

    if confirmation.get("exit_code") in (0, None):
        await log(f"[orchestrator] confirmation run clean for {ws.app_id}; nothing to patch.")
        return result

    approved = await hub.request_approval(
        summary=f"Apply auto-patch to {ws.app_id}?",
        detail="A confirmed finding exists. Approve to let the Remediation agent draft and apply a fix.",
    )
    if not approved:
        await log(f"[orchestrator] human declined patch step for {ws.app_id}.")
        return result

    patched = await remediation_agent.patch_sandbox_app(
        ws,
        file_path="package.json",
        finding=confirmation.get("logs", "dependency audit finding"),
        store=store,
        log=log,
    )
    result.record("patch", {"applied": patched})

    if patched:
        reconfirmation = await exploitation_agent.confirm_sandbox_finding(ws, log)
        result.record("reconfirmation", reconfirmation)

    return result


async def run_external_pipeline(engagement: Engagement) -> PipelineResult:
    result = PipelineResult()
    log = hub.log

    if not engagement.is_valid():
        await log(f"[orchestrator] REFUSED: engagement {engagement.id} is missing, expired, or unconfirmed.")
        raise PermissionError("No valid, confirmed engagement for this target.")

    approved = await hub.request_approval(
        summary=f"Begin recon of external target {engagement.target}?",
        detail=(
            f"Engagement {engagement.id}\nAuthorized by: {engagement.authorized_by}\n"
            f"Scope notes: {engagement.scope_notes}\n\n"
            "Recon is limited to TCP connect probes on common ports and a single "
            "HTTP banner/header grab. No exploit payloads will be sent."
        ),
    )
    if not approved:
        await log(f"[orchestrator] human declined recon step for engagement {engagement.id}.")
        return result

    recon = await vuln_discovery_agent.recon_external_target(engagement, log)
    result.record("recon", recon)

    if not recon.get("open_ports"):
        await log(f"[orchestrator] no open ports found on {engagement.target}; pipeline complete.")
        return result

    approved = await hub.request_approval(
        summary=f"Run passive confirmation checks against {engagement.target}?",
        detail="Checks are passive only: missing security headers, TLS cert expiry, banner disclosure.",
    )
    if not approved:
        await log(f"[orchestrator] human declined confirmation step for engagement {engagement.id}.")
        return result

    confirmation = await exploitation_agent.confirm_external_findings(engagement, recon, log)
    result.record("confirmation", confirmation)

    store = ChromaStore()
    for verdict in confirmation.get("verdicts", []):
        reference = store.query(verdict["finding"], n_results=3)
        recommendation = remediation_agent.recommend_external_fix(verdict["finding"], reference)
        verdict["recommendation"] = recommendation
        await log(f"[remediation] {recommendation}")

    return result
