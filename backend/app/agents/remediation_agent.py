"""Remediation & Auto-Patch Agent.

Only ever writes code into the local sandbox app (generated-apps/app-*). It
never "patches" an external engagement target — for an external finding it
produces a written recommendation for the human to apply to their own
infrastructure, since CyberFactory has no access to modify that target.
"""
from __future__ import annotations

from typing import Callable, Awaitable

from ..ollama_client import OllamaClient, parse_fenced_files
from ..rag.chroma_store import ChromaStore
from ..workspace import AppWorkspace, write_files

LogFn = Callable[[str], Awaitable[None]]

REMEDIATION_PROMPT_TEMPLATE = """A security finding was confirmed in this project.

Finding:
{finding}

Relevant reference material:
{reference}

File to patch: {file_path}
Current contents:
```
{current_contents}
```

Rewrite this file to resolve the finding. Keep all unrelated functionality
intact. Return only the corrected file.
"""


async def patch_sandbox_app(
    ws: AppWorkspace,
    file_path: str,
    finding: str,
    store: ChromaStore,
    log: LogFn,
) -> bool:
    target = ws.path / file_path
    if not target.exists():
        await log(f"[remediation] target file {file_path} does not exist in {ws.app_id}; skipping.")
        return False

    reference_chunks = store.query(finding, n_results=3)
    reference_text = "\n---\n".join(reference_chunks) or "(no reference material indexed yet)"

    prompt = REMEDIATION_PROMPT_TEMPLATE.format(
        finding=finding,
        reference=reference_text,
        file_path=file_path,
        current_contents=target.read_text(),
    )
    await log(f"[remediation] drafting patch for {file_path} in {ws.app_id}...")
    client = OllamaClient()
    response = await client.generate_code(prompt)
    files = parse_fenced_files(response)
    if file_path not in files:
        await log(f"[remediation] model response did not contain a patch for {file_path}.")
        return False

    write_files(ws.path, {file_path: files[file_path]})
    await log(f"[remediation] patch applied to {file_path}. Re-run the exploitation agent to verify.")
    return True


def recommend_external_fix(finding: str, reference_chunks: list[str]) -> str:
    """No code to write for an external target — hand back a human-readable
    recommendation instead."""
    reference_text = "\n---\n".join(reference_chunks) or "(no reference material indexed yet)"
    return (
        f"Recommended remediation for: {finding}\n\n"
        f"Reference material:\n{reference_text}\n\n"
        "Apply this on the target's own infrastructure — CyberFactory does not "
        "have write access to externally engaged targets."
    )
