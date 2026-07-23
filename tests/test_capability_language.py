"""What the product says it does must match what it does.

A belief written through the console is recorded and hash-chained, and nothing
reads it back. `console/make_snapshot.py` holds no reference to `BeliefLedger`
or `decisions.jsonl`, so no rebuild picks a card up, and the one belief the
system challenges is written in Python inside the builder.

Three screens and one document said otherwise, each claiming a card is "picked
up at the next rebuild". The sentence was not a rounding error in the prose: it
described a mechanism that does not exist, on the screen where a human has just
been asked to trust the thing.

The last test here is the load-bearing one. It pins the structural fact the
language rests on, so that wiring the rebuild to read the ledger fails this file
and tells whoever did it to go and update the words.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

REPO = Path(__file__).resolve().parents[1]

# Every surface that describes what the product does to a belief.
SURFACES = (
    ["README.md", "docs/UI.md", "docs/WORKSPACE.md", "docs/DEMO.md"]
    + [f"console/templates/{n}" for n in sorted(os.listdir(REPO / "console" / "templates"))
       if n.endswith(".html")]
)

# Each pattern is a claim the code does not support, with why it is false.
FORBIDDEN = [
    (r"picked up at the next rebuild|picks it up on the next run",
     "no rebuild reads the ledger; make_snapshot.py never opens decisions.jsonl"),
    (r"monitored contract out",
     "the workspace records a contract, it does not begin watching one"),
    (r"start(s|ed)? monitoring|begin(s)? monitoring|monitoring (is )?enabled",
     "nothing starts when a belief is recorded"),
    (r"is now monitored|now being monitored|now watched",
     "a recorded belief is not watched"),
    (r"[Mm]onitoring starts from",
     "recording a belief starts nothing"),
    (r"what this can be watched for",
     "those conditions are not evaluated against the card being approved"),
]

# Allowed on purpose. The command bar counts rows in the frozen snapshot, and
# "contracts monitored" is the product's category language rather than a claim
# about any belief a human just wrote. Named here so the allowance is a decision
# on the record rather than a gap in the patterns.
ALLOWED = {"contracts monitored"}


def _lines(rel: str):
    text = (REPO / rel).read_text()
    return [(i, ln) for i, ln in enumerate(text.splitlines(), 1)]


@pytest.mark.parametrize("rel", SURFACES)
def test_no_surface_claims_a_belief_is_watched(rel):
    offenders = []
    for pattern, why in FORBIDDEN:
        for i, line in _lines(rel):
            if any(a in line for a in ALLOWED):
                continue
            if re.search(pattern, line):
                offenders.append(f"{rel}:{i} [{why}] {line.strip()[:90]}")
    assert not offenders, "capability language outruns the code:\n  " + "\n  ".join(offenders)


def test_the_honest_sentence_is_still_there():
    """A guard that only deletes claims would pass an empty page."""
    belief = (REPO / "console" / "templates" / "belief_new.html").read_text()
    workspace = (REPO / "console" / "templates" / "workspace.html").read_text()
    assert "Recorded, not yet watched" in belief
    assert "Recorded, not yet watched" in workspace


def test_the_ui_contract_states_the_capability_precisely():
    ui = (REPO / "docs" / "UI.md").read_text().lower()
    for phrase in ["recorded", "projected from the frozen snapshot",
                   "manually rebuildable", "automatically monitored"]:
        assert phrase in ui, f"docs/UI.md no longer classifies {phrase!r}"


def test_the_rebuild_still_does_not_read_the_ledger():
    """The fact every sentence above depends on.

    If this fails, the rebuild has learned to read beliefs. That is good news
    and it makes the wording on four surfaces wrong, so fix them together.
    """
    src = (REPO / "console" / "make_snapshot.py").read_text()
    for forbidden in ("BeliefLedger", "decisions.jsonl", "DECISIONS_PATH"):
        assert forbidden not in src, (
            f"make_snapshot.py now references {forbidden}; a rebuild may now pick up a "
            "recorded belief, so the capability language on the belief and workspace "
            "screens, docs/UI.md and docs/DEMO.md has to be revisited"
        )
