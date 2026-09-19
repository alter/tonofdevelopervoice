# app.py
from flask import Flask, render_template_string, request

from tonofdevelopervoice.serve.backend import InferenceBackend, StubInferenceBackend
from tonofdevelopervoice.serve.factory import default_backend

PAGE_TEMPLATE = """
<!doctype html>
<html>
<head><title>tonofdevelopervoice</title></head>
<body>
{% if using_stub %}
<p style="color: #900; font-weight: bold;">
  WARNING: TONOFDEVELOPERVOICE_MODEL_DIR is not set — this is the stub backend, it
  returns your input essentially unchanged, not the real model.
</p>
{% endif %}
{% if finish_reason != "stop" %}
<p style="color: #900; font-weight: bold;">
  Rewrite did not finish cleanly: {{ finish_reason }}
</p>
{% endif %}
<form method="post">
  <div style="display:flex; gap:1em;">
    <textarea name="input_text" rows="24" cols="60"
              placeholder="Paste AI-generated text here">{{ input_text }}</textarea>
    <textarea rows="24" cols="60" readonly
              placeholder="Rewritten text appears here">{{ output_text }}</textarea>
  </div>
  <button type="submit">Rewrite</button>
</form>
</body>
</html>
"""


def create_app(backend: InferenceBackend | None = None) -> Flask:
    app = Flask(__name__)
    app.config["BACKEND"] = backend or default_backend()
    using_stub = isinstance(app.config["BACKEND"], StubInferenceBackend)

    @app.route("/", methods=["GET", "POST"])
    def index() -> str:
        input_text = ""
        output_text = ""
        finish_reason = "stop"
        if request.method == "POST":
            input_text = request.form.get("input_text", "")
            if input_text.strip():
                result = app.config["BACKEND"].rewrite(input_text)
                output_text = result.text
                finish_reason = result.finish_reason
        return render_template_string(
            PAGE_TEMPLATE,
            input_text=input_text,
            output_text=output_text,
            using_stub=using_stub,
            finish_reason=finish_reason,
        )

    return app


def main() -> None:
    create_app().run()


if __name__ == "__main__":
    main()
