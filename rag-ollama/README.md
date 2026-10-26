# Sample RAG with Ollama

A small, honest RAG pipeline you can read in one sitting: **chunk → embed →
hybrid retrieve → answer with citations**, running fully locally on
[Ollama](https://ollama.com).

No vector database, no framework, **no pip installs** — the whole thing is
Python standard library plus two HTTP calls to Ollama. The index is a list of
chunks in memory, persisted as JSON. That is the point: you can see where
every answer came from.

## Models

| Role | Model | Why |
| --- | --- | --- |
| Embeddings | `nomic-embed-text` | 768-dim, 8k context, trained specifically for retrieval; the standard embedding choice on Ollama. Needs the `search_document:` / `search_query:` prefixes, which this code applies for you. |
| Generation | `llama3.1:8b` | 128k context, solid instruction following and citation discipline, runs in ~6GB RAM. |

Swap either without touching code:

```bash
RAG_EMBED_MODEL=mxbai-embed-large RAG_CHAT_MODEL=qwen3:8b docker compose run --rm rag ask "..."
```

On a small machine, `llama3.2:3b` works; on a big one, `qwen3:14b` gives
noticeably better synthesis.

## Run it with Docker

Ollama runs as its own service, models are pulled into a named volume on
first run, and the index is built automatically.

```bash
docker compose build

# Ask one question (first run pulls ~5GB of models, then it is cached)
docker compose run --rm rag ask "how is the SUPER69 voucher validated?"

# Interactive loop
docker compose run --rm rag repl

# Retrieval only, no LLM — the fastest way to debug bad answers
docker compose run --rm rag search "ICICI cap"

# Rebuild the index after changing rag/corpus
docker compose run --rm rag index

# Offline tests (no Ollama needed)
docker compose run --rm --no-deps rag test

docker compose down            # stop; add -v to also drop the model cache
```

Already have Ollama on the host? Point the app at it and skip the compose
service:

```bash
docker run --rm -it --network host -e OLLAMA_HOST=http://localhost:11434 \
  $(docker compose config --images | head -1) ask "what order are discounts applied in?"
```

## Run it without Docker

```bash
ollama serve &
ollama pull nomic-embed-text
ollama pull llama3.1:8b

python -m rag.main index
python -m rag.main ask "is a bank offer capped?"
python -m unittest rag.test_pipeline -v
```

Python 3.9+, nothing to install.

## How it works

```
rag/corpus/*.md
   │  chunk_text()      split on markdown headings, then pack paragraphs to
   │                    ~180 words with 40 words of overlap; the heading is
   │                    prefixed into each chunk so the embedder keeps context
   ▼
RagIndex.from_paths()   embeds chunks in batches of 32 (one request per chunk
   │                    is the slowest mistake people make here)
   ▼
index.search(query)     dense cosine  +  BM25   →  Reciprocal Rank Fusion
   │                    paraphrase       exact IDs,   no score normalisation
   │                    matching         codes, rare  needed, which is why it
   │                                     terms        beats adding scores
   ▼
answer()                prompt carries [source: doc > heading #n] per chunk;
                        the system prompt forbids answering outside context
                        and requires a citation per claim
```

Why hybrid rather than embeddings alone: a query like `ICICI cap` or
`SUPER69` is a rare-term lookup, and dense vectors are mediocre at those.
BM25 nails them. Conversely BM25 misses "which brands are blocked?" when the
document says "excluded brands". You want both, and RRF fuses them by rank
instead of by score, so you never have to calibrate two different scales.

## Where this approach runs out

Plain RAG — even good hybrid RAG — answers *local* questions: "what is the
deadline", "is the offer capped". It fails on *global* ones like "what are
the win themes across these 10 documents", because the answer does not live
in any top-k chunk. When you hit that, the next steps are, roughly in order
of effort:

1. **Document indexing** — build a table of contents plus per-section
   summaries at upload time, hand the agent the index, and let it reason
   about which pages to read. Cheap, precise, explainable.
2. **Knowledge graphs (GraphRAG)** — good for multi-hop answers spread
   across documents; entity extraction at ingest is slow and costly.
3. **Orchestrator–worker sub-agents** — fan files out to workers, recurse on
   the 1000-page one, map-reduce upward. Handles anything; token-heavy.
4. **Recursive language models** — keep the document as a variable in a
   Python REPL, let the model write code to slice it and call sub-LLMs on
   the parts it needs. Scales past the context window; still early.

They compose: an index tells sub-agents which pages to read, so you get
precision and scale together. The query should decide the architecture.

## Use your own documents

Drop `.md` or `.txt` files into `rag/corpus/`, then re-run `index`. The
sample corpus is the rule set of an e-commerce discount engine, which is
useful precisely because the questions have exact answers you can check the
citations against.

## Layout

| File | What it holds |
| --- | --- |
| `rag/ollama.py` | ~60-line Ollama client: `/api/embed`, `/api/generate`, clear errors when the daemon or a model is missing |
| `rag/pipeline.py` | chunking, the index, BM25, cosine, RRF, prompt building |
| `rag/main.py` | CLI: `index`, `ask`, `search`, `repl` |
| `rag/test_pipeline.py` | 11 offline tests; the embedder is stubbed, so no model required |
| `docker/entrypoint.sh` | waits for Ollama, ensures models, builds the index once |
