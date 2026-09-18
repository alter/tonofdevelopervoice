# app.py
from flask import Flask, render_template_string, request

from tonofdevelopervoice.serve.backend import InferenceBackend, StubInferenceBackend

PAGE_TEMPLATE = """
<!doctype html>
<html>
<head><title>tonofdevelopervoice</title></head>
<body>
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
    app.config["BACKEND"] = backend or StubInferenceBackend()

    @app.route("/", methods=["GET", "POST"])
    def index() -> str:
        input_text = ""
        output_text = ""
        if request.method == "POST":
            input_text = request.form.get("input_text", "")
            if input_text.strip():
                output_text = app.config["BACKEND"].rewrite(input_text)
        return render_template_string(
            PAGE_TEMPLATE, input_text=input_text, output_text=output_text
        )

    return app


def main() -> None:
    create_app().run()


if __name__ == "__main__":
    main()
