# sampling.py
import hashlib
from collections.abc import Sequence
from datetime import datetime
from typing import Any


def year_of(iso_date: str) -> int:
    return datetime.fromisoformat(iso_date.replace("Z", "+00:00")).year


def sample_by_year_and_author(
    records: Sequence[dict[str, Any]],
    target: int,
    author_cap_fraction: float = 0.02,
    date_field: str = "author_date",
    id_field: str = "id",
    author_hash_field: str = "author_hash",
) -> list[dict[str, Any]]:
    if target <= 0 or not records:
        return []

    by_year: dict[int, list[dict[str, Any]]] = {}
    for record in records:
        by_year.setdefault(year_of(record[date_field]), []).append(record)
    for group in by_year.values():
        group.sort(key=lambda r: hashlib.sha256(str(r[id_field]).encode("utf-8")).hexdigest())

    years = sorted(by_year)
    base_quota = target // len(years)
    remainder = target - base_quota * len(years)
    quotas = {year: base_quota for year in years}
    for year in years[:remainder]:
        quotas[year] += 1

    author_cap = max(1, int(target * author_cap_fraction))
    author_counts: dict[str, int] = {}
    cursors = {year: 0 for year in years}
    selected: list[dict[str, Any]] = []

    def take_from_year(year: int, count: int) -> int:
        taken = 0
        group = by_year[year]
        while taken < count and cursors[year] < len(group):
            candidate = group[cursors[year]]
            cursors[year] += 1
            author_hash = candidate[author_hash_field]
            if author_counts.get(author_hash, 0) >= author_cap:
                continue
            selected.append(candidate)
            author_counts[author_hash] = author_counts.get(author_hash, 0) + 1
            taken += 1
        return taken

    leftover = 0
    for year in years:
        leftover += quotas[year] - take_from_year(year, quotas[year])

    while leftover > 0:
        progressed = False
        for year in years:
            if leftover <= 0:
                break
            if cursors[year] < len(by_year[year]):
                leftover -= take_from_year(year, 1)
                progressed = True
        if not progressed:
            break

    return selected[:target]
