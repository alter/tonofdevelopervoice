# generate_eval_outputs.py
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tonofdevelopervoice.serve.unsloth_backend import UnslothInferenceBackend  # noqa: E402


def load_jsonl(path: Path) -> list[dict[str, str]]:
    records = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    return records


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the real trained model over an eval split's inputs, producing "
            "{source, model_output, reference} triples for scripts/evaluate.py."
        )
    )
    parser.add_argument("--eval-file", required=True, type=Path)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    backend = UnslothInferenceBackend(str(args.model_dir))
    records = load_jsonl(args.eval_file)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for i, record in enumerate(records):
            result = backend.rewrite(record["input"])
            model_output = result.text
            f.write(
                json.dumps(
                    {
                        "source": record["input"],
                        "model_output": model_output,
                        "reference": record["output"],
                    }
                )
                + "\n"
            )
            print(f"[{i + 1}/{len(records)}] generated")

    print(f"wrote {len(records)} triples to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
