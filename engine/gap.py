"""The catalyst contract: can this company fund itself to its own next readout?

    funding gap = runway exhaustion date - registered primary completion date

Negative means the money runs out first. Both sides are deterministic and sourced:
the left from SEC XBRL tags, the right from the sponsor's own registry filing. No
model contributes a number to either.

What makes this more than a subtraction is the third column. The registry date is not
an observation, it is a *claim the sponsor can revise at will*, and every revision is
timestamped. So alongside the gap we carry the sponsor's revision behaviour: how many
times the date moved, and how much notice was given each time. A company that pushes a
readout eighteen months out with a year of warning is forecasting. One that moves it
three weeks before it arrives was showing a date it had stopped believing -- and if
that behaviour turns out to cluster in cash-constrained sponsors, the registry is not
a data source, it is a disclosure channel with incentives.

That last claim is a hypothesis, not a result. This module assembles the panel needed
to test it. It does not test it, and nothing here should be presented as if it had.
"""
from __future__ import annotations

import json
import urllib.parse
from dataclasses import dataclass
from datetime import date

from engine.ctgov_history import TrialHistory, _get, _parse_date, fetch_history
from engine.runway import Runway, compute_runway, ticker_to_cik

V2 = "https://clinicaltrials.gov/api/v2/studies"
# Phase 2/3 only. Early-phase trials are not value-inflection points, and including
# them buries the catalyst in a pile of dose-escalation studies.
PIVOTAL_PHASES = {"PHASE2", "PHASE3", "PHASE2_PHASE3"}
LIVE = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING"}


def find_trials(sponsor: str, limit: int = 40) -> list[dict]:
    """Live pivotal-ish trials for one lead sponsor.

    The sponsor field is free text with no CIK, so this join is the engineering tax
    of the whole project: matching is by name, and names drift (subsidiaries, "Inc."
    vs "Inc", post-merger renames). Good enough to demo one company; a universe run
    needs an alias table and hand review of the largest names.
    """
    q = urllib.parse.urlencode({
        "query.spons": sponsor,
        "fields": ",".join([
            "protocolSection.identificationModule.nctId",
            "protocolSection.identificationModule.briefTitle",
            "protocolSection.statusModule.overallStatus",
            "protocolSection.statusModule.primaryCompletionDateStruct",
            "protocolSection.designModule.phases",
            "protocolSection.sponsorCollaboratorsModule.leadSponsor",
        ]),
        "pageSize": limit,
    })
    out = []
    for s in _get(f"{V2}?{q}").get("studies", []):
        p = s.get("protocolSection", {})
        phases = set(p.get("designModule", {}).get("phases", []) or [])
        status = p.get("statusModule", {}).get("overallStatus", "")
        pcd = p.get("statusModule", {}).get("primaryCompletionDateStruct", {}) or {}
        if not (phases & PIVOTAL_PHASES) or status not in LIVE or not pcd.get("date"):
            continue
        out.append({
            "nct": p["identificationModule"]["nctId"],
            "title": p["identificationModule"].get("briefTitle", ""),
            "status": status,
            "pcd": pcd["date"],
            "pcd_type": pcd.get("type", ""),
            "phases": sorted(phases),
            "sponsor": p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name", ""),
        })
    return sorted(out, key=lambda t: t["pcd"])


@dataclass
class CatalystContract:
    """One testable claim: this company reaches this readout on this money."""
    runway: Runway
    trial: dict
    history: TrialHistory | None = None

    @property
    def catalyst_date(self) -> date | None:
        return _parse_date(self.trial["pcd"])

    @property
    def gap_months(self) -> float | None:
        """Months of runway left at the registered readout date. Negative = short.

        Computed against the CONSERVATIVE end of the burn band. Reporting the
        optimistic end would flatter every row in the same direction.
        """
        end = self.runway.exhaustion(self.runway.months_low)
        cat = self.catalyst_date
        if end is None or cat is None:
            return None
        return (end - cat).days / (365.25 / 12)

    @property
    def verdict(self) -> str:
        g = self.gap_months
        if g is None:
            return "not computable"
        if not self.runway.reliable:
            return "not rankable (burn estimate unreliable)"
        return "funded to catalyst" if g >= 0 else "financing required before catalyst"

    def lines(self) -> list[str]:
        r, t = self.runway, self.trial
        g = self.gap_months
        out = [
            f"{r.ticker}  {r.name}",
            f"  liquidity      ${r.liquidity/1e6:,.0f}M  ({r.provenance['cash']} + {r.provenance['securities']}, as of {r.as_of})",
            f"  burn band      ${r.burn_ttm_annual/1e6:,.0f}M/yr trailing, ${r.burn_recent_annual/1e6:,.0f}M/yr most recent quarter",
            f"  runway         {r.months_low:.1f}-{r.months_high:.1f} months, exhausted {r.exhaustion(r.months_low)}",
            f"  catalyst       {t['nct']}  {'/'.join(t['phases'])}  {t['status']}",
            f"                 {t['title'][:70]}",
            f"                 primary completion {t['pcd']} ({t['pcd_type'].lower()})",
            f"  FUNDING GAP    {'n/a' if g is None else f'{g:+.1f} months'}   -> {self.verdict}",
        ]
        if self.history and self.history.revisions:
            h = self.history
            out += [
                f"  date integrity {len(h.revisions)} revisions across {h.n_versions} versions, "
                f"net slip {h.total_slip_days:+d} days, {h.n_late_moves} moved with under 90 days notice",
            ]
            if h.n_expired_carried:
                out.append(f"  *** EXPIRED     showed an already-passed completion date for up to "
                           f"{h.max_days_expired} days before correcting it")
            for rev in h.revisions[-4:]:
                if rev.carried_expired:
                    notice = f"{rev.days_expired:>4}d EXPIRED"
                elif rev.held_days is None:
                    notice = ""
                else:
                    notice = f"{rev.held_days:>5}d notice"
                moved = "" if rev.moved_days is None else f"{rev.moved_days:+5d}d"
                out.append(f"                 v{rev.version:<4} {rev.submitted}  -> {rev.pcd}  {moved}  {notice}")
        for n in r.notes:
            out.append(f"  note           {n}")
        return out


def build(ticker: str, cik_map=None, with_history: bool = True) -> CatalystContract | None:
    r = compute_runway(ticker, cik_map)
    trials = find_trials(r.name)
    if not trials:
        return None
    # The nearest live pivotal readout is the binding catalyst.
    trial = trials[0]
    hist = None
    if with_history:
        try:
            hist = fetch_history(trial["nct"])
        except (RuntimeError, ValueError):
            pass  # history is an enrichment, not a precondition
    return CatalystContract(runway=r, trial=trial, history=hist)


def demo() -> None:
    cik_map = ticker_to_cik()
    built = 0
    for ticker in ["SANA", "PRME", "RCKT", "NTLA"]:
        c = build(ticker, cik_map)
        if c is None:
            print(f"{ticker}: no live pivotal trial matched by sponsor name\n")
            continue
        built += 1
        assert c.runway.ticker == ticker
        assert c.trial["nct"].startswith("NCT")
        if c.gap_months is not None:
            # Gap must equal exhaustion minus catalyst, to the day.
            recomputed = (c.runway.exhaustion(c.runway.months_low) - c.catalyst_date).days
            assert abs(recomputed / (365.25 / 12) - c.gap_months) < 1e-9
        print("\n".join(c.lines()))
        print()
    assert built, "no contract assembled"
    print("ok")


if __name__ == "__main__":
    demo()
