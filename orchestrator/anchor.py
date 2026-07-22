"""External anchor for the BeliefLedger.

verify() proves the presented chain is self-consistent. It cannot prove it is
the original chain, because nothing outside the ledger file pins what the head
hash or entry count should be.  This module fills that gap.

After each successful append the decision path calls record(), which writes
the head hash and entry count to data/ledger.anchor.  check() reads that file
and compares: a truncated chain or a wholesale replacement produces a head hash
or count that disagrees with the anchor even when verify() returns True.

Three detectable states:
  "intact"     -- verify() True AND anchor matches head/count
  "tampered"   -- verify() returns False (a byte was edited inside a hashed payload)
  "truncated"  -- verify() True but head or count disagrees with the anchor
                  (deletion, truncation, or wholesale replacement with a fresh chain)

Limitation: this detects the above given that the anchor file itself was not
also rewritten.  It is a real improvement; it is not a guarantee.
"""
from __future__ import annotations

import json
import os

from engine.ledger import BeliefLedger

ANCHOR_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ledger.anchor")


def record(ledger: BeliefLedger, anchor_path: str = ANCHOR_PATH) -> None:
    """Write the current head hash and entry count to the anchor file.

    Called right after a successful ledger append, so the anchor always
    reflects the last known good state of the chain.
    """
    entries = ledger._entries()
    if not entries:
        return
    head = entries[-1]["entry_hash"]
    count = len(entries)
    os.makedirs(os.path.dirname(anchor_path) or ".", exist_ok=True)
    with open(anchor_path, "w") as f:
        json.dump({"head": head, "count": count}, f)


def check(ledger: BeliefLedger, anchor_path: str = ANCHOR_PATH) -> str:
    """Compare the live chain against the anchor file.

    Returns one of three strings:
      "intact"     -- chain verifies and matches the anchor
      "tampered"   -- chain does not verify (a byte was edited)
      "truncated"  -- chain verifies but disagrees with the anchor
                      (deletion, replacement, or truncation)

    If the anchor file does not exist, returns "intact" only when verify()
    is True and there are no entries; otherwise returns "truncated", because
    a missing anchor when decisions have been recorded is itself a signal.
    """
    chain_ok = ledger.verify()

    if not chain_ok:
        return "tampered"

    # Chain verifies -- now compare against the anchor.
    if not os.path.exists(anchor_path):
        entries = ledger._entries()
        # No anchor and no entries: nothing has been decided yet, nothing to check.
        if not entries:
            return "intact"
        # Entries exist but anchor is absent -- someone removed the anchor or
        # the decision path never called record().  Treat as truncated.
        return "truncated"

    try:
        with open(anchor_path) as f:
            anchor = json.load(f)
        expected_head = anchor["head"]
        expected_count = anchor["count"]
    except Exception:       # noqa: BLE001 -- unreadable anchor is itself a signal
        return "truncated"

    entries = ledger._entries()
    actual_head = entries[-1]["entry_hash"] if entries else None
    actual_count = len(entries)

    if actual_head == expected_head and actual_count == expected_count:
        return "intact"
    return "truncated"
