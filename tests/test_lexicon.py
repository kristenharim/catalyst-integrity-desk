"""The forbidden-claims list, enforced rather than documented.

`docs/LIMITS.md` has always said what this system may not claim. Saying it in a
document protects nothing: the claim that ships is the one on the page, and
prose drifts under commercial pressure exactly where it matters most, which is
the pitch.

So the list is a lexicon, and three things check it:

  1. Granite's output passes through it at runtime, beside `_fabricated()`. A
     model that says "this looks like fraud" has broken provenance as badly as
     one that invents a figure, and is discarded the same way.
  2. Every rendered page is scanned. The UI is where a claim reaches a human.
  3. The claim-bearing docs are scanned, with an explicit exemption marker for
     prose that quotes a banned phrase in order to forbid it.

Verified failing before it was trusted, three ways, each recorded in the test
that catches it.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from console.app import app as flask_app  # noqa: E402
from orchestrator import lexicon  # noqa: E402

REPO = os.path.join(os.path.dirname(__file__), "..")

# Every page a human sees. A claim on any of these is a claim the product makes.
PAGES = ["/contract/RCKT", "/contract/BEAM", "/contracts", "/redline", "/queue",
         "/belief/new"]

# Documents that make claims on the project's behalf. LIMITS.md and this file's
# own source are excluded: both quote banned phrases constantly, by design.
CLAIM_DOCS = ["README.md", "docs/SUBMISSION.md", "docs/DEMO.md",
              "docs/PRINCIPLE.md", "docs/WORKSPACE.md", "docs/BACKTEST.md",
              # The cohort write-up is the most claim-dense document here and the
              # one most likely to be read on its own, so it is enforced like a
              # rendered page rather than trusted like a working note. It caught
              # two violations in the first draft.
              "docs/WRITEUP.md"]


@pytest.fixture(scope="module")
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# The lexicon itself
# ---------------------------------------------------------------------------

def test_lexicon_self_check():
    """Each kind fires and each honest phrasing passes.

    The second half matters as much as the first: a guard that also rejects the
    true sentences would push the product toward vaguer language, which is the
    opposite of the intent.
    """
    lexicon.demo()


def test_the_honest_sentences_survive():
    """The sentences this product actually needs must not trip the guard."""
    for ok in [
        "The registered primary-completion expectation moved 943 days.",
        "No amendment was found in the ClinicalTrials.gov version history "
        "queried on 2026-07-21.",
        "The commitment changed shape, so the date difference is not slip.",
        "Rows whose burn estimate is unreliable are shown and never ranked.",
        "The ledger detects tampering, deletion and replacement of recorded "
        "decisions, given the anchor was not also rewritten.",
        "A lapsed completion date is never treated as a catalyst.",
    ]:
        assert lexicon.clean(ok), (ok, [str(v) for v in lexicon.scan(ok)])


# ---------------------------------------------------------------------------
# The pages
# ---------------------------------------------------------------------------
# Failure verification: the string "This suggests the technology does not work."
# was added to queue.html and this test named it as a [feasibility] violation on
# GET /queue. Removed afterwards.

@pytest.mark.parametrize("route", PAGES)
def test_no_page_makes_a_forbidden_claim(client, route):
    r = client.get(route)
    assert r.status_code == 200
    violations = lexicon.scan(r.data.decode())
    assert not violations, (
        f"GET {route} makes a claim the evidence does not support:\n  "
        + "\n  ".join(str(v) for v in violations)
    )


# ---------------------------------------------------------------------------
# The documents
# ---------------------------------------------------------------------------
# Failure verification: 'the technology actually works' was added to README.md
# and this test named it with the file and line.

@pytest.mark.parametrize("doc", CLAIM_DOCS)
def test_no_claim_doc_makes_a_forbidden_claim(doc):
    path = os.path.join(REPO, doc)
    if not os.path.exists(path):
        pytest.skip(f"{doc} does not exist yet")
    with open(path) as f:
        violations = lexicon.scan(f.read())
    assert not violations, (
        f"{doc} makes a claim the evidence does not support:\n  "
        + "\n  ".join(str(v) for v in violations)
        + f"\n(If the line quotes a banned phrase in order to forbid it, end it "
          f"with {lexicon.EXEMPT_MARKER})"
    )


# ---------------------------------------------------------------------------
# The model
# ---------------------------------------------------------------------------
# Failure verification: the lexicon call was removed from granite.py::_parse and
# this test failed, because a rationale reading "this is fraud" was accepted.

def test_granite_rationale_passes_through_the_lexicon():
    """The guard must run in the product, not only in CI.

    Asserted at the call site rather than by mocking a live model, because the
    thing that can regress is someone deleting the call, and a live-model test
    would skip without credentials exactly when that happened.
    """
    path = os.path.join(REPO, "orchestrator", "granite.py")
    with open(path) as f:
        body = f.read()
    assert "lexicon.scan(rationale)" in body, (
        "granite.py no longer screens the model's rationale through the "
        "lexicon; a forbidden claim would reach the page"
    )
    fab = body.index("_fabricated(rationale")
    lex = body.index("lexicon.scan(rationale)")
    parse_end = body.index("Classification(label", lex)
    assert fab < lex < parse_end, (
        "both guards must run inside _parse, before a Classification is built"
    )


# Words that make a line a prohibition rather than an assertion. A line that
# quotes a banned phrase in order to forbid it will contain one of these; a line
# that simply makes the claim will not.
_PROHIBITION_CUES = ("never", "do not say", "don't say", "not immutable",
                     "must not", "rather than", "instead of", "is banned",
                     "forbidden", "avoid", "do not use")


def test_the_exemption_marker_only_appears_on_lines_that_forbid():
    """The escape hatch must not be able to silence an assertion.

    An exemption is legitimate on "Do not say 'immutable' about the ledger" and
    illegitimate on "The ledger is immutable". The difference is mechanical: the
    first is a prohibition and says so. Requiring a prohibition cue on any
    exempted line means the marker cannot turn a claim into a non-claim, only
    stop the guard tripping over a rule it is quoting.

    Verified failing: appending the marker to a bare sentence asserting the
    ledger is immutable fails here with the file and line.
    """
    offenders = []
    surfaces = [(d, os.path.join(REPO, d)) for d in CLAIM_DOCS]
    tpl = os.path.join(REPO, "console", "templates")
    surfaces += [(f"console/templates/{n}", os.path.join(tpl, n))
                 for n in sorted(os.listdir(tpl))]

    for label, path in surfaces:
        if not os.path.exists(path):
            continue
        # A bullet under "## Forbidden claims / ### Feasibility" inherits the
        # prohibition from the section, not from the nearest heading, so the
        # most recent heading at EACH level counts as context. Requiring every
        # bullet to restate "never" would be worse prose for no extra safety.
        headings: dict[int, str] = {}
        with open(path) as f:
            for i, line in enumerate(f, 1):
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    level = len(stripped) - len(stripped.lstrip("#"))
                    headings[level] = line.lower()
                    # A new heading at this level ends any deeper section.
                    headings = {k: v for k, v in headings.items() if k <= level}
                if lexicon.EXEMPT_MARKER not in line:
                    continue
                context = line.lower() + " " + " ".join(headings.values())
                if not any(cue in context for cue in _PROHIBITION_CUES):
                    offenders.append(f"{label}:{i}: {line.strip()[:90]}")

    assert not offenders, (
        "the lexicon exemption marker is silencing an assertion rather than "
        "excusing a quotation:\n  " + "\n  ".join(offenders)
        + "\nAn exempted line must be forbidding the phrase, not making the claim."
    )


def test_no_template_is_exempted_at_all():
    """Templates render claims to humans and never forbid anything.

    Separate from the rule above because the argument is different: a page has
    no reason to quote a banned phrase, so a marker in one is always a silenced
    violation regardless of what else is on the line.
    """
    tpl = os.path.join(REPO, "console", "templates")
    offenders = [n for n in sorted(os.listdir(tpl))
                 if lexicon.EXEMPT_MARKER in open(os.path.join(tpl, n)).read()]
    assert not offenders, (
        f"templates carry a lexicon exemption: {offenders}. A rendered page "
        "makes claims; it does not forbid them."
    )
