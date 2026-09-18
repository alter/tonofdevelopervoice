# peft_backend.py
from typing import Any

from tonofdevelopervoice.serve.prompts import PROMPT_PREFIX_TEMPLATE

# The adapter's own adapter_config.json points at the bitsandbytes 4-bit base
# ("unsloth/qwen3-8b-base-unsloth-bnb-4bit"), which needs bitsandbytes/CUDA to load.
# This backend targets platforms without CUDA (e.g. Apple Silicon, where Unsloth
# routes through its MLX backend instead -- which as of unsloth_zoo 2026.9.5 fails to
# load a bitsandbytes-trained PEFT adapter), so it loads the same architecture from its
# full-precision repo instead and applies the LoRA adapter on top of that.
BASE_MODEL_NAME = "Qwen/Qwen3-8B-Base"


def _select_device() -> str:
    import torch  # type: ignore[import-not-found]

    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class PeftInferenceBackend:
    def __init__(self, adapter_dir: str, max_new_tokens: int = 256) -> None:
        import torch
        from peft import PeftModel  # type: ignore[import-not-found]
        from transformers import (  # type: ignore[import-not-found]
            AutoModelForCausalLM,
            AutoTokenizer,
        )

        self._max_new_tokens = max_new_tokens
        self._device = _select_device()

        tokenizer = AutoTokenizer.from_pretrained(adapter_dir)
        base_model = AutoModelForCausalLM.from_pretrained(BASE_MODEL_NAME, dtype=torch.float16)
        model = PeftModel.from_pretrained(base_model, adapter_dir)
        model = model.to(self._device)
        model.eval()

        self._tokenizer: Any = tokenizer
        self._model: Any = model

    def rewrite(self, text: str) -> str:
        import torch

        prompt = PROMPT_PREFIX_TEMPLATE.format(input=text)
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._device)
        with torch.no_grad():
            output_ids = self._model.generate(**inputs, max_new_tokens=self._max_new_tokens)
        generated: str = self._tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return generated[len(prompt) :].strip()
