# test_report.py
import pytest

from tonofdevelopervoice.evaluate.report import EvalExample, build_report
from tonofdevelopervoice.evaluate.style_classifier import StyleClassifier


class FakeEmbedder:
    def embed(self, text: str) -> list[float]:
        return [float(len(text)), 0.0]


class FakeScorer:
    def score(self, candidate: str, reference: str) -> float:
        return 1.0 if candidate == reference else 0.5


class FakePerplexityModel:
    def perplexity(self, text: str) -> float:
        return 10.0


class FakeJudge:
    def prefers_first(self, sample_a: str, sample_b: str) -> bool:
        return False


def make_classifier() -> tuple[StyleClassifier, float]:
    classifier = StyleClassifier()
    authentic = ["fix bug", "add feature", "update docs", "remove dead code"] * 5
    synthetic = [
        "I've fixed the bug for you",
        "I've added the requested feature",
        "I've updated the documentation",
        "I've removed the dead code",
    ] * 5
    result = classifier.fit(authentic, synthetic)
    return classifier, result.held_out_accuracy


def test_build_report_computes_means_and_worst_examples() -> None:
    classifier, accuracy = make_classifier()
    examples = [
        EvalExample(source="src1", model_output="fix bug", reference="fix bug"),
        EvalExample(source="src2", model_output="I've added a feature", reference="add feature"),
    ]

    report = build_report(
        examples,
        embedder=FakeEmbedder(),
        scorer=FakeScorer(),
        classifier=classifier,
        style_classifier_accuracy=accuracy,
        perplexity_model=FakePerplexityModel(),
        judge=None,
        worst_n=1,
    )

    assert report.style_classifier_accuracy == accuracy
    assert report.perplexity_mean == pytest.approx(10.0)
    assert report.judge_win_rate is None
    assert len(report.worst_examples) == 1


def test_build_report_includes_judge_win_rate_when_provided() -> None:
    classifier, accuracy = make_classifier()
    examples = [EvalExample(source="s", model_output="fix bug", reference="fix bug")]

    report = build_report(
        examples,
        embedder=FakeEmbedder(),
        scorer=FakeScorer(),
        classifier=classifier,
        style_classifier_accuracy=accuracy,
        perplexity_model=FakePerplexityModel(),
        judge=FakeJudge(),
    )

    assert report.judge_win_rate == pytest.approx(0.0)


def test_build_report_raises_for_empty_examples() -> None:
    classifier, accuracy = make_classifier()
    with pytest.raises(ValueError, match="zero examples"):
        build_report(
            [],
            embedder=FakeEmbedder(),
            scorer=FakeScorer(),
            classifier=classifier,
            style_classifier_accuracy=accuracy,
            perplexity_model=FakePerplexityModel(),
        )
