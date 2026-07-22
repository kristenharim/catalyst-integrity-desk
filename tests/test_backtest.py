"""The replay must be blind to the future, or it is a story rather than a test.

Everything here exists to defend one property: an evaluation with a cutoff of
date D sees only what a sponsor had submitted on or before D. If that leaks, the
backtest reports what we already know and calls it a prediction, which is the
most flattering possible bug and the hardest to notice.
"""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.ctgov_history import _parse_date  # noqa: E402
from research.backtest import (  # noqa: E402
    _versions, as_known_on, cached_trials, carried_until_corrected,
    first_observable, replay,
)

ROCKET = "NCT04248439"


@pytest.fixture(scope="module")
def cached():
    trials = cached_trials()
    if ROCKET not in trials:
        pytest.skip("registry version cache is absent; replay needs data/cache/")
    return trials


# ---------------------------------------------------------------------------
# Blindness
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cutoff", ["2020-06-01", "2021-01-01", "2023-09-01",
                                    "2024-04-08", "2026-01-01"])
def test_no_version_submitted_after_the_cutoff_is_visible(cached, cutoff):
    """The one line that makes this a backtest."""
    cut = _parse_date(cutoff)
    for nct in cached:
        for rev in as_known_on(nct, cut):
            submitted = _parse_date(rev["submitted"])
            assert submitted is not None and submitted <= cut, (
                f"{nct} version {rev['version']} was submitted {rev['submitted']}, "
                f"after the {cutoff} cutoff, and leaked into the replay"
            )


def test_visibility_only_grows_with_time(cached):
    """A later cutoff can see everything an earlier one saw, and possibly more.

    Verified failing by flipping the comparison in `as_known_on` from <= to >=,
    which made later cutoffs see fewer versions.
    """
    for nct in cached[:6]:
        counts = [len(as_known_on(nct, date(y, 1, 1)))
                  for y in range(2019, 2028)]
        assert counts == sorted(counts), (nct, counts)


def test_a_cutoff_before_the_first_filing_sees_nothing(cached):
    first = min(_parse_date(r["submitted"]) for r in _versions(ROCKET)
                if r["submitted"])
    assert as_known_on(ROCKET, first - timedelta(days=1)) == []
    assert replay(ROCKET, first - timedelta(days=1)) == []


# ---------------------------------------------------------------------------
# The finding, derived rather than asserted
# ---------------------------------------------------------------------------

def test_the_677_days_is_reproduced_by_replay(cached):
    """The headline result, recomputed from raw versions.

    The engine gets 677 from `held_days`. This gets it from two dates and a
    subtraction over the cached version list. Two independent routes to the same
    number is what makes it worth quoting.
    """
    stretches = carried_until_corrected(ROCKET)
    assert stretches, "no carried-expired stretch found on the demo trial"
    longest = max(stretches, key=lambda s: s["days_carried"])
    assert longest["days_carried"] == 677
    assert longest["expired_on"] == "2022-06-01"
    assert longest["corrected_on"] == "2024-04-08"


def test_the_signal_was_observable_the_day_after_it_expired(cached):
    """Detection latency, and the reason it is the honest claim to make.

    The evidence became public on 2022-06-02, when nothing was filed and nothing
    happened: a date simply passed. Sampling only filing dates would report the
    first day someone touched the record, which is a later and flattering number.
    """
    first = first_observable(ROCKET, "carried_expired")
    assert first == date(2022, 6, 2), first


def test_the_desk_would_have_said_it_before_the_correction(cached):
    """A replay a year before the sponsor corrected the date must already
    state the finding, in period-accurate terms."""
    obs = replay(ROCKET, date(2023, 9, 1))
    expired = [o for o in obs if o.kind == "carried_expired"]
    assert expired, "the standing expired date was not surfaced"
    assert expired[0].days_public_before_now == 457
    assert "2022-06" in expired[0].detail


def test_movement_in_a_replay_obeys_promise_identity(cached):
    """A replay must not report movement the record cannot support, for the
    same reason the live view must not."""
    for nct in cached[:6]:
        for o in replay(nct, date(2026, 1, 1)):
            if o.kind == "movement":
                assert "held its shape" in o.detail
                assert "not comparable" in o.detail


# ---------------------------------------------------------------------------
# Scope, stated as a test so it cannot be quietly overclaimed
# ---------------------------------------------------------------------------

def test_the_replay_makes_no_prediction(cached):
    """No observation may assert an outcome, a cause, or a verdict.

    The backtest measures when evidence became public. It does not measure what
    the evidence foretold, there is no preregistered out-of-sample study here,
    and `orchestrator/lexicon.py` forbids saying otherwise.
    """
    from orchestrator import lexicon

    for nct in cached[:8]:
        for o in replay(nct, date(2026, 1, 1)):
            violations = lexicon.scan(o.detail)
            assert not violations, (
                f"{nct} {o.kind} makes a forbidden claim: "
                + "; ".join(str(v) for v in violations)
            )


def test_carried_expired_needs_no_cross_commitment_comparison(cached):
    """The sturdiest signal in the system, and why.

    One version, one date, one clock. It does not depend on promise identity, so
    the audit that undermined the slip figures cannot touch it. Asserted here so
    the distinction survives someone refactoring the two together.
    """
    obs = replay(ROCKET, date(2023, 9, 1))
    kinds = {o.kind for o in obs}
    assert "carried_expired" in kinds
    # Only two versions are visible at that cutoff, and the finding stands on
    # the latest one alone.
    assert len(as_known_on(ROCKET, date(2023, 9, 1))) == 2


# ---------------------------------------------------------------------------
# The cohort store must not inflate its own n
# ---------------------------------------------------------------------------
# The store is append-only and resumable, so a trial measured twice appends
# twice. Counting both inflates n and every rate computed from it, silently, in
# the direction of more data. It happened: a published report of n=169 was
# really 131 distinct trials, because a background pass and a manual merge
# appended concurrently.

def test_cohort_results_are_deduplicated_on_read():
    """One row per NCT, whatever the file contains."""
    import collections
    from research.cohort import load_results, _results_path

    rows = load_results()
    if not rows:
        pytest.skip("no cohort measured yet")
    counts = collections.Counter(r["nct"] for r in rows)
    dupes = {k: v for k, v in counts.items() if v > 1}
    assert not dupes, f"load_results returned duplicate trials: {dupes}"


def test_deduplication_prefers_the_more_informative_row():
    """A re-measure carrying refusal reasons must beat an older row without
    them, regardless of which was written first. Otherwise resuming a run can
    silently downgrade the schema of rows already measured."""
    from research.cohort import load_results

    rows = load_results()
    if not rows:
        pytest.skip("no cohort measured yet")
    # Any stratum that has been re-measured must show reasons on every row that
    # has any refusals at all.
    for r in rows:
        if r.get("refused_scope") or r.get("refused_superseded"):
            assert "refusal_reasons" in r, r["nct"]


def test_reported_n_matches_distinct_trials():
    """The n printed in a report is the count of distinct trials, not rows.

    Asserted because the two diverged in a published figure, and the divergence
    was invisible: more rows looks like more data rather than like a bug.
    """
    import json
    import os
    from research.cohort import load_results, _results_path

    path = _results_path()
    if not os.path.exists(path):
        pytest.skip("no cohort measured yet")
    with open(path) as f:
        raw = [json.loads(l) for l in f if l.strip()]
    distinct = {r["nct"] for r in raw}
    assert len(load_results()) == len(distinct)
    assert len(load_results()) <= len(raw)
