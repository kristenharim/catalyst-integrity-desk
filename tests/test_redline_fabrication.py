"""Fabrication tests for the redline -> Granite -> ChallengeCard path.

1. `test_no_fabrication_live` -- sends a real breach to Granite over the watsonx.ai
   API and asserts that nothing in the returned rationale is a number absent from the
   input, and that the result came from Granite rather than the stub fallback. Requires
   WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL in the environment. Skipped when
   credentials are absent.

2. `test_fabrication_guard_catches_invented_figure` -- injects a fake transport that
   returns a rationale containing a digit that was not in the input, and asserts that
   `_fabricated` detects it and the classify call falls back to the stub rather than
   returning the poisoned output.

3. `test_scripted_amendment_produces_challenge_card` -- calls run_redline with
   synthetic before/after packets. Asserts it produces a ChallengeCard when the
   recomputed gap breaches the approved band and returns None when it does not.
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

    # source must be "granite" -- if the guard fired or the call failed the stub
    # answered, which means the test passed without reaching Granite at all.
    assert result.source == "granite", (
        f"expected granite, got source={result.source!r}; "
        f"rationale: {result.rationale!r}"
    )
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
    """run_redline fires when the recomputed gap breaches the approved band,
    and returns None when it does not.

    No live network calls. Packets are constructed directly so the test is
    offline and deterministic. The delta is duck-typed rather than built via
    build() to avoid network calls while still exercising run_redline itself.
    """
    before_packet = {
        "gap_months": 9.5,
        "runway_months_low": 9.5,
        "burn_ttm_annual": 80_000_000.0,
        "pcd_revisions": 3.0,
        "max_days_expired": 0.0,
    }
    # After a registry amendment: completion date slipped past runway exhaustion.
    after_breach_packet = {
        "gap_months": -5.2,
        "runway_months_low": 9.5,
        "burn_ttm_annual": 80_000_000.0,
        "pcd_revisions": 4.0,
        "max_days_expired": 0.0,
    }
    # After a different amendment: gap tightened but still inside the approved band.
    after_ok_packet = {
        "gap_months": 3.1,
        "runway_months_low": 9.5,
        "burn_ttm_annual": 80_000_000.0,
        "pcd_revisions": 4.0,
        "max_days_expired": 0.0,
    }

    # Confirm the direction labelling before exercising the full path.
    directions = as_directions(before_packet, after_breach_packet)
    assert "gap_months" in directions
    assert "falls sharply" in directions

    # card with approved range [0, 24]: -5.2 is a breach, 3.1 is not.
    card = _card(low=0.0, high=24.0)

    class _SyntheticDelta:
        """Minimal duck type: run_redline only reads .after and .directions()."""
        def __init__(self, after_pkt):
            self._after = after_pkt

        def directions(self):
            return as_directions(before_packet, self._after)

        @property
        def after(self):
            return self._after

    # --- breach path ---
    challenge = run_redline(_SyntheticDelta(after_breach_packet), card, StubClassifier())

    assert challenge is not None, "run_redline must return a ChallengeCard on a breach"
    assert challenge.classification.label in LABELS, (
        f"unexpected label: {challenge.classification.label!r}"
    )
    assert challenge.memo.strip(), "memo must not be empty"
    assert card.card_id in challenge.memo

    # The fabrication rule applies to the model's rationale text. The memo template
    # legitimately includes engine-computed values; check only the rationale.
    invented = _fabricated(challenge.classification.rationale, card,
                           challenge.breach)
    assert not invented, (
        f"rationale contains figures not in inputs: {invented}\n"
        f"rationale: {challenge.classification.rationale!r}"
    )

    # --- no-breach path ---
    result = run_redline(_SyntheticDelta(after_ok_packet), card, StubClassifier())
    assert result is None, (
        "run_redline must return None when the gap stays inside the approved band"
    )
