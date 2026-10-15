"""Model clients for the LLM planner. FREE / LOCAL only: Ollama (local runtime) over HTTP, or scripted clients for tests.
No API key, no hosted service. If no local model is reachable, OllamaClient raises ModelUnavailable and the integration tests skip loudly."""
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field


class ModelUnavailable(RuntimeError):
    pass


@dataclass
class ModelReply:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0


class ModelClient:
    name = "abstract"; version = ""; runtime = ""

    def chat(self, messages, schema, max_tokens=700) -> ModelReply:      # noqa
        raise NotImplementedError


class OllamaClient(ModelClient):
    """Local Ollama runtime. Structured output: the JSON schema is passed as `format`, so decoding is grammar-constrained."""
    runtime = "ollama"

    def __init__(self, model=None, endpoint=None, timeout=300, seed=7):
        self.model = self.name = model or os.environ.get("NASHA_LLM_MODEL", "qwen2.5:1.5b-instruct")
        self.endpoint = (endpoint or os.environ.get("NASHA_LLM_ENDPOINT", "http://127.0.0.1:11434")).rstrip("/")
        self.timeout, self.seed, self.version = timeout, seed, ""

    def _post(self, path, body, timeout=None):
        req = urllib.request.Request(self.endpoint + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as r: return json.loads(r.read())
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
            raise ModelUnavailable(f"{self.endpoint}{path}: {e}") from e

    def available(self):
        try:
            self._post("/api/show", {"model": self.model}, timeout=5); return True
        except ModelUnavailable:
            return False

    def info(self):
        d = self._post("/api/show", {"model": self.model}, timeout=10)
        det = d.get("details", {})
        return dict(model=self.model, family=det.get("family"), parameter_size=det.get("parameter_size"), quantization=det.get("quantization_level"), license=(d.get("license") or "")[:80])

    def chat(self, messages, schema, max_tokens=700):
        t0 = time.perf_counter()
        d = self._post("/api/chat", {"model": self.model, "stream": False, "messages": messages, "format": schema,
                                     "options": {"temperature": 0, "seed": self.seed, "num_ctx": 6144, "num_predict": max_tokens}})
        return ModelReply(d["message"]["content"], d.get("prompt_eval_count", 0), d.get("eval_count", 0), (time.perf_counter() - t0) * 1000)

    def embed(self, texts, model="all-minilm"):
        d = self._post("/api/embed", {"model": model, "input": texts}); return d["embeddings"]


@dataclass
class ScriptedClient(ModelClient):
    """Test double. `responder(messages, schema, call_index) -> str|dict`. NOT a language model; used to test the planner harness, the
    schema/retry policy and the permission layer against worst-case model behaviour."""
    responder: object = None
    name: str = "scripted"; version: str = "test"; runtime: str = "scripted"
    calls: list = field(default_factory=list)

    def chat(self, messages, schema, max_tokens=700):
        i = len(self.calls); self.calls.append(messages)
        out = self.responder(messages, schema, i)
        text = out if isinstance(out, str) else json.dumps(out)
        return ModelReply(text, sum(len(m["content"]) for m in messages) // 4, len(text) // 4, 1.0)


class CachingClient(ModelClient):
    """Memoises replies by (messages, schema). Lets the guardrail variant reuse the raw model's outputs (temperature 0), so two planner
    variants are compared on IDENTICAL model replies and the model is only run once."""
    def __init__(self, inner, path=None):
        import hashlib
        self.inner, self.path, self._h = inner, path, hashlib
        self.name, self.version, self.runtime = inner.name, getattr(inner, "version", ""), getattr(inner, "runtime", "")
        self.cache = {}
        if path and os.path.exists(path): self.cache = json.load(open(path))
        self.hits = self.misses = 0

    def _key(self, messages, schema): return self._h.sha256(json.dumps([messages, schema], sort_keys=True).encode()).hexdigest()

    def chat(self, messages, schema, max_tokens=700):
        k = self._key(messages, schema)
        if k in self.cache:
            self.hits += 1; c = self.cache[k]; return ModelReply(c["text"], c["p"], c["c"], c["ms"])
        self.misses += 1; r = self.inner.chat(messages, schema, max_tokens)
        self.cache[k] = dict(text=r.text, p=r.prompt_tokens, c=r.completion_tokens, ms=r.latency_ms)
        if self.path: json.dump(self.cache, open(self.path, "w"))
        return r
