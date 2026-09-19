# test_cli.py
from pathlib import Path
from typing import Literal

import pytest

from tonofdevelopervoice.cli import main, run
from tonofdevelopervoice.serve.backend import RewriteResult, StubInferenceBackend


class FakeBackend:
    def __init__(
        self, finish_reason: Literal["stop", "length", "input_too_long"], text: str = "output"
    ) -> None:
        self._finish_reason = finish_reason
        self._text = text

    def rewrite(self, text: str) -> RewriteResult:
        return RewriteResult(
            text=self._text,
            finish_reason=self._finish_reason,
            prompt_tokens=1,
            completion_tokens=1,
            seconds=0.0,
            tokens_per_second=None,
            peak_memory_gb=None,
        )


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


def test_cli_exit_code_2_on_length(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = run(["--text", "x"], FakeBackend("length"))
    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out.strip() == "output"
    assert "length" in captured.err


def test_cli_exit_code_2_on_input_too_long(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = run(["--text", "x"], FakeBackend("input_too_long", text=""))
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "input_too_long" in captured.err


def test_cli_exit_code_0_on_stop(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = run(["--text", "x"], FakeBackend("stop"))
    assert exit_code == 0
