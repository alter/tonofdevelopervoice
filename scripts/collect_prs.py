# collect_prs.py
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tonofdevelopervoice.collect.github_prs import (  # noqa: E402
    fetch_pull_requests,
    filter_pull_requests,
)
from tonofdevelopervoice.collect.sampling import sample_by_year_and_author, year_of  # noqa: E402
from tonofdevelopervoice.collect.sources import PR_REPOS  # noqa: E402
from tonofdevelopervoice.env import load_dotenv  # noqa: E402

CUTOFF_ISO = "2021-01-01T00:00:00Z"


def candidate_paths(out_dir: Path, name: str) -> tuple[Path, Path]:
    candidates_dir = out_dir / ".candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)
    return candidates_dir / f"{name}.jsonl", candidates_dir / f"{name}.checkpoint.json"


def load_checkpoint(path: Path) -> int:
    if not path.exists():
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    return int(data["next_page"])


def save_checkpoint(path: Path, next_page: int) -> None:
    path.write_text(json.dumps({"next_page": next_page}), encoding="utf-8")


def load_candidates(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    seen: set[str] = set()
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").split("\n"):
        if not line.strip():
            continue
        record = json.loads(line)
        if record["id"] in seen:
            continue
        seen.add(record["id"])
        records.append(record)
    return records


def collect_repo_candidates(repo: str, token: str, out_dir: Path) -> Path:
    name = repo.split("/")[-1]
    candidates_path, checkpoint_path = candidate_paths(out_dir, name)
    start_page = load_checkpoint(checkpoint_path)

    with candidates_path.open("a", encoding="utf-8") as f:
        for page, raw_prs in fetch_pull_requests(
            repo, token, CUTOFF_ISO, start_page=start_page
        ):
            for record in filter_pull_requests(raw_prs, repo=name):
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            save_checkpoint(checkpoint_path, page + 1)

    return candidates_path


def repo_manifest(sampled: list[dict[str, Any]]) -> dict[str, Any]:
    year_histogram: dict[str, int] = {}
    author_counts: dict[str, int] = {}
    for record in sampled:
        year = str(year_of(record["author_date"]))
        year_histogram[year] = year_histogram.get(year, 0) + 1
        author_counts[record["author_hash"]] = author_counts.get(record["author_hash"], 0) + 1
    largest_author_share = (max(author_counts.values()) / len(sampled)) if sampled else 0.0
    return {
        "count": len(sampled),
        "year_histogram": year_histogram,
        "largest_author_share": largest_author_share,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect merged, human-written, pre-2021 PR descriptions."
    )
    parser.add_argument(
        "--repos", nargs="*", default=None, help="owner/name list; default: PR_REPOS"
    )
    parser.add_argument("--out-dir", type=Path, default=Path("data/raw_v2/prs"))
    parser.add_argument("--target", type=int, default=3000)
    parser.add_argument("--manifest", type=Path, default=None)
    return parser


def run(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)

    load_dotenv()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is not set (checked environment and .env)", file=sys.stderr)
        return 1

    repos = args.repos or PR_REPOS
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.manifest or (out_dir / "MANIFEST.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {}

    for repo in repos:
        name = repo.split("/")[-1]
        print(f"[{repo}] collecting candidates ...")
        candidates_path = collect_repo_candidates(repo, token, out_dir)
        candidates = load_candidates(candidates_path)
        sampled = sample_by_year_and_author(candidates, args.target)

        out_path = out_dir / f"{name}.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for record in sampled:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        manifest[name] = repo_manifest(sampled)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(
            f"[{repo}] {len(candidates)} candidates -> {len(sampled)} sampled -> {out_path}"
        )

    print(f"wrote manifest to {manifest_path}")
    return 0


def main() -> int:
    return run(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
