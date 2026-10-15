"""Neural embedding retrievers (FREE, local). Two real pretrained models, labelled exactly:

  spacy-md-static   spaCy `en_core_web_md` (MIT): 300-d STATIC word vectors, mean-pooled. Pretrained neural word embeddings, NOT a contextual
                    sentence encoder. Installable in the authoring sandbox.
  minilm            `all-minilm` (sentence-transformers all-MiniLM-L6-v2, Apache-2.0) via a local Ollama runtime: 384-d sentence embeddings.
                    Not downloadable in the authoring sandbox (model hosts blocked); measured in CI (model-eval workflow).

Hashing vectors and LSA in knowledge.py are NOT neural embeddings and are labelled `dense_hashing` / `dense_lsa` everywhere.
Settings recorded: model, dimension, L2 normalisation, chunking (heading-split, <=1800 chars), metric (cosine), exact scan or HNSW (pgvector)."""
import hashlib
import json
import os

import numpy as np

from .knowledge import BM25, Hybrid


class Embedder:
    name = ""; dim = 0; normalized = True

    def embed(self, texts): raise NotImplementedError


class SpacyStaticEmbedder(Embedder):
    name, dim = "spacy-md-static", 300

    def __init__(self):
        import spacy
        self.nlp = spacy.load("en_core_web_md", disable=["parser", "ner", "lemmatizer", "tagger", "attribute_ruler"])
        self.version = self.nlp.meta["version"]

    def embed(self, texts):
        v = np.array([self.nlp(t[:3000]).vector for t in texts], dtype="float32")
        n = np.linalg.norm(v, axis=1, keepdims=True); n[n == 0] = 1; return v / n


class OllamaEmbedder(Embedder):
    name, dim = "minilm", 384

    def __init__(self, model="all-minilm", endpoint=None, cache_path=None):
        from .llm import OllamaClient
        self.client = OllamaClient(model=model, endpoint=endpoint); self.model = model; self.cache_path = cache_path
        self.cache = json.load(open(cache_path)) if cache_path and os.path.exists(cache_path) else {}

    def embed(self, texts):
        out = [None] * len(texts); todo = []
        for i, t in enumerate(texts):
            k = hashlib.sha256((self.model + t).encode()).hexdigest()
            if k in self.cache: out[i] = self.cache[k]
            else: todo.append((i, k, t))
        for b in range(0, len(todo), 32):
            batch = todo[b:b + 32]; vecs = self.client.embed([t[:2500] for _, _, t in batch], self.model)
            for (i, k, _), v in zip(batch, vecs): out[i] = v; self.cache[k] = v
        if self.cache_path and todo: json.dump(self.cache, open(self.cache_path, "w"))
        v = np.array(out, dtype="float32"); n = np.linalg.norm(v, axis=1, keepdims=True); n[n == 0] = 1; return v / n


class NeuralIndex:
    """Exact cosine scan over L2-normalised vectors."""
    def __init__(self, chunks, embedder, name=None):
        self.embedder, self.name = embedder, name or ("neural_" + embedder.name)
        self.ids = [c["chunk_id"] for c in chunks]; self.M = embedder.embed([BM25._text(c) for c in chunks])

    def search(self, query, k=10):
        q = self.embedder.embed([query])[0]; sc = self.M @ q; order = np.argsort(-sc)[:k]
        return [(self.ids[i], float(sc[i])) for i in order]


class PgVectorIndex:
    """PostgreSQL + pgvector retriever: cosine distance (`<=>`), HNSW index (m=16, ef_construction=64). It is ANOTHER retriever: nothing else depends on it.
    Vectors travel as pgvector text literals, so no extra Python dependency beyond psycopg."""
    def __init__(self, chunks, embedder, dsn, name=None, table="nasha_chunks"):
        import psycopg
        self.embedder, self.name, self.table, self.dsn = embedder, name or ("pgvector_" + embedder.name), table, dsn
        self.ids = [c["chunk_id"] for c in chunks]; M = embedder.embed([BM25._text(c) for c in chunks]); self.dim = M.shape[1]
        with psycopg.connect(dsn, autocommit=True) as con:
            con.execute("CREATE EXTENSION IF NOT EXISTS vector")
            con.execute(f"DROP TABLE IF EXISTS {table}")
            con.execute(f"CREATE TABLE {table}(chunk_id text PRIMARY KEY, embedding vector({self.dim}))")
            with con.cursor() as cur:
                cur.executemany(f"INSERT INTO {table} VALUES (%s, %s::vector)", [(i, self._lit(v)) for i, v in zip(self.ids, M)])
            con.execute(f"CREATE INDEX ON {table} USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)")
        self.con = psycopg.connect(dsn, autocommit=True)

    @staticmethod
    def _lit(v): return "[" + ",".join(f"{x:.6f}" for x in v) + "]"

    def search(self, query, k=10):
        q = self._lit(self.embedder.embed([query])[0])
        rows = self.con.execute(f"SELECT chunk_id, 1 - (embedding <=> %s::vector) AS sim FROM {self.table} ORDER BY embedding <=> %s::vector LIMIT %s", (q, q, k)).fetchall()
        return [(r[0], float(r[1])) for r in rows]
