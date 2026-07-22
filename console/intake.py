"""Ticker in, proposed contract out. The layer between the seam and the views.

Reads an `EvidenceSnapshot` and produces the three things the workspace flow
needs: the resolved entity with its state, the candidate trials with what their
revision history does and does not support, and a proposed contract for a human
to edit and approve.

It computes nothing a template will render as a number without going through the
engine, and it decides nothing a human should decide. Two gates are deliberate:
which trial underwrites the thesis, and whether the proposed contract is right.
Neither is inferrable from a ticker.
"""
from __future__ import annotations

import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.ctgov_history import _parse_date
from engine.ledger import BeliefCard
from engine.promise import (
    Promise, net_slip_days, walk,
)
from evidence import EvidenceSnapshot

# Mirrors the console's belief form: an analyst states a floor, and being better
# funded than assumed is not a breach.
# ponytail: a sentinel, not math. Never displayed; the UI says "unbounded above".
UNBOUNDED_ABOVE = 1.0e9


# ---------------------------------------------------------------------------
# Reading the bundle
# ---------------------------------------------------------------------------

def entity(snap: EvidenceSnapshot) -> dict:
    """The sponsor-to-issuer join, as a reviewable claim rather than a fact.

    There is no CIK in the clinical registry, so this join is a string match and
    it is the single largest source of silent wrongness in the system. In demo
    mode a bad match is invisible. Here it is the analyst's first impression, so
    it carries a state and the method that produced it.
    """
    e = dict(snap.entity)
    e.setdefault("state", "unreviewed")
    e["explained"] = {
        "exact": "the registry sponsor string equals the SEC legal name",
        "normalised": "the strings match only after suffixes and punctuation "
                      "were stripped; a human should confirm this is one company",
        "review": "no confident match; treat every trial below as unverified",
        "unreviewed": "the join has not been checked",
    }.get(e["state"], "the join has not been checked")
    return e


def _runway(snap: EvidenceSnapshot) -> dict | None:
    recs = snap.by_source("sec.xbrl")
    return recs[0].payload if recs else None


def _histories(snap: EvidenceSnapshot) -> dict[str, dict]:
    return {r.locator: r.payload for r in snap.by_source("clinicaltrials.versions")}


def _trials(snap: EvidenceSnapshot) -> list[dict]:
    recs = snap.by_source("clinicaltrials.v2")
    return list(recs[0].payload.get("trials", [])) if recs else []


# ---------------------------------------------------------------------------
# Candidates
# ---------------------------------------------------------------------------

def candidates(snap: EvidenceSnapshot) -> list[dict]:
    """Every pivotal trial in the bundle, with what its history supports.

    The per-trial slip figure is the reason this is not a dropdown. A trial whose
    registered date moved 943 days across revisions that held their shape is a
    different object from one that moved the same distance while its endpoint
    changed, and the second must not be summarised with a number. Both are shown;
    only the first carries one.
    """
    as_of = _parse_date(snap.as_of) or date.today()
    runway = _runway(snap) or {}
    actor = runway.get("name", snap.subject)
    hists = _histories(snap)

    out = []
    for t in _trials(snap):
        pcd = _parse_date(t.get("pcd"))
        lapsed = pcd is not None and pcd < as_of
        hist = hists.get(t["nct"])

        slip = refused = None
        n_revisions = 0
        transitions: list = []
        if hist:
            promises = _promises(hist, actor)
            transitions = walk(promises)
            n_revisions = len(hist.get("revisions") or [])
            slip, refused = net_slip_days(transitions)

        out.append({
            "nct": t["nct"],
            "title": t.get("title", ""),
            "status": t.get("status", ""),
            "pcd": t.get("pcd"),
            "pcd_type": t.get("pcd_type", ""),
            "phases": t.get("phases", []),
            "lapsed": lapsed,
            # A lapsed date is never a catalyst. Shown, never selectable as one.
            "selectable": not lapsed,
            "n_revisions": n_revisions,
            "slip_days": slip,
            "refused_revisions": refused,
            "transitions": [
                {"kind": tr.kind, "reason": tr.reason,
                 "slip_days": tr.slip_days, "changed": tr.changed}
                for tr in transitions
            ],
        })
    # Future first, then by nearest date. Lapsed rows sink but never disappear.
    out.sort(key=lambda c: (c["lapsed"], c["pcd"] or "9999"))
    return out


def _promises(hist: dict, actor: str) -> list[Promise]:
    """One Promise per registry version.

    Dimensions the fetcher does not extract stay `None`. That is the honest
    default and it has a cost: those revisions classify as `uncertain` and
    produce no slip number. Defaulting them to something agreeable would
    manufacture exactly the continuity `engine/promise.py` exists to refuse.
    """
    out = []
    for rev in hist.get("revisions") or []:
        out.append(Promise(
            actor=actor,
            subject=hist.get("nct", ""),
            milestone="primary_completion",
            due=_parse_date(rev.get("pcd")),
            scope=rev.get("phase"),
            endpoint=rev.get("primary_outcome"),
            population=rev.get("enrollment"),
            status=rev.get("status"),
            version=rev.get("version"),
            submitted=rev.get("submitted"),
        ))
    return out


# ---------------------------------------------------------------------------
# The proposal
# ---------------------------------------------------------------------------

def propose(snap: EvidenceSnapshot, nct: str, min_gap: float = 0.0) -> dict:
    """A contract for a human to edit, assembled from fields.

    The claim text is deterministic prose built from the record, not generated.
    A model has no part in this step: the analyst edits what is proposed, and it
    is the analyst's wording Granite later reads.
    """
    runway = _runway(snap) or {}
    chosen = next((c for c in candidates(snap) if c["nct"] == nct), None)
    if chosen is None:
        raise ValueError(f"{nct} is not in the evidence for {snap.subject}")
    if not chosen["selectable"]:
        raise ValueError(
            f"{nct} has a registered primary completion of {chosen['pcd']}, which "
            f"has already passed. A lapsed date is never a catalyst."
        )

    name = runway.get("name", snap.subject)
    claim = (
        f"{name} reaches the registered primary completion of {nct} "
        f"({chosen['pcd']}) before its cash is exhausted, and does not need to "
        f"finance before that date."
    )
    card = BeliefCard(
        card_id=f"{snap.subject.lower()}:{nct.lower()}",
        scope=nct,
        claim=claim,
        metric="gap_months",
        expected_low=min_gap,
        expected_high=UNBOUNDED_ABOVE,
        driver=(f"SEC XBRL liquidity (filing as of {runway.get('as_of')}) vs "
                f"ClinicalTrials.gov registered primary completion for {nct}"),
        confidence=3,
        source="console.workspace",
        as_of=runway.get("as_of", snap.as_of),
    )
    return {
        "card": card,
        "trial": chosen,
        "entity": entity(snap),
        "monitors": _monitors(snap),
        "evidence_digest": snap.digest,
    }


def _monitors(snap: EvidenceSnapshot) -> list[dict]:
    """What this contract can and cannot be watched for.

    The unavailable rows are the point. A monitoring product that lists a
    condition it cannot evaluate has told the analyst it is being watched, and
    that is worse than not offering it.
    """
    return [
        {"id": "date_moves", "label": "the registered completion moves later",
         "available": True, "why": "every registry version is retrievable"},
        {"id": "date_lapses", "label": "the registered completion passes without amendment",
         "available": True, "why": "comparing the registered date to the pinned as_of"},
        {"id": "runway_falls", "label": "runway falls below the stated minimum",
         "available": True, "why": "recomputed from SEC XBRL each run"},
        {"id": "burn_unreliable", "label": "the burn estimate becomes unusable",
         "available": True, "why": "a one-time inflow in the trailing window"},
        {"id": "tag_path_changes", "label": "the SEC tag a figure resolves through changes",
         "available": False,
         "why": "needs a previous run to diff against; available from the second "
                "run onward, not the first"},
        {"id": "scope_revision", "label": "the commitment changes shape rather than date",
         "available": bool(_has_dimensions(snap)),
         "why": "needs endpoint and enrolment per registry version, which the "
                "current fetcher does not extract"},
    ]


def _has_dimensions(snap: EvidenceSnapshot) -> bool:
    """Whether any stored revision carries the fields scope comparison needs."""
    for payload in _histories(snap).values():
        for rev in payload.get("revisions") or []:
            if rev.get("primary_outcome") or rev.get("enrollment"):
                return True
    return False


def summary(snap: EvidenceSnapshot) -> dict:
    """What was looked at, so the page can say it rather than imply it."""
    return {
        "subject": snap.subject,
        "as_of": snap.as_of,
        "origin": snap.origin,
        "digest": snap.digest,
        "complete": snap.complete,
        "missing": snap.missing,
        "sources": sorted({r.source for r in snap.records}),
        "negatives": [
            {"source": n.source, "locator": n.locator, "reason": n.reason,
             "fetched_at": n.fetched_at}
            for n in snap.negatives
        ],
    }
