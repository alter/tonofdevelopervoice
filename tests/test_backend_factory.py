# test_backend_factory.py
import json
import sys
from collections.abc import Generator
from pathlib import Path
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


@pytest.fixture
def adapter_dir(tmp_path: Path) -> str:
    (tmp_path / "adapter_config.json").write_text("{}", encoding="utf-8")
    return str(tmp_path)


@pytest.fixture
def mlx_model_dir(tmp_path: Path) -> str:
    (tmp_path / "config.json").write_text(json.dumps({"quantization": {"bits": 4}}))
    return str(tmp_path)


def test_default_backend_returns_unsloth_backend_when_backend_env_var_is_unsloth(
    monkeypatch: pytest.MonkeyPatch, fake_unsloth: MagicMock, adapter_dir: str
) -> None:
    from tonofdevelopervoice.serve.unsloth_backend import UnslothInferenceBackend

    monkeypatch.setenv("TONOFDEVELOPERVOICE_MODEL_DIR", adapter_dir)
    monkeypatch.setenv("TONOFDEVELOPERVOICE_BACKEND", "unsloth")
    monkeypatch.setattr("tonofdevelopervoice.serve.factory._cuda_available", lambda: True)

    backend = default_backend()

    assert isinstance(backend, UnslothInferenceBackend)
    _, kwargs = fake_unsloth.from_pretrained.call_args
    assert kwargs["model_name"] == adapter_dir


def test_default_backend_does_not_warn_when_env_var_set(
    monkeypatch: pytest.MonkeyPatch,
    fake_unsloth: MagicMock,
    adapter_dir: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("TONOFDEVELOPERVOICE_MODEL_DIR", adapter_dir)
    monkeypatch.setenv("TONOFDEVELOPERVOICE_BACKEND", "unsloth")
    monkeypatch.setattr("tonofdevelopervoice.serve.factory._cuda_available", lambda: True)
    default_backend()
    assert capsys.readouterr().err == ""


def test_default_backend_auto_selects_unsloth_for_an_adapter_dir_when_cuda_available(
    monkeypatch: pytest.MonkeyPatch, fake_unsloth: MagicMock, adapter_dir: str
) -> None:
    from tonofdevelopervoice.serve.unsloth_backend import UnslothInferenceBackend

    monkeypatch.setenv("TONOFDEVELOPERVOICE_MODEL_DIR", adapter_dir)
    monkeypatch.delenv("TONOFDEVELOPERVOICE_BACKEND", raising=False)
    monkeypatch.setattr("tonofdevelopervoice.serve.factory._cuda_available", lambda: True)

    backend = default_backend()

    assert isinstance(backend, UnslothInferenceBackend)


def test_default_backend_raises_for_an_adapter_dir_when_cuda_unavailable(
    monkeypatch: pytest.MonkeyPatch, adapter_dir: str
) -> None:
    monkeypatch.setenv("TONOFDEVELOPERVOICE_MODEL_DIR", adapter_dir)
    monkeypatch.delenv("TONOFDEVELOPERVOICE_BACKEND", raising=False)
    monkeypatch.setattr("tonofdevelopervoice.serve.factory._cuda_available", lambda: False)

    with pytest.raises(RuntimeError, match="docs/runbook-deploy.md"):
        default_backend()


def test_default_backend_picks_mlx_for_a_quantised_config(
    monkeypatch: pytest.MonkeyPatch, mlx_model_dir: str
) -> None:
    fake_mlx_backend_cls = MagicMock()
    fake_mlx_module = ModuleType("tonofdevelopervoice.serve.mlx_backend")
    fake_mlx_module.MlxInferenceBackend = fake_mlx_backend_cls  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "tonofdevelopervoice.serve.mlx_backend", fake_mlx_module)

    monkeypatch.setenv("TONOFDEVELOPERVOICE_MODEL_DIR", mlx_model_dir)
    monkeypatch.delenv("TONOFDEVELOPERVOICE_BACKEND", raising=False)

    default_backend()

    fake_mlx_backend_cls.assert_called_once_with(mlx_model_dir)


def test_default_backend_explicit_mlx_choice_skips_directory_sniffing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake_mlx_backend_cls = MagicMock()
    fake_mlx_module = ModuleType("tonofdevelopervoice.serve.mlx_backend")
    fake_mlx_module.MlxInferenceBackend = fake_mlx_backend_cls  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "tonofdevelopervoice.serve.mlx_backend", fake_mlx_module)

    monkeypatch.setenv("TONOFDEVELOPERVOICE_MODEL_DIR", str(tmp_path))
    monkeypatch.setenv("TONOFDEVELOPERVOICE_BACKEND", "mlx")

    default_backend()

    fake_mlx_backend_cls.assert_called_once_with(str(tmp_path))


def test_default_backend_rejects_a_directory_with_unparsable_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "config.json").write_text("not json", encoding="utf-8")
    monkeypatch.setenv("TONOFDEVELOPERVOICE_MODEL_DIR", str(tmp_path))
    monkeypatch.delenv("TONOFDEVELOPERVOICE_BACKEND", raising=False)

    with pytest.raises(ValueError, match="cannot tell what kind of model"):
        default_backend()


def test_default_backend_rejects_a_directory_that_is_neither(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("TONOFDEVELOPERVOICE_MODEL_DIR", str(tmp_path))
    monkeypatch.delenv("TONOFDEVELOPERVOICE_BACKEND", raising=False)

    with pytest.raises(ValueError, match="cannot tell what kind of model"):
        default_backend()


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


def test_default_backend_rejects_unknown_backend_choice(
    monkeypatch: pytest.MonkeyPatch, adapter_dir: str
) -> None:
    monkeypatch.setenv("TONOFDEVELOPERVOICE_MODEL_DIR", adapter_dir)
    monkeypatch.setenv("TONOFDEVELOPERVOICE_BACKEND", "something-else")

    with pytest.raises(ValueError, match="TONOFDEVELOPERVOICE_BACKEND"):
        default_backend()
