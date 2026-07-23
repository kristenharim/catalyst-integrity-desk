"""Workflow state and record integrity: the two axes that are not in the snapshot.

console/states.py computes the evidence axis from the snapshot alone. These two
cannot be, because both depend on files that change long after the snapshot was
built: the belief ledger and its anchor.

Keeping them apart is not tidiness. A decision's evidence state is a statement
about public records, its workflow state is a statement about what a human did,
and its record state is a statement about whether the history of those human
actions is still intact. They fail independently and they have to be able to
say so, which is why states.py cannot import the ledger and why nothing here
feeds back into the evidence state.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field

from orchestrator.anchor import check as anchor_check

# ---------------------------------------------------------------------------
# Workflow states
# ---------------------------------------------------------------------------
# The full vocabulary is declared, but only four of these are computable today.
#
# `in_review` and `deferred` describe a human having picked a task up or pushed
# it out, and nothing in this repo stores either fact. They are named here so
# the templates and tests share one vocabulary, and they are never returned by
# `workflow_state`. Inventing them from a snapshot would be fabricating a
# workflow that does not exist, which is the same failure as inventing a number.

UNRECORDED = "unrecorded"
OPEN = "open"
IN_REVIEW = "in_review"
DEFERRED = "deferred"
RESOLVED = "resolved"
RETIRED = "retired"

WORKFLOW_STATES = [
    (UNRECORDED, "no belief recorded"),
    (OPEN, "open"),
    (IN_REVIEW, "in review"),
    (DEFERRED, "deferred"),
    (RESOLVED, "resolved"),
    (RETIRED, "retired"),
]
WORKFLOW_LABELS = dict(WORKFLOW_STATES)

# States this module can actually derive. Anything outside it is vocabulary
# waiting for a store.
COMPUTABLE = {UNRECORDED, OPEN, RESOLVED, RETIRED}

# ---------------------------------------------------------------------------
# Record integrity
# ---------------------------------------------------------------------------
# Exactly the three strings orchestrator.anchor.check can return, and no more.
#
# A fourth state for "the anchor file is missing" would read well and cannot be
# reported: check() folds a missing anchor into "truncated" on purpose, because
# a decision history with no anchor beside it is not distinguishable from one
# whose anchor was removed. Naming a state the infrastructure cannot detect
# would put a label on screen with nothing behind it.

RECORD_INTACT = "intact"
RECORD_TAMPERED = "tampered"
RECORD_TRUNCATED = "truncated"

RECORD_LABELS = {
    RECORD_INTACT: "record intact",
    RECORD_TAMPERED: "record tampered",
    RECORD_TRUNCATED: "record truncated or replaced",
}


def record_integrity(ledger, anchor_path: str) -> dict:
    """The third axis, read fresh from the ledger at render time.

    `failed` is precomputed so a template can keep this quiet until it matters
    without doing a comparison of its own.
    """
    state = anchor_check(ledger, anchor_path=anchor_path)
    return {
        "state": state,
        "label": RECORD_LABELS.get(state, state),
        "failed": state != RECORD_INTACT,
    }


# ---------------------------------------------------------------------------
# Review tasks
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReviewTask:
    """One decision that needs a human, projected rather than stored.

    `opened_at` is None and stays None. A task opens when a trigger first fires,
    and knowing that would take two snapshots to compare; there is only ever
    one. `resolved_at` is real, because a resolution is a ledger or review-log
    record with a timestamp on it.
    """

    task_id: str
    ticker: str
    card_id: str | None
    baseline_version: int | None
    current_snapshot_id: str
    trigger_kinds: list[str] = field(default_factory=list)
    state: str = OPEN
    opened_at: float | None = None
    resolved_at: float | None = None
    decision_entry_id: str | None = None

    @property
    def label(self) -> str:
        return WORKFLOW_LABELS.get(self.state, self.state)

    @property
    def recorded(self) -> bool:
        return self.card_id is not None

    def as_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "ticker": self.ticker,
            "card_id": self.card_id,
            "baseline_version": self.baseline_version,
            "current_snapshot_id": self.current_snapshot_id,
            "trigger_kinds": list(self.trigger_kinds),
            "state": self.state,
            "label": self.label,
            "recorded": self.recorded,
            "opened_at": self.opened_at,
            "resolved_at": self.resolved_at,
            "decision_entry_id": self.decision_entry_id,
        }


def card_ticker(card_id: str) -> str:
    """The ticker a card_id belongs to.

    Two conventions exist in the ledger: "rckt:funded_to_catalyst" from the
    seeded demo card and "rckt:nct04248439" from the analyst form. Both put the
    ticker first, which is also how apply_displays already derives the redline's
    ticker, so reading the prefix works for each without a lookup table.
    """
    return card_id.split(":")[0].upper()


def _latest_cards(entries: list[dict]) -> dict[str, dict]:
    """card_id -> its most recent card payload, retired ones included.

    `BeliefLedger.current()` drops retired cards, which is right for asking what
    is believed and wrong for asking what state a decision is in. A retired
    decision still has a workflow state and still belongs on the portfolio.
    """
    latest: dict[str, dict] = {}
    for e in entries:
        latest[e["card"]["card_id"]] = e["card"]
    return latest


def _resolution(entries: list[dict], rejects: list[dict], card_id: str):
    """The most recent human ruling on this card, from either store.

    An approval bumps the ledger. A rejection touches only the review log and
    leaves the belief standing. Reading just the ledger would leave every
    rejected review sitting open forever, so both are folded here.
    """
    approved = [
        e for e in entries
        if e["card"]["card_id"] == card_id
        and e.get("event") == "UPDATE"
        and (e.get("triggered_by") or "").startswith("breach:")
    ]
    rejected = [
        r for r in rejects
        if r.get("card_id") == card_id and r.get("verdict") == "reject"
    ]
    last_approved = approved[-1] if approved else None
    last_rejected = rejected[-1] if rejected else None

    if last_approved and last_rejected:
        if (last_rejected.get("ts") or 0) > (last_approved.get("ts") or 0):
            last_approved = None
        else:
            last_rejected = None

    if last_approved:
        return last_approved.get("ts"), last_approved.get("entry_hash")
    if last_rejected:
        # A rejection has no ledger entry to point at, and saying so is more
        # honest than pointing at the nearest one.
        return last_rejected.get("ts"), None
    return None, None


def workflow_state(card: dict | None, resolved_at) -> str:
    if card is None:
        return UNRECORDED
    if card.get("status") == "retired":
        return RETIRED
    if resolved_at is not None:
        return RESOLVED
    return OPEN


def build_tasks(snapshot: dict, ledger, review_log, snapshot_id: str) -> list[dict]:
    """One review task per decision, worst first.

    One task per decision, never one per trigger. Rocket is a single row
    carrying three reasons, because three reasons to look at one belief is one
    piece of work, and splitting it into three rows turns a decision queue back
    into an alert feed.
    """
    entries = ledger._entries()
    rejects = review_log.all()
    latest = _latest_cards(entries)

    by_ticker: dict[str, str] = {}
    for card_id in latest:
        by_ticker.setdefault(card_ticker(card_id), card_id)

    tasks = []
    for ticker, c in (snapshot.get("contracts") or {}).items():
        d = c.get("decision") or {}
        triggers = d.get("triggers") or []
        if not triggers:
            continue

        card_id = by_ticker.get(ticker)
        card = latest.get(card_id) if card_id else None
        resolved_at, entry_hash = (
            _resolution(entries, rejects, card_id) if card_id else (None, None)
        )
        state = workflow_state(card, resolved_at)

        task = ReviewTask(
            task_id=f"{ticker}:{snapshot_id[:12]}",
            ticker=ticker,
            card_id=card_id,
            baseline_version=card.get("version") if card else None,
            current_snapshot_id=snapshot_id,
            trigger_kinds=[t["kind"] for t in triggers],
            state=state,
            resolved_at=resolved_at,
            decision_entry_id=entry_hash,
        )
        tasks.append({
            "task": task.as_dict(),
            "ticker": ticker,
            "name": c["runway"]["name"],
            "decision": d,
            "gap_1f": c.get("gap_months_1f") if c["runway"].get("reliable") else None,
            "sort_key": d.get("sort_key") or [],
        })

    tasks.sort(key=lambda t: (t["sort_key"], t["ticker"]))
    return tasks


def open_tasks(tasks: list[dict]) -> list[dict]:
    return [t for t in tasks if t["task"]["state"] in (OPEN, UNRECORDED)]


def snapshot_digest(path: str) -> str:
    """Content address for the snapshot the states were computed from.

    The footer names this so a reader can tell which artifact produced the
    numbers on screen. Hashing the bytes rather than the parsed dict means the
    id changes when the file changes, which is the only property needed.
    """
    if not os.path.exists(path):
        return "unavailable"
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()
