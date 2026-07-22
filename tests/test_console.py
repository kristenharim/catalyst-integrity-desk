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
"""
from __future__ import annotations

import json
import os
import re
import sys
from html.parser import HTMLParser

import pytest

# Ensure the repo root is importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from console.app import app as flask_app

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


@pytest.mark.parametrize("route", ["/contract/RCKT", "/contracts"])
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
