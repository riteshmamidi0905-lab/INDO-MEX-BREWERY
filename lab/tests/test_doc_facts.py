"""Guards the documented tool counts against the registry so documentation cannot drift again (see docs/CANONICAL-FACTS.md)."""
import re
from pathlib import Path

from nasha_lab import mcp_server, tools as T

DOCS = Path(__file__).resolve().parent.parent


def test_registry_counts_match_canonical_facts():
    n = len(T.TOOLS); exposed = sum(1 for t in T.TOOLS.values() if t.exposed)
    facts = (DOCS / "docs" / "CANONICAL-FACTS.md").read_text()
    assert f"| **{n}** |" in facts and f"| **{exposed}** |" in facts and f"| **{len(mcp_server.MCP_TOOLS)}** |" in facts


def test_readme_does_not_state_a_stale_tool_count():
    n = len(T.TOOLS); readme = (DOCS / "README.md").read_text()
    assert f"{n} registered typed tools" in readme and "18 typed tools" not in readme


def test_permission_class_counts_documented():
    from collections import Counter
    c = Counter(t.permission for t in T.TOOLS.values()); facts = (DOCS / "docs" / "CANONICAL-FACTS.md").read_text()
    for perm, k in c.items(): assert re.search(rf"{perm} {k}\b", facts), (perm, k)
