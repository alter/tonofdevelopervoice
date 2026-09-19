# test_sampling.py
from typing import Any

from tonofdevelopervoice.collect.sampling import sample_by_year_and_author, year_of


def _record(rec_id: str, year: int, author: str) -> dict[str, Any]:
    return {
        "id": rec_id,
        "author_date": f"{year}-06-15T00:00:00Z",
        "author_hash": author,
    }


def test_year_of_parses_iso_dates_with_zulu_suffix() -> None:
    assert year_of("2019-05-01T10:00:00Z") == 2019


def test_sample_returns_empty_for_zero_target_or_no_records() -> None:
    assert sample_by_year_and_author([], 100) == []
    assert sample_by_year_and_author([_record("1", 2019, "a")], 0) == []


def test_sample_distributes_evenly_across_years() -> None:
    records = [
        _record(f"{year}-{i}", year, f"author-{year}-{i}")
        for year in (2018, 2019, 2020)
        for i in range(10)
    ]
    sampled = sample_by_year_and_author(records, target=9)
    counts = {year_of(r["author_date"]): 0 for r in sampled}
    for r in sampled:
        counts[year_of(r["author_date"])] += 1
    assert len(sampled) == 9
    assert set(counts.values()) == {3}


def test_sample_redistributes_a_thin_years_unused_quota() -> None:
    records = [_record("2018-only", 2018, "author-a")]
    records += [_record(f"2019-{i}", 2019, f"author-{i}") for i in range(20)]
    sampled = sample_by_year_and_author(records, target=10)
    assert len(sampled) == 10
    counts = {2018: 0, 2019: 0}
    for r in sampled:
        counts[year_of(r["author_date"])] += 1
    assert counts[2018] == 1
    assert counts[2019] == 9


def test_sample_enforces_the_author_cap() -> None:
    records = [_record(f"same-{i}", 2020, "prolific") for i in range(50)]
    records += [_record(f"other-{i}", 2020, f"author-{i}") for i in range(50)]
    sampled = sample_by_year_and_author(records, target=100, author_cap_fraction=0.02)
    prolific_count = sum(1 for r in sampled if r["author_hash"] == "prolific")
    assert prolific_count <= 2


def test_sample_stops_redistributing_mid_round_once_the_target_is_reached() -> None:
    records = [_record("2018-only", 2018, "author-2018")]
    records += [_record(f"2019-{i}", 2019, f"author-2019-{i}") for i in range(20)]
    records += [_record(f"2020-{i}", 2020, f"author-2020-{i}") for i in range(20)]
    sampled = sample_by_year_and_author(records, target=10)
    assert len(sampled) == 10


def test_sample_is_deterministic() -> None:
    records = [_record(f"id-{i}", 2019 + i % 3, f"author-{i}") for i in range(30)]
    first = sample_by_year_and_author(list(records), target=10)
    second = sample_by_year_and_author(list(reversed(records)), target=10)
    assert [r["id"] for r in first] == [r["id"] for r in second]
