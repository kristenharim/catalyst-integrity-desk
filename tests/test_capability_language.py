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

# Every surface that describes what the product does to a belief. docs/SUBMISSION.md
# was added after it was found carrying the same false sentence as README.md while
# sitting outside the guard entirely.
SURFACES = (
    ["README.md", "docs/UI.md", "docs/WORKSPACE.md", "docs/DEMO.md",
     "docs/SUBMISSION.md"]
    + [f"console/templates/{n}" for n in sorted(os.listdir(REPO / "console" / "templates"))
       if n.endswith(".html")]
)

# Each pattern is a claim the code does not support, with why it is false.
FORBIDDEN = [
    (r"picked up (at|on) the next (run|rebuild)|picks it up on the next run",
     "no rebuild reads the ledger; make_snapshot.py never opens decisions.jsonl"),
    (r"watch(es|ed|ing) a (written |recorded |new )?belief",
     "a belief is recorded against a frozen contract; nothing watches it"),
    (r"begin(s|ning)? watching|start(s|ed)? watching",
     "recording a belief starts no watcher"),
    (r"enter(s|ed|ing)? monitoring",
     "there is no monitoring state for a belief to enter"),
    (r"(is|are|gets?|becomes?|being|then) automatically monitored",
     "nothing is monitored automatically; the rebuild is manual and does not "
     "read the ledger"),
    (r"monitored after (the )?rebuild|monitored on (the )?rebuild",
     "a rebuild does not pick a recorded belief up, so it cannot monitor one"),
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
    """Each line joined to the one after it, so a wrapped claim is still one string.

    Scanning single lines let the exact sentence this file exists to forbid sit
    in `docs/SUBMISSION.md` unnoticed, because the prose wrapped between "the
    system watches a written" and "belief". The identical sentence in README.md
    happened to fall inside one line and was caught. A guard a line break can
    switch off is the hollow kind, and the count guard in tests/test_console.py
    already learned this lesson on its own numbers.

    Two lines is enough: these are wrapped paragraphs, not phrases spanning
    three lines of an eighty-column file. The line number reported is where the
    match starts.
    """
    raw = (REPO / rel).read_text().splitlines()
    return [(i, " ".join(raw[i - 1:i + 1]))
            for i in range(1, len(raw) + 1)]


@pytest.mark.parametrize("rel", SURFACES)
def test_no_surface_claims_a_belief_is_watched(rel):
    offenders = set()
    for pattern, why in FORBIDDEN:
        for i, window in _lines(rel):
            if any(a in window for a in ALLOWED):
                continue
            m = re.search(pattern, window)
            if m:
                offenders.add(f"{rel}:{i} [{why}] {m.group(0)}")
    assert not offenders, ("capability language outruns the code:\n  "
                           + "\n  ".join(sorted(offenders)))


# ---------------------------------------------------------------------------
# The patterns themselves, checked against text rather than against the repo
# ---------------------------------------------------------------------------
# A pattern list is only worth what it catches. Scanning the repo proves the
# repo is currently clean, which an empty pattern list also proves. These two
# cases pin the patterns directly: every unsupported present-tense monitoring
# claim must match something, and every accurate sentence must match nothing.

UNSUPPORTED = [
    "So the system watches a written belief, detects when a change contradicts it.",
    "The contract begins watching once you approve it.",
    "The belief enters monitoring immediately.",
    "From here it is automatically monitored.",
    "The card is monitored after rebuild.",
    "A recorded belief is picked up on the next run.",
    "A recorded belief is picked up at the next rebuild.",
]

# Accurate, or plainly about the intended product class rather than about what
# happens to a belief today. A guard that fires on these is a guard that gets
# switched off, and "monitoring queue" is the name of a shipped page.
SUPPORTED = [
    "Recorded, not yet watched.",
    "The monitoring queue lists one row per contract per reason to look.",
    "recorded yes, projected from the frozen snapshot yes, "
    "**manually rebuildable** no for beliefs, **automatically monitored** no.",
    "The system records a written belief against a frozen evidence contract.",
    "The workspace records a contract.",
    "Two states a monitoring queue should have are deliberately absent.",
]


def _matches(line: str):
    return [why for pattern, why in FORBIDDEN if re.search(pattern, line)]


@pytest.mark.parametrize("line", UNSUPPORTED)
def test_an_unsupported_monitoring_claim_is_caught(line):
    assert _matches(line), (
        f"no FORBIDDEN pattern catches {line!r}; the guard would let this claim "
        "ship on any surface"
    )


@pytest.mark.parametrize("line", SUPPORTED)
def test_accurate_capability_language_is_not_caught(line):
    assert not _matches(line), (
        f"{line!r} was rejected by {_matches(line)}; the guard is firing on "
        "language the code does support"
    )


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
