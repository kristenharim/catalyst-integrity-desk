"""Flask app for the Catalyst Integrity Desk console.

Loads data/snapshot.json once at startup and serves three views:
  GET /                  redirects to /contract/RCKT (demo-opening constraint)
  GET /contracts         ranked contract list
  GET /contract/<ticker> contract detail with revision timeline
  GET /redline           pending challenge card
  POST /redline/decide   accept or reject; writes to data/decisions.jsonl
  GET /redline/confirm   confirmation page with ledger verify() badge

No computation in route handlers. They slice the snapshot and pass it to
render_template(). All arithmetic happened in make_snapshot.py.
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import time

# Ensure repo root is importable when this file is run directly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, redirect, render_template, request, url_for

from console import intake, review
from engine.ledger import BeliefCard, BeliefLedger, Breach
from evidence import FrozenSnapshotProvider, Incomplete
from orchestrator.anchor import check as anchor_check, record as anchor_record
from orchestrator.challenge import (
    ChallengeCard, Decision, ReviewLog, apply_decision, build_challenge,
    without_model_confidence,
)
from orchestrator.classifier import Classification

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(__file__)
_REPO = os.path.join(_HERE, "..")
SNAPSHOT_PATH = os.path.join(_REPO, "data", "snapshot.json")
DECISIONS_PATH = os.path.join(_REPO, "data", "decisions.jsonl")
REVIEW_LOG_PATH = os.path.join(_REPO, "data", "review_log.jsonl")
ANCHOR_PATH = os.path.join(_REPO, "data", "ledger.anchor")
EVIDENCE_DIR = os.path.join(_REPO, "data", "evidence")

# Workspace mode reads through the seam. The frozen provider is the default so a
# judge with no credentials walks the real flow rather than a mock of it;
# swapping in LiveSnapshotProvider changes the data source and nothing else,
# which is the entire argument for the seam existing.
EVIDENCE = FrozenSnapshotProvider(EVIDENCE_DIR)

# ---------------------------------------------------------------------------
# Load snapshot at startup
# ---------------------------------------------------------------------------

if not os.path.exists(SNAPSHOT_PATH):
    raise SystemExit(
        f"ERROR: {SNAPSHOT_PATH} not found.\n"
        "Run: python3 console/make_snapshot.py"
    )

with open(SNAPSHOT_PATH) as _f:
    SNAPSHOT: dict = json.load(_f)

# Content address of the artifact every computed state on screen came from.
# Named in the footer so a reader can tell which snapshot produced the numbers,
# and distinguish them from the human decisions, which are stored rather than
# computed.
SNAPSHOT_ID = review.snapshot_digest(SNAPSHOT_PATH)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = Flask(__name__, template_folder="templates")


# ---------------------------------------------------------------------------
# Context processor: inject snapshot_cmd_bar into every template.
# The command bar counts are precomputed in make_snapshot.py; the processor
# makes them available without passing them to every render_template call.
# ---------------------------------------------------------------------------

@app.context_processor
def inject_cmd_bar():
    return {"snapshot_cmd_bar": SNAPSHOT.get("cmd_bar"),
            "snapshot_id": SNAPSHOT_ID,
            "snapshot_as_of": SNAPSHOT.get("as_of")}


# ---------------------------------------------------------------------------
# Routes -- no arithmetic, only slicing
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    return redirect(url_for("contract_detail", ticker="RCKT"))


@app.get("/demo")
def demo():
    """The seeded scenario, reachable deterministically.

    The inbox becomes the default landing page, which is right for the product
    and wrong for a three-minute presentation: sorting is data-dependent, and a
    demo that depends on Rocket happening to sort first is one snapshot away
    from opening on the wrong company. This route does not care how the inbox
    sorts.
    """
    return redirect(url_for("contract_detail", ticker="RCKT"))


@app.get("/contracts")
def contract_list():
    contracts = SNAPSHOT["contracts"]
    reliable = []
    unreliable = []
    for ticker, c in contracts.items():
        if c["runway"]["reliable"]:
            reliable.append((ticker, c))
        else:
            unreliable.append((ticker, c))
    reliable.sort(key=lambda tc: tc[1]["gap_months"] if tc[1]["gap_months"] is not None else float("inf"))
    return render_template("contracts.html", reliable=reliable, unreliable=unreliable,
                           unresolved=SNAPSHOT.get("unresolved", []))


@app.get("/queue")
def queue_view():
    """This morning's work: one row per reason to look, worst first."""
    return render_template("queue.html", queue=SNAPSHOT.get("queue"))


@app.get("/contract/<ticker>")
def contract_detail(ticker):
    contracts = SNAPSHOT["contracts"]
    if ticker not in contracts:
        return f"Ticker {ticker!r} not in snapshot.", 404
    return render_template("detail.html", ticker=ticker, c=contracts[ticker])


@app.get("/redline")
def redline_view():
    redline = SNAPSHOT["redline"]
    # The contract the redline is about, so its derivation can be shown behind
    # the headline figure without keeping a second copy of it in the snapshot.
    contract = SNAPSHOT["contracts"].get(redline.get("ticker"))
    # The memo is the model's narrative and Python's figures in one string. The
    # figures stay; the model's own confidence does not, because no
    # model-produced number reaches the user.
    return render_template("redline.html", redline=redline, c=contract,
                           memo=without_model_confidence(redline["memo"]))


# ---------------------------------------------------------------------------
# Analyst belief entry: write a contract, review what the desk computed against
# it, then commit it to the ledger.  A challenge is judged against a belief a
# human wrote, so there has to be a way for a human to write one.  Writing one
# records it and nothing more: no rebuild reads the ledger.
# ---------------------------------------------------------------------------

# BeliefCard needs a numeric band and the analyst states a floor only ("the gap
# must not fall below X").  There is no upper bound on being well funded.
# ponytail: a sentinel, not math.  It is never displayed; the UI says
# "unbounded above".  Swap for a nullable expected_high if the ledger schema
# ever grows one.
_UNBOUNDED_ABOVE = 1.0e9


def _form_errors(form) -> tuple[list[str], dict]:
    """Validate the analyst form.  Returns (errors, cleaned fields).

    A trust boundary: everything here is user input and none of it is trusted
    to be well formed, present, or numeric.
    """
    errors: list[str] = []
    ticker = (form.get("ticker") or "").strip().upper()
    nct = (form.get("nct") or "").strip().upper()
    thesis = (form.get("thesis") or "").strip()
    invalidation = (form.get("invalidation") or "").strip()
    min_gap_raw = (form.get("min_gap") or "").strip()

    if ticker not in SNAPSHOT["contracts"]:
        errors.append(f"Ticker {ticker or '(blank)'} is not in this snapshot.")
    if not nct.startswith("NCT") or not nct[3:].isdigit():
        errors.append("Trial identifier must look like NCT06092034.")
    if len(thesis) < 20:
        errors.append("Write the thesis out. Granite reads this text; a stub is not a belief.")
    try:
        min_gap = float(min_gap_raw)
    except ValueError:
        errors.append("Minimum acceptable funding gap must be a number, in months.")
        min_gap = 0.0

    return errors, {
        "ticker": ticker, "nct": nct, "thesis": thesis,
        "invalidation": invalidation, "min_gap_raw": min_gap_raw, "min_gap": min_gap,
    }


def _card_from_form(f: dict) -> BeliefCard:
    """Build the BeliefCard the ledger will store.

    The invalidation conditions ride inside `claim` on purpose: `claim` is the
    text Granite is given as the analyst's rationale, and the conditions under
    which the analyst would abandon the thesis are exactly what a challenge has
    to be judged against.
    """
    c = SNAPSHOT["contracts"][f["ticker"]]
    claim = f["thesis"]
    if f["invalidation"]:
        claim = f"{claim}\n\nInvalidation conditions: {f['invalidation']}"
    return BeliefCard(
        card_id=f"{f['ticker'].lower()}:{f['nct'].lower()}",
        scope=f["nct"],
        claim=claim,
        metric="gap_months",
        expected_low=f["min_gap"],
        expected_high=_UNBOUNDED_ABOVE,
        driver=(f"SEC XBRL liquidity (filing as of {c['runway']['as_of']}) vs "
                f"ClinicalTrials.gov registered primary completion for {f['nct']}"),
        confidence=3,
        source="console.analyst_form",
        as_of=c["runway"]["as_of"],
    )


@app.get("/belief/new")
def belief_new():
    return render_template("belief_new.html", stage="form",
                           contracts=SNAPSHOT["contracts"], form={}, errors=[])


@app.post("/belief/new")
def belief_submit():
    stage = request.form.get("stage", "review")
    errors, f = _form_errors(request.form)
    if errors:
        return render_template("belief_new.html", stage="form",
                               contracts=SNAPSHOT["contracts"], form=f,
                               errors=errors), 400

    card = _card_from_form(f)
    contract = SNAPSHOT["contracts"][f["ticker"]]

    if stage != "commit":
        # Review: show the analyst what the desk computes against the belief
        # they just wrote, before anything is written down.
        return render_template("belief_new.html", stage="review",
                               contracts=SNAPSHOT["contracts"], form=f,
                               errors=[], card=card, c=contract)

    ledger = BeliefLedger(DECISIONS_PATH)
    try:
        entry = ledger.create(card, author="human:analyst")
    except ValueError:
        return render_template(
            "belief_new.html", stage="form", contracts=SNAPSHOT["contracts"],
            form=f, errors=[f"A belief for {f['ticker']} on {f['nct']} already exists "
                            "in the ledger. Retire it before writing a new one."]), 409
    anchor_record(ledger, anchor_path=ANCHOR_PATH)
    return render_template("belief_new.html", stage="done",
                           contracts=SNAPSHOT["contracts"], form=f, errors=[],
                           card=card, c=contract, entry=entry)


# ---------------------------------------------------------------------------
# Workspace mode: ticker in, recorded contract out.
#
# Four steps, two of them human. The machine resolves the company, reads the
# evidence and ranks the candidates; a human says which trial underwrites the
# thesis and whether the proposed contract is right. Neither is inferrable from
# a ticker, and guessing them is how a monitor ends up watching something nobody
# actually believes.
# ---------------------------------------------------------------------------

@app.get("/workspace")
def workspace_new():
    return render_template("workspace.html", stage="ticker",
                           available=EVIDENCE.available(), errors=[])


@app.post("/workspace/discover")
def workspace_discover():
    """Resolve the company and show what the evidence supports.

    Shows the negative results and the identity join BEFORE any candidate. A
    sponsor-name match nobody checked is the largest source of silent wrongness
    here, and if the wrong company's trials came back, nothing below that line
    means anything.
    """
    ticker = (request.form.get("ticker") or "").strip().upper()
    if not ticker:
        return render_template("workspace.html", stage="ticker",
                               available=EVIDENCE.available(),
                               errors=["Enter a ticker."]), 400
    try:
        snap = EVIDENCE.get(ticker)
    except Incomplete as exc:
        return render_template("workspace.html", stage="ticker",
                               available=EVIDENCE.available(),
                               errors=[str(exc)], form={"ticker": ticker}), 404

    return render_template(
        "workspace.html", stage="discover", available=EVIDENCE.available(),
        errors=[], form={"ticker": ticker},
        summary=intake.summary(snap), entity=intake.entity(snap),
        candidates=intake.candidates(snap),
    )


@app.post("/workspace/select")
def workspace_select():
    """The analyst has named the trial. Propose a contract against it."""
    ticker = (request.form.get("ticker") or "").strip().upper()
    nct = (request.form.get("nct") or "").strip().upper()
    try:
        snap = EVIDENCE.get(ticker)
    except Incomplete as exc:
        return render_template("workspace.html", stage="ticker",
                               available=EVIDENCE.available(),
                               errors=[str(exc)]), 404
    try:
        proposal = intake.propose(snap, nct)
    except ValueError as exc:
        # The commonest case is a lapsed date, refused at the intake layer so a
        # hand-posted form cannot bypass what the template merely declines to offer.
        return render_template(
            "workspace.html", stage="discover", available=EVIDENCE.available(),
            errors=[str(exc)], form={"ticker": ticker},
            summary=intake.summary(snap), entity=intake.entity(snap),
            candidates=intake.candidates(snap),
        ), 400

    return render_template(
        "workspace.html", stage="review", available=EVIDENCE.available(),
        errors=[], form={"ticker": ticker, "nct": nct},
        summary=intake.summary(snap), **proposal,
    )


@app.post("/workspace/approve")
def workspace_approve():
    """Write the analyst's belief into the hash-chained ledger."""
    ticker = (request.form.get("ticker") or "").strip().upper()
    nct = (request.form.get("nct") or "").strip().upper()
    claim = (request.form.get("claim") or "").strip()
    raw_gap = (request.form.get("min_gap") or "0").strip()

    try:
        min_gap = float(raw_gap)
    except ValueError:
        return "Minimum acceptable funding gap must be a number.", 400
    if len(claim) < 20:
        return "The claim must be written out; Granite reads this text.", 400

    try:
        snap = EVIDENCE.get(ticker)
        proposal = intake.propose(snap, nct, min_gap=min_gap)
    except (Incomplete, ValueError) as exc:
        return str(exc), 400

    # The analyst's edited wording wins. The proposal is a starting point, and a
    # belief the analyst did not write is not their belief -- it is also the
    # text Granite is later given as their rationale.
    card = proposal["card"]
    card.claim = claim
    card.expected_low = min_gap

    ledger = BeliefLedger(DECISIONS_PATH)
    try:
        entry = ledger.create(card, author="human:analyst")
    except ValueError:
        return render_template(
            "workspace.html", stage="review", available=EVIDENCE.available(),
            errors=[f"A belief for {ticker} on {nct} already exists in the "
                    f"ledger. Retire it before writing a new one."],
            form={"ticker": ticker, "nct": nct},
            summary=intake.summary(snap), **proposal), 409
    anchor_record(ledger, anchor_path=ANCHOR_PATH)

    return render_template(
        "workspace.html", stage="done", available=EVIDENCE.available(),
        errors=[], form={"ticker": ticker, "nct": nct},
        summary=intake.summary(snap), entry=entry, **proposal)


@app.post("/redline/decide")
def redline_decide():
    verdict = request.form.get("verdict", "")
    reason = request.form.get("reason", "")
    if verdict not in ("approve", "reject"):
        return "Invalid verdict.", 400

    snap_redline = SNAPSHOT["redline"]

    # Reconstruct the ChallengeCard from the snapshot.
    breach = Breach(
        card_id=snap_redline["breach"]["card_id"],
        metric=snap_redline["breach"]["metric"],
        observed=snap_redline["breach"]["observed"],
        expected_low=snap_redline["breach"]["expected_low"],
        expected_high=snap_redline["breach"]["expected_high"],
        direction=snap_redline["breach"]["direction"],
    )
    cls = Classification(
        label=snap_redline["classification"]["label"],
        confidence=snap_redline["classification"]["confidence"],
        rationale=snap_redline["classification"]["rationale"],
        source=snap_redline["classification"]["source"],
    )
    pc_raw = snap_redline["proposed_card"]
    proposed_card = BeliefCard(**pc_raw)
    challenge_card = ChallengeCard(
        card_id=snap_redline["card_id"],
        breach=breach,
        classification=cls,
        memo=snap_redline["memo"],
        proposed_card=proposed_card,
    )

    decision = Decision(
        verdict=verdict,
        author="human:demo",
        reason=reason,
    )

    ledger = BeliefLedger(DECISIONS_PATH)
    review_log = ReviewLog(REVIEW_LOG_PATH)

    # Approve path: ledger needs the card to already exist.
    if verdict == "approve":
        current = ledger.current()
        if challenge_card.card_id not in current:
            # Seed the ledger with the original approved card so update() can bump it.
            original_card = BeliefCard(
                card_id=pc_raw["card_id"],
                scope=pc_raw["scope"],
                claim=pc_raw["claim"],
                metric=pc_raw["metric"],
                expected_low=snap_redline["breach"]["expected_low"],
                expected_high=snap_redline["breach"]["expected_high"],
                driver=pc_raw["driver"],
                confidence=pc_raw["confidence"],
                source=pc_raw["source"],
                as_of=pc_raw["as_of"],
            )
            ledger.create(original_card, author="snapshot:seed", ts=0.0)

    entry = apply_decision(ledger, review_log, challenge_card, decision)

    # Record the anchor after every successful approve so deletion is detectable.
    if verdict == "approve":
        anchor_record(ledger, anchor_path=ANCHOR_PATH)

    # Redirect with verdict only.  The confirm handler reads the receipt from
    # the ledger at render time so no receipt data travels in the URL.
    return redirect(url_for("redline_confirm", verdict=verdict))


@app.get("/redline/confirm")
def redline_confirm():
    verdict = request.args.get("verdict", "")

    # Check the ledger fresh at render time via the anchor so all three states
    # are detectable: intact, tampered (hash fails), truncated (anchor mismatch).
    ledger = BeliefLedger(DECISIONS_PATH)
    integrity_status = anchor_check(ledger, anchor_path=ANCHOR_PATH)

    # Build receipt from the ledger's last entry at render time.
    # Nothing from the URL contributes to the receipt -- a URL-carried receipt
    # is not evidence of anything and must not be displayed as if it were.
    #
    # Selected by card_id, not by whichever entry happens to be last. Record a
    # belief through /belief/new after an approval and the ledger's last entry is
    # that belief, so the receipt rendered a different card's hashes underneath
    # this redline's summary of what changed.
    receipt = None
    snap_redline = SNAPSHOT.get("redline", {})
    redline_card_id = snap_redline.get("card_id")
    mine = [e for e in ledger._entries()
            if e.get("card", {}).get("card_id") == redline_card_id]
    last = mine[-1] if mine else None
    if last and verdict == "approve":
        proposed_card = last.get("card", {})
        expected_low = proposed_card.get("expected_low", 0)
        thesis_state = (
            "funded to catalyst" if expected_low >= 0
            else "financing required before catalyst"
        )
        ts_display = datetime.datetime.fromtimestamp(last["ts"]).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
        breach_metric = ""
        classification_label = ""
        if snap_redline:
            breach_metric = snap_redline.get("breach", {}).get("metric", "")
            classification_label = snap_redline.get("classification", {}).get("label", "")
        what_changed = (breach_metric + ": " + classification_label).strip(": ")
        receipt = {
            "author": last["author"],
            "ts_display": ts_display,
            "card_id": proposed_card.get("card_id", ""),
            "what_changed": what_changed,
            "thesis_state": thesis_state,
            "prev_hash": last["prev_hash"],
            "entry_hash": last["entry_hash"],
        }

    return render_template("confirm.html", verdict=verdict,
                           integrity_status=integrity_status, receipt=receipt)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(debug=False, port=port)
