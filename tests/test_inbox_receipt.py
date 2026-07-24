"""The Decision Inbox and the Decision Integrity Receipt, as rendered.

Two screens, and the reason they are tested together is that they are the two
ends of one spine: an inbox item is a decision nobody has ruled on, and a
receipt is the record of ruling on one. Everything between them already existed
and is not retested here.

What these tests are actually for:

  1. One item per decision. `review.build_tasks` groups triggers under a
     decision on purpose, and a template is perfectly capable of unpacking that
     back into one row per trigger, which turns a decision queue into an alert
     feed. Rocket carries three reasons and must be one item.
  2. The unavailable row is shown and never ranked. A screen that hides its hard
     cases is worse than one that shows them.
  3. The receipt names the entry it is a receipt for. Selecting the chain's last
     entry was a real defect once (`tests/test_receipt_identity.py`), and the new
     route addresses entries by hash so it cannot recur by a different path.
  4. Tampered and truncated are demonstrated by mutating a real ledger file, not
     by passing a flag. A badge that flips because a test told it to is evidence
     of nothing; the point of the anchor is that a file on disk disagrees with it.
  5. Nothing unbacked renders. Task age, `in_review`, `deferred`, assignment,
     due dates and unread markers all read naturally on a queue and none of them
     has a store behind it. They are asserted absent from the HTML rather than
     left to review.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import threading
from html.parser import HTMLParser
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from console.app import app as flask_app  # noqa: E402
from orchestrator import lexicon  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = REPO / "data" / "snapshot.json"

THESIS = ("Rocket Pharmaceuticals reaches the registered primary completion of "
          "NCT06092034 before its runway is exhausted, with a non-negative gap.")

# Every element that would read naturally on a work queue and has nothing behind
# it. docs/plans/phase2-inbox-spec.md section 8 says why each is unbacked; this
# list is the enforcement of that section on the rendered page.
UNBACKED = [
    "opened", "days ago", "day ago", "in review", "deferred", "assigned",
    "assignee", "owner", "due date", "unread", "notification", "snooze",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """The console against the committed snapshot and the real ledger paths."""
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


@pytest.fixture()
def isolated(tmp_path, monkeypatch):
    """A client whose ledger, review log and anchor live in tmp_path.

    Every write test uses this. `data/decisions.jsonl` is live demo state and a
    test that mutates it to prove tampering would leave the repo looking
    tampered with.
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


def _approve(client) -> None:
    client.post("/redline/decide", data={"verdict": "approve",
                                         "reason": "the registered date passed"})


def _redline_entry(tmp_path: Path) -> dict:
    """The ledger entry the redline approval wrote."""
    card_id = _snapshot()["redline"]["card_id"]
    mine = [e for e in _entries(tmp_path) if e["card"]["card_id"] == card_id]
    assert mine, "the approval wrote no entry for the redline's card"
    return mine[-1]


# ---------------------------------------------------------------------------
# The inbox: one item per decision
# ---------------------------------------------------------------------------

class _ItemParser(HTMLParser):
    """Every inbox item, with the text of the trigger rows grouped under it.

    Written against the class names rather than the tag names because the point
    of the assertion is the grouping, and grouping is what the classes mean.
    """

    def __init__(self):
        super().__init__()
        self.items: list[dict] = []
        self._depth = 0
        self._in_trigger = False
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        cls = dict(attrs).get("class", "") or ""
        if "inbox-item" in cls:
            self.items.append({"class": cls, "triggers": [], "text": []})
            self._depth = 1
        elif self.items and self._depth:
            if "trigger " in cls or cls.startswith("trigger"):
                if "trigger-" not in cls:
                    self._in_trigger = True
                    self._buf = []

    def handle_endtag(self, tag):
        if self._in_trigger and tag == "li":
            self.items[-1]["triggers"].append(" ".join(
                " ".join(self._buf).split()))
            self._in_trigger = False
            self._buf = []
        elif tag == "li" and self.items and self._depth:
            self._depth = 0

    def handle_data(self, data):
        if self._in_trigger:
            self._buf.append(data)
        elif self.items and self._depth:
            self.items[-1]["text"].append(data)


def _items(html: str) -> list[dict]:
    p = _ItemParser()
    p.feed(html)
    return p.items


def _receipt_fields(html: str) -> dict[str, str]:
    """The receipt table as {row label: value}.

    Asserted field by field rather than by substring, because the page echoes
    the id that was asked for: a receipt showing a different entry's hashes
    still contains the requested hash somewhere, so "the hash is on the page" is
    not the same claim as "this is that entry's receipt". Mutation-tested by
    making the route return the chain's first entry regardless of the id, which
    a substring check let through and this does not.
    """
    rows = re.findall(
        r'<th scope="row">(.*?)</th>\s*<td[^>]*>(.*?)</td>', html, re.S)
    return {k.strip(): " ".join(re.sub(r"<[^>]+>", " ", v).split()) for k, v in rows}


def _declarations(html: str, selector: str) -> dict[str, str]:
    """The declarations of one CSS rule in the rendered page."""
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", html)
    assert m, f"no rule for {selector} is served with the page"
    out = {}
    for decl in m.group(1).split(";"):
        if ":" in decl:
            prop, _, value = decl.partition(":")
            out[prop.strip()] = value.strip()
    return out


def test_inbox_renders_one_item_per_decision_with_triggers_grouped(client):
    """Rocket carries three reasons and is one item, not three rows.

    Verified failing: rendering the loop over `row.decision.triggers` as
    top-level items instead of nested ones produces five items for three
    decisions and this names the count.
    """
    snap = _snapshot()
    expected = {t for t, c in snap["contracts"].items()
                if (c.get("decision") or {}).get("triggers")}

    body = client.get("/inbox").get_data(as_text=True)
    items = _items(body)
    assert len(items) == len(expected), (
        f"expected one item per triggered decision ({sorted(expected)}), got "
        f"{len(items)} items"
    )

    for ticker in expected:
        triggers = snap["contracts"][ticker]["decision"]["triggers"]
        item = [i for i in items if ticker in " ".join(i["text"])]
        assert len(item) == 1, f"{ticker} must appear as exactly one item"
        assert len(item[0]["triggers"]) == len(triggers), (
            f"{ticker} has {len(triggers)} triggers and its item shows "
            f"{len(item[0]['triggers'])}"
        )
        for t in triggers:
            assert any(t["label"] in row for row in item[0]["triggers"]), (
                f"{ticker} trigger {t['label']!r} is not grouped under its item"
            )


def test_inbox_orders_worst_first_and_never_numbers_the_rows(client):
    """Order is the snapshot's `sort_key`, and it is order, not a rank column.

    A rank number beside a row is a claim the row is comparable with the others.
    SRPT's burn estimate is not usable, so it is shown here and carries no
    position anyone should read.
    """
    snap = _snapshot()
    body = client.get("/inbox").get_data(as_text=True)
    items = _items(body)
    shown = [t for t in [" ".join(i["text"]) for i in items]]

    order = sorted(
        [(c["decision"]["sort_key"], t) for t, c in snap["contracts"].items()
         if (c.get("decision") or {}).get("triggers")]
    )
    for expected, text in zip([t for _, t in order], shown):
        assert expected in text, f"expected {expected} in this position, got {text[:40]!r}"

    for item in items:
        cells = [c.strip() for c in item["text"] if c.strip()]
        assert not [c for c in cells if c.isdigit()], (
            f"an inbox item carries a bare rank number: {cells}"
        )


def test_the_unavailable_row_is_shown_and_carries_no_gap(client):
    """SRPT: `unavailable` evidence, unusable burn, no rankable gap."""
    body = client.get("/inbox").get_data(as_text=True)
    items = _items(body)
    srpt = [i for i in items if "SRPT" in " ".join(i["text"])]
    assert srpt, "the unavailable row must be shown, never dropped"
    text = " ".join(srpt[0]["text"])
    assert "unavailable" in text, "SRPT's evidence state must render as unavailable"
    assert "not rankable" in text, (
        "an unreliable burn estimate has no gap figure to show, and the absence "
        "has to be stated rather than left blank"
    )
    assert _snapshot()["contracts"]["SRPT"]["gap_months_1f"] not in text, (
        "the gap of an unreliable row must not be rendered as if it were usable"
    )


def test_the_refusal_outweighs_the_number_it_refuses(client):
    """A UI invariant: 'comparison refused' is louder than the movement it refuses."""
    body = client.get("/inbox").get_data(as_text=True)
    label = body.find("comparison refused")
    assert label != -1, "the refused-comparison trigger must render"
    detail = body.find("is not treated as delay")
    assert detail != -1, "the refusal's own sentence must render"
    assert label < detail, "the refusal label must precede the reading it refuses"

    # The label is heavier than the sentence carrying the figure, and never
    # smaller. Read off the declarations rather than asserted as a string, so
    # reformatting the stylesheet cannot switch the check off.
    label = _declarations(body, ".trigger-label")
    detail = _declarations(body, ".trigger-detail")
    assert int(label["font-weight"]) > int(detail["font-weight"]), (
        f"the refusal label is not heavier than the figure it refuses: {label} vs {detail}"
    )
    assert float(label["font-size"].rstrip("px")) >= float(detail["font-size"].rstrip("px")), (
        "the refusal label is rendered smaller than the reading it refuses"
    )


def test_the_action_is_adjudicate_only_for_the_one_pending_redline(client):
    """Exactly one decision can be ruled on, so exactly one offers a ruling.

    Every other item links to the evidence. There is one challenge in this
    system, written in Python inside make_snapshot.py, and no rebuild reads the
    ledger, so an Adjudicate button on any other row would be a control with
    nothing behind it.
    """
    snap = _snapshot()
    redline_ticker = snap["redline"]["ticker"]
    body = client.get("/inbox").get_data(as_text=True)

    for item in _items(body):
        text = " ".join(item["text"])
        ticker = next(t for t in snap["contracts"] if t in text)
        if ticker == redline_ticker:
            assert "Adjudicate" in text, f"{ticker} is the pending redline"
        else:
            assert "Review evidence" in text, (
                f"{ticker} has no challenge to adjudicate; it must link to evidence"
            )
    assert body.count("Adjudicate") == 1, "only one decision can be adjudicated today"


def test_the_empty_inbox_does_not_imply_anything_is_being_watched(monkeypatch, client):
    """S1e. The hardest sentence on the screen to write honestly.

    An empty queue in a monitoring product reads as "we are watching and there is
    nothing". Nothing here rereads the evidence between snapshots, so the empty
    state has to say what it is actually reporting: the state of one frozen file.
    """
    monkeypatch.setattr("console.app.SNAPSHOT", {**_snapshot(), "contracts": {}})
    body = client.get("/inbox").get_data(as_text=True)

    empty = body[body.find('class="empty"'):body.find("</div>", body.find('class="empty"'))]
    assert "No decision in this snapshot has an open reason to look" in empty
    assert _snapshot()["as_of"] in empty, (
        "the empty state must name the snapshot it is reporting on"
    )
    for word in ["monitor", "watch", "live", "real time", "real-time"]:
        assert word not in empty.lower(), (
            f"the empty state implies {word!r}; nothing rereads the evidence "
            "between snapshots"
        )
    assert not _items(body), "no items may render in the empty state"


def test_the_three_axes_stay_on_three_wires(client):
    """Evidence, workflow and record integrity never collapse into one indicator.

    Asserted structurally: the record-integrity notice is a page-level element
    and never sits inside a decision item, because a tampered decision record is
    not a statement about any thesis on the page.
    """
    body = client.get("/inbox").get_data(as_text=True)
    for item in _items(body):
        text = " ".join(item["text"]).lower()
        for record_word in ["record intact", "record tampered", "record truncated"]:
            assert record_word not in text, (
                f"an inbox item carries {record_word!r}; record integrity is a "
                "separate wire and must not ride on a decision row"
            )
    # And the two axes that do belong on a row are separate elements.
    assert 'class="badge badge-' in body, "the evidence badge must render"
    assert 'class="chip"' in body, "the workflow chip must render"


def test_no_unbacked_element_renders_on_the_inbox(client):
    body = client.get("/inbox").get_data(as_text=True).lower()
    present = [w for w in UNBACKED if w in body]
    assert not present, (
        f"the inbox renders {present}, which nothing in this repo stores. See "
        "docs/plans/phase2-inbox-spec.md section 8."
    )


def test_every_number_on_the_inbox_comes_from_the_snapshot(client):
    """The provenance invariant, extended to the new page.

    Failure verification: a hardcoded '9999' added to the item head is named
    here as a token absent from snapshot.json.
    """
    raw = SNAPSHOT_PATH.read_text()
    body = client.get("/inbox").get_data(as_text=True)

    class _Text(HTMLParser):
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

    p = _Text()
    p.feed(body)
    for token in re.findall(r"-?\d+(?:\.\d+)?", " ".join(p.chunks)):
        assert token in raw, (
            f"number token {token!r} on GET /inbox is not in snapshot.json; it "
            "was computed or hardcoded in the view layer"
        )


def test_the_inbox_makes_no_forbidden_claim(client):
    violations = lexicon.scan(client.get("/inbox").get_data(as_text=True))
    assert not violations, "\n  ".join(str(v) for v in violations)


# ---------------------------------------------------------------------------
# The receipt
# ---------------------------------------------------------------------------

def test_the_receipt_renders_intact_for_a_real_approval(isolated):
    c, tmp = isolated
    _approve(c)
    entry = _redline_entry(tmp)

    r = c.get(f"/receipts/{entry['entry_hash']}")
    assert r.status_code == 200
    body = r.get_data(as_text=True)

    assert "record intact" in body
    assert "&#10007;" not in body and "&#9888;" not in body, (
        "an intact record must not show the tampered or truncated badge"
    )
    fields = _receipt_fields(body)
    assert fields["This entry hash"] == entry["entry_hash"]
    assert fields["Previous entry hash"] == entry["prev_hash"]
    assert fields["Card"] == entry["card"]["card_id"]
    assert fields["Author"] == entry["author"]
    assert fields["Event"] == "belief revised", "the ledger event must be named in words"
    assert fields["Reason given"] == "the registered date passed"
    assert fields["What changed"], "the challenge decision must say what changed"


def test_the_receipt_names_the_entry_asked_for_not_the_chain_tail(isolated):
    """The defect this route is addressed by hash to avoid.

    An unrelated write lands after the decision, which is ordinary use. The
    receipt for the decision must still be the decision's.
    """
    c, tmp = isolated
    _approve(c)
    c.post("/belief/new", data={
        "stage": "commit", "ticker": "RCKT", "nct": "NCT06092034",
        "thesis": THESIS, "invalidation": "the gap falls below zero", "min_gap": "0"})

    entry = _redline_entry(tmp)
    # The entry's own predecessor is on the receipt by design: the pair is what
    # links this decision to the one before it. Every other entry is not.
    others = [e for e in _entries(tmp)
              if e["entry_hash"] not in (entry["entry_hash"], entry["prev_hash"])]
    assert others, "the fixture did not produce a second write"

    body = c.get(f"/receipts/{entry['entry_hash']}").get_data(as_text=True)
    fields = _receipt_fields(body)
    assert fields["This entry hash"] == entry["entry_hash"]
    assert fields["Previous entry hash"] == entry["prev_hash"]
    assert fields["Card"] == entry["card"]["card_id"]
    for other in others:
        assert other["entry_hash"] not in body, (
            "another entry's hash is on this receipt"
        )
    assert "rckt:nct06092034" not in body, "the later belief's identity is on the receipt"


def test_a_receipt_for_a_belief_refuses_to_describe_what_changed(isolated):
    """`what_changed` is composed from the one challenge in the snapshot.

    A belief recorded through the form has a ledger entry and no breach behind
    it. Borrowing the redline's summary would put one decision's description
    under another decision's hashes, which is the same defect as borrowing its
    hashes.
    """
    c, tmp = isolated
    c.post("/belief/new", data={
        "stage": "commit", "ticker": "RCKT", "nct": "NCT06092034",
        "thesis": THESIS, "invalidation": "", "min_gap": "0"})
    entry = _entries(tmp)[-1]

    body = c.get(f"/receipts/{entry['entry_hash']}").get_data(as_text=True)
    assert "belief recorded" in body
    assert "unavailable for this entry" in body
    snap_redline = _snapshot()["redline"]
    assert snap_redline["classification"]["label"] not in body, (
        "the challenge's classification is describing an entry it is not about"
    )
    assert "Granite memo" not in body, (
        "a belief written on the form reaches the ledger with no memo behind it; "
        "the challenge chain must not be drawn over it"
    )


def test_the_receipt_flips_to_tampered_on_a_real_edited_byte(isolated):
    """Demonstrated against the file, not against a flag.

    The edit lands inside the `card` payload, which the hash covers. The verdict
    word lives in review_log.jsonl and is not hashed, so editing that would
    prove nothing.
    """
    c, tmp = isolated
    _approve(c)
    entry = _redline_entry(tmp)
    path = tmp / "decisions.jsonl"

    assert "record intact" in c.get(f"/receipts/{entry['entry_hash']}").get_data(as_text=True)

    lines = path.read_text().splitlines(keepends=True)
    tampered = lines[0].replace('"version": 1', '"version": 2', 1)
    assert tampered != lines[0], "the mutation must change a hashed byte"
    path.write_text(tampered + "".join(lines[1:]))

    body = c.get(f"/receipts/{entry['entry_hash']}").get_data(as_text=True)
    assert "record tampered" in body, "the badge must read tampered after a hashed edit"
    assert "record intact" not in body
    assert "hash FAILED" in body, "the chain strip must fail with the badge"


def test_the_receipt_flips_to_truncated_when_an_entry_is_deleted(isolated):
    """The chain still verifies and no longer matches the anchor.

    The receipt asked for is the surviving one, so this is a real receipt
    rendering beside a record that has lost something, which is the state the
    anchor exists to detect.
    """
    c, tmp = isolated
    _approve(c)
    entries = _entries(tmp)
    assert len(entries) > 1, "the approve path seeds a card before it updates it"
    survivor, decision = entries[0], _redline_entry(tmp)
    path = tmp / "decisions.jsonl"

    # Removing the anchor is the same finding by the other route: the chain
    # still verifies and nothing is left to verify it against.
    (tmp / "ledger.anchor").unlink()
    body = c.get(f"/receipts/{decision['entry_hash']}").get_data(as_text=True)
    assert "record truncated or replaced" in body, (
        "an entry-bearing record with no anchor beside it must not read intact"
    )
    assert "chain replaced" in body, "the chain strip must follow the badge"

    # Deleting the last entry, with the anchor back in place: the chain verifies
    # and disagrees with what was recorded about it.
    (tmp / "ledger.anchor").write_text(json.dumps(
        {"head": decision["entry_hash"], "count": len(entries)}))
    path.write_text("".join(path.read_text().splitlines(keepends=True)[:-1]))
    body = c.get(f"/receipts/{survivor['entry_hash']}").get_data(as_text=True)
    assert "record truncated or replaced" in body
    assert "record intact" not in body
    # The survivor is the seeded card, which never went through the challenge
    # loop, so it carries no chain strip. The badge is the whole statement here.
    assert survivor["card"]["card_id"] in body


def test_a_deleted_entry_is_reported_as_missing_rather_than_substituted(isolated):
    c, tmp = isolated
    _approve(c)
    gone = _redline_entry(tmp)["entry_hash"]
    path = tmp / "decisions.jsonl"
    path.write_text("".join(path.read_text().splitlines(keepends=True)[:-1]))

    body = c.get(f"/receipts/{gone}").get_data(as_text=True)
    assert "No entry with this id is in the decision record" in body
    assert "record truncated or replaced" in body
    for e in _entries(tmp):
        assert e["entry_hash"] not in body, (
            "a receipt for a missing entry is showing a surviving entry's hashes"
        )


def test_an_unknown_id_renders_a_miss_and_no_receipt(isolated):
    c, _ = isolated
    body = c.get("/receipts/not-an-entry-hash").get_data(as_text=True)
    assert "No entry with this id is in the decision record" in body
    assert "Previous entry hash" not in body, "a miss must not render a receipt table"


def test_a_rejection_leaves_nothing_to_receipt(isolated):
    """A receipt exists only after a human action that was recorded.

    Rejecting leaves the belief standing and writes to the review log, not the
    ledger, so there is no entry and no receipt. The page must not imply one.
    """
    c, tmp = isolated
    c.post("/redline/decide", data={"verdict": "reject", "reason": "not persuaded"})
    assert not _entries(tmp), "a rejection must not write a ledger entry"
    body = c.get("/receipts/anything").get_data(as_text=True)
    assert "No entry with this id is in the decision record" in body


def test_no_unbacked_element_renders_on_the_receipt(isolated):
    c, tmp = isolated
    _approve(c)
    body = c.get(f"/receipts/{_redline_entry(tmp)['entry_hash']}").get_data(as_text=True)
    present = [w for w in UNBACKED if w in body.lower()]
    assert not present, f"the receipt renders {present}, which nothing here stores"


def test_the_receipt_makes_no_forbidden_claim(isolated):
    """Driven for real, because the page a route list reads is the miss state."""
    c, tmp = isolated
    _approve(c)
    body = c.get(f"/receipts/{_redline_entry(tmp)['entry_hash']}").get_data(as_text=True)
    violations = lexicon.scan(body)
    assert not violations, "\n  ".join(str(v) for v in violations)


# ---------------------------------------------------------------------------
# The way in: /redline/confirm -> /receipts/<entry_hash>
# ---------------------------------------------------------------------------
# The receipt had an address and no door. These three say the door opens on the
# decision the page is about, that it exists only after a human ruled, and that a
# later write cannot move it, which is the defect Commit E fixed for the receipt
# itself and would be free to reintroduce through the link.


def _receipt_links(html: str) -> list[str]:
    """Every entry id the page links a receipt for.

    An empty id counts. A link to `/receipts/` with nothing after it is still a
    receipt offered, and the first draft of this helper required at least one
    character, so a page that always linked and simply had no entry to name read
    as a page that did not link at all.
    """
    return re.findall(r'href="/receipts/([^"]*)"', html)


def test_the_confirm_link_points_at_the_entry_the_page_rendered(isolated):
    """One link, to the entry whose hashes are in the table above it.

    Verified failing by pointing the href at `receipt.prev_hash`: the link then
    resolves to the seeded predecessor and this names the hash it got.
    """
    c, tmp = isolated
    _approve(c)
    entry = _redline_entry(tmp)

    body = c.get("/redline/confirm?verdict=approve").get_data(as_text=True)
    assert _receipt_links(body) == [entry["entry_hash"]], (
        "the confirm page must link exactly one receipt, the one for the entry "
        "it just rendered"
    )

    # And the door opens on that entry, not merely on a receipt-shaped page.
    fields = _receipt_fields(
        c.get(f"/receipts/{entry['entry_hash']}").get_data(as_text=True))
    assert fields["This entry hash"] == entry["entry_hash"]
    assert fields["Card"] == entry["card"]["card_id"]


def test_no_receipt_link_exists_until_a_human_has_decided(isolated):
    """A receipt exists only after a recorded human action, and so does its link.

    Two ways there is nothing to link to: nobody has ruled yet, and a rejection,
    which leaves the belief standing and writes to the review log rather than the
    ledger. Neither may offer a receipt.

    Verified failing by adding a standing "Receipt" link to the page footer, the
    shape this would take by accident: it names the link rendered with no
    decision behind it.
    """
    c, tmp = isolated
    assert not _receipt_links(c.get("/redline").get_data(as_text=True)), (
        "the pending challenge is undecided; it cannot carry a receipt link"
    )
    assert not _receipt_links(
        c.get("/redline/confirm?verdict=approve").get_data(as_text=True)), (
        "no decision has been recorded, so there is no entry to link"
    )

    c.post("/redline/decide", data={"verdict": "reject", "reason": "not persuaded"})
    assert not _entries(tmp), "a rejection must not write a ledger entry"
    body = c.get("/redline/confirm?verdict=reject").get_data(as_text=True)
    assert "Rejected" in body
    assert not _receipt_links(body), (
        "a rejection wrote no ledger entry; a receipt link would point at a "
        "record that does not exist"
    )


def test_a_later_unrelated_entry_does_not_move_the_link(isolated):
    """The Commit E defect, by the other route.

    Recording a belief after the approval makes that belief the chain's last
    entry. The link is derived from the receipt the page composed, which is
    selected by card_id, so it stays on the decision this page is about.

    Verified failing by composing the confirm receipt from `_entries()[-1]`,
    which is what the handler did before Commit E: the link then follows the
    belief and this names the wrong hash.
    """
    c, tmp = isolated
    _approve(c)
    entry = _redline_entry(tmp)

    c.post("/belief/new", data={
        "stage": "commit", "ticker": "RCKT", "nct": "NCT06092034",
        "thesis": THESIS, "invalidation": "", "min_gap": "0"})
    newest = _entries(tmp)[-1]
    assert newest["entry_hash"] != entry["entry_hash"], (
        "the fixture did not produce a later entry"
    )

    links = _receipt_links(
        c.get("/redline/confirm?verdict=approve").get_data(as_text=True))
    assert links == [entry["entry_hash"]], (
        f"the receipt link follows the chain tail rather than this decision: "
        f"{links}"
    )
    assert newest["entry_hash"] not in links


# ---------------------------------------------------------------------------
# What was not changed
# ---------------------------------------------------------------------------

def test_the_existing_confirm_page_still_renders_its_receipt(isolated):
    """`/redline/confirm` is where docs/DEMO.md ends. It keeps working.

    Both pages now compose the receipt through the same function, so the risk
    the refactor carries is that one of them changed. This pins the one the demo
    script depends on.
    """
    c, tmp = isolated
    _approve(c)
    entry = _redline_entry(tmp)
    body = c.get("/redline/confirm?verdict=approve").get_data(as_text=True)
    assert "Accepted" in body
    assert entry["entry_hash"] in body and entry["prev_hash"] in body
    assert entry["card"]["card_id"] in body
    assert "intact" in body


def test_the_root_still_redirects_to_the_rocket_detail(client):
    """The inbox is at /inbox. The front door did not move."""
    r = client.get("/")
    assert r.status_code == 302 and "/contract/RCKT" in r.headers["Location"]
    r = client.get("/demo")
    assert r.status_code == 302 and "/contract/RCKT" in r.headers["Location"]


# ---------------------------------------------------------------------------
# Accessibility, in a real browser
# ---------------------------------------------------------------------------
# Same gating as tests/test_demo_frame.py, for the same reason: playwright is a
# development extra rather than a repo dependency, so a clean checkout must not
# measure a tier no judge can reproduce. axe-core is a second extra, resolved
# from CID_AXE_CORE or a local node_modules, and skipped when absent rather than
# vendored into the repo. `package.json` and `package-lock.json` pin the version
# `npm ci` puts in that node_modules, so the tier is reproducible rather than
# whatever axe-core the registry served that day.

AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"]

# Every axe.run that actually executed, appended by the test below and read by
# the guard at the end of this file. A skipped accessibility test and a passing
# one are indistinguishable in a green summary, which is how a tier degrades to
# zero scans without anyone noticing.
_AXE_SCANS: list[str] = []


def _axe_source_path() -> str | None:
    for candidate in [os.environ.get("CID_AXE_CORE"),
                      str(REPO / "node_modules" / "axe-core" / "axe.min.js")]:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def _axe_source() -> str | None:
    path = _axe_source_path()
    return Path(path).read_text() if path else None


@pytest.fixture()
def live_server(tmp_path, monkeypatch):
    """The console on an ephemeral port, writing to tmp_path.

    Monkeypatched before the server starts, so the browser drives the same
    isolated ledger the test seeded rather than the repo's live demo state.
    """
    from werkzeug.serving import make_server

    monkeypatch.setattr("console.app.DECISIONS_PATH", str(tmp_path / "decisions.jsonl"))
    monkeypatch.setattr("console.app.REVIEW_LOG_PATH", str(tmp_path / "review_log.jsonl"))
    monkeypatch.setattr("console.app.ANCHOR_PATH", str(tmp_path / "ledger.anchor"))

    server = make_server("127.0.0.1", 0, flask_app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.port}", tmp_path
    finally:
        server.shutdown()


def test_the_decision_screens_pass_axe_core(live_server):
    """The accessibility regression for the three screens of the decision spine.

    Colour is never the only signal, contrast clears the Carbon floor on both
    the quiet and the alarm state, landmarks and heading order are real, and the
    keyboard path reaches every control. axe asserts the mechanical half; the
    structural half is asserted beside it, because axe cannot know that a badge
    which drops its text still has a colour.

    `/redline` is measured here rather than in a second harness of its own. It
    is the demo centrepiece and it carried two colour-contrast violations of its
    own while the two screens either side of it were clean, which is what a
    check scoped to the newest work looks like from the outside.
    """
    if os.environ.get("CID_BASE_DEPS_ONLY"):
        pytest.skip("base dependencies only; playwright is a development extra")
    pytest.importorskip(
        "playwright.sync_api",
        reason="playwright is absent; accessibility cannot be measured in a browser",
    )
    axe = _axe_source()
    if axe is None:
        pytest.skip("axe-core not found; set CID_AXE_CORE to axe.min.js")

    from playwright.sync_api import sync_playwright

    base, tmp = live_server
    flask_app.config["TESTING"] = True
    c = flask_app.test_client()
    _approve(c)
    entry_hash = _redline_entry(tmp)["entry_hash"]

    findings = {}
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:                                # noqa: BLE001
            pytest.skip(f"no playwright browser installed: {exc}")
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            for name, url in [("inbox", f"{base}/inbox"),
                              ("receipt", f"{base}/receipts/{entry_hash}"),
                              ("redline", f"{base}/redline")]:
                page.goto(url, wait_until="load")
                page.add_script_tag(content=axe)
                result = page.evaluate(
                    "async (tags) => await axe.run(document, "
                    "{runOnly: {type: 'tag', values: tags}})", AXE_TAGS)
                _AXE_SCANS.append(name)
                findings[name] = [
                    f"{v['id']} ({v['impact']}): "
                    + "; ".join(n["target"][0] for n in v["nodes"][:3])
                    for v in result["violations"]
                ]
                # Every status carries text, so a reader who cannot see the
                # colour still gets the state.
                for selector in [".badge", ".chip", ".record-badge"]:
                    for handle in page.query_selector_all(selector):
                        assert handle.inner_text().strip(), (
                            f"{selector} on {name} conveys its state by colour alone"
                        )
                # The whole page is reachable by keyboard, with a visible ring.
                focused = []
                for _ in range(40):
                    page.keyboard.press("Tab")
                    focused.append(page.evaluate(
                        "() => document.activeElement && document.activeElement.tagName"))
                assert "A" in focused, f"no link on {name} is reachable by Tab"
        finally:
            browser.close()

    assert not any(findings.values()), (
        "axe-core violations:\n  "
        + "\n  ".join(f"{page}: {v}" for page, vs in findings.items() for v in vs)
    )


def test_the_documented_accessibility_command_ran_an_axe_scan():
    """The accessibility tier cannot report green having scanned nothing.

    Every gate in the test above is a `pytest.skip`, and a skip is invisible in
    the one line a reader looks at. Someone follows the documented setup, `npm
    ci` fails or installs somewhere else or the package layout moves, the axe
    test skips, the suite says green, and the accessibility claim in the README
    is now measured against zero pages. That is the same shape as the
    `_fabricated` substring guard, the hand-maintained `PAGES` list and the
    receipt-link matcher that passed its own mutation: a check with no way to
    fail on the thing it is named after.

    So the documented command sets `CID_AXE_REQUIRED=1`, and with it set this
    asserts that axe actually ran. It reads `_AXE_SCANS`, which is appended only
    after `axe.run` returns for a page, so it fails on a skip, on a browser that
    would not launch, and on a page list that quietly emptied. Without the
    variable it skips, because the base and Playwright tiers do not carry
    axe-core and must not be failed for it.

    This file's tests run in definition order, so the scan is recorded before
    this reads it.
    """
    if not os.environ.get("CID_AXE_REQUIRED"):
        pytest.skip("CID_AXE_REQUIRED unset; the accessibility tier was not requested")

    have_playwright = importlib.util.find_spec("playwright.sync_api") is not None
    assert _AXE_SCANS, (
        "CID_AXE_REQUIRED is set, so the documented accessibility command is "
        "running, and no axe scan executed: the tier reported green having "
        "measured nothing. axe-core source: "
        f"{_axe_source_path() or 'not found, run npm ci in the repo root'}; "
        f"playwright: {'importable' if have_playwright else 'absent, pip install playwright'}"
    )
