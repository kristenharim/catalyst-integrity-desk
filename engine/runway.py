"""Cash runway from SEC XBRL company facts. Deterministic, from filed tags only.

No model computes any number here. Every figure traces to a us-gaap tag in a specific
filing, and `Runway.provenance` names which tag each component came from, because the
tags are not uniform across filers and a runway number whose numerator you cannot
identify is not auditable.

The numerator is the hard part, and it is the opposite of what you would guess. Burn
(`NetCashProvidedByUsedInOperatingActivities`) is tagged by ~99% of clinical-stage
filers. Liquid securities are not: there is no single tag, and roughly half of filers
use none of them because they hold only cash. The ones that DO hold securities are the
well-capitalized companies whose runway matters most, so the tag waterfall below is
load-bearing rather than defensive. `CashCashEquivalentsAndShortTermInvestments` looks
like the right tag and is never filed -- do not reach for it.

Burn is reported as a BAND, not a point. A company that just dosed first patient in a
pivotal trial will burn well above its trailing rate; one that just booked a partnership
upfront shows a positive operating quarter. A single point estimate implies a precision
the filings do not support, and a ranked screen whose order flips under a 25% burn
perturbation is not a screen. Rank on the interval.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import date, datetime

SEC = "https://data.sec.gov"
# SEC's access policy requires a real contact string in the User-Agent.
UA = os.environ.get("SEC_UA", "catalyst-integrity-desk kris10harim@gmail.com")
CACHE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cache")
SLEEP = 0.12  # SEC allows 10 req/s

# Tried in order; first hit wins, and the winner is recorded in provenance.
CASH_TAGS = [
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
]
# Summed, not first-wins: a filer can report several distinct securities buckets.
SECURITIES_TAGS = [
    "ShortTermInvestments",
    "MarketableSecuritiesCurrent",
    "AvailableForSaleSecuritiesDebtSecuritiesCurrent",
]
# Counted toward runway only when opted in. Companies include >12mo maturities in
# their own runway guidance, but calling it "liquidity" without saying so is a stretch.
LONG_TERM_TAGS = ["LongTermInvestments", "MarketableSecuritiesNoncurrent"]

BURN_TAG = "NetCashProvidedByUsedInOperatingActivities"
# Fallback for the ~1% that omit the cash-flow tag: opex is an upper bound on cash burn
# (it includes non-cash stock comp), so a runway built on it is conservative.
BURN_FALLBACK_TAGS = ["OperatingExpenses", "ResearchAndDevelopmentExpense"]

DAYS_PER_MONTH = 365.25 / 12


def _curl_json(url: str, retries: int = 3) -> dict:
    """SEC's edge blocks some non-browser clients; curl with a contact UA is accepted.
    Same shell-out rationale as the registry crawler."""
    for attempt in range(retries):
        p = subprocess.run(
            ["curl", "-sS", "--fail", "--compressed", "--max-time", "60",
             "-H", f"User-Agent: {UA}", url],
            capture_output=True, text=True,
        )
        if p.returncode == 0:
            try:
                return json.loads(p.stdout)
            except json.JSONDecodeError:
                pass
        if attempt == retries - 1:
            raise RuntimeError(f"GET {url} failed: {p.stderr.strip() or p.returncode}")
        time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def _cached(name: str, url: str) -> dict:
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    time.sleep(SLEEP)
    d = _curl_json(url)
    with open(path, "w") as f:
        json.dump(d, f)
    return d


def ticker_to_cik() -> dict[str, str]:
    """SEC's own ticker map. CIKs are zero-padded to 10 digits in the API paths."""
    d = _cached("company_tickers.json", "https://www.sec.gov/files/company_tickers.json")
    return {v["ticker"].upper(): f"{int(v['cik_str']):010d}" for v in d.values()}


def company_facts(cik: str) -> dict:
    return _cached(f"facts-{cik}.json", f"{SEC}/api/xbrl/companyfacts/CIK{cik}.json")


def _d(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _usd(facts: dict, tag: str) -> list[dict]:
    return facts.get("facts", {}).get("us-gaap", {}).get(tag, {}).get("units", {}).get("USD", [])


def _latest_instant(facts: dict, tag: str) -> tuple[float, str] | None:
    """Most recent point-in-time value (balance-sheet items have no `start`)."""
    pts = [f for f in _usd(facts, tag) if "start" not in f and f.get("end")]
    if not pts:
        return None
    best = max(pts, key=lambda f: (f["end"], f.get("fy") or 0))
    return float(best["val"]), best["end"]


def _quarterly_flows(facts: dict, tag: str) -> list[dict]:
    """True quarterly values, newest first, recovered by differencing the YTD series.

    Cash-flow statements are cumulative within a fiscal year. A 10-Q reports
    year-to-date, so the only fact that is natively ~90 days long is Q1; Q2 arrives as
    a 6-month figure, Q3 as 9-month, Q4 inside the 10-K as 12-month. Filtering on a
    60-120 day span therefore does NOT return the last four quarters -- it returns Q1
    of four consecutive years, and summing those produces a plausible-looking annual
    burn that is not the trailing twelve months of anything.

    Facts within one fiscal year share a `start`, so grouping on `start` recovers the
    cumulative progression, and consecutive differences recover the quarters:

        Q1 = YTD(3mo)                Q3 = YTD(9mo) - YTD(6mo)
        Q2 = YTD(6mo) - YTD(3mo)     Q4 = FY(12mo) - YTD(9mo)
    """
    by_start: dict[str, dict[str, float]] = {}
    for f in _usd(facts, tag):
        if not (f.get("start") and f.get("end")):
            continue
        # Later filings restate; keep the most recently reported value for each period.
        by_start.setdefault(f["start"], {})[f["end"]] = float(f["val"])

    quarters: list[dict] = []
    for start, ends in by_start.items():
        prev_end, prev_val = start, 0.0
        for end in sorted(ends):
            span = (_d(end) - _d(prev_end)).days
            if 60 <= span <= 120:      # one quarter's worth of elapsed time
                quarters.append({"start": prev_end, "end": end,
                                 "val": ends[end] - prev_val})
            prev_end, prev_val = end, ends[end]

    seen, uniq = set(), []
    for q in sorted(quarters, key=lambda q: q["end"], reverse=True):
        if q["end"] not in seen:
            seen.add(q["end"])
            uniq.append(q)
    return uniq


@dataclass
class Runway:
    ticker: str
    cik: str
    name: str
    as_of: str
    cash: float
    securities: float
    burn_ttm_annual: float        # trailing four quarters, annualized
    burn_recent_annual: float     # most recent quarter, annualized
    provenance: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    inflow_quarters: list[str] = field(default_factory=list)

    @property
    def liquidity(self) -> float:
        return self.cash + self.securities

    def _months(self, annual_burn: float) -> float | None:
        if annual_burn <= 0:
            return None  # cash-flow positive over this window; runway is not the binding question
        return self.liquidity / (annual_burn / 12)

    @property
    def months_low(self) -> float | None:
        """Shorter runway of the two burn estimates -- the conservative end."""
        got = [m for m in (self._months(self.burn_ttm_annual),
                           self._months(self.burn_recent_annual)) if m is not None]
        return min(got) if got else None

    @property
    def months_high(self) -> float | None:
        got = [m for m in (self._months(self.burn_ttm_annual),
                           self._months(self.burn_recent_annual)) if m is not None]
        return max(got) if got else None

    @property
    def burn_unstable(self) -> bool:
        """True when the two burn estimates disagree by more than 3x.

        This is the honest answer to "your burn number is wrong for exactly the
        companies that matter". A collaboration upfront, a milestone, or a Phase 3
        ramp makes one quarter unrepresentative, and the disagreement between the
        trailing-year and most-recent-quarter estimates is the cheapest available
        detector. A row flagged here must not be ranked on its point estimate.
        """
        lo, hi = self.months_low, self.months_high
        return lo is not None and hi is not None and lo > 0 and hi / lo > 3

    @property
    def reliable(self) -> bool:
        """Whether this row may be RANKED, as opposed to merely reported.

        Cash divided by burn is only a runway when the denominator is an operating
        burn. A partnership upfront or milestone inside the trailing year makes it
        something else: Arrowhead's 2025 Sarepta payment nets its trailing burn to
        near zero and produces a 1,100-month runway, which is arithmetically correct
        and financially meaningless. Those rows stay visible with the reason attached,
        because a screen that silently drops its hard cases is worse than one that
        shows them -- but they never carry a rank.
        """
        return (self.months_low is not None
                and not self.inflow_quarters
                and not self.burn_unstable)

    def exhaustion(self, months: float | None) -> date | None:
        if months is None:
            return None
        return _d(self.as_of) + __import__("datetime").timedelta(days=months * DAYS_PER_MONTH)

    def __str__(self) -> str:
        if self.months_low is None:
            return f"{self.ticker:6} {self.name[:28]:28} cash-flow positive over both windows"
        flag = "  UNSTABLE BURN" if self.burn_unstable else ""
        return (f"{self.ticker:6} {self.name[:28]:28} "
                f"${self.liquidity/1e6:8,.0f}M  "
                f"runway {self.months_low:5.1f}-{self.months_high:5.1f} mo  "
                f"(to {self.exhaustion(self.months_low)}){flag}")


def compute_runway(ticker: str, cik_map: dict[str, str] | None = None,
                   include_long_term: bool = False) -> Runway:
    cik_map = cik_map or ticker_to_cik()
    ticker = ticker.upper()
    if ticker not in cik_map:
        raise KeyError(f"{ticker} not in SEC ticker map")
    cik = cik_map[ticker]
    facts = company_facts(cik)

    prov, notes = {}, []

    # Pick the cash tag with the MOST RECENT balance date, not the first one that
    # exists. Filers migrate between tags: Arrowhead stopped filing
    # CashAndCashEquivalentsAtCarryingValue in 2024 and moved to the restricted-cash-
    # inclusive tag, so a first-wins waterfall silently returned a two-year-old $69M
    # balance instead of the current $1.8B, and dated the whole record to 2024. A
    # stale numerator does not look wrong -- it looks like a company about to die,
    # which is precisely the row a screen like this puts on screen first.
    candidates = [(tag, hit) for tag in CASH_TAGS if (hit := _latest_instant(facts, tag))]
    cash, as_of = 0.0, ""
    if candidates:
        tag, (cash, as_of) = max(candidates, key=lambda c: c[1][1])
        prov["cash"] = tag
        # This tag bundles restricted cash, which cannot fund operations. Net it out
        # when the filer reports it separately on the same date.
        if "RestrictedCash" in tag:
            r = _latest_instant(facts, "RestrictedCashAndCashEquivalentsAtCarryingValue")
            if r and r[1] == as_of:
                cash -= r[0]
                prov["cash"] += " less RestrictedCashAndCashEquivalentsAtCarryingValue"
    else:
        notes.append("no cash tag found")

    securities, sec_tags = 0.0, []
    for tag in SECURITIES_TAGS + (LONG_TERM_TAGS if include_long_term else []):
        hit = _latest_instant(facts, tag)
        # Only count a securities balance struck on the same date as the cash balance,
        # or the numerator mixes two different quarters.
        if hit and hit[1] == as_of:
            securities += hit[0]
            sec_tags.append(tag)
    prov["securities"] = "+".join(sec_tags) if sec_tags else "none"
    if not sec_tags:
        notes.append("no securities tag on the cash date (cash-only, or fragmented tagging)")

    flows = _quarterly_flows(facts, BURN_TAG)
    prov["burn"] = BURN_TAG
    if not flows:
        for tag in BURN_FALLBACK_TAGS:
            flows = [{**f, "val": -abs(float(f["val"]))} for f in _quarterly_flows(facts, tag)]
            if flows:
                prov["burn"] = f"{tag} (fallback, upper bound on cash burn)"
                notes.append("cash-flow tag absent; burn approximated from expense tag")
                break
    if not flows:
        raise ValueError(f"{ticker}: no usable burn tag")

    ttm = flows[:4]
    # Operating cash flow is negative for a company that burns. Flip the sign so a
    # positive burn number means money going out, which is what the ratio expects.
    burn_ttm_annual = -sum(float(f["val"]) for f in ttm) * (4 / len(ttm))
    burn_recent_annual = -float(flows[0]["val"]) * 4
    if len(ttm) < 4:
        notes.append(f"only {len(ttm)} quarters available; TTM scaled up")
    inflow_quarters = [f["end"] for f in ttm if float(f["val"]) > 0]
    if inflow_quarters:
        # A cash-positive quarter inside the trailing year is almost always a
        # partnership upfront or milestone, not a change in operating economics.
        # It deflates the burn estimate and inflates runway; say so on the row.
        notes.append(f"cash-positive operating quarter(s) in TTM window: "
                     f"{', '.join(inflow_quarters)} - likely a one-time inflow")

    return Runway(
        ticker=ticker, cik=cik, name=facts.get("entityName", ""),
        as_of=as_of or flows[0]["end"], cash=cash, securities=securities,
        burn_ttm_annual=burn_ttm_annual, burn_recent_annual=burn_recent_annual,
        provenance=prov, notes=notes, inflow_quarters=inflow_quarters,
    )


def demo() -> None:
    """Self-check on real filers. Values are not hardcoded -- the assertions check
    internal consistency and sane magnitudes, so this keeps passing as filings roll."""
    cik_map = ticker_to_cik()
    assert len(cik_map) > 5000, len(cik_map)
    assert "MRNA" in cik_map

    # company_tickers.json lags: it is missing live filers (Amicus/FOLD is absent from
    # all 10,426 entries). Fine for a demo list, wrong as a universe source -- the
    # universe comes from DERA sub.txt by SIC code, keyed on CIK, with no ticker.
    # Clinical-stage and pre-revenue on purpose. Commercial names (MRNA, SRPT, IONS,
    # ALNY, ARWR) get flagged constantly because product revenue and partnership
    # upfronts land in operating cash flow, which is correct behaviour and also the
    # wrong population: for a company with no product, operating cash flow IS burn.
    tickers = ["BEAM", "NTLA", "SANA", "RCKT", "DYN", "KYMR", "NUVL", "PRME",
               "ARVN", "EDIT", "CRSP", "VOR"]
    rows = []
    for t in tickers:
        try:
            rows.append(compute_runway(t, cik_map))
        except (KeyError, ValueError) as e:
            print(f"  {t}: skipped ({e})")

    assert rows, "no company resolved"
    for r in rows:
        assert r.cash >= 0 and r.securities >= 0
        assert r.liquidity >= r.cash
        if r.months_low is not None:
            assert r.months_low <= r.months_high
        assert r.provenance.get("cash"), r.ticker
    # Only rankable rows must be sane. Unreliable ones are allowed to be absurd --
    # that is what makes them unreliable, and the flag is the point.
    for r in [r for r in rows if r.reliable]:
        assert 0 < r.months_low < 600, (r.ticker, r.months_low)

    rankable = [r for r in rows if r.reliable]
    flagged = [r for r in rows if not r.reliable]
    assert rankable, "every row was flagged; the guards are too aggressive"

    print(f"RANKED  ({len(rankable)} of {len(rows)} rows carry a rank)")
    for r in sorted(rankable, key=lambda r: r.months_low):
        print(f"  {r}")
    if flagged:
        print(f"\nREPORTED, NOT RANKED  ({len(flagged)})")
        for r in flagged:
            print(f"  {r}")
            for n in r.notes:
                print(f"         {n}")
    print()
    for r in rows:
        print(f"  {r.ticker:6} as_of {r.as_of}  cash={r.provenance['cash']}  "
              f"sec={r.provenance['securities']}")
        for n in r.notes:
            print(f"         note: {n}")
    print("\nok")


if __name__ == "__main__":
    demo()
