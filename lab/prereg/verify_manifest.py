"""Verify the stronger-model preregistration manifest: every frozen input hash, the scenario id list, and the preregistration document hash.
Usage: python lab/prereg/verify_manifest.py [--write]   (run from the repository root; --write is only for creating the manifest BEFORE the run)."""
import hashlib, json, subprocess, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOC = "lab/docs/STRONGER-MODEL-PREREGISTRATION.md"
HASH_PREFIX = "Preregistration document SHA-256 (computed over this document excluding this line): "
MANIFEST = "lab/prereg/stronger-model-manifest.json"
CODE_COMMIT = "9cb7ca4"


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def doc_hash():
    lines = (ROOT / DOC).read_text().splitlines(keepends=True)
    return hashlib.sha256("".join(l for l in lines if not l.startswith(HASH_PREFIX)).encode()).hexdigest()


def frozen_files():
    out = [str(p.relative_to(ROOT)) for p in sorted((ROOT / "lab/nasha_lab").rglob("*")) if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"]
    return out + ["lab/requirements.txt", "lab/results/planner_qwen7b_raw.json", "lab/results/planner_deterministic.json"]


def main():
    ids = [r["id"] for r in json.loads((ROOT / "lab/results/planner_qwen7b_raw.json").read_text())["rows"]]
    cur = dict(preregistration_commit_parent=CODE_COMMIT, scenario_ids=ids, scenario_ids_sha256=hashlib.sha256("\n".join(ids).encode()).hexdigest(),
               frozen_file_sha256={f: sha(f) for f in frozen_files()}, preregistration_document=DOC, preregistration_document_sha256=doc_hash())
    if "--write" in sys.argv:
        (ROOT / MANIFEST).write_text(json.dumps(cur, indent=1) + "\n"); print("written", MANIFEST); return 0
    old = json.loads((ROOT / MANIFEST).read_text()); bad = [k for k in cur if cur[k] != old.get(k)]
    if bad:
        for k in bad:
            if isinstance(cur[k], dict): print("MISMATCH", k, [f for f in cur[k] if cur[k][f] != old[k].get(f)])
            else: print("MISMATCH", k)
        return 1
    print("manifest OK:", len(cur["frozen_file_sha256"]), "files,", len(ids), "scenario ids, doc", cur["preregistration_document_sha256"]); return 0


if __name__ == "__main__":
    sys.exit(main())
