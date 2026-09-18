# test_batch_rewrite.py
import sys
from pathlib import Path

import pytest

from tonofdevelopervoice.serve.backend import StubInferenceBackend

sys.path.insert(0, "scripts")

from batch_rewrite import run  # noqa: E402


def test_batch_rewrite_writes_one_output_per_input(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("fix bug in handler")
    (tmp_path / "b.txt").write_text("add feature flag")

    exit_code = run(["--dir", str(tmp_path)], StubInferenceBackend())

    assert exit_code == 0
    assert (tmp_path / "a.rewritten.txt").read_text() == "[rewritten] fix bug in handler"
    assert (tmp_path / "b.rewritten.txt").read_text() == "[rewritten] add feature flag"


def test_batch_rewrite_writes_to_out_dir_when_given(tmp_path: Path) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    (in_dir / "a.txt").write_text("fix bug")

    exit_code = run(["--dir", str(in_dir), "--out-dir", str(out_dir)], StubInferenceBackend())

    assert exit_code == 0
    assert (out_dir / "a.rewritten.txt").read_text() == "[rewritten] fix bug"
    assert not (in_dir / "a.rewritten.txt").exists()


def test_batch_rewrite_skips_already_rewritten_files(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("fix bug")
    (tmp_path / "a.rewritten.txt").write_text("[rewritten] fix bug")

    exit_code = run(["--dir", str(tmp_path)], StubInferenceBackend())

    assert exit_code == 0
    assert (tmp_path / "a.rewritten.txt").read_text() == "[rewritten] fix bug"


def test_batch_rewrite_skips_empty_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "empty.txt").write_text("   ")

    exit_code = run(["--dir", str(tmp_path)], StubInferenceBackend())

    assert exit_code == 0
    assert not (tmp_path / "empty.rewritten.txt").exists()
    assert "skipping empty file" in capsys.readouterr().err


def test_batch_rewrite_errors_on_missing_directory(tmp_path: Path) -> None:
    exit_code = run(["--dir", str(tmp_path / "does-not-exist")], StubInferenceBackend())
    assert exit_code == 1


def test_batch_rewrite_errors_when_no_files_match(tmp_path: Path) -> None:
    exit_code = run(["--dir", str(tmp_path)], StubInferenceBackend())
    assert exit_code == 1
