"""One sponsor's dead-date behaviour, placed against the cohort.

This is the first thing here that looks like the product rather than an
investigation. The cohort answers "what is normal". This answers "where does
this one sit", which is the only form in which a single company's record means
anything.

The framing rule, and it is the whole reason this file is careful: 80.0% of the
industry-sponsored trials in the cohort carried an already-passed registered
completion date at some point, so *doing it* separates nobody. What varies is
*how long*, and the distribution has a long tail: median 240 days, p90 996. So a
profile reports a percentile against the cohort, never a verdict, and the
sentence it supports is "this sponsor's longest stretch sits at the Nth
percentile of trials examined", not anything about the sponsor.

Those two figures are from snapshot `cohort-5b03269658b8` and are quoted here to
explain the design. Nothing in this module reads them: every number it prints is
computed from the cohort at call time, so the prose above can go stale without
the output ever doing so.

    python3 -m research.sponsor_profile NCT04248439
    python3 -m research.sponsor_profile --trial NCT04248439
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from research.backtest import carried_until_corrected
from research.cohort import load_results

# 42 CFR 11.64(a)(1)(ii): the Primary Completion Date "must be updated not later
# than 30 calendar days after the clinical trial reaches its actual primary
# completion date". Cited, not asserted, because the forbidden-claims list allows
# a statement about a disclosure duty only when the duty is named.
#
# It is a reference line on a chart and nothing more. Whether any particular
# stretch breached it depends on whether the trial actually completed on the
# registered date, which is not in this data.
REG_WINDOW_DAYS = 30
REG_CITE = "42 CFR 11.64(a)(1)(ii)"


def cohort_durations(sponsor_class: str | None = None) -> list[int]:
    rows = [r for r in load_results() if "error" not in r]
    if sponsor_class:
        rows = [r for r in rows if r.get("sponsor_class") == sponsor_class]
    return sorted(d for r in rows for d in (r.get("dead_date_days") or []))


def percentile_of(value: int, population: list[int]) -> float | None:
    """Fraction of the population at or below `value`."""
    if not population:
        return None
    return sum(1 for x in population if x <= value) / len(population)


def profile(nct: str, sponsor_class: str = "INDUSTRY") -> dict:
    stretches = carried_until_corrected(nct)
    pop = cohort_durations(sponsor_class)
    days = [s["days_carried"] for s in stretches]
    longest = max(days, default=0)
    return {
        "trial": nct,
        "stretches": stretches,
        "n_stretches": len(stretches),
        "longest_days": longest,
        "total_days": sum(days),
        "cohort_class": sponsor_class,
        "cohort_n_stretches": len(pop),
        "percentile": percentile_of(longest, pop) if longest else None,
        "over_regulatory_window": [s for s in stretches
                                   if s["days_carried"] > REG_WINDOW_DAYS],
    }


def render(p: dict) -> str:
    pop = cohort_durations(p["cohort_class"])
    out = [f"{p['trial']}  dead-date profile",
           f"  stretches carrying an already-passed registered date: {p['n_stretches']}"]
    for s in p["stretches"]:
        marker = "" if s["days_carried"] <= REG_WINDOW_DAYS else "  *"
        out.append(f"    {s['days_carried']:>5} days   expired {s['expired_on']}"
                   f"   corrected {s['corrected_on']}{marker}")
    if p["percentile"] is not None:
        out.append(f"\n  longest stretch {p['longest_days']} days, at the "
                   f"{p['percentile']:.0%} percentile of {p['cohort_n_stretches']} "
                   f"stretches observed in {p['cohort_class']} trials examined")
    if pop:
        import statistics
        out.append(f"  cohort for comparison: median {int(statistics.median(pop))} days, "
                   f"max {max(pop)}")
    if p["over_regulatory_window"]:
        out.append(f"\n  * longer than the {REG_WINDOW_DAYS}-day update window in "
                   f"{REG_CITE}.")
        out.append("    That rule concerns updating the date once a trial reaches its")
        out.append("    actual primary completion. Whether any stretch here breached it")
        out.append("    depends on whether the trial actually completed on the registered")
        out.append("    date, which this data does not contain. The window is a reference")
        out.append("    line, not a finding about this sponsor.")
    return "\n".join(out)


def demo() -> None:
    """Self-check, offline, against whatever cohort exists."""
    p = profile("NCT04248439")
    assert p["n_stretches"] >= 1
    assert p["longest_days"] == 677, p["longest_days"]
    # A percentile needs a population; if the cohort is empty it must be None
    # rather than a made-up number.
    if p["cohort_n_stretches"] == 0:
        assert p["percentile"] is None
    else:
        assert 0.0 <= p["percentile"] <= 1.0
    # Everything over the reference line must actually be over it.
    assert all(s["days_carried"] > REG_WINDOW_DAYS
               for s in p["over_regulatory_window"])
    txt = render(p)
    assert "677" in txt
    # A percentile appears only when there is a population to place it against.
    # An empty cohort must produce no percentile rather than a plausible-looking
    # one, and this asserts the absence rather than assuming it.
    assert ("percentile" in txt) == (p["cohort_n_stretches"] > 0)
    # The output must not read as a verdict.
    from orchestrator import lexicon
    v = lexicon.scan(txt)
    assert not v, [str(x) for x in v]
    print("ok")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("trial", nargs="?")
    ap.add_argument("--class", dest="cls", default="INDUSTRY")
    args = ap.parse_args()
    if not args.trial:
        demo()
        return
    print(render(profile(args.trial, args.cls)))


if __name__ == "__main__":
    main()
