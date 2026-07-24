"""The Decision Review screen, as rendered.

The middle of the spine. `/inbox` says which decision needs a human and
`/receipts/<entry_id>` records what the human decided; this is the page between
them, where the decision is actually read.

What these tests are for, in the order the page is argued:

  1. **Three states, three wires.** `tests/test_layering.py` proves the modules
     cannot see each other. This proves the page does not undo that: a tampered
     record must not move the evidence badge, a breached thesis must not accuse
     the record, and ruling on the workflow must not erase the breach. Three
     tests, one per pair, each driven against a real file on disk rather than a
     flag, because a state that flips because a test asked it to is evidence of
     nothing.
  2. **No control that cannot complete.** Exactly one challenge exists in this
     snapshot, so exactly one decision can be ruled on. Accept, Reject, Amend,
     Defer, Assign and Request evidence are asserted absent from every other
     review page, disabled ones included. A disabled button is a claim the desk
     could act if you asked properly, and it could not.
  3. **The deterministic account comes before the model's prose.** Position, not
     presence: both are on the page and the reader must reach Python's first.
  4. **Refused, contingent, unavailable.** The refusal outweighs the magnitude
     it refuses, the contingent case asks for a human rather than resolving
     itself, and missing evidence renders as unavailable rather than as blank.
"""
from __future__ import annotations

import json
import os
import re
import sys
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from console.app import SNAPSHOT_ID, app as flask_app  # noqa: E402
from orchestrator import lexicon  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = REPO / "data" / "snapshot.json"

# Every control this screen must not offer where it cannot carry it out. The
# six labels docs/plans/phase2-inbox-spec.md section 8 lists as unbacked for any
# decision other than the one pending redline.
INACTIVE_CONTROLS = ["Accept", "Reject", "Amend", "Defer", "Assign",
                     "Request evidence"]

# The elements that read naturally on a review screen and have no store behind
# them, same list the inbox is held to.
UNBACKED = [
    "opened", "days ago", "day ago", "in review", "deferred", "assigned",
    "assignee", "owner", "due date", "unread", "notification", "snooze",
]


def _snapshot() -> dict:
    return json.loads(SNAPSHOT_PATH.read_text())


def _review_url(ticker: str) -> str:
    snap = _snapshot()
    redline = snap.get("redline") or {}
    if redline.get("ticker") == ticker:
        return f"/decisions/{redline['card_id']}/review"
    return f"/decisions/{ticker}/review"


@pytest.fixture()
def client():
    """The console against the committed snapshot.

    `tests/conftest.py` redirects the three runtime paths into this test's own
    temp directory for every test in the suite, so this client starts from an
    empty decision record: nothing recorded, nothing ruled on.
    """
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


@pytest.fixture()
def isolated(tmp_path, monkeypatch):
    """A client whose ledger, review log and anchor live in tmp_path.

    Named explicitly even though conftest already isolates, because these tests
    mutate the ledger file to demonstrate tampering and need the directory they
    are mutating in hand.
    """
    monkeypatch.setattr("console.app.DECISIONS_PATH", str(tmp_path / "decisions.jsonl"))
    monkeypatch.setattr("console.app.REVIEW_LOG_PATH", str(tmp_path / "review_log.jsonl"))
    monkeypatch.setattr("console.app.ANCHOR_PATH", str(tmp_path / "ledger.anchor"))
    flask_app.config["TESTING"] = True
    return flask_app.test_client(), tmp_path


def _approve(client) -> None:
    client.post("/redline/decide", data={"verdict": "approve",
                                         "reason": "the registered date passed"})


class _Controls(HTMLParser):
    """The text of every element a human can operate.

    Read off the elements rather than off the page's raw text, because the words
    this screen must not offer as controls are words it legitimately uses in
    prose: RCKT's own trigger detail says a registered date "was never amended",
    and a substring search for "Amend" would fail on the sentence while missing
    an actual button. What matters is whether a reader can press it.
    """

    def __init__(self):
        super().__init__()
        self.controls: list[str] = []
        self._depth = 0
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag in ("button", "a", "summary") or (
                tag == "input" and d.get("type") in ("submit", "button")):
            self._depth += 1
            if tag == "input":
                self.controls.append((d.get("value") or "").strip())
                self._depth -= 1

    def handle_endtag(self, tag):
        if self._depth and tag in ("button", "a", "summary"):
            self.controls.append(" ".join(" ".join(self._buf).split()))
            self._buf = []
            self._depth -= 1

    def handle_data(self, data):
        if self._depth:
            self._buf.append(data)


def _controls(html: str) -> list[str]:
    p = _Controls()
    p.feed(html)
    return [c for c in p.controls if c]


def _text(html: str) -> str:
    """The page as a reader gets it: no stylesheet, no markup, entities decoded.

    Decoded on purpose. `&#9679;` is a bullet glyph and reads as the digits 9679
    to anything scanning the raw response, which is how a provenance check finds
    four numbers on a page that renders none.
    """
    body = re.sub(r"<style.*?</style>", " ", html, flags=re.S)
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", body)).split())


def _declarations(html: str, selector: str) -> dict[str, str]:
    """The declarations of one CSS rule served with the page."""
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", html)
    assert m, f"no rule for {selector} is served with the page"
    out = {}
    for decl in m.group(1).split(";"):
        if ":" in decl:
            prop, _, value = decl.partition(":")
            out[prop.strip()] = value.strip()
    return out


# ---------------------------------------------------------------------------
# The three axes stay on three wires, on the page as well as in the code
# ---------------------------------------------------------------------------
# tests/test_layering.py walks the import graph. These three drive the rendered
# page, because a view model is perfectly capable of collapsing three separate
# functions back into one badge.


def test_tampering_the_record_does_not_move_the_evidence_state(isolated):
    """Axis 3 fails and axis 1 does not notice.

    A byte inside a hashed payload is edited, which is the demonstration the
    anchor exists for. The decision record must say so and the evidence state
    must be exactly what it was, because the evidence is computed from a frozen
    snapshot that the ledger cannot reach.

    Verified failing by rendering the evidence badge from `record.state`: the
    thesis then reads repaired or broken depending on a file that says nothing
    about it, and this names both readings.
    """
    c, tmp = isolated
    url = _review_url("RCKT")
    expected = _snapshot()["contracts"]["RCKT"]["decision"]

    before = c.get(url).get_data(as_text=True)
    assert f'class="badge badge-{expected["evidence"]}"' in before
    assert "record intact" in before

    _approve(c)
    path = tmp / "decisions.jsonl"
    lines = path.read_text().splitlines(keepends=True)
    tampered = lines[0].replace('"version": 1', '"version": 2', 1)
    assert tampered != lines[0], "the mutation must change a hashed byte"
    path.write_text(tampered + "".join(lines[1:]))

    after = c.get(url).get_data(as_text=True)
    assert "record tampered" in after, "the record axis must report the edit"
    assert f'class="badge badge-{expected["evidence"]}"' in after, (
        "the evidence badge moved when the decision record was edited; the two "
        "axes are joined somewhere they must not be"
    )
    assert expected["evidence_label"] in _text(after)
    for t in expected["triggers"]:
        assert t["label"] in _text(after), (
            f"trigger {t['label']!r} disappeared when the record was tampered with"
        )


def test_a_breached_thesis_does_not_accuse_the_decision_record(client):
    """Axis 1 fails and axis 3 does not.

    RCKT reads `review_required` against an empty decision record. Nothing has
    been tampered with, so the page must not say anything has, and the reverse
    reading is the one that matters: a screen that flips the record badge on a
    breach would turn every broken thesis into an integrity incident.
    """
    body = client.get(_review_url("RCKT")).get_data(as_text=True)
    text = _text(body)

    assert "review required" in text, "RCKT's evidence state must render"
    assert "record intact" in text
    for word in ["record tampered", "record truncated"]:
        assert word not in text, (
            f"a breached thesis renders {word!r}; the evidence axis is driving "
            "the record axis"
        )
    # And the record statement is a page-level element, never inside a panel
    # that describes the thesis.
    panels = re.findall(r'<section class="panel[^"]*".*?</section>', body, re.S)
    assert panels, "the review panels must render"
    for panel in panels:
        assert "record-badge" not in panel, (
            "a decision panel carries the record-integrity badge; record "
            "integrity is a separate wire and must not ride on a thesis"
        )


def test_resolving_the_workflow_does_not_erase_the_evidence_breach(isolated):
    """Axis 2 moves and axis 1 stays where the evidence put it.

    A human accepts the redline. The workflow state becomes resolved and the
    decision leaves the inbox, which is what resolving means. The evidence state
    is a statement about the public record and no ruling changes it: the trial
    dates did not move because somebody agreed they had.

    Verified failing by deriving the evidence badge from `task.state`: the
    breach then reads intact the moment it is ruled on, which is the reading
    that would let a desk close a thesis by agreeing with it.
    """
    c, _ = isolated
    url = _review_url("RCKT")
    expected = _snapshot()["contracts"]["RCKT"]["decision"]

    before = c.get(url).get_data(as_text=True)
    assert "&#9679;</span> review required" in " ".join(before.split())

    _approve(c)

    after = c.get(url).get_data(as_text=True)
    assert "resolved" in _text(after), "the workflow axis must report the ruling"
    assert f'class="badge badge-{expected["evidence"]}"' in after, (
        "ruling on the decision moved its evidence state; a human agreeing with "
        "a breach does not un-break the thesis"
    )
    for t in expected["triggers"]:
        assert t["label"] in _text(after), (
            f"trigger {t['label']!r} disappeared once the task was resolved"
        )
    # The inbox is the one that empties, and it is a different question.
    assert "RCKT" not in _text(c.get("/inbox").get_data(as_text=True))


# ---------------------------------------------------------------------------
# No control that cannot complete
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ticker", ["PRME", "SRPT", "BEAM"])
def test_an_evidence_only_review_offers_no_control_it_cannot_carry_out(client, ticker):
    """The defect class this repo has spent nine commits correcting.

    Exactly one challenge exists, written in Python inside `make_snapshot.py`,
    and no rebuild reads the ledger. Every other decision has nothing to accept,
    reject, amend, defer or assign, so it offers none of them, disabled ones
    included.

    Verified failing by adding a disabled Accept/Reject pair to the approved-
    belief panel, which is the shape this defect takes by accident: it names
    both labels on all three decisions.
    """
    body = client.get(_review_url(ticker)).get_data(as_text=True)
    controls = _controls(body)

    offered = [c for c in controls
               if any(c.lower().startswith(label.lower())
                      for label in INACTIVE_CONTROLS)]
    assert not offered, (
        f"the {ticker} review offers {offered}, and nothing in this repo can "
        "carry any of them out. See docs/plans/phase2-inbox-spec.md section 8."
    )
    assert "<button" not in body and "<form" not in body, (
        f"the {ticker} review renders a form or a button; an evidence-only "
        "review has no write path behind it"
    )
    assert "disabled" not in body, (
        "a disabled control is still a claim the desk could act if asked "
        "properly, and on this decision it could not"
    )
    # A neutral way onward, so the page is a stop rather than a dead end.
    assert f'href="/contract/{ticker}"' in body, (
        "an evidence-only review must offer the way back to the evidence detail"
    )


def test_only_the_pending_redline_offers_the_ruling(client):
    """And the one that does posts to the write path that already exists."""
    body = client.get(_review_url("RCKT")).get_data(as_text=True)
    assert 'action="/redline/decide"' in body
    assert body.count("<form") == 1, "one decision, one form, one write path"
    for label in ("Accept", "Reject"):
        assert any(c.endswith(label) for c in _controls(body)), (
            f"the adjudicable decision must offer {label}"
        )


def test_the_ruling_lands_on_the_receipt_for_this_card(isolated):
    """The form is a second door onto one flow, not a second flow.

    `/redline/decide` seeds, bumps, anchors and hands off to the confirmation,
    which composes the receipt by `card_id`. Ruling from this screen has to
    produce exactly that entry, or the screen has grown a write path of its own.
    """
    c, tmp = isolated
    card_id = _snapshot()["redline"]["card_id"]

    r = c.post("/redline/decide", data={"verdict": "approve",
                                        "reason": "the registered date passed"})
    assert r.status_code == 302 and "/redline/confirm" in r.headers["Location"]

    entries = [json.loads(ln) for ln
               in (tmp / "decisions.jsonl").read_text().splitlines() if ln.strip()]
    mine = [e for e in entries if e["card"]["card_id"] == card_id]
    assert mine, "the ruling wrote no entry for this card"

    body = c.get("/redline/confirm?verdict=approve").get_data(as_text=True)
    assert mine[-1]["entry_hash"] in body
    assert mine[-1]["prev_hash"] in body

    # And the review screen now points at that receipt by its own hash.
    review = c.get(_review_url("RCKT")).get_data(as_text=True)
    assert f'href="/receipts/{mine[-1]["entry_hash"]}"' in review, (
        "the review screen must link the receipt for the entry the ruling wrote"
    )


# ---------------------------------------------------------------------------
# Python's account comes before the model's
# ---------------------------------------------------------------------------

def test_the_deterministic_explanation_precedes_the_granite_prose(client):
    """Position, not presence.

    Both are on the page. The reader must reach the account Python computed
    before the prose the model wrote about it, because the memo is persuasive
    and the derivation is the thing that can be checked.

    Verified failing by moving the memo panel above the grid: the offsets
    reverse and this names them.
    """
    body = client.get(_review_url("RCKT")).get_data(as_text=True)
    redline = _snapshot()["redline"]

    explanation = body.find("Why this requires review")
    memo = body.find("Integrity memo")
    assert explanation != -1, "the deterministic explanation must render"
    assert memo != -1, "the Granite memo must render"
    assert explanation < memo, (
        f"the model's prose is above Python's account: explanation at "
        f"{explanation}, memo at {memo}"
    )

    # The explanation is Python's, figure by figure, from named fields.
    head = body[explanation:memo]
    for figure in (redline["prior_pcd"], redline["current_pcd"],
                   redline["lapse_display"]["current_gap_1f"],
                   redline["breach"]["display"]["expected_low_1f"]):
        assert figure in head, (
            f"{figure!r} is not in the deterministic explanation, so the page "
            "reaches the memo before it has said what happened"
        )


def test_every_number_on_the_review_screen_comes_from_the_snapshot(client):
    """The provenance invariant, extended to the new page.

    Driven against an empty decision record on purpose. A recorded ruling puts
    ledger hashes on the page, which are digits from the decision record rather
    than from the snapshot; with nothing recorded, every token on screen has to
    be the snapshot's.

    The one subtraction is the snapshot's own content address, which is a hash
    OF the file and so cannot be a substring of it. It is blanked by its exact
    value rather than by a pattern, so nothing else can hide behind the
    allowance.

    Failure verification: a hardcoded '9999' added to the current-contract panel
    is named here as a token absent from snapshot.json.
    """
    raw = SNAPSHOT_PATH.read_text()
    for ticker in ("RCKT", "PRME", "SRPT", "BEAM"):
        body = client.get(_review_url(ticker)).get_data(as_text=True)
        rendered = _text(body).replace(SNAPSHOT_ID, " ")
        assert SNAPSHOT_ID in _text(body), (
            "the page no longer names the snapshot its states came from"
        )
        for token in re.findall(r"-?\d+(?:\.\d+)?", rendered):
            assert token in raw, (
                f"number token {token!r} on the {ticker} review is not in "
                "snapshot.json; it was computed or hardcoded in the view layer"
            )


# ---------------------------------------------------------------------------
# Refused, contingent, unavailable
# ---------------------------------------------------------------------------

def test_the_refusal_outweighs_the_magnitude_it_refuses(client):
    """A UI invariant: 'comparison refused' is louder than the movement.

    Two places on this screen state it, and both are checked: the trigger row,
    and the promise-identity drawer where the refused day count actually
    appears. Read off the declarations rather than asserted as a string, so
    reformatting the stylesheet cannot switch the check off.
    """
    body = client.get(_review_url("RCKT")).get_data(as_text=True)
    history = _snapshot()["contracts"]["RCKT"]["history"]

    label = body.find("comparison refused")
    detail = body.find("is not treated as delay")
    assert label != -1, "the refused-comparison trigger must render"
    assert detail != -1, "the refusal's own sentence must render"
    assert label < detail, "the refusal label must precede the reading it refuses"

    refusal = body.find("Comparison refused. Not comparable")
    magnitude = body.find(f"{history['slip_reported_days']} days, refused")
    assert refusal != -1, "the drawer must refuse the comparison in words"
    assert magnitude != -1, "the refused magnitude must be shown, not hidden"
    assert refusal < magnitude, (
        "the refused figure is above the refusal; that is the reading that gets "
        "quoted as a finding"
    )

    tl = _declarations(body, ".trigger-label")
    td = _declarations(body, ".trigger-detail")
    assert int(tl["font-weight"]) > int(td["font-weight"])
    assert float(tl["font-size"].rstrip("px")) >= float(td["font-size"].rstrip("px"))

    ref = _declarations(body, ".refusal")
    fig = _declarations(body, ".refused-figure")
    assert int(ref["font-weight"]) > 400 >= int(fig.get("font-weight", "400"))
    assert float(ref["font-size"].rstrip("px")) > float(fig["font-size"].rstrip("px")), (
        "the refusal is drawn smaller than the magnitude it refuses"
    )


def test_neither_the_refused_nor_the_contingent_reading_is_stated_as_delay(client):
    """The refused total may be shown and may not be summarised.

    `slip_reported_days` is the movement across every revision including the
    ones that changed the commitment's shape. It is on the page, marked refused.
    What must never appear is that figure described as a delay or a slip.
    """
    body = client.get(_review_url("RCKT")).get_data(as_text=True)
    text = _text(body)
    reported = str(_snapshot()["contracts"]["RCKT"]["history"]["slip_reported_days"])

    for phrase in [f"{reported} days late", f"delayed by {reported}",
                   f"slipped {reported}", f"{reported} days of delay",
                   f"{reported}-day delay", f"{reported} day delay"]:
        assert phrase not in text, (
            f"the refused movement is summarised as an established delay: {phrase!r}"
        )
    assert "not treated as delay" in text
    assert "not to be" in text and "read as delay" in text


def test_the_contingent_trigger_asks_a_human_rather_than_resolving_itself(client):
    """The contingent case is a question, and the page has to read as one.

    Recording that two endpoint descriptions name the same commitment has no
    store. The screen shows the two readings and says a human has to make the
    call, because a screen that quietly picked one would be inventing the
    ruling.
    """
    body = client.get(_review_url("RCKT")).get_data(as_text=True)
    contingent = [t for t in _snapshot()["contracts"]["RCKT"]["decision"]["triggers"]
                  if t["state"] == "contingent"]
    assert contingent, "the fixture expects RCKT to carry a contingent trigger"

    assert 'class="trigger tr-contingent"' in body, (
        "the contingent trigger must be marked as contingent, not folded into "
        "the deterministic ones"
    )
    ask = _text(body)
    assert "A human has to read the two descriptions" in ask
    assert "This screen cannot settle it and does not record an answer" in ask
    # And it does not offer to settle it either.
    assert not [c for c in _controls(body)
                if "resolve" in c.lower() or "same commitment" in c.lower()], (
        "the screen offers to resolve a contingent reading; nothing stores that "
        "ruling. See docs/plans/phase2-inbox-spec.md section 8."
    )


def test_the_unavailable_decision_states_unavailable_and_never_a_gap(client):
    """SRPT: unusable burn, so no comparable gap, and the absence is stated.

    Shown, never ranked. The evidence badge reads unavailable, the gap field
    says so in words rather than going blank, and the figure the calculation
    would produce is not offered as a comparable one.
    """
    body = client.get(_review_url("SRPT")).get_data(as_text=True)
    text = _text(body)
    srpt = _snapshot()["contracts"]["SRPT"]

    assert 'class="badge badge-unavailable"' in body
    assert "unavailable" in text
    assert "not rankable" in text, (
        "the absence of a comparable gap has to be stated, not left blank"
    )
    for note in srpt["runway"]["notes"]:
        assert note in text, "the reason the burn estimate is unusable must render"

    # The derivation is still shown, because hiding a hard case is worse than
    # showing it, and the refusal is above the figure it qualifies.
    refusal = body.find("Not comparable. The burn estimate under this")
    figure = body.find(f"{srpt['gap_months_1f']} months")
    assert refusal != -1, "the unusable burn must be named where the gap is derived"
    assert figure != -1, "the derivation is shown rather than hidden"
    assert refusal < figure, "the refusal must precede the figure it qualifies"

    # And it is not offered as a fact about the company anywhere above that.
    assert f"{srpt['gap_months_1f']} months" not in _text(body[:refusal]), (
        "the gap of an unusable burn estimate is rendered as if it were usable"
    )


def test_a_decision_id_that_resolves_to_nothing_says_so(client):
    """A miss, not a guess and not a nearby decision."""
    r = client.get("/decisions/not-a-decision/review")
    assert r.status_code == 404
    text = _text(r.get_data(as_text=True))
    assert "No decision with this id is in this snapshot" in text
    for heading in ("What changed", "Why this requires review",
                    "Current contract", "Evidence and calculations"):
        assert heading not in text, (
            f"the miss page renders {heading!r}; it is describing a decision it "
            "did not find"
        )


# ---------------------------------------------------------------------------
# What the screen may not grow
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ticker", ["RCKT", "PRME", "SRPT", "BEAM"])
def test_no_unbacked_element_renders_on_the_review_screen(client, ticker):
    body = client.get(_review_url(ticker)).get_data(as_text=True).lower()
    present = [w for w in UNBACKED if w in body]
    assert not present, (
        f"the {ticker} review renders {present}, which nothing in this repo "
        "stores. See docs/plans/phase2-inbox-spec.md section 8."
    )


@pytest.mark.parametrize("ticker", ["RCKT", "PRME", "SRPT", "BEAM"])
def test_the_review_screen_makes_no_forbidden_claim(client, ticker):
    violations = lexicon.scan(client.get(_review_url(ticker)).get_data(as_text=True))
    assert not violations, "\n  ".join(str(v) for v in violations)


def test_the_technical_evidence_is_behind_disclosure_and_needs_no_script(client):
    """Progressive disclosure with a native element, so it works without JS.

    The top layer states what happened. The derivation, the date precision, the
    promise identity, the provenance limits, the refused readings and the
    decision record are each one click away and none of them needs a script to
    open.
    """
    body = client.get(_review_url("RCKT")).get_data(as_text=True)
    assert "<script" not in body, "this screen runs no script"
    summaries = [c for c in _controls(body) if c]
    for drawer in ["Deterministic calculation", "Date precision",
                   "Promise identity", "Provenance limitations",
                   "refuses to use", "Decision record"]:
        assert any(drawer in s for s in summaries), (
            f"no disclosure drawer for {drawer!r}"
        )
    assert body.count("<details") >= 6


def test_the_reading_order_is_the_dom_order_the_hierarchy_asks_for(client):
    """What changed, why, approved, current, evidence, in that order.

    Asserted on the markup rather than on a screenshot, because the markup is
    what a screen reader, a keyboard and a 390px viewport all get. Desktop
    places the three panels into a row without moving them, so this order is
    also the mobile order.
    """
    body = client.get(_review_url("RCKT")).get_data(as_text=True)
    order = ["What changed", "Why this requires review", "Approved belief",
             "Current contract", "Evidence and calculations"]
    offsets = [body.find(h) for h in order]
    assert all(o != -1 for o in offsets), (
        f"a section is missing: {[h for h, o in zip(order, offsets) if o == -1]}"
    )
    assert offsets == sorted(offsets), (
        "the page does not read in the order the hierarchy asks for: "
        + ", ".join(f"{h}@{o}" for h, o in zip(order, offsets))
    )


def test_the_centre_panel_is_the_widest_column_on_a_desktop_grid(client):
    """Centre-panel dominance, read off the rule that produces it.

    The geometry is measured in a real browser by the accessibility tier; this
    pins the declaration so a reordered stylesheet fails in the base tier too.
    """
    body = client.get(_review_url("RCKT")).get_data(as_text=True)
    grid = re.search(r"@media \(min-width: 1024px\) \{(.*?)\n  \}\n", body, re.S)
    assert grid, "the desktop grid must be declared behind a min-width query"
    columns = re.search(r"grid-template-columns:\s*([^;]+);", grid.group(1))
    assert columns, "the desktop grid declares no columns"
    widths = [float(w.rstrip("fr")) for w in columns.group(1).split()]
    assert len(widths) == 3, f"expected three columns, got {columns.group(1)!r}"
    assert widths[1] == max(widths), (
        f"the centre panel is not the widest column: {widths}"
    )
