"""Bundle source, model and audit reports, never raw third-party logs or live DB."""
import importlib.metadata
import json
import platform
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent/"output/ae300_backend_v1"
OUT.mkdir(parents=True, exist_ok=True)
names = ["numpy", "fastapi", "uvicorn", "pytest", "httpx", "starlette", "pydantic", "pydantic-core",
         "annotated-types", "typing-extensions", "typing-inspection", "annotated-doc", "anyio", "idna",
         "certifi", "httpcore", "h11", "click", "colorama", "iniconfig", "packaging", "pluggy", "pygments"]
lock = f"# Exact versions tested on Windows / Python {platform.python_version()}; no executable model serialization.\n"
lock += "\n".join(f"{name}=={importlib.metadata.version(name)}" for name in names)+"\n"
(ROOT/"requirements-lock.txt").write_text(lock, encoding="utf-8")
package = OUT/"AE300_Backend_v1.zip"
with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in ROOT.rglob("*"):
        if not path.is_file(): continue
        rel = path.relative_to(ROOT)
        if any(part in {".venv", "data", "__pycache__", ".pytest_cache"} or part.endswith(".egg-info") for part in rel.parts): continue
        if path.suffix in {".sqlite3", ".db"} or "sqlite3-" in path.name or path.name == "replay.jsonl": continue
        archive.write(path, "AE300_Backend/"+rel.as_posix())
with zipfile.ZipFile(package) as archive:
    assert archive.testzip() is None
    assert "AE300_Backend/artifacts/model.json" in archive.namelist()
    assert "AE300_Backend/config/cad_sensor_map.json" in archive.namelist()
    print(json.dumps({"package": str(package), "files": len(archive.namelist()), "bytes": package.stat().st_size}))
