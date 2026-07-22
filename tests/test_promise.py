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
