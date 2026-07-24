"""The claims the submission makes about itself, checked against the record.

Every check here was watched failing at `935e230` before the fix was written.
They are grouped in one file because they share a shape: a sentence somewhere in
the pitch had drifted from the thing it describes, and no existing guard read it.
The four classes:

  - a figure paired with a statistic computed under a different convention
  - a retracted finding still asserted as current
  - a count of Bob's own work that does not match the log or the directory
  - a number the model authored, rendered to a human

The lexicon covers the fifth class, unsupported silence, at its own layer:
`orchestrator/lexicon.py` now catches the semantic equivalents, so the existing
document and template scans fail on them without a new test here.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

REPO = Path(__file__).resolve().parents[1]

CLAIM_DOCS = ["README.md", "docs/SUBMISSION.md", "docs/DEMO.md", "docs/WRITEUP.md",
              "docs/COHORT.md", "docs/STATUS.md"]


def _snapshot(rel: str) -> dict:
    with open(REPO / rel) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 1. The anchor case's percentile belongs to one date convention
# ---------------------------------------------------------------------------
# Failure verification at 935e230: the generated `mechanism` block read "carry of
# at least 648 days sits at the 85th percentile", pairing the end-of-month figure
# with a rank `research/cohort.py` computes from the first-of-month reading of
# 677. Both documents carrying that block failed here, naming the sentence.

_SENTENCE = re.compile(r"[^.]*?percentile[^.]*\.", re.S)
_DAYS = re.compile(r"([\d,]+)[\s–-]*day")


def _sentences_about_percentiles(text: str) -> list[str]:
    return [" ".join(s.split()) for s in _SENTENCE.findall(text)]


@pytest.mark.parametrize("doc", CLAIM_DOCS)
def test_a_percentile_is_never_paired_with_the_other_conventions_days(doc):
    """A rank and the duration it ranks must be read off the same convention.

    A month-only registry date has two readings, and the cohort's percentile is
    computed from the first-of-month one. Quoting the end-of-month duration
    beside it reports a rank the study never measured.
    """
    cohort = _snapshot("data/cohort/snapshot.json")
    first_of_month = cohort["anchor_case"]["days_carried"]
    end_of_month = cohort["month_convention"]["anchor_days_eom"]

    path = REPO / doc
    if not path.exists():
        pytest.skip(f"{doc} does not exist")

    offenders = []
    for sentence in _sentences_about_percentiles(path.read_text()):
        named = {int(d.replace(",", "")) for d in _DAYS.findall(sentence)}
        if end_of_month in named and first_of_month not in named:
            offenders.append(sentence)

    assert not offenders, (
        f"{doc} pairs the end-of-month reading ({end_of_month} days) with a "
        f"percentile computed from the first-of-month reading "
        f"({first_of_month} days):\n  " + "\n  ".join(offenders)
    )


# ---------------------------------------------------------------------------
# 2. The retracted five-of-seven audit is not asserted as current
# ---------------------------------------------------------------------------
# Failure verification at 935e230: README.md:246 asserted it in the present tense
# and docs/SUBMISSION.md:306 repeated it inside "Do not say" guidance, while
# docs/LIMITS.md:313 already records it as the overstatement the three-state
# audit retracted.

_RETRACTED = re.compile(r"\bfive of (?:the )?seven\b", re.IGNORECASE)

# LIMITS.md is the correction record and states the claim in order to retract it.
_RETRACTION_RECORD = ("docs/LIMITS.md", "docs/BOB_LOG.md")


@pytest.mark.parametrize("doc", CLAIM_DOCS)
def test_the_retracted_binary_slip_audit_is_not_reasserted(doc):
    path = REPO / doc
    if not path.exists():
        pytest.skip(f"{doc} does not exist")
    hits = [f"{doc}:{i}: {ln.strip()[:100]}"
            for i, ln in enumerate(path.read_text().splitlines(), 1)
            if _RETRACTED.search(ln)]
    assert not hits, (
        "the first slip audit's five-of-seven count was retracted by the "
        "three-state audit and may not be asserted outside the correction "
        f"record {_RETRACTION_RECORD}:\n  " + "\n  ".join(hits)
    )


# ---------------------------------------------------------------------------
# 3. IBM Bob's counts come from the log and the directory
# ---------------------------------------------------------------------------
# Failure verification at 935e230: docs/SUBMISSION.md:205 said "Eleven logged
# tasks" and CLAUDE.md:14 said "eleven logged tasks and seven session
# transcripts", against 12 rows tagged IBM Bob and 9 transcript files.

_BOB_ROW = re.compile(r"^\|[^|]*\|\s*IBM Bob\s*\|")
_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
          7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven",
          12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen"}

# Every surface that publishes a count of Bob's work.
BOB_COUNT_SURFACES = ["README.md", "docs/SUBMISSION.md", "CLAUDE.md"]

# Each pattern's one group is a count, and what it counts. Pinned to the phrase
# rather than to a bare noun so "unreliable rows" and "two logged rows" are not
# read as claims about Bob. Every pattern must match somewhere across the three
# surfaces, so the guard cannot quietly stop guarding when prose is reworded.
BOB_COUNT_PATTERNS = [
    (r"\b([A-Za-z0-9]+)\s+logged tasks\b", "tasks"),
    (r"\btranscripts covering\s+([A-Za-z0-9]+)\s+rows\b", "tasks"),
    (r"\b([A-Za-z0-9]+)\s+(?:full\s+)?(?:session\s+)?transcripts\b", "transcripts"),
]


def _bob_tasks() -> int:
    return sum(1 for ln in (REPO / "docs" / "BOB_LOG.md").read_text().splitlines()
               if _BOB_ROW.match(ln))


def _bob_transcripts() -> list[Path]:
    return sorted((REPO / "docs" / "bob-sessions").glob("*.json"))


def test_the_transcript_directory_is_what_the_log_points_at():
    """Every transcript named in a Bob row exists, and none is unaccounted for."""
    log = (REPO / "docs" / "BOB_LOG.md").read_text()
    on_disk = {p.name for p in _bob_transcripts()}
    named = set(re.findall(r"docs/bob-sessions/([\w.-]+\.json)", log))
    assert named <= on_disk, f"the log names transcripts that do not exist: {named - on_disk}"
    assert on_disk <= named, f"transcripts no Bob row names: {on_disk - named}"


def test_bob_counts_on_every_surface_match_the_log_and_the_directory():
    """The README's Bob section is written from the log; so is everything else.

    Counting rows and files rather than trusting either published number,
    because the two disagreed: eleven tasks and seven transcripts were on the
    record against twelve rows and nine files.
    """
    actual = {"tasks": _bob_tasks(), "transcripts": len(_bob_transcripts())}
    wrong, matched = [], {p for p, _ in BOB_COUNT_PATTERNS}

    for doc in BOB_COUNT_SURFACES:
        text = " ".join((REPO / doc).read_text().split())
        for pattern, kind in BOB_COUNT_PATTERNS:
            for token in re.findall(pattern, text, re.IGNORECASE):
                matched.discard(pattern)
                want = actual[kind]
                if token.lower() not in {_WORDS.get(want), str(want)}:
                    wrong.append(f"{doc} says {token!r} {kind}; the record says "
                                 f"{want} ({_WORDS.get(want)})")

    assert not wrong, "Bob attribution counts do not match the record:\n  " + "\n  ".join(wrong)
    assert not matched, (
        "these patterns no longer match anything, so they guard nothing: "
        f"{sorted(matched)}")


# ---------------------------------------------------------------------------
# 4. No model-authored number reaches a rendered page
# ---------------------------------------------------------------------------
# Failure verification at 935e230: `conf 0.95` rendered on GET /redline twice,
# once from `redline.classification.confidence` in the template and once inside
# the Granite memo's own header line, which `orchestrator/challenge.py` composed
# from the same field. Both are model-authored. This test named both.

def test_no_rendered_page_carries_the_models_own_confidence():
    """`CLAUDE.md`: no model-produced number reaches the user.

    The classification's confidence is the model's own JSON field. It is kept in
    the snapshot as a record and is not displayed, so the only surviving numbers
    on the page are Python's.
    """
    from console.app import app as flask_app  # noqa: E402

    snap = _snapshot("data/snapshot.json")
    confidence = snap["redline"]["classification"]["confidence"]
    needles = {str(confidence), f"conf {confidence}"}

    flask_app.config["TESTING"] = True
    offenders = []
    with flask_app.test_client() as c:
        for rule in sorted({str(r.rule) for r in flask_app.url_map.iter_rules()}):
            if "<" in rule or "GET" not in (
                    next(r for r in flask_app.url_map.iter_rules()
                         if str(r.rule) == rule).methods or set()):
                continue
            body = c.get(rule).data.decode()
            for needle in needles:
                if needle in body:
                    offenders.append(f"GET {rule} renders {needle!r}")
        for ticker in ("RCKT", "BEAM", "PRME", "SRPT"):
            body = c.get(f"/contract/{ticker}").data.decode()
            for needle in needles:
                if needle in body:
                    offenders.append(f"GET /contract/{ticker} renders {needle!r}")
        # The parameterised rules are skipped by the loop above, and the
        # decision review screen renders the classification block, which is
        # where the confidence sat the first time it reached a page. Driven
        # explicitly rather than left to the filter.
        for path in (f"/decisions/{snap['redline']['card_id']}/review",
                     "/decisions/SRPT/review"):
            body = c.get(path).data.decode()
            for needle in needles:
                if needle in body:
                    offenders.append(f"GET {path} renders {needle!r}")

    assert not offenders, (
        "a number the model authored is on a page a human reads:\n  "
        + "\n  ".join(sorted(set(offenders)))
    )


def test_the_classification_source_is_still_shown():
    """A guard that only deletes would pass an empty page.

    Dropping the confidence must not drop the provenance beside it: the reader
    still has to see whether the judgement came from Granite or from the stub.
    """
    tpl = (REPO / "console" / "templates" / "redline.html").read_text()
    assert "classification.source" in tpl, (
        "the redline page no longer shows where the classification came from")


def test_the_memo_builder_does_not_compose_model_confidence_into_prose():
    """The structural fact the test above depends on.

    If this fails, `build_challenge` has learned to print the model's confidence
    again and every memo built after it carries a model-authored number into the
    page.
    """
    src = (REPO / "orchestrator" / "challenge.py").read_text()
    memo = src[src.index("    memo = ("):src.index("return ChallengeCard")]
    assert "cls.confidence" not in memo, (
        "build_challenge composes the classification's confidence into the memo; "
        "that memo is rendered on /redline")


# ---------------------------------------------------------------------------
# 5. LIMITS describes the controls that landed, not the ones that did not
# ---------------------------------------------------------------------------
# Failure verification at 935e230: docs/LIMITS.md:862 said "the ledger has no
# compare-and-swap on the head" eighteen lines above its own description of the
# `fcntl.flock` critical section and `Conflict`, and the closed receipt bullet
# still described selection by last entry rather than by card id.

RETIRED_LIMITS = [
    ("the ledger has no compare-and-swap on the head",
     "the append is now one critical section under an exclusive flock and a "
     "losing writer raises Conflict"),
    ("read from the ledger's last entry at render time",
     "the receipt is selected by card_id, not by whichever entry is last"),
]

CURRENT_LIMITS = [
    "fcntl.flock",
    "card_id",
]


@pytest.mark.parametrize("stale,why", RETIRED_LIMITS)
def test_limits_does_not_still_describe_a_retired_gap(stale, why):
    # Whitespace-normalised, because both sentences wrap and a guard a line
    # break switches off is the hollow kind.
    text = " ".join((REPO / "docs" / "LIMITS.md").read_text().split())
    assert stale not in text, (
        f"docs/LIMITS.md still says {stale!r}, which the landed control retired: "
        f"{why}")


@pytest.mark.parametrize("token", CURRENT_LIMITS)
def test_limits_names_the_control_that_replaced_it(token):
    """The other half: deleting the stale sentence is not the same as stating
    what is true now, and a limits document that goes quiet about a control is
    the same defect pointing the other way."""
    assert token in (REPO / "docs" / "LIMITS.md").read_text(), (
        f"docs/LIMITS.md no longer names {token!r}")


# ---------------------------------------------------------------------------
# 6. A superseded snapshot id is labelled as one
# ---------------------------------------------------------------------------
# Two ids two generations behind sit in docs/LIMITS.md's correction record, where
# they are correct: each names the store as it stood for the correction it
# describes, and a record that renames its own subject is not a record. Nothing
# checked which kind an id was, so a genuinely stale citation read the same as a
# deliberate one. This is the discriminator, not a ban.

_COHORT_ID = re.compile(r"cohort-[0-9a-f]{12}")


@pytest.mark.parametrize("doc", CLAIM_DOCS + ["docs/LIMITS.md"])
def test_a_superseded_snapshot_id_says_so_on_its_own_line(doc):
    current = _snapshot("data/cohort/snapshot.json")["snapshot_id"]
    path = REPO / doc
    if not path.exists():
        pytest.skip(f"{doc} does not exist")

    # Paragraph-scoped, because prose wraps and a marker one line away from its
    # own citation is still the reader's context. Blank-line separated, which is
    # what a markdown paragraph is.
    offenders = []
    line_no = 1
    for para in path.read_text().split("\n\n"):
        for found in _COHORT_ID.findall(para):
            if found != current and "historical" not in para.lower():
                offenders.append(f"{doc}:~{line_no}: {found}")
        line_no += para.count("\n") + 2

    assert not offenders, (
        f"a snapshot id other than the published {current} is cited without "
        "being marked historical, so a reader cannot tell a deliberate "
        "reference from a stale one:\n  " + "\n  ".join(offenders))
