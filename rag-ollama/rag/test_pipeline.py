"""Offline tests: chunking, BM25 and RRF fusion run without Ollama.

The embedder is stubbed with a deterministic bag-of-words vector, so the
retrieval plumbing is tested without pulling a model.
"""

import hashlib
import unittest
from pathlib import Path

from . import ollama
from .pipeline import Chunk, RagIndex, build_prompt, chunk_text, tokenize

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"


def fake_embed(texts, model=None):
    """Hash each token into one of 64 buckets. Shared vocabulary gives
    similar vectors, which is all the dense path needs to be exercised."""
    vectors = []
    for text in texts:
        vector = [0.0] * 64
        for token in tokenize(text):
            bucket = int(hashlib.md5(token.encode()).hexdigest(), 16) % 64
            vector[bucket] += 1.0
        vectors.append(vector)
    return vectors


class ChunkingTest(unittest.TestCase):
    def test_splits_on_headings(self):
        chunks = chunk_text("# Alpha\n\nfirst body\n\n# Beta\n\nsecond body")
        self.assertEqual(["Alpha", "Beta"], [heading for heading, _ in chunks])

    def test_heading_is_prefixed_into_chunk_text(self):
        _, text = chunk_text("# Alpha\n\nfirst body")[0]
        self.assertTrue(text.startswith("Alpha\n\n"))

    def test_long_section_splits_with_overlap(self):
        paragraphs = "\n\n".join(f"p{i} " + "word " * 60 for i in range(6))
        chunks = chunk_text("# Long\n\n" + paragraphs, target_words=100, overlap_words=60)
        self.assertGreater(len(chunks), 1)
        # The tail of chunk N must reappear at the head of chunk N+1.
        first_paragraphs = chunks[0][1].split("\n\n")
        self.assertIn(first_paragraphs[-1], chunks[1][1])

    def test_untitled_text_still_chunks(self):
        chunks = chunk_text("no headings here, just prose")
        self.assertEqual(1, len(chunks))
        self.assertEqual("", chunks[0][0])


class RetrievalTest(unittest.TestCase):
    def setUp(self):
        self._real_embed = ollama.embed
        ollama.embed = fake_embed
        self.index = RagIndex.from_paths(sorted(CORPUS_DIR.glob("*.md")), verbose=False)

    def tearDown(self):
        ollama.embed = self._real_embed

    def test_index_round_trips_through_json(self):
        path = Path(self.id() + ".json")
        try:
            self.index.save(path)
            reloaded = RagIndex.load(path)
            self.assertEqual(len(self.index.chunks), len(reloaded.chunks))
            self.assertEqual(self.index.chunks[0].text, reloaded.chunks[0].text)
        finally:
            path.unlink(missing_ok=True)

    def test_bm25_finds_the_rare_term(self):
        scores = self.index.bm25_scores("ICICI cap")
        best = self.index.chunks[max(range(len(scores)), key=lambda i: scores[i])]
        self.assertEqual("bank-offers.md", best.doc_id)

    def test_bm25_ignores_unknown_terms(self):
        self.assertEqual(
            [0.0] * len(self.index.chunks),
            self.index.bm25_scores("zzzznonexistentterm"),
        )

    def test_hybrid_search_returns_top_k_ranked(self):
        hits = self.index.search("which brands does SUPER69 exclude?", top_k=3)
        self.assertEqual(3, len(hits))
        self.assertEqual("voucher-rules.md", hits[0][0].doc_id)
        scores = [score for _, score in hits]
        self.assertEqual(sorted(scores, reverse=True), scores)

    def test_empty_index_returns_no_hits(self):
        self.assertEqual([], RagIndex().search("anything"))

    def test_prompt_carries_citable_ids(self):
        hits = self.index.search("bank offer cap", top_k=2)
        prompt = build_prompt("what is the cap?", hits)
        for chunk, _ in hits:
            self.assertIn(f"[source: {chunk.citation}]", prompt)
        self.assertIn("what is the cap?", prompt)

    def test_citation_includes_heading_when_present(self):
        chunk = Chunk(doc_id="a.md", chunk_id=2, text="body", heading="Caps")
        self.assertEqual("a.md > Caps #2", chunk.citation)


if __name__ == "__main__":
    unittest.main()
