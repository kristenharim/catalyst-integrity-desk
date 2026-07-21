"""Append-only, hash-chained BeliefCard ledger — the governed record of what
the engine *believes* about a catalyst contract.

A BeliefCard is one claim: "RCKT is funded to its primary completion date with
a gap of at least zero months." The engine measures the metric; the card holds
the *expected range plus the human rationale*. The Challenge step (later,
Granite) reads that rationale to judge whether a breach actually matters — the
card is what keeps the AI's job semantic, not a threshold check.

The ledger is event-sourced: every CREATE / UPDATE / RETIRE is appended, never
mutated, and hash-chained so tampering is detectable. Only an explicit human
approval appends an UPDATE — that is the whole governance guarantee.

Store: one JSONL file, one event per line. Human-readable, `cat`-able in a demo,
dependency-free (stdlib). ponytail: swap to sqlite3 only if querying history at
scale becomes the bottleneck — the append/verify logic stays identical.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, asdict, replace

GENESIS_HASH = "0" * 64
CREATE, UPDATE, RETIRE = "CREATE", "UPDATE", "RETIRE"


@dataclass
class BeliefCard:
    card_id: str
    scope: str            # "company:RCKT" or "trial:NCT04248439"
    claim: str            # the belief in words — the rationale Granite must read
    metric: str           # engine metric_id, e.g. "gap_months"
    expected_low: float
    expected_high: float
    driver: str
    confidence: int       # 1 (weak) .. 5 (high)
    source: str
    as_of: str
    status: str = "active"   # active | under_review | retired
    version: int = 1

    def in_range(self, value: float) -> bool:
        return self.expected_low <= value <= self.expected_high


@dataclass
class Breach:
    card_id: str
    metric: str
    observed: float
    expected_low: float
    expected_high: float
    direction: str        # "over" | "under"


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _hash(prev_hash: str, payload: dict) -> str:
    return hashlib.sha256((prev_hash + _canonical(payload)).encode()).hexdigest()


class BeliefLedger:
    def __init__(self, path: str):
        self.path = path

    # --- low-level read ---
    def _entries(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        with open(self.path) as f:
            return [json.loads(line) for line in f if line.strip()]

    def _last(self) -> dict | None:
        entries = self._entries()
        return entries[-1] if entries else None

    # --- append (the only writer) ---
    def _append(self, event: str, card: BeliefCard, author: str,
                triggered_by: str | None, reason: str | None, ts: float | None) -> dict:
        last = self._last()
        prev_hash = last["entry_hash"] if last else GENESIS_HASH
        seq = (last["seq"] + 1) if last else 0
        payload = {
            "seq": seq,
            "ts": ts if ts is not None else time.time(),
            "event": event,
            "author": author,
            "triggered_by": triggered_by,
            "reason": reason,
            "card": asdict(card),
            "prev_hash": prev_hash,
        }
        entry = {**payload, "entry_hash": _hash(prev_hash, payload)}
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

    def create(self, card: BeliefCard, author: str = "seed", ts: float | None = None) -> dict:
        if card.card_id in self.current():
            raise ValueError(f"card {card.card_id} already exists")
        return self._append(CREATE, replace(card, version=1, status="active"),
                            author, None, None, ts)

    def update(self, card: BeliefCard, author: str, triggered_by: str | None,
               reason: str, ts: float | None = None) -> dict:
        """Append an approved change. Bumps version off the current card.
        `author` should be a human (e.g. "human:kristen") — this is the gate."""
        cur = self.current().get(card.card_id)
        if cur is None:
            raise ValueError(f"card {card.card_id} does not exist")
        bumped = replace(card, version=cur.version + 1)
        return self._append(UPDATE, bumped, author, triggered_by, reason, ts)

    def retire(self, card_id: str, author: str, reason: str, ts: float | None = None) -> dict:
        cur = self.current().get(card_id)
        if cur is None:
            raise ValueError(f"card {card_id} does not exist")
        return self._append(RETIRE, replace(cur, status="retired", version=cur.version + 1),
                            author, None, reason, ts)

    # --- read models (fold events) ---
    def current(self) -> dict[str, BeliefCard]:
        """Latest card state per id, excluding retired ones."""
        state: dict[str, BeliefCard] = {}
        for e in self._entries():
            card = BeliefCard(**e["card"])
            if card.status == "retired":
                state.pop(card.card_id, None)
            else:
                state[card.card_id] = card
        return state

    def history(self, card_id: str) -> list[dict]:
        return [e for e in self._entries() if e["card"]["card_id"] == card_id]

    # --- integrity ---
    def verify(self) -> bool:
        """Recompute the whole chain; True iff untampered. Never raises.

        Editing a byte of the file usually breaks the JSON or drops a key rather
        than producing a well-formed entry with a wrong hash, so an integrity
        check that only handles the tidy case raises on the most likely kind of
        tampering. A ledger that cannot be parsed is a ledger that cannot be
        verified, and the honest answer to "is this intact" is no, not a
        traceback. Callers render this as a status; a status that throws is worse
        than one that reports false.
        """
        try:
            entries = self._entries()
        except Exception:                                       # noqa: BLE001
            return False

        prev_hash = GENESIS_HASH
        for i, e in enumerate(entries):
            try:
                if e["seq"] != i or e["prev_hash"] != prev_hash:
                    return False
                payload = {k: e[k] for k in
                           ("seq", "ts", "event", "author", "triggered_by", "reason", "card", "prev_hash")}
                if _hash(prev_hash, payload) != e["entry_hash"]:
                    return False
                prev_hash = e["entry_hash"]
            except Exception:                                   # noqa: BLE001
                return False
        return True


def scan_breaches(cards: dict[str, BeliefCard], packet_flat: dict[str, float]) -> list[Breach]:
    """Deterministic breach trigger: which active cards have their metric outside
    the expected range *right now*. This only fires the Challenge — whether the
    breach MATTERS is Granite's judgment call against the card's rationale."""
    breaches = []
    for card in cards.values():
        if card.status != "active":
            continue
        v = packet_flat.get(card.metric)
        if v is None:
            continue
        if not card.in_range(v):
            breaches.append(Breach(
                card_id=card.card_id, metric=card.metric, observed=float(v),
                expected_low=card.expected_low, expected_high=card.expected_high,
                direction="over" if v > card.expected_high else "under",
            ))
    return breaches
