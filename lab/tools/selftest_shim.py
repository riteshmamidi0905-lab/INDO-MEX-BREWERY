"""SELF-TEST SHIM, NOT A MODEL. A scripted OpenAI-compatible HTTP server used only to debug the plumbing of tools/live_model_battery.py on a machine that has no model runtime.
It answers planner requests with a fixed plan and synthesizer requests with the first evidence line it was given. It does not implement Ollama's /api/version or /api/show, so the battery can never mark `executed`
true against it, and everything the battery records from it is labelled `harness_self_test_with_scripted_shim`. Its output is never evidence of model behaviour."""
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = "selftest-shim"


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("content-type", "application/json"); self.send_header("content-length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        if self.path.endswith("/models"):
            return self._send({"data": [{"id": MODEL}]})
        if self.path.endswith("/api/tags"):
            return self._send({"models": [{"name": MODEL, "digest": "shim", "size": 0}]})
        self._send({"error": "not found"}, 404)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}")
        msgs = body.get("messages", [])
        system = next((m["content"] for m in msgs if m["role"] == "system"), "")
        user = "\n".join(m["content"] for m in msgs if m["role"] == "user")
        if "planning component" in system:
            q = re.search(r"<request>\n(.*?)\n</request>", user, re.S)
            out = {"summary": "Search the corpus for the request.", "steps": [{"id": "s1", "goal": "retrieve", "tool": "search_corpus", "args": {"query": q.group(1) if q else "suppliers"}, "depends_on": []}]}
        else:
            ev = re.findall(r"\[(e\d+)\] \(([^)]*)\) (.*?)(?=\n\n\[e\d+\]|\n</evidence>)", user, re.S)
            claims = []
            for eid, title, text in ev[:1]:
                line = next((l for l in text.splitlines() if l.strip().startswith("-")), text.splitlines()[-1] if text.splitlines() else text)
                claims.append({"text": line.lstrip("- ").strip()[:240], "evidence_ids": [eid]})
            out = {"title": "shim report", "answer": " ".join(f"{c['text']} [{c['evidence_ids'][0]}]" for c in claims) or "No evidence.", "claims": claims, "limitations": [] if claims else ["no evidence"]}
        n = max(1, len(user) // 4)
        self._send({"id": "x", "object": "chat.completion", "model": MODEL, "choices": [{"index": 0, "message": {"role": "assistant", "content": json.dumps(out)}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": n, "completion_tokens": 40, "total_tokens": n + 40}})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 11999
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
