# metrics.py
import math
from typing import Protocol


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...


class ReferenceScorer(Protocol):
    def score(self, candidate: str, reference: str) -> float: ...


class PerplexityModel(Protocol):
    def perplexity(self, text: str) -> float: ...


class Judge(Protocol):
    def prefers_first(self, sample_a: str, sample_b: str) -> bool: ...


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def content_similarity(output: str, source: str, embedder: Embedder) -> float:
    return cosine_similarity(embedder.embed(output), embedder.embed(source))


def reference_fidelity(output: str, reference: str, scorer: ReferenceScorer) -> float:
    return scorer.score(output, reference)


def fluency_perplexity(text: str, model: PerplexityModel) -> float:
    return model.perplexity(text)


def judge_win_rate(pairs: list[tuple[str, str]], judge: Judge) -> float:
    if not pairs:
        return 0.0
    wins = sum(1 for model_output, real in pairs if judge.prefers_first(model_output, real))
    return wins / len(pairs)
