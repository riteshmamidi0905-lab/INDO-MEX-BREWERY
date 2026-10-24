"""Dependency-free frontend build. Copies only reviewed local assets to a NEW build dir."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def build(destination):
    src=Path(__file__).with_name('ui')
    destination=Path(destination)
    if destination.exists():
        raise FileExistsError('Choose a new output directory; builds never delete existing files')
    for path in src.rglob('*'):
        if path.is_symlink(): raise ValueError('No symlink assets')
    html=(src/'index.html').read_text()
    if 'https://' in html or 'http://' in html:
        raise ValueError('Frontend must not load remote dependencies')
    if not all(f'/{name}' in html for name in ('app.js','styles.css')):
        raise ValueError('Missing entry assets')
    shutil.copytree(src,destination)
    files={str(p.relative_to(destination)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(destination.rglob('*')) if p.is_file()}
    (destination/'build-manifest.json').write_text(json.dumps({'files':files,'remote_assets':False},indent=2)+'\n')
    return files

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--out',required=True)
    args=p.parse_args()
    print('Built',len(build(args.out)),'local assets')
