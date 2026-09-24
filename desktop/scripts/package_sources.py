"""Create a source + prepared assets handoff, excluding logs and runtime data."""
from pathlib import Path
import hashlib
import zipfile

root = Path(__file__).resolve().parents[2]
output = root / 'output' / 'ae300_desktop_v1'
output.mkdir(parents=True, exist_ok=True)
archive = output / 'AeroTrace-Desktop-Source-0.1.0.zip'
trees = [
    'desktop/src', 'desktop/electron', 'desktop/scripts', 'desktop/tests',
    'desktop/public', 'desktop/build', 'backend/aerotrace', 'backend/tests',
    'backend/docs', 'backend/config',
]
files = [
    'desktop/README.md', 'desktop/VALIDATION.md', 'desktop/FAULT_INJECTION.md', 'desktop/package.json',
    'desktop/pnpm-lock.yaml', 'desktop/pnpm-workspace.yaml', 'desktop/tsconfig.json',
    'desktop/webpack.config.cjs', 'desktop/index.html', 'desktop/.gitignore',
    'desktop/python/desktop_server.py', 'backend/pyproject.toml', 'backend/README.md',
    'backend/artifacts/model.json', 'backend/artifacts/data_audit.json',
    'backend/artifacts/data_provenance.json', 'backend/artifacts/evaluation.json',
    'backend/artifacts/split.json', 'backend/artifacts/VALIDATION_REPORT.md',
]
selected = [root / name for name in files]
for tree in trees:
    selected.extend(p for p in (root / tree).rglob('*') if p.is_file()
                    and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts)
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
    for path in sorted(set(selected)):
        if path.exists():
            bundle.write(path, path.relative_to(root).as_posix())
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    names = bundle.namelist()
    assert 'desktop/public/engine.glb' in names
    assert not any('/preview-data/' in name or name.endswith('.sqlite3') for name in names)
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
(output / 'AeroTrace-Desktop-Source-0.1.0.sha256').write_text(f'{digest}  {archive.name}\n')
print(f'Validated {len(names)} entries: {archive} ({archive.stat().st_size:,} bytes)')
print(f'SHA256: {digest}')
