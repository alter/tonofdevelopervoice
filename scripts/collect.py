# collect.py
import argparse
import os
import sys
from pathlib import Path

from tonofdevelopervoice.collect.github_api import fetch_commits
from tonofdevelopervoice.collect.pipeline import filter_records, write_jsonl
from tonofdevelopervoice.env import load_dotenv


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="owner/name, e.g. torvalds/linux")
    parser.add_argument("--until", default="2021-01-01T00:00:00Z")
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    load_dotenv()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is not set (checked environment and .env)", file=sys.stderr)
        return 1

    repo_name = args.repo.split("/")[-1]
    raw_commits = fetch_commits(args.repo, token, args.until, max_pages=args.max_pages)
    records = filter_records(raw_commits, repo_name)
    count = write_jsonl(records, args.out)
    print(f"wrote {count} records to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
