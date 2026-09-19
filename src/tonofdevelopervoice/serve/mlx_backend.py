# mlx_backend.py
import time
from typing import Any, Literal

from tonofdevelopervoice.serve.backend import RewriteResult
from tonofdevelopervoice.serve.generation import GenerationSettings, completion_budget
from tonofdevelopervoice.serve.prompts import PROMPT_PREFIX_TEMPLATE


class MlxInferenceBackend:
    def __init__(self, model_dir: str, settings: GenerationSettings | None = None) -> None:
        from mlx_lm import load  # type: ignore[import-not-found]

        self._settings = settings if settings is not None else GenerationSettings()
        model, tokenizer = load(model_dir)
        self._model: Any = model
        self._tokenizer: Any = tokenizer

    def rewrite(self, text: str) -> RewriteResult:
        from mlx_lm import stream_generate
        from mlx_lm.sample_utils import (  # type: ignore[import-not-found]
            make_logits_processors,
            make_sampler,
        )

        start = time.monotonic()
        prompt = PROMPT_PREFIX_TEMPLATE.format(input=text)
        prompt_tokens = len(self._tokenizer.encode(prompt))

        if prompt_tokens > self._settings.max_prompt_tokens:
            return RewriteResult(
                text="",
                finish_reason="input_too_long",
                prompt_tokens=prompt_tokens,
                completion_tokens=0,
                seconds=time.monotonic() - start,
                tokens_per_second=None,
                peak_memory_gb=None,
            )

        budget = completion_budget(prompt_tokens, self._settings)
        sampler = make_sampler(temp=self._settings.temperature, top_p=self._settings.top_p)
        logits_processors = make_logits_processors(
            repetition_penalty=self._settings.repetition_penalty
        )

        pieces: list[str] = []
        last_response: Any = None
        for response in stream_generate(
            self._model,
            self._tokenizer,
            prompt,
            max_tokens=budget,
            sampler=sampler,
            logits_processors=logits_processors,
        ):
            pieces.append(response.text)
            last_response = response

        seconds = time.monotonic() - start
        if last_response is None:
            return RewriteResult(
                text="",
                finish_reason="stop",
                prompt_tokens=prompt_tokens,
                completion_tokens=0,
                seconds=seconds,
                tokens_per_second=None,
                peak_memory_gb=None,
            )

        finish_reason: Literal["stop", "length"] = (
            "length" if last_response.finish_reason == "length" else "stop"
        )
        return RewriteResult(
            text="".join(pieces).strip(),
            finish_reason=finish_reason,
            prompt_tokens=last_response.prompt_tokens,
            completion_tokens=last_response.generation_tokens,
            seconds=seconds,
            tokens_per_second=last_response.generation_tps,
            peak_memory_gb=last_response.peak_memory,
        )
