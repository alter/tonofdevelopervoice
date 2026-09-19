# collect_ai_eval_inputs.py
import argparse
import hashlib
import json
import os
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tonofdevelopervoice.collect.github_search import search  # noqa: E402
from tonofdevelopervoice.env import load_dotenv  # noqa: E402
from tonofdevelopervoice.evaluate.ai_inputs import (  # noqa: E402
    select_ai_commits,
    select_ai_prs,
    select_with_repo_cap,
)

AGENTS = ["Claude", "Copilot", "Cursor", "Devin", "aider", "Codex", "Gemini"]


def commit_queries() -> list[str]:
    return [f'"Co-authored-by: {agent}" committer-date:>2023-01-01' for agent in AGENTS]


def pr_queries() -> list[str]:
    queries = [f'type:pr "Co-authored-by: {agent}" created:>2023-01-01' for agent in AGENTS]
    queries.append('type:pr "Generated with" in:body created:>2023-01-01')
    return queries


def dedup_key_field(endpoint: str) -> str:
    return "sha" if endpoint == "commits" else "id"


def collect_raw(
    endpoint: str,
    queries: list[str],
    token: str,
    sleep: Callable[[float], None] = time.sleep,
) -> list[dict[str, Any]]:
    key_field = dedup_key_field(endpoint)
    seen: set[Any] = set()
    items: list[dict[str, Any]] = []
    for query in queries:
        print(f"[{endpoint}] searching: {query}")
        for item in search(endpoint, query, token, sleep=sleep):
            key = item.get(key_field)
            if key in seen:
                continue
            seen.add(key)
            items.append(item)
    return items


def write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def sha256_of(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_for(records: list[dict[str, Any]], path: Path) -> dict[str, Any]:
    agent_counts: dict[str, int] = {}
    dates: list[str] = []
    for record in records:
        agent_counts[record["agent"]] = agent_counts.get(record["agent"], 0) + 1
        dates.append(record["date"])
    return {
        "count": len(records),
        "agent_counts": agent_counts,
        "min_date": min(dates) if dates else None,
        "sha256": sha256_of(path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect real AI-written commit/PR text as evaluation inputs only."
    )
    parser.add_argument("--out-dir", type=Path, default=Path("data/eval_real"))
    parser.add_argument("--commit-target", type=int, default=300)
    parser.add_argument("--pr-target", type=int, default=200)
    parser.add_argument("--repo-cap", type=int, default=5)
    parser.add_argument("--manifest", type=Path, default=None)
    return parser


def run(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)

    load_dotenv()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is not set (checked environment and .env)", file=sys.stderr)
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)

    raw_commits = collect_raw("commits", commit_queries(), token)
    capped_commits = select_with_repo_cap(list(select_ai_commits(raw_commits)), cap=args.repo_cap)
    commits_out = capped_commits[: args.commit_target]

    raw_prs = collect_raw("issues", pr_queries(), token)
    capped_prs = select_with_repo_cap(list(select_ai_prs(raw_prs)), cap=args.repo_cap)
    prs_out = capped_prs[: args.pr_target]

    commits_path = args.out_dir / "ai_commits.jsonl"
    prs_path = args.out_dir / "ai_prs.jsonl"
    write_jsonl(commits_out, commits_path)
    write_jsonl(prs_out, prs_path)

    manifest = {
        "ai_commits": manifest_for(commits_out, commits_path),
        "ai_prs": manifest_for(prs_out, prs_path),
    }
    manifest_path = args.manifest or (args.out_dir / "MANIFEST.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {len(commits_out)} commits, {len(prs_out)} PRs; manifest at {manifest_path}")
    return 0


def main() -> int:
    return run(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
