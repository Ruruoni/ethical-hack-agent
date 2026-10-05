# CyberFactory

A self-hosted, 100% open-source local app-generation platform (a free alternative to
tools like Lovable) hardened for building and testing security-focused applications.

CyberFactory turns natural-language prompts into a running Vite + React + TypeScript +
Tailwind frontend, backed by a Python/FastAPI workspace engine, compiled and hot-reloaded
locally. A sandboxed, human-gated agent swarm can scan the *apps CyberFactory itself
generates* for common issues (vulnerable dependencies, insecure patterns), propose
patches, and verify the fix — entirely inside isolated local Docker containers, never
against third-party or live targets.

## Why this scope

The original specification described a very large system (compiler pipeline,
multi-agent security swarm, RAG knowledge store, live exploitation against arbitrary
targets, four-panel dashboard). Building all of that as finished, production-grade
code in one pass isn't realistic or safe to hand over unreviewed — especially the
"exploitation" pieces. This implementation instead gives you a working, extensible
scaffold for every piece, with the security-agent loop deliberately constrained:

- **No network scanning of arbitrary hosts.** The Vulnerability Discovery and Safe
  Exploitation agents only ever operate against containers CyberFactory spun up itself,
  running the code CyberFactory itself generated, on an isolated Docker network with
  no outbound access.
- **Every patch and every "exploit" run requires a human click.** The WebSocket
  approval gate in `backend/app/routers/agents.py` is not cosmetic — the orchestrator
  (`backend/app/agents/orchestrator.py`) blocks on it.
- **"Exploitation" means dependency/CVE and static-analysis checks** (`pip-audit`,
  `npm audit`, `bandit`, `semgrep` if installed), not payload generation against live
  systems. Swap in more tooling later with the same approval gate in front of it.

## Stack

- **Backend:** Python 3.11+, FastAPI, Docker SDK, ChromaDB, Ollama (Qwen2.5-Coder for
  generation/repair, Llama Guard for intent checks, nomic-embed-text for RAG).
- **Frontend:** Vite + React + TypeScript + Tailwind, shadcn/ui-style tokens,
  lucide-react icons.
- **Orchestration:** a small explicit Python state machine (`orchestrator.py`) standing
  in for LangGraph — swap in LangGraph directly if you want its graph/checkpoint
  machinery; the node functions are already shaped as `(state) -> state`.

## Running it locally

Prereqs: Node 18+, Python 3.11+, Docker, and `ollama` running locally with
`qwen2.5-coder`, `llama-guard3`, and `nomic-embed-text` pulled.

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (dashboard)
cd frontend
npm install
npm run dev   # http://localhost:5173

# Optional: local Ollama + ChromaDB via compose
docker compose -f docker/docker-compose.yml up -d
```

Generated apps land in `generated-apps/app-<uuid>/` and get their own dev server
port, hot-reloaded into the dashboard's iframe viewer.

## Layout

```
backend/   FastAPI workspace scaffolder, compiler loop, agent orchestrator, sandboxed agents
frontend/  4-panel dashboard: prompter, live app viewer, agent stream, approval gate
docker/    compose file for local Ollama + ChromaDB
generated-apps/   output of the scaffolder (gitignored)
```

See `backend/app/agents/orchestrator.py` for the agent state machine and
`frontend/src/components/Dashboard.tsx` for the dashboard grid.
