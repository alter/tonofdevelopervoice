# reference_scorer.py
def _patch_build_inputs_with_special_tokens() -> None:
    # bert-score 0.3.13 calls tokenizer.build_inputs_with_special_tokens(), which
    # transformers>=5 removed from RobertaTokenizer's public API. Restore the standard
    # <s> token_ids_0 </s> behavior bert-score relies on when it's missing.
    try:
        from transformers import RobertaTokenizer  # type: ignore[import-not-found]
    except ImportError:
        return

    if hasattr(RobertaTokenizer, "build_inputs_with_special_tokens"):
        return

    def build_inputs_with_special_tokens(
        self: RobertaTokenizer, token_ids_0: list[int], token_ids_1: list[int] | None = None
    ) -> list[int]:
        if token_ids_1 is None:
            return [self.bos_token_id, *token_ids_0, self.eos_token_id]
        return [
            self.bos_token_id,
            *token_ids_0,
            self.eos_token_id,
            self.eos_token_id,
            *token_ids_1,
            self.eos_token_id,
        ]

    RobertaTokenizer.build_inputs_with_special_tokens = build_inputs_with_special_tokens


class BERTScoreScorer:
    def __init__(self, lang: str = "en") -> None:
        self._lang = lang

    def score(self, candidate: str, reference: str) -> float:
        from bert_score import score  # type: ignore[import-not-found]

        _patch_build_inputs_with_special_tokens()
        _precision, _recall, f1 = score([candidate], [reference], lang=self._lang, verbose=False)
        return float(f1[0])
