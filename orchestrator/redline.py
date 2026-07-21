"""Redline: detect when a recomputed CatalystContract breaches its approved belief,
then build a ChallengeCard for human review.

Entry point: `run_redline(approved_contract, new_contract, card, classifier)`.

The engine produces two metric packets -- one for the previously approved state of the
contract, one for the recomputed state after an amendment or new filing. `as_directions`
turns the per-metric change into a description suitable for Granite: the direction and
size of the move in words, never a measured value. The application renders every figure.

Metric definitions (required because the signs are non-obvious):
    gap_months           signed months of runway surplus at the registered primary
                         completion date; negative means cash is exhausted BEFORE the
                         readout, not that the trial is running late.
    runway_months_low    months until cash exhaustion at the conservative (high-burn)
                         end of the burn band.
    burn_ttm_annual      trailing-twelve-month annualised operating cash outflow, in
                         dollars; higher is worse.
    pcd_revisions        cumulative count of times the registry date has moved.
    max_days_expired     longest continuous stretch, in days, that the registry showed
                         a primary completion date that had already passed.
"""
from __future__ import annotations

from dataclasses import dataclass

from engine.contract import to_packet
from engine.gap import CatalystContract
from engine.ledger import BeliefCard, Breach
from orchestrator.challenge import ChallengeCard, build_challenge
from orchestrator.classifier import StubClassifier

# Metric definitions surfaced in the brief so the model knows what the sign means.
# Indexed by metric_id; each value is the one-line definition.
_METRIC_DEFS: dict[str, str] = {
    "gap_months": (
        "signed months of runway surplus at the registered primary completion date; "
        "negative means cash is exhausted BEFORE the readout, not that the trial is "
        "running late"
    ),
    "runway_months_low": (
        "months until cash exhaustion at the conservative end of the burn band; "
        "lower is worse"
    ),
    "burn_ttm_annual": (
        "trailing-twelve-month annualised operating cash outflow in dollars; "
        "higher means the company is spending more"
    ),
    "pcd_revisions": (
        "cumulative number of times the sponsor has revised the registered primary "
        "completion date; a rising count means the sponsor is revising more"
    ),
    "max_days_expired": (
        "longest continuous stretch in days that the registry showed a completion date "
        "that had already passed; higher means the sponsor carried a stale date longer"
    ),
}


def _direction(pct_change: float) -> str:
    """Direction and magnitude of a metric shift, in words.

    Buckets are deliberately coarse -- the model reasons over these, so they must
    not be reconstructible into a figure. The same vocabulary as scenario.py's
    _direction, adapted for metrics that move in both directions.
    """
    if pct_change != pct_change:    # nan
        return "not comparable"
    verb = "rises" if pct_change > 0 else "falls"
    mag = abs(pct_change)
    if mag < 1:
        return "essentially unchanged"
    if mag < 5:
        return f"{verb} slightly"
    if mag < 15:
        return f"{verb} moderately"
    if mag < 30:
        return f"{verb} materially"
    return f"{verb} sharply"


def _pct_change(before: float, after: float) -> float:
    """Signed percentage change. Returns nan when the denominator is zero."""
    if before == 0.0:
        return float("nan")
    return (after / before - 1.0) * 100


def as_directions(before: dict[str, float], after: dict[str, float]) -> str:
    """Express each metric change as a direction label, never a value.

    Only metrics present in both packets are reported. Each line names the metric,
    its one-line definition (so the model knows what the sign means), and the
    direction of the move.

    The application renders every number. This string contains none.
    """
    lines = []
    for metric in sorted(set(before) & set(after)):
        b, a = before[metric], after[metric]
        direction = _direction(_pct_change(b, a))
        defn = _METRIC_DEFS.get(metric, "")
        if defn:
            lines.append(f"  {metric} ({defn}): {direction}")
        else:
            lines.append(f"  {metric}: {direction}")
    return "\n".join(lines) if lines else "  no shared metrics changed"


@dataclass
class ContractDelta:
    """Before and after packets for one amendment event."""
    approved: CatalystContract    # the contract as it was when last approved
    recomputed: CatalystContract  # the contract after the new filing or amendment

    @property
    def before(self) -> dict[str, float]:
        return to_packet(self.approved)

    @property
    def after(self) -> dict[str, float]:
        return to_packet(self.recomputed)

    def directions(self) -> str:
        """What moved, in words. Fed to Granite; never contains a measured value."""
        return as_directions(self.before, self.after)


def _breach_for_gap(card: BeliefCard, new_packet: dict[str, float]) -> Breach | None:
    """Return the gap_months breach if one exists, else None.

    The funding gap is the primary signal. When it is absent (not computable) the
    breach cannot be constructed and the caller falls back to other metrics.
    """
    gap = new_packet.get("gap_months")
    if gap is None:
        return None
    if card.in_range(gap):
        return None
    return Breach(
        card_id=card.card_id,
        metric="gap_months",
        observed=gap,
        expected_low=card.expected_low,
        expected_high=card.expected_high,
        direction="over" if gap > card.expected_high else "under",
    )


def run_redline(
    delta: ContractDelta,
    card: BeliefCard,
    classifier=None,
    context: dict | None = None,
) -> ChallengeCard | None:
    """Build a ChallengeCard when a recomputed contract breaches the approved belief.

    Returns None when no breach is detected -- the contract still satisfies the
    approved range and no review is needed.

    `context` is forwarded to Granite as supplementary evidence (e.g. news snippets).
    The directions string is merged into it so the prompt carries both the standing
    belief and a description of what moved.

    The classifier defaults to StubClassifier so the loop is demoable without
    credentials; swap in a GraniteClassifier for live judgment.
    """
    classifier = classifier or StubClassifier()

    breach = _breach_for_gap(card, delta.after)
    if breach is None:
        return None

    # Merge the directions summary into context so the Granite user prompt carries
    # the description of what moved alongside the standing belief and breach reading.
    ctx = dict(context or {})
    ctx["directions"] = delta.directions()

    return build_challenge(card, breach, ctx, classifier)
