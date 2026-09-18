# test_metrics.py
import pytest

from tonofdevelopervoice.evaluate.metrics import (
    content_similarity,
    cosine_similarity,
    fluency_perplexity,
    judge_win_rate,
    reference_fidelity,
)


class FakeEmbedder:
    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self._vectors = vectors

    def embed(self, text: str) -> list[float]:
        return self._vectors[text]


class FakeScorer:
    def __init__(self, scores: dict[tuple[str, str], float]) -> None:
        self._scores = scores

    def score(self, candidate: str, reference: str) -> float:
        return self._scores[(candidate, reference)]


class FakePerplexityModel:
    def __init__(self, values: dict[str, float]) -> None:
        self._values = values

    def perplexity(self, text: str) -> float:
        return self._values[text]


class FakeJudge:
    def __init__(self, preferences: dict[tuple[str, str], bool]) -> None:
        self._preferences = preferences

    def prefers_first(self, sample_a: str, sample_b: str) -> bool:
        return self._preferences[(sample_a, sample_b)]


def test_cosine_similarity_identical_vectors_is_one() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors_is_zero() -> None:
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_similarity_zero_vector_is_zero() -> None:
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_content_similarity_uses_embedder() -> None:
    embedder = FakeEmbedder({"a": [1.0, 0.0], "b": [1.0, 0.0]})
    assert content_similarity("a", "b", embedder) == pytest.approx(1.0)


def test_reference_fidelity_uses_scorer() -> None:
    scorer = FakeScorer({("out", "ref"): 0.83})
    assert reference_fidelity("out", "ref", scorer) == pytest.approx(0.83)


def test_fluency_perplexity_uses_model() -> None:
    model = FakePerplexityModel({"text": 12.5})
    assert fluency_perplexity("text", model) == pytest.approx(12.5)


def test_judge_win_rate_computes_fraction_fooled() -> None:
    judge = FakeJudge(
        {
            ("model out 1", "real 1"): True,
            ("model out 2", "real 2"): False,
            ("model out 3", "real 3"): True,
            ("model out 4", "real 4"): False,
        }
    )
    pairs = [
        ("model out 1", "real 1"),
        ("model out 2", "real 2"),
        ("model out 3", "real 3"),
        ("model out 4", "real 4"),
    ]
    assert judge_win_rate(pairs, judge) == pytest.approx(0.5)


def test_judge_win_rate_empty_pairs_is_zero() -> None:
    assert judge_win_rate([], FakeJudge({})) == 0.0
