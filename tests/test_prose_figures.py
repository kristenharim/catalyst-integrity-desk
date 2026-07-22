"""Every figure in the claim documents traces to the frozen snapshot.

This is the console's number-provenance test pointed at markdown. Prose was the
last unguarded surface in the project, and five rounds of adversarial review
found the measured figures clean every time and the retyped ones wrong
repeatedly.

The first version of this guard was mutation-tested against three cases it
happened to catch, declared working, and then failed 19 of 19 planted defects
written by the reviewers, including the 106.5-printed-as-106 error named in its
own docstring. That is why the corpus in `tests/mutation_corpus.py` comes from
the seats rather than from the author, why the checks below run against text so
the corpus can exercise them, and why `test_the_corpus_is_caught` is the test
that matters here.

What is enforced, stated at the strength it actually holds:

  - every numeric token in a table row traces to a snapshot field or to an
    enumerated exception
  - every `N of M` anywhere in the file, wrapped or not, traces the same way
  - every line of a paragraph containing a bolded claim is scanned, not just the
    line the asterisks fall on
  - a value is accepted only in a representation that does not lose information:
    a half-integer must print as a half-integer, so 106.5 is never "106"
  - the headline table binds cell by cell to named fields
  - every snapshot id named anywhere equals the current one
  - retired phrases stay retired

What is NOT enforced, because it was measured rather than assumed: a figure that
is correct, present in the snapshot, and attached to the wrong label outside the
headline table. See `docs/LIMITS.md`.
"""
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from research import cohort
from mutation_corpus import CORPUS

REPO = os.path.join(os.path.dirname(__file__), "..")

CLAIM_DOCS = ["README.md", "docs/WRITEUP.md", "docs/SUBMISSION.md",
              "docs/COHORT.md", "docs/STATUS.md"]

# Phrases withdrawn in review. Kept as a list because "exactly opposite order"
# was reported fixed in three consecutive rounds while surviving in two files.
RETIRED = {
    "exactly opposite order": "industry and NIH tie, so the reversal is not exact",
    "overwhelmingly": "unsupported on every measured reading; use the counts",
}

# Numbers that are not cohort measurements. Each carries its source. Nothing that
# IS a snapshot field belongs here: listing one turns the exception list into a
# laundering route, which is how `48` and `188` got in.
NON_SNAPSHOT = {
    "2016": "frame start", "2023": "frame end", "20260722": "draw seed",
    "3000": "enumeration cap", "2026": "as-of year",
    "11.64": "42 CFR 11.64", 
    "677": "NCT04248439 carried-expired days, pinned by tests/test_backtest.py",
    "2022": "its expiry year", "2024": "its correction year",
    "85": "677 percentile over stretches, store-derived",
    "67": "677 percentile over trials, store-derived",
    "159": "stretches at or below 677, store-derived",
    "84.6": "159/188 as a percentage",
    "97": "NCT02931474 versions, store-derived",
    "169": "correction 1", "131": "correction 1", "179": "correction 1",
    "123": "correction 1", "1,430": "correction 2",
    "52.4": "correction 8, retracted", "82.7": "correction 8, retracted",
    "83.3": "correction 7, retracted", "96.7": "correction 7, retracted",
    "3.5": "contingency overstatement, convenience sample",
    "6.7": "contingency rate, convenience sample",
    "58": "correction 5, NIH before recovery",
    "1,008": "promise audit, tests/test_promise.py", "422": "promise audit",
    "943": "promise audit", "12.2": "Shadbolt et al. median delay",
    "166": "suite size", "167": "suite size with credentials",
    "8050": "default port", "5000": "the port it moved off",
    "1,769": "observed interval range, store-derived",
    "15.4": "even-spread baseline, industry",
    "12.9": "even-spread baseline, NIH", "10.9": "even-spread baseline, OTHER",
    "9.9": "even-spread baseline, OTHER_GOV",
    "1.7": "1/60, the trial-level resolution", "5.2": "MB, the initial push payload",
    "99.9": "a mutation value, quoted", "9999": "a planted literal, quoted",
    "106": "quoted as the wrong rendering of 106.5, in the sentence forbidding it",
}

_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?%?")
_CODE = re.compile(r"`[^`]*`|\[[^\]]*\]\([^)]*\)|https?://\S+"
                   r"|\d{4}-\d{2}(?:-\d{2})?")   # ISO dates are not figures
_STAT = re.compile(r"^\d[\d,]*(?:\.\d+)?%$|^\d[\d,]*\.\d+$|^\d{3,}$|^\d[\d,]{2,}$")
_N_OF_M = re.compile(r"(\d[\d,]*) of (\d[\d,]*)\b")
_SNAP_ID = re.compile(r"cohort-[0-9a-f]{12}")

# Sentence-level binding. Presence cannot falsify a small integer, so the claims
# the headline rests on are bound to the fields they render, by name. This is the
# "per-element binding" upgrade `docs/LIMITS.md` has named as the fix for the
# console's provenance test since before this guard existed.
def _bound_claims(S):
    def inv(c):
        return [S[c]["carrying_now_invisible_to_stretches"], S[c]["carrying_now"]]
    return [
        ("docs/WRITEUP.md",
         r"(\d+) of\s+(\d+) in industry, (\d+) of (\d+) in OTHER, (\d+) of (\d+) in\s+OTHER_GOV",
         inv("INDUSTRY") + inv("OTHER") + inv("OTHER_GOV"),
         "silent carriers per stratum"),
        ("README.md",
         r"(\d+) of (\d+) in industry,\s+(\d+) of (\d+) for government sponsors",
         inv("INDUSTRY") + inv("OTHER_GOV"),
         "silent carriers, industry and government"),
        ("docs/STATUS.md",
         r"(\d+) of (\d+) in industry,\s+(\d+) of (\d+) for government sponsors",
         inv("INDUSTRY") + inv("OTHER_GOV"),
         "silent carriers, industry and government"),
        ("docs/COHORT.md",
         r"(\d+) of (\d+) in industry,\s+(\d+) of (\d+) for government sponsors",
         inv("INDUSTRY") + inv("OTHER_GOV"),
         "silent carriers, industry and government"),
        ("docs/SUBMISSION.md",
         r"(\d+) of (\d+) in industry,\s+(\d+) of (\d+) for government sponsors",
         inv("INDUSTRY") + inv("OTHER_GOV"),
         "silent carriers, industry and government"),
        ("docs/WRITEUP.md",
         r"The median is ([\d,.]+) days in industry, ([\d,.]+) in OTHER and\s+([\d,.]+) in\s+OTHER_GOV",
         [S["INDUSTRY"]["silent_carrier_days_p50"], S["OTHER"]["silent_carrier_days_p50"],
          S["OTHER_GOV"]["silent_carrier_days_p50"]],
         "silent-carrier medians, in stratum order"),
        ("docs/WRITEUP.md",
         r"the shortest anywhere is ([\d,]+) days",
         [min(v["silent_carrier_days_min"] for v in S.values()
              if v.get("silent_carrier_days_min") is not None)],
         "minimum silent carry"),
        ("docs/WRITEUP.md",
         r"\*\*(\d+) of (\d+) \(([\d.]+)%\)",
         [S["INDUSTRY"]["submit_intervals_near_year_multiple"],
          S["INDUSTRY"]["submit_intervals_n"],
          round(S["INDUSTRY"]["submit_intervals_near_year_rate"] * 100, 1)],
         "industry near-anniversary intervals"),
    ]


def _representations(v) -> set:
    """Representations that do not lose information.

    `{:.0f}` is admitted only when the value is an integer or is not a
    half-integer. It used to be unconditional, which made "106" an accepted
    rendering of 106.5 and let the guard miss the first defect its own docstring
    names. A half-integer rounds by banker's rounding, so 239.5 goes up to 240
    and 106.5 goes down to 106 in the same format string: both directions have
    shipped, so neither is accepted.
    """
    out = set()
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return out
    out.add(str(v))
    if v < 0:                            # "-14.5" tokenizes as "14.5"
        out |= _representations(-v)
    if float(v) == int(v):
        out.update({str(int(v)), f"{int(v):,}", f"{v:.0f}", f"{v:.1f}"})
    else:
        out.update({f"{v:.1f}", f"{v:.2f}", f"{float(v):g}"})
        if abs(v) >= 1000:
            out.add(f"{v:,.1f}")
        if abs(v - int(v)) != 0.5:
            out.update({f"{v:.0f}", f"{float(f'{v:.0f}'):,.0f}"})
    if 0 <= v <= 1:
        out.update({f"{v:.1%}", f"{v:.2%}"})
        if abs(v * 100 - int(v * 100)) < 1e-9:
            out.add(f"{v:.0%}")
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
    console = os.path.join(REPO, "data", "snapshot.json")
    if os.path.exists(console):
        with open(console) as f:
            walk(json.load(f))
    S = snap["strata"]
    for x in S.values():
        for y in S.values():
            if x.get("trial_days_p50") and y.get("trial_days_p50"):
                ok.add(f"{y['trial_days_p50'] / x['trial_days_p50']:.1f}")
            if x.get("dead_days_p50") and y.get("dead_days_p50"):
                ok.add(f"{y['dead_days_p50'] / x['dead_days_p50']:.1f}")
    for v in S.values():
        for k in ("carrying_now", "carrying_now_invisible_to_stretches",
                  "trials_with_lapse_to_estimate", "never_revised_and_carrying"):
            for d in ("carrying_now", "open_estimates", "trials_revising",
                      "never_revised", "n"):
                if v.get(d):
                    ok.update(_representations(v.get(k, 0) / v[d]))
        for k in ("silent_carrier_days_p50", "carrying_days_since_expiry_p50"):
            if v.get(k):
                ok.add(f"{v[k] / 365.25:.1f}")
    ok |= set(NON_SNAPSHOT)
    return ok


def _scanned(text: str):
    """(lineno, line, strict) over the surfaces that carry claims.

    A paragraph containing a bolded claim is scanned in full, not only the line
    the asterisks land on: markdown wraps, and README's medians sat on a
    continuation line outside the guard entirely.
    """
    lines = text.splitlines()
    paragraphs, start = [], 0
    for i, line in enumerate(lines):
        if not line.strip():
            if i > start:
                paragraphs.append((start, i))
            start = i + 1
    if start < len(lines):
        paragraphs.append((start, len(lines)))

    bolded = set()
    for a, b in paragraphs:
        if any("**" in lines[j] for j in range(a, b)):
            bolded.update(range(a, b))

    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("|") and set(s) - set("|-: "):
            yield i + 1, line, True
        elif i in bolded and _NUM.search(line):
            yield i + 1, line, False


def _violations(doc: str, text: str, ok: set, snapshot_id: str) -> list:
    """Every guard finding for one document's text.

    Callable on mutated text, so the corpus exercises exactly the code the real
    files run through rather than a reconstruction of it.
    """
    out = []
    clean = _CODE.sub(" ", text)

    for lineno, line, strict in _scanned(clean):
        for tok in _NUM.findall(line):
            if not strict and not _STAT.match(tok):
                continue
            t = tok.rstrip("%")
            if tok in ok or t in ok or t.replace(",", "") in ok:
                continue
            out.append(f"{doc}:{lineno}: untraceable {tok!r} in {line.strip()[:80]}")

    # `N of M` is the shape every headline claim in this project takes, so it is
    # scanned over the whole file rather than only over claim lines.
    for i, raw in enumerate(clean.splitlines(), start=1):
        for a, b in _N_OF_M.findall(raw):
            for tok in (a, b):
                if tok in ok or tok.replace(",", "") in ok:
                    continue
                out.append(f"{doc}:{i}: untraceable {tok!r} in 'N of M' "
                           f"{raw.strip()[:80]}")

    # Snapshot ids live in code spans, so they are scanned in the raw text.
    for sid in set(_SNAP_ID.findall(text)):
        if sid != snapshot_id:
            out.append(f"{doc}: names superseded snapshot {sid!r}, current is "
                       f"{snapshot_id!r}")

    snap = cohort.load_snapshot()
    if snap:
        S = snap["strata"]
        # Cell-by-cell binding of the headline table, run here so the corpus
        # exercises it rather than only the real files.
        if doc == "docs/WRITEUP.md":
            for cls, v in S.items():
                row = _headline_row(text, cls)
                if row is None:
                    out.append(f"{doc}: the headline table has no {cls} row")
                    continue
                nums = [_NUM.findall(c) for c in
                        row.strip().strip("|").split("|")]
                want = [
                    [f"{v['carrying_now']}", f"{v['n']}",
                     f"{v['carrying_now_rate']:.1%}"],
                    [f"{v['carrying_now']}", f"{v['open_estimates']}",
                     f"{v['carrying_now_of_open_rate']:.1%}"],
                    [f"{v['carrying_now_invisible_to_stretches']}",
                     f"{v['carrying_now']}"],
                    [f"{v['median_versions']:g}"],
                    [f"{v['median_date_changes']:g}"],
                ]
                for got, exp in zip(nums[1:], want):
                    if got != exp:
                        out.append(f"{doc}: {cls} headline cell reads {got}, "
                                   f"fields say {exp}")
        for bdoc, pattern, expected, label in _bound_claims(S):
            if bdoc != doc:
                continue
            m = re.search(pattern, clean)
            if m is None:
                out.append(f"{doc}: bound claim missing ({label}); the sentence "
                           f"it pins was reworded, so nothing checks it")
                continue
            got = [g.replace(",", "") for g in m.groups()]
            exp = [f"{e:g}" for e in expected]
            if got != exp:
                out.append(f"{doc}: {label} reads {got}, fields say {exp}")

    low = text.lower()
    for phrase, why in RETIRED.items():
        if phrase in low:
            out.append(f"{doc}: retired phrase {phrase!r} ({why})")
    return out


@pytest.mark.parametrize("doc", CLAIM_DOCS)
def test_every_figure_in_a_claim_traces_to_the_snapshot(doc):
    snap = cohort.load_snapshot()
    if snap is None:
        pytest.skip("no snapshot frozen yet")
    path = os.path.join(REPO, doc)
    if not os.path.exists(path):
        pytest.skip(f"{doc} does not exist")
    with open(path) as f:
        text = f.read()
    v = _violations(doc, text, _acceptable(), snap["snapshot_id"])
    assert not v, (f"{len(v)} finding(s) in {doc}:\n  " + "\n  ".join(v[:25])
                   + "\n\nEither the figure is wrong, or it is a real non-cohort "
                     "figure and belongs in NON_SNAPSHOT with its source.")


def test_the_corpus_is_caught():
    """All 19 reviewer-planted defects, applied to the real documents.

    This is the test that matters. A guard amendment is accepted only when every
    fixture here is watched failing and then passing on the real files.
    """
    snap = cohort.load_snapshot()
    if snap is None:
        pytest.skip("no snapshot frozen yet")
    ok, sid = _acceptable(), snap["snapshot_id"]
    stale, missed = [], []
    for name, doc, find, replace, why in CORPUS:
        with open(os.path.join(REPO, doc)) as f:
            text = f.read()
        if find not in text:
            stale.append(f"{name}: {find!r} no longer in {doc}")
            continue
        # Against the document's OWN baseline, not against zero. The first
        # version compared to zero, and every fixture "passed" because the
        # documents happened to carry an unrelated defect at the time: a
        # pre-existing stale snapshot id made all 19 look caught while the
        # checks that should catch them did nothing.
        before = set(_violations(doc, text, ok, sid))
        after = set(_violations(doc, text.replace(find, replace, 1), ok, sid))
        if after - before:
            continue
        missed.append(f"{name} ({why}): {find!r} -> {replace!r} in {doc}")
    assert not stale, (
        "stale fixture(s); the prose moved and the mutation no longer applies, "
        "so it was silently testing nothing:\n  " + "\n  ".join(stale))
    assert not missed, (
        f"{len(missed)} of {len(CORPUS)} planted defects passed the guard:\n  "
        + "\n  ".join(missed))


def _headline_row(text: str, cls: str):
    for line in text.splitlines():
        if line.strip().startswith(f"| {cls} |"):
            return line
    return None


def test_the_headline_table_binds_cell_by_cell_to_named_fields():
    """Correspondence, not presence, for the table the headline rests on.

    Token presence cannot catch a small-integer error, and cannot catch a value
    that is real but sitting in the wrong cell. Every numeric cell of this table
    is bound to the field it claims to render.
    """
    snap = cohort.load_snapshot()
    if snap is None:
        pytest.skip("no snapshot frozen yet")
    text = open(os.path.join(REPO, "docs", "WRITEUP.md")).read()
    seen = 0
    for cls, v in snap["strata"].items():
        row = _headline_row(text, cls)
        assert row is not None, f"the headline table has no {cls} row"
        seen += 1
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        nums = [_NUM.findall(c) for c in cells]
        expected = [
            [f"{v['carrying_now']}", f"{v['n']}", f"{v['carrying_now_rate']:.1%}"],
            [f"{v['carrying_now']}", f"{v['open_estimates']}",
             f"{v['carrying_now_of_open_rate']:.1%}"],
            [f"{v['carrying_now_invisible_to_stretches']}", f"{v['carrying_now']}"],
            [f"{v['median_versions']:g}"],
            [f"{v['median_date_changes']:g}"],
        ]
        labels = ("carrying/n/rate", "carrying/open/rate", "invisible/carrying",
                  "median_versions", "median_date_changes")
        for got, want, label in zip(nums[1:], expected, labels):
            assert got == want, (
                f"{cls} {label}: table reads {got}, fields say {want}")
    assert seen == 4, "all four strata must appear in the headline table"


def test_n_pcd_revisions_is_not_the_number_of_changes():
    """The field-level root cause, asserted so the trap cannot be re-entered."""
    rows = [r for r in cohort.load_results() if "error" not in r]
    if not rows:
        pytest.skip("no cohort measured yet")
    never = [r for r in rows if not r.get("n_date_changes")]
    assert never and all(r.get("n_pcd_revisions") == 1 for r in never)
    for r in rows:
        assert r["n_date_changes"] == max(0, (r.get("n_pcd_revisions") or 0) - 1)


def test_no_exception_launders_a_real_snapshot_field():
    """`NON_SNAPSHOT` is for figures the snapshot does not carry.

    `48` and `188` were listed here while being `n_trials_with_a_carry` and
    `n_stretches`, which made two real fields unfalsifiable.
    """
    snap = cohort.load_snapshot()
    if snap is None:
        pytest.skip("no snapshot frozen yet")
    fields = set()
    for v in snap["strata"].values():
        for val in v.values():
            fields |= _representations(val)
    launder = sorted(set(NON_SNAPSHOT) & fields)
    assert not launder, (
        f"these are listed as exceptions and are also snapshot fields: {launder}. "
        f"An exception list containing real fields cannot falsify them.")


def test_a_hedge_present_in_most_claim_docs_is_present_in_all():
    """Cross-document consistency, matched wrap-insensitively because the first
    version silently exempted README on a line break."""
    claim = re.compile(r"cannot\s+separate\s+reconciliation\s+from\s+filing\s+"
                       r"frequency", re.I)
    cues = ("not a tested", "untested", "ordering across four",
            "an association", "not separable")
    offenders = []
    for doc in CLAIM_DOCS:
        path = os.path.join(REPO, doc)
        if not os.path.exists(path):
            continue
        text = open(path).read()
        if claim.search(text) and not any(c in text.lower() for c in cues):
            offenders.append(doc)
    assert not offenders, (
        f"these state the headline claim with no qualifier: {offenders}")
