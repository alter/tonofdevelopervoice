# test_cli.py
from pathlib import Path

import pytest

from tonofdevelopervoice.cli import main, run
from tonofdevelopervoice.serve.backend import StubInferenceBackend


def test_cli_rewrites_text_arg(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = run(["--text", "fix bug"], StubInferenceBackend())
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "[rewritten] fix bug"


def test_cli_rewrites_file_input(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    input_file = tmp_path / "input.txt"
    input_file.write_text("add feature flag\n")

    exit_code = run(["--file", str(input_file)], StubInferenceBackend())
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == "[rewritten] add feature flag"


def test_cli_reads_from_stdin_when_no_args(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO("fix null pointer\n"))

    exit_code = run([], StubInferenceBackend())
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == "[rewritten] fix null pointer"


def test_cli_errors_on_missing_file(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = run(["--file", "/no/such/file.txt"], StubInferenceBackend())
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "not found" in captured.err


def test_cli_errors_on_empty_input(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = run(["--text", "   "], StubInferenceBackend())
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "no input" in captured.err


def test_main_uses_stub_backend_and_argv(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("TONOFDEVELOPERVOICE_MODEL_DIR", raising=False)
    monkeypatch.setattr("sys.argv", ["tonofdevelopervoice", "--text", "fix bug"])
    exit_code = main()
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "[rewritten] fix bug"


def test_cli_rejects_both_text_and_file(tmp_path: Path) -> None:
    input_file = tmp_path / "input.txt"
    input_file.write_text("x")
    with pytest.raises(SystemExit):
        run(["--text", "a", "--file", str(input_file)], StubInferenceBackend())
