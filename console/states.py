"""Evidence state for one monitored decision, and the triggers behind it.

Three axes describe a monitored decision, and they are deliberately kept apart:

  evidence   what the current evidence says about the contract
  workflow   what a human is doing about it
  record     whether the decision history itself is still intact

One badge carrying all three is how a tampered ledger ends up reading as a
broken thesis, and a broken thesis ends up reading as a tampered ledger. This
module computes the FIRST axis only. It imports nothing from engine.ledger or
orchestrator.anchor, and that is load bearing rather than tidy: it cannot learn
about record integrity even by accident. console/review.py joins the other two
at request time, because both depend on a file that changes after the snapshot
was built.

Everything here is computed from one snapshot. Nothing reads the clock and
nothing reads the network, so the state a committed snapshot reports today is
the state it reports next month.
"""
from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Evidence states, in precedence order
# ---------------------------------------------------------------------------
# The list order IS the precedence. Writing the ladder as a separate if/elif
# chain lets the two drift; deriving the ladder from the declared order means a
# reordering here is the only way to change precedence.
#
# Deterministic failure outranks contingent on purpose. A contract can both have
# failed a stated condition and be carrying an endpoint reword nobody has ruled
# on. Leading with "contingent" in that case buries the part that is actually
# established, which is the more actionable half.

UNAVAILABLE = "unavailable"
REVIEW_REQUIRED = "review_required"
CONTINGENT = "contingent"
INTACT = "intact"

EVIDENCE_STATES = [
    (UNAVAILABLE, "unavailable"),
    (REVIEW_REQUIRED, "review required"),
    (CONTINGENT, "contingent"),
    (INTACT, "intact"),
]
EVIDENCE_LABELS = dict(EVIDENCE_STATES)
EVIDENCE_RANK = {k: i for i, (k, _) in enumerate(EVIDENCE_STATES)}

# Badge precedence and reading order are two different questions and were worth
# separating. Precedence asks which single state is true of one decision, and
# "unavailable" wins there because a contract you cannot establish is not a
# contract you may call breached. Reading order asks which decision to open
# first, and there "review required" wins, because an unavailable row needs its
# data fixed while a breached one needs a judgement today. Ranking unavailable
# first put a row nobody can act on above the one that broke.
INBOX_ORDER = [REVIEW_REQUIRED, CONTINGENT, UNAVAILABLE, INTACT]
INBOX_RANK = {k: i for i, k in enumerate(INBOX_ORDER)}

# ---------------------------------------------------------------------------
# Trigger states
# ---------------------------------------------------------------------------
# What kind of thing a trigger is, which decides what evidence state it forces.
#
#   deterministic  a stated condition failed, and the failure is established
#   contingent     the comparison needs a human to read two texts
#   unavailable    the evidence or the identity needed is not usable
#   watch          a stated condition is near, and none has failed

DETERMINISTIC = "deterministic"
WATCH = "watch"

# CONTINGENT and UNAVAILABLE are reused from the evidence states above: a
# contingent trigger forces a contingent state, an unavailable trigger forces an
# unavailable one. The other two rename themselves on the way up.
#
# A watch trigger forces `intact` on purpose. "Review required" is a claim that
# a deterministic condition changed or expired, and being four months from a
# threshold is neither. The contract still holds, so the badge says so and the
# trigger underneath says what to watch. Calling that review required would
# overstate the record, which is the one thing this product may not do.
_FORCES = {
    UNAVAILABLE: UNAVAILABLE,
    DETERMINISTIC: REVIEW_REQUIRED,
    CONTINGENT: CONTINGENT,
    WATCH: INTACT,
}

SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}

# ---------------------------------------------------------------------------
# Trigger kinds
# ---------------------------------------------------------------------------

FUNDING_THRESHOLD_CROSSED = "funding_threshold_crossed"
FUNDING_THRESHOLD_APPROACHING = "funding_threshold_approaching"
REGISTERED_EXPECTATION_EXPIRED = "registered_expectation_expired"
ENDPOINT_CONTINUITY = "endpoint_continuity"
COMPARISON_REFUSED = "comparison_refused"
RUNWAY_UNRELIABLE = "runway_unreliable"

TRIGGER_LABELS = {
    FUNDING_THRESHOLD_CROSSED: "funding threshold crossed",
    FUNDING_THRESHOLD_APPROACHING: "approaching funding threshold",
    REGISTERED_EXPECTATION_EXPIRED: "registered expectation expired",
    ENDPOINT_CONTINUITY: "endpoint continuity requires review",
    COMPARISON_REFUSED: "comparison refused",
    RUNWAY_UNRELIABLE: "burn estimate unreliable",
}

# Months of gap below which a contract is close enough to breaching to be worth
# a look. One quarter is too tight to act on and a year is not news, so a half
# year is the compromise, and it is a judgement rather than a finding.
APPROACHING_MONTHS = 6.0

# The queue that shipped before this module had five states of its own. The
# inbox groups triggers per decision instead, but /queue still redirects and its
# rows are still built, so the mapping is kept explicit. Triggers with no entry
# here are new and correctly absent from the old queue rather than silently
# changing its counts.
LEGACY_QUEUE_STATE = {
    FUNDING_THRESHOLD_CROSSED: "breached",
    REGISTERED_EXPECTATION_EXPIRED: "lapsed",
    FUNDING_THRESHOLD_APPROACHING: "approaching",
    RUNWAY_UNRELIABLE: "unreliable",
}


@dataclass(frozen=True)
class Trigger:
    """One reason a decision needs looking at.

    `detail` is a finished sentence, not a template. Every number inside it came
    from a pre-formatted snapshot field, so once the trigger is serialised into
    the snapshot the whole string is a substring of the JSON and the provenance
    test finds it there.
    """

    kind: str
    state: str
    severity: str
    detail: str

    @property
    def label(self) -> str:
        return TRIGGER_LABELS.get(self.kind, self.kind)

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "state": self.state,
            "severity": self.severity,
            "detail": self.detail,
            "label": self.label,
        }


def build_triggers(c: dict) -> list[Trigger]:
    """Every reason this contract is worth looking at, from one snapshot.

    The first three are mutually exclusive and that is deliberate. An unreliable
    burn makes the gap unusable, so a contract with an unusable gap does not
    also get told its gap crossed a threshold. Reporting both would rank a row
    the project's own rule says may be shown and never ranked.
    """
    r = c["runway"]
    gap = c.get("gap_months")
    gap_1f = c.get("gap_months_1f")
    nct = (c.get("trial") or {}).get("nct", "")
    against = f"{nct} ({c.get('catalyst_date')})"
    out: list[Trigger] = []

    if not r.get("reliable"):
        out.append(Trigger(
            RUNWAY_UNRELIABLE, UNAVAILABLE, "high",
            "; ".join(r.get("notes") or []) or "burn estimate is not usable",
        ))
    elif gap is not None and gap < 0:
        out.append(Trigger(
            FUNDING_THRESHOLD_CROSSED, DETERMINISTIC, "high",
            f"funding gap {gap_1f} months against {against}",
        ))
    elif gap is not None and gap < APPROACHING_MONTHS:
        out.append(Trigger(
            FUNDING_THRESHOLD_APPROACHING, WATCH, "medium",
            f"funding gap {gap_1f} months against {against}",
        ))

    # A lapsed registered completion is never a catalyst and never a funding
    # target. It is a date-integrity signal about the sponsor, so it gets its
    # own trigger rather than modifying the funding one.
    for lapsed in c.get("lapsed") or []:
        out.append(Trigger(
            REGISTERED_EXPECTATION_EXPIRED, DETERMINISTIC, "high",
            f"{lapsed['nct']} registered primary completion {lapsed['pcd']} "
            "has passed and was never amended",
        ))

    # Promise identity on the binding trial. These two are why the product can
    # say a date moved without claiming the sponsor is late: if the endpoint was
    # reworded or the enrolment changed, the two dates describe two different
    # commitments and the difference between them is not slip.
    hist = c.get("history") or {}
    n_contingent = hist.get("slip_contingent_revisions") or 0
    if n_contingent:
        out.append(Trigger(
            ENDPOINT_CONTINUITY, CONTINGENT, "medium",
            f"{n_contingent} {_revisions(n_contingent)} reworded the endpoint, so a "
            "date difference across them needs a human reading before it is slip",
        ))
    n_refused = hist.get("slip_refused_revisions") or 0
    if n_refused:
        out.append(Trigger(
            COMPARISON_REFUSED, CONTINGENT, "medium",
            f"{n_refused} {_revisions(n_refused)} changed enrolment or scope, so the "
            "reported movement across them is not treated as delay",
        ))

    return out


def _revisions(n: int) -> str:
    return "revision" if n == 1 else "revisions"


def evidence_state(triggers: list[Trigger]) -> str:
    """The single evidence state, by declared precedence.

    Secondary triggers are never discarded to produce this. The badge is the
    headline; `build_decision` keeps the whole list beside it.
    """
    forced = {_FORCES[t.state] for t in triggers}
    for state, _ in EVIDENCE_STATES:
        if state in forced:
            return state
    return INTACT


def worst_severity(triggers: list[Trigger]) -> str | None:
    if not triggers:
        return None
    return sorted(triggers, key=lambda t: SEVERITY_RANK[t.severity])[0].severity


def build_decision(c: dict) -> dict:
    """The evidence axis for one contract, ready to serialise into the snapshot.

    Counts are precomputed because the templates may not use `|length` or a
    comparison. That rule is what keeps every number on screen traceable to a
    field rather than to Jinja arithmetic.
    """
    triggers = build_triggers(c)
    state = evidence_state(triggers)
    severity = worst_severity(triggers)
    return {
        "evidence": state,
        "evidence_label": EVIDENCE_LABELS[state],
        "triggers": [t.as_dict() for t in triggers],
        "n_triggers": len(triggers),
        "severity": severity,
        "severity_rank": SEVERITY_RANK.get(severity, len(SEVERITY_RANK)),
        "evidence_rank": EVIDENCE_RANK[state],
        # Worst first: what needs a judgement today, then severity, then the
        # busiest row. Never the ticker, and never a hardcoded company.
        "sort_key": [INBOX_RANK[state],
                     SEVERITY_RANK.get(severity, len(SEVERITY_RANK)),
                     -len(triggers)],
    }
