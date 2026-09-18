# perplexity_model.py
import math
from typing import Any


class GPT2Perplexity:
    def __init__(self, model_name: str = "gpt2") -> None:
        from transformers import (  # type: ignore[import-not-found]
            AutoModelForCausalLM,
            AutoTokenizer,
        )

        self._tokenizer: Any = AutoTokenizer.from_pretrained(model_name)
        self._model: Any = AutoModelForCausalLM.from_pretrained(model_name)
        self._model.eval()

    def perplexity(self, text: str) -> float:
        import torch  # type: ignore[import-not-found]

        inputs = self._tokenizer(text, return_tensors="pt")
        with torch.no_grad():
            outputs = self._model(**inputs, labels=inputs["input_ids"])
        return float(math.exp(outputs.loss.item()))
