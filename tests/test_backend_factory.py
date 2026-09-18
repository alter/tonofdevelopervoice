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


def test_default_backend_returns_unsloth_backend_when_env_var_set(
    monkeypatch: pytest.MonkeyPatch, fake_unsloth: MagicMock
) -> None:
    from tonofdevelopervoice.serve.unsloth_backend import UnslothInferenceBackend

    monkeypatch.setenv("TONOFDEVELOPERVOICE_MODEL_DIR", "training/output")

    backend = default_backend()

    assert isinstance(backend, UnslothInferenceBackend)
    _, kwargs = fake_unsloth.from_pretrained.call_args
    assert kwargs["model_name"] == "training/output"
