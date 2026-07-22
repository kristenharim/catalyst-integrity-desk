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
        resp = c.get("/redline/confirm?verdict=approve")
        assert b"intact" in resp.data
        assert b"tampered" not in resp.data

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


@pytest.mark.parametrize("route", ["/contract/RCKT", "/contracts", "/redline"])
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
