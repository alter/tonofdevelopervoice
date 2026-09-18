# test_evaluate.py
import json
import sys
from pathlib import Path

sys.path.insert(0, "scripts")

from evaluate import fit_style_classifier, load_examples, load_jsonl  # noqa: E402


def test_load_jsonl_reads_all_lines(tmp_path: Path) -> None:
    path = tmp_path / "data.jsonl"
    path.write_text('{"a": "one"}\n{"a": "two"}\n')

    records = load_jsonl(path)

    assert records == [{"a": "one"}, {"a": "two"}]


def test_fit_style_classifier_uses_input_output_fields(tmp_path: Path) -> None:
    path = tmp_path / "train.jsonl"
    rows = [
        {"input": "I've fixed the bug for you", "output": "fix bug"},
        {"input": "I've added a new feature", "output": "add feature"},
        {"input": "I've updated the docs", "output": "update docs"},
        {"input": "I've removed dead code", "output": "remove dead code"},
    ] * 5
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    classifier, accuracy = fit_style_classifier(path)

    assert 0.0 <= accuracy <= 1.0
    assert classifier.score("fix bug") >= 0.0


def test_load_examples_builds_eval_examples(tmp_path: Path) -> None:
    path = tmp_path / "eval.jsonl"
    rows = [{"source": "s1", "model_output": "m1", "reference": "r1"}]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    examples = load_examples(path)

    assert len(examples) == 1
    assert examples[0].source == "s1"
    assert examples[0].model_output == "m1"
    assert examples[0].reference == "r1"
