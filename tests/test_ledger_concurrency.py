"""Two humans deciding at the same moment must not make the ledger cry tamper.

The chain is the product's evidence that a decision history was not edited. A
guard that reports tampering when nobody tampered is worse than no guard: it
teaches the reader to ignore the one signal that matters.

Before the lock, `_append` read the tail, computed `seq` and `prev_hash`, and
only then appended. Two writers released together read the same tail and wrote
two entries claiming the same link. `verify()` then returned False and
`anchor.check` returned "tampered" on a file nobody had touched.
"""
from __future__ import annotations

import json
import os
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.ledger import BeliefCard, BeliefLedger, Conflict
from orchestrator.anchor import check as anchor_check, record as anchor_record

WRITERS = 4


def _card(i: int) -> BeliefCard:
    return BeliefCard(
        card_id=f"conc{i}:funded_to_catalyst", scope=f"NCT9000000{i}",
        claim="Test Bio reaches its registered primary completion before runway exhaustion.",
        metric="gap_months", expected_low=0.0, expected_high=10.0,
        driver="SEC XBRL liquidity vs registered primary completion",
        confidence=3, source="tests", as_of="2026-03-31",
    )


def _race(path: str, anchor: str, n: int = WRITERS) -> BeliefLedger:
    """Seed one entry, then release n writers at the same instant."""
    ledger = BeliefLedger(path)
    ledger.create(_card(0), author="human:seed")
    anchor_record(ledger, anchor_path=anchor)

    barrier = threading.Barrier(n)
    errors: list[BaseException] = []

    def write(i: int) -> None:
        try:
            barrier.wait()
            own = BeliefLedger(path)
            own.create(_card(i), author=f"human:{i}")
            anchor_record(own, anchor_path=anchor)
        except BaseException as exc:                     # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=write, args=(i,)) for i in range(1, n + 1)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"writer raised: {errors[0]!r}"
    return BeliefLedger(path)


def test_concurrent_writes_leave_one_unbroken_chain(tmp_path):
    path = str(tmp_path / "decisions.jsonl")
    anchor = str(tmp_path / "ledger.anchor")
    ledger = _race(path, anchor)

    entries = [json.loads(line) for line in open(path) if line.strip()]
    seqs = [e["seq"] for e in entries]

    assert len(entries) == WRITERS + 1, "an append was lost"
    assert seqs == sorted(set(seqs)), f"duplicated or reordered seq: {seqs}"
    assert seqs == list(range(len(seqs))), f"seq is not consecutive: {seqs}"

    prevs = [e["prev_hash"] for e in entries]
    assert len(set(prevs)) == len(prevs), "two entries claim the same predecessor"


def test_concurrent_writes_do_not_report_tampering(tmp_path):
    """The regression this file exists for."""
    path = str(tmp_path / "decisions.jsonl")
    anchor = str(tmp_path / "ledger.anchor")
    ledger = _race(path, anchor)

    assert ledger.verify() is True, "benign concurrent writes broke the chain"
    assert anchor_check(ledger, anchor_path=anchor) == "intact", (
        "benign concurrent writes were reported as tampering"
    )


def test_every_concurrent_card_survives(tmp_path):
    path = str(tmp_path / "decisions.jsonl")
    anchor = str(tmp_path / "ledger.anchor")
    ledger = _race(path, anchor)
    assert len(ledger.current()) == WRITERS + 1, "a card was lost to a lost update"


def test_same_card_concurrent_creates_conflict_rather_than_corrupt(tmp_path):
    """Four writers, one card id. Exactly one wins and the losers are told.

    The precondition used to run outside the lock, so every writer read a ledger
    without the card, every writer passed its own existence check, and four
    CREATEs for one id went in. Losing a race and being told is a correct
    outcome; silently writing a second entry is not.
    """
    path = str(tmp_path / "decisions.jsonl")
    anchor = str(tmp_path / "ledger.anchor")
    BeliefLedger(path).create(_card(0), author="human:seed")
    anchor_record(BeliefLedger(path), anchor_path=anchor)

    n = 4
    barrier = threading.Barrier(n)
    won, lost = [], []

    def write(_i: int) -> None:
        barrier.wait()
        try:
            BeliefLedger(path).create(_card(99), author="human:racer")
            won.append(1)
        except Conflict:
            lost.append(1)

    threads = [threading.Thread(target=write, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(won) == 1, f"{len(won)} writers created the same card id"
    assert len(lost) == n - 1, "a loser was not told it lost"
    ledger = BeliefLedger(path)
    assert ledger.verify() is True
    assert anchor_check(ledger, anchor_path=anchor) in ("intact", "truncated")
    ids = [e["card"]["card_id"] for e in
           [json.loads(l) for l in open(path) if l.strip()]]
    assert ids.count("conc99:funded_to_catalyst") == 1


def test_concurrent_updates_do_not_share_a_version(tmp_path):
    """Every approved amendment must bump off the version it actually saw."""
    path = str(tmp_path / "decisions.jsonl")
    anchor = str(tmp_path / "ledger.anchor")
    BeliefLedger(path).create(_card(1), author="human:seed")
    anchor_record(BeliefLedger(path), anchor_path=anchor)

    n = 4
    barrier = threading.Barrier(n)

    def write(i: int) -> None:
        barrier.wait()
        BeliefLedger(path).update(_card(1), author=f"human:{i}",
                                  triggered_by="breach:test", reason="amended")

    threads = [threading.Thread(target=write, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    entries = [json.loads(l) for l in open(path) if l.strip()]
    versions = [e["card"]["version"] for e in entries if e["event"] == "UPDATE"]
    assert sorted(versions) == list(range(2, 2 + n)), (
        f"two amendments bumped off the same version: {versions}"
    )
    assert BeliefLedger(path).verify() is True


def test_real_tampering_is_still_caught(tmp_path):
    """The control. A lock that also silenced the guard would pass everything above."""
    path = str(tmp_path / "decisions.jsonl")
    anchor = str(tmp_path / "ledger.anchor")
    ledger = _race(path, anchor)

    text = open(path).read().replace('"confidence": 3', '"confidence": 4', 1)
    open(path, "w").write(text)

    assert BeliefLedger(path).verify() is False
    assert anchor_check(BeliefLedger(path), anchor_path=anchor) == "tampered"
