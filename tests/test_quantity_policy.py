"""Granite prose carries no quantities, and the whole response goes if it does.

This replaces the span-typing guard, which authorised a magnitude by binding it
to a unit and a sign. That was strictly weaker than it read. The binding carried
no *field*, so any bare digit anywhere in the input licensed that magnitude in
the metric's own unit, and an audit demonstrated it against ordinary analyst
prose: a thesis reading "Phase 3 readiness across 12 sites and 2 arms" authorised
"3 months", "12 months" and "2 months", and the card's own conviction score
authorised a fourth. Those four cases are pinned at the bottom of this file,
because they are the reason the policy changed.

The rule now is that the model does not measure. Python and Jinja render every
figure from a deterministic field; Granite says which assumption moved and in
which direction. A response carrying any quantity is discarded whole and the
stub answers, so nothing is ever partially sanitised.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.ledger import BeliefCard, Breach                       # noqa: E402
from orchestrator.granite import (                                  # noqa: E402
    GraniteClassifier, _quantitative, SYSTEM_PROMPT,
)

REPO = os.path.join(os.path.dirname(__file__), "..")


@pytest.fixture
def live():
    card = BeliefCard(
        card_id="rckt:funded_to_catalyst", scope="trial:NCT04248439",
        claim="Rocket reaches the registered primary completion before runway "
              "exhaustion, with a non-negative funding gap.",
        metric="gap_months", expected_low=0.0, expected_high=10.4,
        driver="SEC XBRL liquidity (Q1-2026 10-Q) vs ClinicalTrials.gov registered PCD",
        confidence=3, source="10-Q", as_of="2026-07-21")
    breach = Breach(card_id="rckt:funded_to_catalyst", metric="gap_months",
                    observed=-14.5, expected_low=0.0, expected_high=10.4,
                    direction="under")
    return card, breach


# ---------------------------------------------------------------------------
# Refused: every shape a quantity arrives in
# ---------------------------------------------------------------------------

REFUSED = [
    ("plain magnitude",        "The gap is 3 months."),
    ("magnitude in words",     "Three months remain."),
    ("duration in words",      "The shortfall is thirty days."),
    ("confidence score",       "Confidence is 3 out of 10."),
    ("percentage",             "The result fell by 20%."),
    ("ratio",                  "The ratio is 2:1."),
    ("scientific notation",    "The value is 1e3."),
    ("bare year",              "Completion is expected in 2027."),
    ("date without a digit",   "The deadline is March fifth."),
    ("identifier",             "NCT04248439 no longer supports the claim."),
    ("input magnitude, right unit", "The gap is -14.5 months."),
    ("input magnitude, wrong unit", "The gap is 14.5 years."),
    ("input magnitude, wrong sign", "The gap is +14.5 months."),
]


@pytest.mark.parametrize("label,text", REFUSED, ids=[r[0] for r in REFUSED])
def test_quantities_are_refused(label, text):
    found = _quantitative(text)
    assert found, f"{label}: {text!r} carried no detected quantity"


# ---------------------------------------------------------------------------
# Accepted: the qualitative judgment the model is actually for
# ---------------------------------------------------------------------------

ACCEPTED = [
    ("assumption named",  "The approved funding assumption no longer holds."),
    ("direction only",    "The current evidence is below the analyst-defined threshold."),
    ("evidence class",    "The registered expectation changed."),
    ("review required",   "Human review is required."),
    ("refusal",           "The comparison cannot be established from the available evidence."),
]


@pytest.mark.parametrize("label,text", ACCEPTED, ids=[a[0] for a in ACCEPTED])
def test_qualitative_statements_are_accepted(label, text):
    found = _quantitative(text)
    assert not found, f"{label}: {text!r} was refused, naming {found}"


# ---------------------------------------------------------------------------
# The laundering cases that ended the previous policy
# ---------------------------------------------------------------------------

LAUNDERED = [
    ("'Phase 3' licensed 3 months",   "The gap has narrowed to 3 months of headroom."),
    ("'12 sites' licensed 12 months", "Cash runs out 12 months before the readout."),
    ("'2 arms' licensed 2 months",    "Only 2 months of runway remain."),
    ("confidence=3 licensed 3 months", "The shortfall is 3 months."),
]


@pytest.mark.parametrize("label,text", LAUNDERED, ids=[l[0] for l in LAUNDERED])
def test_semantic_laundering_is_refused(label, text):
    """Each of these passed the span-typing guard. None may pass this one."""
    assert _quantitative(text), f"{label}: {text!r} was authorised again"


# ---------------------------------------------------------------------------
# Whole-response discard, never partial sanitisation
# ---------------------------------------------------------------------------

def _transport(rationale, label="direct_contradiction", confidence=0.9):
    def call(messages):
        return {"choices": [{"message": {"content": json.dumps(
            {"label": label, "confidence": confidence, "rationale": rationale})}}]}
    return call


def test_a_quantitative_response_falls_back_whole(live):
    card, breach = live
    bad = "The gap is 3 months, which is below the approved floor."
    g = GraniteClassifier(api_key="x", project_id="y",
                          transport=_transport(bad))
    result = g.classify(card, breach, {})
    assert result.source == "stub", "a quantitative rationale must not reach the user"
    assert result.rationale != bad, "the model's text must be discarded, not reused"
    assert "3 months" not in result.rationale, (
        "the offending phrase survived; the guard must discard the response "
        "rather than edit the number out of it"
    )


def test_a_qualitative_response_is_kept(live):
    card, breach = live
    good = ("The approved funding assumption no longer holds. The current value "
            "sits below the approved value, so human review is required.")
    g = GraniteClassifier(api_key="x", project_id="y",
                          transport=_transport(good))
    result = g.classify(card, breach, {})
    assert result.source == "granite", f"clean prose was rejected: {result.rationale!r}"
    assert result.rationale == good


# ---------------------------------------------------------------------------
# The shipped artifact and the shipped prompt
# ---------------------------------------------------------------------------

def test_the_frozen_rationale_survives_the_policy():
    """The committed demo memo must not need regenerating to satisfy this.

    If it did, the policy would be changing a displayed figure, and the frozen
    snapshot is not F2's to move.
    """
    snap = json.load(open(os.path.join(REPO, "data", "snapshot.json")))
    rationale = snap["redline"]["classification"]["rationale"]
    assert snap["redline"]["classification"]["source"] == "granite"
    found = _quantitative(rationale)
    assert not found, (
        f"the frozen Granite rationale carries quantities {found}, so adopting "
        f"this policy would require rebuilding the demo snapshot: {rationale!r}"
    )


def test_the_prompt_asks_for_what_the_guard_enforces():
    """A guard the prompt does not warn about is a guard that fires constantly."""
    for phrase in ("NO QUANTITIES OF ANY KIND", "the approved value",
                   "the current value", "below the threshold"):
        assert phrase in SYSTEM_PROMPT, f"prompt no longer says {phrase!r}"
    # "No digits." survives as one item in the broader list. What must not
    # survive is the retired rule that digits were the whole of it.
    assert "must contain NO digits" not in SYSTEM_PROMPT, (
        "the prompt still states the retired digits-only rule as the constraint"
    )
