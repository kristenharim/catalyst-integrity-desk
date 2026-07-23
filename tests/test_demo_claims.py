"""Every quantitative claim spoken in the demo traces to the frozen artifact.

`docs/DEMO.md` is a claim-bearing document: it is read aloud on camera, and a
figure in it that the console does not back is the same failure the whole project
exists to prevent, one layer out. The demo is spoken, so its figures are spelled
in words -- "six hundred and seventy seven", not "677" -- and a digit scan cannot
see them. So this guard is explicit: each spoken figure is pinned to the demo
snapshot field it encodes, and the pin fails if the snapshot moves and the word
does not.

What is enforced:

  - the anchor figure is a bound, not a bare number. The registered date is
    `2022-06`, a month with no day; the console reads it as the first of the
    month, the longer reading, so both the first-of-month days and the
    end-of-month days are derived from the snapshot and both must be spoken, with
    the conservative one available.
  - the break figures (the two gaps, the two dates, the command-bar counts) match
    the demo snapshot.
  - the refused comparison is gone. The replacement trial's date moved across a
    scope change, so its movement is not a slip and cannot be a demo fact; the
    number must not appear.
  - a claim the replay cannot support is gone. The registry replay shows what the
    registry showed, not the absence of a press release or an 8-K.
  - any remaining digit in a spoken line is a snapshot value or a named source.
"""
import json
import os
import re
import sys
from datetime import date

import pytest

REPO = os.path.join(os.path.dirname(__file__), "..")
DEMO_PATH = os.path.join(REPO, "docs", "DEMO.md")
SNAP_PATH = os.path.join(REPO, "data", "snapshot.json")


def _load():
    with open(DEMO_PATH) as f:
        demo = f.read()
    with open(SNAP_PATH) as f:
        snap = json.load(f)
    return demo, snap


def _eom(ym: str) -> date:
    """A month-only registry date at the last day of the month."""
    import calendar
    y, m = (int(x) for x in ym.split("-")[:2])
    return date(y, m, calendar.monthrange(y, m)[1])


def _fom(ym: str) -> date:
    y, m = (int(x) for x in ym.split("-")[:2])
    return date(y, m, 1)


def _anchor_days(snap: dict) -> tuple[int, int, str]:
    """(first-of-month days, end-of-month days, expired date) for the 677 case.

    The carried-expired revision on Rocket's lapsed trial carries `days_expired`,
    the first-of-month reading, and its own `submitted` is the correction date.
    The expired date is the previous kept revision's `pcd`. Both readings are
    derived here from the snapshot so neither is a literal the demo can drift.
    """
    revs = snap["contracts"]["RCKT"]["lapsed_history"][0]["revisions"]
    for i, r in enumerate(revs):
        if r.get("carried_expired"):
            expired_pcd = revs[i - 1]["pcd"]           # the date that had passed
            corrected = date.fromisoformat(r["submitted"])
            fom = r["days_expired"]
            eom = (corrected - _eom(expired_pcd)).days
            return fom, eom, expired_pcd
    raise AssertionError("no carried-expired revision on the Rocket lapsed trial")


def _spoken_lines(demo: str) -> list[str]:
    """The blockquote lines, which are what is read on camera."""
    return [ln for ln in demo.splitlines() if ln.lstrip().startswith(">")]


# Figures that are real but come from outside the demo snapshot, each named. This
# is the demo's NON_SNAPSHOT: a bare number in a spoken or claim line must be a
# snapshot value or appear here with its source.
NAMED_SOURCES = {
    "949": "BiopharmaWatch company count, cited in the prior-art table",
    "11,000": "BiopharmaWatch readout count, cited in the prior-art table",
    "12.2": "Shadbolt et al. median delay, cited",
    "33": "EY Beyond Borders runway share, cited",
    "677": "the first-of-month reading of the anchor date; always spoken bounded",
}


def test_the_refused_and_unsupported_claims_are_gone():
    """The 943 slip comparison and the external-disclosure claim must not appear.

    The replacement trial's date moved across a scope change, so `slip_days` is
    refused and the movement is not a fact. And the registry replay cannot
    establish that no press release or 8-K was filed.
    """
    demo, _ = _load()
    banned = {
        "943": "the refused slip comparison (scope changed, so it is not a slip)",
        "nine hundred and forty three": "the same, spelled",
        "No 8-K": "an external-disclosure absence the registry replay cannot show",
        "No press release": "the same",
        "Q1 2028": "an ungrounded illustrative date",
        "Q3 2027": "an ungrounded illustrative date",
    }
    found = [f"{p!r} ({why})" for p, why in banned.items() if p in demo]
    assert not found, "these must be removed from the demo:\n  " + "\n  ".join(found)


def test_the_anchor_figure_is_a_bound_not_a_bare_number():
    """Both readings of the month-only anchor date are spoken and snapshot-derived."""
    demo, snap = _load()
    fom, eom, expired = _anchor_days(snap)
    assert len(expired.split("-")) == 2, (
        f"the anchor expired date {expired} is not month-only, so the bound story "
        f"no longer applies; re-examine the demo's 677 framing")
    assert fom == 677 and eom == 648, (
        f"the anchor readings moved: first-of-month {fom}, end-of-month {eom}. "
        f"Update the spoken bound in docs/DEMO.md.")
    # Both readings must be spoken on camera, not only mentioned in a filming
    # note. Checked over the blockquote text, whitespace-collapsed, since the
    # fact wraps across lines.
    spoken = " ".join(" ".join(_spoken_lines(demo)).replace(">", " ").split())
    words = {677: "six hundred and seventy seven", 648: "six hundred and forty eight"}
    for val, spelled in words.items():
        which = "first-of-month" if val == fom else "end-of-month"
        assert spelled in spoken, (
            f"the spoken script must state the {which} reading {spelled!r} ({val})")
    # The longer figure is never stated as a bare "N days" fact in a spoken line.
    for ln in _spoken_lines(demo):
        assert not re.search(r"\b677 days\b", ln), (
            f"a spoken line states the first-of-month figure as a bare fact: {ln.strip()!r}")


def test_the_break_figures_match_the_demo_snapshot():
    """The gaps, the dates, and the command-bar counts are what the console holds."""
    demo, snap = _load()
    r = snap["redline"]
    cmd = snap["cmd_bar"]
    checks = [
        (round(r["prior_gap_months"], 1) == 8.4, "eight point four",
         "prior funding gap"),
        (round(-r["current_gap_months"], 1) == 14.5, "fourteen point five",
         "current funding gap"),
        (r["prior_pcd"].startswith("2026-05"), "May 2026", "prior completion date"),
        (r["current_pcd"].startswith("2028-04"), "April 2028", "current completion date"),
        (cmd["monitored"] == 4, "Four contracts", "monitored count"),
        (cmd["active_breaches"] == 2, "Two active breaches", "active breach count"),
        (cmd["lapsed_expectations"] == 3,
         "Three registered completion dates already lapsed", "lapsed count"),
    ]
    # Whitespace-collapsed, dropping blockquote continuations, because a spoken
    # phrase wraps across lines ("... already\n> lapsed").
    flat = " ".join(demo.replace("\n>", " ").split())
    for ok, phrase, what in checks:
        assert ok, (f"the demo snapshot's {what} no longer matches the spoken "
                    f"{phrase!r}; re-read docs/DEMO.md")
        assert phrase in flat, (f"the demo no longer speaks {phrase!r} for the {what}")


def test_every_digit_in_a_claim_line_traces():
    """A bare digit in demo prose is a snapshot value, a named source, or a date.

    Timing markers, ISO dates, markdown links and the citation table carry their
    own provenance and are excluded; what remains is claim prose.
    """
    demo, snap = _load()
    ok = _snapshot_representations(snap) | set(NAMED_SOURCES)

    lines, in_code, in_table = demo.splitlines(), False, False
    findings = []
    for i, raw in enumerate(lines, start=1):
        s = raw.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if s.startswith("## What already exists"):
            in_table = True
        elif s.startswith("## "):
            in_table = False
        if in_code or in_table:
            continue
        # strip timing markers (m:ss), ISO dates, and markdown link targets
        clean = re.sub(r"\b\d:\d\d\b", " ", raw)
        clean = re.sub(r"\b\d{4}-\d{2}(?:-\d{2})?\b", " ", clean)
        clean = re.sub(r"\[[^\]]*\]\([^)]*\)|https?://\S+", " ", clean)
        clean = re.sub(r"^\s*\d+\.\s", " ", clean)          # list ordinals
        for tok in re.findall(r"\d[\d,]*\.?\d*%?", clean):
            t = tok.rstrip("%").rstrip(".").rstrip(",")
            if re.fullmatch(r"\d{4}", t.replace(",", "")):   # a year
                continue
            if t in ok or t.replace(",", "") in ok:
                continue
            findings.append(f"docs/DEMO.md:{i}: untraceable {tok!r} in {s[:70]}")
    assert not findings, ("\n  ".join(findings)
                          + "\n\nAdd the number to NAMED_SOURCES with its source, "
                            "or remove it.")


def _snapshot_representations(snap: dict) -> set:
    """Digit representations of every value in the demo snapshot."""
    out = set()

    def walk(node):
        if isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
        elif isinstance(node, bool):
            return
        elif isinstance(node, (int, float)):
            out.add(str(node))
            out.add(f"{node:,}")
            if float(node) == int(node):
                out.add(str(int(node)))
            else:
                out.add(f"{node:.1f}")
                out.add(f"{abs(node):.1f}")

    walk(snap)
    fom, eom, _ = _anchor_days(snap)
    out.update({str(fom), str(eom)})
    return out
