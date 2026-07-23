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
from engine.ctgov_history import CACHE

REPO = os.path.join(os.path.dirname(__file__), "..")


def _have_cache() -> bool:
    return os.path.isdir(CACHE) and any(os.scandir(CACHE))


def test_month_convention_reconstructs_the_first_of_month():
    """The second date reading is a bound only if it is computed off the same
    revision set as the first. The reconstruction from the cache must reproduce
    the stored first-of-month aggregates exactly, or end-of-month is a bound on a
    different measurement. Cache-present; skips on a clone without it.

    This is the independent check of the end-of-month figures that the prose
    guard reads from the snapshot rather than recomputes, because CI has no cache.
    """
    if not _have_cache():
        pytest.skip("no version cache; the second date reading cannot be checked")
    snap = cohort.load_snapshot()
    if snap is None:
        pytest.skip("no snapshot frozen yet")
    rows = [r for r in cohort.load_results() if "error" not in r]
    for cls in cohort.STRATA:
        sub = [r for r in rows if r["sponsor_class"] == cls]
        pro = lapse = est = 0
        for r in sub:
            p, l, e = cohort._held_split(r["nct"], False)
            pro += p
            lapse += l
            est += e
        s = snap["strata"][cls]
        assert (pro, lapse, est) == (
            s["revisions_prospective"], s["revisions_after_lapse"],
            s["revisions_after_lapse_to_estimate"]), (
            f"{cls}: the cache reconstruction does not reproduce the stored "
            f"first-of-month split, so the end-of-month reading is not a bound on "
            f"the same measurement")
    # The end-of-month figures, recomputed by an INDEPENDENT implementation rather
    # than by re-running the function that produced them. Comparing the snapshot to
    # `cohort.month_convention(rows)` would compare it to itself: an end-of-month
    # bug present at freeze time is in both sides and cancels. This resolves month
    # dates to the last day here, in the test, and walks the revisions itself.
    import calendar
    from datetime import date as _d

    def eom(raw):
        if not raw:
            return None
        p = [int(x) for x in raw.split("-")]
        if len(p) == 3:
            return _d(p[0], p[1], p[2])
        return _d(p[0], p[1], calendar.monthrange(p[0], p[1])[1])

    def revs(nct):
        out, prev = [], None
        for v in cohort._cached_versions(nct):
            f = cohort._parse_date(v.get("pcd"))          # first-of-month, to match the set
            if f is None or (prev is not None and f == prev):
                prev = f if f is not None else prev
                continue
            out.append(v)
            prev = f
        return out

    mc = snap["month_convention"]
    assert mc["anchor_days_eom"] == max(
        (cohort._parse_date(n.get("submitted")) - eom(p.get("pcd"))).days
        for p, n in zip(revs(cohort.ANCHOR_NCT), revs(cohort.ANCHOR_NCT)[1:])
        if eom(p.get("pcd")) and cohort._parse_date(n.get("submitted"))
        and eom(p.get("pcd")) < cohort._parse_date(n.get("submitted"))), "anchor eom"
    def pct(xs, q):
        if not xs:
            return None
        v = sorted(xs)
        k = (len(v) - 1) * q
        lo = int(k)
        return v[lo] + (v[min(lo + 1, len(v) - 1)] - v[lo]) * (k - lo)

    def eom_stretches(nct):
        vs = cohort._cached_versions(nct)
        out = []
        for a, b in zip(vs, vs[1:]):
            p = eom(a.get("pcd"))
            s = cohort._parse_date(b.get("submitted"))
            if p is not None and s is not None and p < s:
                out.append((s - p).days)
        return out

    for cls in cohort.STRATA:
        sub = [r for r in rows if r["sponsor_class"] == cls]
        lapse = est = pro = 0
        for r in sub:
            prev = None
            for v in revs(r["nct"]):
                p = eom(v.get("pcd"))
                s = cohort._parse_date(v.get("submitted"))
                if prev is not None and s is not None:
                    if (prev - s).days >= 0:
                        pro += 1
                    else:
                        lapse += 1
                        est += int((v.get("pcd_type") or "").upper() != "ACTUAL")
                prev = p
        m = mc["strata"][cls]
        assert m["revisions_after_lapse_eom"] == lapse, f"{cls} eom lapse"
        assert m["revisions_after_lapse_to_estimate_eom"] == est, f"{cls} eom est"
        assert abs(m["lapse_to_estimate_rate_eom"] - est / (pro + lapse)) < 1e-9, cls
        # The end-of-month DURATION medians the direction-corrected prose renders
        # ("rises from 336 to 388.5"). The circular check this replaced covered
        # these; the first independent walk did not, so a corrupted eom duration
        # passed. Recomputed here from the same last-day resolution.
        strs = [d for r in sub for d in eom_stretches(r["nct"])]
        per = [max(eom_stretches(r["nct"])) for r in sub if eom_stretches(r["nct"])]
        assert m["n_stretches_eom"] == len(strs), f"{cls} eom n_stretches"
        assert m["dead_days_p50_eom"] == pct(strs, .5), f"{cls} eom stretch p50"
        assert m["trial_days_p50_eom"] == pct(per, .5), f"{cls} eom trial p50"

    assert snap["silent_carrier_audit"] == cohort.silent_carrier_audit(
        rows, cohort._parse_date(snap["as_of"]))


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


STUDY_AS_OF = "2026-07-22"


def test_the_study_as_of_is_the_pinned_date():
    """Point prevalence is as of a fixed study date, and its value is pinned.

    `freeze()` preserves an existing snapshot's `as_of` so a re-freeze cannot walk
    every days-since-expiry figure forward as the wall clock advances -- a real
    drift that shifted every median by a day once. But preservation means a wrong
    `as_of`, hand-edited or drift-adopted before this guard existed, would also
    persist, and `figures_hash` recomputes over it so the snapshot stays
    internally consistent. No data check can tell a right point-prevalence date
    from a wrong one, because any date is a valid reference. So the date itself is
    pinned here. A new draw is a different study: it sets its own `as_of` and this
    line changes with it, deliberately.
    """
    snap = cohort.load_snapshot()
    if snap is None:
        pytest.skip("no snapshot frozen yet")
    assert snap["as_of"] == STUDY_AS_OF, (
        f"the snapshot's point-prevalence date is {snap['as_of']}, not the pinned "
        f"study date {STUDY_AS_OF}. If this is a new draw, update STUDY_AS_OF; if it "
        f"is a re-freeze that adopted the wall clock, restore the study date.")
    assert snap["frozen_at"] == STUDY_AS_OF


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


def test_a_hand_edit_to_any_published_figure_is_caught():
    """`snapshot_id` hashes the measured rows, not the derived blocks, so editing
    `anchor_case` or `month_convention` in the committed json did not move it and
    the figure published. `figures_hash` covers every block the reader sees and
    is recomputed from the snapshot's own bytes, no cache. Watched failing on the
    977-days edit a reviewer demonstrated.
    """
    snap = cohort.load_snapshot()
    if snap is None:
        pytest.skip("no snapshot frozen yet")
    assert snap.get("figures_hash") == cohort.figures_hash(snap), (
        "the snapshot's figures_hash disagrees with a recomputation over its own "
        "published blocks, so a figure was edited without re-freezing")
    # EVERY hashed key must be exercised, not a sample: the point is to catch a
    # regression that drops a key from `figures_hash`'s covered tuple, and a
    # sampled loop cannot see a dropped key it does not touch. `snapshot_id` was
    # added to the hash and was not in the old loop, so dropping it again would
    # have passed. This tampers one leaf inside each covered top-level key.
    import copy

    covered = ("strata", "anchor_case", "month_convention", "silent_carrier_audit",
               "clustering", "frame", "as_of", "seed", "snapshot_id",
               "n_distinct_trials")
    for key in covered:
        assert key in snap, f"{key} is not in the snapshot"
        tampered = copy.deepcopy(snap)
        v = tampered[key]
        if isinstance(v, dict):
            # descend to a leaf and change it
            node = v
            while isinstance(node, dict):
                k = next(iter(node))
                if not isinstance(node[k], (dict,)):
                    node[k] = (node[k] + 1) if isinstance(node[k], (int, float)) \
                        and not isinstance(node[k], bool) else "TAMPERED"
                    break
                node = node[k]
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            tampered[key] = v + 1
        else:
            tampered[key] = "TAMPERED"
        assert tampered["figures_hash"] != cohort.figures_hash(tampered), (
            f"editing the {key} block did not change the figures hash, so it is not "
            f"covered")


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


def test_freeze_preserves_an_existing_as_of(tmp_path, monkeypatch):
    """Re-freezing the same rows keeps the study date, not the wall clock.

    This is the preservation branch itself, which nothing exercised. It stops the
    drift that shifted every days-since-expiry figure by a day when a re-freeze
    picked up a rolled-over UTC date. No clock mock is needed: the study date is
    2026-07-22 and the wall clock in any later session is a different day, so a
    re-freeze that read the clock would move as_of and one that preserves does not.

    The write is redirected to a temp file. `freeze()` writes the snapshot, and
    running it against the committed path would rewrite `data/cohort/snapshot.json`
    as a test side effect -- byte-identical under a complete cache, but a partial
    cache (this study is resumable and fetch-bound) recomputes the cache-fed blocks
    from fewer versions and would corrupt the committed file while this test's
    cache-independent assertions still passed. The prior snapshot is copied to the
    temp path first, so `freeze()` reads the real committed `as_of` and writes back
    to the copy.
    """
    import shutil
    if not _have_cache():
        pytest.skip("freeze needs the version cache")
    snap = cohort.load_snapshot()
    if snap is None or snap["as_of"] != STUDY_AS_OF:
        pytest.skip("no snapshot at the study date")
    temp_snap = tmp_path / "snapshot.json"
    shutil.copy(cohort._snapshot_path(), temp_snap)
    monkeypatch.setattr(cohort, "_snapshot_path", lambda: str(temp_snap))
    refrozen = cohort.freeze()
    assert refrozen["as_of"] == STUDY_AS_OF, (
        "re-freezing adopted the wall clock instead of preserving the study date")
    assert refrozen["snapshot_id"] == snap["snapshot_id"]


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

    # And what a MISSING type does, which the original assertion never pinned.
    # `(row.get("last_pcd_type") or "").upper() != "ACTUAL"` is true for a row
    # with no type at all, so an unmeasured type counts as carrying, in the
    # flattering direction and in the same shape as the defect above. Every row
    # in the live store carries a type, so this pins behaviour rather than
    # recording a live error.
    missing = cohort.stats(
        [{**base, "nct": "D", "last_pcd": "2020-01-01"}], "INDUSTRY", as_of)
    assert missing["carrying_now"] == 1, (
        "a row with no recorded type counts as carrying. That is the current "
        "behaviour and it is the flattering direction; `freeze()` refuses rows "
        "that predate the field, which is what keeps it out of a published "
        "figure.")
    live = [r for r in cohort.load_results() if "error" not in r]
    if live:
        assert all("last_pcd_type" in r for r in live), (
            "a stored row has no completion-date type, so it would be counted "
            "as carrying an expired estimate without ever having been measured")


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
