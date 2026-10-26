"""A small but honest RAG pipeline: chunk -> embed -> hybrid retrieve -> answer.

No vector database, no framework, no pip installs. The index is a list of
chunks held in memory and persisted as JSON, which is all you need to see
how the parts fit together.

Hybrid retrieval = dense (embeddings, catches paraphrase) + BM25 (keywords,
catches exact IDs, codes and rare terms), fused with Reciprocal Rank Fusion.
RRF needs no score normalisation, which is why it beats naive score addition.
"""

import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from . import ollama

TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(text.lower())


# --------------------------------------------------------------------------
# Chunking
# --------------------------------------------------------------------------

@dataclass
class Chunk:
    doc_id: str
    chunk_id: int
    text: str
    heading: str = ""
    embedding: List[float] = field(default_factory=list)

    @property
    def citation(self) -> str:
        where = f" > {self.heading}" if self.heading else ""
        return f"{self.doc_id}{where} #{self.chunk_id}"


def chunk_text(text: str, target_words: int = 180, overlap_words: int = 40) -> List[Tuple[str, str]]:
    """Split on markdown headings first, then pack paragraphs into chunks.

    Splitting on structure before size keeps a chunk about one thing, and
    carrying the heading into the chunk gives the embedder context that a
    bare paragraph loses. Returns (heading, chunk_text) pairs.
    """
    sections: List[Tuple[str, List[str]]] = [("", [])]
    for line in text.splitlines():
        if line.startswith("#"):
            sections.append((line.lstrip("# ").strip(), []))
        else:
            sections[-1][1].append(line)

    chunks: List[Tuple[str, str]] = []
    for heading, lines in sections:
        paragraphs = [p.strip() for p in "\n".join(lines).split("\n\n") if p.strip()]
        current: List[str] = []
        current_len = 0

        def flush() -> None:
            if current:
                body = "\n\n".join(current)
                prefix = f"{heading}\n\n" if heading else ""
                chunks.append((heading, prefix + body))

        for paragraph in paragraphs:
            words = len(paragraph.split())
            if current_len + words > target_words and current:
                flush()
                # Overlap: keep a tail of the previous chunk so a fact that
                # straddles the boundary survives in at least one chunk.
                tail, tail_len = [], 0
                for previous in reversed(current):
                    tail.insert(0, previous)
                    tail_len += len(previous.split())
                    if tail_len >= overlap_words:
                        break
                current, current_len = tail, tail_len
            current.append(paragraph)
            current_len += words
        flush()
    return chunks


# --------------------------------------------------------------------------
# Index
# --------------------------------------------------------------------------

class RagIndex:
    def __init__(self, chunks: Sequence[Chunk] = ()):
        self.chunks: List[Chunk] = list(chunks)
        self._doc_freq: Dict[str, int] = {}
        self._doc_tokens: List[Counter] = []
        self._doc_len: List[int] = []
        self._rebuild_lexical()

    # ---- build -----------------------------------------------------------

    @classmethod
    def from_paths(cls, paths: Iterable[Path], verbose: bool = True) -> "RagIndex":
        chunks: List[Chunk] = []
        for path in sorted(paths):
            text = path.read_text(encoding="utf-8")
            for index, (heading, body) in enumerate(chunk_text(text)):
                chunks.append(Chunk(doc_id=path.name, chunk_id=index, text=body, heading=heading))

        if verbose:
            print(f"Chunked {len(set(c.doc_id for c in chunks))} docs into {len(chunks)} chunks")
            print(f"Embedding with {ollama.EMBED_MODEL} ...")

        # Batch the embedding calls; one request per chunk is the single
        # slowest mistake people make here.
        for start in range(0, len(chunks), 32):
            batch = chunks[start:start + 32]
            for chunk, vector in zip(batch, ollama.embed_documents([c.text for c in batch])):
                chunk.embedding = vector
        return cls(chunks)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps([asdict(c) for c in self.chunks]), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "RagIndex":
        return cls([Chunk(**record) for record in json.loads(path.read_text(encoding="utf-8"))])

    def _rebuild_lexical(self) -> None:
        self._doc_tokens = [Counter(tokenize(c.text)) for c in self.chunks]
        self._doc_len = [sum(counts.values()) for counts in self._doc_tokens]
        self._doc_freq = {}
        for counts in self._doc_tokens:
            for token in counts:
                self._doc_freq[token] = self._doc_freq.get(token, 0) + 1

    # ---- scoring ---------------------------------------------------------

    def dense_scores(self, query: str) -> List[float]:
        """Cosine similarity. Ollama returns L2-normalised vectors, but we
        normalise anyway so the code survives a model swap."""
        query_vector = ollama.embed_query(query)
        query_norm = math.sqrt(sum(value * value for value in query_vector)) or 1.0
        scores = []
        for chunk in self.chunks:
            dot = sum(a * b for a, b in zip(query_vector, chunk.embedding))
            chunk_norm = math.sqrt(sum(v * v for v in chunk.embedding)) or 1.0
            scores.append(dot / (query_norm * chunk_norm))
        return scores

    def bm25_scores(self, query: str, k1: float = 1.5, b: float = 0.75) -> List[float]:
        total = len(self.chunks)
        if not total:
            return []
        average_len = sum(self._doc_len) / total
        scores = [0.0] * total
        for token in tokenize(query):
            document_freq = self._doc_freq.get(token, 0)
            if not document_freq:
                continue
            idf = math.log(1 + (total - document_freq + 0.5) / (document_freq + 0.5))
            for index, counts in enumerate(self._doc_tokens):
                frequency = counts.get(token, 0)
                if not frequency:
                    continue
                length_norm = k1 * (1 - b + b * self._doc_len[index] / average_len)
                scores[index] += idf * frequency * (k1 + 1) / (frequency + length_norm)
        return scores

    def search(self, query: str, top_k: int = 5, rrf_k: int = 60) -> List[Tuple[Chunk, float]]:
        """Hybrid search with Reciprocal Rank Fusion."""
        if not self.chunks:
            return []
        fused: Dict[int, float] = {}
        for scores in (self.dense_scores(query), self.bm25_scores(query)):
            ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            for rank, index in enumerate(ranked):
                if scores[index] <= 0:
                    continue
                fused[index] = fused.get(index, 0.0) + 1.0 / (rrf_k + rank + 1)
        best = sorted(fused.items(), key=lambda item: item[1], reverse=True)[:top_k]
        return [(self.chunks[index], score) for index, score in best]


# --------------------------------------------------------------------------
# Answering
# --------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You answer strictly from the provided context. "
    "Cite the source of every claim as [source: <id>] using the ids given. "
    "If the context does not contain the answer, say exactly: "
    "I don't know based on the provided documents."
)


def build_prompt(question: str, hits: Sequence[Tuple[Chunk, float]]) -> str:
    blocks = [f"[source: {chunk.citation}]\n{chunk.text}" for chunk, _ in hits]
    context = "\n\n---\n\n".join(blocks)
    return f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"


def answer(index: RagIndex, question: str, top_k: int = 5) -> Tuple[str, List[Tuple[Chunk, float]]]:
    hits = index.search(question, top_k=top_k)
    if not hits:
        return "I don't know based on the provided documents.", []
    return ollama.generate(build_prompt(question, hits), system=SYSTEM_PROMPT), hits
