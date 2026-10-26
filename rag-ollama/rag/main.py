"""CLI for the sample RAG pipeline.

    python -m rag.main index                      # build rag/index.json
    python -m rag.main ask "how is SUPER69 validated?"
    python -m rag.main search "ICICI cap"         # retrieval only, no LLM
    python -m rag.main repl
"""

import os
import sys
from pathlib import Path

from . import ollama
from .pipeline import RagIndex, answer

HERE = Path(__file__).resolve().parent
CORPUS_DIR = HERE / "corpus"
INDEX_PATH = Path(os.environ.get("RAG_INDEX_PATH", HERE / "index.json"))


def build_index() -> RagIndex:
    paths = sorted(CORPUS_DIR.glob("*.md")) + sorted(CORPUS_DIR.glob("*.txt"))
    if not paths:
        sys.exit(f"No .md or .txt files in {CORPUS_DIR}")
    index = RagIndex.from_paths(paths)
    index.save(INDEX_PATH)
    print(f"Saved {len(index.chunks)} chunks to {INDEX_PATH}")
    return index


def load_index() -> RagIndex:
    if not INDEX_PATH.exists():
        print("No index found, building one first.")
        return build_index()
    return RagIndex.load(INDEX_PATH)


def print_hits(hits) -> None:
    for chunk, score in hits:
        preview = " ".join(chunk.text.split())[:120]
        print(f"  {score:.4f}  {chunk.citation}: {preview}...")


def ask(index: RagIndex, question: str) -> None:
    text, hits = answer(index, question)
    print(f"\nQ: {question}\n")
    print(text)
    print("\nRetrieved:")
    print_hits(hits)


def main(argv: list) -> None:
    command = argv[0] if argv else "repl"

    if command == "index":
        build_index()
        return

    index = load_index()

    if command == "search":
        query = " ".join(argv[1:]) or sys.exit("Usage: search <query>")
        print_hits(index.search(query))
    elif command == "ask":
        question = " ".join(argv[1:]) or sys.exit("Usage: ask <question>")
        ask(index, question)
    elif command == "repl":
        print(f"Models: {ollama.EMBED_MODEL} (embed) / {ollama.CHAT_MODEL} (chat)")
        print("Ask a question, or Ctrl-D to quit.")
        while True:
            try:
                question = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if question:
                ask(index, question)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except ollama.OllamaError as error:
        sys.exit(f"Ollama error: {error}")
