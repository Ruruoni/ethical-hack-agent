"""Local ChromaDB-backed knowledge store using Ollama's nomic-embed-text."""
from __future__ import annotations

import uuid

import httpx

from .. import config

try:
    import chromadb
except ImportError:  # pragma: no cover
    chromadb = None


class _OllamaEmbedder:
    """Minimal embedding function satisfying chromadb's EmbeddingFunction protocol."""

    def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002
        vectors = []
        with httpx.Client(timeout=60.0) as client:
            for text in input:
                resp = client.post(
                    f"{config.OLLAMA_HOST}/api/embeddings",
                    json={"model": config.EMBED_MODEL, "prompt": text},
                )
                resp.raise_for_status()
                vectors.append(resp.json()["embedding"])
        return vectors


class ChromaStore:
    def __init__(self, collection_name: str = "cyberfactory_knowledge"):
        if chromadb is None:
            self._client = None
            self._collection = None
            return
        self._client = chromadb.PersistentClient(path=config.CHROMA_DIR)
        self._collection = self._client.get_or_create_collection(
            name=collection_name, embedding_function=_OllamaEmbedder()
        )

    def add_documents(self, source: str, chunks: list[str]) -> None:
        if self._collection is None:
            return
        ids = [f"{source}-{uuid.uuid4().hex[:8]}" for _ in chunks]
        self._collection.add(documents=chunks, ids=ids, metadatas=[{"source": source}] * len(chunks))

    def query(self, text: str, n_results: int = 5) -> list[str]:
        if self._collection is None:
            return []
        result = self._collection.query(query_texts=[text], n_results=n_results)
        docs = result.get("documents") or [[]]
        return docs[0]
