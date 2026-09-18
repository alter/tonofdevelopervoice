# backend.py
from typing import Protocol, runtime_checkable


@runtime_checkable
class InferenceBackend(Protocol):
    def rewrite(self, text: str) -> str: ...


class StubInferenceBackend:
    def __init__(self, prefix: str = "[rewritten] ") -> None:
        self._prefix = prefix

    def rewrite(self, text: str) -> str:
        return f"{self._prefix}{text.strip()}"
