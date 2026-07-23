"""The claim documents are rendered from the snapshot, not typed from it.

Five rounds of adversarial review found the same thing every round: the frozen
measurement was clean and the prose that quoted it was wrong. A median printed
as an integer where the field holds a half. A count off by one. Right values in
the wrong stratum. A phrase reported as fixed in three consecutive rounds whose
replacement matched nothing. The guard built against that class was a presence
check over retyped text, and a presence check cannot falsify a small integer.

So the retyping stops. Every figure in the claim documents is emitted here from
a field of `data/cohort/snapshot.json`, and the prose around it is a template
that **contains no numerals at all**. Those are the two halves of one rule, and
together they close the class rather than sampling it:

  - `PROSE` is checked for digits over its whole surface, not over table rows
    and bolded lines. A figure cannot be typed into prose because prose cannot
    contain a digit.
  - the rendered documents are committed, and a test regenerates and compares
    them byte for byte. A figure cannot drift from its field because it is never
    copied from it.

What that replaces: the per-figure guard, its `NON_SNAPSHOT` exception list, its
representation matching, and its cell-by-cell bindings. A figure that is not a
snapshot field can no longer be published by adding it to a list. It has to
become a field, which is where `anchor_case` and the clustering parameters went.

The two things this does not close, stated because the last guard's docstring
overstated the same way:

  - **A wrong field is still a wrong document.** Binding a table cell to
    `carrying_now` when it should render `open_estimates` produces a document
    that regenerates identically forever. The corpus in `tests/mutation_corpus.py`
    attacks exactly that, because it is now the only place a figure defect can
    live.
  - **Prose can still be false without containing a number.** "The ordering is
    monotone" is a claim, it has no digits, and nothing here checks it.

    python3 -m research.render_writeup            # write the documents
    python3 -m research.render_writeup --check    # fail if they are stale
"""
from __future__ import annotations

import argparse
import inspect
import os
import re
import sys
import textwrap
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from research import cohort
from research.backtest import carried_until_corrected

REPO = os.path.join(os.path.dirname(__file__), "..")
WRITEUP = "docs/WRITEUP.md"

# Documents carrying generated blocks rather than being generated whole. A block
# opens with `<!-- generated: name -->` and closes with `<!-- /generated -->`,
# and everything between the two is replaced on every render.
BLOCK_DOCS = ("README.md", "docs/STATUS.md", "docs/COHORT.md",
              "docs/SUBMISSION.md", "docs/LIMITS.md")

OPEN = "<!-- generated: %s -->"
CLOSE = "<!-- /generated -->"
_BLOCK = re.compile(r"<!-- generated: ([a-z_]+) -->\n.*?\n<!-- /generated -->",
                    re.S)

# Figures from outside this study, quoted rather than restated, each carrying
# its source. This is not the old exception list wearing a new name: an entry
# here is a verbatim quotation of an external document, not a bare number
# admitted by assertion, and a test fails if any value here is derivable from
# the snapshot. Nothing measured by this study may be listed.
CITATIONS = {
    "reg": {
        "cite": "42 CFR 11.64(a)(1)(ii)",
        "quote": ("Primary Completion Date must be updated not later than 30 "
                  "calendar days after the clinical trial reaches its actual "
                  "primary completion date."),
        "window": "30 days",
    },
    "shadbolt": {
        "cite": "Shadbolt et al., JAMA Network Open 2023",
        "quote": ("roughly one in five randomised trials complete on time, "
                  "with a median delay of 12.2 months"),
    },
    "guenzel": {
        "cite": "Guenzel & Liu, RFS 2026",
    },
}

STRATA = ("INDUSTRY", "NIH", "OTHER_GOV", "OTHER")

# The correction log is numbered from this order rather than by hand. A log that
# numbers itself cannot skip a number, reuse one, or disagree with the places
# that cite it, and prose cannot carry the numeral at all.
CORRECTIONS = (
    "store_n", "overcorrection", "headline_downgrade", "pooled_rate",
    "cache_loss", "silence", "filter_never_fired", "mandated_filing",
    "one_stratum", "clustering_control", "anecdote", "month_convention",
    "by_construction", "jurisdiction",
)

# Each correction's layer, so the closing table renders its own counts rather
# than having them typed. The layers run from the most mechanical defect a check
# can catch to the least: a wrong number, then a wrong measure, then a figure
# mistyped into prose, then a claim wrong in what it asserts. The point the table
# makes is its first row: no numbered correction is a wrong measured number. A
# reviewer can check any correction's layer against its own methods entry.
CORRECTION_LAYER = {
    "store_n": "figure_code", "cache_loss": "figure_code",
    "filter_never_fired": "figure_code",
    "overcorrection": "method", "pooled_rate": "method", "silence": "method",
    "one_stratum": "method", "clustering_control": "method",
    "anecdote": "prose",
    "headline_downgrade": "semantic", "mandated_filing": "semantic",
    "month_convention": "semantic", "by_construction": "semantic",
    "jurisdiction": "semantic",
}
LAYERS = (
    ("arithmetic", "the measured numbers",
     "recomputed from the store by a review seat every round, and never wrong"),
    ("figure_code", "figure-production code",
     "a store that double-counted, a cache that truncated, a type filter that "
     "never fired: a bug yielding a wrong figure from correct data"),
    ("method", "measure and method design",
     "the stretch measure could not see silence, the clustering test had no "
     "control, a pooled rate printed against the rule forbidding it"),
    ("prose", "retyped prose figures",
     "the class the generated form eliminated; the last was an invented word, "
     "not a digit, and none is numbered since figures were rendered not typed"),
    ("semantic", "semantic and framing",
     "a regulation quoted past its jurisdiction, an unexamined date convention, "
     "an entailment that did not hold: no numeric check sees these"),
)


# ---------------------------------------------------------------------------
# Formatting. Every rendered figure passes through one of these.
# ---------------------------------------------------------------------------

def _n(v) -> str:
    """A count or a day figure, thousands-separated, halves kept.

    A half-integer prints as a half-integer. A zero-decimal format rounds half
    to even, so the same format string sends one median down and another up, and
    both directions have shipped.
    """
    if v is None:
        return "n/a"
    if float(v) == int(v):
        return f"{int(v):,}"
    return f"{v:,}"


def _pct(v) -> str:
    return "n/a" if v is None else f"{v * 100:.1f}%"


def _x(v) -> str:
    return "n/a" if v is None else f"{v:.2f}x"


def _ratio(a, b) -> str:
    return "n/a" if not a or not b else f"{a / b:.1f}x"


def _of(a, b) -> str:
    return f"{_n(a)} of {_n(b)}"


def _month(iso: str) -> str:
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%B %Y")


def _src(fn) -> tuple[str, str]:
    """A function's own source, and the name to cite it by."""
    return (textwrap.dedent(inspect.getsource(fn)).rstrip(),
            f"{fn.__module__}.{fn.__qualname__}")


def _wrap(text: str, width: int = 92) -> str:
    """Reflow prose paragraphs after substitution.

    A template is wrapped for the placeholder names, not for the figures that
    replace them, so a rendered line can be any length. Tables, fenced code and
    anything indented are passed through untouched.
    """
    out: list[str] = []
    buf: list[str] = []
    lead = cont = ""
    fence = False

    def flush():
        nonlocal buf, lead, cont
        if buf:
            out.extend(textwrap.fill(
                " ".join(buf), width=width, initial_indent=lead,
                subsequent_indent=cont, break_long_words=False,
                break_on_hyphens=False).splitlines())
            buf, lead, cont = [], "", ""

    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("```"):
            flush()
            fence = not fence
            out.append(line)
        elif fence or not s or s[0] in "|#" or line.startswith("    "):
            flush()
            out.append(line)
        elif s.startswith("- ") or s.startswith("> "):
            flush()
            lead, cont, buf = s[:2], "  " if s[0] == "-" else "> ", [s[2:]]
        elif buf:
            buf.append(s)
        else:
            lead, cont, buf = "", "", [s]
    flush()
    return "\n".join(out)


def _table(header: list[str], align: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(header) + " |",
           "|" + "|".join(align) + "|"]
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# The figures
# ---------------------------------------------------------------------------

def figures(snap: dict) -> dict:
    """Every numeral that reaches a claim document, keyed by name.

    Nothing else may produce one. A value here is a field of the snapshot, a
    quotation from `CITATIONS`, or arithmetic over fields whose operands are
    named on the same line.
    """
    S = snap["strata"]
    frame = snap["frame"]
    clus = snap["clustering"]
    anchor = snap["anchor_case"]
    f: dict = {}

    def by(key, fmt=_n):
        return {c: fmt(S[c][key]) for c in STRATA}

    f["snapshot_id"] = snap["snapshot_id"]
    f["as_of"] = snap["as_of"]
    f["n_trials"] = _n(snap["n_distinct_trials"])
    f["n_per_stratum"] = _n(S["INDUSTRY"]["n"])
    f["frame_from"] = frame["first_posted_from"]
    f["frame_to"] = frame["first_posted_to"]
    f["frame_to_year"] = frame["first_posted_to"][:4]
    f["frame_next_year"] = str(int(frame["first_posted_to"][:4]) + 1)
    f["phases"] = " / ".join(p.replace("PHASE", "").replace("_", "-")
                             for p in frame["phases"])
    f["seed"] = str(snap["seed"])
    # Emitted rather than typed, so the write-up cannot name a path that moved.
    paths = cohort.store_paths()
    f["store_path"] = paths["store"]
    f["archive_path"] = os.path.basename(paths["archive"])
    f["snapshot_path"] = paths["snapshot"]
    f["cap"] = _n(frame["enumeration_cap_per_stratum"])

    # --- the definition, quoted from the code that applies it ---------------
    src, name = _src(cohort.silent_carrier)
    f["silent_source"] = src
    f["silent_source_cite"] = name
    src, name = _src(cohort.carrying_expired_now)
    f["carrying_source"] = src
    f["carrying_source_cite"] = name
    f["stretch_source_cite"] = _src(carried_until_corrected)[1]

    # --- the headline -------------------------------------------------------
    f["headline_table"] = _table(
        ["Stratum", "carrying an expired estimate",
         "of trials whose commitment is still open",
         "invisible to the stretch measure", "median registry versions",
         "median date revisions"],
        ["---", "---:", "---:", "---:", "---:", "---:"],
        [[c,
          f"{_of(S[c]['carrying_now'], S[c]['n'])} ({_pct(S[c]['carrying_now_rate'])})",
          f"{_of(S[c]['carrying_now'], S[c]['open_estimates'])} "
          f"({_pct(S[c]['carrying_now_of_open_rate'])})",
          _of(S[c]["carrying_now_invisible_to_stretches"], S[c]["carrying_now"]),
          _n(S[c]["median_versions"]),
          _n(S[c]["median_date_changes"])] for c in STRATA])

    carriers = [c for c in STRATA if S[c]["carrying_now"]]
    f["silent_by_stratum"] = ", ".join(
        f"{_of(S[c]['carrying_now_invisible_to_stretches'], S[c]['carrying_now'])} "
        f"in {c}" for c in carriers)
    f["silent_medians"] = ", ".join(
        f"{_n(S[c]['silent_carrier_days_p50'])} days in {c}" for c in carriers)
    yrs = [S[c]["silent_carrier_days_p50"] / 365.25 for c in carriers]
    f["silent_years_span"] = f"{min(yrs):.1f} to {max(yrs):.1f} years"
    f["silent_min"] = _n(min(S[c]["silent_carrier_days_min"] for c in carriers))

    # The population the withdrawn anecdote was offered as an instance of.
    versions = sorted(v for c in STRATA for v in S[c]["silent_carrier_versions"])
    f["silent_n"] = _n(len(versions))
    f["silent_versions_p50"] = _n(cohort._pct(versions, 0.5))
    f["silent_versions_one"] = _n(sum(1 for v in versions if v == 1))
    f["silent_versions_max"] = _n(max(versions))
    f["silent_versions_below_max"] = _of(
        sum(1 for v in versions if v < max(versions)), len(versions))

    f["completed_industry"] = _of(S["INDUSTRY"]["n"] - S["INDUSTRY"]["open_estimates"],
                                  S["INDUSTRY"]["n"])
    f["og_of_open"] = _of(S["OTHER_GOV"]["carrying_now"], S["OTHER_GOV"]["open_estimates"])
    f["industry_carrying"] = _n(S["INDUSTRY"]["carrying_now"])
    f["industry_silent"] = _of(S["INDUSTRY"]["carrying_now_invisible_to_stretches"],
                               S["INDUSTRY"]["carrying_now"])
    f["og_silent"] = _of(S["OTHER_GOV"]["carrying_now_invisible_to_stretches"],
                         S["OTHER_GOV"]["carrying_now"])
    f["other_silent"] = _of(S["OTHER"]["carrying_now_invisible_to_stretches"],
                            S["OTHER"]["carrying_now"])
    f["og_never_revised"] = _of(S["OTHER_GOV"]["never_revised"], S["OTHER_GOV"]["n"])
    f["industry_never_revised"] = _of(S["INDUSTRY"]["never_revised"], S["INDUSTRY"]["n"])

    v = by("median_versions")
    f["nih_versions"] = v["NIH"]
    f["og_versions"] = v["OTHER_GOV"]
    d = by("median_date_changes")
    f["date_change_medians"] = (
        f"{d['NIH']} for NIH, {d['INDUSTRY']} for industry, {d['OTHER']} for "
        f"OTHER and **{d['OTHER_GOV']}** for OTHER_GOV")
    f["version_spread"] = _ratio(S["NIH"]["median_versions"],
                                 S["OTHER_GOV"]["median_versions"])
    f["converse"] = ", ".join(
        f"{_of(S[c]['never_revised_and_carrying'], S[c]['never_revised'])} for {c}"
        for c in STRATA)

    f["resolution_trial"] = f"{100 / S['INDUSTRY']['n']:.1f}"
    f["resolution_open"] = " and ".join(
        f"{100 / S[c]['open_estimates']:.1f} percentage points at n="
        f"{_n(S[c]['open_estimates'])}" for c in ("INDUSTRY", "NIH"))
    f["nih_open"] = _of(S["NIH"]["carrying_now"], S["NIH"]["open_estimates"])

    # --- the two measures reversed -----------------------------------------
    order = sorted(STRATA, key=lambda c: -S[c]["carried_dead_date_rate"])
    f["reversal_table"] = _table(
        ["Stratum", "ever carried, and filed again", "carrying one now",
         "median versions"],
        ["---", "---:", "---:", "---:"],
        [[c, _pct(S[c]["carried_dead_date_rate"]), _pct(S[c]["carrying_now_rate"]),
          _n(S[c]["median_versions"])] for c in order])

    # --- the revision-level mechanism ---------------------------------------
    # The "after a lapse" columns and the rate depend on whether a month-only
    # date is read as the first or the last of its month, so the rate is a
    # bound: end-of-month is the smaller reading and is quoted with "at least".
    mc = snap["month_convention"]

    def _rate_band(c):
        lo = mc["strata"][c]["lapse_to_estimate_rate_eom"]
        return f"{_pct(lo)} to {_pct(S[c]['lapse_to_estimate_rate'])}"

    f["mechanism_table"] = _table(
        ["Stratum", "dated revisions", "after a lapse",
         "of those, recorded ACTUAL", "**estimate to estimate**",
         "rate (end-of-month to first)"],
        ["---", "---:", "---:", "---:", "---:", "---:"],
        [[c, _n(S[c]["revisions_dated"]), _n(S[c]["revisions_after_lapse"]),
          _n(S[c]["revisions_after_lapse_to_actual"]),
          _n(S[c]["revisions_after_lapse_to_estimate"]),
          _rate_band(c)] for c in STRATA])
    f["industry_lapse_to_estimate_band"] = _rate_band("INDUSTRY")
    f["industry_lapse_to_estimate"] = _pct(S["INDUSTRY"]["lapse_to_estimate_rate"])
    f["nih_lapse_to_estimate"] = _pct(S["NIH"]["lapse_to_estimate_rate"])
    f["og_lapse_to_estimate"] = _pct(S["OTHER_GOV"]["lapse_to_estimate_rate"])
    f["other_lapse_to_estimate"] = _pct(S["OTHER"]["lapse_to_estimate_rate"])
    f["industry_lapse_counts"] = _of(S["INDUSTRY"]["revisions_after_lapse_to_estimate"],
                                     S["INDUSTRY"]["revisions_dated"])
    f["trial_level_mechanism"] = ", ".join(
        f"{_of(S[c]['trials_with_lapse_to_estimate'], S[c]['trials_revising'])} for {c}"
        for c in STRATA)
    f["industry_trial_mechanism"] = (
        f"{_of(S['INDUSTRY']['trials_with_lapse_to_estimate'], S['INDUSTRY']['trials_revising'])} "
        f"({_pct(S['INDUSTRY']['trials_with_lapse_to_estimate'] / S['INDUSTRY']['trials_revising'])})")
    f["boundary"] = _of(sum(S[c]["revisions_on_the_day"] for c in STRATA),
                        sum(S[c]["revisions_dated"] for c in STRATA))
    f["never_revising"] = ", ".join(
        f"{_of(S[c]['trials_never_revising'], S[c]['n'])} for {c}"
        for c in ("INDUSTRY", "OTHER_GOV"))
    f["carrying_never_revised"] = ", ".join(
        f"{_of(S[c]['carrying_never_revised'], S[c]['n'])} for {c}"
        for c in ("INDUSTRY", "OTHER_GOV"))

    # --- comparability ------------------------------------------------------
    f["comparability_table"] = _table(
        ["Stratum", "Transitions", "Contingent", "Refused", "scope changed",
         "superseded", "**unreadable**"],
        ["---", "---:", "---:", "---:", "---:", "---:", "---:"],
        [[c, _n(S[c]["transitions"]), _pct(S[c]["contingent_rate"]),
          _pct(S[c]["refused_rate"]), _pct(S[c]["refused_scope_rate"]),
          _pct(S[c]["refused_superseded_rate"]),
          f"**{_pct(S[c]['refused_unreadable_rate'])}**"] for c in STRATA])
    f["refusal_table"] = _table(
        ["Stratum", "transitions", "scope changed", "superseded",
         "**unreadable**"],
        ["---", "---:", "---:", "---:", "---:"],
        [[c, _n(S[c]["transitions"]), _pct(S[c]["refused_scope_rate"]),
          _pct(S[c]["refused_superseded_rate"]),
          f"**{_pct(S[c]['refused_unreadable_rate'])}**"] for c in STRATA])
    f["industry_contingent"] = _pct(S["INDUSTRY"]["contingent_rate"])
    f["nih_contingent"] = _pct(S["NIH"]["contingent_rate"])
    f["industry_contingent_counts"] = _of(S["INDUSTRY"]["contingent"],
                                          S["INDUSTRY"]["transitions"])

    # --- duration -----------------------------------------------------------
    f["trial_duration_table"] = _table(
        ["Stratum", "trials with a carry", "median", "p90", "max"],
        ["---", "---:", "---:", "---:", "---:"],
        [[c, _n(S[c]["n_trials_with_a_carry"]), f"**{_n(S[c]['trial_days_p50'])}**",
          _n(round(S[c]["trial_days_p90"], 1)), _n(S[c]["trial_days_max"])]
         for c in STRATA])
    f["stretch_duration_table"] = _table(
        ["Stratum", "stretches", "median", "p90", "max", "ever carried"],
        ["---", "---:", "---:", "---:", "---:", "---:"],
        [[c, _n(S[c]["n_stretches"]), _n(S[c]["dead_days_p50"]),
          _n(round(S[c]["dead_days_p90"], 1)), _n(S[c]["dead_days_max"]),
          _pct(S[c]["carried_dead_date_rate"])] for c in STRATA])
    f["trial_ratio"] = _ratio(S["NIH"]["trial_days_p50"],
                              S["INDUSTRY"]["trial_days_p50"])
    f["stretch_ratio"] = _ratio(S["NIH"]["dead_days_p50"],
                                S["INDUSTRY"]["dead_days_p50"])
    f["nih_trial_p50"] = _n(S["NIH"]["trial_days_p50"])
    f["industry_trial_p50"] = _n(S["INDUSTRY"]["trial_days_p50"])
    f["other_gov_trial_p50"] = _n(S["OTHER_GOV"]["trial_days_p50"])
    f["other_gov_stretch_p50"] = _n(S["OTHER_GOV"]["dead_days_p50"])
    # Bound to the silent carriers, not to `carrying_now`. The sentence is about
    # trials excluded from the per-trial duration table, and a trial carrying an
    # open lapse that also has a closed one still appears there: one industry
    # carrier does.
    f["censoring"] = ", ".join(
        f"{_n(S[c]['carrying_now_invisible_to_stretches'])} {c}" for c in STRATA
        if S[c]["carrying_now_invisible_to_stretches"])
    top = S["NIH"]["max_stretch_trial"]
    f["top_stretch_trial"] = (
        f"`{top['nct']}`, with {_n(top['n_versions'])} versions and "
        f"{_n(top['n_date_changes'])} date changes, contributes "
        f"{_n(top['n_stretches'])} of that stratum's "
        f"{_n(S['NIH']['n_stretches'])} stretches")

    # --- clustering ---------------------------------------------------------
    f["window"] = _n(clus["window_half_width_days"])
    f["anniversaries"] = " / ".join(_n(d) for d in clus["anniversary_centres_days"])
    f["controls"] = " / ".join(_n(d) for d in clus["control_centres_days"])
    # The two window sets have the same total width and both fall inside every
    # stratum's observed interval range, so they share one null. Printing it
    # twice implied the control had been normalised independently; it had not,
    # and the ratio comparison is a raw count comparison. Asserted rather than
    # assumed, because it stops being true if a window ever falls outside.
    for c in STRATA:
        if (S[c]["submit_intervals_even_spread_baseline"]
                != S[c]["submit_intervals_control_even_spread_baseline"]):
            raise ValueError(
                f"{c}: the anniversary and control windows no longer share a "
                f"null, so the table must print both again.")
    f["clustering_table"] = _table(
        ["Stratum", "intervals", "median interval", "within the anniversary windows",
         "within the control windows", "even-spread null", "anniversary ratio",
         "control ratio"],
        ["---", "---:", "---:", "---:", "---:", "---:", "---:", "---:"],
        [[c, _n(S[c]["submit_intervals_n"]), _n(S[c]["submit_intervals_p50"]),
          f"{_of(S[c]['submit_intervals_near_year_multiple'], S[c]['submit_intervals_n'])} "
          f"({_pct(S[c]['submit_intervals_near_year_rate'])})",
          f"{_of(S[c]['submit_intervals_near_control_multiple'], S[c]['submit_intervals_n'])} "
          f"({_pct(S[c]['submit_intervals_near_control_rate'])})",
          _pct(S[c]["submit_intervals_even_spread_baseline"]),
          f"**{_x(S[c]['submit_intervals_bunching_ratio'])}**",
          f"**{_x(S[c]['submit_intervals_control_bunching_ratio'])}**"]
         for c in STRATA])
    f["industry_anniversary_ratio"] = _x(S["INDUSTRY"]["submit_intervals_bunching_ratio"])
    f["industry_control_ratio"] = _x(S["INDUSTRY"]["submit_intervals_control_bunching_ratio"])
    f["control_ratios"] = ", ".join(
        f"{c} {_x(S[c]['submit_intervals_bunching_ratio'])} against "
        f"{_x(S[c]['submit_intervals_control_bunching_ratio'])}" for c in STRATA)
    f["other_median_interval"] = _n(S["OTHER"]["submit_intervals_p50"])
    f["industry_median_interval"] = _n(S["INDUSTRY"]["submit_intervals_p50"])
    f["industry_window_counts"] = (
        f"{_of(S['INDUSTRY']['submit_intervals_near_year_multiple'], S['INDUSTRY']['submit_intervals_n'])} "
        f"at the anniversaries against "
        f"{_of(S['INDUSTRY']['submit_intervals_near_control_multiple'], S['INDUSTRY']['submit_intervals_n'])} "
        f"at the controls")
    f["industry_carrying_never_revised"] = _of(
        S["INDUSTRY"]["carrying_never_revised"], S["INDUSTRY"]["carrying_now"])
    f["og_anniversary_ratio"] = _x(S["OTHER_GOV"]["submit_intervals_bunching_ratio"])
    f["other_anniversary_ratio"] = _x(S["OTHER"]["submit_intervals_bunching_ratio"])

    # --- the innocence check ------------------------------------------------
    f["carrying_medians"] = ", ".join(
        f"{_n(S[c]['carrying_days_since_expiry_p50'])} days in {c}"
        for c in carriers)
    f["carrying_total"] = _n(sum(S[c]["carrying_now"] for c in STRATA))
    f["carrying_under_a_year"] = _of(
        sum(S[c]["carriers_under_a_year"] for c in STRATA),
        sum(S[c]["carrying_now"] for c in STRATA))
    f["carrying_shortest"] = _n(min(S[c]["carrying_days_since_expiry_min"]
                                    for c in carriers))
    f["month_precision"] = _of(sum(S[c]["carriers_month_precision"] for c in STRATA),
                               sum(S[c]["carrying_now"] for c in STRATA))

    # --- the silent-carrier split (the "by construction" retraction) --------
    aud = snap["silent_carrier_audit"]
    f["silent_multi"] = _n(aud["multi"])
    f["silent_single"] = _n(aud["single"])
    f["silent_multi_filed_after"] = _n(aud["multi_filed_after"])
    f["silent_single_filed_after"] = _n(aud["single_filed_after"])
    f["silent_counterexample"] = aud["counterexample"]

    # --- the two readings of a month-only date ------------------------------
    # End-of-month is the conservative reading of everything it touches, so it is
    # the figure quoted with "at least" and the first-of-month reading is shown
    # beside it. See month_convention() for why the direction is uniform.
    mc = snap["month_convention"]
    f["anchor_days_eom"] = _n(mc["anchor_days_eom"])
    f["flips"] = _n(mc["dated_revisions_that_flip"])
    f["dated_total"] = _n(mc["dated_revisions_total"])
    for c in STRATA:
        m = mc["strata"][c]
        f[f"{c.lower()}_lapse_to_estimate_eom"] = _pct(m["lapse_to_estimate_rate_eom"])
        f[f"{c.lower()}_stretch_p50_eom"] = _n(m["dead_days_p50_eom"])
        f[f"{c.lower()}_trial_p50_eom"] = _n(m["trial_days_p50_eom"])
    f["og_stretch_vanished"] = _of(
        S["OTHER_GOV"]["n_stretches"] - mc["strata"]["OTHER_GOV"]["n_stretches_eom"],
        S["OTHER_GOV"]["n_stretches"])

    # --- the anchor case ----------------------------------------------------
    f["anchor_nct"] = anchor["nct"]
    f["anchor_days"] = _n(anchor["days_carried"])
    f["anchor_expired"] = anchor["expired_on"]
    f["anchor_corrected"] = anchor["corrected_on"]
    f["anchor_expired_month"] = _month(anchor["expired_on"])
    f["anchor_corrected_month"] = _month(anchor["corrected_on"])
    st, tr = anchor["industry_stretches"], anchor["industry_trials"]
    f["anchor_stretch_pct"] = f"{st['share'] * 100:.0f}th"
    f["anchor_trial_pct"] = f"{tr['share'] * 100:.0f}th"
    f["anchor_stretch_counts"] = _of(st["at_or_below"], st["n"])
    f["anchor_stretch_n"] = _n(st["n"])
    f["anchor_stretch_share"] = _pct(st["share"])
    f["anchor_trial_counts"] = _of(tr["at_or_below"], tr["n"])

    # --- corrections whose retracted figures are themselves fields ----------
    f["retracted_after_lapse_rate"] = _pct(S["INDUSTRY"]["revised_after_lapse_rate"])
    f["retracted_after_lapse_counts"] = _of(S["INDUSTRY"]["revisions_after_lapse"],
                                            S["INDUSTRY"]["revisions_dated"])
    f["retracted_actual_share"] = _of(S["INDUSTRY"]["revisions_after_lapse_to_actual"],
                                      S["INDUSTRY"]["revisions_after_lapse"])
    f["retracted_trial_rate"] = _pct(S["INDUSTRY"]["trials_with_a_lapse"]
                                     / S["INDUSTRY"]["trials_revising"])
    f["retracted_trial_counts"] = _of(S["INDUSTRY"]["trials_with_a_lapse"],
                                      S["INDUSTRY"]["trials_revising"])
    f["industry_prevalence"] = _pct(S["INDUSTRY"]["carrying_now_rate"])
    f["og_prevalence"] = _pct(S["OTHER_GOV"]["carrying_now_rate"])
    f["industry_open_rate"] = _pct(S["INDUSTRY"]["carrying_now_of_open_rate"])

    # --- citations ----------------------------------------------------------
    for k, v in CITATIONS.items():
        for field, text in v.items():
            f[f"{k}_{field}"] = text

    # --- correction numbers, from the order rather than from prose ----------
    for i, key in enumerate(CORRECTIONS, start=1):
        f["c_" + key] = f"Correction {i}"

    # --- the corrections-by-layer table, counts rendered from the record ----
    by_layer = {}
    for slug in CORRECTIONS:
        by_layer.setdefault(CORRECTION_LAYER[slug], []).append(slug)
    # Every correction must carry a layer, or the total below is wrong and the
    # table silently under-counts. Asserted here so a new correction cannot be
    # added without placing it.
    unplaced = [s for s in CORRECTIONS if s not in CORRECTION_LAYER]
    if unplaced:
        raise ValueError(f"corrections with no layer: {unplaced}")
    f["corrections_layer_table"] = _table(
        ["Layer", "a defect here", "numbered corrections"],
        ["---", "---", "---:"],
        [[label, note, _n(len(by_layer.get(key, [])))]
         for key, label, note in LAYERS])
    f["n_corrections"] = _n(len(CORRECTIONS))
    f["n_arithmetic"] = _n(len(by_layer.get("arithmetic", [])))
    f["n_semantic"] = _n(len(by_layer.get("semantic", [])))
    return f


# ---------------------------------------------------------------------------
# The prose. Every value below is checked for digits over its whole surface.
# ---------------------------------------------------------------------------

PROSE = {

"title": """\
# Most trials carrying an expired commitment have never reconciled a lapsed date
""",

"banner": """\
**This document is generated.** Every cohort figure in it is emitted from a field of
snapshot `{snapshot_id}`, frozen {as_of}, with point prevalence computed as of that same
date: {n_trials} drawn trials, {n_per_stratum} in each of four sponsor strata, all
measured. The id is content-addressed over the measured rows and the frame together, so it
cannot be re-cut under the same name.

The prose you are reading is a template that carries no numerals of its own, and a test
enforces that over the whole template rather than over selected lines. The exception is a
small table of verbatim quotations from sources outside this study, checked separately so a
measurement cannot launder through it. Every other figure is filled in from a named field by
`research/render_writeup.py`. A test regenerates this file and fails if a single byte
differs, so a figure cannot be edited here at all: it can only be changed by changing the
field it renders. **No figure in this document was copied from the snapshot by a person.**

That closes the class of defect the review rounds kept finding in retyped prose, and it does
not close everything. The residuals are named here rather than discovered later, because the
guard this replaced gave a narrower account of itself than was true. A cell in a table renders
wrongly if it is bound to the wrong field, so every table cell in every document is recomputed
from the store by a second implementation and the headers are pinned; a figure in a sentence
the recomputation does not cover is not checked. A number spelled in words is invisible to a
rule about digits, and one, a count of strata as "three of the four", shipped in three
documents. A digit assembled at runtime evaluates past the literal rule. And the recomputation
shares the measurement's own reading of a field, so a claim that misunderstands what a field
means can pass both, which is the hole the withdrawn "by construction" claim went through.
`docs/LIMITS.md` carries the full account.

The draw is uniform over the first {cap} trials in the registry's own ordering within each
stratum, not over the whole stratum. "Randomly drawn" throughout means that and not more.
""",

"finding_head": """\
## The finding: this study cannot separate reconciliation from filing frequency

Most trials carrying an expired commitment have never reconciled a lapsed date:
{silent_by_stratum}. The measure that was going to be this study's headline is built from
observed corrections and therefore cannot see them.
""",

"definition": """\
**The measured condition is stronger than "has not filed lately", and rather than
paraphrase it this document quotes the code that applies it.** A paraphrase is a second
implementation that no test runs, and the paraphrase this replaces was wrong: it said "no
correction since this date lapsed", which is true of essentially every carrier by
construction, since a correction would have moved the date.

From `{silent_source_cite}`:

```python
{silent_source}
```

and the predicate it composes with, `{carrying_source_cite}`:

```python
{carrying_source}
```

So the condition is: the most recent registered primary completion date is in the past, is
still typed as an estimate, and `{stretch_source_cite}` has never emitted a stretch for
this trial at any point in its history. Not once. A past date typed ACTUAL is the
reconciled case, a completed trial recording when it completed, and does not count.
""",

"durations_stood": """\
Those dates have stood a long time. The median is {silent_medians}, which is
{silent_years_span}, and the shortest anywhere is {silent_min} days.

**Most of these are not trials that kept filing while one field went stale, and the record is
silent on the rest.** The population splits by whether the stretch measure could see it at
all. For the {silent_multi} carriers with more than one registry version, the measure ran and
found no filing arriving over a standing expired date: {silent_multi_filed_after} of them
filed anything after the date had passed. For the {silent_single} with a single version there
is no consecutive pair to measure, so their zero is an empty loop rather than a clean record,
and {silent_single_filed_after} of them, `{silent_counterexample}`, registered its single
filing years after the date it recorded had already gone by. So the honest reading is: no
multi-version silent carrier reconciled and kept filing, and the single-version ones filed
once, at a time relative to expiry that runs both ways. They are not busy filers in general:
{silent_versions_one} have never filed a second registry version of any kind, and the median
across the whole life of one of these trials is {silent_versions_p50} registry versions
against a median of {nih_versions} for an NIH trial. An earlier draft asserted a stronger,
false claim over the whole population, corrected as {c_by_construction} below.
""",

"headline_table_intro": """\
A trial is **carrying an expired commitment** when the predicate above holds. Measured as
of {as_of}, against two denominators, beside how often each stratum files at all:
""",

"headline_table_after": """\
Both denominators are reported because they answer different questions. Out of all
{n_per_stratum} trials the rate is small and should be: most trials in this frame have
finished and recorded an actual completion date, which is the system working. But
{completed_industry} industry trials are in that state and cannot be carrying an expired
estimate by construction. Among those whose commitment is still open, one in three industry
trials is already past its stated date, and for OTHER_GOV it is {og_of_open}.
**{industry_silent} industry trials currently carrying an expired estimate are invisible to
the measure this project started with**, which is the industry instance of the finding
below.

That is a handful of events. No interval is computed anywhere in this document, and the
conditional column's denominators are smaller still: one trial is {resolution_open},
so the zero for NIH is {nih_open}.

NIH sponsors file a median of {nih_versions} registry versions per trial and have **no**
trial currently carrying an expired estimate. OTHER_GOV sponsors file a median of
{og_versions} and nearly all of their open commitments are expired. The ordering is
monotone in filing frequency across all four strata. That is an association across four
points, not a tested mechanism, and nothing here separates filing frequency from any other
property that varies alongside it.

**A registry version is any record edit, not a completion-date edit**, and the
{version_spread} spread between NIH and OTHER_GOV is mostly edits to fields nobody here is
discussing. On date changes alone the medians are {date_change_medians}: the same ordering
over a far smaller range. The count excludes the initial registration, which the underlying
`n_pcd_revisions` field includes; an earlier draft of this column read that field directly
and so credited every trial with a revision it had never made. The last column above
carries both so the spread is not read as fifty times more date maintenance.

**The converse does not hold, and the study can say so.** Among trials that never revised a
date, the share carrying an expired estimate is {converse}. Going quiet is common among the
trials carrying an expired commitment; it does not follow that a quiet trial is carrying
one.
""",

"reversal": """\
### The measure that misses them, and why it inverts

The stretch measure, reported in full further down, records a lapse only when a *later
filing* arrives while an already-passed date is standing. A sponsor that lets a date expire
and then files nothing produces no stretch at all and scores as never having carried one.
The silence is exactly what makes it invisible: {og_silent} of OTHER_GOV's currently
expired trials are invisible that way and {other_silent} of OTHER's, and
{og_never_revised} OTHER_GOV trials never revised a date at all.

The two measures therefore reverse the ordering, with industry and NIH tied at the top of
the first:
""",

"reversal_after": """\
Read alone, the stretch measure would have said the OTHER_GOV and OTHER strata lapse and file
again least often. They are the most likely to be carrying an expired date now. A measure that
needs its subject to keep talking cannot see the subject that stops, and any frequency statistic
built from observed corrections has the same blind spot.
""",

"mechanism_head": """\
## The mechanism, among sponsors that are still filing

That trials run late is documented. {shadbolt_cite} find {shadbolt_quote}. Any measure of
"the registered date passed" is close to a restatement of something already known, and a
study that stops there has measured lateness with extra steps.

The distinction that separates them is **when** the date was revised and **to what**. Every
revision carries how much time the old date still had when it was moved:

- **Revised while the date was still in the future.** The registered date had not yet
  passed when it was replaced. The trial may be very late and the record still never
  showed a date that had expired.
- **Revised after the date had already passed, recording an ACTUAL completion.** For a
  trial that ran late this necessarily lands after the earlier estimate expired, and it is
  the update {reg_cite} requires within {reg_window} of actual completion. It is the
  reconciliation event, not its absence.
- **Revised after the date had already passed, with another ESTIMATE.** The sponsor let the
  date pass and then pushed it, with no completion recorded. This is the behaviour this
  project claims to measure.

None of the three describes what anyone knew or intended, which a registry diff cannot
show.
""",

"mechanism_after": """\
At the trial level, the share of trials that revised a date at all and did this at least
once is {trial_level_mechanism}.

So among sponsors that are still filing, **at least {industry_lapse_to_estimate_eom} of
industry revisions** are something delay does not account for. That figure is a bound, not a
point: whether a revision counts as filed-after-a-lapse turns on the date it replaced, and a
month-only date has two readings. The rate column above carries both, {industry_lapse_to_estimate_band}
for industry, and the smaller end-of-month reading is the one quoted here because it is the
weaker claim. An earlier draft reported the undivided after-lapse rate here, which counted
the mandated update-to-actual filing as a failure to reconcile; that is retracted as
{c_mandated_filing}. A separate earlier draft disclosed the month convention as touching only
days-since-expiry and moving no revision-level figure; it moves this one, and that is
{c_month_convention}.

**This measure is conditional on a revision existing**, which is the same blind spot as the
stretch measure, one level up: a trial that lapses and never files again contributes to
neither the numerator nor the denominator. The excluded set is every trial that never
changed a date at all, which is {never_revising}; the subset of it that matters here, trials
carrying an expired estimate and never having revised one, is {carrying_never_revised}. It is
why this section supports the finding above rather than standing on its own.

A boundary convention: a revision filed on the exact day the date came due has zero days
remaining and is counted as prospective rather than as a lapse. That is {boundary} dated
revisions across all four strata and it moves no published figure.

**The month-only convention, which does move figures.** A registry date given to the month
rather than the day names no day, so it has two readings: the first of the month or the last.
Resolving to the last pushes every date later, and the direction that moves a figure is not the
same for every figure, so "conservative" has to be worked out per quantity rather than asserted
once. For a single carry and for the after-a-lapse rate the later date makes the figure
**smaller**: the anchor case's carry shrinks and fewer revisions land after a lapse, so
end-of-month is the weaker reading there and is the one this document quotes with "at least".
For the closed-spell duration medians it makes the figure **larger**, not smaller, because the
shortest carries cease to be lapses under the later date and drop out of the set, lifting the
median of what remains; there the first-of-month reading is the smaller one, and it is the one
the duration tables print. In both cases the figure shown is the weaker of the two, but they
come from opposite ends of the convention. Of the {dated_total} dated revisions across all four
strata, {flips} cross between prospective and after-a-lapse when the reading is switched, which
is why the rate above is a band. The tables that follow carry both readings where the
convention moves them.
""",

"scope": """\
## What is being measured, and what is not

This is a measurement of **reconciliation**, not of performance.

The system observes whether a public, dated, self-authored commitment was kept, revised,
superseded, or left standing after its date passed without anyone reconciling it. It does
not observe whether the underlying trial was going well, whether the sponsor was in
difficulty, or whether the original date was ever achievable. There is no outcome variable
in this dataset at all.

That boundary has a partial mechanical guard. `orchestrator/lexicon.py` is a list of banned
phrasings checked in CI against every rendered page and every claim-bearing document
including this one, and a sentence matching one of those patterns does not survive the
build. It is a list of phrasings, so it catches the ones someone thought of. It is a floor
under the prose, not the boundary itself.

Two vocabulary points that follow from the same discipline:

- This is the **registered primary-completion expectation**, which is last patient last
  visit for the primary endpoint. Topline results follow it by roughly two to four months,
  a working figure used throughout this project and not one measured here.
- A stretch is **carried**. That a date passed and stayed standing is a fact about the
  record. Whether anyone intended anything by it is not observable from a registry diff,
  and nothing here asserts that they did.

## The frame, which is the denominator

Every rate this project published before this study came from fourteen trials that happened
to be cached, belonging to five companies chosen by hand to illustrate the problem. A
sample selected on the outcome cannot produce a base rate. This is the replacement.
""",

"frame_after": """\
The end date is deliberate. A trial first posted in {frame_next_year} has had too little
time to accumulate a revision history, and including it would bias every duration downward.

**A limitation, and the frame size is not known:** enumeration is capped at {cap} trials
per stratum, so within a stratum the draw is uniform over the registry's own ordering
rather than over the whole stratum. What fraction of each stratum that cap represents was
not recorded, so how much this matters is unmeasured rather than small.
""",

"duration_head": """\
## Duration

**Primary: one observation per trial, its longest carry.** A trial that lapsed once
contributes one number regardless of how often its sponsor happened to file afterwards.
""",

"duration_after": """\
Days. NIH against industry at the median: **{trial_ratio}**.

**Every duration in this section is measured on completed spells**, meaning lapses that
were eventually ended by a later filing. Excluding open lapses biases every duration
**downward**, and the exclusion is unequal across strata: no NIH trial is excluded on this
ground, against {censoring}. The cross-stratum ratio is therefore between differently
censored distributions and should be read with that. The open cases, which are the ones a
monitor would actually alert on, contribute no duration at all: this study counts them and
does not say how long they run or where the replacement date lands. Recorded in
`docs/PARKING.md` as the next measurement rather than estimated here.

The medians in this table are the first-of-month reading, which for durations is the shorter
one. Under the end-of-month reading OTHER_GOV's per-trial median rises from {other_gov_trial_p50}
to {other_gov_trial_p50_eom} days, because its shortest carries stop being lapses and leave the
set; the other three strata do not move on this unit. The smaller figure is the one printed, and
for a duration that is the first-of-month reading, the opposite end from the rate and the anchor
above.

**Sensitivity, per stretch.** A stretch is emitted per consecutive version pair, so one
lapse spanning many filings contributes many overlapping rows measuring the same expiry to
successively later endpoints, and a frequent filer contributes more of them. One NIH trial,
{top_stretch_trial}.
""",

"sensitivity_after": """\
Percentiles are linearly interpolated and printed to a tenth of a day wherever the
interpolation lands between two days, rather than rounded. Half-integer medians print in
full for the same reason: a rounding format rounds half to even, which drops the half in one
direction and adds one in the other, and both have shipped from this document.

On this unit the NIH against industry ratio is **{stretch_ratio}** rather than
{trial_ratio}. **The gap between the two is the filing-frequency artifact, not a finding**,
which is why the per-trial unit is primary and this one is labelled as a sensitivity.

The month convention moves this table too, and further than it moves the per-trial one, because
a stretch can cease to be a lapse entirely when the later reading of its date lands after the
filing that would have ended it. Under end-of-month OTHER_GOV's stretch median rises from
{other_gov_stretch_p50} to {other_gov_stretch_p50_eom} days and {og_stretch_vanished} of its
stretches disappear. The first-of-month figures printed above are the smaller reading and the
one to lead with.

### Why the strata are not pooled

Three independent differences, none of which rests on the duration ratio alone. The
reconciliation rates in the first bullet are quoted at the first-of-month reading, the upper
end of the band in the mechanism table; the ordering between strata holds under either reading.

- **Reconciliation behaviour.** {industry_lapse_to_estimate} of industry revisions replace
  an already-expired estimate, against {nih_lapse_to_estimate} of NIH and
  {og_lapse_to_estimate} of OTHER_GOV ones.
- **Point prevalence.** {og_prevalence} of OTHER_GOV trials are carrying an expired
  estimate now against {industry_prevalence} of industry trials and none of the NIH ones.
- **Filing frequency**, which varies alongside both and is not separable from either here,
  at a median of {og_versions} registry versions per trial against {nih_versions}. It does
  not order the reconciliation rate: OTHER files more than OTHER_GOV and has the higher
  estimate-to-estimate rate, {other_lapse_to_estimate} against {og_lapse_to_estimate}.

`stats()` raises rather than returning a pooled rate, so the figure cannot be computed by
accident.

## Comparability, and why three totals rather than two

A date moving between two registry versions is a delay only if both dates describe the same
commitment. Every transition is classified into three states and refusals carry their
reason:
""",

"comparability_after": """\
**Contingent** means comparability turns on prose alone: the sponsor reworded a free-text
endpoint in the same filing that moved the date, and no string comparison can tell a reword
from a redefinition. These get bounds and never verdicts. **Refused** means a count or
enumeration changed, which no wording explains away, or the commitment was withdrawn.

The unreadable column is the share of refusals caused by a gap in *our* data rather than by
an event in the sponsor's record, and it is zero in every stratum. The hole this check was
built to find is empty. It was defined narrowly and says nothing about gaps of other
shapes; the adversarial review of this document found two of those.

## The innocence check

If sponsors simply batch their registry housekeeping annually, a median lapse of months is
an artifact of update cadence rather than of anything being ignored.

Annual batching would not be compliant, because the rule for this element is not annual.
{reg_cite}:

> "{reg_quote}"

**That is a statement about the duty, not a refutation of the behaviour**, and the section
is titled as a check rather than a result for that reason. A roughly annual housekeeping
cycle is consistent with the durations observed here.

An earlier draft claimed the revision timing settled this, on the grounds that a majority of
industry revisions arrive after the date they replace has already expired. That argument
does not work, for two separate reasons. The majority figure counted the mandated
update-to-actual filing and is retracted as {c_mandated_filing}. And the surviving
estimate-to-estimate subset does not rebut batching either: a sponsor on a yearly cycle
would replace an expired estimate with a fresh one at the next pass, which is exactly what
that subset counts. **A cadence hypothesis is not refuted by evidence that the cadence is
slow.**

**The check ends in three places, and only one of them is resolved.**

*One, the currently-carrying population, excluded everywhere on duration.* Measured on that
population rather than on the silent subset of it, the median date has stood
{carrying_medians}. A yearly sweep does not leave a date standing that long. It is not
excluded for all of them: {carrying_under_a_year} carriers have been expired under a
year, the shortest {carrying_shortest} days, and for those a slow cycle and a
non-reconciliation look alike.

*Two, industry filing timing: **unresolved**, and this leg was published as resolved.* An
earlier draft read industry's anniversary windows against an even-spread null, found them at
or below it, and called that the absence of an annual signal. The control windows below
retire that null, and a conclusion cannot be drawn from a statistic the same section calls
uninterpretable in three strata and interpretable in the fourth because it came out the
convenient way. Industry does show the table's largest gap between the two window sets,
{industry_window_counts}, but the control centres sit at shorter lags than the anniversaries
and industry's median interval falls between them, so that gap is the same distributional
artifact. It is also the wrong population: {industry_carrying_never_revised} of the industry
trials carrying an expired estimate have never changed a date, so they contribute no interval
at all.

*Three, closed-spell durations in the other strata: **unresolved**.* An earlier draft
concluded that the batching explanation stood for OTHER and OTHER_GOV because their intervals
bunch near anniversaries. Their closed-spell durations are neither excluded nor explained by
anything measured here.

Both of these legs were withdrawn by {c_clustering_control}, which gave the test its missing
control; the earlier {c_one_stratum} only stopped it being shown for one stratum. The test is
published below because it was run, not because it settles anything.

### The clustering test, and the control windows that undercut it

The test asks how many gaps between consecutive date-changing filings fall within
{window} days of a one, two or three year multiple, at {anniversaries} days. An interval is
the gap between the submit dates of two consecutive versions that changed the completion
date; a trial's first interval runs from its initial registration. The null is the share of
each stratum's observed interval range covered by the three windows, which is what an even
spread would land in.

**The control windows are the same test run at {controls} days**, half a year off each
anniversary and the same width. They are not anniversaries, and a yearly housekeeping cycle
gives no reason to expect anything at them. Both window sets have the same total width and
both fall inside every stratum's observed interval range, so they share one null and the
comparison between the two ratios reduces to a comparison of the two counts.
""",

"clustering_after": """\
**The control windows score no lower than the anniversary windows in three of the four
strata, and lower by a few hundredths in the fourth**, anniversary against control:
{control_ratios}. Windows that no cadence hypothesis singles out score about the same as the
ones it does. So the ratio measures the shape of the interval distribution, which is concentrated
at short lags, against a null that assumes an even spread and is therefore wrong. It does
not measure anniversaries. Two things were withdrawn in sequence and they are not the same
withdrawal: {c_one_stratum} retired the *presentation* that showed the industry row alone
under "there is no annual bunching", by publishing all four strata, and {c_clustering_control}
retired the *conclusions* drawn from any of them, by adding the control the test never had.
The industry "no annual bunching" reading survived {c_one_stratum} and falls only here.

**Nothing survives for any stratum, including the one the earlier draft cleared.** Industry's
anniversary windows hold about half what its control windows do,
{industry_window_counts}, which is the largest separation in the table and is the only
direction that would have supported an innocence claim. It is not read as one here: the
control centres sit at systematically shorter lags than the anniversaries, industry's median
interval of {industry_median_interval} days falls between the two, and a distribution
concentrated at short lags produces exactly that deficit with no cadence involved. The test
discriminates or it does not, and this study cannot say which.

**Two further limits, which were already stated and still hold.** The windows stop at three
years while intervals run past the longest anniversary window, so long gaps sit in the
denominator and can never score. And a trial that never changed its date contributes no
interval at all, so the carriers this section is about supply almost none of what is
measured. The test describes the cadence of sponsors that file. It cannot describe the
cadence of sponsors that do not.

**What the regulation does and does not license, precisely.** The rule concerns updating
the date to *actual* once a trial reaches its actual primary completion. Much of what is
observed here is a registered *estimate* that passed and stayed standing. Those overlap but
are not the same event, and this dataset cannot say which happened for any given trial. The
window quoted above is therefore a **reference line on a distribution**, not a test any
trial passes or fails, and no stretch here is called a breach. Naming the duty is what the
claims lexicon requires before any statement touching disclosure obligations is permitted
at all. Naming it is not alleging it was breached.

**And the duty does not reach every stratum, which an earlier draft did not say.** {reg_cite}
is U.S. law, and it binds the applicable clinical trials the statute defines: broadly, trials
with a U.S. site or a U.S.-regulated product. The two strata this study most wants to contrast
are industry and NIH, where the duty plausibly applies. The OTHER_GOV stratum, drawn here, is
not U.S. federal agencies: the drawn sponsors are non-U.S. public bodies, a Turkish institute,
a Thai ministry, a Mexican social-security system, and a trial run by one of them with no U.S.
arm is generally not an applicable clinical trial at all. So the reference line is drawn
against industry and NIH and is **not** extended to OTHER_GOV or OTHER. What survives for
those strata is the registry fact, stated without the regulation: their dates passed and
stayed standing, for the durations reported, and no U.S. duty is asserted over them. This is
{c_jurisdiction}, and the registry has a separate lead-sponsor class, FED, for U.S. federal
agencies other than NIH, which this study never drew; `docs/PARKING.md` records it as the
follow-up, because it is the stratum where the duty applies most directly.

## The case this project was built around

This project opened on a single company that had published a completion date **at least
{anchor_days_eom} days** after it passed, sitting on a public registry the whole time. The
trial is `{anchor_nct}`. Its registered date is a month, {anchor_expired_month}, which names
no day: read as the first of the month it was carried {anchor_days} days before the correction
on {anchor_corrected}, read as the last of the month {anchor_days_eom}. The smaller figure is
the one to lead with, and it is still roughly twenty-one times the thirty-day window the
regulation sets for the strata that window reaches. The cohort places the case on the
first-of-month distribution: the **{anchor_stretch_pct} percentile** of the industry
stretches, and the **{anchor_trial_pct} percentile** of the industry trials counted one
observation each. Long, and inside the distribution rather than outside it.

Both figures are the empirical share of observations at or below that duration;
{anchor_stretch_counts} is {anchor_stretch_share}. No observation equals it exactly, so "at
or below" versus "below" makes no difference, and the trial ranks {anchor_trial_counts} on
the per-trial unit. This is a different convention from the interpolated percentiles in the
tables above, so the two cannot be read off each other.

The finding was never that one sponsor was unusual. It is that in this frame a lapsed date
routinely stands for months before anything ends it, and that a quarter of industry
revisions replace a date that had already expired. Whether re-reading that field changes any
decision or outcome is not measured here and is not in this dataset.

## Methods, including everything that went wrong

The correction history is the record of what was caught, offered as that and nothing more.
It is incomplete by construction: later review rounds added more corrections after this
section was first written, and two of them are larger than anything that was in it.

**Measured with the product's own code.** The cohort calls the same `fetch_history`,
`from_cache` and `slip_breakdown` the console uses. That argument is sound and it has a cost
worth stating: a defect in the shared measurement code is shared by the product and the
study, so the study cannot act as an independent check on the product. It did not catch
{c_silence}.

**{c_store_n}: n was inflated, in the flattering direction.** The results store is written
by appending and the run is resumable, so a background pass and a manual merge appended
concurrently, and a large minority of rows were duplicates. A figure published mid-run as a
trial count was a row count. This correction was itself first published wrong, pairing a row
count from one moment with a distinct count from a later one. The magnitudes are in
`docs/LIMITS.md` and the git history; they are not snapshot fields, and this document no
longer carries figures that are not.

**{c_overcorrection}: an overcorrection, retracted.** An audit of the slip figures treated any
endpoint reword as a scope change and concluded most of the audited trials had unsupported
figures. That was wrong in both directions: it excluded a real multi-year movement because
the sponsor reworded an endpoint in the same filing, and it created a laundering route,
since a sponsor wanting a delay gone from the comparable total need only reword the
endpoint. A guard the subject can defeat by editing prose, in the direction that flatters
them, is not a guard.

**{c_headline_downgrade}: the headline was downgraded**, from calling the anchor case remarkable to
placing it at its percentile, on this project's own evidence.

**{c_pooled_rate}: a rule stated in prose and violated in code.** The report printed a pooled
all-strata section on every run, for as long as the rule against pooling had existed.

**{c_cache_loss}: two trials lost to a bug and recovered.** The version cache wrote each fetch
straight to its target path, so an interrupted run left a truncated file that every later
read of that trial failed on. Two NIH trials stored a parse error in place of a measurement.
Fixed at the source under a written amendment procedure, then re-measured.

**{c_silence}: the headline measure could not see silence.** The stretch measure needs a
later filing to close a lapse, so a sponsor that goes quiet scores as clean. Found by an
adversarial reviewer, not by the study. It is now reported as the secondary measure with
that property stated, point prevalence is primary, and the silent population is a result in
its own right rather than a gap.

**{c_filter_never_fired}: a wrong figure, published for one revision, from a filter that never fired.**
The first attempt at point prevalence read the date's ESTIMATED/ACTUAL type from a helper
that did not return it, compared a missing value against the string it was meant to exclude,
and therefore counted every completed trial that had correctly recorded its actual
completion date as carrying a lapsed one. It reported an order-of-magnitude larger
prevalence for industry and a near-universal one for OTHER_GOV. The true figures are
{industry_prevalence} and {og_prevalence}. The error was in the flattering direction,
produced a dramatic result, and passed a manual review, because a check that silently does
not apply looks exactly like a check that passes. The rank inversion it was offered as
evidence for turned out to be real and is reported above; the magnitudes were an order out.
A test now asserts that a past ACTUAL date does not count.

**{c_mandated_filing}: half a published headline was the filing the regulation requires.** A draft
reported that {retracted_after_lapse_rate} of industry dated revisions
({retracted_after_lapse_counts}) were filed after the date had already passed and presented
that as non-reconciliation. {retracted_actual_share} set the date to ACTUAL, which
for a late trial necessarily lands after the earlier estimate expired and is exactly the
update {reg_cite} mandates. The draft therefore quoted a regulation to argue the behaviour
was unlicensed while that regulation licensed half the numerator, and called the same filing
"the system working" in one section and a failure in another. Every number was
arithmetically correct; the sentence they supported was not, so no numeric check could have
caught it. The surviving figure is {industry_lapse_to_estimate}, and it is a supporting
mechanism here rather than the headline. The same draft published the trial-level companion,
{retracted_trial_counts} industry trials ({retracted_trial_rate}), from the same undivided
numerator; under the split it is {industry_trial_mechanism}. **Both figures are retracted.**
Found by an adversarial reviewer on its second pass over the same document.

**{c_one_stratum}: a four-stratum conclusion drawn from one stratum.** The clustering test was
first published as the industry row alone, under the sentence "there is no annual bunching".
The other three strata sat above their nulls and were not shown. Publishing all four was the
fix at the time; {c_clustering_control} is what happened when the test was given a control.

**{c_clustering_control}: the clustering conclusion is withdrawn in both directions.** With all four
strata published, the section concluded that the batching explanation stood for OTHER and
OTHER_GOV, whose intervals sat well above an even-spread null near anniversaries. Running
the identical test on control windows half a year off each anniversary returns a count at
least as high in three of the four strata, and in the fourth a count lower by a single
interval. The ratio therefore measures a right-skewed interval
distribution against a null that assumes an even spread, and says nothing about
anniversaries. Nothing about the test was wrong arithmetically; it had no control, and a
comparison with no control is not evidence. The innocence check now ends unresolved for
those strata rather than conceding to them.

**{c_anecdote}: an anecdote asserting a timing the record does not carry.** A draft named the
busiest of these trials and wrote that it had filed its {silent_versions_max} registry
versions *while* sitting past its date, offered as evidence that the silent carriers keep
filing other things and stop touching one field. The version count is real and it is a
**lifetime** count: nothing in the count says when those versions were filed relative to the
expiry, so the word "while" was invented. The generated form did not prevent this and would
not have. The version count is emitted from a field in the replacement sentence above; the
error was in a word with no digit in it, which is the residual the banner names, arriving in
the correction log of the same pass that built the guard.

**{c_month_convention}: a disclosure that understated its own scope.** The same pass that built
the generated form added a note that a month-only registry date is resolved to the first of
its month and so inflates days-since-expiry figures, and scoped that note to those figures and
to nothing else. It moves more than that. The same resolved date sets the sign of every
after-a-lapse revision, so switching to the end-of-month reading moves {flips} of the
{dated_total} dated revisions across the prospective boundary and moves the mechanism headline
from {industry_lapse_to_estimate} to {industry_lapse_to_estimate_eom} for industry. The
convention now appears where the mechanism figure is stated, both readings are carried in the
tables, and the smaller reading is the one quoted with "at least". Found by an adversarial
reviewer computing the alternate resolution the note said would not matter.

**{c_by_construction}: a claim upgraded, under review, from unsupported to false.** An earlier
draft said no silent carrier had filed anything since its date passed and called it true "by
construction", on the reasoning that a zero stretch count means no filing arrived over a
standing expired date. `{stretch_source_cite}` pairs consecutive versions, so it cannot emit a
stretch for a trial's first filing, and {silent_single} of the {silent_n} carriers have a
single version and therefore no pair at all. For those the zero is an empty loop, not a clean
record. One of them, `{silent_counterexample}`, registered its single filing years after the
date it recorded had already passed, so it is in the population and it did file after its date
passed. The claim is now split: {silent_multi_filed_after} of the {silent_multi} multi-version
carriers filed after a lapse, and the {silent_single} single-version ones filed once at a time
that runs both ways. The prior text said only that the store failed to support the anecdote;
the version under review asserted refutation on a mechanism that does not deliver it. A
correction written under review pressure is where the next defect goes, and this is the
instance.

**{c_jurisdiction}: a regulation quoted against a stratum it does not reach.** The document
used the {reg_cite} thirty-day window as a reference line against all four strata, including
OTHER_GOV. That stratum is not U.S. federal agencies; the drawn sponsors are non-U.S. public
bodies, and a trial one of them runs with no U.S. arm is generally not an applicable clinical
trial the U.S. rule binds at all. The window is now drawn against industry and NIH and
explicitly not extended to OTHER_GOV or OTHER, the registry facts for those strata are stated
without the regulation, and the undrawn FED stratum, where the duty applies most directly, is
recorded in `docs/PARKING.md` as the follow-up. What survives is a registry fact and not a
compliance one: where the U.S. duty plainly applies, industry still carries an expired estimate
at the rate the mechanism table reports; the strata where no such duty exists carry expired
dates more often, not less. That the two facts sit either side of a jurisdictional line is not
evidence the line explains them, and it is not offered as such: filing frequency confounds the
comparison and this study cannot separate the two.

**A note on what the corrections have in common, and when they stopped.** Most were found by
breaking something or by an outside reader, and several only on a later pass over material an
earlier pass had already read without catching it. {c_clustering_control} is the first found by
giving an existing test a control rather than by reading its output, and {c_by_construction} is
the first where a fix written under review made a true-but-weak claim false. The last three
came in one round, the eighth, and they are the deepest: an unexamined date convention, a
regulation quoted past its jurisdiction, an entailment that did not hold. Three review rounds
after that added no numbered correction. They found things -- a directional sentence backwards,
gaps in the guard's own coverage, a test that could corrupt what it checked -- but nothing that
retracted a published figure or claim, which is what a numbered correction is. Those are
recorded in `docs/LIMITS.md` instead, where the guard's limits live. A correction log is
supposed to reach zero, and the point of counting the rounds after it does is to be able to say
it did rather than assert it: the numbered corrections stopped at fourteen, and the rounds kept
running.

**What the corrections were, by layer.** The {n_corrections} of them sort into layers that run
from the most mechanical defect a check can catch to the least, and the sort is the argument:

{corrections_layer_table}

The first row is the point. Not one numbered correction is a wrong measured number: a review
seat recomputes every figure from the store each round, and the arithmetic has been right every
time. What was wrong was one layer up and then two: code that produced a wrong figure from right
data, a measure that was blind or a method that had no control, and, the hardest to catch and
where the last findings landed, {n_semantic} claims that were wrong in what they asserted while
every number in them was correct. The retyped-prose layer is the one this document's own form
closed: figures are rendered from fields now, not typed, so a mistyped figure is not a defect
that can occur here, and none has been numbered since. This is not a claim that the study is
without error. It is a claim about where its errors have been, which is a thing the record can
show and this table is how it shows it.

The review that produced this table ran to a stopping rule rather than to exhaustion. The
question space is unbounded: each adversarial round samples new questions, and "previously
cleared" only ever means "not yet asked". So the rule was not "review until nothing is found",
which never arrives, but "review until findings stop moving a claim past the bound it discloses".
The deep findings came in one round, the eighth. The rounds after it found a sentence with its
direction backwards, gaps in the guard's own coverage, a test that could corrupt what it checked,
a paragraph crediting the wrong round: real, fixed, and none of them a figure, a claim, or a
number that a reader relies on. When three consecutive rounds turned up nothing of that kind, the
rule was met. A study that says it stopped there is making a smaller claim than one that implies
the questions ran out, and it is the true one.

## What this does not license

- **No outcome claim.** There is no outcome variable here. This study does not know which of
  these trials succeeded, which sponsors raised money, or what any of it preceded.
- **No prediction.** Nothing here has been validated out of sample against anything.
- **No motive.** Why a date moved, or did not, is not observable from a registry diff. Slip
  has many ordinary causes: enrolment, regulators, honest rescoping, financing.
- **No time series.** Every rate is one look at the registry. Whether this is getting better
  or worse is a different study.
- **No uncertainty quantification.** At this stratum size the trial-level resolution is
  {resolution_trial} percentage points, and the conditional-prevalence column is far
  coarser at {resolution_open}, and no interval is computed anywhere. The
  equal ever-carried frequencies for industry and NIH should not be read as an estimate of
  equality. The revision-level rates are worse: they are computed over revisions, not
  trials, and revisions within a trial are not independent, since the industry revisions
  come from fewer than half as many trials. No clustered interval is computed, so every
  cross-stratum difference in this document is described, not tested.
- **Not novel terrain.** Trial delay is documented ({shadbolt_cite}). Registry version
  histories have been assembled at far larger scale by others. Adjacent published work links
  trial timing and firm behaviour ({guenzel_cite}), running the causal arrow the other way.
  What we could not find, in searches recorded in `docs/FINDINGS.md`, is work on how long a
  lapsed date is carried as a disclosure behaviour in its own right. That is a statement
  about our search, not about the literature.

## Reproducing this

```bash
python3 -m research.cohort --report            # prints the snapshot id beside the figures
python3 -m research.render_writeup --check     # fails if this document is stale
python3 -m pytest tests/test_cohort_store.py tests/test_prose_figures.py -q
```

The report refuses to describe the snapshot as current if the store has moved since the
freeze. The store is `{store_path}`, one row per trial; superseded measurements are kept in
`{archive_path}`. The frozen figures are in `{snapshot_path}` under the id `{snapshot_id}`, and a test recomputes every one of them from the store, field
by field, against the snapshot's own pinned as-of date. This document is written from those
fields by `research/render_writeup.py` and is regenerated whenever the snapshot is frozen.
""",

# --- blocks shared by the other four claim documents -----------------------

"block_anchor": """\
In {anchor_corrected_month}, Rocket Pharmaceuticals filed a protocol revision for trial
`{anchor_nct}` carrying a primary completion date of {anchor_expired_month}. That date names a
month, not a day, so read at its latest it **had already been expired for at least
{anchor_days_eom} days** when the revision was filed, and at its earliest {anchor_days} days.
Either way it stood in public, on a federal registry, machine readable the entire time.
""",

"block_headline": """\
In a random sample of {n_trials} phase {phases} trials, **this study cannot separate
reconciliation from filing frequency, and most trials carrying an expired commitment have
never reconciled a lapsed date** — {silent_by_stratum}, dates that have stood a median of
{silent_medians}. NIH sponsors file a median of {nih_versions} registry versions per
trial and have **zero** trials currently carrying an expired completion date. Non-U.S.
government and institutional sponsors, the OTHER_GOV stratum, file a median of {og_versions},
and **{og_of_open} of their still-open commitments have already expired**. The ordering is
monotone in filing frequency across all four strata, which is an association across four
points rather than a tested relationship.
""",

"block_mechanism": """\
The supporting mechanism, among sponsors still filing: **at least {industry_lapse_to_estimate_eom}
of industry completion-date revisions replace an estimate that had already expired**, a bound
because a month-only date has two readings and this is the smaller; the first-of-month reading
is {industry_lapse_to_estimate} ({industry_lapse_counts}). {industry_trial_mechanism} industry
trials that revised a date at all did it at least once. That is narrower than running late,
which is well documented, and narrower than the raw after-lapse count, because a revision
recording an *actual* completion is the update the regulation requires rather than a failure to
file it.

Industry point prevalence is {industry_prevalence} of all trials, and {industry_open_rate}
of those whose commitment is still open. The anchor case's carry of at least {anchor_days_eom}
days sits at the **{anchor_stretch_pct} percentile** of {anchor_stretch_n} such stretches:
long, but not the tail.
""",

"block_primary_measures": """\
Primary frequency is point prevalence, {industry_prevalence} of all industry trials and
{industry_open_rate} of those whose commitment is still open. Primary duration is per-trial
longest carry, NIH {nih_trial_p50} days against industry {industry_trial_p50}, a ratio of
{trial_ratio}, and every duration here is measured on completed spells only. The
stretch-based figures are a labelled secondary and cannot see a sponsor that stops filing.
**No all-strata average exists anywhere**, and the no-pooling rule rests on three differences
rather than on one ratio.
""",

"block_provenance": """\
Every cohort figure in the claim documents is emitted from a field of snapshot
`{snapshot_id}` by `research/render_writeup.py`: {n_trials} trials, {n_per_stratum} in each
of four sponsor strata, all measured, point prevalence as of {as_of}. The prose around them
contains no numerals and a test regenerates every generated block and fails on a one-byte
difference.
""",

"block_silence_note": """\
Trials whose most recent registered date is in the past and still typed as an estimate,
against the stretch measure that cannot see them, as of {as_of}:
""",

"block_clustering_note": """\
The clustering test in `docs/WRITEUP.md` reports both anniversary and control windows. The
control windows score at least as high in three of the four strata and lower by a single
interval in the fourth, so the test supports no conclusion about annual batching. The
conclusions drawn from it are withdrawn by {c_clustering_control}, which gave the test the
control it lacked; the earlier {c_one_stratum} only stopped it being shown for one stratum and
withdrew no conclusion.
""",
}


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def _p(key: str, f: dict) -> str:
    return PROSE[key].format(**f)


def writeup(f: dict) -> str:
    parts = [
        _p("title", f), _p("banner", f), _p("finding_head", f),
        _p("definition", f), _p("durations_stood", f),
        _p("headline_table_intro", f), f["headline_table"] + "\n",
        _p("headline_table_after", f),
        _p("reversal", f), f["reversal_table"] + "\n", _p("reversal_after", f),
        _p("mechanism_head", f), f["mechanism_table"] + "\n",
        _p("mechanism_after", f),
        _p("scope", f), _frame_table(f) + "\n", _p("frame_after", f),
        _p("duration_head", f), f["trial_duration_table"] + "\n",
        _p("duration_after", f), f["stretch_duration_table"] + "\n",
        _p("sensitivity_after", f), f["comparability_table"] + "\n",
        _p("comparability_after", f), f["clustering_table"] + "\n",
        _p("clustering_after", f),
    ]
    return _wrap("\n".join(parts))


def _frame_table(f: dict) -> str:
    return _table(
        ["", ""], ["---", "---"],
        [["Study type", "Interventional"],
         ["Phase", f["phases"]],
         ["Requires", "A registered primary completion date"],
         ["First posted", f"{f['frame_from']} to {f['frame_to']}"],
         ["Stratified by", "Lead sponsor class"],
         ["Drawn", f"{f['n_per_stratum']} per stratum, seed {f['seed']}"],
         ["Measured", f"{f['n_trials']} of {f['n_trials']}, after recovering two "
                      f"trials lost to a cache defect ({f['c_cache_loss']})"],
         ["Point prevalence as of", f"{f['as_of']}, pinned in the snapshot, never "
                                    f"read from the clock"]])


def blocks(f: dict) -> dict:
    """Named fragments the other claim documents embed."""
    S = cohort.load_snapshot()["strata"]
    primary = _table(
        ["Stratum", "carrying an expired estimate now",
         "invisible to the stretch measure", "longest carry p50",
         "median versions"],
        ["---", "---:", "---:", "---:", "---:"],
        [[c, f"{_of(S[c]['carrying_now'], S[c]['n'])} "
             f"({_pct(S[c]['carrying_now_rate'])})",
          _n(S[c]["carrying_now_invisible_to_stretches"]),
          _n(S[c]["trial_days_p50"]), _n(S[c]["median_versions"])]
         for c in STRATA])
    secondary = _table(
        ["Stratum", "n", "Carried a dead date", "days p50 / p90 / max",
         "Transitions", "Contingent", "Refused"],
        ["---", "---:", "---:", "---", "---:", "---:", "---:"],
        [[c, _n(S[c]["n"]), f"**{_pct(S[c]['carried_dead_date_rate'])}**",
          f"**{_n(S[c]['dead_days_p50'])}** / {_n(round(S[c]['dead_days_p90'], 1))} "
          f"/ {_n(S[c]['dead_days_max'])}",
          _n(S[c]["transitions"]), _pct(S[c]["contingent_rate"]),
          _pct(S[c]["refused_rate"])] for c in STRATA])
    silence = _table(
        ["Stratum", "carried at some point (stretch measure)", "carrying one now",
         "invisible to the stretch measure", "median versions"],
        ["---", "---:", "---:", "---:", "---:"],
        [[c, _pct(S[c]["carried_dead_date_rate"]), _pct(S[c]["carrying_now_rate"]),
          _n(S[c]["carrying_now_invisible_to_stretches"]),
          _n(S[c]["median_versions"])] for c in STRATA])
    unit = _table(
        ["", "INDUSTRY", "NIH", "ratio"],
        ["---", "---:", "---:", "---:"],
        # Both ratios come from `figures()` rather than being recomputed here.
        # They were computed twice, and the second copy kept rendering the right
        # answer while the first rendered an inverted one.
        [["median over all stretches", _n(S["INDUSTRY"]["dead_days_p50"]),
          _n(S["NIH"]["dead_days_p50"]), f"**{f['stretch_ratio']}**"],
         ["median of per-trial longest carry", _n(S["INDUSTRY"]["trial_days_p50"]),
          _n(S["NIH"]["trial_days_p50"]), f"**{f['trial_ratio']}**"],
         ["p90 over all stretches", _n(round(S["INDUSTRY"]["dead_days_p90"], 1)),
          _n(round(S["NIH"]["dead_days_p90"], 1)),
          _ratio(S["NIH"]["dead_days_p90"], S["INDUSTRY"]["dead_days_p90"])],
         ["p90 of per-trial longest carry", _n(round(S["INDUSTRY"]["trial_days_p90"], 1)),
          _n(round(S["NIH"]["trial_days_p90"], 1)),
          _ratio(S["NIH"]["trial_days_p90"], S["INDUSTRY"]["trial_days_p90"])]])
    return {
        "anchor": _wrap(_p("block_anchor", f)),
        "headline": _wrap(_p("block_headline", f)),
        "mechanism": _wrap(_p("block_mechanism", f)),
        "provenance": _wrap(_p("block_provenance", f)),
        "primary_measures": _wrap(_p("block_primary_measures", f)),
        "primary_table": primary + "\n",
        "secondary_table": secondary + "\n",
        "mechanism_table": f["mechanism_table"] + "\n",
        "refusal_table": f["refusal_table"] + "\n",
        "clustering_note": _wrap(_p("block_clustering_note", f)),
        "silence_note": _wrap(_p("block_silence_note", f)),
        "silence_table": silence + "\n",
        "unit_table": unit + "\n",
    }


def render(docs: dict | None = None) -> dict:
    """Every generated document, as {repo-relative path: full text}.

    `docs` supplies the current text of the block-carrying documents. It
    defaults to reading them from disk, and a caller passes them in so a check
    can render from a document it holds in memory rather than from the file. A
    guard that always renders from disk cannot tell a hand-edited document from
    a clean one: it compares the file against itself.
    """
    snap = cohort.load_snapshot()
    if snap is None:
        raise ValueError("no frozen snapshot; run `--freeze` first.")
    f = figures(snap)
    out = {WRITEUP: writeup(f)}
    frags = blocks(f)
    for doc in BLOCK_DOCS:
        path = os.path.join(REPO, doc)
        if docs is not None and doc in docs:
            text = docs[doc]
        elif os.path.exists(path):
            with open(path) as fh:
                text = fh.read()
        else:
            continue

        def sub(m):
            name = m.group(1)
            if name not in frags:
                raise ValueError(f"{doc} asks for unknown block {name!r}")
            return (OPEN % name) + "\n" + frags[name].rstrip("\n") + "\n" + CLOSE

        out[doc] = _BLOCK.sub(sub, text)
    return out


def write() -> list[str]:
    changed = []
    for doc, text in render().items():
        path = os.path.join(REPO, doc)
        old = open(path).read() if os.path.exists(path) else None
        if old != text:
            with open(path, "w") as fh:
                fh.write(text)
            changed.append(doc)
    return changed


def stale() -> list[str]:
    """Documents whose committed bytes differ from what the snapshot renders."""
    out = []
    for doc, text in render().items():
        path = os.path.join(REPO, doc)
        if not os.path.exists(path) or open(path).read() != text:
            out.append(doc)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if any generated document is stale")
    args = ap.parse_args()
    if args.check:
        bad = stale()
        if bad:
            print("STALE, regenerate with `python3 -m research.render_writeup`:")
            for d in bad:
                print(f"  {d}")
            raise SystemExit(1)
        print("Every generated document matches the snapshot.")
        return
    changed = write()
    print("Rewrote: " + (", ".join(changed) if changed else "nothing, all current"))


if __name__ == "__main__":
    main()
