# batch_rewrite.py
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tonofdevelopervoice.serve.backend import InferenceBackend  # noqa: E402
from tonofdevelopervoice.serve.factory import default_backend  # noqa: E402

OUTPUT_SUFFIX = ".rewritten.txt"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rewrite every text file in a directory into authentic engineering style."
    )
    parser.add_argument("--dir", required=True, type=Path, help="directory of input .txt files")
    parser.add_argument(
        "--out-dir", type=Path, default=None, help="where to write output (default: --dir)"
    )
    parser.add_argument("--pattern", default="*.txt", help="glob pattern for input files")
    return parser


def collect_input_files(directory: Path, pattern: str) -> list[Path]:
    return sorted(
        path
        for path in directory.glob(pattern)
        if path.is_file() and not path.name.endswith(OUTPUT_SUFFIX)
    )


def run(argv: list[str], backend: InferenceBackend) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.dir.is_dir():
        print(f"not a directory: {args.dir}", file=sys.stderr)
        return 1

    files = collect_input_files(args.dir, args.pattern)
    if not files:
        print(f"no files matching {args.pattern!r} in {args.dir}", file=sys.stderr)
        return 1

    out_dir = args.out_dir or args.dir
    out_dir.mkdir(parents=True, exist_ok=True)

    for path in files:
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            print(f"skipping empty file: {path.name}", file=sys.stderr)
            continue
        result = backend.rewrite(text)
        out_path = out_dir / f"{path.stem}{OUTPUT_SUFFIX}"
        out_path.write_text(result.text, encoding="utf-8")
        print(f"{path.name} -> {out_path.name}")

    return 0


def main() -> int:
    return run(sys.argv[1:], default_backend())


if __name__ == "__main__":
    sys.exit(main())
