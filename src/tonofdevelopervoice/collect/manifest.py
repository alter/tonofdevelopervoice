# manifest.py
import json
from pathlib import Path


def build_manifest(raw_dir: Path) -> dict[str, int]:
    manifest: dict[str, int] = {}
    for path in sorted(raw_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as f:
            manifest[path.stem] = sum(1 for _ in f)
    return manifest


def write_manifest(raw_dir: Path, out_path: Path) -> dict[str, int]:
    manifest = build_manifest(raw_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
