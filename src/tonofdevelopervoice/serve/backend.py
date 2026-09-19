# backend.py
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

FinishReason = Literal["stop", "length", "input_too_long"]


@dataclass(frozen=True)
class RewriteResult:
    text: str
    finish_reason: FinishReason
    prompt_tokens: int
    completion_tokens: int
    seconds: float
    tokens_per_second: float | None
    peak_memory_gb: float | None


@runtime_checkable
class InferenceBackend(Protocol):
    def rewrite(self, text: str) -> RewriteResult: ...


class StubInferenceBackend:
    def __init__(self, prefix: str = "[rewritten] ") -> None:
        self._prefix = prefix

    def rewrite(self, text: str) -> RewriteResult:
        stripped = text.strip()
        output = f"{self._prefix}{stripped}"
        return RewriteResult(
            text=output,
            finish_reason="stop",
            prompt_tokens=len(stripped.split()),
            completion_tokens=len(output.split()),
            seconds=0.0,
            tokens_per_second=None,
            peak_memory_gb=None,
        )
