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

import json
import os
import time

from flask import Flask, redirect, render_template, request, url_for

from engine.ledger import BeliefCard, BeliefLedger, Breach
from orchestrator.challenge import (
    ChallengeCard, Decision, ReviewLog, apply_decision, build_challenge,
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

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = Flask(__name__, template_folder="templates")


# ---------------------------------------------------------------------------
# Routes — no arithmetic, only slicing
# ---------------------------------------------------------------------------

@app.get("/")
def index():
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
    return render_template("contracts.html", reliable=reliable, unreliable=unreliable)


@app.get("/contract/<ticker>")
def contract_detail(ticker):
    contracts = SNAPSHOT["contracts"]
    if ticker not in contracts:
        return f"Ticker {ticker!r} not in snapshot.", 404
    return render_template("detail.html", ticker=ticker, c=contracts[ticker])


@app.get("/redline")
def redline_view():
    return render_template("redline.html", redline=SNAPSHOT["redline"])


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

    apply_decision(ledger, review_log, challenge_card, decision)

    return redirect(url_for("redline_confirm", verdict=verdict))


@app.get("/redline/confirm")
def redline_confirm():
    verdict = request.args.get("verdict", "")
    # Read the ledger fresh at render time so a tampered file shows "tampered"
    # even after a reload.  The query-string intact param is dropped: it was set
    # once at decision time and could not detect a post-decision tamper.
    ledger = BeliefLedger(DECISIONS_PATH)
    intact = ledger.verify()
    return render_template("confirm.html", verdict=verdict, intact=intact)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(debug=False, port=port)
