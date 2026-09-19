# test_mlx_backend.py
import sys
from collections.abc import Generator
from dataclasses import dataclass
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock

import pytest


@dataclass
class FakeGenerationResponse:
    text: str
    finish_reason: str | None
    prompt_tokens: int = 5
    generation_tokens: int = 1
    generation_tps: float = 42.0
    peak_memory: float = 3.5


class FakeTokenizer:
    def encode(self, text: str) -> list[int]:
        return list(range(len(text.split())))


@pytest.fixture
def fake_mlx_lm() -> Generator[dict[str, Any], None, None]:
    fake_model = MagicMock()
    fake_tokenizer = FakeTokenizer()
    fake_load = MagicMock(return_value=(fake_model, fake_tokenizer))
    fake_stream_generate = MagicMock()
    fake_make_sampler = MagicMock(return_value="sampler")
    fake_make_logits_processors = MagicMock(return_value="logits_processors")

    mlx_lm_module = ModuleType("mlx_lm")
    mlx_lm_module.load = fake_load  # type: ignore[attr-defined]
    mlx_lm_module.stream_generate = fake_stream_generate  # type: ignore[attr-defined]
    sample_utils_module = ModuleType("mlx_lm.sample_utils")
    sample_utils_module.make_sampler = fake_make_sampler  # type: ignore[attr-defined]
    sample_utils_module.make_logits_processors = (  # type: ignore[attr-defined]
        fake_make_logits_processors
    )

    originals = {name: sys.modules.get(name) for name in ("mlx_lm", "mlx_lm.sample_utils")}
    sys.modules["mlx_lm"] = mlx_lm_module
    sys.modules["mlx_lm.sample_utils"] = sample_utils_module
    try:
        yield {
            "model": fake_model,
            "tokenizer": fake_tokenizer,
            "load": fake_load,
            "stream_generate": fake_stream_generate,
        }
    finally:
        for name, original in originals.items():
            if original is not None:
                sys.modules[name] = original
            else:
                del sys.modules[name]


def test_constructs_from_load(fake_mlx_lm: dict[str, Any]) -> None:
    from tonofdevelopervoice.serve.mlx_backend import MlxInferenceBackend

    MlxInferenceBackend("models/v1-mlx-q4")

    fake_mlx_lm["load"].assert_called_once_with("models/v1-mlx-q4")


def test_rewrite_joins_streamed_pieces_and_reports_last_response_fields(
    fake_mlx_lm: dict[str, Any],
) -> None:
    from tonofdevelopervoice.serve.mlx_backend import MlxInferenceBackend

    fake_mlx_lm["stream_generate"].return_value = iter(
        [
            FakeGenerationResponse(text="fix ", finish_reason=None),
            FakeGenerationResponse(
                text="null deref",
                finish_reason="stop",
                prompt_tokens=5,
                generation_tokens=2,
                generation_tps=17.5,
                peak_memory=4.2,
            ),
        ]
    )

    backend = MlxInferenceBackend("models/v1-mlx-q4")
    result = backend.rewrite("fix bug")

    assert result.text == "fix null deref"
    assert result.finish_reason == "stop"
    assert result.prompt_tokens == 5
    assert result.completion_tokens == 2
    assert result.tokens_per_second == 17.5
    assert result.peak_memory_gb == 4.2


def test_rewrite_passes_length_finish_reason_through(
    fake_mlx_lm: dict[str, Any],
) -> None:
    from tonofdevelopervoice.serve.mlx_backend import MlxInferenceBackend

    fake_mlx_lm["stream_generate"].return_value = iter(
        [FakeGenerationResponse(text="cut off", finish_reason="length")]
    )

    backend = MlxInferenceBackend("models/v1-mlx-q4")
    result = backend.rewrite("fix bug")

    assert result.finish_reason == "length"


def test_rewrite_handles_an_empty_generation_stream(
    fake_mlx_lm: dict[str, Any],
) -> None:
    from tonofdevelopervoice.serve.mlx_backend import MlxInferenceBackend

    fake_mlx_lm["stream_generate"].return_value = iter([])

    backend = MlxInferenceBackend("models/v1-mlx-q4")
    result = backend.rewrite("fix bug")

    assert result.text == ""
    assert result.finish_reason == "stop"
    assert result.completion_tokens == 0


def test_rewrite_refuses_input_over_max_prompt_tokens_without_generating(
    fake_mlx_lm: dict[str, Any],
) -> None:
    from tonofdevelopervoice.serve.generation import GenerationSettings
    from tonofdevelopervoice.serve.mlx_backend import MlxInferenceBackend

    backend = MlxInferenceBackend("models/v1-mlx-q4", GenerationSettings(max_prompt_tokens=1))
    result = backend.rewrite("way too long an input for this budget")

    assert result.finish_reason == "input_too_long"
    assert result.text == ""
    fake_mlx_lm["stream_generate"].assert_not_called()


def test_satisfies_inference_backend_protocol(fake_mlx_lm: dict[str, Any]) -> None:
    from tonofdevelopervoice.serve.backend import InferenceBackend
    from tonofdevelopervoice.serve.mlx_backend import MlxInferenceBackend

    backend: InferenceBackend = MlxInferenceBackend("models/v1-mlx-q4")
    assert isinstance(backend, InferenceBackend)
