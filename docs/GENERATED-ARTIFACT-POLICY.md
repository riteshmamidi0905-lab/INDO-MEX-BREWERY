# Generated artifact policy (repository size)
History is not rewritten. Sprint 15 committed one 12 MB ASCII STL; Sprint 16 converted meshes to binary.
- **Commit:** the generator script, its parameters (`specs.json`), summary CSV and a PNG preview. These are small, diffable and enough to rebuild everything.
- **Do not commit:** regenerable meshes (STL/glTF) above ~1 MB. Glass V2 STL files (~90 MB for ten) are git-ignored; rebuild with `python3 tools/glass_v2.py build`. If a manufacturer needs a file, generate it then and send it out of band; if a mesh must be kept, store it as binary STL or glTF.
- **Recommendation:** keep this ratio (source + script + metadata, not outputs). Check `du -sh` on `git status` additions before committing.
