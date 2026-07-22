"""Promise identity: the tests that matter are the ones asserting a REFUSAL.

Every other guard in this project stops a wrong number from being displayed.
This one stops a *right-looking* number from being computed at all, and the
failure it prevents is the worst one available: an exact subtraction across two
records that describe different commitments, rendered with a full provenance
trail underneath it. The citation makes it more convincing, not less.

So the assertions below are mostly `slip_days is None`. A test suite for this
module that only checked the happy path would be checking the easy half.
"""
from __future__ import annotations

import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.promise import (  # noqa: E402
    DATE_ONLY, SCOPE_REVISION, SUPERSESSION, UNCERTAIN, UNCHANGED,
    Promise, Transition, classify, net_slip_days, walk,
)

BASE = dict(actor="Rocket Pharmaceuticals Inc.", subject="NCT06092034",
            milestone="primary_completion", scope="PHASE2",
            endpoint="safety and tolerability", population="30",
            status="RECRUITING")


def p(**over) -> Promise:
    return Promise(**{**BASE, **over})


# ---------------------------------------------------------------------------
# The two transitions that MAY produce a number
# ---------------------------------------------------------------------------

def test_date_only_move_is_comparable_and_reproduces_the_real_slip():
    """Rocket's registered completion moved 2025-09-01 to 2028-04-01.

    943 days is the figure the engine already reports for this trial, so this
    doubles as a cross-check that promise identity agrees with the number the
    rest of the system has been showing.
    """
    t = classify(p(due=date(2025, 9, 1)), p(due=date(2028, 4, 1)))
    assert t.kind == DATE_ONLY
    assert t.comparable
    assert t.slip_days == 943


def test_unchanged_is_zero_not_none():
    """Zero slip and no slip are different answers and must not collapse."""
    t = classify(p(due=date(2028, 4, 1)), p(due=date(2028, 4, 1)))
    assert t.kind == UNCHANGED
    assert t.slip_days == 0


# ---------------------------------------------------------------------------
# The three that MUST NOT
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("dimension,new_value", [
    ("endpoint", "overall survival"),
    ("population", "120"),
    ("scope", "PHASE3"),
    ("milestone", "study_completion"),
    ("actor", "Acquirer Bio Inc."),
])
def test_a_changed_dimension_refuses_a_slip_number(dimension, new_value):
    """The date moved AND the commitment changed shape.

    The subtraction still evaluates. It just does not mean what it appears to
    mean, so the module refuses to state it. This is the entire point of the
    file: 943 days between two different promises is not slip, it is a category
    error with a citation attached.
    """
    t = classify(p(due=date(2025, 9, 1)),
                 p(due=date(2028, 4, 1), **{dimension: new_value}))
    assert t.kind == SCOPE_REVISION, f"{dimension} change should be a scope revision"
    assert not t.comparable
    assert t.slip_days is None, (
        f"a changed {dimension} produced a slip number; that number would be "
        f"false and would carry a provenance trail making it look authoritative"
    )
    assert dimension in t.changed


@pytest.mark.parametrize("status", ["TERMINATED", "WITHDRAWN", "SUSPENDED"])
def test_a_terminal_status_is_supersession_not_slip(status):
    """A withdrawn trial's date did not slip. The commitment stopped existing.

    Reporting slip here invents a future that was retracted, which is the
    registry equivalent of treating a lapsed date as a catalyst.
    """
    t = classify(p(due=date(2025, 9, 1)), p(due=date(2028, 4, 1), status=status))
    assert t.kind == SUPERSESSION
    assert t.slip_days is None


def test_unknown_continuity_is_uncertain_never_unchanged():
    """An unreadable endpoint is not evidence the endpoint held.

    This is the failure mode that would be easiest to ship by accident: default
    the missing dimension to None on both sides, compare None to None, find them
    equal, and emit a confident number. Absence of a field is absence of
    evidence.
    """
    thin = {k: v for k, v in BASE.items() if k != "endpoint"}
    t = classify(Promise(**thin, endpoint=None, due=date(2025, 9, 1)),
                 Promise(**thin, endpoint=None, due=date(2028, 4, 1)))
    assert t.kind == UNCERTAIN
    assert t.slip_days is None


def test_different_subjects_are_not_a_revision():
    """Two trials are not two versions of one promise.

    A caller reaching here with two NCT ids has a bug, and quietly diffing them
    would produce the most confident wrong number this system can emit.
    """
    t = classify(p(due=date(2025, 9, 1)),
                 p(due=date(2028, 4, 1), subject="NCT04248439"))
    assert t.kind == UNCERTAIN
    assert t.slip_days is None


def test_a_missing_date_says_nothing_about_movement():
    t = classify(p(due=None), p(due=date(2028, 4, 1)))
    assert t.kind == UNCERTAIN
    assert t.slip_days is None


# ---------------------------------------------------------------------------
# The guard cannot be talked around
# ---------------------------------------------------------------------------

def test_comparable_is_computed_not_settable():
    """A caller cannot opt into a slip number by asserting confidence.

    `moved_days` can be set on any Transition; `slip_days` gates on `kind`. That
    is deliberate, so the refusal survives a caller who is sure they know better.
    """
    t = Transition(SCOPE_REVISION, "I am confident these are the same", moved_days=943)
    assert t.moved_days == 943
    assert not t.comparable
    assert t.slip_days is None


def test_net_slip_reports_what_it_refused():
    """A total computed over some revisions while others were refused must carry
    the refusal count, or it reads as a total over all of them.
    """
    total, refused = net_slip_days([
        Transition(DATE_ONLY, "", 100),
        Transition(SCOPE_REVISION, "", 900),
        Transition(SUPERSESSION, "", 400),
        Transition(DATE_ONLY, "", 8),
    ])
    assert total == 108, "refused revisions must not contribute to the total"
    assert refused == 2


def test_walk_classifies_every_consecutive_pair():
    ps = [p(due=date(2025, 9, 1)), p(due=date(2026, 9, 1)),
          p(due=date(2028, 4, 1), endpoint="overall survival")]
    ts = walk(ps)
    assert len(ts) == 2
    assert ts[0].kind == DATE_ONLY
    assert ts[1].kind == SCOPE_REVISION
    total, refused = net_slip_days(ts)
    assert refused == 1


def test_every_transition_carries_a_reason():
    """A refusal with no reason is indistinguishable from a bug."""
    cases = [
        classify(p(due=date(2025, 9, 1)), p(due=date(2028, 4, 1))),
        classify(p(due=date(2025, 9, 1)), p(due=date(2028, 4, 1), endpoint="os")),
        classify(p(due=date(2025, 9, 1)), p(due=date(2028, 4, 1), status="TERMINATED")),
        classify(p(due=None), p(due=date(2028, 4, 1))),
    ]
    for t in cases:
        assert t.reason and len(t.reason) > 10, t


def test_no_model_participates_in_classification():
    """Promise identity is decided by structured fields only.

    A model deciding 'is this the same promise' is exactly the judgement the
    architecture excludes, relocated from the value to the match. Asserted
    structurally so it cannot be softened later without the test naming it.
    """
    import ast
    path = os.path.join(os.path.dirname(__file__), "..", "engine", "promise.py")
    with open(path) as f:
        tree = ast.parse(f.read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
    assert "orchestrator" not in imported, (
        "engine/promise.py imports the orchestrator, which is where the model "
        "lives. Promise identity must be decided without one."
    )
    with open(path) as f:
        body = f.read().lower()
    for word in ("granite", "watsonx", "classifier("):
        assert word not in body, f"promise.py references {word!r}"


# ---------------------------------------------------------------------------
# The audit of this project's own reported figures
# ---------------------------------------------------------------------------
# This section exists because promise identity, applied to the committed
# snapshot, found that five of seven trials report a net-slip figure the record
# does not support. The reported number sums every date movement; the supported
# number sums only the movements where the endpoint and enrolment held. Where
# they differ, the difference is a revision that changed the commitment.
#
# NCT04248439 is the clearest: 1,008 reported days, of which a single +1,430-day
# revision coincided with the primary endpoint changing from "Phenotypic
# correction of bone marrow colony forming units" to "Bone Marrow Colony-Forming
# Cell Mitomycin-C resistance". Those are different endpoints, so those are
# different promises, so that is not slip.
#
# Unaffected, and worth stating because it is the demo centrepiece: the 677-day
# expired-date finding is about ONE version carrying an already-passed date, not
# a diff across two commitments, so nothing here touches it. Nor is the funding
# gap affected, which compares the current registered date to the runway.

import json as _json  # noqa: E402

_SNAP = os.path.join(os.path.dirname(__file__), "..", "data", "snapshot.json")


def _histories():
    with open(_SNAP) as f:
        snap = _json.load(f)
    for ticker, c in snap["contracts"].items():
        for h in [c.get("history")] + list(c.get("lapsed_history") or []):
            if h:
                yield ticker, h


def test_every_history_carries_its_audit():
    """A stored history without a classification would render the old,
    unaudited figure with nothing marking it."""
    seen = 0
    for ticker, h in _histories():
        seen += 1
        for key in ("slip_established_days", "slip_refused_revisions",
                    "slip_reported_days", "slip_fully_established"):
            assert key in h, f"{ticker} {h['nct']} is missing {key}"
    assert seen >= 5


def test_established_slip_never_exceeds_what_was_classified():
    """The supported figure must be the sum of comparable movements only."""
    for ticker, h in _histories():
        revs = h.get("revisions") or []
        comparable = sum(r.get("slip_days") or 0
                         for r in revs if r.get("slip_days") is not None)
        assert h["slip_established_days"] == comparable, (
            f"{ticker} {h['nct']}: established {h['slip_established_days']} but "
            f"comparable revisions sum to {comparable}"
        )


def test_refused_count_matches_the_revisions_marked_uncomparable():
    for ticker, h in _histories():
        revs = h.get("revisions") or []
        marked = sum(1 for r in revs
                     if r.get("transition") and r.get("slip_days") is None)
        assert h["slip_refused_revisions"] == marked, (
            f"{ticker} {h['nct']}: says {h['slip_refused_revisions']} refused, "
            f"{marked} revisions are marked non-comparable"
        )


def test_the_finding_itself_is_still_true():
    """At least one committed history reports slip it cannot support.

    If this ever fails it is good news and the docs must be corrected: it means
    every reported figure became establishable. It fails loudly rather than
    quietly so that nobody leaves the LIMITS.md section standing after the
    problem is gone.
    """
    unsupported = [
        (t, h["nct"], h["slip_reported_days"], h["slip_established_days"])
        for t, h in _histories()
        if not h["slip_fully_established"]
    ]
    assert unsupported, (
        "every reported slip figure is now fully established. That is an "
        "improvement, and docs/LIMITS.md must be updated to stop saying "
        "otherwise."
    )


def test_rocket_lapsed_trial_is_the_documented_case():
    """The specific numbers quoted in LIMITS.md and the log, pinned.

    A doc that quotes a figure the code no longer produces is the failure this
    project has already had twice with test counts.
    """
    h = next(h for _t, h in _histories() if h["nct"] == "NCT04248439")
    assert h["slip_reported_days"] == 1008
    assert h["slip_established_days"] == -422
    assert h["slip_refused_revisions"] == 1


def test_the_677_day_finding_is_untouched():
    """The demo centrepiece does not depend on promise identity.

    677 days is one version carrying an already-passed date. It is not a diff
    across two commitments, so nothing in this module can undermine it, and
    saying so explicitly stops the audit above being read as bigger than it is.
    """
    expired = [r for _t, h in _histories()
               for r in (h.get("revisions") or []) if r.get("carried_expired")]
    assert max(r["days_expired"] for r in expired) == 677
