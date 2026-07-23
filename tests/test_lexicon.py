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
#
# Derived from the app's own url_map rather than typed out. The list that stood
# here was written once and never edited: /redline/confirm, the receipt the demo
# script ends on, was never in it, and every /workspace stage was added two
# commits later and never added. Forbidden language rendered on all of them with
# the whole suite green. A hand-maintained list of pages fails open, and this one
# did, for thirty-one commits.
#
# Every rule must be scanned or named here with a reason. Nothing falls through.
NON_CLAIM_ROUTES = {
    "/": "302 to the Rocket detail, renders no prose of its own",
    "/demo": "302 to the Rocket detail, renders no prose of its own",
    "/static/<path:filename>": "Flask builtin, serves files rather than claims",
    # POST-only surfaces. They render templates rather than new prose, and the
    # template scan below covers every stage of each, including the stages no
    # GET can reach.
    "/redline/decide": "POST only, redirects; template scan covers confirm.html",
    "/workspace/discover": "POST only; template scan covers workspace.html",
    "/workspace/select": "POST only; template scan covers workspace.html",
    "/workspace/approve": "POST only; template scan covers workspace.html",
}

# Rules taking a parameter, given every value the frozen snapshot carries. The
# old list scanned two of four tickers, so prose driven by the other two rows
# was never read.
PARAMETERISED = {
    "/contract/<ticker>": ["/contract/RCKT", "/contract/BEAM",
                           "/contract/PRME", "/contract/SRPT"],
}

TEMPLATE_DIR = os.path.join(REPO, "console", "templates")


def _get_pages() -> list[str]:
    pages: list[str] = []
    for rule in flask_app.url_map.iter_rules():
        r = str(rule.rule)
        if r in NON_CLAIM_ROUTES or "GET" not in (rule.methods or set()):
            continue
        pages.extend(PARAMETERISED.get(r, [r]))
    return sorted(set(pages))


PAGES = _get_pages()

# Documents that make claims on the project's behalf. LIMITS.md and this file's
# own source are excluded: both quote banned phrases constantly, by design.
CLAIM_DOCS = ["README.md", "docs/SUBMISSION.md", "docs/DEMO.md",
              "docs/PRINCIPLE.md", "docs/WORKSPACE.md", "docs/BACKTEST.md",
              # The cohort write-up is the most claim-dense document here and the
              # one most likely to be read on its own, so it is enforced like a
              # rendered page rather than trusted like a working note. It caught
              # two violations in the first draft.
              "docs/WRITEUP.md",
              # The UI contract states what each screen may and may not assert,
              # so it makes claims on the product's behalf like any other.
              "docs/UI.md"]


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


def test_every_route_is_scanned_or_named_as_exempt():
    """The control that cannot silently omit a newly added page.

    Keyed on the url_map, so adding a route without deciding whether it is
    claim-bearing fails here rather than going unscanned. This is the check that
    was missing while /redline/confirm and /workspace went unread.
    """
    rules = {str(r.rule) for r in flask_app.url_map.iter_rules()}
    scanned = set()
    for rule, expanded in PARAMETERISED.items():
        if set(expanded) & set(PAGES):
            scanned.add(rule)
    scanned |= {p for p in PAGES if p in rules}
    unaccounted = rules - scanned - set(NON_CLAIM_ROUTES)
    assert not unaccounted, (
        "these routes are neither scanned nor named in NON_CLAIM_ROUTES: "
        f"{sorted(unaccounted)}"
    )


def test_no_template_makes_a_forbidden_claim():
    """Keyed on files, not routes.

    A template reachable only by POST, or only in one stage of a multi-stage
    page, or not yet wired to a route at all, is still read. The receipt, every
    workspace stage and the belief form's review and done stages were all
    invisible to a route-keyed scan, and a planted 'immutable' rendered on each
    of them with the suite green.
    """
    offenders = {}
    for name in sorted(os.listdir(TEMPLATE_DIR)):
        if not name.endswith(".html"):
            continue
        with open(os.path.join(TEMPLATE_DIR, name)) as f:
            violations = lexicon.scan(f.read())
        if violations:
            offenders[name] = violations
    assert not offenders, "templates make claims the evidence does not support:\n" + "\n".join(
        f"  {n}: " + "; ".join(str(v) for v in vs) for n, vs in offenders.items()
    )


# ---------------------------------------------------------------------------
# The stages no GET can reach
# ---------------------------------------------------------------------------
# Scanning routes reads whatever a GET renders. The receipt, the belief form's
# review and done stages, and every workspace stage past the first are reachable
# only by POST, so a route list reads the shell and never the page the analyst
# actually decides on. Each one is driven here for real, against the rendered
# body, because that is the text a human reads.

_THESIS = ("Rocket Pharmaceuticals reaches the registered primary completion of "
           "NCT06092034 before its runway is exhausted, with a non-negative gap.")


def _scan_body(resp, label):
    assert resp.status_code == 200, f"{label} returned {resp.status_code}"
    violations = lexicon.scan(resp.data.decode())
    assert not violations, (
        f"{label} makes a claim the evidence does not support:\n  "
        + "\n  ".join(str(v) for v in violations)
    )


def _isolated_client(tmp_path, monkeypatch):
    """A client whose writes land in tmp_path, never in data/."""
    monkeypatch.setattr("console.app.DECISIONS_PATH", str(tmp_path / "decisions.jsonl"))
    monkeypatch.setattr("console.app.REVIEW_LOG_PATH", str(tmp_path / "review_log.jsonl"))
    monkeypatch.setattr("console.app.ANCHOR_PATH", str(tmp_path / "ledger.anchor"))
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


def test_belief_review_stage_makes_no_forbidden_claim(client):
    r = client.post("/belief/new", data={
        "stage": "review", "ticker": "RCKT", "nct": "NCT06092034",
        "thesis": _THESIS, "invalidation": "the gap falls below zero",
        "min_gap": "0"})
    _scan_body(r, "POST /belief/new stage=review")


def test_belief_completion_stage_makes_no_forbidden_claim(tmp_path, monkeypatch):
    c = _isolated_client(tmp_path, monkeypatch)
    r = c.post("/belief/new", data={
        "stage": "commit", "ticker": "RCKT", "nct": "NCT06092034",
        "thesis": _THESIS, "invalidation": "the gap falls below zero",
        "min_gap": "0"})
    _scan_body(r, "POST /belief/new stage=commit")


def test_workspace_discover_stage_makes_no_forbidden_claim(client):
    r = client.post("/workspace/discover", data={"ticker": "RCKT"})
    _scan_body(r, "POST /workspace/discover")


def test_workspace_review_stage_makes_no_forbidden_claim(client):
    r = client.post("/workspace/select",
                    data={"ticker": "RCKT", "nct": "NCT06092034"})
    _scan_body(r, "POST /workspace/select")


def test_workspace_approval_stage_makes_no_forbidden_claim(tmp_path, monkeypatch):
    c = _isolated_client(tmp_path, monkeypatch)
    r = c.post("/workspace/approve", data={
        "ticker": "RCKT", "nct": "NCT06092034", "claim": _THESIS, "min_gap": "0"})
    _scan_body(r, "POST /workspace/approve")


def test_the_receipt_makes_no_forbidden_claim(tmp_path, monkeypatch):
    """The page the demo script ends on, and the one the old list never read."""
    c = _isolated_client(tmp_path, monkeypatch)
    c.post("/redline/decide", data={"verdict": "approve", "reason": "the date lapsed"})
    _scan_body(c.get("/redline/confirm?verdict=approve"),
               "GET /redline/confirm after an approval")


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
