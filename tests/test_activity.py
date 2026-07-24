"""The activity screen: decision history, and nothing else.

One question, kept narrow: what decisions were recorded, reviewed, changed or
retired, and in what order. Everything here defends the difference between
answering that and answering the question a reader of a monitoring product will
assume it answers, which is when the evidence changed. There are no historical
evidence runs in this repo, so the second question has no page behind it and the
screen says so.

What these tests are for, in the order they run:

  1. Every row is one entry that is actually in the record. A history screen
     that renders anything else is a history of something that did not happen,
     and the frozen snapshot's one hardcoded challenge is the thing closest to
     hand to render: it looks exactly like a decision and nobody took it.
  2. Receipt links are bound to their row's own entry hash. Selecting the
     record's latest entry was a real defect twice, once on the receipt and once
     on the link into it. A third route to the same page is a third chance.
  3. Two decisions recorded against one company are two rows. Folding them by
     ticker would report a history in which one of them never happened.
  4. Tampered and truncated are disclosed against a real mutated file, not a
     flag, and the rows are still listed: hiding them removes the only evidence
     of what the file now says.
  5. The empty state reports the two files it read, and does not imply anything
     is being checked between snapshots.
"""
from __future__ import annotations

import json
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from console import review  # noqa: E402
from console.app import app as flask_app  # noqa: E402
from orchestrator import lexicon  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = REPO / "data" / "snapshot.json"

THESIS = ("Rocket Pharmaceuticals reaches the registered primary completion of "
          "NCT06092034 before its runway is exhausted, with a non-negative gap.")

# The sentence the page has to render, verbatim. It is the whole capability
# claim of the screen and `tests/test_capability_language.py` scans the template
# it lives in, so this pins that it is present as well as permitted.
SCOPE_STATEMENT = ("Activity records human decision events in the ledger. It does not yet "
                   "represent a complete history of evidence refreshes.")

# Nothing on this page stores any of these. Same list as the inbox's, plus the
# two a history screen invites specifically: an evidence-change history and a
# schedule for the next look.
UNBACKED = [
    "opened", "days ago", "day ago", "in review", "deferred", "assigned",
    "assignee", "owner", "due date", "unread", "notification", "snooze",
    "evidence changed", "last checked", "next check", "refreshed at",
]


@pytest.fixture()
def isolated(tmp_path, monkeypatch):
    """A client whose ledger, review log and anchor live in tmp_path.

    `data/` holds live demo state and a test that mutates it to prove tampering
    would leave the repo looking tampered with. `tests/conftest.py` redirects
    these for every test; this restates it locally so the paths are readable
    here and so `tmp_path` is the one this fixture returns.
    """
    monkeypatch.setattr("console.app.DECISIONS_PATH", str(tmp_path / "decisions.jsonl"))
    monkeypatch.setattr("console.app.REVIEW_LOG_PATH", str(tmp_path / "review_log.jsonl"))
    monkeypatch.setattr("console.app.ANCHOR_PATH", str(tmp_path / "ledger.anchor"))
    flask_app.config["TESTING"] = True
    return flask_app.test_client(), tmp_path


def _snapshot() -> dict:
    return json.loads(SNAPSHOT_PATH.read_text())


def _entries(tmp_path: Path) -> list[dict]:
    path = tmp_path / "decisions.jsonl"
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]


def _rejections(tmp_path: Path) -> list[dict]:
    path = tmp_path / "review_log.jsonl"
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]


def _approve(client, reason="the registered date passed") -> None:
    client.post("/redline/decide", data={"verdict": "approve", "reason": reason})


def _record_belief(client, nct="NCT06092034") -> None:
    client.post("/belief/new", data={
        "stage": "commit", "ticker": "RCKT", "nct": nct, "thesis": THESIS,
        "invalidation": "", "min_gap": "0"})


class _RowParser(HTMLParser):
    """Every activity row, with the receipt and review ids it links.

    Keyed on the class name because the class is what makes a row a row. The
    text is collected flat: the assertions below are about which entry a row
    names, not about where on the row it names it.
    """

    def __init__(self):
        super().__init__()
        self.rows: list[dict] = []
        self._open = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class", "") or ""
        if tag == "li" and cls.startswith("event "):
            self.rows.append({"class": cls, "text": [], "receipts": [], "reviews": []})
            self._open = True
        elif self._open and tag == "a":
            href = a.get("href", "")
            if href.startswith("/receipts/"):
                self.rows[-1]["receipts"].append(href[len("/receipts/"):])
            elif href.startswith("/decisions/"):
                self.rows[-1]["reviews"].append(href)

    def handle_endtag(self, tag):
        if tag == "li":
            self._open = False

    def handle_data(self, data):
        if self._open:
            self.rows[-1]["text"].append(data)


def _rows(html: str) -> list[dict]:
    p = _RowParser()
    p.feed(html)
    for r in p.rows:
        r["flat"] = " ".join(" ".join(r["text"]).split())
    return p.rows


# ---------------------------------------------------------------------------
# Every row is an entry that is really in the record
# ---------------------------------------------------------------------------

def test_every_row_resolves_to_an_exact_recorded_event(isolated):
    """One row per stored event, and each names the event it is.

    Verified failing: dropping the `review_log` half of `activity_rows` leaves
    the rejection unrendered and this names the count.
    """
    c, tmp = isolated
    _approve(c)
    _record_belief(c)
    c.post("/redline/decide", data={"verdict": "reject", "reason": "not persuaded"})

    entries, rejects = _entries(tmp), _rejections(tmp)
    assert entries and rejects, "the fixture must write to both stores"

    rows = _rows(c.get("/activity").get_data(as_text=True))
    assert len(rows) == len(entries) + len(rejects), (
        f"{len(entries)} ledger entries and {len(rejects)} rejections are recorded; "
        f"the page renders {len(rows)} rows"
    )

    # Each ledger entry is named by exactly one row, as that row's own entry.
    # Matched on the labelled hash rather than on the hash alone, because the
    # following row carries the same value as its predecessor link, which is the
    # point of a chain and would make a bare substring match count it twice.
    for e in entries:
        named = [r for r in rows if f"this entry {e['entry_hash']}" in r["flat"]]
        assert len(named) == 1, (
            f"entry {e['entry_hash'][:12]} is named by {len(named)} rows"
        )
        row = named[0]
        assert e["card"]["card_id"] in row["flat"]
        assert str(e["card"]["version"]) in row["flat"]
        assert e["author"] in row["flat"]
        assert review.EVENT_LABELS[e["event"]] in row["flat"], (
            "the ledger event must be named in the words a reader gets"
        )

    # The rejection is the row with no entry hash and no receipt.
    rejected = [r for r in rows if review.REJECTED_LABEL in r["flat"]]
    assert len(rejected) == len(rejects)
    for row in rejected:
        assert not row["receipts"], (
            "a rejection wrote no ledger entry; a receipt link would point at a "
            "record that does not exist"
        )


def test_the_order_is_the_order_the_record_holds(isolated):
    """Chronological, and for entries sharing a timestamp the chain's own order.

    The seed the approve path writes carries `ts=0.0` deliberately, so ordering
    by timestamp and ordering by chain position agree; a sort that disagreed
    with the hash links would be reporting an order the record does not hold.
    """
    c, tmp = isolated
    _approve(c)
    _record_belief(c)

    rows = _rows(c.get("/activity").get_data(as_text=True))
    positions = [next(i for i, r in enumerate(rows)
                      if f"this entry {e['entry_hash']}" in r["flat"])
                 for e in _entries(tmp)]
    assert positions == sorted(positions), (
        f"the ledger's own sequence is rendered out of order: {positions}"
    )


def test_two_decisions_on_one_company_stay_two_rows(isolated):
    """Grouping is a decision-inbox idea and the wrong idea here.

    The inbox groups triggers under a decision, because three reasons to look at
    one belief is one piece of work. Two beliefs recorded against one company are
    two things that happened, and folding them by ticker would report a history
    in which one of them did not.
    """
    c, tmp = isolated
    _record_belief(c, nct="NCT06092034")
    _record_belief(c, nct="NCT04248439")

    entries = _entries(tmp)
    card_ids = {e["card"]["card_id"] for e in entries}
    assert len(card_ids) == 2, "the fixture did not record two distinct cards"
    assert {review.card_ticker(cid) for cid in card_ids} == {"RCKT"}, (
        "the fixture's two cards must belong to one company"
    )

    rows = _rows(c.get("/activity").get_data(as_text=True))
    assert len(rows) == 2, f"two recorded beliefs must be two rows, got {len(rows)}"
    for cid in card_ids:
        assert len([r for r in rows if cid in r["flat"]]) == 1, (
            f"{cid} is not on exactly one row"
        )


# ---------------------------------------------------------------------------
# Receipt links are bound to their own entry
# ---------------------------------------------------------------------------

def test_each_receipt_link_carries_its_own_rows_entry_hash(isolated):
    """The Commit E defect by a third route, and it has already recurred twice.

    Verified failing: binding the href to `rows[-1].entry_hash` — the shape a
    "link to the receipt" written from the handler's last read would take —
    points every row at the record's latest entry and this names the row that
    got the wrong hash.
    """
    c, tmp = isolated
    _approve(c)
    _record_belief(c)

    entries = _entries(tmp)
    assert len(entries) > 2, "the fixture must write more than one entry"
    latest = entries[-1]["entry_hash"]

    rows = _rows(c.get("/activity").get_data(as_text=True))
    for e in entries:
        row = next(r for r in rows
                   if f"this entry {e['entry_hash']}" in r["flat"])
        assert row["receipts"] == [e["entry_hash"]], (
            f"the row for {e['entry_hash'][:12]} links {row['receipts']}"
        )

    linked = [h for r in rows for h in r["receipts"]]
    assert linked.count(latest) == 1, (
        "more than one row links the record's latest entry, which is what a link "
        f"bound to the chain tail looks like: {linked}"
    )

    # And the door opens on the entry the row named, not merely on a
    # receipt-shaped page.
    for e in entries:
        body = c.get(f"/receipts/{e['entry_hash']}").get_data(as_text=True)
        fields = dict(re.findall(
            r'<th scope="row">(.*?)</th>\s*<td[^>]*>(.*?)</td>', body, re.S))
        this_hash = " ".join(re.sub(r"<[^>]+>", " ",
                                    fields["This entry hash"]).split())
        assert this_hash == e["entry_hash"], (
            "an activity row's receipt link resolves to a different entry"
        )


def test_every_review_link_resolves_to_a_decision_this_snapshot_holds(isolated):
    """A link is offered only where it leads somewhere.

    A card whose ticker names no contract in this snapshot has no review screen,
    and the row says that rather than minting an address that 404s.
    """
    c, _ = isolated
    _approve(c)
    _record_belief(c)

    body = c.get("/activity").get_data(as_text=True)
    hrefs = [h for r in _rows(body) for h in r["reviews"]]
    assert hrefs, "the activity screen renders no review link"
    for href in hrefs:
        assert href.startswith("/decisions/") and href.endswith("/review")
        assert c.get(href).status_code == 200, f"{href} does not resolve"


# ---------------------------------------------------------------------------
# Nothing is fabricated from the frozen snapshot
# ---------------------------------------------------------------------------

def test_the_snapshots_one_challenge_is_not_an_event(isolated):
    """The hardcoded challenge looks exactly like a decision and is not one.

    It is written in Python inside `make_snapshot._build_rckt_redline`, it names
    a card, a breach, a classification and a memo, and no human ever took it. On
    an empty record the page has to say the record is empty, not draw the
    challenge as the thing that happened.

    Verified failing: seeding the row list from `SNAPSHOT["redline"]` when the
    ledger is empty renders one row and this names it.
    """
    c, tmp = isolated
    assert not _entries(tmp) and not _rejections(tmp)

    body = c.get("/activity").get_data(as_text=True)
    assert not _rows(body), "an empty record must render no event rows"

    redline = _snapshot()["redline"]
    for fabricated in [redline["card_id"], redline["classification"]["label"],
                       redline["breach"]["metric"], redline["prior_trial"],
                       redline["current_trial"]]:
        assert fabricated not in body, (
            f"{fabricated!r} comes from the frozen snapshot's challenge, which is "
            "a computed state and not something anybody did"
        )


def test_no_unbacked_element_renders_on_the_activity_screen(isolated):
    c, _ = isolated
    _approve(c)
    body = c.get("/activity").get_data(as_text=True).lower()
    present = [w for w in UNBACKED if w in body]
    assert not present, (
        f"the activity screen renders {present}, which nothing in this repo "
        "stores. See docs/plans/phase2-inbox-spec.md section 8."
    )


def test_the_scope_statement_is_rendered_where_a_reader_meets_it(isolated):
    """Above the list, not under it.

    The screen a reader assumes they are looking at is an evidence-change
    history. The sentence that says otherwise is worth nothing below the thing
    it qualifies.
    """
    c, _ = isolated
    _approve(c)
    body = c.get("/activity").get_data(as_text=True)
    flat = " ".join(re.sub(r"<[^>]+>", " ", body).split())
    assert SCOPE_STATEMENT in flat, (
        "the scope statement is not rendered; the page it qualifies is the one a "
        "reader will otherwise take for an evidence-change history"
    )
    # In the markup, so it is above the list for a screen reader and a keyboard
    # as well as for an eye.
    scope = body.find("Activity records human decision events")
    listing = body.find('<ol class="activity">')
    assert scope != -1 and listing != -1
    assert scope < listing, (
        "the scope statement is rendered below the list it qualifies"
    )


# ---------------------------------------------------------------------------
# Record integrity
# ---------------------------------------------------------------------------

def test_a_tampered_history_is_disclosed_and_still_listed(isolated):
    """Demonstrated against the file, not against a flag.

    The edit lands inside the `card` payload, which the hash covers. The rows
    stay on the page: a screen that empties itself when its record fails removes
    the only evidence of what the record now says.
    """
    c, tmp = isolated
    _approve(c)
    path = tmp / "decisions.jsonl"

    assert "record intact" in c.get("/activity").get_data(as_text=True)

    lines = path.read_text().splitlines(keepends=True)
    tampered = lines[0].replace('"version": 1', '"version": 2', 1)
    assert tampered != lines[0], "the mutation must change a hashed byte"
    path.write_text(tampered + "".join(lines[1:]))

    body = c.get("/activity").get_data(as_text=True)
    assert "record tampered" in body
    assert "record intact" not in body
    assert "This history cannot be trusted to be what was recorded" in body, (
        "the failure has to be disclosed in words, not only as a badge colour"
    )
    assert _rows(body), "the events must still be listed under the disclosure"


def test_a_truncated_history_says_it_may_be_missing_events(isolated):
    """The chain still verifies and no longer matches the anchor.

    Both routes to it: the anchor removed, and an entry deleted with the anchor
    left describing the record before the deletion.
    """
    c, tmp = isolated
    _approve(c)
    entries = _entries(tmp)
    assert len(entries) > 1, "the approve path seeds a card before it updates it"
    path = tmp / "decisions.jsonl"

    (tmp / "ledger.anchor").unlink()
    body = c.get("/activity").get_data(as_text=True)
    assert "record truncated or replaced" in body, (
        "an entry-bearing record with no anchor beside it must not read intact"
    )
    assert "This history may be missing events" in body

    (tmp / "ledger.anchor").write_text(json.dumps(
        {"head": entries[-1]["entry_hash"], "count": len(entries)}))
    path.write_text("".join(path.read_text().splitlines(keepends=True)[:-1]))
    body = c.get("/activity").get_data(as_text=True)
    assert "record truncated or replaced" in body
    assert "record intact" not in body
    assert len(_rows(body)) == len(entries) - 1, (
        "the surviving events must be listed; what is gone is not recoverable "
        "from the file that is left"
    )


def test_record_integrity_never_rides_on_an_event_row(isolated):
    """Three wires, and on this page two of them are not present at all.

    A row states what a human did. Whether the record of those actions still
    agrees with its anchor is a statement about the list, so it is a page-level
    element, and no row may carry it.
    """
    c, tmp = isolated
    _approve(c)
    path = tmp / "decisions.jsonl"
    lines = path.read_text().splitlines(keepends=True)
    path.write_text(lines[0].replace('"version": 1', '"version": 2', 1)
                    + "".join(lines[1:]))

    for row in _rows(c.get("/activity").get_data(as_text=True)):
        text = row["flat"].lower()
        for word in ["record intact", "record tampered", "record truncated"]:
            assert word not in text, (
                f"an activity row carries {word!r}; record integrity is a "
                "separate wire and must not ride on an event"
            )


# ---------------------------------------------------------------------------
# The empty state
# ---------------------------------------------------------------------------

def test_the_empty_activity_screen_does_not_imply_anything_is_being_watched(isolated):
    """The same sentence problem the empty inbox has, one screen further on.

    An empty history in a monitoring product reads as "we have been watching and
    nothing happened". Nothing here reads any evidence at all, so the empty state
    has to report the two files it actually opened.
    """
    c, tmp = isolated
    assert not _entries(tmp) and not _rejections(tmp)
    body = c.get("/activity").get_data(as_text=True)

    start = body.find('class="empty"')
    assert start != -1, "the empty state must render"
    # Whitespace-normalised: prose wraps, and a check a line break can switch
    # off is the hollow kind this repo keeps re-learning about.
    empty = " ".join(re.sub(r"<[^>]+>", " ",
                            body[start:body.find("</div>", start)]).split())
    assert "No decision event has been recorded here" in empty
    assert "decision ledger" in empty and "review log" in empty, (
        "the empty state must name the stores it is reporting on"
    )
    for word in ["monitor", "watch", "live", "real time", "real-time"]:
        assert word not in empty.lower(), (
            f"the empty state implies {word!r}; this page reads no evidence"
        )
    assert not _rows(body), "no event rows may render in the empty state"


# ---------------------------------------------------------------------------
# The claims the page makes
# ---------------------------------------------------------------------------

def test_the_activity_screen_makes_no_forbidden_claim(isolated):
    """Driven populated, because the route scan reads the empty state.

    `tests/test_lexicon.py` scans `/activity` off the url_map from a clean
    checkout, where the record is empty, so every word an event row renders is
    invisible to it.
    """
    c, tmp = isolated
    _approve(c)
    _record_belief(c)
    c.post("/redline/decide", data={"verdict": "reject", "reason": "not persuaded"})
    violations = lexicon.scan(c.get("/activity").get_data(as_text=True))
    assert not violations, "\n  ".join(str(v) for v in violations)


def test_the_screen_is_reachable_without_knowing_its_address(isolated):
    """The receipt spent a commit being addressable and unreachable.

    A history nobody can get to from the product is a history nobody reads.
    """
    c, _ = isolated
    assert 'href="/activity"' in c.get("/inbox").get_data(as_text=True)


# ---------------------------------------------------------------------------
# What was not changed
# ---------------------------------------------------------------------------

def test_the_four_pinned_routes_are_untouched(isolated):
    """Adding a screen must not move the ones the demo and the spine depend on.

    Their contents are pinned in detail by `tests/test_inbox_receipt.py` and
    `tests/test_decision_review.py`; this is the cheap check that the route
    table itself did not shift under them.
    """
    c, _ = isolated
    assert c.get("/demo").status_code == 302
    assert "/contract/RCKT" in c.get("/demo").headers["Location"]
    for path in ["/redline", "/inbox",
                 "/decisions/rckt:funded_to_catalyst/review"]:
        assert c.get(path).status_code == 200, f"{path} no longer renders"


def test_one_timestamp_rendering_serves_both_pages_that_show_an_entry():
    """The receipt and the activity list date the same entries.

    Two formatters would let one page say an entry landed at a time the other
    denies, which is a discrepancy in the record rather than in the layout. The
    zone is asserted because the label says UTC and `fromtimestamp` with no
    timezone reads the machine's local clock.
    """
    assert review.ts_display(0.0) == "1970-01-01 00:00:00 UTC"
    assert review.ts_display(None) == "unavailable"
    src = (REPO / "console" / "app.py").read_text()
    assert "review.ts_display(entry[\"ts\"])" in src, (
        "the receipt no longer composes its timestamp through the shared "
        "renderer, so the two pages can disagree about one entry"
    )
