"""The revision timelines have to be readable, and readable is checkable.

SRPT's NCT06246513 shipped with three revisions, two of them filed two days
apart at the end of a 397-day span. The layout placed nodes by date and nothing
else, so those two label pairs landed 4.9px apart and rendered as four lines of
text on top of each other. The same canvas was 1100px wide in the placement code
and 1220px wide in the template, so the right-hand "carried expired" label sat
outside the panel and was cut off by its own container.

Neither is visible from a passing render: the page returns 200 with the text
unreadable. So the checks are geometric, over the committed snapshot, and they
are the ones a reader would make with a ruler:

  - no two labels on the same row are closer than a label is wide
  - every label, at its full width, falls inside the drawn canvas
  - the canvas is tall enough for the deepest row it stacked
  - each lapsed timeline's heading date belongs to that timeline's own trial

The last one is not a layout property. `build()` drops the lapsed trials whose
history would not fetch, so `lapsed_history` is shorter than `lapsed` the moment
one fetch fails, and the heading used to read its date out of the position-
matched slot of the other list. That prints one trial's id beside another
trial's completion date, silently, and only when a fetch fails.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from console.make_snapshot import (  # noqa: E402
    SVG_LABEL_GAP, SVG_PAD, SVG_ROW_H, SVG_WIDTH,
    _add_svg_x, _join_lapsed_pcd, _svg_height,
)

SNAPSHOT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "snapshot.json")

# "carried expired · NNN days" is the widest label a node carries: 26 monospace
# characters at font-size 10, which SF Mono renders at about 6px each.
WIDEST_LABEL = 26 * 6


def _timelines():
    """Every revision timeline the detail page draws, as (name, history dict)."""
    with open(SNAPSHOT_PATH) as f:
        snap = json.load(f)
    for ticker, c in snap["contracts"].items():
        for h in [c.get("history"), *(c.get("lapsed_history") or [])]:
            if h and h.get("revisions"):
                yield f"{ticker}/{h['nct']}", h


@pytest.mark.parametrize("name,history", list(_timelines()))
def test_labels_on_one_row_do_not_collide(name, history):
    rows: dict[int, list[float]] = {}
    for r in history["revisions"]:
        rows.setdefault(r["label_row"], []).append(r["svg_x"])
    for row, xs in rows.items():
        xs.sort()
        for left, right in zip(xs, xs[1:]):
            assert right - left >= SVG_LABEL_GAP, (
                f"{name}: two labels on row {row} are {right - left:.1f}px apart, "
                f"under the {SVG_LABEL_GAP}px a date label needs, so they overlap"
            )


@pytest.mark.parametrize("name,history", list(_timelines()))
def test_every_label_falls_inside_the_canvas(name, history):
    half = WIDEST_LABEL / 2
    for r in history["revisions"]:
        assert SVG_PAD <= r["svg_x"] <= SVG_WIDTH - SVG_PAD, (
            f"{name}: node at x={r['svg_x']} is outside the padded span"
        )
        assert 0 <= r["svg_x"] - half and r["svg_x"] + half <= SVG_WIDTH, (
            f"{name}: the label centred on x={r['svg_x']} runs past the canvas edge"
        )


@pytest.mark.parametrize("name,history", list(_timelines()))
def test_canvas_is_tall_enough_for_its_deepest_label(name, history):
    deepest = max(r["y_pcd"] for r in history["revisions"])
    assert history["svg_height"] >= deepest, (
        f"{name}: canvas is {history['svg_height']}px tall and the lowest label "
        f"sits at y={deepest}, so it is drawn outside the viewBox"
    )


def test_lapsed_heading_date_is_joined_on_the_trial_id():
    """A missing history must not slide the next trial's date up the list."""
    lapsed = [{"nct": "NCT-A", "pcd": "2025-01-01"},
              {"nct": "NCT-B", "pcd": "2026-02-02"}]
    # NCT-A's history did not fetch, so only NCT-B's survives to be serialised.
    lapsed_history = [{"nct": "NCT-B"}]
    _join_lapsed_pcd(lapsed_history, lapsed)
    assert lapsed_history[0]["lapsed_pcd"] == "2026-02-02"


def test_collision_stacks_downward_and_keeps_the_true_position():
    """Two revisions days apart keep their x and get separate label rows."""
    revisions = [
        {"submitted": "2024-01-30", "carried_expired": False},
        {"submitted": "2025-02-28", "carried_expired": True},
        {"submitted": "2025-03-02", "carried_expired": False},
    ]
    _add_svg_x(revisions)
    assert revisions[1]["svg_x"] < revisions[2]["svg_x"] <= SVG_WIDTH - SVG_PAD
    assert revisions[2]["svg_x"] - revisions[1]["svg_x"] < SVG_LABEL_GAP  # still collide
    assert revisions[1]["label_row"] == 0 and revisions[2]["label_row"] == 1
    assert revisions[2]["y_submitted"] - revisions[1]["y_submitted"] >= SVG_ROW_H
    assert _svg_height(revisions) >= revisions[2]["y_pcd"]
