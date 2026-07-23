"""The demo's opening frame, asserted as geometry rather than as document order.

`docs/STATUS.md` calls this the rule that outranks the rest: the carried-expired
row is the only thing in the demo the room has not seen before, so it must be
visible without scrolling and without a click. That was measured true at 1280x800
on 2026-07-21 and then quietly stopped being true, because the thesis-break chart
and the binding trial's revision panel were added above it and pushed the node to
y=992 against an 800px fold. Every test stayed green, because the only thing any
of them checked was that the number appeared somewhere in the HTML.

Presence is not position. A demo narrated over the wrong screen is the failure
this file exists to prevent, so the load-bearing check here opens a real browser
at a real viewport and reads real bounding boxes.
"""
from __future__ import annotations

import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from console.app import app as flask_app  # noqa: E402

REPO = os.path.join(os.path.dirname(__file__), "..")
FOLD_W, FOLD_H = 1280, 800


@pytest.fixture(scope="module")
def live_server():
    """The console on an ephemeral port, so the browser loads the real thing."""
    from werkzeug.serving import make_server

    server = make_server("127.0.0.1", 0, flask_app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.port}"
    finally:
        server.shutdown()


# ---------------------------------------------------------------------------
# Document order: cheap, runs everywhere, and catches the regression that
# happened. It is not the real check -- see the geometry test below.
# ---------------------------------------------------------------------------

def test_lapsed_anchor_section_precedes_the_thesis_break_chart():
    client = flask_app.test_client()
    body = client.get("/contract/RCKT").get_data(as_text=True)
    lapsed = body.find("LAPSED registered completion")
    chart = body.find("Thesis break")
    assert lapsed != -1, "the lapsed registered-completion section must render on RCKT"
    assert chart != -1, "the thesis-break chart must render on RCKT"
    assert lapsed < chart, (
        "the lapsed section carrying the anchor case must open the page, above the "
        f"thesis-break chart; found lapsed at offset {lapsed}, chart at {chart}"
    )


# ---------------------------------------------------------------------------
# Geometry: the real check.
# ---------------------------------------------------------------------------

def _frame_nodes(page):
    """Every node of interest on the opening frame, with its box and weight."""
    return page.evaluate(
        """() => {
          const out = [];
          const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
          let n;
          while ((n = w.nextNode())) {
            const t = n.textContent.replace(/\\s+/g, ' ').trim();
            if (!t) continue;
            if (!/(carried expired|Not comparable|943 days)/i.test(t)) continue;
            const el = n.parentElement;
            const r = el.getBoundingClientRect();
            const cs = getComputedStyle(el);
            out.push({text: t, top: r.top,
                      size: parseFloat(cs.fontSize),
                      weight: parseInt(cs.fontWeight, 10) || 400});
          }
          return out;
        }"""
    )


def test_demo_opening_frame_at_1280x800(live_server):
    """The anchor case is above the fold and nothing unrelated outranks it.

    Skips without playwright or its browser. That is a real gap and it is
    recorded in docs/LIMITS.md rather than hidden: on a machine with neither,
    only the document-order check above runs, and document order is not
    position.
    """
    if os.environ.get("CID_BASE_DEPS_ONLY"):
        # The clean-checkout tier is defined as `pip install -r requirements.txt`
        # and nothing else. Playwright lives in the environment rather than the
        # repo, so a developer machine would otherwise measure a tier no judge
        # can reproduce. See test_console.py's count guard, which sets this.
        pytest.skip("base dependencies only; playwright is a development extra")
    pytest.importorskip(
        "playwright.sync_api",
        reason="playwright is absent; the demo frame's geometry cannot be measured",
    )
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:                                # noqa: BLE001
            pytest.skip(f"no playwright browser installed: {exc}")
        try:
            page = browser.new_page(viewport={"width": FOLD_W, "height": FOLD_H})
            page.goto(f"{live_server}/demo", wait_until="load")
            assert page.evaluate("window.scrollY") == 0, "the frame must be unscrolled"
            nodes = _frame_nodes(page)
        finally:
            browser.close()

    def one(pattern):
        hits = [n for n in nodes if pattern.lower() in n["text"].lower()]
        assert len(hits) == 1, f"expected exactly one {pattern!r} node, got {hits}"
        return hits[0]

    anchor = one("carried expired · 677 days")
    other = one("carried expired · 30 days")
    refusal = one("Not comparable")
    refused_number = one("943 days")

    # 1. The anchor case is on screen without scrolling.
    assert 0 <= anchor["top"] < FOLD_H, (
        f"the 677-day anchor row must be visible at {FOLD_W}x{FOLD_H} without "
        f"scrolling; its top is {anchor['top']:.0f}px against a {FOLD_H}px fold"
    )

    # 2. The unrelated current-trial figure does not lead the frame. It belongs
    #    to a different trial and is a fifth the size of the anchor carry, so a
    #    viewer who sees only that one has been told the wrong fact.
    assert anchor["top"] < other["top"], (
        f"the 30-day figure of the binding trial must not sit above the 677-day "
        f"anchor case; 677 at {anchor['top']:.0f}px, 30 at {other['top']:.0f}px"
    )

    # 3. The refused comparison stays subordinate to its refusal.
    assert refusal["top"] <= refused_number["top"], (
        "the refusal label must precede the number it refuses; "
        f"label at {refusal['top']:.0f}px, 943 at {refused_number['top']:.0f}px"
    )
    assert (refusal["weight"], refusal["size"]) >= (refused_number["weight"],
                                                    refused_number["size"]), (
        "the refusal label must not be rendered more quietly than the refused "
        f"number; label {refusal['weight']}/{refusal['size']}px, "
        f"943 {refused_number['weight']}/{refused_number['size']}px"
    )


# ---------------------------------------------------------------------------
# Screen and script
# ---------------------------------------------------------------------------

def test_demo_script_speaks_the_figure_the_screen_shows():
    """The narration and the opening frame must name the same reading.

    `docs/DEMO.md` requires the conservative end-of-month reading to be spoken
    first, with the first-of-month figure second, because the console renders
    only the first-of-month one. If the screen's figure ever stops being the
    one the script calls first-of-month, the narration is describing a frame
    the viewer is not looking at.
    """
    import json

    snap = json.load(open(os.path.join(REPO, "data", "snapshot.json")))
    revisions = snap["contracts"]["RCKT"]["lapsed_history"][0]["revisions"]
    carried = [r["days_expired"] for r in revisions if r.get("carried_expired")]
    assert carried, "the RCKT lapsed history must carry an expired-date revision"
    shown = max(carried)

    script = open(os.path.join(REPO, "docs", "DEMO.md")).read()
    words = {648: "six hundred and forty eight", 677: "six hundred and seventy seven"}
    assert shown in words, (
        f"the screen shows {shown} days, which docs/DEMO.md has no spoken form for"
    )
    assert words[shown] in script, (
        f"the screen shows {shown} days but docs/DEMO.md never speaks it"
    )

    # The ordering rule governs the spoken line, not the guidance note above it:
    # the note names the figure the console renders first, on purpose, because it
    # is explaining what the screen shows. Scope to the narration beat.
    start = script.index("0:20 to 0:50")
    spoken = script[start:script.index("0:50 to 1:25", start)]
    assert words[648] in spoken and words[677] in spoken, (
        "the 0:20 beat must speak both readings of the month-only date; it says "
        f"{[w for w in words.values() if w in spoken]}"
    )
    assert spoken.index(words[648]) < spoken.index(words[677]), (
        "the spoken line must give the conservative end-of-month reading before "
        "the first-of-month figure the console renders"
    )
