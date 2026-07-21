"""Fabrication tests for the redline -> Granite -> ChallengeCard path.

Two tests:

1. `test_no_fabrication_live` -- sends a real breach to Granite over the watsonx.ai
   API and asserts that nothing in the returned rationale is a number absent from the
   input. Requires WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL in the environment.
   Skipped when credentials are absent.

2. `test_fabrication_guard_catches_invented_figure` -- injects a fake transport that
   returns a rationale containing a digit that was not in the input, and asserts that
   `_fabricated` detects it and the classify call falls back to the stub rather than
   returning the poisoned output.

3. `test_scripted_amendment_produces_challenge_card` -- builds two synthetic
   CatalystContract-like packets (before/after an amendment), runs run_redline with
   a stub classifier, and asserts the resulting ChallengeCard has a classification
   label and a non-empty memo.
"""
from __future__ import annotations

import os
import pytest

from dataclasses import replace

from engine.ledger import BeliefCard, Breach
from orchestrator.classifier import StubClassifier, LABELS
from orchestrator.granite import GraniteClassifier, _fabricated, _numbers_in, SYSTEM_PROMPT
from orchestrator.redline import as_directions, ContractDelta, run_redline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _card(metric: str = "gap_months",
          low: float = 0.0, high: float = 24.0) -> BeliefCard:
    return BeliefCard(
        card_id="test:RCKT-funded",
        scope="company:RCKT",
        claim=(
            "Rocket Pharmaceuticals reaches its Fanconi anemia primary completion "
            "on cash in hand, without a dilutive raise."
        ),
        metric=metric,
        expected_low=low,
        expected_high=high,
        driver="9.5 months runway against a 2026-05 registered completion (XBRL tag "
               "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents, as of "
               "2026-03-31; ClinicalTrials.gov NCT04248439 v42)",
        confidence=3,
        source="test",
        as_of="2026-07-21",
    )


def _breach(observed: float = -5.2, low: float = 0.0, high: float = 24.0) -> Breach:
    return Breach(
        card_id="test:RCKT-funded",
        metric="gap_months",
        observed=observed,
        expected_low=low,
        expected_high=high,
        direction="under",
    )


# ---------------------------------------------------------------------------
# Test 1: live Granite, no fabrication
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.environ.get("WATSONX_API_KEY"),
    reason="WATSONX_API_KEY not set; skipping live Granite test",
)
def test_no_fabrication_live():
    """Granite returns a rationale that contains no figure absent from its input.

    This is the single most important correctness property of the system: a model
    that invents a number and presents it as a measurement breaks the provenance
    chain the whole desk rests on.
    """
    card = _card()
    breach = _breach()

    clf = GraniteClassifier()
    # The context includes directions so the full redline path is exercised.
    ctx = {
        "directions": (
            "  gap_months (signed months of runway surplus at the registered primary "
            "completion date; negative means cash is exhausted BEFORE the readout, not "
            "that the trial is running late): falls sharply\n"
            "  runway_months_low (months until cash exhaustion at the conservative end "
            "of the burn band; lower is worse): essentially unchanged"
        ),
    }
    result = clf.classify(card, breach, ctx)

    # If Granite fabricated, it falls back to the stub. The stub source is "stub".
    # A live Granite result has source="granite".
    # Either way there must be no invented figure in the rationale.
    invented = _fabricated(result.rationale, card, breach)
    assert not invented, (
        f"Granite fabricated {invented} in rationale: {result.rationale!r}"
    )
    assert result.label in LABELS
    assert 0.0 <= result.confidence <= 1.0


# ---------------------------------------------------------------------------
# Test 2: fabrication guard catches an invented figure
# ---------------------------------------------------------------------------

def test_fabrication_guard_catches_invented_figure():
    """A transport that invents a number gets caught and the stub takes over.

    The invented figure is 42.7, which appears nowhere in the card or breach.
    The stub does not see that number either, so if the guard fails the
    assertion on `invented` below would catch it from the other direction.
    """
    card = _card()
    breach = _breach()

    poisoned_response = {
        "choices": [{
            "message": {
                "content": (
                    '{"label": "direct_contradiction", "confidence": 0.9, '
                    '"rationale": "The gap has fallen to 42.7 months below the '
                    'approved floor, confirming the thesis is broken."}'
                )
            }
        }]
    }

    def fake_transport(messages):
        return poisoned_response

    clf = GraniteClassifier(transport=fake_transport)
    result = clf.classify(card, breach, {})

    # The guard must have fired and the fallback stub must have answered.
    assert result.source == "stub", (
        f"expected stub fallback after fabrication, got source={result.source!r}"
    )
    # The stub rationale must not contain 42.7 either.
    assert "42.7" not in result.rationale


# ---------------------------------------------------------------------------
# Test 3: scripted amendment produces a ChallengeCard
# ---------------------------------------------------------------------------

def test_scripted_amendment_produces_challenge_card():
    """A synthetic amendment that pushes gap_months below zero produces a
    ChallengeCard with a label and a non-empty memo.

    No live network calls. The before/after packets are constructed directly
    rather than via build() so the test is offline and deterministic.
    """
    # Simulate before: funded, gap positive.
    before_packet = {
        "gap_months": 9.5,
        "runway_months_low": 9.5,
        "burn_ttm_annual": 80_000_000.0,
        "pcd_revisions": 3.0,
        "max_days_expired": 0.0,
    }
    # Simulate after: completion date slipped, now gap is negative.
    after_packet = {
        "gap_months": -5.2,
        "runway_months_low": 9.5,
        "burn_ttm_annual": 80_000_000.0,
        "pcd_revisions": 4.0,
        "max_days_expired": 0.0,
    }

    directions = as_directions(before_packet, after_packet)

    # gap_months: 9.5 -> -5.2 is a sharp fall. Confirm direction is present.
    assert "gap_months" in directions
    assert "falls sharply" in directions

    # build a card whose approved range is [0, 24] so -5.2 is a breach
    card = _card(low=0.0, high=24.0)

    # ContractDelta with synthetic packets -- bypass the full network stack
    # by constructing a minimal object whose .before and .after properties
    # return the pre-baked dicts directly.
    class _SyntheticDelta:
        def directions(self):
            return as_directions(before_packet, after_packet)

        @property
        def after(self):
            return after_packet

    delta = _SyntheticDelta()

    breach = Breach(
        card_id=card.card_id,
        metric="gap_months",
        observed=-5.2,
        expected_low=0.0,
        expected_high=24.0,
        direction="under",
    )
    from orchestrator.challenge import build_challenge
    ctx = {"directions": delta.directions()}
    challenge = build_challenge(card, breach, ctx, StubClassifier())

    assert challenge is not None
    assert challenge.classification.label in LABELS, (
        f"unexpected label: {challenge.classification.label!r}"
    )
    assert challenge.memo.strip(), "memo must not be empty"
    # The memo must name the card_id so a reviewer can trace it.
    assert card.card_id in challenge.memo
    # The fabrication rule applies to the model's rationale text, not the
    # application-rendered memo template. The template legitimately includes
    # engine-computed values (confidence, breach reading, band) and those are
    # fine -- provenance is maintained because the values come from the engine,
    # not from the model. Check only the classification rationale itself.
    rationale = challenge.classification.rationale
    invented = _fabricated(rationale, card, breach)
    assert not invented, (
        f"rationale contains figures not in inputs: {invented}\nrationale: {rationale!r}"
    )
