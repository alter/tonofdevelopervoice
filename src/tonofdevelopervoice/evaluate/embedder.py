# embedder.py
from typing import Any


class MiniLMEmbedder:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]

        self._model: Any = SentenceTransformer(model_name)

    def embed(self, text: str) -> list[float]:
        vector = self._model.encode(text)
        return [float(x) for x in vector]
