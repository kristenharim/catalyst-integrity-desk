"""The seam where IBM Granite plugs in.

StubClassifier is a deterministic placeholder so the full Measure -> Challenge ->
Support loop is demoable today. To go live, add a GraniteClassifier with the same
`.classify(card, breach, context)` signature and swap it in — that is the ONLY
change; the pipeline, ledger, and UI are untouched. That is the point of the seam.

Granite's real job (NOT what this stub does): read the BeliefCard's claim/rationale
and judge whether the breach changes the underlying *story* — a contract can be over
its numeric band and still be fine if the thesis said so. The stub only compares
numbers; do not mistake it for the semantic step.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from engine.ledger import BeliefCard, Breach

DIRECT_CONTRADICTION = "direct_contradiction"
ASSUMPTION_WEAKENED = "assumption_weakened"
ASSUMPTION_STRENGTHENED = "assumption_strengthened"
NEW_MATERIAL_EVIDENCE = "new_material_evidence"
LABELS = {DIRECT_CONTRADICTION, ASSUMPTION_WEAKENED, ASSUMPTION_STRENGTHENED, NEW_MATERIAL_EVIDENCE}


@dataclass
class Classification:
    label: str
    confidence: float     # 0-1 stub heuristic; Granite will replace with real judgment
    rationale: str        # placeholder narrative; Granite writes the real one
    source: str = "stub"  # "stub" | "granite"


class Classifier(Protocol):
    def classify(self, card: BeliefCard, breach: Breach, context: dict) -> Classification: ...


class StubClassifier:
    """Deterministic heuristic — a placeholder for Granite, NOT semantic reasoning."""

    def classify(self, card: BeliefCard, breach: Breach, context: dict) -> Classification:
        band = max(breach.expected_high - breach.expected_low, 1e-9)
        over_by = (breach.observed - breach.expected_high) if breach.direction == "over" \
            else (breach.expected_low - breach.observed)
        frac = over_by / band  # how far past the band, in band-widths

        if breach.direction == "over" and "risk" in breach.metric:
            label = DIRECT_CONTRADICTION if frac > 0.5 else ASSUMPTION_WEAKENED
            rationale = (
                f"Observed {breach.metric} = {breach.observed:.1f} exceeds the belief's ceiling "
                f"of {breach.expected_high:.1f}; the position is taking more risk than the thesis "
                f"called deliberate."
            )
        elif breach.direction == "under" and "return" in breach.metric:
            label = ASSUMPTION_WEAKENED
            rationale = (
                f"{breach.metric} = {breach.observed:.1f} fell below the floor {breach.expected_low:.1f}; "
                f"the position is not being paid for the risk it consumes — the 'compensated' premise "
                f"is eroding."
            )
        else:
            label = ASSUMPTION_WEAKENED
            rationale = (
                f"{breach.metric} = {breach.observed:.1f} is outside "
                f"[{breach.expected_low:.1f}, {breach.expected_high:.1f}]."
            )
        return Classification(label, round(min(0.5 + frac, 0.95), 2), rationale, source="stub")
