"""Every figure in the claim documents traces to the frozen snapshot.

This is the console's number-provenance test pointed at markdown, and it exists
because prose was the last unguarded surface in the project. Four rounds of
adversarial review found the measured figures clean every time and the retyped
ones wrong repeatedly:

  - a median printed as 106 where the snapshot holds 106.5, fixed in one file and
    missed in five other places
  - "at least once" silently dropped from a count, making the sentence
    arithmetically impossible against the figure two lines above it
  - a "median date revisions" column off by one, because the field it was typed
    from counts the initial registration as a revision
  - a phrase reported as corrected in two consecutive rounds whose replacement
    never matched and silently did nothing

None of those were caught by a human reader on the pass that introduced them. A
number in a document is a claim, and a claim nobody can recompute is a claim
nobody is checking.

The rule: every numeric token appearing in a table row or a bolded claim in a
claim document must either be a representation of a snapshot field, or be listed
in `NON_SNAPSHOT` with its source. The second list is the enforced version of the
write-up's "figures that are not snapshot fields" paragraph, which drifted out of
date twice while it lived only in prose.
"""
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from research import cohort

REPO = os.path.join(os.path.dirname(__file__), "..")

CLAIM_DOCS = ["README.md", "docs/WRITEUP.md", "docs/SUBMISSION.md",
              "docs/COHORT.md", "docs/STATUS.md"]

# Numbers that legitimately appear in a claim document and are not cohort
# measurements. Each needs a reason: the point is that the exceptions are
# enumerated somewhere a test can read, not asserted in a sentence.
NON_SNAPSHOT = {
    # the frame, which is stated rather than measured
    "2016": "frame start", "2023": "frame end", "01": "frame date part",
    "12": "frame date part", "31": "frame date part", "20260722": "draw seed",
    "3000": "enumeration cap per stratum", "2": "phase 2", "3": "phase 2/3",
    "240": "trials drawn", "60": "trials drawn per stratum", "4": "strata",
    # the snapshot's own identity
    "2026": "as-of / frozen-at year", "07": "as-of month", "22": "as-of day",
    # the regulation, quoted
    "42": "42 CFR 11.64", "11.64": "42 CFR 11.64", "1": "11.64(a)(1)(ii)",
    "30": "the 30-day update window",
    # the case study, derived in docs/BACKTEST.md and pinned by test_backtest.py
    "677": "NCT04248439 carried-expired days", "04248439": "NCT id",
    "2022": "NCT04248439 expiry year", "06": "expiry month",
    "2024": "correction year", "08": "correction day",
    "85": "677 percentile rank over stretches, store-derived",
    "67": "677 percentile rank over trials, store-derived",
    "159": "stretches at or below 677", "188": "industry stretches",
    "48": "industry trials with a carry", "84.6": "159/188 as a percentage",
    # the correction history, sourced from docs/BOB_LOG.md and git
    "169": "correction 1", "131": "correction 1", "179": "correction 1",
    "123": "correction 1", "37": "correction 1 inflation percent",
    "29": "correction 1, the retracted inflation percent",
    "1430": "correction 2", "1,430": "correction 2", "5": "correction 2",
    "3.5": "correction: contingency overstatement factor, convenience sample",
    "6.7": "correction: contingency rate on the convenience sample",
    "7": "correction 2", "52.4": "correction 8, retracted",
    "82.7": "correction 8, retracted", "43": "correction 8, retracted",
    "83.3": "correction 7, retracted", "96.7": "correction 7, retracted",
    "58": "correction 5, NIH before recovery", "99.9": "a mutation value",
    "8.4": "RCKT prior gap, from data/snapshot.json",
    "14.5": "RCKT recomputed gap, from data/snapshot.json",
    "9999": "a planted literal, quoted",
    # the promise/slip audit, pinned by tests/test_promise.py and docs/LIMITS.md
    "1,008": "NCT04248439 reported slip", "1008": "NCT04248439 reported slip",
    "422": "NCT04248439 established", "943": "NCT06092034 reported",
    "760": "SRPT reported", "2463": "SRPT reported", "1031": "SRPT established",
    "1826": "BEAM reported", "122": "PRME reported", "2,104": "max carry",
    # other projects' published figures, attributed in place
    "2003": "Lerner et al.", "12.2": "Shadbolt et al. median delay",
    # test counts, asserted by tests/test_console.py
    "165": "suite size", "166": "suite size with credentials",
    "8050": "default port", "5000": "the port it moved off",
    # structural
    "0": "zero", "100": "percent", "1100": "svg canvas width",
    "1280": "demo viewport", "800": "demo viewport",
}

_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?%?")
# Identifiers and paths are not claims: NCT ids, snapshot ids, file names and
# URLs all live in code spans or links and carry digits that mean nothing.
_CODE = re.compile(r"`[^`]*`|\[[^\]]*\]\([^)]*\)|https?://\S+")
# A bolded line is scanned only for statistic-shaped tokens. Ordinals, list
# numbering, clock times and "the 90 second tour" are not figures, and treating
# them as such buries the real ones.
_STAT = re.compile(r"^\d[\d,]*(?:\.\d+)?%$|^\d[\d,]*\.\d+$|^\d{3,}$")


def _representations(v) -> set:
    """Every way a number might legitimately be written in prose."""
    out = set()
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return out
    out.add(str(v))
    if float(v) == int(v):
        out.add(str(int(v)))
        out.add(f"{int(v):,}")
    for spec in ("{:.0f}", "{:.1f}", "{:.2f}"):
        out.add(spec.format(v))
    if 0 <= v <= 1:                      # rates, as the report formats them
        for spec in ("{:.0%}", "{:.1%}", "{:.2%}"):
            out.add(spec.format(v))
    return out


def _acceptable() -> set:
    snap = cohort.load_snapshot()
    if snap is None:
        return set()
    ok = set()

    def walk(node):
        if isinstance(node, dict):
            for x in node.values():
                walk(x)
        elif isinstance(node, list):
            for x in node:
                walk(x)
        else:
            ok.update(_representations(node))

    walk(snap)
    # data/snapshot.json is the console's frozen evidence, pinned by the console
    # provenance tests. Figures quoted from it are traceable, just to the other
    # artifact, so it counts as a source rather than as an exception.
    console = os.path.join(REPO, "data", "snapshot.json")
    if os.path.exists(console):
        with open(console) as f:
            walk(json.load(f))
    # Ratios between snapshot fields are legitimate derived figures, so the
    # handful the documents quote are accepted at one decimal place.
    S = snap["strata"]
    for a, b in (("trial_days_p50", "trial_days_p50"),
                 ("dead_days_p50", "dead_days_p50")):
        for x in S.values():
            for y in S.values():
                if x.get(a) and y.get(b):
                    ok.add(f"{y[b] / x[a]:.1f}")
    for cls, v in S.items():
        for k in ("carrying_now", "carrying_now_invisible_to_stretches",
                  "trials_with_lapse_to_estimate", "never_revised_and_carrying"):
            for d in ("carrying_now", "open_estimates", "trials_revising",
                      "never_revised", "n"):
                if v.get(d):
                    ok.update(_representations(v.get(k, 0) / v[d]))
        # days expressed in years
        for k in ("silent_carrier_days_p50", "carrying_days_since_expiry_p50"):
            if v.get(k):
                ok.add(f"{v[k] / 365.25:.1f}")
    ok |= set(NON_SNAPSHOT)
    return ok


def _claim_lines(text: str):
    """Table rows and bolded claims: where the figures actually live.

    Yields (lineno, line, strict). `strict` is True for table rows, where every
    numeric token is a figure, and False for bolded prose, where only
    statistic-shaped tokens are.
    """
    for i, raw in enumerate(text.splitlines(), start=1):
        line = _CODE.sub(" ", raw)
        s = line.strip()
        if s.startswith("|") and set(s) - set("|-: "):
            yield i, line, True
        elif "**" in line and _NUM.search(line):
            yield i, line, False


@pytest.mark.parametrize("doc", CLAIM_DOCS)
def test_every_figure_in_a_claim_traces_to_the_snapshot(doc):
    if cohort.load_snapshot() is None:
        pytest.skip("no snapshot frozen yet")
    path = os.path.join(REPO, doc)
    if not os.path.exists(path):
        pytest.skip(f"{doc} does not exist")
    ok = _acceptable()
    with open(path) as f:
        text = f.read()

    offenders = []
    for lineno, line, strict in _claim_lines(text):
        for tok in _NUM.findall(line):
            if not strict and not _STAT.match(tok):
                continue
            t = tok.rstrip("%") if tok.endswith("%") else tok
            if tok in ok or t in ok or t.replace(",", "") in ok:
                continue
            offenders.append(f"{doc}:{lineno}: {tok!r} in {line.strip()[:88]}")
    assert not offenders, (
        f"{len(offenders)} figure(s) in {doc} are neither a snapshot field nor a "
        f"listed exception:\n  " + "\n  ".join(offenders[:25])
        + "\n\nEither the number is wrong, or it is a real non-cohort figure and "
          "belongs in NON_SNAPSHOT with its source.")


def test_the_guard_catches_a_planted_wrong_figure():
    """Watched failing, because a provenance test that has only ever passed is
    not evidence. A digit changed anywhere in a claim must be rejected."""
    ok = _acceptable()
    if not ok:
        pytest.skip("no snapshot frozen yet")
    planted = "| INDUSTRY | 26.3% | 34 of 126 |"
    bad = [t for _, line, _s in _claim_lines(planted) for t in _NUM.findall(line)
           if t not in ok and t.rstrip("%") not in ok]
    assert "26.3%" in bad and "34" in bad, (
        "the guard accepted a figure that is in no snapshot field; it would not "
        "have caught the 106-versus-106.5 error it was written for")


def test_a_hedge_present_in_most_claim_docs_is_present_in_all():
    """Cross-document consistency, added because one fix pass deleted the only
    hedge in `docs/SUBMISSION.md` while the other four kept theirs, and the
    externally-facing document was the one left unqualified.

    The rule is mechanical: if a document states the headline claim, it carries a
    qualifier on it.
    """
    claim = "cannot separate reconciliation from filing frequency"
    cues = ("not a tested", "untested", "ordering across four",
            "an association", "not separable")
    offenders = []
    for doc in CLAIM_DOCS:
        path = os.path.join(REPO, doc)
        if not os.path.exists(path):
            continue
        text = open(path).read().lower()
        if claim in text and not any(c in text for c in cues):
            offenders.append(doc)
    assert not offenders, (
        f"these state the headline claim with no qualifier anywhere in the "
        f"document: {offenders}. Four strata ordering the same way is an "
        f"ordering, not a tested relationship, and every document that makes the "
        f"claim says so or none should.")


def _headline_row(text: str, cls: str):
    for line in text.splitlines():
        if line.strip().startswith(f"| {cls} |"):
            return line
    return None


def test_the_headline_table_binds_cell_by_cell_to_named_fields():
    """Correspondence, not presence.

    The token-presence test above cannot catch a small-integer error: reverting
    the median-date-changes column from 0 to 1 passes it, because "1" appears
    somewhere in the snapshot and in the regulation citation. That is the same
    limit `docs/LIMITS.md` records for the console's provenance test, and it is
    precisely the defect class that shipped (a column off by one).

    So the headline table's last two columns are bound to the fields they claim
    to render, by name, per stratum. Watched failing: restoring the off-by-one
    fails this.
    """
    snap = cohort.load_snapshot()
    if snap is None:
        pytest.skip("no snapshot frozen yet")
    text = open(os.path.join(REPO, "docs", "WRITEUP.md")).read()
    for cls, v in snap["strata"].items():
        row = _headline_row(text, cls)
        if row is None:
            continue
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        # ... | median registry versions | median date changes |
        versions, changes = cells[-2], cells[-1]
        assert versions == f"{v['median_versions']:g}", (
            f"{cls}: median registry versions reads {versions!r}, field says "
            f"{v['median_versions']:g}")
        assert changes == f"{v['median_date_changes']:g}", (
            f"{cls}: median date changes reads {changes!r}, field "
            f"`median_date_changes` says {v['median_date_changes']:g}. Note "
            f"`n_pcd_revisions` counts the initial registration and is NOT this "
            f"number; typing from it is what produced the published off-by-one.")


def test_n_pcd_revisions_is_not_the_number_of_changes():
    """The field-level root cause, asserted so the trap cannot be re-entered.

    67 trials in this cohort have `n_pcd_revisions == 1` and have never changed
    a date. A field named "revisions" whose value includes the initial
    registration already misled one published column.
    """
    rows = [r for r in cohort.load_results() if "error" not in r]
    if not rows:
        pytest.skip("no cohort measured yet")
    never = [r for r in rows if not r.get("n_date_changes")]
    assert never, "expected trials that never changed a date"
    assert all(r.get("n_pcd_revisions") == 1 for r in never), (
        "a trial that never changed its date should carry n_pcd_revisions == 1")
    for r in rows:
        assert r["n_date_changes"] == max(0, (r.get("n_pcd_revisions") or 0) - 1)
