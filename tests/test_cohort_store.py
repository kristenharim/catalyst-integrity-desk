"""The cohort store, and the three ways it has already lied about itself.

An append-only store that only ever grows will eventually be read as though growth
were evidence. It happened here: a background pass and a manual merge appended
concurrently, and the store held 179 rows for 131 distinct trials with 48 counted
twice. A figure published mid-run as "169 trials measured" was a row count covering
123 distinct trials. Every rate computed from it was wrong in the flattering
direction and nothing looked broken, because more rows reads as more data.

(An earlier version of this docstring said "49 rows of 180" and "n=169 was really
131". Both were wrong, and they are corrected here rather than left standing,
because a project whose thesis is that an uncorrected record is the defect cannot
leave a retracted figure asserted as fact in its own source.)

`load_results()` deduplicating on read closed that for the readers this project
owns. These tests close the rest:

  - the file itself now holds one row per trial, with the superseded rows archived
    rather than deleted, so a consumer reading it directly gets the same n
  - nothing outside `research/cohort.py` may read the store directly, so a future
    consumer cannot reintroduce the inflated view
  - every published figure cites a snapshot id, and the id is recomputed from the
    store here, so a snapshot cannot silently describe a file that has since moved
  - no pooled all-strata rate can be produced at all
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from research import cohort

REPO = os.path.join(os.path.dirname(__file__), "..")


def _rows():
    if not os.path.exists(cohort._results_path()):
        pytest.skip("no cohort measured yet")
    with open(cohort._results_path()) as f:
        return [json.loads(line) for line in f if line.strip()]


# ---------------------------------------------------------------------------
# The file itself, not just the reader

def test_store_holds_one_row_per_trial():
    """Post-compaction the raw file agrees with the deduplicated read.

    This is the assertion `load_results()` could not make: it fixed what *this*
    project reads, and left the inflated view sitting in the file for anyone else.
    """
    raw = _rows()
    distinct = {r["nct"] for r in raw}
    assert len(raw) == len(distinct), (
        f"{len(raw) - len(distinct)} duplicate rows in the store; run "
        f"`python3 -m research.cohort --compact`")


def test_compaction_archived_rather_than_deleted():
    """Every trial in the archive is still measured in the live store.

    Compaction must never be the thing that loses a measurement. If a trial appears
    only in the archive, a row was dropped rather than superseded.
    """
    if not os.path.exists(cohort._archive_path()):
        pytest.skip("nothing has been compacted")
    with open(cohort._archive_path()) as f:
        archived = [json.loads(line) for line in f if line.strip()]
    live = {r["nct"] for r in _rows()}
    orphans = sorted({r["nct"] for r in archived} - live)
    assert not orphans, f"archived but no longer measured: {orphans}"


# ---------------------------------------------------------------------------
# Nobody may read the store directly

def test_no_module_reads_the_store_around_load_results():
    """The store is read through `load_results()` or not at all.

    A direct read gets whatever the file contains, which is exactly how the n=169
    figure was published. Compaction makes a direct read correct *today*; this keeps
    it correct after the next resumable run appends a duplicate.

    Scoped to shipped modules. `tests/` may read the file directly, because
    asserting things about its raw contents is the point of this file.
    """
    offenders = []
    for sub in ("engine", "orchestrator", "console", "research"):
        d = os.path.join(REPO, sub)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".py"):
                continue
            path = os.path.join(d, name)
            if os.path.abspath(path) == os.path.abspath(cohort.__file__):
                continue          # the owner of the store
            with open(path) as f:
                src = f.read()
            for marker in ("results.jsonl", "_results_path", "_archive_path"):
                if marker in src:
                    offenders.append(f"{sub}/{name} references {marker}")
    assert not offenders, (
        "these read the cohort store directly instead of via load_results(): "
        + "; ".join(offenders))


# ---------------------------------------------------------------------------
# Strata are not poolable, so no pooled number may exist

def test_stats_refuses_a_pooled_all_strata_rate():
    """NIH trials carry a dead date about as often as industry ones and roughly
    2.4x as long. A pooled rate describes no population, so asking for one is an
    error rather than a number."""
    rows = cohort.load_results()
    if not rows:
        pytest.skip("no cohort measured yet")
    for bad in ("ALL", "all", "POOLED", ""):
        with pytest.raises(ValueError):
            cohort.stats(rows, bad)


def test_report_prints_no_pooled_section(capsys):
    if not cohort.load_results():
        pytest.skip("no cohort measured yet")
    cohort.report()
    out = capsys.readouterr().out
    assert "--- ALL" not in out, "the report printed a pooled all-strata section"
    for cls in cohort.STRATA:
        assert f"--- {cls}" in out


def test_snapshot_carries_no_pooled_figure():
    snap = cohort.load_snapshot()
    if snap is None:
        pytest.skip("no snapshot frozen yet")
    assert set(snap["strata"]) == set(cohort.STRATA), (
        "the snapshot's strata must be exactly the four measured strata, with no "
        "pooled entry")


# ---------------------------------------------------------------------------
# The snapshot id is the thing published numbers cite

def test_snapshot_id_still_matches_the_store():
    """A snapshot id is content-addressed. If the store has moved since the freeze,
    every figure citing that id is describing a file that no longer exists, so this
    fails rather than letting the citation rot quietly."""
    snap = cohort.load_snapshot()
    if snap is None:
        pytest.skip("no snapshot frozen yet")
    assert snap["snapshot_id"] == cohort.snapshot_id(), (
        "the frozen snapshot does not describe the current store; re-freeze with "
        "`python3 -m research.cohort --freeze` and update every figure citing the "
        "old id")


def test_snapshot_id_changes_when_a_measurement_changes():
    """Watched failing in the other direction: if the id did not move when a row
    moved, citing it would prove nothing."""
    rows = cohort.load_results()
    if not rows:
        pytest.skip("no cohort measured yet")
    before = cohort.snapshot_id(rows)
    mutated = [dict(r) for r in rows]
    mutated[0]["max_dead_days"] = (mutated[0].get("max_dead_days") or 0) + 1
    assert cohort.snapshot_id(mutated) != before


def test_snapshot_figures_match_a_recomputation():
    """Every published figure is recomputed from the store and compared to the
    frozen one, field by field. The snapshot is a cache of the measurement, and a
    cache that can disagree with its source is worse than no cache."""
    snap = cohort.load_snapshot()
    if snap is None:
        pytest.skip("no snapshot frozen yet")
    rows = [r for r in cohort.load_results() if "error" not in r]
    # The snapshot's own as-of date, never the clock. Point prevalence is a
    # statement about a date, so recomputing it against today would make this
    # test start failing tomorrow for no reason and, worse, would let a snapshot
    # frozen on one date be silently validated against another.
    as_of = cohort._parse_date(snap["as_of"])
    for cls in cohort.STRATA:
        assert snap["strata"][cls] == cohort.stats(rows, cls, as_of), cls
    assert snap["n_distinct_trials"] == len(rows)


def test_point_prevalence_is_pinned_not_read_from_the_clock():
    """The primary frequency must not drift with the wall clock.

    Verified by asking for the same stratum at two different as-of dates and
    requiring the answer to change. If it did not, the as_of argument would be
    decorative and the snapshot would silently mean 'whenever you ran it'.
    """
    import datetime
    rows = [r for r in cohort.load_results() if "error" not in r]
    if not rows:
        pytest.skip("no cohort measured yet")
    early = cohort.stats(rows, "INDUSTRY", datetime.date(2016, 1, 1))
    late = cohort.stats(rows, "INDUSTRY", datetime.date(2030, 1, 1))
    assert early["carrying_now"] < late["carrying_now"], (
        "point prevalence did not move between 2016 and 2030, so the as-of date "
        "is not reaching the computation")


def test_an_actual_completion_date_is_not_a_lapsed_commitment():
    """A past date typed ACTUAL is the reconciled case and must not count.

    This is the check whose absence produced a wrong published figure: an earlier
    pass read the type from a helper that never returned it, compared `None`
    against "ACTUAL", and counted every completed trial that had correctly
    recorded its completion date as carrying a lapsed one.
    """
    import datetime
    as_of = datetime.date(2026, 7, 22)
    base = {"sponsor_class": "INDUSTRY", "dead_date_stretches": 0,
            "dead_date_days": [], "n_transitions": 0, "established_days": 0}
    rows = [
        {**base, "nct": "A", "last_pcd": "2020-01-01", "last_pcd_type": "ACTUAL"},
        {**base, "nct": "B", "last_pcd": "2020-01-01", "last_pcd_type": "ESTIMATED"},
        {**base, "nct": "C", "last_pcd": "2029-01-01", "last_pcd_type": "ESTIMATED"},
    ]
    s = cohort.stats(rows, "INDUSTRY", as_of)
    assert s["carrying_now"] == 1, (
        "only the expired ESTIMATE counts: a past ACTUAL is a completed trial "
        "recording when it completed, and a future estimate has not expired")


def test_freeze_refuses_an_incomplete_measurement(monkeypatch):
    """A trial that failed to measure must block the freeze. A snapshot that
    quietly drops trials is the n-inflation bug wearing the other sign."""
    rows = cohort.load_results()
    if not rows:
        pytest.skip("no cohort measured yet")
    monkeypatch.setattr(cohort, "load_results",
                        lambda: rows + [{"nct": "NCT09999999",
                                         "sponsor_class": "NIH",
                                         "error": "JSONDecodeError: truncated"}])
    with pytest.raises(ValueError, match="failed to measure"):
        cohort.freeze()


def test_freeze_refuses_unsplit_refusals(monkeypatch):
    """An unsplit refusal rate is an upper bound, not a figure: it bundles a
    finding about the sponsor with a gap in our own data."""
    rows = [dict(r) for r in cohort.load_results() if "error" not in r]
    if not rows:
        pytest.skip("no cohort measured yet")
    stale = next((r for r in rows if r["sponsor_class"] == "INDUSTRY"), None)
    if stale is None:
        pytest.skip("no industry rows")
    stale["refused_revisions"] = stale.get("refused_revisions", 0) + 3   # unaccounted
    monkeypatch.setattr(cohort, "load_results", lambda: rows)
    with pytest.raises(ValueError, match="before the reason split"):
        cohort.freeze()
