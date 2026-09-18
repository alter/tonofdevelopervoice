# cli.py
import argparse
import sys
from pathlib import Path

from tonofdevelopervoice.serve.backend import InferenceBackend, StubInferenceBackend


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rewrite AI-generated commit/PR text into authentic engineering style."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--text", help="text to rewrite")
    group.add_argument("--file", type=Path, help="path to a file containing the text to rewrite")
    return parser


def read_input(args: argparse.Namespace) -> str:
    if args.text is not None:
        text: str = args.text
        return text
    if args.file is not None:
        file_path: Path = args.file
        if not file_path.exists():
            raise FileNotFoundError(f"input file not found: {file_path}")
        return file_path.read_text(encoding="utf-8")
    return sys.stdin.read()


def run(argv: list[str], backend: InferenceBackend) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        text = read_input(args)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not text.strip():
        print("no input text provided", file=sys.stderr)
        return 1

    print(backend.rewrite(text))
    return 0


def main() -> int:
    return run(sys.argv[1:], StubInferenceBackend())


if __name__ == "__main__":
    sys.exit(main())
