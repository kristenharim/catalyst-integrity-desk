"""The Narrow Evidence Explorer, as rendered.

One screen with one job: take a figure the console displays and show the record
it came from, the calculation that produced it, and the point where the chain
stops. What these tests are actually for:

  1. **Identity.** A page addressed by a contract or decision id must render
     that contract's evidence and no other's. The receipt spent a commit
     learning this lesson through a hash; an evidence page reached by the wrong
     ticker would publish one company's XBRL tags under another company's name.
  2. **The three provenance states cannot blur.** `source_linked` is the only
     one that asserts a link, and it is minted in exactly one function. The
     upgrade path is what has to be impossible, so it is asserted twice: over
     every input combination, and structurally over the module's syntax tree.
  3. **A missing source reads as missing.** The bundle is removed, a stored
     field is deleted, and a stored byte is edited. Each has a different honest
     answer and none of them is a link.
  4. **Negative results stay on the page.** A query that ran and found nothing
     is evidence, and a screen that goes quiet about it reads exactly like one
     whose evidence held.
  5. **The scope language holds.** The page may say what the artifact records.
     It may not say the thesis is verified, and it never calls a registered
     primary completion a readout date.
"""
from __future__ import annotations

import ast
import itertools
import json
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from console import provenance, review  # noqa: E402
from console.app import app as flask_app  # noqa: E402
from evidence import FrozenSnapshotProvider  # noqa: E402
from orchestrator import lexicon  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = REPO / "data" / "snapshot.json"
BUNDLE_DIR = REPO / "data" / "evidence"
TEMPLATE = REPO / "console" / "templates" / "evidence.html"
MODULE = REPO / "console" / "provenance.py"

TICKERS = ["RCKT", "PRME", "BEAM", "SRPT"]
STATES = [provenance.SOURCE_LINKED, provenance.NAMED_BUT_UNRESOLVED,
          provenance.UNAVAILABLE]

# The rendered tag, not the stylesheet rule that colours it. Asserting on the
# bare class name matched the `<style>` block, so "no link renders" passed on a
# page whose every field was linked.
LINK_TAG = 'class="prov prov-source_linked"'

# The scope statement the page is required to render, verbatim.
SCOPE = ("This page shows the evidence recorded in the committed artifact. It "
         "does not independently verify the underlying investment or scientific "
         "thesis.")


@pytest.fixture()
def client():
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


def _snapshot() -> dict:
    return json.loads(SNAPSHOT_PATH.read_text())


def _bundle(ticker: str) -> dict:
    return json.loads((BUNDLE_DIR / f"{ticker}.json").read_text())


def _with_bundle(tmp_path, monkeypatch, ticker: str, edit) -> None:
    """Serve one edited bundle to the route, leaving `data/evidence/` alone.

    Every fixture here mutates a copy. The committed bundles are the demo's
    evidence and a test that edited one would leave the repo describing
    something nobody fetched.
    """
    d = _bundle(ticker)
    edit(d)
    (tmp_path / f"{ticker}.json").write_text(json.dumps(d))
    monkeypatch.setattr("console.app.EVIDENCE", FrozenSnapshotProvider(str(tmp_path)))


def _text(html: str) -> str:
    """The rendered text, with style and script contents dropped."""

    class _T(HTMLParser):
        def __init__(self):
            super().__init__()
            self.skip = False
            self.chunks: list[str] = []

        def handle_starttag(self, tag, attrs):
            if tag in ("style", "script"):
                self.skip = True

        def handle_endtag(self, tag):
            if tag in ("style", "script"):
                self.skip = False

        def handle_data(self, data):
            if not self.skip:
                self.chunks.append(data)

    p = _T()
    p.feed(html)
    # Whitespace collapsed, because a sentence in the template wraps across
    # lines and a phrase assertion against the raw text would depend on where
    # the source happened to break it.
    return " ".join(" ".join(p.chunks).split())


def _section(html: str, element_id: str) -> str:
    start = html.find(f'id="{element_id}"')
    assert start != -1, f"the page has no element with id {element_id!r}"
    return html[start:html.find("<h2", start)]


# ---------------------------------------------------------------------------
# Identity and routing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ticker", TICKERS)
def test_a_contract_renders_its_own_evidence_and_no_other_contracts(client, ticker):
    """The identity assertion, both directions.

    Verified failing by resolving the id to the first contract in the snapshot
    regardless of the ticker: three of the four pages then name another
    company's CIK and this reports which.
    """
    snap = _snapshot()
    r = client.get(f"/evidence/{ticker}")
    assert r.status_code == 200
    body = r.get_data(as_text=True)

    mine = snap["contracts"][ticker]
    assert mine["runway"]["cik"] in body, "the page must name this contract's CIK"
    assert mine["trial"]["nct"] in body, "the page must name this contract's trial"
    assert mine["runway"]["name"] in body

    for other in TICKERS:
        if other == ticker:
            continue
        c = snap["contracts"][other]
        assert c["runway"]["cik"] not in body, (
            f"{ticker}'s evidence page carries {other}'s CIK")
        assert c["trial"]["nct"] not in body, (
            f"{ticker}'s evidence page carries {other}'s trial")
        assert c["runway"]["name"] not in body


def test_the_decision_id_resolves_the_same_contract_as_the_ticker(client):
    """Both shapes of decision identity reach one contract's evidence.

    The review screen addresses the one pending challenge by the card id the
    ledger and the receipt select by, and everything else by ticker. The
    explorer takes both, so the link between the screens is the same selection
    rather than a second way of naming a company.
    """
    card_id = _snapshot()["redline"]["card_id"]
    by_card = client.get(f"/evidence/{card_id}")
    by_ticker = client.get("/evidence/RCKT")
    assert by_card.status_code == by_ticker.status_code == 200

    card_body = by_card.get_data(as_text=True)
    assert "Evidence &middot; RCKT" in card_body
    assert _snapshot()["contracts"]["RCKT"]["runway"]["cik"] in card_body
    assert card_id in card_body, "the page must name the id it was asked for"
    # The two differ only in the id echoed back, not in the evidence shown.
    assert card_body.replace(card_id, "RCKT") == by_ticker.get_data(as_text=True)


@pytest.mark.parametrize("bad", ["ZZZZ", "nope:nope", "SANA", "rckt%20", "0"])
def test_an_unknown_id_is_an_honest_404(client, bad):
    """A miss, not the nearest contract.

    SANA is in the run: it has a committed evidence bundle and no contract,
    because the sponsor-name query returned nothing. There is no decision claim
    to trace for it, so the honest answer is that no contract with this id is
    here.
    """
    r = client.get(f"/evidence/{bad}")
    assert r.status_code == 404
    body = r.get_data(as_text=True)
    assert "No contract with this id is in this snapshot" in body
    for c in _snapshot()["contracts"].values():
        assert c["runway"]["cik"] not in body, (
            "a miss is rendering some contract's evidence")


@pytest.mark.parametrize("decision_id", [
    "rckt:funded_to_catalyst", "PRME", "SRPT", "BEAM"])
def test_decision_review_links_to_the_matching_evidence_route(client, decision_id):
    """One link, resolving the decision being viewed.

    Verified failing by pointing the href at the ticker instead of the decision
    id: the challenge's page then links to `/evidence/RCKT`, which resolves to
    the same contract by a different name, and this names the mismatch.
    """
    body = client.get(f"/decisions/{decision_id}/review").get_data(as_text=True)
    hrefs = re.findall(r'href="(/evidence/[^"]*)"', body)
    assert hrefs == [f"/evidence/{decision_id}"], (
        f"the review screen for {decision_id} links {hrefs}")

    evidence = client.get(hrefs[0])
    assert evidence.status_code == 200
    ticker = provenance.card_ticker(decision_id)
    assert f"Evidence &middot; {ticker}" in evidence.get_data(as_text=True)


# ---------------------------------------------------------------------------
# Provenance states
# ---------------------------------------------------------------------------

def test_source_linked_needs_the_stored_field_and_the_stored_value(client):
    """The committed bundle carries the tag and the figure, so the link holds."""
    body = client.get("/evidence/RCKT").get_data(as_text=True)
    assert LINK_TAG in body
    text = _text(body)
    assert "CashAndCashEquivalentsAtCarryingValue" in text
    assert "source linked" in text


def test_a_field_the_source_record_does_not_carry_is_named_not_resolved(
        tmp_path, monkeypatch, client):
    """Delete the value from the record and the link must not survive it.

    The XBRL tag is still named by the snapshot and the record is still there.
    What is gone is the only thing that made the figure traceable: the value on
    the record. That is `named_but_unresolved` by definition, and rendering it
    as a link would be the page asserting a resolution it did not perform.
    """
    def drop_cash(d):
        for rec in d["records"]:
            if rec["source"] == "sec.xbrl":
                rec["payload"].pop("cash")
        d.pop("digest")            # the bundle is re-derived, not forged

    _with_bundle(tmp_path, monkeypatch, "RCKT", drop_cash)
    body = client.get("/evidence/RCKT").get_data(as_text=True)
    assert 'class="prov prov-named_but_unresolved"' in body

    view = provenance.explorer(_snapshot(), "RCKT",
                               FrozenSnapshotProvider(str(tmp_path)))
    sec = next(s for s in view["sources"] if s["key"] == "sec.xbrl")
    cash = next(f for f in sec["fields"] if f["label"] == "Cash")
    assert cash["state"] == provenance.NAMED_BUT_UNRESOLVED
    assert sec["state"] == provenance.NAMED_BUT_UNRESOLVED, (
        "a record folds to its weakest field, never to its strongest")
    step = next(s for s in view["steps"] if s["step"] == "Cash")
    assert step["state"] == provenance.NAMED_BUT_UNRESOLVED, (
        "the derivation step inherits the state of the record it cites")


def test_a_missing_bundle_renders_unavailable_and_never_source_linked(
        tmp_path, monkeypatch, client):
    """No record, no field, no identity: the whole chain reads unavailable.

    The derivation is still shown, because it is committed and hiding it would
    hide the hard case. What it does not do is keep claiming its inputs are
    linked to records that are not there.
    """
    monkeypatch.setattr("console.app.EVIDENCE", FrozenSnapshotProvider(str(tmp_path)))
    body = client.get("/evidence/RCKT").get_data(as_text=True)
    assert LINK_TAG not in body, (
        "no link may render when there is no source record to link to")
    assert 'class="prov prov-unavailable"' in body
    assert "no committed evidence bundle is stored for RCKT" in body
    # The committed derivation is still on the page.
    assert "CashAndCashEquivalentsAtCarryingValue" in body
    assert "-14.5 months" in body

    view = provenance.explorer(_snapshot(), "RCKT",
                               FrozenSnapshotProvider(str(tmp_path)))
    assert {s["state"] for s in view["sources"]} == {provenance.UNAVAILABLE}
    assert provenance.SOURCE_LINKED not in {s["state"] for s in view["steps"]}


def test_an_edited_bundle_is_refused_rather_than_read(tmp_path, monkeypatch, client):
    """A stored byte is changed and the content address no longer recomputes.

    The bundle is not partially trusted. Its digest covers the payloads, so an
    edited file is not evidence of what it says it is, and the page reports that
    instead of resolving figures against it.
    """
    def bump_cash(d):
        for rec in d["records"]:
            if rec["source"] == "sec.xbrl":
                rec["payload"]["cash"] += 1.0      # digest deliberately left alone

    _with_bundle(tmp_path, monkeypatch, "RCKT", bump_cash)
    body = client.get("/evidence/RCKT").get_data(as_text=True)
    assert "digest mismatch" in body
    assert LINK_TAG not in body


def test_a_negative_result_is_rendered_and_never_dropped(
        tmp_path, monkeypatch, client):
    """A query that ran and found nothing is evidence, and it stays visible.

    Verified failing by rendering `negatives` only when the bundle is
    incomplete: the entry disappears and the page reads as though every query
    returned something.
    """
    def add_negative(d):
        d["negatives"].append({
            "source": "clinicaltrials.versions",
            "locator": "NCT06092034",
            "fetched_at": "2026-07-21T00:00:00+00:00",
            "reason": "version history returned zero revisions",
        })
        d.pop("digest")

    _with_bundle(tmp_path, monkeypatch, "RCKT", add_negative)
    text = _text(client.get("/evidence/RCKT").get_data(as_text=True))
    assert "version history returned zero revisions" in text
    assert "Queries that ran and returned nothing" in text


def test_the_empty_negative_list_is_not_reported_as_nothing_queried(client):
    """Empty is not the same fact as never asked, and the page says which.

    Both read as an empty list if only findings are stored, which is the exact
    failure `evidence/snapshot.py` records negatives to prevent. The page has to
    carry the distinction in words, because there is nothing to render.
    """
    text = _text(client.get("/evidence/RCKT").get_data(as_text=True))
    assert "Every source query recorded in this bundle returned a record" in text
    assert "different fact from a source that was never reached" in text
    assert "were never queried here" in text, (
        "the never-queried dimensions must be listed as well as the empty ones")


def test_only_one_function_can_produce_the_strongest_state():
    """Structural, over the module's own syntax tree.

    A second place to mint `source_linked` is a second place for a guess to be
    promoted into a link, and it would be invisible in a diff that only added a
    branch. Read from the tree rather than from a grep so a reformatted return
    statement cannot switch the check off.

    Verified failing two ways, because there are two: returning the constant
    from a second function, and passing it to the tag formatter without
    deciding it. Any mention of the name outside `_state` fails here, so both
    shapes and the ones nobody has thought of are caught by the same rule. The
    module-level constant and the two label maps are outside any function and
    are unaffected.
    """
    src = MODULE.read_text()
    offenders = []
    for fn in ast.walk(ast.parse(src)):
        if not isinstance(fn, ast.FunctionDef) or fn.name == "_state":
            continue
        for node in ast.walk(fn):
            if (isinstance(node, ast.Name)
                    and node.id == provenance.SOURCE_LINKED.upper()):
                offenders.append(f"{fn.name}:{node.lineno}")
    assert not offenders, (
        "these functions name the strongest provenance state without going "
        f"through _state: {offenders}. Returning it, assigning it or passing it "
        "to a formatter are the same defect by three routes")
    assert src.count('"source_linked"') == 1, (
        "the literal 'source_linked' appears more than once, so a state can be "
        "typed rather than decided")


def test_the_state_rule_has_no_upgrade_path():
    """Every input combination, and the fold across a record's fields.

    `_state` may only return the strongest state when all three of its
    conditions hold, and `_weakest` may only return a state it was given. Both
    directions matter: a rule that never says `source_linked` would pass the
    first half alone.
    """
    for record, field, value in itertools.product([True, False], repeat=3):
        state = provenance._state(record, field, value)
        assert state in STATES
        if state == provenance.SOURCE_LINKED:
            assert record and field and value
        if not record:
            assert state == provenance.UNAVAILABLE
    assert provenance._state(True, True, True) == provenance.SOURCE_LINKED

    for combo in itertools.product(STATES, repeat=3):
        folded = provenance._weakest(list(combo))
        assert folded in combo, "the fold invented a state no field carried"
        if folded == provenance.SOURCE_LINKED:
            assert set(combo) == {provenance.SOURCE_LINKED}
    assert provenance._weakest([]) == provenance.UNAVAILABLE


@pytest.mark.parametrize("ticker", TICKERS)
def test_every_provenance_state_on_the_page_is_one_of_the_three(client, ticker):
    body = client.get(f"/evidence/{ticker}").get_data(as_text=True)
    rendered = set(re.findall(r'class="prov prov-([a-z_]+)"', body))
    assert rendered, "the page renders no provenance state at all"
    assert rendered <= set(STATES), f"{ticker} renders states outside the three: {rendered}"


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ticker", TICKERS)
def test_every_number_on_the_page_comes_from_a_committed_artifact(client, ticker):
    """The provenance invariant, extended to this page.

    Two artifacts are allowed because the page reads two: the snapshot for every
    displayed figure, and the evidence bundle for the record identities,
    timestamps and version numbers it cites. Nothing may be computed in the view
    layer.

    Failure verification: a hardcoded '9999' added to the displayed-result panel
    is named here as a token in neither file.
    """
    # The two content addresses are the identities of the artifacts themselves,
    # hashed from committed bytes at render time, so they are not inside either
    # file and are not figures. Named here rather than skipped, so a third
    # unexplained number still fails.
    allowed = (SNAPSHOT_PATH.read_text()
               + (BUNDLE_DIR / f"{ticker}.json").read_text()
               + review.snapshot_digest(str(SNAPSHOT_PATH)))
    text = _text(client.get(f"/evidence/{ticker}").get_data(as_text=True))
    for token in re.findall(r"-?\d+(?:\.\d+)?", text):
        assert token in allowed, (
            f"number token {token!r} on GET /evidence/{ticker} is in neither the "
            "snapshot nor the evidence bundle; it was computed in the view layer")


def test_the_template_does_no_arithmetic():
    """No computation in the template, asserted on the template.

    Every figure is a preformatted field. A `| length` or a `+` in a Jinja
    expression is the view layer computing, which is how a number reaches a page
    without a field behind it.
    """
    offenders = []
    for expr in re.findall(r"\{\{(.*?)\}\}|\{%(.*?)%\}", TEMPLATE.read_text(), re.S):
        body = (expr[0] or expr[1]).strip().strip("-").strip()
        if re.search(r"[+*/]|\s-\s|\|\s*(length|sum|count|int|float|round)\b", body):
            offenders.append(body[:70])
    assert not offenders, f"the evidence template computes: {offenders}"


def test_the_unreliable_row_shows_no_gap_and_no_rank(client):
    """SRPT: the funding gap is withheld, and nothing ranks it.

    The row is shown, because a screen that hides its hard cases is worse than
    one that shows them. What it does not do is print a figure computed over an
    input this desk has flagged, or a position implying the row is comparable
    with the others.
    """
    snap = _snapshot()
    body = client.get("/evidence/SRPT").get_data(as_text=True)
    panel = _text(_section(body, "displayed-result"))

    assert "not rankable" in panel
    assert snap["contracts"]["SRPT"]["gap_months_1f"] not in panel, (
        "the gap of an unreliable row is displayed as if it were usable")
    assert "flagged unusable" in panel
    # And nothing composite is offered in its place. The row says it is not
    # rankable; it does not get a score, a grade or a percentile instead.
    for word in ("score", "grade", "percentile", "out of"):
        assert word not in panel.lower(), (
            f"the withheld row is given a {word!r} instead of a figure")


def test_the_derivation_of_an_unreliable_row_is_shown_under_its_refusal(client):
    """The steps stay, and the reason not to read the last one comes first."""
    body = client.get("/evidence/SRPT").get_data(as_text=True)
    text = _text(body)
    assert "ShortTermInvestments" in text, "the derivation must still be shown"
    refusal = text.find("flagged unusable")
    gap = text.find("2.6 months")
    assert refusal != -1 and gap != -1
    assert refusal < gap, (
        "the withheld figure appears before the reason it is withheld")


def test_a_refused_comparison_stays_refused(client):
    """The refusal is rendered above the magnitude it refuses, and heavier.

    Reversing that order is how a refused figure gets quoted as a finding.
    """
    body = client.get("/evidence/RCKT").get_data(as_text=True)
    text = _text(body)
    label = text.find("Comparison refused")
    figure = text.find("943 days reported")
    assert label != -1, "the refused comparison must render"
    assert figure != -1, "the refused magnitude must be shown, not hidden"
    assert label < figure, "the refusal must precede the reading it refuses"
    assert "not to be read as delay" in text

    refusal = re.search(r"\.refusal\s*\{([^}]*)\}", body).group(1)
    refused = re.search(r"\.refused-figure\s*\{([^}]*)\}", body).group(1)
    assert "font-weight: 700" in refusal
    assert "font-weight" not in refused


def test_the_lapsed_date_is_kept_and_never_a_catalyst(client):
    """A lapsed completion is surfaced as a date-integrity signal, not a target."""
    text = _text(client.get("/evidence/RCKT").get_data(as_text=True))
    assert "NCT04248439" in text
    assert "never a catalyst" in text
    assert "date-integrity signal" in text


# ---------------------------------------------------------------------------
# Scope language
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ticker", TICKERS)
def test_the_scope_statement_is_visible(client, ticker):
    body = client.get(f"/evidence/{ticker}").get_data(as_text=True)
    assert SCOPE in " ".join(_text(body).split()), (
        "the scope statement must be rendered on the page, not implied by it")


# Words that would turn this page from a record of evidence into a verdict on
# it. "verify" survives in the negative, inside the scope statement above.
FORBIDDEN_WORDS = ["verified", "verifies", "verification", "proven", "proves",
                   "confirms", "credible", "readout date", "validated"]


@pytest.mark.parametrize("ticker", TICKERS)
def test_the_page_claims_no_verification(client, ticker):
    text = " ".join(_text(client.get(f"/evidence/{ticker}").get_data(as_text=True))
                    .lower().split())
    present = [w for w in FORBIDDEN_WORDS
               if re.search(r"\b" + w.replace(" ", r"\s+") + r"\b", text)]
    assert not present, (
        f"/evidence/{ticker} claims {present}; the page shows the evidence chain "
        "and does not rule on the thesis")
    assert not re.search(r"\btrue\b", text), (
        "nothing on this page is established as true; it is a record comparison")


@pytest.mark.parametrize("ticker", TICKERS)
def test_the_page_makes_no_forbidden_claim(client, ticker):
    violations = lexicon.scan(
        client.get(f"/evidence/{ticker}").get_data(as_text=True))
    assert not violations, "\n  ".join(str(v) for v in violations)


def test_the_page_states_what_the_evidence_does_not_establish(client):
    text = _text(client.get("/evidence/RCKT").get_data(as_text=True))
    assert "does not establish whether the underlying science is sound" in text
    assert "registered primary-completion" in text
    assert "not the date a result is published" in text


# ---------------------------------------------------------------------------
# Route compatibility: nothing around this screen moved
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("route", [
    "/inbox", "/activity", "/redline", "/queue", "/contracts",
    "/contract/RCKT", "/decisions/rckt:funded_to_catalyst/review",
    "/decisions/SRPT/review", "/receipts/no-entry-with-this-id",
    "/redline/confirm", "/belief/new", "/workspace"])
def test_the_routes_around_the_explorer_still_render(client, route):
    assert client.get(route).status_code == 200, f"{route} no longer renders"


def test_the_demo_entry_points_are_unmoved(client):
    for route in ("/", "/demo"):
        r = client.get(route)
        assert r.status_code == 302 and "/contract/RCKT" in r.headers["Location"]


def test_the_redline_still_serves_the_decision_form(client):
    body = client.get("/redline").get_data(as_text=True)
    assert 'action="/redline/decide"' in body
    assert "/evidence/" not in body, (
        "the pending challenge page was not part of this screen's scope")
