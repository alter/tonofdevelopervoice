# test_unsloth_backend.py
import sys
from collections.abc import Generator
from types import ModuleType
from unittest.mock import MagicMock

import pytest


class FakeEncoding(dict[str, MagicMock]):
    def to(self, _device: object) -> "FakeEncoding":
        return self


@pytest.fixture
def fake_unsloth() -> Generator[tuple[MagicMock, MagicMock, MagicMock], None, None]:
    fake_model = MagicMock()
    fake_tokenizer = MagicMock()
    fake_fast_language_model = MagicMock()
    fake_fast_language_model.from_pretrained.return_value = (fake_model, fake_tokenizer)

    unsloth_module = ModuleType("unsloth")
    unsloth_module.FastLanguageModel = fake_fast_language_model  # type: ignore[attr-defined]

    original = sys.modules.get("unsloth")
    sys.modules["unsloth"] = unsloth_module
    try:
        yield fake_fast_language_model, fake_model, fake_tokenizer
    finally:
        if original is not None:
            sys.modules["unsloth"] = original
        else:
            del sys.modules["unsloth"]


def test_constructs_model_from_pretrained_with_model_dir(
    fake_unsloth: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    from tonofdevelopervoice.serve.unsloth_backend import UnslothInferenceBackend

    fake_flm, _fake_model, _fake_tokenizer = fake_unsloth
    UnslothInferenceBackend("training/output")

    fake_flm.from_pretrained.assert_called_once()
    _, kwargs = fake_flm.from_pretrained.call_args
    assert kwargs["model_name"] == "training/output"
    fake_flm.for_inference.assert_called_once()


def test_rewrite_builds_prompt_generates_and_decodes(
    fake_unsloth: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    from tonofdevelopervoice.serve.unsloth_backend import UnslothInferenceBackend

    _fake_flm, fake_model, fake_tokenizer = fake_unsloth

    fake_encoded = FakeEncoding({"input_ids": MagicMock(), "attention_mask": MagicMock()})
    fake_tokenizer.return_value = fake_encoded
    fake_model.generate.return_value = ["ids"]
    fake_tokenizer.decode.return_value = (
        "Rewrite the following text in terse, authentic open-source engineering "
        "commit/PR style, preserving its meaning:\n\nfix bug\n\n### Rewritten:\nfix null deref"
    )

    backend = UnslothInferenceBackend("training/output")
    result = backend.rewrite("fix bug")

    assert result == "fix null deref"
    fake_tokenizer.assert_called()
    fake_model.generate.assert_called_once()


def test_satisfies_inference_backend_protocol(
    fake_unsloth: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    from tonofdevelopervoice.serve.backend import InferenceBackend
    from tonofdevelopervoice.serve.unsloth_backend import UnslothInferenceBackend

    backend: InferenceBackend = UnslothInferenceBackend("training/output")
    assert isinstance(backend, InferenceBackend)
