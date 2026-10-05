"""Thin wrapper around a local Ollama instance. No network calls leave the host."""
import httpx
from . import config

CODER_SYSTEM_PROMPT = """You are a senior full-stack engineer generating code for a \
Vite + React + TypeScript + Tailwind + shadcn/ui frontend, or a Python/FastAPI backend.
Output ONLY the complete contents of the file(s) requested, as fenced code blocks of the
form:

```path/to/file.ext
<full file contents>
```

Do not include explanations outside the code blocks. Write clean, idiomatic, fully
working code — no placeholders like "...rest of code...".
"""

REPAIR_SYSTEM_PROMPT = """You are a senior engineer fixing a build/compile error.
You will be given the current contents of a file and the exact terminal error produced
by compiling it. Identify the structural or syntax flaw, rewrite the file completely,
and return ONLY the corrected file as a single fenced code block in the same format:

```path/to/file.ext
<full corrected file contents>
```

Do not explain. Do not omit any part of the file.
"""


class OllamaClient:
    def __init__(self, host: str = config.OLLAMA_HOST):
        self.host = host

    async def _generate(self, model: str, system: str, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.host}/api/generate",
                json={
                    "model": model,
                    "system": system,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            return resp.json().get("response", "")

    async def generate_code(self, prompt: str) -> str:
        return await self._generate(config.CODER_MODEL, CODER_SYSTEM_PROMPT, prompt)

    async def repair_code(self, file_path: str, file_contents: str, build_error: str) -> str:
        prompt = (
            f"File: {file_path}\n\n"
            f"Current contents:\n```\n{file_contents}\n```\n\n"
            f"The code provided failed compilation with the following terminal error:\n"
            f"```\n{build_error}\n```\n\n"
            "Identify the structural/syntax flaw, rewrite the file completely, and "
            "return only valid code."
        )
        return await self._generate(config.CODER_MODEL, REPAIR_SYSTEM_PROMPT, prompt)

    async def check_intent(self, prompt: str) -> dict:
        """Run the prompt through a guard model before acting on it.

        Returns {"safe": bool, "raw": str}. Fails closed (safe=False) on any
        error talking to Ollama, so a down guard model blocks action rather
        than silently permitting it.
        """
        try:
            raw = await self._generate(
                config.GUARD_MODEL,
                "Classify the following user request as 'safe' or 'unsafe' for a "
                "local, sandboxed code-generation tool. Respond with a single word.",
                prompt,
            )
        except Exception as exc:  # noqa: BLE001
            return {"safe": False, "raw": f"guard model unavailable: {exc}"}
        return {"safe": "unsafe" not in raw.lower(), "raw": raw}


def parse_fenced_files(response: str) -> dict[str, str]:
    """Parse one or more ```path\\ncontents``` blocks out of a model response."""
    files: dict[str, str] = {}
    lines = response.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```") and len(line.strip()) > 3:
            path = line.strip()[3:].strip()
            body: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
            if path:
                files[path] = "\n".join(body) + "\n"
        i += 1
    return files
