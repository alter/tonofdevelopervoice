# generation.py
from dataclasses import dataclass


@dataclass(frozen=True)
class GenerationSettings:
    max_prompt_tokens: int = 2048
    max_completion_tokens: int = 2048
    completion_margin: int = 64
    temperature: float = 0.0
    top_p: float = 1.0
    repetition_penalty: float | None = None


def completion_budget(input_tokens: int, settings: GenerationSettings | None = None) -> int:
    resolved = settings if settings is not None else GenerationSettings()
    return min(resolved.max_completion_tokens, input_tokens + resolved.completion_margin)
