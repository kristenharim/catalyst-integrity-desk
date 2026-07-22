"""Monitoring queue: which beliefs need an analyst's attention today?

Joins runway bands to the full PCD revision histories of live pivotal trials
for the twelve clinical-stage names in the engine's demo list, and asks: given
what the engine knows right now, which companies have an active breach, a
lapsed registered completion, or a history of carrying expired dates?

Output:
  research/panel.csv  -- one row per PCD revision, tidy format
  research/figures/revision_timeline.png   -- descriptive figure

This is a sample of twelve companies, not a sector study. No regression is
run, no causal relationship is claimed, and nothing here should be described
as if cash runway predicts revision behaviour.  The question is open:
docs/FINDINGS.md section 2 says exactly why.

Finding 1.7 reversal filter: a +X then -X pair within two months of each other
is almost certainly a data-entry correction, not a forecast change.  Reversals
are included in the CSV with is_reversal=True and are excluded from the figure.
"""
from __future__ import annotations

import csv
import os
import sys
from dataclasses import dataclass
from datetime import date, timedelta

import matplotlib
matplotlib.use("Agg")    # no display required; must come before pyplot import
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Ensure the repo root is importable when this file is run as a script.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.ctgov_history import Revision, TrialHistory, fetch_history
from engine.gap import CatalystContract, build, find_trials, _parse_date
from engine.runway import compute_runway, ticker_to_cik

# The twelve clinical-stage, pre-revenue names from engine/runway.py's demo list.
TICKERS = ["BEAM", "NTLA", "SANA", "RCKT", "DYN", "KYMR", "NUVL", "PRME",
           "ARVN", "EDIT", "CRSP", "VOR"]

_HERE = os.path.dirname(__file__)
FIGURES_DIR = os.path.join(_HERE, "figures")
CSV_PATH = os.path.join(_HERE, "panel.csv")

CSV_COLUMNS = [
    "ticker",
    "company",
    "runway_as_of",
    "cash_m",           # total liquidity in $M
    "runway_low_mo",    # conservative end of burn band
    "runway_high_mo",   # optimistic end of burn band
    "runway_reliable",  # True if this row may be ranked
    "nct",
    "trial_status",
    "is_binding_catalyst",  # True for the trial used as the catalyst
    "is_lapsed",            # True for pivotal trials whose PCD is in the past
    "revision_version",
    "submitted",        # date sponsor filed this version
    "pcd",              # primary completion date as of this version
    "pcd_type",
    "moved_days",       # PCD change vs previous version (None for first revision)
    "held_days",        # days remaining on old PCD when it was replaced (negative = expired)
    "carried_expired",  # True when the old PCD had already passed
    "days_expired",     # magnitude of expiry (0 unless carried_expired)
    "is_late_move",     # moved with < 90 days left (but not yet expired)
    "is_reversal",      # +X then -X within 60 days -- likely a data-entry correction
    "gap_months",       # funding gap for the binding catalyst (None for non-binding trials)
    "verdict",          # funded to catalyst / financing required / not rankable / ...
]


# ---------------------------------------------------------------------------
# Reversal detection (finding 1.7)
# ---------------------------------------------------------------------------

def _mark_reversals(revisions: list[Revision]) -> list[bool]:
    """Mark revisions that are a near-exact reversal of the immediately prior move.

    A +1317 day move followed by a -1317 day move two months later is a data-entry
    correction (confirmed empirically on NCT04613596, versions 92 and 94).  Any move
    where abs(moved) == abs(prev_moved) and the two submissions are within 60 days of
    each other is tagged as a reversal.  Both the forward and the correcting entry are
    tagged, because neither is a genuine forecast change.
    """
    flags = [False] * len(revisions)
    for i in range(1, len(revisions)):
        r, prev = revisions[i], revisions[i - 1]
        if (r.moved_days is not None and prev.moved_days is not None
                and r.moved_days != 0
                and r.moved_days == -prev.moved_days):
            sub_r = _parse_date(r.submitted)
            sub_prev = _parse_date(prev.submitted)
            if sub_r and sub_prev and abs((sub_r - sub_prev).days) <= 60:
                flags[i] = True
                flags[i - 1] = True
    return flags


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

@dataclass
class _Row:
    """One CSV row."""
    ticker: str
    company: str
    runway_as_of: str
    cash_m: float
    runway_low_mo: float | None
    runway_high_mo: float | None
    runway_reliable: bool
    nct: str
    trial_status: str
    is_binding_catalyst: bool
    is_lapsed: bool
    revision_version: int
    submitted: str
    pcd: str
    pcd_type: str
    moved_days: int | None
    held_days: int | None
    carried_expired: bool
    days_expired: int
    is_late_move: bool
    is_reversal: bool
    gap_months: float | None
    verdict: str


def _rows_for_contract(contract: CatalystContract) -> list[_Row]:
    """Expand a CatalystContract to one _Row per PCD revision across all trials."""
    r = contract.runway
    rows: list[_Row] = []

    def _add_trial(trial: dict, history: TrialHistory | None,
                   is_binding: bool, is_lapsed: bool) -> None:
        if history is None:
            return
        reversal_flags = _mark_reversals(history.revisions)
        for rev, is_rev in zip(history.revisions, reversal_flags):
            rows.append(_Row(
                ticker=r.ticker,
                company=r.name,
                runway_as_of=r.as_of,
                cash_m=round(r.liquidity / 1e6, 1),
                runway_low_mo=round(r.months_low, 2) if r.months_low is not None else None,
                runway_high_mo=round(r.months_high, 2) if r.months_high is not None else None,
                runway_reliable=r.reliable,
                nct=trial["nct"],
                trial_status=trial["status"],
                is_binding_catalyst=is_binding,
                is_lapsed=is_lapsed,
                revision_version=rev.version,
                submitted=rev.submitted,
                pcd=rev.pcd,
                pcd_type=rev.pcd_type,
                moved_days=rev.moved_days,
                held_days=rev.held_days,
                carried_expired=rev.carried_expired,
                days_expired=rev.days_expired,
                is_late_move=rev.is_late_move,
                is_reversal=is_rev,
                gap_months=round(contract.gap_months, 2)
                    if is_binding and contract.gap_months is not None else None,
                verdict=contract.verdict if is_binding else "",
            ))

    _add_trial(contract.trial, contract.history, is_binding=True, is_lapsed=False)
    for trial, hist in zip(contract.lapsed, contract.lapsed_history):
        _add_trial(trial, hist, is_binding=False, is_lapsed=True)

    return rows


def build_panel(tickers: list[str] | None = None) -> list[_Row]:
    tickers = tickers or TICKERS
    cik_map = ticker_to_cik()
    rows: list[_Row] = []

    for ticker in tickers:
        print(f"  {ticker}...", end=" ", flush=True)
        try:
            contract = build(ticker, cik_map)
        except Exception as exc:
            print(f"skipped ({exc})")
            continue

        if contract is None:
            print("no live pivotal trial")
            continue

        r = _rows_for_contract(contract)
        print(f"{len(r)} revision(s) across "
              f"{1 + len(contract.lapsed)} trial(s)")
        rows.extend(r)

    return rows


def write_csv(rows: list[_Row], path: str = CSV_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for row in rows:
            w.writerow({
                "ticker": row.ticker,
                "company": row.company,
                "runway_as_of": row.runway_as_of,
                "cash_m": row.cash_m,
                "runway_low_mo": row.runway_low_mo,
                "runway_high_mo": row.runway_high_mo,
                "runway_reliable": row.runway_reliable,
                "nct": row.nct,
                "trial_status": row.trial_status,
                "is_binding_catalyst": row.is_binding_catalyst,
                "is_lapsed": row.is_lapsed,
                "revision_version": row.revision_version,
                "submitted": row.submitted,
                "pcd": row.pcd,
                "pcd_type": row.pcd_type,
                "moved_days": row.moved_days if row.moved_days is not None else "",
                "held_days": row.held_days if row.held_days is not None else "",
                "carried_expired": row.carried_expired,
                "days_expired": row.days_expired,
                "is_late_move": row.is_late_move,
                "is_reversal": row.is_reversal,
                "gap_months": row.gap_months if row.gap_months is not None else "",
                "verdict": row.verdict,
            })


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------

def make_figure(rows: list[_Row], path: str | None = None) -> None:
    """Per-trial timeline of registered completion revisions, carried-expired marked.

    Runway is deliberately on neither axis. An earlier version plotted runway against
    move magnitude, which is visually the causal chart for the one hypothesis this
    project refuses to claim: that cash-constrained sponsors handle dates differently.
    With 23 revisions across 7 companies, and two of the three carried-expired points
    belonging to the same sponsor, that reading is unsupported by this sample, and a
    chart that invites it while the caption disclaims it is having the argument both
    ways. See docs/FINDINGS.md section 2.

    What this shows instead is what the monitor actually observes: when each sponsor
    revised a registered completion date, and which of those revisions carried a date
    that had already passed.
    """
    if path is None:
        os.makedirs(FIGURES_DIR, exist_ok=True)
        path = os.path.join(FIGURES_DIR, "revision_timeline.png")

    plot_rows = [r for r in rows if r.submitted and not r.is_reversal]
    if not plot_rows:
        print("  no plottable rows; figure skipped")
        return

    def _d(value):
        return date.fromisoformat(value)

    # One lane per trial, ordered so the trials carrying expired dates sit on top.
    trials: dict[tuple, list[_Row]] = {}
    for r in plot_rows:
        trials.setdefault((r.ticker, r.nct), []).append(r)
    order = sorted(
        trials,
        key=lambda k: (max((x.days_expired or 0) for x in trials[k]), len(trials[k])),
    )

    fig, ax = plt.subplots(figsize=(11, 0.52 * len(order) + 3.2), facecolor="#0d1117")
    ax.set_facecolor("#0d1117")
    labelled = set()   # legend entries are attached on first use, not on a fixed lane

    for lane, key in enumerate(order):
        revs = sorted(trials[key], key=lambda x: x.submitted)
        xs = [_d(x.submitted) for x in revs]
        ax.plot(xs, [lane] * len(xs), color="#30363d", linewidth=1, zorder=1)
        ordinary = [x for x in revs if not x.carried_expired]
        expired = [x for x in revs if x.carried_expired]
        if ordinary:
            ax.scatter([_d(x.submitted) for x in ordinary], [lane] * len(ordinary),
                       s=46, color="#4ade80", marker="o", zorder=3,
                       label=None if "rev" in labelled else "revision")
            labelled.add("rev")
        for x in expired:
            ax.scatter([_d(x.submitted)], [lane], s=132, color="#f85149", marker="s",
                       zorder=4,
                       label=None if "exp" in labelled else "carried an already-passed date")
            labelled.add("exp")
            ax.annotate(f"{x.days_expired}d expired", xy=(_d(x.submitted), lane),
                        xytext=(9, 5), textcoords="offset points",
                        fontsize=8, color="#f85149", fontweight="bold")

    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([f"{t}  {n}" for t, n in order], color="#c9d1d9", fontsize=8.5)
    ax.set_ylim(-0.6, len(order) - 0.4)
    ax.set_xlabel("Date the revision was submitted to the registry",
                  color="#c9d1d9", fontsize=11)
    ax.tick_params(colors="#8b949e")
    for spine in ax.spines.values():
        spine.set_edgecolor("#30363d")
    ax.grid(axis="x", color="#21262d", linewidth=0.6, zorder=0)
    # Right margin so the "Nd expired" annotations are not clipped at the edge.
    x0, x1 = ax.get_xlim()
    ax.set_xlim(x0, x1 + (x1 - x0) * 0.13)

    n_companies = len({r.ticker for r in plot_rows})
    n_trials = len(order)
    n_expired = sum(1 for r in plot_rows if r.carried_expired)
    n_expired_sponsors = len({r.ticker for r in plot_rows if r.carried_expired})

    ax.set_title(
        "When sponsors revised a registered primary completion date\n"
        f"{n_companies} companies that resolved, of {len(TICKERS)} attempted. "
        "Not the sector.",
        color="#c9d1d9", fontsize=13, pad=12,
    )
    legend = ax.legend(facecolor="#161b22", edgecolor="#30363d",
                       labelcolor="#c9d1d9", fontsize=9, loc="lower left")
    legend.set_zorder(6)

    caption = (
        f"Sample: {n_companies} clinical-stage companies, {n_trials} pivotal trials, "
        f"{len(plot_rows)} registry revisions. "
        f"{n_expired} revision(s) across {n_expired_sponsors} sponsor(s) carried a completion "
        f"date that had already passed. "
        "Runway is on neither axis on purpose: whether cash position relates to this "
        "behaviour is an open question this sample cannot answer. Descriptive only."
    )
    fig.text(0.5, -0.02, caption, ha="center", va="top", fontsize=7.5,
             color="#8b949e", wrap=True, transform=fig.transFigure)

    fig.tight_layout()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  figure: {path}")


# ---------------------------------------------------------------------------
# Queue display
# ---------------------------------------------------------------------------

def _queue_key(contract: CatalystContract) -> tuple:
    """Sort key: active breach first, then lapsed-date severity, then gap ascending."""
    gap = contract.gap_months
    has_breach = gap is not None and gap < 0
    max_expired = max(
        (h.max_days_expired for h in contract.lapsed_history if h), default=0
    )
    # Binding history expired too
    if contract.history:
        max_expired = max(max_expired, contract.history.max_days_expired)
    # (breach, max_expired desc, gap asc)
    return (not has_breach, -max_expired, gap if gap is not None else float("inf"))


def print_queue(contracts: dict[str, CatalystContract]) -> None:
    ranked = sorted(contracts.items(), key=lambda kv: _queue_key(kv[1]))
    print(f"\n{'='*70}")
    print(f"MONITORING QUEUE  ({len(ranked)} contract(s))")
    print(f"{'='*70}")
    for ticker, c in ranked:
        gap = c.gap_months
        breach = gap is not None and gap < 0
        flag = "BREACH" if breach else ("UNRELIABLE" if not c.runway.reliable else "ok")
        lapsed_note = f"  lapsed: {len(c.lapsed)}" if c.lapsed else ""
        expired_note = ""
        all_hist = ([c.history] if c.history else []) + list(c.lapsed_history)
        max_exp = max((h.max_days_expired for h in all_hist if h), default=0)
        if max_exp:
            expired_note = f"  max_expired: {max_exp}d"
        gap_str = f"{gap:+.1f} mo" if gap is not None else "n/a"
        print(f"  [{flag:10}] {ticker:6} gap {gap_str:>9} "
              f"runway {c.runway.months_low or 0:.1f}-{c.runway.months_high or 0:.1f} mo"
              f"{lapsed_note}{expired_note}")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("Building panel...")
    contracts: dict[str, CatalystContract] = {}
    cik_map = ticker_to_cik()
    for ticker in TICKERS:
        print(f"  {ticker}...", end=" ", flush=True)
        try:
            c = build(ticker, cik_map)
        except Exception as exc:
            print(f"skipped ({exc})")
            continue
        if c is None:
            print("no live pivotal trial")
        else:
            contracts[ticker] = c
            gap_str = f"{c.gap_months:+.1f} mo" if c.gap_months is not None else "n/a"
            print(gap_str)

    print_queue(contracts)

    print("Expanding to revision rows...")
    rows: list[_Row] = []
    for ticker, c in contracts.items():
        rows.extend(_rows_for_contract(c))

    n_companies = len({r.ticker for r in rows})
    n_trials = len({r.nct for r in rows})
    n_revisions = len(rows)
    n_reversals = sum(1 for r in rows if r.is_reversal)
    n_expired = sum(1 for r in rows if r.carried_expired)
    print(f"  {n_companies} companies, {n_trials} trial(s), "
          f"{n_revisions} revision(s) "
          f"({n_reversals} reversal(s), {n_expired} carried-expired)")

    write_csv(rows)
    print(f"  CSV: {CSV_PATH}")

    print("Making figure...")
    make_figure(rows)


if __name__ == "__main__":
    main()
