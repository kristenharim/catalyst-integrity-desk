"""A magnitude is a value, a unit and a sign. All three must come from the input.

`_fabricated` rejects "a number absent from the input", which is the right rule
and was read too loosely. It matched bare digit runs anywhere in the card, so
the live Rocket driver, "SEC XBRL liquidity (Q1-2026 10-Q)", licensed the model
to write "2026 days of cash remaining" and "a 1 month delay". Neither figure was
ever computed.

The rule is unchanged. What tightened is the reading of "the same number".
Identifier spans are typed out first, because the digits in NCT04248439,
2026-05-05 and 10-Q name a record and measure nothing. What survives is parsed
into a Quantity of (value, unit, sign), and a rationale quantity is authorised
only when its value and sign both appear in the input and its unit is one the
input actually measures in.

It deliberately does not become "ban all digits". CLAUDE.md forbids that, and
for a good reason: a guard that rejects a figure the card itself states would
push the model toward vaguer prose, which is the opposite of the intent. The
controls at the bottom are as load-bearing as the rejections at the top.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.ledger import BeliefCard, Breach
from orchestrator.granite import Quantity, _fabricated, _typed

SNAPSHOT = Path(__file__).resolve().parents[1] / "data" / "snapshot.json"


@pytest.fixture(scope="module")
def live():
    """The real card the demo challenges, so this is about shipped data."""
    snap = json.loads(SNAPSHOT.read_text())
    r = snap["redline"]
    b = r["breach"]
    return BeliefCard(**r["proposed_card"]), Breach(
        card_id=b["card_id"], metric=b["metric"], observed=b["observed"],
        expected_low=b["expected_low"], expected_high=b["expected_high"],
        direction=b["direction"],
    )


# --- the mutation matrix ------------------------------------------------------
# Each row is a way a model can put a number on screen that nobody computed.

REJECTED = [
    ("invented magnitude", "This shifts the completion by 7 months."),
    ("borrowed from a fiscal quarter", "The sponsor has 2026 days of cash remaining."),
    ("borrowed from a quarter number", "A 1 month delay is immaterial."),
    ("borrowed from an ISO date", "The completion moved to 05 months out."),
    ("borrowed from a registry id", "Runway stands at 4248439 months."),
    ("wrong unit", "The runway covers 10 days of operations."),
    ("wrong sign", "The funding gap is +15 months."),
    ("number word", "The thesis slips by thirty months."),
    ("number word, wrong unit", "Cash covers fifteen days."),
]

ACCEPTED = [
    ("a figure the model was given", "The band's upper edge is 10 months."),
    ("the observed value with its own sign", "The gap is -15 months."),
    ("an echoed registry id and date",
     "Trial NCT04248439 filed on 2026-05-05 no longer supports the thesis."),
    ("the confidence it was handed", "Confidence stands at 3."),
    ("no magnitude at all",
     "The registered expectation the thesis depended on has been superseded."),
]


@pytest.mark.parametrize("label,text", REJECTED, ids=[r[0] for r in REJECTED])
def test_fabricated_magnitudes_are_refused(live, label, text):
    card, breach = live
    assert _fabricated(text, card, breach), f"{label}: {text!r} was authorised"


@pytest.mark.parametrize("label,text", ACCEPTED, ids=[a[0] for a in ACCEPTED])
def test_supported_statements_still_pass(live, label, text):
    card, breach = live
    offenders = _fabricated(text, card, breach)
    assert not offenders, f"{label}: {text!r} was refused, naming {offenders}"


# --- the schema ---------------------------------------------------------------

def test_a_quantity_binds_value_unit_and_sign():
    assert _typed("a 14.5 month slip") == {Quantity("14.5", "months", "")}
    assert _typed("down -15 months") == {Quantity("15", "months", "-")}
    assert _typed("thirty days") == {Quantity("30", "days", "")}
    # A unit this desk does not measure in is not comparable, so the magnitude
    # is judged on its value alone rather than silently trusted.
    assert _typed("7 widgets") == {Quantity("7", "", "")}


def test_identifier_spans_never_become_quantities():
    for name in ("NCT04248439", "2026-05-05", "Q1-2026", "10-Q", "CIK 0001281895"):
        assert _typed(name) == set(), f"{name} produced a measurable quantity"


def test_the_guard_does_not_ban_all_digits(live):
    """CLAUDE.md forbids that reading, and this is the test that holds it."""
    card, breach = live
    assert not _fabricated("The band's upper edge is 10 months.", card, breach)


# --- the boundary, stated rather than implied ---------------------------------

def test_a_ratio_of_two_input_values_is_not_caught(live):
    """A known limit of "a number absent from the input", written down.

    Both 3 and 10 are in the input, so a ratio built from them carries no number
    the model invented. Catching it would mean rejecting figures the card
    states, which is the reading CLAUDE.md rules out.
    """
    card, breach = live
    assert not _fabricated("Confidence is 3 out of 10.", card, breach)


def test_the_displayed_gap_is_refused_and_that_is_known(live):
    """Fail-closed, and worth knowing about.

    The console shows -14.5. The model is given -14.521560574948666 and the
    rounded -15, so quoting the displayed figure is refused. Safe direction, but
    it means the guard would reject correct output.
    """
    card, breach = live
    assert _fabricated("The gap is -14.5 months.", card, breach)
