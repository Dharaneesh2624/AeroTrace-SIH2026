"""Download only public CSV examples at an immutable revision; execute no upstream code."""
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

REV = "f9187ca3cd9094c5b547a8186559f5e099976c6d"
BASE = "https://raw.githubusercontent.com/ingramleedy/AustroView/" + REV + "/"
ROOT = Path(__file__).resolve().parents[1]

def get(url):
    with urlopen(Request(url, headers={"User-Agent": "AeroTrace-research/0.1"}), timeout=45) as r:
        data = r.read(10_000_001)
    if len(data) > 10_000_000:
        raise ValueError("Unexpected source size")
    return data

def main():
    out = ROOT / "data" / "public_examples"
    out.mkdir(parents=True, exist_ok=True)
    tree = json.loads(get(f"https://api.github.com/repos/ingramleedy/AustroView/git/trees/{REV}?recursive=1"))
    entries = []
    for entry in tree["tree"]:
        path = entry["path"]
        if not (path.startswith("examples/output/") and path.endswith(".csv")):
            continue
        url = BASE + path
        data = get(url)
        sha = hashlib.sha256(data).hexdigest()
        target = out / Path(path).name
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != sha:
            raise ValueError(f"Refusing to overwrite modified data: {target}")
        target.write_bytes(data)
        entries.append({"file": target.name, "url": url, "sha256": sha, "bytes": len(data)})
    manifest = {"repository": "https://github.com/ingramleedy/AustroView", "commit": REV,
                "kind": "public example, health labels and engine identity unverified", "files": entries,
                "license_note": "README states MIT; no standalone LICENSE found. Raw data excluded from release ZIP."}
    (out / "provenance.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Downloaded {len(entries)} CSV files to {out}")

if __name__ == "__main__":
    main()
