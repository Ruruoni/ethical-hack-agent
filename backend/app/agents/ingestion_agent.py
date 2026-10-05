"""Ingestion & Self-Learning Agent.

Pulls reference material (framework docs, advisories) into ChromaDB so the
Remediation agent has something concrete to cite instead of hallucinating a
fix. Scraping targets here are documentation sources, not engagement targets.
"""
from __future__ import annotations

from typing import Callable, Awaitable

from ..rag.chroma_store import ChromaStore

LogFn = Callable[[str], Awaitable[None]]


async def ingest_text(store: ChromaStore, source: str, text: str, log: LogFn) -> int:
    """Chunk and embed `text` (e.g. a CVE advisory, a doc page) under `source`."""
    chunks = [text[i : i + 1500] for i in range(0, len(text), 1500)] or [text]
    await log(f"[ingestion] indexing {len(chunks)} chunk(s) from {source}")
    store.add_documents(source=source, chunks=chunks)
    return len(chunks)
