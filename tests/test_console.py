"""Tests for the Catalyst Integrity Desk console.

No live server needed — uses Flask app.test_client().
No network access — all data comes from data/snapshot.json.

Number-provenance invariant (spec sub-task 6, step 8)
------------------------------------------------------
Before finalising this suite, a literal "9999" was temporarily added to a
<td> in detail.html and the provenance test was run. It failed with:

    AssertionError: number token '9999' from GET /contract/RCKT not in snapshot

The hardcoded value was then removed. A provenance check that has never been
seen failing is not evidence of anything.

Badge-tamper test (Prompt 3 repair, item 1)
-------------------------------------------
Before adding the fix to redline_confirm, this test was run and failed with:

    AssertionError: badge should read 'tampered' after a hashed byte is edited

That confirmed the confirm handler was reading intact from the query string
rather than calling verify() itself.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from html.parser import HTMLParser

import pytest

# Ensure the repo root is importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from console.app import app as flask_app, DECISIONS_PATH

SNAPSHOT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "snapshot.json")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture(scope="session")
def snapshot_raw() -> str:
    """Raw snapshot JSON as a string — used for substring matching."""
    with open(SNAPSHOT_PATH) as f:
        return f.read()


# ---------------------------------------------------------------------------
# Routing tests
# ---------------------------------------------------------------------------

def test_root_redirects_to_rckt(client):
    """GET / must redirect to /contract/RCKT — demo-opening constraint."""
    r = client.get("/")
    assert r.status_code == 302
    assert "/contract/RCKT" in r.headers["Location"]


def test_contracts_200(client):
    r = client.get("/contracts")
    assert r.status_code == 200
    assert "text/html" in r.content_type


def test_contract_rckt_200(client):
    r = client.get("/contract/RCKT")
    assert r.status_code == 200
    assert "text/html" in r.content_type


def test_redline_200(client):
    r = client.get("/redline")
    assert r.status_code == 200
    assert "text/html" in r.content_type


# ---------------------------------------------------------------------------
# Demo-critical content
# ---------------------------------------------------------------------------

def test_rckt_detail_contains_677(client):
    """The 677-day expired-date row must appear in the rendered RCKT page."""
    r = client.get("/contract/RCKT")
    assert b"677" in r.data


def test_rckt_detail_carried_expired_marker(client):
    """The CSS class 'carried-expired' must be present on the expired node."""
    r = client.get("/contract/RCKT")
    assert b"carried-expired" in r.data


def test_redline_memo_says_granite(client):
    """The memo must confirm Granite authorship and must not contain 'stub'."""
    r = client.get("/redline")
    text = r.data.decode()
    assert "granite" in text.lower(), "redline page must reference Granite authorship"
    assert "stub" not in text.lower(), "redline page must not contain 'stub'"


# ---------------------------------------------------------------------------
# Number-provenance invariant
# ---------------------------------------------------------------------------

class _TextCollector(HTMLParser):
    """Walk all text nodes (not attribute values) and collect visible text."""

    def __init__(self):
        super().__init__()
        self._skip = False
        self.chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        # style and script content is not user-visible text.
        if tag in ("style", "script"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("style", "script"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self.chunks.append(data)


_TOKEN_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _visible_numbers(html: bytes) -> list[str]:
    """Extract every number-like token from the visible text of an HTML page."""
    parser = _TextCollector()
    parser.feed(html.decode())
    text = " ".join(parser.chunks)
    return _TOKEN_RE.findall(text)


# ---------------------------------------------------------------------------
# Integrity badge — tamper detection (Prompt 3 repair, item 1)
# ---------------------------------------------------------------------------

def test_badge_flips_on_tampered_ledger(tmp_path, monkeypatch):
    """POST a decision, tamper a byte inside the card payload (which the hash
    covers), reload /redline/confirm, and assert the badge reads 'tampered'.

    The verdict word lives in review_log.jsonl, not the ledger, so editing
    'approve' there changes nothing hashed and verify() stays True.  The tamper
    must touch something inside the 'card' payload of a ledger entry.
    """
    decisions_file = str(tmp_path / "decisions.jsonl")
    review_log_file = str(tmp_path / "review_log.jsonl")

    # Point the app at the temp files for this test.
    monkeypatch.setattr("console.app.DECISIONS_PATH", decisions_file)
    monkeypatch.setattr("console.app.REVIEW_LOG_PATH", review_log_file)

    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        # POST an approve decision to populate the ledger.
        resp = c.post("/redline/decide", data={"verdict": "approve", "reason": "test"})
        assert resp.status_code == 302
        assert "verdict=approve" in resp.headers["Location"]

        # Confirm page should show intact before tamper.
        # &#10007; is the cross (✗) shown only in the tampered badge span.
        # &#9888; is the warning (⚠) shown only in the truncated badge span.
        # Cannot assert "tampered" is absent from the page because the tamper demo
        # blockquote now contains that word as instructional text.
        resp = c.get("/redline/confirm?verdict=approve")
        assert b"intact" in resp.data
        assert b"&#10007;" not in resp.data, "intact state must not show cross (tampered) badge"
        assert b"&#9888;" not in resp.data, "intact state must not show warning (truncated) badge"

        # Tamper: change a character inside the card payload of the first ledger entry.
        # The verdict word is in review_log.jsonl, not here, so we must edit the card.
        with open(decisions_file) as f:
            lines = f.readlines()
        assert lines, "ledger should have at least one entry after approve"
        # Replace a digit in the first entry's card payload so the hash check fails.
        tampered = lines[0].replace('"version": 1', '"version": 2', 1)
        assert tampered != lines[0], "tamper must change something"
        with open(decisions_file, "w") as f:
            f.write(tampered)
            f.writelines(lines[1:])

        # Reload confirm — the handler must call verify() fresh, not trust the URL param.
        resp = c.get("/redline/confirm?verdict=approve")
        assert b"tampered" in resp.data, (
            "badge should read 'tampered' after a hashed byte is edited"
        )


# ---------------------------------------------------------------------------
# Flagged row — SRPT visible but unranked (Prompt 3 widening, item 3)
# ---------------------------------------------------------------------------

def test_contracts_flagged_section_contains_srpt(client):
    """SRPT must appear in the flagged section of /contracts."""
    r = client.get("/contracts")
    assert r.status_code == 200
    assert b"SRPT" in r.data, "/contracts must show SRPT in the flagged section"


def test_srpt_has_no_rank_number(client):
    """SRPT is unreliable and must not carry a rank number on /contracts.

    The ranked table uses loop.index (1, 2, 3, ...) in the Rank column.
    SRPT must appear in the flagged table, which has no Rank column.
    We verify this by checking the HTML: SRPT's row must not be preceded
    by a rank cell containing a digit within the same <tr>.

    Implementation: parse the page, find every <tr> that contains 'SRPT',
    and assert none of them also contains a lone digit that would be a rank.
    """
    from html.parser import HTMLParser as _HP

    class _TableParser(_HP):
        def __init__(self):
            super().__init__()
            self._in_tr = False
            self._cells: list[str] = []
            self._cur: list[str] = []
            self.srpt_rows: list[list[str]] = []  # all <tr> cells containing SRPT

        def handle_starttag(self, tag, attrs):
            if tag == "tr":
                self._in_tr = True
                self._cells = []
                self._cur = []

        def handle_endtag(self, tag):
            if tag == "td":
                self._cells.append("".join(self._cur).strip())
                self._cur = []
            elif tag == "tr":
                row_text = " ".join(self._cells)
                if "SRPT" in row_text:
                    self.srpt_rows.append(list(self._cells))
                self._in_tr = False

        def handle_data(self, data):
            if self._in_tr:
                self._cur.append(data)

    r = client.get("/contracts")
    p = _TableParser()
    p.feed(r.data.decode())
    assert p.srpt_rows, "SRPT must appear in at least one table row"
    for row in p.srpt_rows:
        # A rank cell is a cell whose stripped content is a plain integer.
        rank_cells = [c for c in row if c.isdigit()]
        assert not rank_cells, (
            f"SRPT row contains a rank cell {rank_cells!r} — "
            "unreliable rows must not be ranked"
        )


# /contract/BEAM is here for its sign: BEAM is the only reliable contract with a
# positive gap, so it is the only route that renders the "+" branch of
# _derivation.html. A literal planted in that branch went undetected until this
# route was added, because every other page takes the negative branch.
@pytest.mark.parametrize("route", ["/contract/RCKT", "/contract/BEAM", "/contracts",
                                   "/redline", "/queue"])
def test_number_provenance(client, snapshot_raw, route):
    """Every number visible in the rendered HTML must appear in snapshot.json.

    This is the mechanical check for the 'no number displayed to a user was
    computed in the view layer' invariant.  Attribute values (viewBox, r,
    stroke-width, etc.) are not text nodes and are not reached by the parser.
    SVG x positions are stored in the snapshot (sub-task 1) and pass on their
    own merit.

    Failure verification (performed before finalising — see module docstring):
    a literal '9999' was temporarily added to a <td> in detail.html and this
    test correctly failed, naming '9999' as the offending token on
    GET /contract/RCKT.
    """
    r = client.get(route)
    assert r.status_code == 200
    tokens = _visible_numbers(r.data)
    for token in tokens:
        assert token in snapshot_raw, (
            f"number token {token!r} from GET {route} not found in snapshot.json\n"
            f"(This means a number was computed or hardcoded in the view layer.)"
        )


# ---------------------------------------------------------------------------
# Snapshot staleness guard (Prompt 3, the breach moment, item 1)
# ---------------------------------------------------------------------------

def test_snapshot_no_lapsed_catalyst():
    """No contract in the snapshot may bind to a catalyst date in the past.

    The stale snapshot passed every existing test while reporting RCKT as
    'funded to catalyst' against NCT04248439 (registered primary completion
    2026-05-05, a date already in the past).  This check is the one that
    would have caught it.

    The engine's build() now enforces the same rule: it binds to the nearest
    registered primary completion still in the future and puts lapsed trials
    on contract.lapsed.  The snapshot must reflect that rule.

    Failure verification: this test was written before the snapshot was
    rebuilt.  With the stale snapshot it failed on RCKT with catalyst_date
    2026-05-05, which is in the past.
    """
    import datetime as _dt

    with open(SNAPSHOT_PATH) as f:
        snap = json.load(f)

    today = _dt.date.today().isoformat()
    for ticker, c in snap["contracts"].items():
        cat = c.get("catalyst_date")
        if cat is None:
            continue  # no catalyst is fine; no catalyst != past catalyst
        assert cat >= today, (
            f"{ticker} binds to catalyst_date {cat!r} which is in the past "
            f"(today is {today}).  The snapshot was built against a lapsed date "
            f"and must be regenerated."
        )

# ---------------------------------------------------------------------------
# Anchor tests (Prompt 3, the anchor: make deletion detectable)
# ---------------------------------------------------------------------------
# All three tests were written before record() was wired into the decision
# path.  Each failed as documented below; the fix was added afterward.
#
# test_badge_truncated_on_deleted_entry:
#   FAILED -- badge showed 'intact' after deleting the newest entry.
#   The confirm handler only called verify(), which returned True because
#   the shortened chain is internally valid.
#
# test_badge_truncated_on_replaced_chain:
#   FAILED -- badge showed 'intact' after replacing the whole file with a
#   fresh, internally valid chain (different head hash, same count).
#
# test_badge_tampered_not_truncated_on_byte_edit:
#   FAILED -- badge showed 'intact' rather than 'tampered'.
#   (Same root cause as test_badge_flips_on_tampered_ledger above; both
#   tests independently anchor the tampered path.)
#
# After wiring record() into redline_decide and switching the confirm handler
# to check(), all three pass.

def _post_approve(c, decisions_file, review_log_file, monkeypatch):
    """Helper: POST an approve decision and return the confirm-page location."""
    monkeypatch.setattr("console.app.DECISIONS_PATH", decisions_file)
    monkeypatch.setattr("console.app.REVIEW_LOG_PATH", review_log_file)
    resp = c.post("/redline/decide", data={"verdict": "approve", "reason": "test"})
    assert resp.status_code == 302
    return resp.headers["Location"]


def test_badge_truncated_on_deleted_entry(tmp_path, monkeypatch):
    """Delete the newest ledger entry; badge must report 'truncated or replaced',
    not 'intact'.  Deletion leaves a valid (shorter) chain so verify() returns
    True -- only the anchor catches it.
    """
    decisions_file = str(tmp_path / "decisions.jsonl")
    review_log_file = str(tmp_path / "review_log.jsonl")
    anchor_file = str(tmp_path / "ledger.anchor")
    monkeypatch.setattr("console.app.ANCHOR_PATH", anchor_file)

    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        _post_approve(c, decisions_file, review_log_file, monkeypatch)

        # Confirm intact before deletion.
        resp = c.get("/redline/confirm?verdict=approve")
        assert b"intact" in resp.data

        # Delete the newest (and only) entry from the ledger file.
        with open(decisions_file) as f:
            lines = f.readlines()
        assert len(lines) >= 2, "ledger should have at least 2 entries (seed + update)"
        with open(decisions_file, "w") as f:
            f.writelines(lines[:-1])   # drop the last entry

        # Reload confirm -- badge must say 'truncated or replaced'.
        resp = c.get("/redline/confirm?verdict=approve")
        assert b"truncated" in resp.data, (
            "badge must report 'truncated or replaced' after the newest entry is deleted"
        )
        assert b"intact" not in resp.data


def test_badge_truncated_on_replaced_chain(tmp_path, monkeypatch):
    """Replace the entire ledger file with a freshly built, internally valid
    chain; badge must report 'truncated or replaced', not 'intact'.

    This is the sharpest attack: a valid chain whose claim reads anything the
    attacker wants.  verify() accepts it; only the anchor catches it.
    """
    import time
    from engine.ledger import BeliefLedger, BeliefCard, GENESIS_HASH

    decisions_file = str(tmp_path / "decisions.jsonl")
    review_log_file = str(tmp_path / "review_log.jsonl")
    anchor_file = str(tmp_path / "ledger.anchor")
    monkeypatch.setattr("console.app.ANCHOR_PATH", anchor_file)

    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        _post_approve(c, decisions_file, review_log_file, monkeypatch)

        # Confirm intact before replacement.
        resp = c.get("/redline/confirm?verdict=approve")
        assert b"intact" in resp.data

        # Build a fresh valid chain in a separate file, then overwrite.
        fresh_file = str(tmp_path / "fresh.jsonl")
        fresh_ledger = BeliefLedger(fresh_file)
        fake_card = BeliefCard(
            card_id="RCKT-gap_months",
            scope="trial:NCT06092034",
            claim="Rocket is comfortably funded and no financing is required",
            metric="gap_months",
            expected_low=0.0,
            expected_high=20.0,
            driver="test",
            confidence=5,
            source="test",
            as_of="2026-01-01",
        )
        fresh_ledger.create(fake_card, author="attacker", ts=time.time())
        with open(fresh_file) as f:
            fresh_lines = f.readlines()
        with open(decisions_file, "w") as f:
            f.writelines(fresh_lines)

        # Reload confirm -- badge must say 'truncated or replaced'.
        resp = c.get("/redline/confirm?verdict=approve")
        assert b"truncated" in resp.data, (
            "badge must report 'truncated or replaced' after wholesale chain replacement"
        )
        assert b"intact" not in resp.data


def test_badge_tampered_not_truncated_on_byte_edit(tmp_path, monkeypatch):
    """Edit a byte inside a hashed payload; badge must report 'tampered' (not
    'truncated or replaced').  The two failure modes are distinct accusations
    and must be reported distinctly.

    The tamper demo blockquote contains the word 'truncated' as instructional
    text, so we check the badge span itself rather than the full page.
    """
    decisions_file = str(tmp_path / "decisions.jsonl")
    review_log_file = str(tmp_path / "review_log.jsonl")
    anchor_file = str(tmp_path / "ledger.anchor")
    monkeypatch.setattr("console.app.ANCHOR_PATH", anchor_file)

    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        _post_approve(c, decisions_file, review_log_file, monkeypatch)

        # Tamper a byte in the card payload.
        with open(decisions_file) as f:
            lines = f.readlines()
        tampered = lines[0].replace('"version": 1', '"version": 9', 1)
        assert tampered != lines[0]
        with open(decisions_file, "w") as f:
            f.write(tampered)
            f.writelines(lines[1:])

        resp = c.get("/redline/confirm?verdict=approve")
        assert b"tampered" in resp.data, (
            "badge must report 'tampered' when a hashed byte is edited"
        )
        # The badge must show 'tampered', not 'truncated or replaced'.
        # The blockquote also contains 'truncated' as instructional text, so
        # we confirm the badge span colour belongs to the tampered style
        # (red border #f85149) rather than the truncated style (amber #f59e0b).
        assert b"f85149" in resp.data, (
            "tampered badge must use red styling, not amber"
        )
        assert b"f59e0b" not in resp.data, (
            "badge must not show amber 'truncated or replaced' styling on a byte-edit tamper"
        )


# ---------------------------------------------------------------------------
# Forged-receipt test (Prompt 3, the receipt: read it from the ledger)
# ---------------------------------------------------------------------------
# Written before the fix.  With the fix absent the confirm handler reads
# receipt fields directly from the URL, so the page renders the forged author
# and entry_hash instead of the real ledger values.  Expected failure:
#
#   AssertionError: confirm page must show real author 'human:demo', not
#   forged 'nobody:forged'
#
# After the fix, redline_confirm ignores the receipt query parameter and
# builds the receipt from the ledger's last entry, so forged values never
# reach the rendered page.

def test_confirm_ignores_forged_receipt(tmp_path, monkeypatch):
    """POST a real approve, then request confirm with a forged receipt param.

    The page must show the ledger's real author and real entry_hash, not the
    forged values.  A receipt carried in the URL is not evidence of anything.
    """
    decisions_file = str(tmp_path / "decisions.jsonl")
    review_log_file = str(tmp_path / "review_log.jsonl")
    anchor_file = str(tmp_path / "ledger.anchor")
    monkeypatch.setattr("console.app.DECISIONS_PATH", decisions_file)
    monkeypatch.setattr("console.app.REVIEW_LOG_PATH", review_log_file)
    monkeypatch.setattr("console.app.ANCHOR_PATH", anchor_file)

    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        # POST a real approve to populate the ledger.
        resp = c.post("/redline/decide", data={"verdict": "approve", "reason": "test"})
        assert resp.status_code == 302

        # Read the real entry_hash from the ledger so we can assert against it.
        import json as _json
        with open(decisions_file) as f:
            lines = [l for l in f if l.strip()]
        real_entry = _json.loads(lines[-1])
        real_hash = real_entry["entry_hash"]
        real_author = real_entry["author"]

        # Craft a confirm URL with completely forged receipt values.
        forged_receipt = _json.dumps({
            "author": "nobody:forged",
            "ts_display": "1970-01-01 00:00:00 UTC",
            "card_id": "FAKE-card",
            "what_changed": "nothing",
            "thesis_state": "funded to catalyst, no financing required",
            "prev_hash": "deadbeef" * 8,
            "entry_hash": "deadbeef" * 8,
        })
        resp = c.get(f"/redline/confirm?verdict=approve&receipt={forged_receipt}")
        assert resp.status_code == 200
        text = resp.data.decode()

        # The page must show the real author and real hash, not the forged ones.
        assert real_author in text, (
            f"confirm page must show real author {real_author!r}, not forged 'nobody:forged'"
        )
        assert real_hash in text, (
            f"confirm page must show real entry_hash from the ledger"
        )
        assert "nobody:forged" not in text, (
            "confirm page must not render a forged author from the URL"
        )
        assert "deadbeef" * 8 not in text, (
            "confirm page must not render a forged hash from the URL"
        )


# ---------------------------------------------------------------------------
# Display strings must faithfully render the fields they label
# ---------------------------------------------------------------------------

def test_display_strings_match_their_sources(snapshot_raw):
    """Every display string recomputes from its own source value.

    The provenance test proves a rendered number came from the snapshot. It does
    not prove the string faithfully renders the field it labels, and those are
    different claims. Verified by mutation before this existed: setting
    prior_gap_months to 99.9 while the page still showed 8.4 left the whole suite
    green, as did setting runway.cash to 1.0 while the page still showed $50M.

    apply_displays() is the single writer of every display block, so recomputing
    it on a copy and comparing is the whole check. It uses the real formatters
    rather than reimplementing them, so the test cannot drift alongside the code.
    """
    import copy
    from console.make_snapshot import apply_displays

    committed = json.loads(snapshot_raw)
    recomputed = apply_displays(copy.deepcopy(committed))

    for ticker, c in committed["contracts"].items():
        assert c["runway"]["display"] == recomputed["contracts"][ticker]["runway"]["display"], (
            f"{ticker} runway display strings do not match their source values"
        )
        assert c.get("gap_months_1f") == recomputed["contracts"][ticker].get("gap_months_1f"), (
            f"{ticker} gap_months_1f does not match gap_months"
        )
        assert c.get("thesis_timeline") == recomputed["contracts"][ticker].get("thesis_timeline"), (
            f"{ticker} thesis_timeline does not match the runway and dates it draws"
        )
        assert c.get("derivation") == recomputed["contracts"][ticker].get("derivation"), (
            f"{ticker} derivation rows do not match the values they claim to derive"
        )

    r_committed, r_recomputed = committed.get("redline"), recomputed.get("redline")
    if r_committed:
        assert r_committed["breach"].get("display") == r_recomputed["breach"].get("display"), (
            "redline breach display strings do not match their source values"
        )
        assert r_committed.get("lapse_display") == r_recomputed.get("lapse_display"), (
            "lapse_display does not match prior_gap_months / current_gap_months"
        )

    assert committed.get("cmd_bar") == recomputed.get("cmd_bar"), (
        "command bar counts do not match the contracts they summarise"
    )


def test_unresolved_ticker_is_shown_not_dropped(client):
    """A monitored ticker that produces no contract must still reach the screen.

    SANA is in console.make_snapshot.TICKERS and has a reliable runway, but the
    sponsor-name search matches no trial, so build() returns None. It used to be
    dropped with only a line on stderr, which meant /contracts silently showed
    four of five requested tickers. A screen that hides its hard cases is worse
    than one that shows them, so it gets a row and a stated reason.
    """
    r = client.get("/contracts")
    assert r.status_code == 200
    body = r.data.decode()
    assert "SANA" in body, "/contracts must show SANA rather than dropping it"
    assert "no pivotal trial matched" in body, (
        "/contracts must say why SANA produced no contract, not just list it"
    )


def test_every_monitored_ticker_appears_on_contracts(client):
    """Nothing in TICKERS may vanish from /contracts without appearing somewhere.

    Ranked, flagged, or unresolved: every requested ticker lands in one of the
    three sections. This is the general form of the SANA bug, so a sixth ticker
    added later cannot reintroduce it silently.
    """
    from console.make_snapshot import TICKERS

    body = client.get("/contracts").data.decode()
    missing = [t for t in TICKERS if t not in body]
    assert not missing, f"tickers requested but absent from /contracts: {missing}"


# ---------------------------------------------------------------------------
# Thesis-break timeline
# ---------------------------------------------------------------------------
# The timeline is the one picture a viewer is expected to read the conclusion
# off, so it needs its own binding to the engine's numbers.  Verified by
# mutation before it was trusted: setting the timeline's catalyst gap_1f to
# "-99.9" in the committed snapshot failed test_timeline_agrees_with_contract,
# and deleting the lapsed marker failed test_rckt_timeline_shows_the_flip.


def test_timeline_agrees_with_contract():
    """Every timeline figure must equal the contract figure it draws.

    The timeline recomputes the exhaustion date and the lapsed-anchor gap from
    raw fields rather than copying the contract's own strings.  That is
    deliberate -- an independent recomputation that disagrees is a real defect,
    not a formatting difference -- so it has to be asserted rather than assumed.
    """
    with open(SNAPSHOT_PATH) as f:
        snap = json.load(f)

    drawn = 0
    for ticker, c in snap["contracts"].items():
        tl = c.get("thesis_timeline")
        if tl is None:
            continue
        drawn += 1
        assert tl["catalyst"]["gap_1f"] == c["gap_months_1f"], (
            f"{ticker} timeline draws gap {tl['catalyst']['gap_1f']} but the "
            f"contract computes {c['gap_months_1f']}"
        )
        assert tl["catalyst"]["date"] == c["catalyst_date"], (
            f"{ticker} timeline binds to a different date than the contract"
        )
        assert tl["catalyst"]["nct"] == c["trial"]["nct"]
        # A negative gap must be drawn as short, and a positive one must not be.
        assert tl["short"] == (c["gap_months"] < 0), (
            f"{ticker} timeline's shortfall styling disagrees with the sign of the gap"
        )
        # Markers must land inside the frame the axis defines.
        for name, x in (("filing", tl["filing"]["x"]), ("today", tl["today"]["x"]),
                        ("catalyst", tl["catalyst"]["x"]),
                        ("exhaustion", tl["runway"]["x_lo"])):
            assert tl["x0"] <= x <= tl["x1"], f"{ticker} {name} marker at {x} is off the axis"
    assert drawn, "no contract produced a thesis timeline"


def test_rckt_timeline_shows_the_flip():
    """RCKT's timeline must carry both sides of the conclusion: the lapsed
    anchor the thesis used to read positive against, and the binding date it
    reads negative against.  Showing only one of them loses the point.
    """
    with open(SNAPSHOT_PATH) as f:
        snap = json.load(f)
    tl = snap["contracts"]["RCKT"]["thesis_timeline"]
    assert tl["lapsed"] is not None, "RCKT timeline must show the lapsed anchor"
    assert tl["lapsed"]["gap_1f"] == snap["redline"]["lapse_display"]["prior_gap_1f"], (
        "the timeline's lapsed-anchor gap must equal the redline's prior gap"
    )
    assert tl["catalyst"]["gap_1f"] == snap["redline"]["lapse_display"]["current_gap_1f"]
    assert tl["short"] is True


def test_rckt_detail_renders_timeline(client):
    """The markers must reach the page, not just the snapshot."""
    r = client.get("/contract/RCKT")
    assert b"binding-marker" in r.data
    assert b"lapsed-marker" in r.data


# ---------------------------------------------------------------------------
# Derivation: every displayed figure bound to a named record
# ---------------------------------------------------------------------------

def test_derivation_names_a_record_for_every_sourced_row():
    """Rows that claim a filing or a registry version must name it.

    'presence in the snapshot' is not provenance.  A row whose kind is 'tag' is
    asserting the figure came from a specific field of a specific record, so it
    has to carry that record.
    """
    with open(SNAPSHOT_PATH) as f:
        snap = json.load(f)
    for ticker, c in snap["contracts"].items():
        rows = c.get("derivation") or []
        assert rows, f"{ticker} has no derivation"
        for row in rows:
            assert row["source"], f"{ticker} derivation row {row['step']!r} names no source"
            if row["kind"] == "tag":
                assert row["record"], (
                    f"{ticker} row {row['step']!r} claims a tag but names no record"
                )


def test_derivation_gap_row_matches_the_contract():
    """The derivation's final row must state the contract's own gap."""
    with open(SNAPSHOT_PATH) as f:
        snap = json.load(f)
    for ticker, c in snap["contracts"].items():
        result = [r for r in (c.get("derivation") or []) if r["kind"] == "result"]
        if not result:
            continue
        assert result[-1]["value"] == f"{c['gap_months_1f']} months", (
            f"{ticker} derivation result row disagrees with gap_months_1f"
        )


def test_redline_exposes_the_derivation(client):
    """The headline figure on /redline must open onto its derivation."""
    r = client.get("/redline")
    text = r.data.decode()
    assert "came from, step by step" in text
    assert "CashAndCashEquivalentsAtCarryingValue" in text, (
        "/redline drawer must name the XBRL tag the cash figure resolved through"
    )


# ---------------------------------------------------------------------------
# Analyst belief entry
# ---------------------------------------------------------------------------

_GOOD_FORM = {
    "ticker": "RCKT",
    "nct": "NCT06092034",
    "thesis": ("Rocket reaches the registered primary completion of this trial "
               "before its cash runs out and does not need to finance first."),
    "invalidation": "any registered completion date moving later by a quarter or more",
    "min_gap": "0",
}


def test_belief_form_renders(client):
    r = client.get("/belief/new")
    assert r.status_code == 200
    assert b"Minimum acceptable funding gap" in r.data


def test_belief_review_writes_nothing(tmp_path, monkeypatch):
    """The review stage must not touch the ledger.  A form that commits on the
    way to showing you what it will commit is not a confirmation step.
    """
    decisions_file = str(tmp_path / "decisions.jsonl")
    monkeypatch.setattr("console.app.DECISIONS_PATH", decisions_file)
    monkeypatch.setattr("console.app.ANCHOR_PATH", str(tmp_path / "ledger.anchor"))
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        r = c.post("/belief/new", data={**_GOOD_FORM, "stage": "review"})
        assert r.status_code == 200
        assert b"Confirm and record this belief" in r.data
    assert not os.path.exists(decisions_file), "review stage must write no ledger entry"


def test_belief_commit_appends_to_ledger(tmp_path, monkeypatch):
    """Confirming writes one CREATE entry carrying the analyst's own words."""
    decisions_file = str(tmp_path / "decisions.jsonl")
    monkeypatch.setattr("console.app.DECISIONS_PATH", decisions_file)
    monkeypatch.setattr("console.app.ANCHOR_PATH", str(tmp_path / "ledger.anchor"))
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        r = c.post("/belief/new", data={**_GOOD_FORM, "stage": "commit"})
        assert r.status_code == 200
        assert b"Belief recorded" in r.data

    with open(decisions_file) as f:
        entries = [json.loads(line) for line in f if line.strip()]
    assert len(entries) == 1
    card = entries[0]["card"]
    assert entries[0]["event"] == "CREATE"
    assert entries[0]["author"] == "human:analyst"
    assert card["card_id"] == "rckt:nct06092034"
    assert card["scope"] == "NCT06092034"
    assert card["expected_low"] == 0.0
    # The invalidation conditions must travel with the claim: that text is what
    # a challenge gets judged against.
    assert "Invalidation conditions:" in card["claim"]
    assert "moving later by a quarter" in card["claim"]

    # The chain the entry joined must still verify.
    from engine.ledger import BeliefLedger
    assert BeliefLedger(decisions_file).verify() is True


@pytest.mark.parametrize("bad,expect", [
    ({"ticker": "ZZZZ"}, b"not monitored"),
    ({"nct": "not-a-trial"}, b"NCT06092034"),
    ({"thesis": "short"}, b"Write the thesis out"),
    ({"min_gap": "soon"}, b"must be a number"),
])
def test_belief_form_rejects_bad_input(tmp_path, monkeypatch, bad, expect):
    """Every field is a trust boundary.  Bad input is refused, not stored."""
    decisions_file = str(tmp_path / "decisions.jsonl")
    monkeypatch.setattr("console.app.DECISIONS_PATH", decisions_file)
    monkeypatch.setattr("console.app.ANCHOR_PATH", str(tmp_path / "ledger.anchor"))
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        r = c.post("/belief/new", data={**_GOOD_FORM, **bad, "stage": "commit"})
        assert r.status_code == 400
        assert expect in r.data
    assert not os.path.exists(decisions_file), "rejected input must write no ledger entry"


def test_belief_duplicate_is_refused(tmp_path, monkeypatch):
    """A second belief on the same ticker and trial is a conflict, not an
    overwrite.  Silently replacing a recorded belief would defeat the ledger.
    """
    decisions_file = str(tmp_path / "decisions.jsonl")
    monkeypatch.setattr("console.app.DECISIONS_PATH", decisions_file)
    monkeypatch.setattr("console.app.ANCHOR_PATH", str(tmp_path / "ledger.anchor"))
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        assert c.post("/belief/new", data={**_GOOD_FORM, "stage": "commit"}).status_code == 200
        r = c.post("/belief/new", data={**_GOOD_FORM, "stage": "commit"})
        assert r.status_code == 409
        assert b"already exists" in r.data

    with open(decisions_file) as f:
        assert len([l for l in f if l.strip()]) == 1, "the duplicate must not be appended"


# ---------------------------------------------------------------------------
# The pinned as_of
# ---------------------------------------------------------------------------

def test_snapshot_pins_its_own_as_of():
    """Classification and everything drawn from it must be a statement about a
    recorded date, not about whatever day the file is read on.
    """
    import datetime as _dt

    with open(SNAPSHOT_PATH) as f:
        snap = json.load(f)
    assert "as_of" in snap, "snapshot must pin the date it was built"
    _dt.date.fromisoformat(snap["as_of"])   # raises if it is not a real date
    for ticker, c in snap["contracts"].items():
        tl = c.get("thesis_timeline")
        if tl:
            assert tl["today"]["date"] == snap["as_of"], (
                f"{ticker} timeline reads a different 'today' than the snapshot pins"
            )


_CLEAN_CHECKOUT_MARKER = "CID_CLEAN_CHECKOUT_CHILD"


def test_documented_test_counts_match_a_real_run():
    """The documented results must come from running the suite, not counting it.

    The previous guard ran `pytest --collect-only` and asserted the README figure
    equalled collected - 1. That is true by construction: it sees how many tests
    EXIST and never how many SKIP. A tracked-files-only checkout carries no
    `data/cache/`, so the fifteen registry-replay tests skip and the real result
    is "176 passed, 16 skipped" while the README said "191 passed, 1 skipped".
    The guard certified the wrong number instead of catching it, and then a later
    commit edited the number up and the guard certified that too. It is the defect
    shape docs/LIMITS.md keeps recording -- a check that cannot fail on the thing
    it names -- sitting on the first command a judge runs.

    So this exports every tracked path at its current content into a temporary
    directory, which is what a clone yields minus the gitignored cache, and runs
    the documented command there. The child deselects this test because it would
    otherwise recurse; the environment marker is a second stop in case the node id
    drifts, and the git check is a third for a source download with no history.

    Two tiers are measured or checked and a third deliberately states no number.
    The clean-checkout tier is measured here. The cache-present tier cannot be
    measured from a clean tree, so it is held to the same total. The credentialed
    tier quotes nothing, because nothing has been measured for it.
    """
    import shutil
    import subprocess

    if os.environ.get(_CLEAN_CHECKOUT_MARKER):
        pytest.skip("child run of the clean-checkout guard")

    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ls = subprocess.run(["git", "ls-files", "-z"], cwd=repo, capture_output=True)
    if ls.returncode != 0:
        pytest.skip("not a git checkout; the clean-clone tier cannot be measured")
    tracked = [p for p in ls.stdout.decode().split("\0") if p]
    assert tracked, "git ls-files returned nothing; cannot build a clean checkout"

    tmp = tempfile.mkdtemp(prefix="cid-clean-")
    try:
        for rel in tracked:
            src = os.path.join(repo, rel)
            if not os.path.isfile(src):
                continue
            dst = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        assert not os.path.isdir(os.path.join(tmp, "data", "cache")), (
            "the exported checkout carries data/cache/, so it is not a clean clone"
        )
        me = ("tests/test_console.py::"
              + test_documented_test_counts_match_a_real_run.__name__)
        child = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "--deselect", me],
            cwd=tmp, capture_output=True, text=True,
            env={**os.environ, _CLEAN_CHECKOUT_MARKER: "1"},
        ).stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    runs = re.findall(r"(\d+) passed(?:, (\d+) skipped)?", child)
    assert runs, f"no pytest summary in the clean-checkout run:\n{child[-800:]}"
    # Deselected in the child and passing here, so it is added back.
    clean_passed = int(runs[-1][0]) + 1
    clean_skipped = int(runs[-1][1] or 0)
    total = clean_passed + clean_skipped

    for name in ("README.md", "docs/SUBMISSION.md"):
        text = open(os.path.join(repo, name)).read()
        # Whitespace-tolerant: prose wraps, and a guard that a line break can
        # switch off is the hollow kind this one exists to replace.
        pairs = {(int(p), int(s)) for p, s in
                 re.findall(r"(\d+)\s+passed,\s+(\d+)\s+skipped", text)}
        assert len(pairs) >= 2, (
            f"{name} must document the clean-checkout tier and the cache-present "
            f"tier separately; it states {sorted(pairs)}"
        )
        assert (clean_passed, clean_skipped) in pairs, (
            f"{name} does not state the clean-checkout result this suite actually "
            f"produces, {clean_passed} passed and {clean_skipped} skipped; it "
            f"states {sorted(pairs)}"
        )
        for p, s in sorted(pairs):
            assert p + s == total, (
                f"{name} states {p} passed, {s} skipped, accounting for {p + s} "
                f"tests; the suite has {total}"
            )


# ---------------------------------------------------------------------------
# The monitoring queue
# ---------------------------------------------------------------------------
# The queue is a second computation over the same contracts, which means it can
# disagree with the first one. Two of the checks below exist purely to make that
# disagreement fail loudly: the counts must equal the command bar's, and no
# contract may be missing from the queue entirely.


def test_queue_200(client):
    r = client.get("/queue")
    assert r.status_code == 200
    assert "text/html" in r.content_type


def _queue_of(snap):
    return snap["queue"]


def test_queue_counts_agree_with_the_command_bar():
    """The queue and the command bar count the same events two different ways.

    `_cmd_bar` counts breached contracts off `verdict`; `_queue` counts them off
    the sign of `gap_months`. Those must land on the same number, and if they
    ever stop doing so one of them is lying to the analyst.
    """
    with open(SNAPSHOT_PATH) as f:
        snap = json.load(f)
    q = _queue_of(snap)
    by_state = {c["state"]: c["n"] for c in q["counts"]}

    assert by_state["breached"] == snap["cmd_bar"]["active_breaches"], (
        "queue breach count disagrees with the command bar's"
    )
    assert by_state["lapsed"] == snap["cmd_bar"]["lapsed_expectations"], (
        "queue lapsed count disagrees with the command bar's"
    )


def test_every_contract_appears_in_the_queue():
    """No contract may be absent. A queue that quietly omits a row is the same
    failure as a screen that hides its hard cases, one screen further on.
    """
    with open(SNAPSHOT_PATH) as f:
        snap = json.load(f)
    listed = {row["ticker"] for row in _queue_of(snap)["rows"]}
    assert listed == set(snap["contracts"]), (
        f"queue lists {sorted(listed)} but the snapshot holds "
        f"{sorted(snap['contracts'])}"
    )


def test_queue_counts_sum_to_its_rows():
    """Counts are precomputed, so they can drift from the rows they count."""
    with open(SNAPSHOT_PATH) as f:
        snap = json.load(f)
    q = _queue_of(snap)
    assert sum(c["n"] for c in q["counts"]) == len(q["rows"])
    assert q["needs_attention"] == sum(
        1 for row in q["rows"] if row["state"] != "clear"
    )


def test_queue_states_match_the_contracts_they_describe():
    """Each row's state must be recomputable from the contract it names.

    Verified by mutation before it was trusted: flipping BEAM's queue row from
    'clear' to 'breached' in the committed snapshot failed here, and so did
    dropping SRPT's unreliable row.
    """
    with open(SNAPSHOT_PATH) as f:
        snap = json.load(f)

    for row in _queue_of(snap)["rows"]:
        c = snap["contracts"][row["ticker"]]
        gap, reliable = c["gap_months"], c["runway"]["reliable"]
        if row["state"] == "breached":
            assert reliable and gap < 0, f"{row['ticker']} is not breached"
        elif row["state"] == "unreliable":
            assert not reliable, f"{row['ticker']} has a usable burn estimate"
        elif row["state"] == "lapsed":
            assert c["lapsed"], f"{row['ticker']} has no lapsed expectation"
        elif row["state"] == "clear":
            assert reliable and gap >= 0 and not c["lapsed"], (
                f"{row['ticker']} is listed clear but something is wrong with it"
            )


def test_queue_is_sorted_worst_first():
    """An inbox that buries the breach under the clear rows is not an inbox."""
    from console.make_snapshot import _QUEUE_RANK

    with open(SNAPSHOT_PATH) as f:
        snap = json.load(f)
    ranks = [_QUEUE_RANK[row["state"]] for row in _queue_of(snap)["rows"]]
    assert ranks == sorted(ranks), "queue rows are not ordered worst first"


def test_queue_shows_rocket_twice(client):
    """Rocket is breached AND carrying a lapsed expectation. Both must appear:
    collapsing a contract to one worst state hides the other piece of work.
    """
    with open(SNAPSHOT_PATH) as f:
        snap = json.load(f)
    states = {row["state"] for row in _queue_of(snap)["rows"]
              if row["ticker"] == "RCKT"}
    assert {"breached", "lapsed"} <= states, (
        f"RCKT should be queued as both breached and lapsed, got {states}"
    )
    assert b"NCT04248439" in client.get("/queue").data


def test_queue_never_ranks_an_unreliable_row():
    """A contract with an unusable burn estimate must show no gap figure.

    The project's rule is that unreliable rows are shown and never ranked. The
    queue broke it in a way the rule's own test could not see: SRPT's rows
    printed "2.6 mo" beside "burn estimate unreliable", which ranks it in the
    reader's head even though no column called it a rank. Caught by looking at
    the rendered page, not by a test, which is why this one exists now.
    """
    with open(SNAPSHOT_PATH) as f:
        snap = json.load(f)
    for row in snap["queue"]["rows"]:
        if not snap["contracts"][row["ticker"]]["runway"]["reliable"]:
            assert row["gap_1f"] is None, (
                f"{row['ticker']} has an unreliable burn estimate but the queue "
                f"prints a gap of {row['gap_1f']}"
            )


def test_queue_claims_no_comparison_it_cannot_make(client):
    """Nothing may say "newly", "since", or "moved" on this page.

    There is one committed snapshot and no previous one, so no state here can
    be a comparison against an earlier look. The first label said "newly
    breached" and could not have known.
    """
    # Collapse whitespace: the sentence is wrapped across lines in the template.
    text = " ".join(client.get("/queue").data.decode().lower().split())
    labels = " ".join(
        c["label"] for c in json.load(open(SNAPSHOT_PATH))["queue"]["counts"]
    ).lower()
    for word in ("newly", "since last", "moved since"):
        assert word not in labels, (
            f"queue state label claims {word!r}, a comparison with no previous "
            "snapshot to make it against"
        )
    assert "nothing here knows what was true yesterday" in text, (
        "the page must say why 'newly' is absent, or the absence reads as an oversight"
    )


# ---------------------------------------------------------------------------
# The no-rank rule, stated generally
# ---------------------------------------------------------------------------
# `test_srpt_has_no_rank_number` checks one page for one shape of violation: a
# plain-integer rank cell in SRPT's row on /contracts. The queue then broke the
# same rule a different way, printing "2.6 mo" beside "burn estimate
# unreliable", and that test passed on it because a gap figure is not a rank
# cell. A rule worth having is worth stating once, over every page.
#
# Verified failing before it was trusted: a gap column added to the flagged
# table on /contracts passes `test_srpt_has_no_rank_number` and fails this.

class _RowParser(HTMLParser):
    """Collect the visible text of every <tr> on a page."""

    def __init__(self):
        super().__init__()
        self._in_tr = False
        self._cur: list[str] = []
        self.rows: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._in_tr, self._cur = True, []

    def handle_endtag(self, tag):
        if tag == "tr":
            self.rows.append(" ".join("".join(self._cur).split()))
            self._in_tr = False

    def handle_data(self, data):
        if self._in_tr:
            self._cur.append(data)


@pytest.mark.parametrize("route", ["/contracts", "/queue"])
def test_unrankable_rows_carry_no_gap_figure(client, route):
    """No page may print a gap figure in a row for a contract it calls unrankable.

    An unreliable burn estimate makes the gap unusable. Showing it anyway ranks
    the row in the reader's head whether or not a column is headed "rank", and
    the project's rule is that such rows are shown and never ranked.
    """
    with open(SNAPSHOT_PATH) as f:
        snap = json.load(f)

    unrankable = {
        t: c["gap_months_1f"]
        for t, c in snap["contracts"].items()
        if not c["runway"]["reliable"] and c.get("gap_months_1f")
    }
    assert unrankable, "snapshot has no unreliable contract; this test proves nothing"

    p = _RowParser()
    p.feed(client.get(route).data.decode())

    for ticker, gap in unrankable.items():
        for row in p.rows:
            if ticker not in row:
                continue
            assert gap not in row, (
                f"{route} prints gap {gap!r} in a row for {ticker}, whose burn "
                f"estimate is unreliable:\n  {row}"
            )
