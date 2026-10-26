#!/bin/sh
# Wait for the Ollama service, make sure both models are present, build the
# index once, then hand control to the CLI.
set -e

EMBED_MODEL="${RAG_EMBED_MODEL:-nomic-embed-text}"
CHAT_MODEL="${RAG_CHAT_MODEL:-llama3.1:8b}"

if [ "$1" = "test" ]; then
    exec python -m unittest rag.test_pipeline -v
fi

echo "Waiting for Ollama at ${OLLAMA_HOST} ..."
i=0
until python -c "
import os, sys, urllib.request
urllib.request.urlopen(os.environ['OLLAMA_HOST'] + '/api/tags', timeout=3)
" 2>/dev/null; do
    i=$((i + 1))
    if [ "$i" -ge 60 ]; then
        echo "Ollama did not come up in time." >&2
        exit 1
    fi
    sleep 2
done

for model in "$EMBED_MODEL" "$CHAT_MODEL"; do
    # Pulls are cached in the ollama volume, so this is a no-op after the
    # first run.
    echo "Ensuring model ${model} ..."
    python - "$model" <<'PY'
import json, os, sys, urllib.request
model = sys.argv[1]
host = os.environ["OLLAMA_HOST"]
tags = json.loads(urllib.request.urlopen(host + "/api/tags", timeout=10).read())
have = {m["name"] for m in tags.get("models", [])}
if model in have or f"{model}:latest" in have:
    sys.exit(0)
print(f"  pulling {model} (first run only, this can take a few minutes)")
request = urllib.request.Request(
    host + "/api/pull",
    data=json.dumps({"model": model}).encode(),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(request, timeout=3600) as response:
    for line in response:
        status = json.loads(line).get("status", "")
        if status:
            print(f"  {status}", flush=True)
PY
done

INDEX_PATH="${RAG_INDEX_PATH:-/app/rag/index.json}"
if [ ! -f "$INDEX_PATH" ]; then
    python -m rag.main index
fi

exec python -m rag.main "$@"
