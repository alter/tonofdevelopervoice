# test_manifest.py
import json
from pathlib import Path

from tonofdevelopervoice.collect.manifest import build_manifest, write_manifest


def test_build_manifest_counts_lines_per_repo_file(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "linux.jsonl").write_text('{"a":1}\n{"a":2}\n', encoding="utf-8")
    (raw_dir / "nginx.jsonl").write_text('{"a":1}\n', encoding="utf-8")

    manifest = build_manifest(raw_dir)

    assert manifest == {"linux": 2, "nginx": 1}


def test_build_manifest_empty_dir_yields_empty_manifest(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    assert build_manifest(raw_dir) == {}


def test_write_manifest_writes_json_file(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "apache.jsonl").write_text('{"a":1}\n{"a":2}\n{"a":3}\n', encoding="utf-8")
    out_path = tmp_path / "manifest.json"

    manifest = write_manifest(raw_dir, out_path)

    assert manifest == {"apache": 3}
    assert json.loads(out_path.read_text(encoding="utf-8")) == {"apache": 3}
