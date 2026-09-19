# unsloth_backend.py
import time
from typing import Any, Literal

from tonofdevelopervoice.serve.backend import RewriteResult
from tonofdevelopervoice.serve.generation import GenerationSettings, completion_budget
from tonofdevelopervoice.serve.prompts import PROMPT_PREFIX_TEMPLATE


class UnslothInferenceBackend:
    def __init__(self, model_dir: str, settings: GenerationSettings | None = None) -> None:
        from unsloth import FastLanguageModel  # type: ignore[import-not-found]

        self._settings = settings if settings is not None else GenerationSettings()
        model, tokenizer = FastLanguageModel.from_pretrained(model_name=model_dir)
        FastLanguageModel.for_inference(model)
        self._model: Any = model
        self._tokenizer: Any = tokenizer

    def rewrite(self, text: str) -> RewriteResult:
        start = time.monotonic()
        prompt = PROMPT_PREFIX_TEMPLATE.format(input=text)
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
        prompt_tokens = len(inputs["input_ids"][0])

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
        output_ids = self._model.generate(**inputs, max_new_tokens=budget)
        new_ids = output_ids[0][prompt_tokens:]
        completion_tokens = len(new_ids)
        generated: str = self._tokenizer.decode(new_ids, skip_special_tokens=True).strip()
        seconds = time.monotonic() - start
        finish_reason: Literal["stop", "length"] = (
            "length" if completion_tokens >= budget else "stop"
        )
        return RewriteResult(
            text=generated,
            finish_reason=finish_reason,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            seconds=seconds,
            tokens_per_second=(completion_tokens / seconds) if seconds > 0 else None,
            peak_memory_gb=None,
        )
