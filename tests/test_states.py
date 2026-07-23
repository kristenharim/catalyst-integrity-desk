"""The three state axes stay separate, and the precedence between them holds.

These are behaviour tests rather than number tests. The numeric provenance suite
already proves every figure on screen came from the snapshot; what it cannot
prove is that a tampered ledger stops short of being reported as a broken
thesis, which is a different failure and a worse one.
"""
from __future__ import annotations

import ast
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from console import review, states
from engine.ledger import BeliefCard, BeliefLedger
from orchestrator.anchor import record as anchor_record
from orchestrator.challenge import ReviewLog


def _contract(*, reliable=True, gap=None, lapsed=(), contingent=0, refused=0,
              name="Test Bio", nct="NCT00000001", catalyst="2027-01-01"):
    """A contract dict shaped like the snapshot, with only the fields the state
    model reads. Building these by hand rather than slicing the real snapshot
    keeps each test about one condition."""
    return {
        "runway": {
            "name": name, "reliable": reliable,
            "notes": [] if reliable else ["burn estimate is not usable"],
        },
        "trial": {"nct": nct},
        "catalyst_date": catalyst,
        "gap_months": gap,
        "gap_months_1f": None if gap is None else f"{gap:.1f}",
        "lapsed": list(lapsed),
        "history": {
            "slip_contingent_revisions": contingent,
            "slip_refused_revisions": refused,
        },
    }


def _card(card_id="tst:funded_to_catalyst"):
    return BeliefCard(
        card_id=card_id, scope="NCT00000001",
        claim="Test Bio reaches its registered primary completion before runway exhaustion.",
        metric="gap_months", expected_low=0.0, expected_high=10.0,
        driver="SEC XBRL liquidity vs ClinicalTrials.gov registered PCD",
        confidence=3, source="tests", as_of="2026-03-31",
    )


# ---------------------------------------------------------------------------
# The separation itself
# ---------------------------------------------------------------------------

def test_states_module_cannot_reach_the_ledger_or_anchor():
    """Enforced by the import graph, not by anyone remembering.

    If this fails, someone gave the evidence axis a way to learn about record
    integrity, and the two can now be conflated by accident.
    """
    tree = ast.parse(Path(states.__file__).read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
    leaked = [m for m in imported if "ledger" in m or "anchor" in m or "review" in m]
    assert not leaked, f"states.py must not import {leaked}"


def test_ledger_tampering_does_not_become_a_contract_breach(tmp_path):
    ledger = BeliefLedger(str(tmp_path / "decisions.jsonl"))
    anchor = str(tmp_path / "ledger.anchor")
    ledger.create(_card(), author="human:test")
    anchor_record(ledger, anchor_path=anchor)

    contract = _contract(gap=4.0)
    before = states.build_decision(contract)
    assert review.record_integrity(ledger, anchor)["state"] == review.RECORD_INTACT

    path = tmp_path / "decisions.jsonl"
    path.write_text(path.read_text().replace('"confidence": 3', '"confidence": 4'))

    assert review.record_integrity(ledger, anchor)["state"] == review.RECORD_TAMPERED
    # The contract never moved. Evidence is a statement about public records and
    # nothing a human did to the decision file can change it.
    assert states.build_decision(contract) == before


def test_contract_breach_does_not_become_record_tampering(tmp_path):
    ledger = BeliefLedger(str(tmp_path / "decisions.jsonl"))
    anchor = str(tmp_path / "ledger.anchor")
    ledger.create(_card(), author="human:test")
    anchor_record(ledger, anchor_path=anchor)

    breached = states.build_decision(_contract(gap=-14.5))
    assert breached["evidence"] == states.REVIEW_REQUIRED
    assert review.record_integrity(ledger, anchor)["state"] == review.RECORD_INTACT


def test_workflow_state_does_not_change_evidence_state():
    contract = _contract(gap=-14.5)
    evidence = states.build_decision(contract)["evidence"]
    for card, resolved in [(None, None), ({"status": "active"}, None),
                           ({"status": "active"}, 1.0), ({"status": "retired"}, None)]:
        assert review.workflow_state(card, resolved) in review.COMPUTABLE
        assert states.build_decision(contract)["evidence"] == evidence


# ---------------------------------------------------------------------------
# Precedence
# ---------------------------------------------------------------------------

def test_deterministic_outranks_contingent_and_both_stay_visible():
    """Rocket's shape: a breach plus an endpoint question nobody has ruled on."""
    d = states.build_decision(_contract(gap=-14.5, refused=1))
    assert d["evidence"] == states.REVIEW_REQUIRED
    kinds = {t["kind"] for t in d["triggers"]}
    assert states.FUNDING_THRESHOLD_CROSSED in kinds
    # The secondary condition is not discarded to produce the badge.
    assert states.COMPARISON_REFUSED in kinds


def test_unavailable_outranks_a_deterministic_failure():
    d = states.build_decision(
        _contract(reliable=False, gap=-14.5,
                  lapsed=[{"nct": "NCT00000002", "pcd": "2025-03-04"}]))
    assert d["evidence"] == states.UNAVAILABLE
    kinds = [t["kind"] for t in d["triggers"]]
    assert states.RUNWAY_UNRELIABLE in kinds
    assert states.REGISTERED_EXPECTATION_EXPIRED in kinds
    # An unusable burn makes the gap unusable, so the contract is never also
    # told its threshold was crossed.
    assert states.FUNDING_THRESHOLD_CROSSED not in kinds


def test_contingent_alone_is_contingent():
    d = states.build_decision(_contract(gap=40.0, contingent=2))
    assert d["evidence"] == states.CONTINGENT


def test_approaching_a_threshold_is_not_a_failed_condition():
    """The contract still holds, so the badge may not say it broke.

    The trigger stays visible underneath, which is the whole point of keeping
    triggers beside the state instead of collapsing into it.
    """
    d = states.build_decision(_contract(gap=4.0))
    assert d["evidence"] == states.INTACT
    assert [t["kind"] for t in d["triggers"]] == [states.FUNDING_THRESHOLD_APPROACHING]


def test_no_triggers_is_intact():
    d = states.build_decision(_contract(gap=40.0))
    assert d["evidence"] == states.INTACT
    assert d["triggers"] == []


def test_reading_order_puts_judgement_above_unfixable_data():
    """Badge precedence and inbox order are different questions.

    Unavailable wins the badge because a contract you cannot establish may not
    be called breached. It must not win the queue, because the analyst can do
    nothing about it today.
    """
    breached = states.build_decision(_contract(gap=-14.5))
    unavailable = states.build_decision(_contract(reliable=False))
    assert breached["sort_key"] < unavailable["sort_key"]


# ---------------------------------------------------------------------------
# The legacy queue is a projection, not a second opinion
# ---------------------------------------------------------------------------

def test_queue_rows_project_from_triggers_and_never_rank_an_unreliable_row():
    from console.make_snapshot import _queue_rows

    rows = _queue_rows("SRPT", _contract(reliable=False,
                                         lapsed=[{"nct": "NCT2", "pcd": "2025-03-04"}]))
    states_seen = {r["state"] for r in rows}
    assert states_seen == {"unreliable", "lapsed"}
    # The project's rule: shown, never ranked. A gap figure beside an unusable
    # burn ranks it in the reader's head.
    assert all(r["gap_1f"] is None for r in rows)


def test_new_triggers_do_not_silently_move_the_old_queue_counts():
    from console.make_snapshot import _queue_rows

    rows = _queue_rows("TST", _contract(gap=40.0, contingent=3, refused=2))
    # Endpoint continuity and refused comparison have no legacy queue state, so
    # the old queue still calls this clear rather than inventing rows for them.
    assert [r["state"] for r in rows] == ["clear"]


# ---------------------------------------------------------------------------
# Against the real snapshot
# ---------------------------------------------------------------------------

def test_real_snapshot_carries_a_decision_block_for_every_contract():
    path = Path(__file__).resolve().parents[1] / "data" / "snapshot.json"
    snap = json.loads(path.read_text())
    for ticker, c in snap["contracts"].items():
        d = c.get("decision")
        assert d, f"{ticker} has no decision block"
        assert d["evidence"] in states.EVIDENCE_LABELS
        assert d["n_triggers"] == len(d["triggers"])


def test_rocket_reads_review_required_with_its_contingent_trigger_beneath():
    path = Path(__file__).resolve().parents[1] / "data" / "snapshot.json"
    snap = json.loads(path.read_text())
    d = snap["contracts"]["RCKT"]["decision"]
    assert d["evidence"] == states.REVIEW_REQUIRED
    kinds = {t["kind"] for t in d["triggers"]}
    assert states.REGISTERED_EXPECTATION_EXPIRED in kinds
    assert states.FUNDING_THRESHOLD_CROSSED in kinds
    assert any(t["state"] == states.CONTINGENT for t in d["triggers"])
