"""Minimal Ollama HTTP client (stdlib only).

Ollama exposes a local REST API on port 11434. We only need two endpoints:
  POST /api/embed      -> embeddings for one or more strings
  POST /api/generate   -> a single-shot completion
"""

import json
import os
import urllib.error
import urllib.request
from typing import List

# Defaults are overridable so you can swap models without touching code.
HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# nomic-embed-text: 768-dim, 8k context, trained for retrieval and the
# standard choice for RAG on Ollama. It is asymmetric: queries and documents
# get different prefixes (see embed_query / embed_documents below).
EMBED_MODEL = os.environ.get("RAG_EMBED_MODEL", "nomic-embed-text")

# llama3.1:8b is a good answer-generation default: 128k context, solid
# instruction following, runs on ~6GB of RAM. qwen3:8b is a fine swap.
CHAT_MODEL = os.environ.get("RAG_CHAT_MODEL", "llama3.1:8b")

TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "120"))


class OllamaError(RuntimeError):
    pass


def _post(path: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"{HOST}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")
        if error.code == 404 and "not found" in detail:
            raise OllamaError(
                f"{detail.strip()}\nPull it first: ollama pull <model>"
            ) from error
        raise OllamaError(f"{path} failed ({error.code}): {detail.strip()}") from error
    except urllib.error.URLError as error:
        raise OllamaError(
            f"Cannot reach Ollama at {HOST} ({error.reason}). Is `ollama serve` running?"
        ) from error


def embed(texts: List[str], model: str = EMBED_MODEL) -> List[List[float]]:
    """Embed a batch of strings. One HTTP round trip for the whole batch."""
    if not texts:
        return []
    return _post("/api/embed", {"model": model, "input": texts})["embeddings"]


def embed_documents(texts: List[str]) -> List[List[float]]:
    return embed([f"search_document: {text}" for text in texts])


def embed_query(text: str) -> List[float]:
    return embed([f"search_query: {text}"])[0]


def generate(prompt: str, system: str = "", model: str = CHAT_MODEL) -> str:
    """Single-shot completion. temperature=0 keeps answers reproducible."""
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": 0, "num_ctx": 8192},
    }
    return _post("/api/generate", payload)["response"].strip()
