# test_dataset.py
from pathlib import Path

from tonofdevelopervoice.dataset.assemble import (
    PrecomputedSynthesizer,
    build_pairs,
    dedup_records,
    load_raw_records,
    split_train_eval,
)

RECORD_A = {"sha": "aaa", "repo": "linux", "text": "fix null pointer dereference"}
RECORD_B = {"sha": "bbb", "repo": "nginx", "text": "add config directive for timeout"}
RECORD_A_DUP = {"sha": "aaa", "repo": "linux", "text": "fix null pointer dereference"}


def test_load_raw_records_reads_all_jsonl_files(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "linux.jsonl").write_text('{"sha": "aaa", "repo": "linux", "text": "a"}\n')
    (raw_dir / "nginx.jsonl").write_text('{"sha": "bbb", "repo": "nginx", "text": "b"}\n')

    records = load_raw_records(raw_dir)

    assert len(records) == 2
    assert {r["sha"] for r in records} == {"aaa", "bbb"}


def test_load_raw_records_empty_dir_yields_empty_list(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    assert load_raw_records(raw_dir) == []


def test_dedup_records_removes_duplicate_sha_keeping_first() -> None:
    records = [RECORD_A, RECORD_B, RECORD_A_DUP]
    deduped = dedup_records(records)
    assert len(deduped) == 2
    assert [r["sha"] for r in deduped] == ["aaa", "bbb"]


def test_dedup_records_no_duplicates_is_a_noop() -> None:
    records = [RECORD_A, RECORD_B]
    assert dedup_records(records) == records


def test_split_train_eval_covers_every_record_exactly_once() -> None:
    records = [{"sha": f"sha{i}", "repo": "linux", "text": f"msg {i}"} for i in range(200)]
    train, eval_ = split_train_eval(records, eval_fraction=0.1)
    assert len(train) + len(eval_) == len(records)
    assert {r["sha"] for r in train} | {r["sha"] for r in eval_} == {r["sha"] for r in records}
    assert not ({r["sha"] for r in train} & {r["sha"] for r in eval_})


def test_split_train_eval_is_deterministic() -> None:
    records = [{"sha": f"sha{i}", "repo": "linux", "text": f"msg {i}"} for i in range(200)]
    train1, eval1 = split_train_eval(records, eval_fraction=0.1)
    train2, eval2 = split_train_eval(records, eval_fraction=0.1)
    assert [r["sha"] for r in train1] == [r["sha"] for r in train2]
    assert [r["sha"] for r in eval1] == [r["sha"] for r in eval2]


def test_split_train_eval_roughly_matches_fraction() -> None:
    records = [{"sha": f"sha{i}", "repo": "linux", "text": f"msg {i}"} for i in range(2000)]
    train, eval_ = split_train_eval(records, eval_fraction=0.1)
    assert 150 <= len(eval_) <= 250


def test_split_train_eval_stable_under_new_records_appended() -> None:
    base = [{"sha": f"sha{i}", "repo": "linux", "text": f"msg {i}"} for i in range(200)]
    _, eval_before = split_train_eval(base, eval_fraction=0.1)

    extended = base + [{"sha": "sha_new", "repo": "linux", "text": "msg new"}]
    _, eval_after = split_train_eval(extended, eval_fraction=0.1)

    before_shas = {r["sha"] for r in eval_before}
    after_shas = {r["sha"] for r in eval_after}
    assert before_shas <= after_shas


def test_precomputed_synthesizer_returns_mapped_value() -> None:
    synthesizer = PrecomputedSynthesizer({"aaa": "I have fixed the null pointer issue."})
    assert synthesizer.synthesize("aaa") == "I have fixed the null pointer issue."


def test_precomputed_synthesizer_raises_key_error_for_missing_sha() -> None:
    synthesizer = PrecomputedSynthesizer({})
    try:
        synthesizer.synthesize("missing")
    except KeyError:
        pass
    else:
        raise AssertionError("expected KeyError")


def test_build_pairs_uses_synthesizer_and_repo_as_project() -> None:
    synthesizer = PrecomputedSynthesizer({"aaa": "synthetic version of aaa"})
    pairs = build_pairs([RECORD_A], synthesizer)
    assert pairs == [
        {
            "input": "synthetic version of aaa",
            "output": "fix null pointer dereference",
            "project": "linux",
        }
    ]


def test_build_pairs_skips_records_the_synthesizer_has_no_mapping_for() -> None:
    synthesizer = PrecomputedSynthesizer({})
    pairs = build_pairs([RECORD_A, RECORD_B], synthesizer)
    assert pairs == []
