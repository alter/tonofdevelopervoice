# Corpus collection approach (Sept 2026)

Scope: building a pre-2021, non-AI-co-authored commit/PR text corpus from linux,
postgresql, nginx, apache, mysql (and later additions per `docs/PROJECT.md` §4).

## GH Archive + BigQuery public dataset

GH Archive records the public GitHub *event* timeline (PushEvent, PullRequestEvent,
etc.), not a clean commit/PR table — commit messages live inside
`PushEvent.payload.commits[].message`, PR titles/bodies inside
`PullRequestEvent.payload.pull_request.{title,body}`. Coverage starts 2011-02-12.
Raw hourly gzipped JSON is downloadable directly (no BigQuery needed); the BigQuery
mirror (`githubarchive.day/month/year`) is SQL-queryable within a 1TB/month free tier.
A live GitHub discussion (igrigorik/gharchive.org#307) states the BigQuery mirror
"isn't updated anymore, apparently for about 2 years" despite docs claiming hourly
updates — irrelevant for a pre-2021 historical pull (those months are static) but a
maintenance-currency red flag. Event-stream sampling is not equivalent to full git
history (misses non-default-branch pushes, can duplicate on force-push) — usable for PR
text, weaker than a direct clone for exhaustive commit messages.
`bigquery-public-data.github_repos` has a proper `commits` table (145M+ commits) within
the same free tier, but per-repo snapshot freshness is unconfirmed — verify before
relying on it.

## GitHub REST/GraphQL API

PAT-authenticated REST: 5,000 req/hour; GraphQL is metered by query cost, not request
count. Pagination: `pullRequests(first: 100, after: $cursor) { nodes { title body
createdAt } pageInfo { hasNextPage endCursor } }`. `body` is a first-class field — this
is the right channel for PR description text, ~100 PRs/request, comfortably within
rate limits. Caveat: linux, postgresql, and apache httpd primarily review over mailing
lists rather than GitHub PRs, so their GitHub PR volume may be thin/unrepresentative —
check actual PR counts per repo before investing in this for those three specifically.

## Plain `git clone` + local `git log` mining

No rate limits; the most complete and cheapest path for commit messages. Only the Linux
kernel's size was confirmed by research (~4-7GB clone / ~15-30GB on disk); the other four
repos are expected smaller but unverified — cheap to confirm with `git clone` directly.
Extraction pattern:

```
git log --all --date=iso-strict --pretty=format:'%H%x1f%an%x1f%ae%x1f%ad%x1f%s%x1e%b' > commits.tsv
```

Filter on parsed `%ad` (**author date**, not `%cd` commit date) `< 2021-01-01` in a
script, not via `git log --before` (its default date-field semantics weren't confirmed by
research — parse both `%ad` and `%cd` yourself). Flag any commit where `%cd` diverges far
from `%ad` as a possible history rewrite (see AI-co-author detection below).

PR description text is **not** available this way — PR titles/bodies are GitHub-side
records, not git objects. The one incidental leak path (GitHub's squash-merge UI
sometimes copying PR title/body into the squash commit message) is inconsistent, not a
reliable extraction method.

## Existing public commit-message datasets

CommitBench (arXiv:2403.05188, ~1.66M commits/71,676 projects, excludes bot commits) and
CommitPackFT are candidate supplements, but neither was confirmed by research to carry a
usable per-row date field or to cover the five target repos — treat as optional,
inspect-before-use, not a dependency. MCMD is weaker (heavy duplication per CommitBench's
own comparison). None of the three were found to include PR description text.

## AI co-author detection (validation pass, not the primary filter)

Claude Code auto-appends `Co-Authored-By: Claude <model-id>`; OpenAI Codex does not
reliably auto-insert a trailer (depends on user git config or an optional
`chatgpt-codex-connector[bot]` account). Multiple 2026 papers (arXiv:2603.23802,
arXiv:2605.08435, arXiv:2602.00409) converge on trailer + bot-account + body-phrase
detection, one reporting 100% precision on 500 manually-checked commits with
trailer/substring matching. Detection regex (case-insensitive, applied to the full commit
message):

```
(?i)co-authored-by:.*(claude|opus|sonnet|haiku|gpt|chatgpt|codex|copilot|cursor|gemini|devin|aider|cline|windsurf|grok|deepseek|jules|coderabbit|openhands)
```

plus an author/committer name/email check for `[bot]`/`-bot` suffixes.

For this project this check is **validation-only**: since the primary filter is
author-date strictly before 2021-01-01 and these trailer conventions postdate 2020, no
genuine pre-2021 commit can match. Run it anyway to catch a rewritten-history scenario
(a rebase that back-dates author metadata on an actually-recent, AI-touched commit) — the
most direct tell for that is a large gap between `%ad` and `%cd` on an otherwise
old-dated commit.

## Decision

**Primary source: local `git clone --mirror` + `git log` extraction** for commit messages
across all five repos (and any added later) — no rate limits, most complete, filter on
parsed `%ad < 2021-01-01`, cross-check `%cd` for rewrite signals, then run the AI
co-author regex as a validation pass (expected zero matches on genuine data; any match
means drop and investigate).

**Secondary source: GitHub GraphQL API with `GITHUB_TOKEN`** for PR description text,
filtering `createdAt < 2021-01-01` client-side, ~100 PRs/request. Check actual GitHub PR
volume per repo first (`gh pr list -R <repo> --state all`) before building tooling around
this for linux/postgresql/apache specifically, since their primary review workflows are
off-GitHub and their PR corpora may be thin.

**Skip GH Archive/BigQuery as a primary source** — adds JSON-parsing/event-completeness
complexity without being more complete than the two sources above, and the BigQuery
mirror's currency is in question as of 2026.

**Treat CommitBench/CommitPackFT/MCMD as optional, unverified supplements** — sample and
check target-repo coverage and date fields before merging in; not required for v1.

Consequence for T07 (collector implementation): clone each repo, extract via `git log`
with the format string above, filter/validate as described, and separately pull PR
bodies via GraphQL where repo PR volume justifies it — output both into the JSONL shape
`training-approach.md` specifies (`{input, output, project}` after synthesis in T09; raw
collection output before synthesis is just `{text, source: commit|pr, repo, date}`).
