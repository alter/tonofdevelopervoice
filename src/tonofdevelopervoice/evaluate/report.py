# report.py
from dataclasses import dataclass
from typing import Any

from tonofdevelopervoice.evaluate.metrics import (
    Embedder,
    Judge,
    PerplexityModel,
    ReferenceScorer,
    content_similarity,
    fluency_perplexity,
    judge_win_rate,
    reference_fidelity,
)
from tonofdevelopervoice.evaluate.style_classifier import StyleClassifier


@dataclass(frozen=True)
class EvalExample:
    source: str
    model_output: str
    reference: str


@dataclass(frozen=True)
class EvalReport:
    content_similarity_mean: float
    reference_fidelity_mean: float
    style_score_mean: float
    style_classifier_accuracy: float
    perplexity_mean: float
    judge_win_rate: float | None
    worst_examples: list[dict[str, Any]]


def build_report(
    examples: list[EvalExample],
    embedder: Embedder,
    scorer: ReferenceScorer,
    classifier: StyleClassifier,
    style_classifier_accuracy: float,
    perplexity_model: PerplexityModel,
    judge: Judge | None = None,
    worst_n: int = 5,
) -> EvalReport:
    if not examples:
        raise ValueError("cannot build a report from zero examples")

    per_example: list[dict[str, Any]] = []
    for ex in examples:
        per_example.append(
            {
                "source": ex.source,
                "model_output": ex.model_output,
                "reference": ex.reference,
                "content_similarity": content_similarity(ex.model_output, ex.source, embedder),
                "reference_fidelity": reference_fidelity(ex.model_output, ex.reference, scorer),
                "style_score": classifier.score(ex.model_output),
                "perplexity": fluency_perplexity(ex.model_output, perplexity_model),
            }
        )

    win_rate = None
    if judge is not None:
        win_rate = judge_win_rate([(ex.model_output, ex.reference) for ex in examples], judge)

    worst = sorted(per_example, key=lambda r: float(r["style_score"]))[:worst_n]
    n = len(per_example)

    return EvalReport(
        content_similarity_mean=sum(r["content_similarity"] for r in per_example) / n,
        reference_fidelity_mean=sum(r["reference_fidelity"] for r in per_example) / n,
        style_score_mean=sum(r["style_score"] for r in per_example) / n,
        style_classifier_accuracy=style_classifier_accuracy,
        perplexity_mean=sum(r["perplexity"] for r in per_example) / n,
        judge_win_rate=win_rate,
        worst_examples=worst,
    )
