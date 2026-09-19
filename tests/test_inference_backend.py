# test_inference_backend.py
from tonofdevelopervoice.serve.backend import InferenceBackend, StubInferenceBackend


def test_stub_backend_rewrites_text() -> None:
    backend = StubInferenceBackend()
    result = backend.rewrite("fix bug in handler")
    assert result.text == "[rewritten] fix bug in handler"
    assert result.finish_reason == "stop"


def test_stub_backend_strips_surrounding_whitespace() -> None:
    backend = StubInferenceBackend()
    result = backend.rewrite("  fix bug  \n")
    assert result.text == "[rewritten] fix bug"


def test_stub_backend_accepts_custom_prefix() -> None:
    backend = StubInferenceBackend(prefix="[styled] ")
    result = backend.rewrite("add feature")
    assert result.text == "[styled] add feature"


def test_stub_backend_satisfies_inference_backend_protocol() -> None:
    backend: InferenceBackend = StubInferenceBackend()
    assert isinstance(backend, InferenceBackend)


def test_stub_backend_reports_whitespace_token_counts() -> None:
    backend = StubInferenceBackend()
    result = backend.rewrite("fix bug")
    assert result.prompt_tokens == 2
    assert result.completion_tokens == len(result.text.split())
    assert result.peak_memory_gb is None
    assert result.tokens_per_second is None
