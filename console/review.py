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

`registry_reconciliation` joined them for a different reason. It reads only the
snapshot, so it could have been a stored field, and it was one: a hardcoded
`no_amendment_filed: True`. A date-integrity claim whose truth value is typed
rather than read is a caption, not a finding, and it is computed here so that
moving the evidence moves the sentence.
"""
from __future__ import annotations

import datetime
import hashlib
import os
from dataclasses import dataclass, field

from engine.ctgov_history import _parse_date
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

# Ledger events, in the words a reader gets. A belief written here is recorded
# and nothing rereads it, so the label says recorded and never monitored.
EVENT_LABELS = {
    "CREATE": "belief recorded",
    "UPDATE": "belief revised",
    "RETIRE": "belief retired",
}

# The one human action that is not a ledger event. A rejection leaves the belief
# standing and writes to the review log, so it has no entry, no hash and no
# receipt. It is still something a human did to a decision, and a history that
# read only the ledger would report one in which nobody ever declined anything.
REJECTED_LABEL = "challenge rejected, belief stands"
REVIEWED_LABEL = "challenge reviewed"

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
# Registry reconciliation
# ---------------------------------------------------------------------------
# Whether any registry version moved a registered expectation before that
# expectation's own date arrived. The centre column of /redline says so, and
# until now it said so on the authority of a literal in the snapshot builder:
# deleting the literal deleted the sentence while the version history behind it
# sat unchanged, which is the wrong way round.
#
# The state names are the claim. `no_amendment_filed` named a fact about the
# world that a registry diff cannot reach, because an amendment can be filed
# with a regulator, a wire, or an investor deck without any registry version
# moving. What is actually proved is narrower and is now what it is called.

NO_LATER_VERSION = "no_later_registry_version_before_expiry"
RECONCILED_BEFORE_EXPIRY = "reconciled_before_expiry"
RECONCILIATION_UNKNOWN = "unknown"


def _stored_history(contract: dict, nct: str) -> dict | None:
    """The committed version history for one trial, binding or lapsed.

    A lapsed trial's history lives in `lapsed_history`, which is where the trial
    a redline is anchored to will be by the time the redline exists.
    """
    for h in [contract.get("history"), *(contract.get("lapsed_history") or [])]:
        if h and h.get("nct") == nct:
            return h
    return None


def registry_reconciliation(redline: dict, contract: dict, as_of: str) -> dict:
    """Did a registry version move this expectation before its date arrived?

    Read from the committed version history of `redline["prior_trial"]` and the
    snapshot's own `as_of`. Three outcomes, of which only one is an assertion:

      NO_LATER_VERSION          the date passed, and no stored version submitted
                                before it moved it
      RECONCILED_BEFORE_EXPIRY  a stored version moved it while it was still ahead
      RECONCILIATION_UNKNOWN    the committed history cannot answer

    Every gap in the evidence returns unknown rather than folding into an answer.
    Absence of a later version in a frozen artifact has two causes -- none was
    filed, or the artifact does not hold them all -- and they are not separable
    from inside the artifact. Only one of them supports the claim, so the pair
    has to be refused rather than resolved by default.

    What this establishes is bounded by the registry and by `as_of`. It says
    nothing about press releases, SEC filings, correspondence, or what anyone
    knew, and it cannot: none of those were queried.
    """
    nct = (redline or {}).get("prior_trial")
    pcd = (redline or {}).get("prior_pcd")
    out = {
        "state": RECONCILIATION_UNKNOWN,
        "trial": nct,
        "expectation": pcd,
        "as_of": as_of,
        "why": "no registry-version history for this trial is stored here",
    }

    history = _stored_history(contract or {}, nct) if nct else None
    revisions = (history or {}).get("revisions") or []
    if not revisions or not pcd or not as_of:
        return out

    # Every registry version the fetch saw has to be stored, or the question
    # stays open: a version this snapshot never kept cannot be shown not to have
    # moved the date.
    if history.get("n_versions") != len(revisions):
        out["why"] = "the stored history does not cover every registry version"
        return out

    setters = [i for i, r in enumerate(revisions) if r.get("pcd") == pcd]
    if not setters:
        out["why"] = "no stored version sets the expectation this claim is about"
        return out
    later = revisions[setters[-1] + 1:]

    if later:
        # The engine already computes this shape and the snapshot already carries
        # it. `carried_expired` on the version that replaced a date means the
        # date had already passed when it was replaced, so its negation is a
        # reconciliation inside the window, which is the whole question.
        out["state"] = (NO_LATER_VERSION if later[0].get("carried_expired")
                        else RECONCILED_BEFORE_EXPIRY)
        return out

    # Nothing later is stored, so the snapshot's own as_of stands in for the next
    # submission date, and the claim is bounded at the day the artifact froze.
    expected, frozen = _parse_date(pcd), _parse_date(as_of)
    if expected is None or frozen is None:
        out["why"] = "the stored dates cannot be read"
    elif expected < frozen:
        out["state"] = NO_LATER_VERSION
        out["why"] = ""
    else:
        out["why"] = "the expectation had not passed when this snapshot was taken"
    return out


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


def _cards_by_ticker(latest: dict[str, dict]) -> dict[str, str]:
    """ticker -> the first card_id recorded for it."""
    by_ticker: dict[str, str] = {}
    for card_id in latest:
        by_ticker.setdefault(card_ticker(card_id), card_id)
    return by_ticker


def _task_row(ticker: str, c: dict, entries: list[dict], rejects: list[dict],
              latest: dict[str, dict], by_ticker: dict[str, str],
              snapshot_id: str) -> dict:
    """One decision, projected: its evidence, its workflow state, its gap.

    Split out of `build_tasks` so one decision can be looked up without going
    through the inbox's filter. The inbox skips a contract carrying no trigger,
    which is right for a work queue and wrong for a page addressed by the
    decision's own id: a contract nobody needs to look at still has a state, and
    a review screen that 404s on it would be reporting that it has none.
    """
    d = c.get("decision") or {}
    card_id = by_ticker.get(ticker)
    card = latest.get(card_id) if card_id else None
    resolved_at, entry_hash = (
        _resolution(entries, rejects, card_id) if card_id else (None, None)
    )
    task = ReviewTask(
        task_id=f"{ticker}:{snapshot_id[:12]}",
        ticker=ticker,
        card_id=card_id,
        baseline_version=card.get("version") if card else None,
        current_snapshot_id=snapshot_id,
        trigger_kinds=[t["kind"] for t in (d.get("triggers") or [])],
        state=workflow_state(card, resolved_at),
        resolved_at=resolved_at,
        decision_entry_id=entry_hash,
    )
    return {
        "task": task.as_dict(),
        "ticker": ticker,
        "name": c["runway"]["name"],
        "decision": d,
        "gap_1f": c.get("gap_months_1f") if c["runway"].get("reliable") else None,
        "sort_key": d.get("sort_key") or [],
    }


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
    by_ticker = _cards_by_ticker(latest)

    tasks = [
        _task_row(ticker, c, entries, rejects, latest, by_ticker, snapshot_id)
        for ticker, c in (snapshot.get("contracts") or {}).items()
        if (c.get("decision") or {}).get("triggers")
    ]
    tasks.sort(key=lambda t: (t["sort_key"], t["ticker"]))
    return tasks


def open_tasks(tasks: list[dict]) -> list[dict]:
    return [t for t in tasks if t["task"]["state"] in (OPEN, UNRECORDED)]


def decision_id_for(ticker: str, redline: dict) -> str:
    """How one decision is addressed in a URL.

    The recorded card's id when a challenge names one, and the ticker when
    nothing does. Exactly one challenge exists and it is written in Python
    inside `make_snapshot.py`, so every other decision has no card id to carry;
    minting one would put an identifier on screen that names no record. Both
    shapes read back through `card_ticker`, which is why they can share a route.
    """
    return (redline.get("card_id") or ticker
            if redline.get("ticker") == ticker else ticker)


def _action(row: dict, redline: dict) -> dict:
    """The one primary action for an inbox item, and only the backed one.

    Adjudicating needs a challenge: a breach scanned against a recorded belief,
    a memo about it, and a form that writes the ruling to the ledger. Exactly
    one exists, written in Python inside `make_snapshot.py`, and no rebuild
    reads the ledger, so no other row has a challenge to rule on. Offering
    "Adjudicate" on those would put a button on screen with nothing behind it,
    so they open the same review screen with the evidence only. See
    docs/plans/phase2-inbox-spec.md section 8.

    Both labels now lead to `/decisions/<card_id>/review`, which is the
    adjudication surface for the one challenge and the evidence surface for
    everything else. `/redline` is unchanged and still serves the challenge.
    """
    href = f"/decisions/{decision_id_for(row['ticker'], redline)}/review"
    if redline.get("ticker") == row["ticker"]:
        return {"label": "Adjudicate", "href": href}
    return {"label": "Review evidence", "href": href}


def decision_review(snapshot: dict, card_id: str, ledger, review_log,
                    snapshot_id: str, anchor_path: str) -> dict | None:
    """Everything the decision review screen renders for one decision.

    `card_id` is the recorded card's id where one exists and the ticker where
    none does; see `decision_id_for`. `card_ticker` reads both, so the route
    resolves either without a lookup table. An id naming no contract in this
    snapshot returns None, which the route renders as a miss rather than
    guessing at the nearest decision.

    The three axes come back as three keys and are never combined into a fourth.
    `decision.evidence` is what the public record says, `task.state` is what a
    human has done about it, `record` is whether the history of those human
    actions still agrees with its anchor. A page that merged them could render a
    tampered ledger as a broken thesis, which is the failure the split exists to
    prevent.
    """
    ticker = card_ticker(card_id)
    c = (snapshot.get("contracts") or {}).get(ticker)
    if c is None:
        return None

    entries = ledger._entries()
    latest = _latest_cards(entries)
    row = _task_row(ticker, c, entries, review_log.all(), latest,
                    _cards_by_ticker(latest), snapshot_id)

    # Adjudication is offered only where a challenge exists to adjudicate. The
    # snapshot carries one, keyed by its own card id, and matching on that id
    # rather than on the ticker means a second decision recorded against the
    # same company cannot inherit the form.
    redline = snapshot.get("redline") or {}
    adjudicable = bool(redline.get("card_id")) and redline["card_id"] == card_id

    return {
        **row,
        "decision_id": card_id,
        "c": c,
        "record": record_integrity(ledger, anchor_path),
        "adjudicable": adjudicable,
        "redline": redline if adjudicable else None,
        "reconciliation": (registry_reconciliation(redline, c, snapshot.get("as_of"))
                           if adjudicable else None),
    }


def inbox_rows(snapshot: dict, ledger, review_log, snapshot_id: str) -> list[dict]:
    """Open decisions, worst first, each carrying its single primary action.

    The route slices this and renders it. Which action an item gets depends on
    what the backend can do about that item, which is a question for this module
    rather than for a template.
    """
    rows = open_tasks(build_tasks(snapshot, ledger, review_log, snapshot_id))
    redline = snapshot.get("redline") or {}
    return [{**r, "action": _action(r, redline)} for r in rows]


# ---------------------------------------------------------------------------
# Activity: the decision history
# ---------------------------------------------------------------------------


def ts_display(ts) -> str:
    """One timestamp rendering, so two pages cannot date the same entry
    differently.

    `console/app.py::_receipt` formatted the ledger's epoch seconds inline and
    the activity screen lists the same entries, so the format is shared rather
    than copied.

    The conversion is to UTC, which is what the label has always said and not
    what the code did: `fromtimestamp` with no timezone reads the machine's
    local clock, so the receipt has been stamping local wall time with a UTC
    suffix. On a page whose subject is the order events happened in, a timestamp
    that names the wrong zone is the field a reader would use to check the
    order. Fixed here rather than beside it, because both pages read this.
    """
    if ts is None:
        return "unavailable"
    return datetime.datetime.fromtimestamp(
        ts, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def activity_rows(ledger, review_log, tickers) -> list[dict]:
    """Every recorded decision event, in the order the record holds them.

    What decisions were recorded, reviewed, changed or retired, and in what
    order. That is the whole question, and the answer comes from the two stores
    a human ruling can land in: the hash-chained ledger, and the review log a
    rejection writes to instead.

    Nothing here is derived from the snapshot. The snapshot carries exactly one
    challenge and it is written in Python inside `make_snapshot.py`; it is a
    computed state rather than something anybody did, so putting it on this page
    would fabricate a decision. `tickers` is read for one purpose only, which is
    whether a review link would resolve to a contract this snapshot holds.

    Ordering is the record's own. Ledger entries come back in `seq` order and
    the sort is stable, so two entries sharing a timestamp keep the order the
    chain links them in rather than an arbitrary one.
    """
    rows: list[dict] = []

    for e in ledger._entries():
        card = e.get("card") or {}
        card_id = card.get("card_id") or ""
        rows.append({
            "source": "ledger",
            "ts": e.get("ts") or 0.0,
            "ts_display": ts_display(e.get("ts")),
            "event": e.get("event") or "",
            "action": EVENT_LABELS.get(e.get("event") or ""),
            "card_id": card_id,
            "ticker": card_ticker(card_id) if card_id else "",
            "version": card.get("version"),
            "author": e.get("author") or "",
            "reason": e.get("reason") or "",
            "triggered_by": e.get("triggered_by") or "",
            "entry_hash": e.get("entry_hash") or "",
            "prev_hash": e.get("prev_hash") or "",
        })

    for r in review_log.all():
        card_id = r.get("card_id") or ""
        rows.append({
            "source": "review_log",
            "ts": r.get("ts") or 0.0,
            "ts_display": ts_display(r.get("ts")),
            "event": "",
            "action": (REJECTED_LABEL if r.get("verdict") == "reject"
                       else REVIEWED_LABEL),
            "card_id": card_id,
            "ticker": card_ticker(card_id) if card_id else "",
            # A rejection bumps nothing and hashes nothing. Both are stated on
            # the page as absent for a reason rather than left blank.
            "version": None,
            "author": r.get("author") or "",
            "reason": r.get("reason") or "",
            "triggered_by": "",
            "entry_hash": "",
            "prev_hash": "",
        })

    rows.sort(key=lambda r: r["ts"])
    for r in rows:
        # The receipt is addressed by this row's own entry hash, never by the
        # ledger's latest entry: a later unrelated write must not move a link on
        # a history page any more than it may move one on the receipt itself.
        r["receipt_href"] = f"/receipts/{r['entry_hash']}" if r["entry_hash"] else None
        r["review_href"] = (f"/decisions/{r['card_id']}/review"
                            if r["ticker"] in tickers else None)
    return rows


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
