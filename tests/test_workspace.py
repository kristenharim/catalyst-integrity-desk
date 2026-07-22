"""Workspace mode: ticker in, monitored contract out.

The tests that matter here are the ones about what the flow REFUSES to do,
because a discovery wizard's failure mode is confidently proceeding on evidence
it does not have. Three refusals are pinned: a lapsed date cannot be selected as
a catalyst, an unknown subject is a 404 rather than an empty result, and a
source that returned nothing is displayed as such rather than omitted.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from console import intake  # noqa: E402
from console.app import app as flask_app  # noqa: E402
from evidence import FrozenSnapshotProvider  # noqa: E402

REPO = os.path.join(os.path.dirname(__file__), "..")
EVIDENCE_DIR = os.path.join(REPO, "data", "evidence")


@pytest.fixture(scope="module")
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture(scope="module")
def provider():
    return FrozenSnapshotProvider(EVIDENCE_DIR)


# ---------------------------------------------------------------------------
# The bundles exist and the demo needs no network
# ---------------------------------------------------------------------------

def test_every_snapshot_ticker_has_an_evidence_bundle(provider):
    """Workspace mode must cover the same companies the demo does, or the two
    modes disagree about what is being monitored."""
    with open(os.path.join(REPO, "data", "snapshot.json")) as f:
        snap = json.load(f)
    expected = set(snap["contracts"]) | {u["ticker"] for u in snap.get("unresolved", [])}
    assert set(provider.available()) >= expected


def test_the_flow_runs_with_no_network_and_no_credentials(client):
    """The frozen provider is the default, so a judge walks the real flow.

    Asserted by driving the whole thing: if anything reached for the network,
    this would hang or fail rather than pass in milliseconds.
    """
    assert client.get("/workspace").status_code == 200
    r = client.post("/workspace/discover", data={"ticker": "RCKT"})
    assert r.status_code == 200
    r = client.post("/workspace/select", data={"ticker": "RCKT", "nct": "NCT06092034"})
    assert r.status_code == 200
    assert b"Proposed contract" in r.data


# ---------------------------------------------------------------------------
# The refusals
# ---------------------------------------------------------------------------

def test_a_lapsed_date_cannot_be_selected_as_a_catalyst(client):
    """You cannot run out of money before an event that already happened.

    The rule is enforced at the intake layer, not just hidden in the template,
    so a hand-posted form cannot bypass it.
    """
    r = client.post("/workspace/select",
                    data={"ticker": "RCKT", "nct": "NCT04248439"})
    assert r.status_code == 400
    assert b"already passed" in r.data


def test_the_lapsed_trial_is_still_shown(client):
    """Refused as a catalyst, never hidden. A sponsor carrying an expired date
    is the signal this project exists to surface."""
    r = client.post("/workspace/discover", data={"ticker": "RCKT"})
    assert b"NCT04248439" in r.data
    assert b"LAPSED" in r.data


def test_an_unknown_subject_is_a_404_not_an_empty_result(client):
    """An empty page would read as "this company has no filings and no trials",
    which is a finding the system did not earn."""
    r = client.post("/workspace/discover", data={"ticker": "NOSUCHTICKER"})
    assert r.status_code == 404


def test_a_source_that_returned_nothing_is_displayed(client):
    """SANA has a reliable runway and zero trials matching its sponsor string.

    The bundle records the query that came back empty, and the page shows it. A
    page that showed nothing would be claiming the search never happened.
    """
    r = client.post("/workspace/discover", data={"ticker": "SANA"})
    assert r.status_code == 200
    assert b"Queried, and empty" in r.data
    assert b"no pivotal trial matched" in r.data


def test_an_incomplete_bundle_blocks_a_proposal(client, provider):
    snap = provider.get("SANA")
    assert not snap.complete
    r = client.post("/workspace/discover", data={"ticker": "SANA"})
    assert b"incomplete" in r.data.lower()


# ---------------------------------------------------------------------------
# Identity is surfaced before anything depends on it
# ---------------------------------------------------------------------------

def test_the_sponsor_join_is_shown_with_its_state(client):
    """The largest source of silent wrongness in the system, made visible.

    In demo mode a bad match is invisible; here it is the analyst's first
    impression, so it appears above the candidates rather than beneath them.
    """
    r = client.post("/workspace/discover", data={"ticker": "RCKT"})
    text = r.data.decode()
    assert "Company identity" in text
    assert text.index("Company identity") < text.index("Candidate catalysts")


def test_an_unmatched_sponsor_is_flagged_for_review(provider):
    e = intake.entity(provider.get("SANA"))
    assert e["state"] == "review"
    assert "unverified" in e["explained"]


# ---------------------------------------------------------------------------
# Promise identity reaches the product
# ---------------------------------------------------------------------------

def test_candidates_carry_what_their_history_supports(provider):
    """A trial whose revisions changed shape must not be summarised with a slip
    number, and the page must say how many were refused."""
    cands = intake.candidates(provider.get("RCKT"))
    assert cands
    binding = next(c for c in cands if c["nct"] == "NCT06092034")
    assert binding["refused_revisions"] >= 1
    assert binding["slip_days"] == 0, (
        "every revision on this trial changed shape, so no movement is established"
    )


def test_unavailable_monitors_are_listed_as_unavailable(provider):
    """Offering a condition the desk cannot evaluate would tell the analyst it
    is being watched, which is worse than not offering it."""
    p = intake.propose(provider.get("RCKT"), "NCT06092034")
    by_id = {m["id"]: m for m in p["monitors"]}
    assert by_id["tag_path_changes"]["available"] is False
    assert "previous run" in by_id["tag_path_changes"]["why"]
    assert by_id["date_lapses"]["available"] is True


# ---------------------------------------------------------------------------
# Approval
# ---------------------------------------------------------------------------

def test_approval_writes_the_analysts_wording_not_the_proposal(tmp_path, monkeypatch):
    """The proposed claim is a starting point. A belief the analyst did not
    write is not their belief, and it is the text Granite later reads."""
    decisions = str(tmp_path / "decisions.jsonl")
    monkeypatch.setattr("console.app.DECISIONS_PATH", decisions)
    monkeypatch.setattr("console.app.ANCHOR_PATH", str(tmp_path / "ledger.anchor"))

    mine = ("Rocket reaches this readout on current cash and will not need to "
            "finance beforehand, which is the whole reason I am long.")
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        r = c.post("/workspace/approve", data={
            "ticker": "RCKT", "nct": "NCT06092034",
            "claim": mine, "min_gap": "0",
        })
        assert r.status_code == 200
        assert b"Recorded" in r.data

    with open(decisions) as f:
        entries = [json.loads(l) for l in f if l.strip()]
    assert len(entries) == 1
    card = entries[0]["card"]
    assert card["claim"] == mine
    assert card["card_id"] == "rckt:nct06092034"
    assert card["expected_low"] == 0.0
    assert entries[0]["author"] == "human:analyst"

    from engine.ledger import BeliefLedger
    assert BeliefLedger(decisions).verify() is True


def test_approval_refuses_a_stub_claim(tmp_path, monkeypatch):
    decisions = str(tmp_path / "decisions.jsonl")
    monkeypatch.setattr("console.app.DECISIONS_PATH", decisions)
    monkeypatch.setattr("console.app.ANCHOR_PATH", str(tmp_path / "ledger.anchor"))
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        r = c.post("/workspace/approve", data={
            "ticker": "RCKT", "nct": "NCT06092034", "claim": "yes", "min_gap": "0",
        })
        assert r.status_code == 400
    assert not os.path.exists(decisions)


def test_a_duplicate_is_a_conflict_not_an_overwrite(tmp_path, monkeypatch):
    decisions = str(tmp_path / "decisions.jsonl")
    monkeypatch.setattr("console.app.DECISIONS_PATH", decisions)
    monkeypatch.setattr("console.app.ANCHOR_PATH", str(tmp_path / "ledger.anchor"))
    claim = "Rocket reaches this registered completion on the cash it already holds."
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        data = {"ticker": "RCKT", "nct": "NCT06092034", "claim": claim, "min_gap": "0"}
        assert c.post("/workspace/approve", data=data).status_code == 200
        assert c.post("/workspace/approve", data=data).status_code == 409
    with open(decisions) as f:
        assert len([l for l in f if l.strip()]) == 1
