# judge.py
class UnavailableJudge:
    def prefers_first(self, sample_a: str, sample_b: str) -> bool:
        raise NotImplementedError(
            "no LLM-judge API key is configured for this project (see docs/PROJECT.md) "
            "— provide a real Judge implementation (e.g. calling an LLM API) before "
            "using the forced-choice judge metric"
        )
