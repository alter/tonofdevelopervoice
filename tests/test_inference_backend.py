# test_inference_backend.py
from tonofdevelopervoice.serve.backend import InferenceBackend, StubInferenceBackend


def test_stub_backend_rewrites_text() -> None:
    backend = StubInferenceBackend()
    result = backend.rewrite("fix bug in handler")
    assert result == "[rewritten] fix bug in handler"


def test_stub_backend_strips_surrounding_whitespace() -> None:
    backend = StubInferenceBackend()
    result = backend.rewrite("  fix bug  \n")
    assert result == "[rewritten] fix bug"


def test_stub_backend_accepts_custom_prefix() -> None:
    backend = StubInferenceBackend(prefix="[styled] ")
    result = backend.rewrite("add feature")
    assert result == "[styled] add feature"


def test_stub_backend_satisfies_inference_backend_protocol() -> None:
    backend: InferenceBackend = StubInferenceBackend()
    assert isinstance(backend, InferenceBackend)
