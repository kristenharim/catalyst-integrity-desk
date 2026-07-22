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
import hashlib
import json
import os
import random
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.ctgov_history import _get, _parse_date
from engine.dimensions import from_cache
from engine.promise import Promise, slip_breakdown, walk
from research.backtest import carried_until_corrected, _versions as _cached_versions

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

    # Point prevalence: is this trial carrying a dead date RIGHT NOW? The stretch
    # measure above is ever-prevalence and counts only stretches that were
    # eventually corrected, so a date still standing today appears in neither.
    #
    # The discriminator is the date's own type, not the trial's status. An ACTUAL
    # date in the past is the reconciled case: the trial completed and the sponsor
    # recorded when. An ESTIMATED date in the past is a forecast that expired and
    # that nothing has reconciled since.
    #
    # 2026-07-22: this read `hist.__dict__.get("status")`, and `TrialHistory` has
    # no `status` field, so the "not COMPLETED" exclusion it appears to apply
    # never fired on any trial and the flag silently meant "the last date is in
    # the past". Nothing consumed it, so no published figure was affected, which
    # is luck and not design. Status is a per-revision field; the date's type is
    # the better discriminator and is why the fix does not simply reach for it.
    # Stored raw rather than resolved here, so the as-of date lives in the frozen
    # snapshot instead of in whenever the row happened to be measured. A point
    # prevalence computed against the wall clock is a different number every day
    # and silently so.
    # Read from the latest submitted version, NOT from `revs[-1]`. `revs` holds
    # only versions where the date's VALUE changed, so a sponsor who later flipped
    # the type from ESTIMATED to ACTUAL while keeping the same date does not appear
    # in it, and `revs[-1].pcd_type` then reports a stale ESTIMATED forever. That
    # over-counted point prevalence by 3 to 6 trials per stratum when measured.
    cached = _cached_versions(nct)
    last = cached[-1] if cached else None
    row["last_pcd"] = (last or {}).get("pcd")
    row["last_pcd_type"] = (last or {}).get("pcd_type")
    row["last_status"] = (last or {}).get("status")

    # The separation the thesis turns on. `held_days` is how much runway the OLD
    # date still had when the sponsor moved it, so its sign splits two behaviours
    # that a delay statistic cannot tell apart:
    #
    #   >= 0  revised while the date was still in the future. The sponsor is
    #         forecasting. The trial may be very late and the record still honest.
    #   <  0  revised only after the date had already passed. The record carried a
    #         commitment its author had stopped believing.
    #
    # Lateness is documented in the literature. Non-reconciliation is the claim
    # this project makes, and without this split the two are the same number.
    # And the split that survives scrutiny. A revision filed after the old date
    # passed is NOT automatically a failure to reconcile: if it sets the date to
    # ACTUAL it is the sponsor recording when the trial finished, which for a late
    # trial necessarily lands after the earlier estimate lapsed and is the update
    # 42 CFR 11.64(a)(1)(ii) requires. That is the reconciliation event, not its
    # absence. Half of the industry after-lapse revisions are exactly that.
    #
    # The behaviour this project claims to measure is narrower: an expired
    # ESTIMATE replaced by another ESTIMATE. The sponsor let the date pass and
    # then pushed it, without the trial having completed.
    # `n_pcd_revisions` is len(revs) and the FIRST entry is the initial
    # registration, not a change: 67 trials in this cohort have
    # n_pcd_revisions == 1 and have never revised anything. A field named
    # "revisions" whose value includes the registration has already misled one
    # published figure, so the count of actual changes gets its own name and the
    # prose uses only this one.
    row["n_date_changes"] = max(0, len(revs) - 1)

    # Submission intervals between consecutive date-changing filings, for the
    # batching test. Keying convention, stated because it changes the answer:
    # each interval runs between the submit dates of two consecutive versions
    # that CHANGED the completion date, so the first interval of a trial runs
    # from its initial registration rather than from a previous change.
    subs = [_parse_date(r.get("submitted")) for r in revs]
    row["submit_intervals"] = [(b - a).days for a, b in zip(subs, subs[1:])
                               if a and b]

    pairs = [(r.get("held_days"), (r.get("pcd_type") or "").upper())
             for r in revs if r.get("held_days") is not None]
    row["held_days"] = [h for h, _ in pairs]
    row["revisions_prospective"] = sum(1 for h, _ in pairs if h >= 0)
    row["revisions_on_the_day"] = sum(1 for h, _ in pairs if h == 0)
    row["revisions_after_lapse"] = sum(1 for h, _ in pairs if h < 0)
    row["revisions_after_lapse_to_actual"] = sum(
        1 for h, t in pairs if h < 0 and t == "ACTUAL")
    row["revisions_after_lapse_to_estimate"] = sum(
        1 for h, t in pairs if h < 0 and t != "ACTUAL")

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


def _archive_path() -> str:
    return os.path.join(OUT, "results-archive.jsonl")


def _snapshot_path() -> str:
    return os.path.join(OUT, "snapshot.json")


def load_results() -> list[dict]:
    """Measured trials, one row per NCT.

    Deduplicated on read, and this is not tidiness. The store is append-only and
    resumable, so a trial measured twice -- by an interrupted run resuming, or by
    two passes overlapping -- appends twice. Counting both inflates n and every
    rate computed from it, silently, in the direction of more data. That happened:
    a store of 179 rows held 131 distinct trials, 48 counted twice, and a figure
    published mid-run as "169 trials measured" was a row count covering 123. See
    Correction 1 in `docs/WRITEUP.md`.

    Last row wins, so a re-measure supersedes an earlier one without deleting it.
    A row carrying refusal reasons beats one that predates them regardless of
    order, because the later schema is strictly more informative.
    """
    path = _results_path()
    if not os.path.exists(path):
        return []
    with open(path) as f:
        rows = [json.loads(line) for line in f if line.strip()]
    return list(_dedupe(rows).values())


def _dedupe(rows: list[dict]) -> dict[str, dict]:
    """The winning row per trial, from rows already in memory.

    Separate from `load_results()` so that `compact()` selects winners by the same
    rule rather than by a second implementation of it. The first version of
    `compact()` re-read the file and compared object identity against rows it had
    not loaded, matched nothing, and archived the entire store.
    """
    best: dict[str, dict] = {}
    for r in rows:
        prev = best.get(r["nct"])
        if prev is None:
            best[r["nct"]] = r
        elif "refusal_reasons" in r or "refusal_reasons" not in prev:
            best[r["nct"]] = r
    return best


def compact() -> tuple[int, int]:
    """Rewrite the store with one row per trial, archiving every row dropped.

    `load_results()` already deduplicates on read, so this changes no published
    figure. It closes the residual named in `docs/LIMITS.md`: the file itself still
    held the duplicates, so any consumer reading it directly got the inflated view
    that produced the n=169 error. Deduplicating on read fixes the readers this
    project owns; it cannot fix a reader nobody has written yet.

    Nothing is destroyed. Superseded rows move to `results-archive.jsonl`, because
    discarding a measurement to make a count tidy is the wrong direction and an
    earlier measurement of the same trial is evidence about the measurement process
    even when it is not evidence about the trial.

    Written through a temp file and renamed, for the same reason `_cached()` now is.
    """
    path = _results_path()
    if not os.path.exists(path):
        return (0, 0)
    with open(path) as f:
        raw = [json.loads(line) for line in f if line.strip()]

    # Selected by the same rule `load_results()` uses, over the same objects, so
    # identity is meaningful. A trial's winning row survives and every other row
    # for that trial is archived, including one that happens to compare equal.
    keep = _dedupe(raw)
    winners = [r for r in raw if r is keep.get(r["nct"])]
    archived = [r for r in raw if r is not keep.get(r["nct"])]

    if archived:
        with open(_archive_path(), "a") as f:
            for r in archived:
                f.write(json.dumps(r) + "\n")

    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        for r in winners:
            f.write(json.dumps(r) + "\n")
    os.replace(tmp, path)
    return (len(winners), len(archived))


# ---------------------------------------------------------------------------
# The frozen snapshot
# ---------------------------------------------------------------------------
#
# Every published number has to cite a version of this store, or "80.0%" is a
# claim about whatever the file happened to contain the day someone read it. The
# id is content-addressed rather than a date or a counter, so a snapshot cannot be
# quietly re-cut under the same name: change one measured row and the id changes,
# and a test recomputes it from the store and fails when the two disagree.

SNAPSHOT_VERSION = 1


def _canonical(rows: list[dict]) -> bytes:
    """The bytes the snapshot id hashes. Frame included, because a rate means
    nothing without the denominator that produced it."""
    payload = {
        "snapshot_version": SNAPSHOT_VERSION,
        "seed": SEED,
        "frame_start": FRAME_START,
        "frame_end": FRAME_END,
        "phases": list(PHASES),
        "strata": list(STRATA),
        "rows": sorted(json.dumps(r, sort_keys=True) for r in rows),
    }
    return json.dumps(payload, sort_keys=True).encode()


def snapshot_id(rows: list[dict] | None = None) -> str:
    rows = load_results() if rows is None else rows
    return "cohort-" + hashlib.sha256(_canonical(rows)).hexdigest()[:12]


def stats(rows: list[dict], cls: str, as_of: date | None = None) -> dict:
    """Every rate for one stratum, computed once and used by both the report and
    the frozen snapshot, so the printed number and the published number cannot
    drift apart.

    There is deliberately no all-strata branch. NIH trials carry a dead date about
    as often as industry ones and roughly two and a half times as long, so a pooled
    figure would describe no population that exists. Asking for one is a mistake
    the caller should hear about rather than a number this returns.
    """
    if cls not in STRATA:
        raise ValueError(
            f"{cls!r} is not a stratum. Strata are not poolable: they differ by "
            f"about 2.4x on dead-date duration, so an all-strata rate describes "
            f"no population. Ask for one of {STRATA}.")

    sub = [r for r in rows if r["sponsor_class"] == cls]
    n = len(sub)
    if not n:
        return {"n": 0}
    with_dead = [r for r in sub if r["dead_date_stretches"] > 0]
    durations = [d for r in sub for d in r["dead_date_days"]]
    trans = sum(r.get("n_transitions", 0) for r in sub)
    est = [r["established_days"] for r in sub if r.get("n_transitions")]
    scope = sum(r.get("refused_scope", 0) for r in sub)
    unread = sum(r.get("refused_unreadable", 0) for r in sub)
    sup = sum(r.get("refused_superseded", 0) for r in sub)
    ref = sum(r.get("refused_revisions", 0) for r in sub)
    cont = sum(r.get("contingent_revisions", 0) for r in sub)

    # PRIMARY frequency: is the trial carrying a lapsed date right now? Needs no
    # later filing to exist, so unlike the stretch measure it can see a sponsor
    # that lapsed and went quiet. An ACTUAL date in the past is the reconciled
    # case and must not count; an ESTIMATE in the past is an expired forecast.
    as_of = as_of or date.today()

    def _carr(r: dict) -> bool:
        p = _parse_date(r.get("last_pcd"))
        return bool(p is not None and p < as_of
                    and (r.get("last_pcd_type") or "").upper() != "ACTUAL")

    carrying_now = silent = 0
    since, since_silent = [], []
    for r in sub:
        if _carr(r):
            carrying_now += 1
            d = (as_of - _parse_date(r["last_pcd"])).days
            since.append(d)
            if not r["dead_date_stretches"]:
                silent += 1                      # invisible to the stretch measure
                since_silent.append(d)

    # PRIMARY duration: one observation per trial, its longest carry. The stretch
    # unit emits a row per consecutive version pair, so one lapse spanning many
    # filings contributes many overlapping rows and a frequent filer contributes
    # more of them. Kept below as a labelled sensitivity, not as the headline.
    per_trial = [max(r["dead_date_days"]) for r in sub if r["dead_date_days"]]

    # The lateness/non-reconciliation split, at revision and at trial level. Trial
    # level is here rather than derived in prose because a figure that is not a
    # snapshot field is a figure no test can check.
    pro = sum(r.get("revisions_prospective", 0) for r in sub)
    late = sum(r.get("revisions_after_lapse", 0) for r in sub)
    late_act = sum(r.get("revisions_after_lapse_to_actual", 0) for r in sub)
    late_est = sum(r.get("revisions_after_lapse_to_estimate", 0) for r in sub)
    versions = sorted(r.get("n_versions") or 0 for r in sub)

    revising = [r for r in sub
                if (r.get("revisions_prospective", 0)
                    + r.get("revisions_after_lapse", 0)) > 0]
    t_late = [r for r in revising if r.get("revisions_after_lapse", 0)]
    t_late_est = [r for r in revising
                  if r.get("revisions_after_lapse_to_estimate", 0)]

    # The cross-tab the headline rests on, computed here rather than in prose.
    never = [r for r in sub if not r.get("n_date_changes")]
    date_changes = sorted(r.get("n_date_changes") or 0 for r in sub)

    # Batching test. If sponsors swept the registry on a yearly cycle, intervals
    # between date-changing filings would bunch near multiples of a year.
    NEAR, YEARS = 45, (365, 730, 1095)
    intervals = [d for r in sub for d in (r.get("submit_intervals") or [])]
    near = sum(1 for d in intervals
               if any(abs(d - y) <= NEAR for y in YEARS))

    # Trials still carrying an open commitment: the last registered date is an
    # estimate rather than an actual. The denominator a reader who only looks at
    # unreported trials actually wants, since a completed trial cannot be carrying
    # an expired estimate by construction.
    open_est = [r for r in sub
                if r.get("last_pcd")
                and (r.get("last_pcd_type") or "").upper() != "ACTUAL"]

    return {
        "n": n,
        # --- primary ---
        "carrying_now": carrying_now,
        "carrying_now_rate": carrying_now / n,
        "carrying_now_invisible_to_stretches": silent,
        # Conditional on the commitment still being open, which is the denominator
        # a reader looking only at unreported trials wants.
        "open_estimates": len(open_est),
        # How long the currently-expired dates have stood, which is what earns
        # the word "stopped" in "stopped filing".
        "carrying_days_since_expiry_p50": _pct(sorted(since), .5),
        "carrying_days_since_expiry_min": min(since) if since else None,
        # The subset the phrase "stopped filing" is about: carrying an expired
        # estimate AND no date correction filed since it lapsed. How long those
        # have stood is what earns the word "stopped".
        "silent_carrier_days_p50": _pct(sorted(since_silent), .5),
        "silent_carrier_days_min": min(since_silent) if since_silent else None,
        "silent_carriers_under_a_year": sum(1 for d in since_silent if d < 365),
        "carrying_never_revised": sum(1 for r in sub
                                      if not r.get("n_date_changes") and _carr(r)),
        "never_revised": len(never),
        "never_revised_and_carrying": sum(1 for r in never if _carr(r)),
        "never_revised_not_carrying": sum(1 for r in never if not _carr(r)),
        "median_date_changes": _pct(date_changes, .5),
        "submit_intervals_n": len(intervals),
        "submit_intervals_p50": _pct(sorted(intervals), .5),
        "submit_intervals_near_year_multiple": near,
        "submit_intervals_near_year_rate": (near / len(intervals)) if intervals else None,
        "carrying_now_of_open_rate": (carrying_now / len(open_est)) if open_est else None,
        "trial_days_p50": _pct(per_trial, .5),
        "trial_days_p90": _pct(per_trial, .9),
        "trial_days_max": max(per_trial) if per_trial else None,
        "n_trials_with_a_carry": len(per_trial),
        # --- the lateness split ---
        "revisions_prospective": pro,
        "revisions_on_the_day": sum(r.get("revisions_on_the_day", 0) for r in sub),
        "revisions_after_lapse": late,
        "revisions_after_lapse_to_actual": late_act,
        "revisions_after_lapse_to_estimate": late_est,
        "revisions_dated": pro + late,
        "revised_after_lapse_rate": (late / (pro + late)) if (pro + late) else None,
        # The claim that survives review: an expired estimate replaced by another
        # estimate. The rate above includes the mandated update-to-actual filing.
        "lapse_to_estimate_rate": (late_est / (pro + late)) if (pro + late) else None,
        "trials_revising": len(revising),
        "trials_with_a_lapse": len(t_late),
        "trials_with_lapse_to_estimate": len(t_late_est),
        "trials_never_revising": n - len(revising),
        "median_versions": _pct(versions, .5),
        # --- secondary, stretch-based: "lapsed and subsequently filed again" ---
        "carried_dead_date": len(with_dead),
        "carried_dead_date_rate": len(with_dead) / n,
        "n_stretches": len(durations),
        "dead_days_p50": _pct(durations, .5),
        "dead_days_p90": _pct(durations, .9),
        "dead_days_max": max(durations) if durations else None,
        "transitions": trans,
        "contingent": cont,
        "contingent_rate": (cont / trans) if trans else None,
        "refused": ref,
        "refused_rate": (ref / trans) if trans else None,
        "refused_scope": scope,
        "refused_scope_rate": (scope / trans) if trans else None,
        "refused_unreadable": unread,
        "refused_unreadable_rate": (unread / trans) if trans else None,
        "refused_superseded": sup,
        "refused_superseded_rate": (sup / trans) if trans else None,
        # Refusals measured before reasons were recorded. Must be zero before a
        # snapshot is published: an unsplit refusal bundles a finding about the
        # sponsor with a gap in our own data, and one number cannot carry both.
        "refused_unsplit": ref - scope - unread - sup,
        "established_p10": _pct(est, .1),
        "established_p50": _pct(est, .5),
        "established_p90": _pct(est, .9),
    }


def freeze() -> dict:
    """Cut a snapshot every published number can cite.

    Refuses to cut one over an incomplete measurement, because the failure this
    guards against is not a wrong number: it is a correct number that silently
    described fewer trials than the reader thinks.
    """
    all_rows = load_results()
    rows = [r for r in all_rows if "error" not in r]
    errors = [r for r in all_rows if "error" in r]
    if errors:
        raise ValueError(
            f"{len(errors)} trials failed to measure "
            f"({', '.join(r['nct'] for r in errors[:5])}). Fix or re-measure them "
            f"before freezing; a snapshot that quietly drops trials is the n-inflation "
            f"bug wearing the other sign.")

    # Point prevalence is as of a date, so the date is pinned into the snapshot
    # rather than read from the clock on every later report.
    as_of = datetime.now(timezone.utc).date()
    stale = [r["nct"] for r in rows if "last_pcd_type" not in r]
    if stale:
        raise ValueError(
            f"{len(stale)} rows predate the point-prevalence fields "
            f"({', '.join(stale[:5])}). Re-measure before freezing; the primary "
            f"frequency cannot be computed from them and would silently read as 0.")

    by_stratum = {cls: stats(rows, cls, as_of) for cls in STRATA}
    unsplit = {c: s["refused_unsplit"] for c, s in by_stratum.items()
               if s.get("refused_unsplit")}
    if unsplit:
        raise ValueError(
            f"refusals measured before the reason split: {unsplit}. Re-measure "
            f"those strata; an unsplit refusal rate is an upper bound, not a figure.")

    snap = {
        "snapshot_id": snapshot_id(all_rows),
        "snapshot_version": SNAPSHOT_VERSION,
        "frozen_at": as_of.isoformat(),
        "as_of": as_of.isoformat(),
        "seed": SEED,
        "frame": {
            "study_type": "INTERVENTIONAL",
            "phases": list(PHASES),
            "first_posted_from": FRAME_START,
            "first_posted_to": FRAME_END,
            "requires_registered_primary_completion": True,
            "enumeration_cap_per_stratum": 3000,
        },
        "n_distinct_trials": len(rows),
        "n_failed_to_measure": len(errors),
        "n_rows_stored": (sum(1 for _ in open(_results_path()))
                          if os.path.exists(_results_path()) else 0),
        "strata": by_stratum,
    }
    tmp = f"{_snapshot_path()}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(snap, f, indent=2, sort_keys=True)
    os.replace(tmp, _snapshot_path())
    return snap


def load_snapshot() -> dict | None:
    if not os.path.exists(_snapshot_path()):
        return None
    with open(_snapshot_path()) as f:
        return json.load(f)


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

    raw = sum(1 for _ in open(_results_path())) if os.path.exists(_results_path()) else 0
    print(f"COHORT: {len(rows)} distinct trials measured, {len(errors)} failed to "
          f"fetch, from {raw} stored rows (deduplicated on read).")
    print(f"Frame: interventional, phases {'/'.join(PHASES)}, first posted "
          f"{FRAME_START} to {FRAME_END}, with a registered primary completion.")
    print(f"Seed {SEED}. This is the denominator for every rate below.")

    snap = load_snapshot()
    if snap and snap["snapshot_id"] == snapshot_id():
        print(f"Snapshot {snap['snapshot_id']}, frozen {snap['frozen_at']}. "
              f"Cite it with every number.")
    elif snap:
        print(f"Snapshot {snap['snapshot_id']} is STALE: the store has changed "
              f"since it was frozen. Re-freeze before publishing anything.")
    else:
        print("No frozen snapshot. Run --freeze before publishing any number.")
    print()

    # No ALL section, and its absence is the finding. NIH sponsors carry a dead
    # date about as often as industry ones and roughly two and a half times as
    # long, so a pooled rate would describe no population that exists.
    as_of = _parse_date((snap or {}).get("as_of")) or date.today()
    for cls in STRATA:
        s = stats(rows, cls, as_of)
        if not s["n"]:
            continue
        print(f"--- {cls}  (n={s['n']}) ---")
        print(f"  CARRYING a lapsed date, {as_of}   {s['carrying_now']:>4} "
              f"({s['carrying_now_rate']:.1%})"
              f"   [{s['carrying_now_invisible_to_stretches']} invisible to stretches]")
        if s["trial_days_p50"] is not None:
            print(f"  longest carry per trial, days       "
                  f"p50 {s['trial_days_p50']:.0f}   p90 {s['trial_days_p90']:.0f}   "
                  f"max {s['trial_days_max']}")
        if s["revisions_dated"]:
            print(f"  date revisions                      {s['revisions_dated']:>4}"
                  f"   after it had lapsed {s['revisions_after_lapse']:>4} "
                  f"({s['revised_after_lapse_rate']:.1%})"
                  f"   prospective {s['revisions_prospective']:>4}")
        print(f"  median registry versions            {s['median_versions']:>4.0f}")
        print(f"  -- secondary: lapsed AND subsequently filed again --")
        print(f"  carried at some point               {s['carried_dead_date']:>4} "
              f"({s['carried_dead_date_rate']:.1%})")
        if s["n_stretches"]:
            print(f"  per-stretch duration, days          "
                  f"p50 {s['dead_days_p50']:.0f}   p90 {s['dead_days_p90']:.0f}   "
                  f"max {s['dead_days_max']}")
        print(f"  transitions                         {s['transitions']:>4}")
        if s["transitions"]:
            print(f"  contingent on prose alone           {s['contingent']:>4} "
                  f"({s['contingent_rate']:.1%})")
            print(f"  refused outright                    {s['refused']:>4} "
                  f"({s['refused_rate']:.1%})")
            # Split, because a finding about the sponsor and a gap in our data
            # are different things and one number cannot carry both.
            print(f"    of which scope changed            {s['refused_scope']:>4} "
                  f"({s['refused_scope_rate']:.1%})")
            print(f"    of which unreadable here          {s['refused_unreadable']:>4} "
                  f"({s['refused_unreadable_rate']:.1%})")
            print(f"    of which superseded               {s['refused_superseded']:>4} "
                  f"({s['refused_superseded_rate']:.1%})")
            if s["refused_unsplit"]:
                print(f"    measured before the split         {s['refused_unsplit']:>4}"
                      f"  <- re-measure these to close the bundle")
        if s["established_p50"] is not None:
            print(f"  established movement, days          "
                  f"p10 {s['established_p10']:.0f}   p50 {s['established_p50']:.0f}   "
                  f"p90 {s['established_p90']:.0f}")
        print()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--draw", type=int, metavar="N",
                    help="draw N trials per stratum and measure them")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--compact", action="store_true",
                    help="rewrite the store one row per trial, archiving the rest")
    ap.add_argument("--freeze", action="store_true",
                    help="cut a snapshot id every published number must cite")
    args = ap.parse_args()
    if args.draw:
        run(args.draw)
        report()
    elif args.compact:
        kept, archived = compact()
        print(f"Compacted: {kept} rows kept, {archived} archived to "
              f"{os.path.relpath(_archive_path())}. Nothing deleted.")
        report()
    elif args.freeze:
        snap = freeze()
        counts = ", ".join("%s %d" % (c, snap["strata"][c]["n"]) for c in STRATA)
        print(f"Frozen {snap['snapshot_id']} at {snap['frozen_at']}: "
              f"{snap['n_distinct_trials']} trials ({counts}).")
        print(f"Written to {os.path.relpath(_snapshot_path())}. Cite this id "
              f"beside every published figure.")
    elif args.report:
        report()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
