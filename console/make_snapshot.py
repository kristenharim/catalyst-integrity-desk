"""Build data/snapshot.json for the console.

Captures the full engine output for the demo tickers (SANA, PRME, RCKT) plus one
scripted amendment for RCKT so the Flask app never touches a live API during rendering.

Run:
    set -a; . ./.env; set +a
    python3 console/make_snapshot.py

Verify an existing snapshot:
    python3 console/make_snapshot.py --verify
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from copy import deepcopy
from dataclasses import asdict
from datetime import date, timedelta

# Repo root is one level up from this file.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.gap import build, CatalystContract
from engine.ledger import BeliefCard
from engine.runway import ticker_to_cik
from orchestrator.granite import GraniteClassifier
from orchestrator.redline import ContractDelta, run_redline

TICKERS = ["SANA", "PRME", "RCKT"]
SNAPSHOT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "snapshot.json")
SVG_WIDTH = 1100
SVG_PAD = 60  # pixels each side; usable span = SVG_WIDTH - 2*SVG_PAD = 980

# The scripted amendment shifts RCKT's catalyst_date forward by this many months
# so gap_months goes negative and a breach fires.
RCKT_SHIFT_MONTHS = 9


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


def _serialise_runway(r) -> dict:
    """Runway dataclass fields plus all properties the template needs.

    The 'display' sub-dict holds every formatted string the templates render
    so the provenance test can find them verbatim in the snapshot.  Rounding
    happens here, not in the template.
    """
    return {
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
        # Pre-formatted display strings: templates use these verbatim so every
        # number in the HTML is a substring of the snapshot JSON.
        "display": {
            "cash_m": _fmt_m(r.cash),
            "securities_m": _fmt_m(r.securities),
            "liquidity_m": _fmt_m(r.liquidity),
            "burn_ttm_annual_m": _fmt_m(r.burn_ttm_annual),
            "burn_recent_annual_m": _fmt_m(r.burn_recent_annual),
            "months_low_1f": _fmt_1f(r.months_low),
            "months_high_1f": _fmt_1f(r.months_high),
        },
    }


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
    return {
        "runway": _serialise_runway(c.runway),
        "trial": c.trial,
        "history": _serialise_history(c.history),
        "gap_months": c.gap_months,
        # Pre-formatted gap string: "+8.4" or "-0.6" — stored so the template
        # outputs it verbatim and the provenance test finds it in the snapshot.
        "gap_months_1f": _fmt_1f(c.gap_months),
        "catalyst_date": _iso(c.catalyst_date),
        "verdict": c.verdict,
    }


# ---------------------------------------------------------------------------
# Scripted amendment for RCKT
# ---------------------------------------------------------------------------

_GRANITE_MAX_ATTEMPTS = 5
_GRANITE_BACKOFF_START = 30  # seconds; doubles each attempt


def _classify_once(delta, card) -> "ChallengeCard | None":  # type: ignore[name-defined]
    """One attempt at Granite classification via run_redline.

    Returns None if the engine detected no breach — that is a broken premise,
    not a case to work around.  Returns the ChallengeCard otherwise; caller
    checks source.  A fresh GraniteClassifier is constructed each time so any
    cached token state from a failed attempt does not carry over.
    """
    classifier = GraniteClassifier()
    return run_redline(delta, card, classifier=classifier)


def _build_rckt_redline(rckt: CatalystContract) -> dict:
    """Construct a scripted +9-month shift on RCKT's catalyst_date and run the
    redline loop with up to five attempts.  Exits non-zero if all fail."""
    # Build the recomputed contract: same runway, same trial but with pcd shifted
    # forward by RCKT_SHIFT_MONTHS months (approx 30.44 days/month).
    original_pcd_str = rckt.trial["pcd"]
    try:
        original_date = date.fromisoformat(original_pcd_str)
    except ValueError:
        # Month-only format like "2026-05": pad to first of month.
        original_date = date.fromisoformat(original_pcd_str + "-01")

    shift_days = int(RCKT_SHIFT_MONTHS * 30.4375)
    new_date = original_date + timedelta(days=shift_days)
    new_pcd_str = new_date.isoformat()

    new_trial = deepcopy(rckt.trial)
    new_trial["pcd"] = new_pcd_str

    recomputed = CatalystContract(
        runway=rckt.runway,
        trial=new_trial,
        history=rckt.history,
    )

    delta = ContractDelta(approved=rckt, recomputed=recomputed)

    # BeliefCard: approved range requires gap_months >= 0 (funded to catalyst).
    # expected_low=0 ensures the +9-month shift into negative territory triggers a breach.
    original_gap = rckt.gap_months or 0.0
    card = BeliefCard(
        card_id="rckt:funded_to_catalyst",
        scope="company:RCKT",
        claim=(
            "Rocket Pharmaceuticals reaches its registered primary completion date "
            "before runway exhaustion, with a non-negative funding gap."
        ),
        metric="gap_months",
        expected_low=0.0,
        expected_high=max(original_gap + 2.0, 2.0),
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
            # run_redline found no breach: the scripted amendment did not break the
            # contract.  The demo premise is wrong — nothing to judge, nothing to ship.
            print(
                f"ERROR: scripted +{RCKT_SHIFT_MONTHS}-month RCKT amendment did not produce "
                f"a breach (recomputed gap_months={delta.recomputed.gap_months:.2f}, "
                f"approved band=[{card.expected_low:.1f}, {card.expected_high:.1f}]).\n"
                f"The demo premise is broken. Check the amendment parameters.",
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
        "original_pcd": original_pcd_str,
        "shifted_pcd": new_pcd_str,
        "shift_months": RCKT_SHIFT_MONTHS,
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

    for ticker in TICKERS:
        print(f"  building {ticker}...", flush=True)
        c = build(ticker, cik_map)
        if c is None:
            print(f"  {ticker}: no live pivotal trial found, skipping", file=sys.stderr)
            continue
        contracts[ticker] = _serialise_contract(c)
        if ticker == "RCKT":
            rckt_contract = c

    if rckt_contract is None:
        print("ERROR: RCKT contract not built — cannot produce redline.", file=sys.stderr)
        sys.exit(1)

    # The 677-day expired-date row is the demo centrepiece.  Assert it is present in the
    # serialized snapshot before writing anything.  If this fires, the snapshot has no
    # centrepiece and must not be written — better to fail here than to ship a silent gap.
    rckt_revisions = contracts["RCKT"]["history"]["revisions"] if (
        contracts.get("RCKT") and contracts["RCKT"].get("history")
    ) else []
    expired_rows = [r for r in rckt_revisions if r.get("carried_expired")]
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
    }
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or verify data/snapshot.json")
    parser.add_argument("--verify", action="store_true",
                        help="Load and verify an existing snapshot instead of rebuilding")
    args = parser.parse_args()

    if args.verify:
        verify_snapshot()
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
