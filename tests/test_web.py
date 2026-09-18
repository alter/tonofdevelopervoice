# test_web.py
from unittest.mock import patch

from flask.testing import FlaskClient

from tonofdevelopervoice.serve.backend import StubInferenceBackend
from tonofdevelopervoice.web.app import create_app, main


def make_client() -> FlaskClient:
    app = create_app(StubInferenceBackend())
    app.config["TESTING"] = True
    return app.test_client()


def test_get_index_returns_empty_form() -> None:
    client = make_client()
    response = client.get("/")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "<form" in body
    assert "textarea" in body


def test_post_rewrites_text_and_shows_output() -> None:
    client = make_client()
    response = client.post("/", data={"input_text": "fix bug in handler"})
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "[rewritten] fix bug in handler" in body


def test_post_with_empty_text_shows_no_output() -> None:
    client = make_client()
    response = client.post("/", data={"input_text": "   "})
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "[rewritten]" not in body


def test_post_escapes_html_in_input() -> None:
    client = make_client()
    response = client.post("/", data={"input_text": "<script>alert(1)</script>"})
    body = response.get_data(as_text=True)
    assert "<script>alert(1)</script>" not in body


def test_main_starts_the_dev_server() -> None:
    with patch("flask.Flask.run") as mock_run:
        main()
    mock_run.assert_called_once()


def test_stub_backend_shows_warning_banner() -> None:
    client = make_client()
    response = client.get("/")
    body = response.get_data(as_text=True)
    assert "TONOFDEVELOPERVOICE_MODEL_DIR" in body


def test_non_stub_backend_shows_no_warning_banner() -> None:
    class FakeRealBackend:
        def rewrite(self, text: str) -> str:
            return text

    app = create_app(FakeRealBackend())
    app.config["TESTING"] = True
    response = app.test_client().get("/")
    body = response.get_data(as_text=True)
    assert "TONOFDEVELOPERVOICE_MODEL_DIR" not in body
