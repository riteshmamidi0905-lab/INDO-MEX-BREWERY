"""Trust boundary for MCP responses. Arriving through MCP does not make a response trustworthy.
Every response is classified by SOURCE (TRUSTED = the NASHA server we operate; UNTRUSTED = anything else), then schema-validated (extra fields forbidden),
timeout-bounded, size-capped, metadata-checked, freshness-checked and scanned for instruction-like text. Untrusted values are TAINTED: the tool layer refuses
to let them become arguments of DRAFT or MUTATE tools unless the same value also appears in trusted evidence (information-flow idea from mcp-weir, applied minimally)."""
import asyncio
import datetime as dt
import re
from typing import Optional

from mcp import Client
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from . import knowledge as K

TRUSTED, UNTRUSTED = "TRUSTED", "UNTRUSTED"
MAX_NOTE_CHARS = 600
STALE_DAYS = 30


class SupplierNote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supplier_id: str = Field(pattern=r"^S\d{2}$"); note: str; as_of: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class Gateway:
    """Holds named MCP servers with a declared trust class. Servers are in-process (simulation); no network is involved."""
    def __init__(self, servers, today=dt.date(2026, 4, 28), timeout=0.5):
        self.servers, self.today, self.timeout = servers, today, timeout        # {label: (MCPServer, trust)}

    async def _call(self, label, tool, args):
        srv, _ = self.servers[label]
        async with Client(srv) as c:
            r = await asyncio.wait_for(c.call_tool(tool, args), timeout=self.timeout)
            if getattr(r, "is_error", False): raise RuntimeError("tool reported an error")
            if r.structured_content is not None: return r.structured_content
            import json                                           # an untrusted server may answer with unstructured text: parse, then validate like anything else
            return json.loads(r.content[0].text)

    def call_supplier_notes(self, label, supplier_id):
        """Returns dict(ok, trust, source, data, flags, tainted). `data` is None whenever any check fails."""
        import time
        trust = self.servers[label][1]; flags = []; t0 = time.perf_counter(); out = dict(ok=False, trust=trust, source=f"mcp:{label}", data=None, flags=flags, tainted=[])
        try:
            raw = asyncio.run(self._call(label, "get_supplier_notes", dict(supplier_id=supplier_id)))
        except BaseException as e:
            if isinstance(e, (KeyboardInterrupt, SystemExit)): raise
            leaves = list(getattr(e, "exceptions", [e]))
            timed_out = time.perf_counter() - t0 >= self.timeout * 0.9 or any(isinstance(x, (asyncio.TimeoutError, TimeoutError)) for x in leaves)
            flags.append("TIMEOUT" if timed_out else "UPSTREAM_ERROR"); return out
        raw = raw.get("result", raw) if isinstance(raw, dict) and set(raw) == {"result"} else raw
        try: d = SupplierNote.model_validate(raw)
        except ValidationError: flags.append("SCHEMA_MISMATCH"); return out
        if d.supplier_id != supplier_id: flags.append("METADATA_MISMATCH"); return out
        if len(d.note) > MAX_NOTE_CHARS: flags.append("OVERSIZE"); return out
        if (self.today - dt.date.fromisoformat(d.as_of)).days > STALE_DAYS: flags.append("STALE"); out["data"] = None; return out
        if K.INJECTION_RE.search(d.note): flags.append("INJECTION_SUSPECTED"); out["tainted"] = _values(d.model_dump()); return out
        out.update(ok=True, data=d.model_dump(), tainted=_values(d.model_dump()) if trust == UNTRUSTED else [])
        return out


def _values(d):
    vals = set()
    for k, v in d.items():
        if k == "as_of": continue
        if isinstance(v, str):
            vals.add(v)
            vals.update(re.findall(r"\bS\d{2}\b", v)); vals.update(re.findall(r"\b\d+(?:\.\d+)?\b", v))
        elif isinstance(v, (int, float)): vals.add(str(v))
    return sorted(vals)
