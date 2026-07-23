"""A receipt must name the decision it is a receipt for.

`redline_confirm` built its receipt from the ledger's last entry. That is right
exactly while the redline approval is the last thing anyone did. Record a belief
through `/belief/new` afterwards and the last entry is that belief, so the page
rendered a different card's hashes underneath the redline's summary of what
changed: a receipt for one decision carrying the identity of another.

Nothing from the URL contributes to the receipt, which was already true and is
kept. The fix is to select the entry by card id rather than by recency.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from console.app import app as flask_app

REPO = Path(__file__).resolve().parents[1]
THESIS = ("Rocket Pharmaceuticals reaches the registered primary completion of "
          "NCT06092034 before its runway is exhausted, with a non-negative gap.")


def _client(tmp_path, monkeypatch):
    monkeypatch.setattr("console.app.DECISIONS_PATH", str(tmp_path / "decisions.jsonl"))
    monkeypatch.setattr("console.app.REVIEW_LOG_PATH", str(tmp_path / "review_log.jsonl"))
    monkeypatch.setattr("console.app.ANCHOR_PATH", str(tmp_path / "ledger.anchor"))
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


def _redline_card_id() -> str:
    snap = json.loads((REPO / "data" / "snapshot.json").read_text())
    return snap["redline"]["card_id"]


def test_receipt_still_names_the_redline_after_a_later_belief(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    redline_id = _redline_card_id()

    c.post("/redline/decide", data={"verdict": "approve", "reason": "the date lapsed"})
    # An unrelated write lands after the decision, which is ordinary use.
    c.post("/belief/new", data={
        "stage": "commit", "ticker": "RCKT", "nct": "NCT06092034",
        "thesis": THESIS, "invalidation": "the gap falls below zero",
        "min_gap": "0"})

    body = c.get("/redline/confirm?verdict=approve").data.decode()

    assert redline_id in body, "the receipt no longer names the decision it is for"
    assert "rckt:nct06092034" not in body, (
        "the receipt is showing the later belief's identity"
    )


def test_receipt_hashes_belong_to_the_redline_entry(tmp_path, monkeypatch):
    """The hashes are the receipt. Showing another entry's pair is the defect."""
    c = _client(tmp_path, monkeypatch)
    redline_id = _redline_card_id()

    c.post("/redline/decide", data={"verdict": "approve", "reason": "the date lapsed"})
    c.post("/belief/new", data={
        "stage": "commit", "ticker": "RCKT", "nct": "NCT06092034",
        "thesis": THESIS, "invalidation": "", "min_gap": "0"})

    entries = [json.loads(l) for l in open(tmp_path / "decisions.jsonl") if l.strip()]
    redline_entries = [e for e in entries if e["card"]["card_id"] == redline_id]
    other = [e for e in entries if e["card"]["card_id"] != redline_id]
    assert redline_entries and other, "the fixture did not produce both writes"

    body = c.get("/redline/confirm?verdict=approve").data.decode()
    assert redline_entries[-1]["entry_hash"] in body
    for e in other:
        assert e["entry_hash"] not in body, "an unrelated entry's hash is on the receipt"


def test_the_receipt_still_reads_the_ledger_rather_than_the_url(tmp_path, monkeypatch):
    """The property that was already right, kept while the selection changed."""
    c = _client(tmp_path, monkeypatch)
    body = c.get("/redline/confirm?verdict=approve").data.decode()
    # No decision has been made, so there is no receipt to show.
    assert _redline_card_id() not in body
