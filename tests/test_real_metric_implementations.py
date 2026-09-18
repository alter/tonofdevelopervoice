# test_real_metric_implementations.py
import sys
from collections.abc import Generator
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from tonofdevelopervoice.evaluate.judge import UnavailableJudge


@pytest.fixture
def fake_sentence_transformers() -> Generator[MagicMock, None, None]:
    fake_model = MagicMock()
    fake_model.encode.return_value = [0.1, 0.2, 0.3]

    fake_st_class = MagicMock(return_value=fake_model)
    module = ModuleType("sentence_transformers")
    module.SentenceTransformer = fake_st_class  # type: ignore[attr-defined]

    original = sys.modules.get("sentence_transformers")
    sys.modules["sentence_transformers"] = module
    try:
        yield fake_model
    finally:
        if original is not None:
            sys.modules["sentence_transformers"] = original
        else:
            del sys.modules["sentence_transformers"]


def test_minilm_embedder_embeds_via_sentence_transformers(
    fake_sentence_transformers: MagicMock,
) -> None:
    from tonofdevelopervoice.evaluate.embedder import MiniLMEmbedder

    embedder = MiniLMEmbedder()
    result = embedder.embed("some text")

    assert result == [0.1, 0.2, 0.3]
    fake_sentence_transformers.encode.assert_called_once_with("some text")


@pytest.fixture
def fake_bert_score() -> Generator[MagicMock, None, None]:
    fake_score_fn = MagicMock(return_value=([0.9], [0.8], [0.85]))
    module = ModuleType("bert_score")
    module.score = fake_score_fn  # type: ignore[attr-defined]

    original = sys.modules.get("bert_score")
    sys.modules["bert_score"] = module
    try:
        yield fake_score_fn
    finally:
        if original is not None:
            sys.modules["bert_score"] = original
        else:
            del sys.modules["bert_score"]


def test_bertscore_scorer_returns_f1(fake_bert_score: MagicMock) -> None:
    from tonofdevelopervoice.evaluate.reference_scorer import BERTScoreScorer

    scorer = BERTScoreScorer()
    result = scorer.score("candidate", "reference")

    assert result == pytest.approx(0.85)
    fake_bert_score.assert_called_once_with(
        ["candidate"], ["reference"], lang="en", verbose=False
    )


class FakeLoss:
    def item(self) -> float:
        return 0.0


class FakeOutputs:
    loss = FakeLoss()


@pytest.fixture
def fake_transformers_and_torch() -> Generator[tuple[MagicMock, MagicMock], None, None]:
    fake_tokenizer = MagicMock()
    fake_encoded = {"input_ids": MagicMock()}
    fake_tokenizer.return_value = fake_encoded

    fake_model = MagicMock(return_value=FakeOutputs())

    fake_tokenizer_cls = MagicMock()
    fake_tokenizer_cls.from_pretrained.return_value = fake_tokenizer
    fake_model_cls = MagicMock()
    fake_model_cls.from_pretrained.return_value = fake_model

    transformers_module = ModuleType("transformers")
    transformers_module.AutoTokenizer = fake_tokenizer_cls  # type: ignore[attr-defined]
    transformers_module.AutoModelForCausalLM = fake_model_cls  # type: ignore[attr-defined]

    class FakeNoGrad:
        def __enter__(self) -> None:
            return None

        def __exit__(self, *_args: object) -> None:
            return None

    torch_module = ModuleType("torch")
    torch_module.no_grad = FakeNoGrad  # type: ignore[attr-defined]

    original_transformers = sys.modules.get("transformers")
    original_torch = sys.modules.get("torch")
    sys.modules["transformers"] = transformers_module
    sys.modules["torch"] = torch_module
    try:
        yield fake_tokenizer, fake_model
    finally:
        for name, original in (
            ("transformers", original_transformers),
            ("torch", original_torch),
        ):
            if original is not None:
                sys.modules[name] = original
            else:
                del sys.modules[name]


def test_gpt2_perplexity_computes_exp_of_loss(
    fake_transformers_and_torch: tuple[MagicMock, MagicMock],
) -> None:
    from tonofdevelopervoice.evaluate.perplexity_model import GPT2Perplexity

    model = GPT2Perplexity()
    result = model.perplexity("some text")

    assert result == pytest.approx(1.0)


def test_unavailable_judge_raises_not_implemented_with_context() -> None:
    judge = UnavailableJudge()
    with pytest.raises(NotImplementedError, match="LLM-judge API key"):
        judge.prefers_first("a", "b")
