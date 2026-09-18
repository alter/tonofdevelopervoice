# test_backend_factory.py
import sys
from collections.abc import Generator
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from tonofdevelopervoice.serve.backend import StubInferenceBackend
from tonofdevelopervoice.serve.factory import default_backend


def test_default_backend_returns_stub_when_env_var_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TONOFDEVELOPERVOICE_MODEL_DIR", raising=False)
    backend = default_backend()
    assert isinstance(backend, StubInferenceBackend)


def test_default_backend_warns_on_stderr_when_env_var_unset(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("TONOFDEVELOPERVOICE_MODEL_DIR", raising=False)
    default_backend()
    assert "TONOFDEVELOPERVOICE_MODEL_DIR" in capsys.readouterr().err


@pytest.fixture
def fake_unsloth() -> Generator[MagicMock, None, None]:
    fake_model = MagicMock()
    fake_tokenizer = MagicMock()
    fake_flm = MagicMock()
    fake_flm.from_pretrained.return_value = (fake_model, fake_tokenizer)

    module = ModuleType("unsloth")
    module.FastLanguageModel = fake_flm  # type: ignore[attr-defined]

    original = sys.modules.get("unsloth")
    sys.modules["unsloth"] = module
    try:
        yield fake_flm
    finally:
        if original is not None:
            sys.modules["unsloth"] = original
        else:
            del sys.modules["unsloth"]


def test_default_backend_returns_unsloth_backend_when_backend_env_var_is_unsloth(
    monkeypatch: pytest.MonkeyPatch, fake_unsloth: MagicMock
) -> None:
    from tonofdevelopervoice.serve.unsloth_backend import UnslothInferenceBackend

    monkeypatch.setenv("TONOFDEVELOPERVOICE_MODEL_DIR", "training/output")
    monkeypatch.setenv("TONOFDEVELOPERVOICE_BACKEND", "unsloth")

    backend = default_backend()

    assert isinstance(backend, UnslothInferenceBackend)
    _, kwargs = fake_unsloth.from_pretrained.call_args
    assert kwargs["model_name"] == "training/output"


def test_default_backend_does_not_warn_when_env_var_set(
    monkeypatch: pytest.MonkeyPatch,
    fake_unsloth: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("TONOFDEVELOPERVOICE_MODEL_DIR", "training/output")
    monkeypatch.setenv("TONOFDEVELOPERVOICE_BACKEND", "unsloth")
    default_backend()
    assert capsys.readouterr().err == ""


def test_default_backend_auto_selects_unsloth_when_cuda_available(
    monkeypatch: pytest.MonkeyPatch, fake_unsloth: MagicMock
) -> None:
    from tonofdevelopervoice.serve.unsloth_backend import UnslothInferenceBackend

    monkeypatch.setenv("TONOFDEVELOPERVOICE_MODEL_DIR", "training/output")
    monkeypatch.delenv("TONOFDEVELOPERVOICE_BACKEND", raising=False)
    monkeypatch.setattr("tonofdevelopervoice.serve.factory._cuda_available", lambda: True)

    backend = default_backend()

    assert isinstance(backend, UnslothInferenceBackend)


def test_default_backend_auto_selects_peft_when_cuda_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_peft_backend_cls = MagicMock()
    fake_peft_module = ModuleType("tonofdevelopervoice.serve.peft_backend")
    fake_peft_module.PeftInferenceBackend = fake_peft_backend_cls  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "tonofdevelopervoice.serve.peft_backend", fake_peft_module)

    monkeypatch.setenv("TONOFDEVELOPERVOICE_MODEL_DIR", "training/output")
    monkeypatch.delenv("TONOFDEVELOPERVOICE_BACKEND", raising=False)
    monkeypatch.setattr("tonofdevelopervoice.serve.factory._cuda_available", lambda: False)

    default_backend()

    fake_peft_backend_cls.assert_called_once_with("training/output")


def test_default_backend_explicit_peft_choice(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_peft_backend_cls = MagicMock()
    fake_peft_module = ModuleType("tonofdevelopervoice.serve.peft_backend")
    fake_peft_module.PeftInferenceBackend = fake_peft_backend_cls  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "tonofdevelopervoice.serve.peft_backend", fake_peft_module)

    monkeypatch.setenv("TONOFDEVELOPERVOICE_MODEL_DIR", "training/output")
    monkeypatch.setenv("TONOFDEVELOPERVOICE_BACKEND", "peft")

    default_backend()

    fake_peft_backend_cls.assert_called_once_with("training/output")


def test_cuda_available_returns_false_when_torch_not_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tonofdevelopervoice.serve.factory import _cuda_available

    monkeypatch.setitem(sys.modules, "torch", None)
    assert _cuda_available() is False


def test_cuda_available_reflects_torch_cuda_is_available(monkeypatch: pytest.MonkeyPatch) -> None:
    from tonofdevelopervoice.serve.factory import _cuda_available

    for expected in (True, False):
        fake_torch = ModuleType("torch")
        fake_cuda = ModuleType("torch.cuda")
        fake_cuda.is_available = lambda expected=expected: expected  # type: ignore[attr-defined]
        fake_torch.cuda = fake_cuda  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "torch", fake_torch)
        assert _cuda_available() is expected


def test_default_backend_rejects_unknown_backend_choice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TONOFDEVELOPERVOICE_MODEL_DIR", "training/output")
    monkeypatch.setenv("TONOFDEVELOPERVOICE_BACKEND", "something-else")

    with pytest.raises(ValueError, match="TONOFDEVELOPERVOICE_BACKEND"):
        default_backend()
