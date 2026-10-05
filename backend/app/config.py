"""Central configuration. Everything defaults to local/offline services."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
GENERATED_APPS_DIR = BASE_DIR / "generated-apps"
GENERATED_APPS_DIR.mkdir(exist_ok=True)

# Ollama (local only)
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
CODER_MODEL = os.environ.get("CYBERFACTORY_CODER_MODEL", "qwen2.5-coder:7b")
GUARD_MODEL = os.environ.get("CYBERFACTORY_GUARD_MODEL", "llama-guard3")
EMBED_MODEL = os.environ.get("CYBERFACTORY_EMBED_MODEL", "nomic-embed-text")

# ChromaDB
CHROMA_DIR = str(BASE_DIR / "chroma-data")

# Self-healing compiler loop
MAX_SELF_HEAL_ATTEMPTS = 5

# Dev server port allocation for generated apps
DEV_SERVER_PORT_RANGE = (5173, 5273)

# Docker sandbox
SANDBOX_NETWORK_NAME = "cyberfactory-sandbox-isolated"
SANDBOX_IMAGE = os.environ.get("CYBERFACTORY_SANDBOX_IMAGE", "node:20-slim")
