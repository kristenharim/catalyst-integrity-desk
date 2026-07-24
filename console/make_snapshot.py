"""Build data/snapshot.json for the console.

Captures the full engine output for the demo tickers (SANA, PRME, RCKT, BEAM, SRPT)
plus the real lapse event for RCKT so the Flask app never touches a live API during
rendering.

Run:
    set -a; . ./.env; set +a
    python3 console/make_snapshot.py

Verify an existing snapshot:
    python3 console/make_snapshot.py --verify

Refresh display strings without a full rebuild (no credentials needed):
    python3 console/make_snapshot.py --displays

Recompute which requested tickers produced no contract, and why (network, but
no watsonx credentials, and it leaves the contracts and redline blocks alone):
    python3 console/make_snapshot.py --unresolved
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from datetime import date, timedelta

# Repo root is one level up from this file.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from console import states
from engine.ctgov_history import _parse_date
from engine.gap import build, find_trials, CatalystContract
from engine.ledger import BeliefCard
from engine.runway import DAYS_PER_MONTH, compute_runway, ticker_to_cik
from orchestrator.granite import GraniteClassifier
from orchestrator.redline import ContractDelta, run_redline

TICKERS = ["SANA", "PRME", "RCKT", "BEAM", "SRPT"]
SNAPSHOT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "snapshot.json")
SVG_WIDTH = 1100
SVG_PAD = 60  # pixels each side; usable span = SVG_WIDTH - 2*SVG_PAD = 980

# Thesis-break timeline geometry.  Wider padding than the revision timeline
# because the end markers carry two lines of label each.
TL_WIDTH = 1100
TL_PAD = 90


# ---------------------------------------------------------------------------
# Serialise one CatalystContract
# ---------------------------------------------------------------------------

def _fmt_m(v: float) -> str:
    """Format dollars as '$NNNm' with zero decimal places (e.g. '$182M').
    Stored in the snapshot so the template can output the string verbatim
    and the provenance test finds it as a substring of the snapshot.
    """
    return f"{round(v / 1e6)}"


def _fmt_1f(v: float | None) -> str | None:
    """Format a float to 1 decimal place.  None -> None."""
    if v is None:
        return None
    return f"{v:.1f}"


def _runway_display(r: dict) -> dict:
    """Compute the display sub-dict for a serialised runway dict.

    Takes raw numeric fields from the dict so this can be called on a loaded
    snapshot as well as on a live Runway object.
    """
    return {
        "cash_m": _fmt_m(r["cash"]),
        "securities_m": _fmt_m(r["securities"]),
        "liquidity_m": _fmt_m(r["liquidity"]),
        "burn_ttm_annual_m": _fmt_m(r["burn_ttm_annual"]),
        "burn_recent_annual_m": _fmt_m(r["burn_recent_annual"]),
        "months_low_1f": _fmt_1f(r["months_low"]),
        "months_high_1f": _fmt_1f(r["months_high"]),
    }


def _redline_display(breach: dict) -> dict:
    """Compute display strings for the redline breach so the template never
    formats numbers itself.
    """
    return {
        "observed_1f": _fmt_1f(breach["observed"]),
        "expected_low_1f": _fmt_1f(breach["expected_low"]),
        "expected_high_1f": _fmt_1f(breach["expected_high"]),
    }


def _lapse_display(redline: dict) -> dict:
    """Compute gap display strings for the lapse story fields."""
    return {
        "prior_gap_1f": _fmt_1f(redline.get("prior_gap_months")),
        "current_gap_1f": _fmt_1f(redline.get("current_gap_months")),
    }


def _cmd_bar(contracts: dict) -> dict:
    """Precompute command-bar counts so the template never uses |length or comparisons.

    counts:
      monitored        - total contracts in the snapshot
      active_breaches  - contracts whose verdict is not 'funded to catalyst'
                         and whose runway is reliable (they are ranked and breached)
      lapsed_expectations - total lapsed pivotal trials across all contracts
    """
    monitored = len(contracts)
    active_breaches = sum(
        1 for c in contracts.values()
        if c["runway"]["reliable"] and c.get("verdict") not in ("funded to catalyst", None)
    )
    lapsed_expectations = sum(
        len(c.get("lapsed", [])) for c in contracts.values()
    )
    return {
        "monitored": monitored,
        "active_breaches": active_breaches,
        "lapsed_expectations": lapsed_expectations,
    }


def _unresolved_row(ticker: str, cik_map) -> dict:
    """Say why a requested ticker produced no contract, instead of dropping it.

    `build()` returns None for two different reasons and the caller cannot tell
    them apart from the None alone.  Re-deriving here rather than changing the
    signature keeps `engine/gap.py` untouched, and both reasons are worth
    distinguishing on screen:

      no trial matched  - the sponsor-name search returned nothing.  A matching
                          problem, not a finding about the company.
      every date lapsed - the sponsor has registered pivotal completions and
                          every one of them is in the past.  That is the
                          strongest date-integrity signal there is, and it is
                          exactly the row that must never disappear quietly.

    Needs network (SEC and ClinicalTrials.gov), like the rest of the build.  No
    credentials, and never called at render time.
    """
    r = compute_runway(ticker, cik_map)
    trials = find_trials(r.name)
    if not trials:
        reason = "no pivotal trial matched this sponsor name in the registry"
    else:
        latest = max((t["pcd"] for t in trials if t.get("pcd")), default=None)
        reason = (
            f"every registered pivotal completion has lapsed "
            f"(latest {latest})" if latest else
            "every registered pivotal completion has lapsed"
        )
    # `name` is the string the registry search was actually run against, which is
    # why the no-match reason is readable: it names what was searched for.
    return {"ticker": ticker, "name": r.name, "reason": reason}


# ---------------------------------------------------------------------------
# Thesis-break timeline
# ---------------------------------------------------------------------------
# One picture carrying the whole conclusion: money on one axis, registered dates
# on the same axis, and the shortfall as the distance between them.  Reading the
# runway panel and the registry panel and joining them in your head is what this
# replaces.
#
# Every coordinate and every label string is computed here, so the template does
# no arithmetic and every number it prints is a substring of the snapshot.


def _months_after(iso_day: str, months: float) -> date:
    """Same month->days convention the engine uses, so the exhaustion date drawn
    here is the exhaustion date the engine computed and not a near miss."""
    return date.fromisoformat(iso_day) + timedelta(days=months * DAYS_PER_MONTH)


def _gap_months_between(exhaustion: date, catalyst: date) -> float:
    """Runway months left at a registered completion date.  Negative = short.
    Mirrors CatalystContract.gap_months exactly."""
    return (exhaustion - catalyst).days / DAYS_PER_MONTH


def _thesis_timeline(c: dict, today_iso: str) -> dict | None:
    """Precompute the thesis-break timeline for one contract.

    Returns None when there is nothing to draw: no bound catalyst, or a runway
    that could not be banded.  A contract with no lapsed trial still gets a
    timeline; the lapsed marker is simply absent.

    `today_iso` is the snapshot's pinned as_of, never the wall clock, so the
    picture a committed snapshot draws does not change tomorrow.
    """
    r = c["runway"]
    catalyst = _parse_date(c.get("catalyst_date"))
    if catalyst is None or r.get("months_low") is None:
        return None

    filing = date.fromisoformat(r["as_of"])
    # months_low is the conservative end (bigger burn), so it is the date the
    # money runs out first, and the one the gap is computed against.
    exh_lo = _months_after(r["as_of"], r["months_low"])
    exh_hi = _months_after(r["as_of"], r["months_high"])
    today = date.fromisoformat(today_iso)

    lapsed_trials = c.get("lapsed") or []
    lapsed_date = _parse_date(lapsed_trials[0]["pcd"]) if lapsed_trials else None

    marks = [filing, exh_lo, exh_hi, today, catalyst]
    if lapsed_date is not None:
        marks.append(lapsed_date)
    t0, t1 = min(marks), max(marks)
    span = (t1 - t0).days or 1
    # 6% breathing room each side so end markers are not flush with the frame.
    margin = timedelta(days=round(span * 0.06))
    t0, t1 = t0 - margin, t1 + margin
    span = (t1 - t0).days or 1
    usable = TL_WIDTH - 2 * TL_PAD

    def x(d: date) -> float:
        return round(TL_PAD + (d - t0).days / span * usable, 1)

    gap = c.get("gap_months")
    tl = {
        "x0": TL_PAD,
        "x1": TL_PAD + usable,
        "filing": {"x": x(filing), "date": r["as_of"]},
        "runway": {
            "x_lo": x(exh_lo),
            "x_hi": x(exh_hi),
            "date_lo": exh_lo.isoformat(),
            "date_hi": exh_hi.isoformat(),
            "months_lo_1f": _fmt_1f(r["months_low"]),
            "months_hi_1f": _fmt_1f(r["months_high"]),
        },
        "today": {"x": x(today), "date": today_iso},
        "catalyst": {
            "x": x(catalyst),
            "date": c.get("catalyst_date"),
            "nct": (c.get("trial") or {}).get("nct", ""),
            "gap_1f": _fmt_1f(gap),
        },
        "lapsed": None,
        "shortfall": None,
        "short": bool(gap is not None and gap < 0),
    }

    if lapsed_date is not None:
        tl["lapsed"] = {
            "x": x(lapsed_date),
            "date": lapsed_trials[0]["pcd"],
            "nct": lapsed_trials[0]["nct"],
            # The gap the thesis showed while this date was still binding.
            "gap_1f": _fmt_1f(_gap_months_between(exh_lo, lapsed_date)),
        }

    # The shortfall band runs from the day the money is gone to the day the
    # registered event is expected.  Drawn only when it is a shortfall; a
    # positive gap is a surplus and gets the same band in the other direction.
    if gap is not None:
        lo, hi = sorted([exh_lo, catalyst])
        tl["shortfall"] = {
            "x_from": x(lo),
            "x_to": x(hi),
            "months_1f": _fmt_1f(abs(gap)),
        }
    return tl


# ---------------------------------------------------------------------------
# Derivation: every displayed figure bound to the record and field it came from
# ---------------------------------------------------------------------------


def _derivation(c: dict, tl: dict | None) -> list[dict]:
    """One row per step from filed data to the funding gap.

    The point is not the arithmetic, which is a division and a subtraction. It is
    that each row names the exact record: an XBRL tag on a dated filing, or a
    numbered ClinicalTrials.gov version with the date it was submitted. A figure
    that cannot name its record does not get a row.
    """
    r = c["runway"]
    p = r.get("provenance") or {}
    d = r["display"]
    rows = [
        {"step": "Cash", "value": f"${d['cash_m']}M",
         "source": p.get("cash", "unknown"), "kind": "tag",
         "record": f"SEC XBRL company facts, CIK {r['cik']}, as of {r['as_of']}"},
    ]
    if p.get("securities") and p["securities"] != "none":
        rows.append({"step": "Short-term securities", "value": f"${d['securities_m']}M",
                     "source": p["securities"], "kind": "tag",
                     "record": f"SEC XBRL company facts, CIK {r['cik']}, as of {r['as_of']}"})
    else:
        rows.append({"step": "Short-term securities", "value": f"${d['securities_m']}M",
                     "source": "no short-term investment tag on the cash date",
                     "kind": "note", "record": ""})
    rows.append({"step": "Liquidity", "value": f"${d['liquidity_m']}M",
                 "source": "cash + short-term securities", "kind": "calc", "record": ""})

    # The conservative end of the burn band is whichever window burns faster;
    # naming it rather than assuming keeps the row honest when they swap.
    ttm, recent = r["burn_ttm_annual"], r["burn_recent_annual"]
    if recent >= ttm:
        burn_v, burn_label = d["burn_recent_annual_m"], "most recent quarter, annualised"
    else:
        burn_v, burn_label = d["burn_ttm_annual_m"], "trailing twelve months"
    rows.append({"step": "Burn, conservative end of band", "value": f"${burn_v}M/yr",
                 "source": p.get("burn", "unknown"), "kind": "tag",
                 "record": burn_label})

    if tl is None:
        return rows

    rows.append({"step": "Runway, conservative end",
                 "value": f"{tl['runway']['months_lo_1f']} months",
                 "source": "liquidity / burn", "kind": "calc", "record": ""})
    rows.append({"step": "Runway exhaustion date", "value": tl["runway"]["date_lo"],
                 "source": f"filing date {r['as_of']} + {tl['runway']['months_lo_1f']} months",
                 "kind": "calc", "record": ""})

    hist = c.get("history") or {}
    revs = hist.get("revisions") or []
    if revs:
        last = revs[-1]
        record = (f"ClinicalTrials.gov version {last['version']}, "
                  f"submitted {last['submitted']}")
    else:
        record = "ClinicalTrials.gov, current version"
    rows.append({"step": "Registered primary completion", "value": tl["catalyst"]["date"],
                 "source": tl["catalyst"]["nct"], "kind": "tag", "record": record})

    if tl["catalyst"]["gap_1f"] is not None:
        rows.append({"step": "Funding gap", "value": f"{tl['catalyst']['gap_1f']} months",
                     "source": "exhaustion date - registered completion date",
                     "kind": "result", "record": ""})
    return rows


# ---------------------------------------------------------------------------
# The monitoring queue
# ---------------------------------------------------------------------------
# The question this product answers is not "rank these companies", which a
# commercial screener already does. It is "which of my beliefs need me this
# morning". So the queue is a list of reasons to look, not a list of companies:
# one row per contract per reason, worst first, and a row saying nothing is
# wrong when nothing is.
#
# Every state here is computed from the snapshot. States that cannot be computed
# from one snapshot are not shown rather than shown empty: a changed SEC tag path
# needs a previous snapshot to diff against, and there is only ever one.

# Re-exported so there is exactly one threshold in the codebase. The classifier
# owns it because the trigger it produces is what the queue row is projected from.
APPROACHING_MONTHS = states.APPROACHING_MONTHS

# Worst first. The order is the order an analyst should read them in, so it is
# ranked by how much of the thesis is already gone, not by how alarming it looks.
QUEUE_STATES = [
    ("breached", "breached"),
    ("lapsed", "registry expectation lapsed"),
    ("approaching", "approaching breach"),
    ("unreliable", "burn estimate unreliable"),
    ("clear", "no action required"),
]
_QUEUE_RANK = {k: i for i, (k, _) in enumerate(QUEUE_STATES)}


def _queue_rows(ticker: str, c: dict) -> list[dict]:
    """Every reason this contract is worth looking at today.

    A projection over `states.build_triggers`, not a second opinion about it.
    Two functions deciding independently what counts as a reason to look is how
    the queue and the inbox end up disagreeing about the same company, so the
    triggers are canonical and this maps them onto the older vocabulary.

    Triggers with no legacy state (endpoint continuity, refused comparison) are
    skipped rather than invented into the queue. They are new, the queue never
    counted them, and adding them here would silently move its counts.
    """
    rows = []
    for t in states.build_triggers(c):
        legacy = states.LEGACY_QUEUE_STATE.get(t.kind)
        if legacy is None:
            continue
        rows.append({"state": legacy, "detail": t.detail})

    if not rows:
        rows.append({
            "state": "clear",
            "detail": (f"funding gap {c.get('gap_months_1f')} months against "
                       f"{c['trial']['nct']} ({c.get('catalyst_date')})"),
        })

    r = c["runway"]
    for row in rows:
        row["ticker"] = ticker
        row["name"] = r["name"]
        # An unreliable burn makes the gap unusable, and the project's rule is
        # that such a row is shown and never ranked.  Printing 2.6 months beside
        # "burn estimate unreliable" ranks it in the reader's head, which is the
        # same flattery by another route.
        row["gap_1f"] = c.get("gap_months_1f") if r.get("reliable") else None
        row["label"] = dict(QUEUE_STATES)[row["state"]]
    return rows


def _queue(contracts: dict) -> dict:
    """The whole queue, sorted worst first, with per-state counts.

    Counts are precomputed because the template must not use `|length` or a
    comparison; that rule is what keeps every number on screen traceable.
    """
    rows = []
    for ticker, c in contracts.items():
        rows.extend(_queue_rows(ticker, c))
    rows.sort(key=lambda row: (_QUEUE_RANK[row["state"]], row["ticker"]))

    counts = [
        {"state": state, "label": label,
         "n": sum(1 for row in rows if row["state"] == state)}
        for state, label in QUEUE_STATES
    ]
    return {
        "rows": rows,
        "counts": counts,
        # Rows that are not "no action required": the size of this morning's work.
        "needs_attention": sum(1 for row in rows if row["state"] != "clear"),
    }


# ---------------------------------------------------------------------------
# Promise identity, baked into the snapshot
# ---------------------------------------------------------------------------
# `engine/dimensions.py` reads the endpoint and enrolment per registry version
# out of `data/cache/`, which is gitignored and therefore absent from a fresh
# clone. So the classification is computed once here, at build time, and stored.
# `apply_displays` never recomputes it: a figure that changes depending on
# whether a local cache happens to exist is not a figure this project may show.


def _classify_history(hist: dict, actor: str) -> dict:
    """Attach a transition to each revision, and the totals it supports.

    This is where the project's own slip statistics get audited. A revision whose
    endpoint or enrolment changed did not slip, it changed shape, and the days
    between its dates describe two different commitments.
    """
    from engine.dimensions import enrich
    from engine.promise import Promise, slip_breakdown, walk

    enriched = enrich(hist)
    revs = enriched.get("revisions") or []
    promises = [
        Promise(
            actor=actor, subject=enriched.get("nct", ""),
            milestone="primary_completion", due=_parse_date(r.get("pcd")),
            scope=r.get("phase"), endpoint=r.get("primary_outcome"),
            population=r.get("enrollment"), status=r.get("status"),
            version=r.get("version"), submitted=r.get("submitted"),
        )
        for r in revs
    ]
    transitions = walk(promises)
    # A transition describes a PAIR, so it is stored on the later revision. The
    # first revision has no predecessor and therefore no transition, which is
    # different from having an uncertain one.
    for rev, t in zip(revs[1:], transitions):
        rev["transition"] = t.kind
        rev["transition_reason"] = t.reason
        rev["transition_changed"] = t.changed
        rev["slip_days"] = t.slip_days
    if revs:
        revs[0]["transition"] = None

    b = slip_breakdown(transitions)
    enriched["slip_established_days"] = b["established"]
    enriched["slip_contingent_days"] = b["contingent"]
    enriched["slip_contingent_revisions"] = b["contingent_revisions"]
    enriched["slip_upper_bound_days"] = b["upper_bound"]
    enriched["slip_refused_revisions"] = b["refused"]
    enriched["slip_reported_days"] = hist.get("total_slip_days")
    # Fully established only when nothing was refused AND nothing is waiting on
    # a human reading two endpoint descriptions.
    enriched["slip_fully_established"] = (
        b["refused"] == 0 and b["contingent_revisions"] == 0
    )
    return enriched


def apply_transitions(snapshot: dict) -> dict:
    """Classify every stored revision. Needs data/cache/; run before committing."""
    for c in snapshot.get("contracts", {}).values():
        actor = c["runway"]["name"]
        if c.get("history"):
            c["history"] = _classify_history(c["history"], actor)
        c["lapsed_history"] = [
            _classify_history(h, actor) for h in (c.get("lapsed_history") or []) if h
        ]
    return snapshot


def apply_displays(snapshot: dict) -> dict:
    """Add or refresh all display sub-dicts in a loaded snapshot dict.

    Idempotent: calling twice produces the same result.  No network access,
    no credentials needed.  Returns the mutated snapshot for convenience.
    """
    # Pin the classification date once, then never read the clock again.
    # Lapsed-versus-future, and everything the timeline draws from it, is a
    # statement about the day the snapshot was built.  Leaving it on
    # date.today() meant a committed snapshot silently redrew itself tomorrow.
    today_iso = snapshot.setdefault("as_of", date.today().isoformat())

    for c in snapshot.get("contracts", {}).values():
        c["runway"]["display"] = _runway_display(c["runway"])
        if c.get("gap_months") is not None:
            c["gap_months_1f"] = _fmt_1f(c["gap_months"])
        c["thesis_timeline"] = _thesis_timeline(c, today_iso)
        c["derivation"] = _derivation(c, c["thesis_timeline"])
        # Evidence axis only. Workflow and record integrity are joined at
        # request time in console/review.py, because both depend on a ledger
        # file that changes long after this snapshot was written.
        c["decision"] = states.build_decision(c)

    redline = snapshot.get("redline")
    if redline and redline.get("breach"):
        redline["breach"]["display"] = _redline_display(redline["breach"])
    if redline and redline.get("prior_gap_months") is not None:
        redline["lapse_display"] = _lapse_display(redline)
    if redline and redline.get("card_id"):
        # The card_id carries the ticker ("rckt:funded_to_catalyst"), so the
        # redline view can reach that contract's derivation without a second
        # copy of it living in the redline block.
        redline["ticker"] = redline["card_id"].split(":")[0].upper()

    # Refresh command-bar counts from the (now display-enriched) contracts block.
    snapshot["cmd_bar"] = _cmd_bar(snapshot.get("contracts", {}))
    # The queue reads gap_months_1f, so it is built after the display pass.
    snapshot["queue"] = _queue(snapshot.get("contracts", {}))

    return snapshot


def _serialise_runway(r) -> dict:
    """Runway dataclass fields plus all properties the template needs.

    The 'display' sub-dict holds every formatted string the templates render
    so the provenance test can find them verbatim in the snapshot.  Rounding
    happens here, not in the template.
    """
    raw = {
        "ticker": r.ticker,
        "cik": r.cik,
        "name": r.name,
        "as_of": r.as_of,
        "cash": r.cash,
        "securities": r.securities,
        "liquidity": r.liquidity,
        "burn_ttm_annual": r.burn_ttm_annual,
        "burn_recent_annual": r.burn_recent_annual,
        "months_low": r.months_low,
        "months_high": r.months_high,
        "reliable": r.reliable,
        "burn_unstable": r.burn_unstable,
        "inflow_quarters": r.inflow_quarters,
        "provenance": r.provenance,
        "notes": r.notes,
    }
    # Pre-formatted display strings: templates use these verbatim so every
    # number in the HTML is a substring of the snapshot JSON.
    raw["display"] = _runway_display(raw)
    return raw


def _iso(d: date | None) -> str | None:
    return d.isoformat() if d is not None else None


def _add_svg_x(revisions: list[dict]) -> list[dict]:
    """Compute and attach svg_x to each revision dict (mutates in place, returns list).

    Maps each revision's submitted date linearly onto a 1100px canvas with 60px
    padding each side.  When there is only one revision the single node sits centred.
    """
    dates = []
    for r in revisions:
        try:
            dates.append(date.fromisoformat(r["submitted"]))
        except (ValueError, TypeError):
            dates.append(None)

    real_dates = [d for d in dates if d is not None]
    if not real_dates:
        for r in revisions:
            r["svg_x"] = SVG_PAD + (SVG_WIDTH - 2 * SVG_PAD) / 2
        return revisions

    span_start = min(real_dates)
    span_end = max(real_dates)
    total_days = (span_end - span_start).days or 1  # avoid div-by-zero for single node

    usable = SVG_WIDTH - 2 * SVG_PAD
    for r, d in zip(revisions, dates):
        if d is None:
            r["svg_x"] = round(SVG_PAD + usable / 2, 1)
        else:
            frac = (d - span_start).days / total_days
            r["svg_x"] = round(SVG_PAD + frac * usable, 1)

    return revisions


def _serialise_history(history) -> dict | None:
    if history is None:
        return None
    d = history.as_dict()
    # as_dict() uses dataclasses.asdict() for revisions, which serializes fields only.
    # carried_expired, days_expired and is_late_move are @property on Revision, so they
    # are silently dropped.  Patch them in by reading the properties off the live objects
    # rather than recomputing from held_days, so the snapshot cannot drift from the engine.
    for rev_dict, rev_obj in zip(d["revisions"], history.revisions):
        rev_dict["carried_expired"] = rev_obj.carried_expired
        rev_dict["days_expired"] = rev_obj.days_expired
        rev_dict["is_late_move"] = rev_obj.is_late_move
    _add_svg_x(d["revisions"])
    return d


def _serialise_contract(c: CatalystContract) -> dict:
    # Lapsed pivotal trials: each is a date-integrity signal, never a catalyst.
    # Serialise with the same svg_x treatment as the binding history so the
    # template can draw their timelines identically.
    lapsed_serialised = [
        _serialise_history(h) for h in c.lapsed_history if h is not None
    ]
    return {
        "runway": _serialise_runway(c.runway),
        "trial": c.trial,
        "history": _serialise_history(c.history),
        "gap_months": c.gap_months,
        # Pre-formatted gap string: "+8.4" or "-14.5" — stored so the template
        # outputs it verbatim and the provenance test finds it in the snapshot.
        "gap_months_1f": _fmt_1f(c.gap_months),
        "catalyst_date": _iso(c.catalyst_date),
        "verdict": c.verdict,
        # Lapsed: list of trial dicts whose registered completion has passed.
        "lapsed": c.lapsed,
        # Lapsed history: serialised TrialHistory objects for each lapsed trial.
        "lapsed_history": lapsed_serialised,
    }


# ---------------------------------------------------------------------------
# Real lapse event for RCKT
# ---------------------------------------------------------------------------

_GRANITE_MAX_ATTEMPTS = 5
_GRANITE_BACKOFF_START = 30  # seconds; doubles each attempt


def _classify_once(delta, card) -> "ChallengeCard | None":  # type: ignore[name-defined]
    """One attempt at Granite classification via run_redline.

    Returns None if the engine detected no breach -- that is a broken premise,
    not a case to work around.  Returns the ChallengeCard otherwise; caller
    checks source.  A fresh GraniteClassifier is constructed each time so any
    cached token state from a failed attempt does not carry over.
    """
    classifier = GraniteClassifier()
    return run_redline(delta, card, classifier=classifier)


def _build_rckt_redline(rckt: CatalystContract) -> dict:
    """Build the redline from the real lapse event on RCKT.

    The approved contract is built from the lapsed trial the engine already
    carries (NCT04248439, registered primary completion 2026-05-05), which
    gives gap_months ~+8.4.  The recomputed contract is the real current
    contract (NCT06092034, 2028-04), which gives gap_months ~-14.5.

    No later registry version reconciled the registered expectation before the
    date passed.  That is the event the BeliefCard is being updated to reflect,
    and it is the whole of what the record supports: this project reads registry
    version history, so it can say what the registry did and cannot say what the
    company did or did not publish elsewhere.
    """
    if not rckt.lapsed:
        print(
            "ERROR: RCKT has no lapsed trial. Cannot build the lapse redline.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Approved contract: same runway, bound to the lapsed trial that the
    # original thesis rested on.
    approved_trial = rckt.lapsed[0]
    approved_history = rckt.lapsed_history[0] if rckt.lapsed_history else None
    approved = CatalystContract(
        runway=rckt.runway,
        trial=approved_trial,
        history=approved_history,
    )

    # Recomputed contract: the real current contract (already built by the caller).
    recomputed = rckt

    prior_gap = approved.gap_months
    current_gap = recomputed.gap_months

    delta = ContractDelta(approved=approved, recomputed=recomputed)

    # BeliefCard: the thesis as it stood against the lapsed trial.
    # The approved band is centred on the prior gap; expected_low=0 (funded to
    # catalyst was the thesis).  The current gap is well below 0, so a breach fires.
    card = BeliefCard(
        card_id="rckt:funded_to_catalyst",
        scope=approved_trial["nct"],
        claim=(
            "Rocket Pharmaceuticals reaches the registered primary completion of "
            f"{approved_trial['nct']} ({approved_trial['pcd']}) before runway exhaustion, "
            "with a non-negative funding gap."
        ),
        metric="gap_months",
        expected_low=0.0,
        expected_high=max((prior_gap or 0.0) + 2.0, 2.0),
        driver="SEC XBRL liquidity (Q1-2026 10-Q) vs ClinicalTrials.gov registered PCD",
        confidence=3,
        source="console.make_snapshot",
        as_of=rckt.runway.as_of,
    )

    challenge_card = None
    for attempt in range(1, _GRANITE_MAX_ATTEMPTS + 1):
        print(f"  Granite attempt {attempt}/{_GRANITE_MAX_ATTEMPTS}...", flush=True)
        challenge_card = _classify_once(delta, card)
        if challenge_card is None:
            # run_redline found no breach: the lapse did not break the contract.
            # This should never happen because the gap flipped from +8.4 to -14.5.
            print(
                f"ERROR: RCKT lapse did not produce a breach "
                f"(recomputed gap_months={delta.recomputed.gap_months:.2f}, "
                f"approved band=[{card.expected_low:.1f}, {card.expected_high:.1f}]).\n"
                f"Check that rckt.lapsed[0] is the correct trial.",
                file=sys.stderr,
            )
            sys.exit(1)
        if challenge_card.classification.source == "granite":
            break
        if attempt < _GRANITE_MAX_ATTEMPTS:
            wait = _GRANITE_BACKOFF_START * (2 ** (attempt - 1))
            print(f"  stub fallback (free-tier congestion?), waiting {wait}s...", flush=True)
            time.sleep(wait)
    else:
        print(
            "ERROR: Granite returned stub after all attempts.\n"
            "The free-tier concurrent pool is likely congested. Run again later.",
            file=sys.stderr,
        )
        sys.exit(1)

    return {
        "card_id": challenge_card.card_id,
        "breach": {
            "card_id": challenge_card.breach.card_id,
            "metric": challenge_card.breach.metric,
            "observed": challenge_card.breach.observed,
            "expected_low": challenge_card.breach.expected_low,
            "expected_high": challenge_card.breach.expected_high,
            "direction": challenge_card.breach.direction,
        },
        "classification": {
            "label": challenge_card.classification.label,
            "confidence": challenge_card.classification.confidence,
            "rationale": challenge_card.classification.rationale,
            "source": challenge_card.classification.source,
        },
        "memo": challenge_card.memo,
        "redline": challenge_card.redline(),
        "proposed_card": asdict(challenge_card.proposed_card),
        # Lapse story fields: serialised so the template never does arithmetic.
        "prior_trial": approved_trial["nct"],
        "prior_pcd": approved_trial["pcd"],
        "prior_gap_months": prior_gap,
        "current_trial": recomputed.trial["nct"],
        "current_pcd": _iso(recomputed.catalyst_date),
        "current_gap_months": current_gap,
        # Whether the registry ever reconciled the lapsed expectation is NOT
        # serialised here. It used to be, as a hardcoded True, which made the
        # sentence on /redline a caption rather than a reading: the literal and
        # the version history it summarised could disagree and only the literal
        # reached the page. `console.review.registry_reconciliation` derives it
        # from `lapsed_history` at render time instead. The frozen snapshot still
        # carries the retired key and nothing reads it.
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_snapshot() -> dict:
    # Fail loudly if Granite credentials are absent — no silent fallback to stub.
    if not os.environ.get("WATSONX_API_KEY"):
        print("ERROR: WATSONX_API_KEY is not set.", file=sys.stderr)
        print("Run: set -a; . ./.env; set +a", file=sys.stderr)
        sys.exit(1)

    cik_map = ticker_to_cik()
    contracts: dict[str, dict] = {}
    rckt_contract: CatalystContract | None = None

    unresolved: list[dict] = []
    for ticker in TICKERS:
        print(f"  building {ticker}...", flush=True)
        c = build(ticker, cik_map)
        if c is None:
            # Shown on the screen, never silently dropped.  A requested ticker
            # that vanishes with only a stderr line is the failure this project
            # exists to catch, so it gets a row and a reason.
            row = _unresolved_row(ticker, cik_map)
            print(f"  {ticker}: unresolved, {row['reason']}", file=sys.stderr)
            unresolved.append(row)
            continue
        contracts[ticker] = _serialise_contract(c)
        if ticker == "RCKT":
            rckt_contract = c

    if rckt_contract is None:
        print("ERROR: RCKT contract not built — cannot produce redline.", file=sys.stderr)
        sys.exit(1)

    # The 677-day expired-date row is the demo centrepiece.  Assert it survives in the
    # serialized snapshot.  The binding trial (NCT06092034) and each lapsed trial are
    # searched: NCT04248439 is now lapsed, so the 677-day row lives in lapsed_history[].
    rckt_snap = contracts.get("RCKT", {})
    all_histories = []
    if rckt_snap.get("history"):
        all_histories.append(rckt_snap["history"])
    all_histories.extend(h for h in rckt_snap.get("lapsed_history", []) if h)

    expired_rows = [
        r
        for h in all_histories
        for r in h.get("revisions", [])
        if r.get("carried_expired")
    ]
    if not expired_rows:
        print(
            "ERROR: no RCKT revision has carried_expired=True in the serialized snapshot.\n"
            "The demo centrepiece is missing. Check that the ctgov cache is fresh.",
            file=sys.stderr,
        )
        sys.exit(1)
    max_expired = max(r["days_expired"] for r in expired_rows)
    if max_expired != 677:
        print(
            f"ERROR: expected max days_expired=677 for RCKT, got {max_expired}.\n"
            "The 677-day expired row is missing or has changed. Inspect the ctgov cache.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("  running Granite redline for RCKT...", flush=True)
    redline_data = _build_rckt_redline(rckt_contract)

    snapshot = {
        "contracts": contracts,
        "redline": redline_data,
        "unresolved": unresolved,
    }
    # Add display strings for the redline breach so the template needs none.
    apply_displays(snapshot)
    return snapshot


def verify_snapshot() -> None:
    if not os.path.exists(SNAPSHOT_PATH):
        print(f"ERROR: {SNAPSHOT_PATH} does not exist. Run make_snapshot.py first.")
        sys.exit(1)
    with open(SNAPSHOT_PATH) as f:
        snap = json.load(f)

    rckt = snap["contracts"].get("RCKT", {})
    gap = rckt.get("gap_months")
    history = rckt.get("history") or {}
    revisions = history.get("revisions", [])
    source = snap.get("redline", {}).get("classification", {}).get("source")

    print(f"RCKT gap_months:       {gap}")
    print(f"revision count:        {len(revisions)}")
    print(f"classification.source: {source}")

    assert source == "granite", f"expected source='granite', got {source!r}"
    print("ok")


def refresh_displays() -> None:
    """Load data/snapshot.json, apply display strings, write it back.

    No credentials needed.  Idempotent: running twice leaves the file
    byte-identical.
    """
    if not os.path.exists(SNAPSHOT_PATH):
        print(f"ERROR: {SNAPSHOT_PATH} does not exist. Run make_snapshot.py first.",
              file=sys.stderr)
        sys.exit(1)
    with open(SNAPSHOT_PATH) as f:
        snap = json.load(f)
    apply_displays(snap)
    with open(SNAPSHOT_PATH, "w") as f:
        json.dump(snap, f, indent=2)
    print(f"Display strings refreshed: {SNAPSHOT_PATH}")


def refresh_unresolved() -> None:
    """Recompute the unresolved block of an existing snapshot and write it back.

    Any ticker in TICKERS with no contract gets a row saying why.  Hits SEC and
    ClinicalTrials.gov, needs no watsonx credentials, and leaves the contracts
    and redline blocks untouched, so it cannot disturb the Granite-sourced
    classification the way a full rebuild would.
    """
    if not os.path.exists(SNAPSHOT_PATH):
        print(f"ERROR: {SNAPSHOT_PATH} does not exist. Run make_snapshot.py first.",
              file=sys.stderr)
        sys.exit(1)
    with open(SNAPSHOT_PATH) as f:
        snap = json.load(f)

    cik_map = ticker_to_cik()
    missing = [t for t in TICKERS if t not in snap.get("contracts", {})]
    snap["unresolved"] = [_unresolved_row(t, cik_map) for t in missing]

    with open(SNAPSHOT_PATH, "w") as f:
        json.dump(snap, f, indent=2)
    for row in snap["unresolved"]:
        print(f"  {row['ticker']}: {row['reason']}")
    print(f"Unresolved block refreshed ({len(missing)} of {len(TICKERS)}): {SNAPSHOT_PATH}")


def refresh_transitions() -> None:
    """Classify revisions in an existing snapshot and write it back.

    Offline: reads only `data/cache/`. Idempotent. Prints where the project's
    own reported slip differs from what promise identity can support, because
    that difference is the finding.
    """
    if not os.path.exists(SNAPSHOT_PATH):
        print(f"ERROR: {SNAPSHOT_PATH} does not exist.", file=sys.stderr)
        sys.exit(1)
    with open(SNAPSHOT_PATH) as f:
        snap = json.load(f)

    apply_transitions(snap)
    apply_displays(snap)

    with open(SNAPSHOT_PATH, "w") as f:
        json.dump(snap, f, indent=2)

    for ticker, c in snap["contracts"].items():
        for h in [c.get("history")] + list(c.get("lapsed_history") or []):
            if not h:
                continue
            rep = h.get("slip_reported_days")
            est = h.get("slip_established_days")
            con = h.get("slip_contingent_days")
            ub = h.get("slip_upper_bound_days")
            ref = h.get("slip_refused_revisions")
            if h.get("slip_fully_established"):
                flag = ""
            elif ref:
                flag = "   <- refused: a count or enumeration changed"
            else:
                flag = "   <- contingent on a human reading two endpoint texts"
            print(f"  {ticker:5} {h['nct']:12} reported {rep!s:>6}  "
                  f"established {est!s:>6}  contingent {con!s:>6}  "
                  f"upper {ub!s:>6}  refused {ref}{flag}")
    print(f"Transitions written: {SNAPSHOT_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or verify data/snapshot.json")
    parser.add_argument("--verify", action="store_true",
                        help="Load and verify an existing snapshot instead of rebuilding")
    parser.add_argument("--displays", action="store_true",
                        help="Refresh display strings in an existing snapshot (no credentials needed)")
    parser.add_argument("--transitions", action="store_true",
                        help="classify every stored revision against promise identity "
                             "using data/cache/ (offline, no credentials)")
    parser.add_argument("--unresolved", action="store_true",
                        help="Recompute the unresolved-ticker block in an existing snapshot "
                             "(network, but no watsonx credentials)")
    args = parser.parse_args()

    if args.verify:
        verify_snapshot()
        return

    if args.displays:
        refresh_displays()
        return

    if args.unresolved:
        refresh_unresolved()
        return

    if args.transitions:
        refresh_transitions()
        return

    print("Building snapshot...")
    snapshot = build_snapshot()

    os.makedirs(os.path.dirname(SNAPSHOT_PATH), exist_ok=True)
    with open(SNAPSHOT_PATH, "w") as f:
        json.dump(snapshot, f, indent=2)
    print(f"Written: {SNAPSHOT_PATH}")
    print(f"  tickers: {list(snapshot['contracts'].keys())}")
    print(f"  redline source: {snapshot['redline']['classification']['source']}")

    # Final assertion: the written file's classification must be 'granite'.
    assert snapshot["redline"]["classification"]["source"] == "granite"
    print("ok")


if __name__ == "__main__":
    main()
