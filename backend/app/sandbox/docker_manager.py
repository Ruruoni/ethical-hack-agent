"""Docker SDK wrapper: isolated, no-outbound-network containers for re-running
checks against a generated app's own code. Used only by the sandbox path —
never for anything pointed at an external engagement target.
"""
from __future__ import annotations

from pathlib import Path

from .. import config

try:
    import docker
except ImportError:  # pragma: no cover - optional at import time
    docker = None


def _ensure_isolated_network(client) -> None:
    try:
        client.networks.get(config.SANDBOX_NETWORK_NAME)
    except Exception:  # noqa: BLE001
        client.networks.create(
            config.SANDBOX_NETWORK_NAME,
            driver="bridge",
            internal=True,  # no outbound internet access from this network
        )


def run_isolated_check(app_path: Path, command: list[str]) -> dict:
    """Run `command` inside a throwaway, network-isolated container with
    app_path mounted read-only. Returns {exit_code, logs}."""
    if docker is None:
        return {"exit_code": -1, "logs": "docker SDK not installed; skipping isolated run."}

    client = docker.from_env()
    _ensure_isolated_network(client)

    container = client.containers.run(
        config.SANDBOX_IMAGE,
        command=command,
        volumes={str(app_path): {"bind": "/workspace", "mode": "ro"}},
        working_dir="/workspace",
        network=config.SANDBOX_NETWORK_NAME,
        mem_limit="512m",
        pids_limit=256,
        detach=True,
        remove=False,
    )
    try:
        result = container.wait(timeout=120)
        logs = container.logs().decode(errors="replace")
        return {"exit_code": result.get("StatusCode", -1), "logs": logs[-4000:]}
    finally:
        container.remove(force=True)
