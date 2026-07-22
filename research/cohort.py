"""A random sponsor cohort, because every rate this project has quoted needs one.

Everything measured so far ran on fourteen trials that happened to be cached, and
those fourteen are the lapsed and binding trials of five companies picked by hand
to illustrate the problem. "Six of fourteen carried a dead date" is therefore a
direction and not a base rate: the sample was selected on the outcome.

This draws a random sample from a stated frame instead, so the four distributions
downstream of it mean something:

    dead-date duration    how long a passed completion date stays standing
    correction rate       how often one is ever corrected at all
    contingency rate      how often comparability breaks on prose alone
    established slip      date movement where the commitment provably held

THE FRAME IS THE DENOMINATOR, so it is stated rather than implied:

    interventional studies, phases 2 / 2-3 / 3, with a registered primary
    completion date, first posted between 2016-01-01 and 2023-12-31, stratified
    by lead-sponsor class.

The end date is deliberate. A trial first posted in 2024 has had too little time
to accumulate a revision history, and including it would bias every duration
downward. The start date is where ClinicalTrials.gov version history becomes
reliably complete.

    python3 -m research.cohort --draw 200        # sample, then measure
    python3 -m research.cohort --report          # re-report from stored results

Resumable: every measured trial is written as it completes, so an interrupted
run continues rather than restarting. Reproducible: the draw is seeded, and the
seed is stored with the results.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import urllib.parse
import urllib.request
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.ctgov_history import _get, _parse_date
from engine.dimensions import from_cache
from engine.promise import Promise, slip_breakdown, walk
from research.backtest import carried_until_corrected

V2 = "https://clinicaltrials.gov/api/v2/studies"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "cohort")
FRAME_START, FRAME_END = "2016-01-01", "2023-12-31"
PHASES = ("PHASE2", "PHASE2_PHASE3", "PHASE3")
SEED = 20260722          # stored with the results; changing it changes the sample

# Lead-sponsor classes to stratify on. Industry is the population the product is
# about; the others are the contrast that says whether anything found is a
# property of commercial sponsors or of registries in general.
STRATA = ("INDUSTRY", "NIH", "OTHER_GOV", "OTHER")


def _frame_query(sponsor_class: str, page_token: str | None, page_size: int = 200) -> str:
    params = {
        "filter.advanced": (
            f"AREA[StudyType]INTERVENTIONAL AND "
            f"AREA[StudyFirstPostDate]RANGE[{FRAME_START},{FRAME_END}] AND "
            f"AREA[LeadSponsorClass]{sponsor_class}"
        ),
        "filter.overallStatus": ",".join([
            "COMPLETED", "ACTIVE_NOT_RECRUITING", "RECRUITING",
            "ENROLLING_BY_INVITATION", "TERMINATED", "WITHDRAWN", "SUSPENDED",
            "UNKNOWN",
        ]),
        "fields": ",".join([
            "protocolSection.identificationModule.nctId",
            "protocolSection.statusModule.primaryCompletionDateStruct",
            "protocolSection.designModule.phases",
            "protocolSection.sponsorCollaboratorsModule.leadSponsor",
        ]),
        "pageSize": page_size,
        "countTotal": "true",
    }
    if page_token:
        params["pageToken"] = page_token
    return f"{V2}?{urllib.parse.urlencode(params)}"


def enumerate_frame(sponsor_class: str, cap: int = 3000) -> list[str]:
    """NCT ids in the frame for one stratum, up to a cap.

    The cap exists so a draw is cheap; it biases toward the registry's own
    ordering rather than being a true uniform draw from the whole stratum, and
    that is recorded in the results rather than glossed over.
    """
    out, token = [], None
    while len(out) < cap:
        d = _get(_frame_query(sponsor_class, token))
        for s in d.get("studies", []):
            p = s.get("protocolSection", {})
            phases = set((p.get("designModule") or {}).get("phases") or [])
            pcd = ((p.get("statusModule") or {}).get("primaryCompletionDateStruct") or {})
            if not (phases & set(PHASES)) or not pcd.get("date"):
                continue
            out.append(p["identificationModule"]["nctId"])
        token = d.get("nextPageToken")
        if not token:
            break
    return out[:cap]


def draw(n_per_stratum: int, seed: int = SEED) -> dict[str, list[str]]:
    rng = random.Random(seed)
    picked = {}
    for cls in STRATA:
        frame = enumerate_frame(cls)
        rng.shuffle(frame)
        picked[cls] = frame[:n_per_stratum]
        print(f"  {cls:10} frame {len(frame):>5}  drawn {len(picked[cls])}",
              flush=True)
    return picked


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------

def measure(nct: str, sponsor_class: str) -> dict:
    """The four metrics for one trial, using the same code the product uses.

    Deliberately calls `fetch_history`, `from_cache` and `slip_breakdown` rather
    than reimplementing them. A cohort study measured by a second implementation
    measures the second implementation.
    """
    from engine.ctgov_history import fetch_history

    row: dict = {"nct": nct, "sponsor_class": sponsor_class}
    try:
        hist = fetch_history(nct)
    except Exception as exc:                              # noqa: BLE001
        row["error"] = f"{type(exc).__name__}: {exc}"
        return row

    d = hist.as_dict()
    revs = d.get("revisions") or []
    row["n_versions"] = d.get("n_versions")
    row["n_pcd_revisions"] = len(revs)

    # Dead dates: every stretch where a passed date stayed standing.
    stretches = carried_until_corrected(nct)
    row["dead_date_stretches"] = len(stretches)
    row["dead_date_days"] = [s["days_carried"] for s in stretches]
    row["max_dead_days"] = max((s["days_carried"] for s in stretches), default=0)

    # Was the LAST registered date still standing after passing, uncorrected?
    last_pcd = _parse_date(revs[-1]["pcd"]) if revs else None
    row["ends_with_uncorrected_dead_date"] = bool(
        last_pcd is not None and last_pcd < date.today()
        and (hist.__dict__.get("status") or "") not in ("COMPLETED",)
    )

    # Comparability, via the product's own classifier.
    dims = from_cache(nct)
    promises = [
        Promise(
            actor=d.get("sponsor", ""), subject=nct,
            milestone="primary_completion", due=_parse_date(r.get("pcd")),
            scope=(dims[r["version"]].phase if r.get("version") in dims else None),
            endpoint=(dims[r["version"]].endpoint if r.get("version") in dims else None),
            population=(dims[r["version"]].enrollment if r.get("version") in dims else None),
            status=(dims[r["version"]].status if r.get("version") in dims else None),
            version=r.get("version"), submitted=r.get("submitted"),
        )
        for r in revs
    ]
    transitions = walk(promises)
    b = slip_breakdown(transitions)

    # Why each refusal happened. Without this, "refused" bundles a finding about
    # the sponsor (a count changed) with a gap in our data (a dimension was
    # unreadable), and the two cannot be told apart afterwards. An upper bound
    # that mixes them supports no downstream claim at all.
    reasons: dict[str, int] = {}
    for t in transitions:
        if t.comparable or t.kind == "text_revised":
            continue
        if t.kind == "supersession":
            key = "supersession"
        elif t.kind == "scope_revision":
            key = "scope:" + "+".join(sorted(t.changed)) if t.changed else "scope"
        else:
            key = "unreadable:" + ("+".join(sorted(t.changed)) if t.changed
                                   else "no_date")
        reasons[key] = reasons.get(key, 0) + 1
    row["refusal_reasons"] = reasons
    row["refused_scope"] = sum(v for k, v in reasons.items()
                               if k.startswith("scope"))
    row["refused_unreadable"] = sum(v for k, v in reasons.items()
                                    if k.startswith("unreadable"))
    row["refused_superseded"] = reasons.get("supersession", 0)

    row["n_transitions"] = len(transitions)
    row["established_days"] = b["established"]
    row["contingent_days"] = b["contingent"]
    row["contingent_revisions"] = b["contingent_revisions"]
    row["refused_revisions"] = b["refused"]
    row["reported_days"] = d.get("total_slip_days")
    return row


def _results_path() -> str:
    return os.path.join(OUT, "results.jsonl")


def load_results() -> list[dict]:
    path = _results_path()
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def run(n_per_stratum: int) -> None:
    os.makedirs(OUT, exist_ok=True)
    done = {r["nct"] for r in load_results()}
    print(f"Drawing {n_per_stratum} per stratum from the frame "
          f"({FRAME_START} to {FRAME_END}, phases {'/'.join(PHASES)}), seed {SEED}.")
    picked = draw(n_per_stratum)

    with open(os.path.join(OUT, "sample.json"), "w") as f:
        json.dump({"seed": SEED, "frame_start": FRAME_START,
                   "frame_end": FRAME_END, "phases": list(PHASES),
                   "n_per_stratum": n_per_stratum, "picked": picked}, f, indent=2)

    # Under-measured strata first. NIH trials carry far more versions, so a
    # fetch-bound run that takes strata in dict order starves them, which is a
    # stratification risk and not merely incompleteness: if NIH trials also
    # reconcile differently, every "all strata" rate inherits the gap.
    priority = {"NIH": 0, "OTHER_GOV": 1, "OTHER": 2, "INDUSTRY": 3}
    todo = [(nct, cls) for cls, ncts in picked.items()
            for nct in ncts if nct not in done]
    todo.sort(key=lambda t: (priority.get(t[1], 9), picked[t[1]].index(t[0])))
    print(f"\n{len(todo)} to measure ({len(done)} already stored).")
    with open(_results_path(), "a") as out:
        for i, (nct, cls) in enumerate(todo, 1):
            row = measure(nct, cls)
            out.write(json.dumps(row) + "\n")
            out.flush()
            if i % 10 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)}  {nct} {cls}", flush=True)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _pct(xs: list[float], p: float) -> float | None:
    if not xs:
        return None
    s = sorted(xs)
    k = (len(s) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def report() -> None:
    rows = [r for r in load_results() if "error" not in r]
    errors = [r for r in load_results() if "error" in r]
    if not rows:
        print("No results yet. Run --draw first.")
        return

    print(f"COHORT: {len(rows)} trials measured, {len(errors)} failed to fetch.")
    print(f"Frame: interventional, phases {'/'.join(PHASES)}, first posted "
          f"{FRAME_START} to {FRAME_END}, with a registered primary completion.")
    print(f"Seed {SEED}. This is the denominator for every rate below.\n")

    for cls in STRATA + ("ALL",):
        sub = rows if cls == "ALL" else [r for r in rows if r["sponsor_class"] == cls]
        if not sub:
            continue
        n = len(sub)
        with_dead = [r for r in sub if r["dead_date_stretches"] > 0]
        durations = [d for r in sub for d in r["dead_date_days"]]
        trans = sum(r.get("n_transitions", 0) for r in sub)
        cont = sum(r.get("contingent_revisions", 0) for r in sub)
        ref = sum(r.get("refused_revisions", 0) for r in sub)
        est = [r["established_days"] for r in sub if r.get("n_transitions")]

        print(f"--- {cls}  (n={n}) ---")
        print(f"  carried a dead date at some point   {len(with_dead):>4} "
              f"({len(with_dead)/n:.1%})")
        if durations:
            print(f"  dead-date duration, days            "
                  f"p50 {_pct(durations,.5):.0f}   p90 {_pct(durations,.9):.0f}   "
                  f"max {max(durations)}")
        print(f"  transitions                         {trans:>4}")
        if trans:
            print(f"  contingent on prose alone           {cont:>4} ({cont/trans:.1%})")
            print(f"  refused outright                    {ref:>4} ({ref/trans:.1%})")
            # Split, because a finding about the sponsor and a gap in our data
            # are different things and one number cannot carry both.
            scope = sum(r.get("refused_scope", 0) for r in sub)
            unread = sum(r.get("refused_unreadable", 0) for r in sub)
            sup = sum(r.get("refused_superseded", 0) for r in sub)
            unsplit = ref - scope - unread - sup
            print(f"    of which scope changed            {scope:>4} ({scope/trans:.1%})")
            print(f"    of which unreadable here          {unread:>4} ({unread/trans:.1%})")
            print(f"    of which superseded               {sup:>4} ({sup/trans:.1%})")
            if unsplit:
                print(f"    measured before the split         {unsplit:>4}"
                      f"  <- re-measure these to close the bundle")
        if est:
            print(f"  established movement, days          "
                  f"p10 {_pct(est,.1):.0f}   p50 {_pct(est,.5):.0f}   "
                  f"p90 {_pct(est,.9):.0f}")
        print()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--draw", type=int, metavar="N",
                    help="draw N trials per stratum and measure them")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    if args.draw:
        run(args.draw)
        report()
    elif args.report:
        report()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
