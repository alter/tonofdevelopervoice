# reference_scorer.py
class BERTScoreScorer:
    def __init__(self, lang: str = "en") -> None:
        self._lang = lang

    def score(self, candidate: str, reference: str) -> float:
        from bert_score import score  # type: ignore[import-not-found]

        _precision, _recall, f1 = score([candidate], [reference], lang=self._lang, verbose=False)
        return float(f1[0])
