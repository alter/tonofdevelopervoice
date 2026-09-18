# build_manifest.py
import argparse
import sys
from pathlib import Path

from tonofdevelopervoice.collect.manifest import write_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--out", type=Path, default=Path("data/manifest.json"))
    args = parser.parse_args()

    manifest = write_manifest(args.raw_dir, args.out)
    for repo, count in manifest.items():
        print(f"{repo}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
