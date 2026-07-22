"""Monitoring queue: which beliefs need an analyst's attention today?

Joins runway bands to the full PCD revision histories of live pivotal trials
for the twelve clinical-stage names in the engine's demo list, and asks: given
what the engine knows right now, which companies have an active breach, a
lapsed registered completion, or a history of carrying expired dates?

Output:
  research/panel.csv  -- one row per PCD revision, tidy format
  research/figures/revision_vs_runway.png  -- descriptive figure

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
    """Scatter: runway at filing vs PCD move magnitude. Carried-expired marked.

    X axis: runway band (months_low) at the snapshot date -- context, not ranking.
    Y axis: moved_days for genuine revisions (reversals excluded).
    Each point is one PCD-moving revision.  Carried-expired revisions are marked
    with a distinct colour and shape so they are visible at video resolution.

    Caption states the sample size explicitly.
    """
    if path is None:
        os.makedirs(FIGURES_DIR, exist_ok=True)
        path = os.path.join(FIGURES_DIR, "revision_vs_runway.png")

    # Only genuine revisions after the first (first has no moved_days) and no reversals.
    plot_rows = [
        r for r in rows
        if r.moved_days is not None and not r.is_reversal and r.runway_low_mo is not None
    ]

    if not plot_rows:
        print("  no plottable rows; figure skipped")
        return

    expired = [r for r in plot_rows if r.carried_expired]
    ordinary = [r for r in plot_rows if not r.carried_expired]

    fig, ax = plt.subplots(figsize=(10, 6), facecolor="#0d1117")
    ax.set_facecolor("#0d1117")

    # Ordinary revisions -- muted teal
    if ordinary:
        ax.scatter(
            [r.runway_low_mo for r in ordinary],
            [r.moved_days for r in ordinary],
            s=55, alpha=0.7, color="#4ade80", marker="o",
            label="PCD revision (ordinary)",
            zorder=3,
        )

    # Carried-expired revisions -- red, square marker, prominent
    if expired:
        ax.scatter(
            [r.runway_low_mo for r in expired],
            [r.moved_days for r in expired],
            s=100, alpha=0.95, color="#f85149", marker="s",
            label="PCD revision (carried expired date)",
            zorder=4,
        )
        # Annotate each expired point with ticker + days_expired.
        for r in expired:
            ax.annotate(
                f"{r.ticker}\n{r.days_expired}d expired",
                xy=(r.runway_low_mo, r.moved_days),
                xytext=(8, 6), textcoords="offset points",
                fontsize=7, color="#f85149",
            )

    # Zero line
    ax.axhline(0, color="#30363d", linewidth=0.8, zorder=1)

    # Axis labels and styling
    ax.set_xlabel("Runway (months, conservative estimate)", color="#c9d1d9", fontsize=11)
    ax.set_ylabel("PCD move (days)", color="#c9d1d9", fontsize=11)
    ax.tick_params(colors="#8b949e")
    for spine in ax.spines.values():
        spine.set_edgecolor("#30363d")

    n_companies = len({r.ticker for r in rows})
    n_trials = len({r.nct for r in rows})
    n_revisions = len(plot_rows)
    n_expired_revisions = len(expired)
    n_reversals = sum(1 for r in rows if r.is_reversal and r.moved_days is not None)

    ax.set_title(
        "PCD revision magnitude vs. sponsor runway\n"
        "12 companies, not the sector",
        color="#c9d1d9", fontsize=13, pad=12,
    )

    # Legend
    legend = ax.legend(
        facecolor="#161b22", edgecolor="#30363d",
        labelcolor="#c9d1d9", fontsize=9,
    )

    # Caption below the axes
    caption = (
        f"Sample: {n_companies} clinical-stage companies, {n_trials} pivotal trial(s), "
        f"{n_revisions} PCD-moving revisions (excluding {n_reversals} data-entry reversals). "
        f"Red squares: {n_expired_revisions} revision(s) where the sponsor carried a date that had already passed. "
        f"Runway is from the most recent SEC 10-Q/10-K (as of 2026-Q1). "
        f"Descriptive only. No causal claim."
    )
    fig.text(
        0.5, -0.03, caption,
        ha="center", va="top", fontsize=7.5, color="#8b949e",
        wrap=True, transform=fig.transFigure,
    )

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
