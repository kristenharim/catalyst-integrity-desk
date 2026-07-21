"""Challenge pipeline: turn a breach into a bounded, human-answerable review, then
apply the human's decision to the governed stores.

Flow:  breach -> build_challenge (classify + redline + memo)  ->  human Decision
       -> apply_decision  ->  approve/edit: ledger.update  |  reject: review-log

Three separate stores (as designed): the BeliefLedger (approvals only), the
ReviewLog (rejections + why), and the eval-set (later — reviewed examples become
regression tests). Nothing here computes a risk number, and nothing changes a
belief without an explicit human verdict.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
import os
import time

from engine.ledger import BeliefCard, BeliefLedger, Breach
from orchestrator.classifier import Classifier, StubClassifier, Classification

ACCEPT, REDUCE, HEDGE = "accept", "reduce", "hedge"

# Structured fields the human answers on the challenge card (bounded, not free chat).
QUESTIONS = [
    {"field": "intentional", "prompt": "Is this exposure intentional or accidental?",
     "options": ["intentional", "accidental"]},
    {"field": "conviction", "prompt": "Conviction in the driver now (1-5)?",
     "options": [1, 2, 3, 4, 5]},
    {"field": "thesis", "prompt": "One-line thesis for the disposition.", "options": None},
    {"field": "invalidation", "prompt": "What would prove this wrong?", "options": None},
    {"field": "action", "prompt": "Action?", "options": [ACCEPT, REDUCE, HEDGE]},
]


@dataclass
class ChallengeCard:
    card_id: str
    breach: Breach
    classification: Classification
    memo: str                    # narrative draft (stub; Granite replaces)
    proposed_card: BeliefCard    # the "accept new reality" redline vs the current card
    questions: list = field(default_factory=lambda: QUESTIONS)

    def redline(self) -> str:
        """Human-readable diff of the proposed change vs the current belief."""
        cur, new = self.breach, self.proposed_card
        if new.expected_low != cur.expected_low:
            return f"expected_low: {cur.expected_low:.1f} -> {new.expected_low:.1f}"
        if new.expected_high != cur.expected_high:
            return f"expected_high: {cur.expected_high:.1f} -> {new.expected_high:.1f}"
        return "no range change proposed"


def build_challenge(card: BeliefCard, breach: Breach, context: dict | None = None,
                    classifier: Classifier | None = None) -> ChallengeCard:
    classifier = classifier or StubClassifier()
    cls = classifier.classify(card, breach, context or {})

    # Proposed redline = "accept the new reality": widen the band to include the
    # observed value. Approving this says "yes, this exposure is acceptable now."
    if breach.direction == "over":
        proposed = replace(card, expected_high=round(breach.observed, 1))
    else:
        proposed = replace(card, expected_low=round(breach.observed, 1))

    memo = (
        f"CHALLENGE [{cls.label}]  {card.card_id} (v{card.version})  conf {cls.confidence}\n"
        f"  Belief : {card.claim}\n"
        f"  Driver : {card.driver} (conviction {card.confidence}/5)\n"
        f"  Reading: {breach.metric} = {breach.observed:.1f}, expected "
        f"[{breach.expected_low:.1f}, {breach.expected_high:.1f}]\n"
        f"  {cls.rationale}\n"
        # Every number above is rendered here from the engine's output; the classifier
        # supplies only the judgment sentence. The tag keeps that provenance visible.
        + ("  [judgment drafted by IBM Granite]" if cls.source == "granite" else
           "  [stub judgment — IBM Granite drafts this from the RiskPacket + news context]")
    )
    return ChallengeCard(card.card_id, breach, cls, memo, proposed)


@dataclass
class Decision:
    verdict: str                      # "approve" | "edit" | "reject"
    author: str                       # e.g. "human:kristen" — this is the governance gate
    reason: str = ""
    edited_card: BeliefCard | None = None   # required for "edit"
    answers: dict = field(default_factory=dict)


class ReviewLog:
    """3rd store: why a challenge was rejected. Append-only, never touches the ledger."""

    def __init__(self, path: str):
        self.path = path

    def append(self, challenge: ChallengeCard, decision: Decision) -> dict:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        rec = {
            "ts": time.time(),
            "card_id": challenge.card_id,
            "classification": challenge.classification.label,
            "verdict": decision.verdict,
            "reason": decision.reason,
            "author": decision.author,
            "observed": challenge.breach.observed,
            "answers": decision.answers,
        }
        with open(self.path, "a") as f:
            f.write(json.dumps(rec) + "\n")
        return rec

    def all(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        with open(self.path) as f:
            return [json.loads(line) for line in f if line.strip()]


def apply_decision(ledger: BeliefLedger, review_log: ReviewLog,
                   challenge: ChallengeCard, decision: Decision):
    """Route the human verdict to the right store. Approve/edit -> ledger version
    bump; reject -> review log. The ledger is the ONLY thing an approval mutates."""
    if decision.verdict in ("approve", "edit"):
        card = decision.edited_card if decision.verdict == "edit" else challenge.proposed_card
        if card is None:
            raise ValueError("edit verdict requires edited_card")
        return ledger.update(
            card, author=decision.author,
            triggered_by=f"breach:{challenge.card_id}",
            reason=decision.reason or challenge.classification.label,
        )
    if decision.verdict == "reject":
        return review_log.append(challenge, decision)   # belief stands; ledger untouched
    raise ValueError(f"unknown verdict: {decision.verdict}")
