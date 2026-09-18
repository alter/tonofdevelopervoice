# unsloth_backend.py
from typing import Any

from tonofdevelopervoice.serve.prompts import PROMPT_PREFIX_TEMPLATE


class UnslothInferenceBackend:
    def __init__(self, model_dir: str, max_new_tokens: int = 256) -> None:
        from unsloth import FastLanguageModel  # type: ignore[import-not-found]

        self._max_new_tokens = max_new_tokens
        model, tokenizer = FastLanguageModel.from_pretrained(model_name=model_dir)
        FastLanguageModel.for_inference(model)
        self._model: Any = model
        self._tokenizer: Any = tokenizer

    def rewrite(self, text: str) -> str:
        prompt = PROMPT_PREFIX_TEMPLATE.format(input=text)
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
        output_ids = self._model.generate(**inputs, max_new_tokens=self._max_new_tokens)
        generated: str = self._tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return generated[len(prompt) :].strip()
