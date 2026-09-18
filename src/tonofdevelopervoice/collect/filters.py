# filters.py
import re
from datetime import datetime

AI_CO_AUTHOR_PATTERN = re.compile(
    r"(?im)^co-authored-by:.*("
    r"claude|opus|sonnet|haiku|gpt|chatgpt|codex|copilot|cursor|gemini|"
    r"devin|aider|cline|windsurf|grok|deepseek|jules|coderabbit|openhands"
    r")"
)

CUTOFF = datetime.fromisoformat("2021-01-01T00:00:00+00:00")

# Trailer conventions like "Co-authored-by: Claude" postdate ~2023; a commit dated
# before 2021 but *committed* at or after 2023 is more likely rewritten/replayed
# history than a genuinely old commit, regardless of how large the author/commit
# date gap is (kernel-style maintainer trees can legitimately delay commits by months).
REWRITE_SUSPECT_CUTOFF = datetime.fromisoformat("2023-01-01T00:00:00+00:00")


def has_ai_co_author(message: str) -> bool:
    return AI_CO_AUTHOR_PATTERN.search(message) is not None


def is_before_cutoff(author_date: datetime, cutoff: datetime = CUTOFF) -> bool:
    return author_date < cutoff


def is_suspicious_rewrite(
    commit_date: datetime, rewrite_cutoff: datetime = REWRITE_SUSPECT_CUTOFF
) -> bool:
    return commit_date >= rewrite_cutoff


def is_valid_record(
    author_date: datetime,
    commit_date: datetime,
    message: str,
    cutoff: datetime = CUTOFF,
) -> bool:
    if not is_before_cutoff(author_date, cutoff):
        return False
    if has_ai_co_author(message):
        return False
    if is_suspicious_rewrite(commit_date):
        return False
    return True
