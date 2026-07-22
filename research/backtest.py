"""Period-accurate replay: what would this desk have said, on a past date?

The pressure test that matters is not "does it flag Rocket today", when the
answer is already in the snapshot. It is "would it have flagged Rocket on the
day the evidence first existed, using only what was public then". That question
is answerable here and almost nowhere else, because ClinicalTrials.gov keeps
every version a sponsor ever submitted, with the submission date attached.

So a replay is honest rather than simulated: take a cutoff date, discard every
registry version submitted after it, and evaluate. Nothing after the cutoff can
leak in, because nothing after the cutoff is in the input.

    python3 -m research.backtest NCT04248439
    python3 -m research.backtest --all

WHAT THIS MEASURES, and the distinction is the whole point:

    detection latency   the gap between the day the evidence was public and the
                        day anyone acted on it. Measurable. This is the claim.

    prediction          that the signal implies a future outcome. NOT measured,
                        NOT claimed, and forbidden by orchestrator/lexicon.py.
                        There is no preregistered out-of-sample study here and
                        saying otherwise would be the exact overreach this
                        project refuses.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from dataclasses import dataclass
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.ctgov_history import CACHE, _parse_date
from engine.dimensions import from_cache
from engine.promise import Promise, classify, net_slip_days, walk


@dataclass
class Observation:
    """One thing the desk would have been able to say, and the day it could."""
    as_of: str
    nct: str
    kind: str
    detail: str
    days_public_before_now: int | None = None


def _versions(nct: str) -> list[dict]:
    """Every cached version of one trial, in submission order.

    Reads the raw cache rather than `fetch_history`, because the fetcher keeps
    only versions that moved the completion date, and a replay needs to know
    what the registry said on a date when nothing had moved.
    """
    out = []
    for path in sorted(glob.glob(os.path.join(CACHE, f"{nct}-v*.json"))):
        try:
            version = int(os.path.basename(path).rsplit("-v", 1)[1][: -len(".json")])
        except (IndexError, ValueError):
            continue
        try:
            with open(path) as f:
                doc = json.load(f)
        except (json.JSONDecodeError, OSError):
            # See engine/dimensions.py: a truncated entry is skipped, not fatal.
            continue
        proto = doc.get("study", doc).get("protocolSection", {})
        status = proto.get("statusModule", {})
        pcd = (status.get("primaryCompletionDateStruct") or {}).get("date")
        submitted = (status.get("lastUpdateSubmitDate")
                     or status.get("statusVerifiedDate"))
        out.append({
            "version": version,
            "submitted": submitted,
            "pcd": pcd,
            # ESTIMATED or ACTUAL. Read from the same record as the date, because
            # the two together are what say whether a past date is reconciled: an
            # ACTUAL date in the past is a completed trial recording when it
            # completed, and an ESTIMATE in the past is a forecast that expired.
            "pcd_type": (status.get("primaryCompletionDateStruct") or {}).get("type"),
            "status": status.get("overallStatus"),
        })
    out.sort(key=lambda r: (r["submitted"] or "", r["version"]))
    return out


def as_known_on(nct: str, cutoff: date) -> list[dict]:
    """Only the versions a sponsor had submitted on or before the cutoff.

    The one line that makes this a backtest rather than a story.
    """
    out = []
    for rev in _versions(nct):
        submitted = _parse_date(rev["submitted"])
        if submitted is not None and submitted <= cutoff:
            out.append(rev)
    return out


def replay(nct: str, cutoff: date, actor: str = "sponsor") -> list[Observation]:
    """Everything the desk could have stated about one trial on one day."""
    known = as_known_on(nct, cutoff)
    if not known:
        return []

    dims = from_cache(nct)
    obs: list[Observation] = []
    iso = cutoff.isoformat()

    # --- 1. A registered date that had already passed, still standing --------
    # The signal this project was built on. It needs no comparison across
    # versions, which is why it is the sturdiest thing here.
    latest = known[-1]
    pcd = _parse_date(latest["pcd"])
    submitted = _parse_date(latest["submitted"])
    if pcd is not None and pcd < cutoff:
        days = (cutoff - pcd).days
        obs.append(Observation(
            iso, nct, "carried_expired",
            f"the registered primary completion is {latest['pcd']}, which passed "
            f"{days} days before this date, and version {latest['version']} "
            f"(submitted {latest['submitted']}) still carries it",
            days_public_before_now=days,
        ))

    # --- 2. A revision FILED carrying an already-dead date -------------------
    # Stronger than the above: not merely stale, but re-affirmed after expiry.
    for rev in known:
        p, s = _parse_date(rev["pcd"]), _parse_date(rev["submitted"])
        if p is not None and s is not None and p < s:
            obs.append(Observation(
                iso, nct, "filed_expired",
                f"version {rev['version']} was submitted {rev['submitted']} "
                f"carrying a completion date of {rev['pcd']}, already expired by "
                f"{(s - p).days} days at the moment of filing",
            ))

    # --- 3. Movement, only where the commitment held its shape ---------------
    promises = [
        Promise(
            actor=actor, subject=nct, milestone="primary_completion",
            due=_parse_date(r["pcd"]),
            scope=(dims.get(r["version"]).phase if r["version"] in dims else None),
            endpoint=(dims.get(r["version"]).endpoint if r["version"] in dims else None),
            population=(dims.get(r["version"]).enrollment if r["version"] in dims else None),
            status=r["status"], version=r["version"], submitted=r["submitted"],
        )
        for r in known
    ]
    transitions = walk(promises)
    established, refused = net_slip_days(transitions)
    if transitions:
        obs.append(Observation(
            iso, nct, "movement",
            f"{established} days of movement across revisions where the commitment "
            f"held its shape; {refused} revision(s) not comparable"
        ))

    # --- 4. A commitment withdrawn rather than moved -------------------------
    for a, b, t in zip(promises, promises[1:], transitions):
        if t.kind == "supersession":
            obs.append(Observation(
                iso, nct, "supersession",
                f"between version {a.version} and {b.version}: {t.reason}"))

    return obs


def first_observable(nct: str, kind: str) -> date | None:
    """The earliest date on which an observation of this kind was available.

    This is the detection-latency number. It is a fact about when evidence
    became public, not a claim about what it foretold.

    The candidate dates must include the day AFTER each registered completion,
    not only the days something was filed. An expired date becomes observable on
    a day when nothing happens at all -- the sponsor files nothing, and the date
    simply passes. Sampling only filing dates finds the first day someone
    happened to touch the record, which is a different and much later number,
    and quoting it would understate the latency this measures.
    """
    from datetime import timedelta

    revs = _versions(nct)
    candidates = {_parse_date(r["submitted"]) for r in revs}
    for r in revs:
        p = _parse_date(r["pcd"])
        if p is not None:
            candidates.add(p)
            candidates.add(p + timedelta(days=1))
    for d in sorted(c for c in candidates if c is not None):
        if any(o.kind == kind for o in replay(nct, d)):
            return d
    return None


def carried_until_corrected(nct: str) -> list[dict]:
    """Stretches where the registry showed an already-passed date, and the
    filing that ended each one.

    This is the 677-day result, derived by replay rather than asserted. It is the
    sturdiest signal in the system because it needs no comparison between two
    commitments: one version, one date, one clock.
    """
    revs = _versions(nct)
    out = []
    for prev, nxt in zip(revs, revs[1:]):
        pcd = _parse_date(prev["pcd"])
        corrected = _parse_date(nxt["submitted"])
        if pcd is None or corrected is None or pcd >= corrected:
            continue
        out.append({
            "expired_on": pcd.isoformat(),
            "corrected_on": corrected.isoformat(),
            "days_carried": (corrected - pcd).days,
            "version_carrying": prev["version"],
            "version_correcting": nxt["version"],
        })
    return out


def cached_trials() -> list[str]:
    return sorted({os.path.basename(p).rsplit("-v", 1)[0]
                   for p in glob.glob(os.path.join(CACHE, "*-v*.json"))})


def demo() -> None:
    """Self-check: the replay must be blind to everything after its cutoff."""
    trials = cached_trials()
    assert trials, f"no cached versions under {CACHE}"

    nct = "NCT04248439"
    assert nct in trials, f"{nct} is not cached"

    # Monotonic: a later cutoff can only ever see more versions.
    seen = [len(as_known_on(nct, date(y, 1, 1))) for y in (2019, 2021, 2023, 2025, 2027)]
    assert seen == sorted(seen), seen
    assert seen[0] == 0, "a cutoff before the first filing must see nothing"
    assert seen[-1] > 0, "a cutoff after the last filing must see something"

    # The blindness property, stated as an assertion rather than a comment:
    # nothing submitted after the cutoff may appear in the input.
    for cut in (date(2021, 1, 1), date(2024, 1, 1)):
        for rev in as_known_on(nct, cut):
            assert _parse_date(rev["submitted"]) <= cut, rev

    # And the finding itself: the expired date was observable years before now.
    first = first_observable(nct, "carried_expired")
    assert first is not None, "the expired-date signal never becomes observable"
    assert first < date(2025, 1, 1), first
    print(f"ok, {len(trials)} trials cached; {nct} carried_expired first "
          f"observable {first}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("nct", nargs="?", help="trial to replay")
    ap.add_argument("--as-of", help="cutoff date, YYYY-MM-DD")
    ap.add_argument("--all", action="store_true", help="scan every cached trial")
    args = ap.parse_args()

    if args.all:
        rows = []
        for nct in cached_trials():
            d = first_observable(nct, "carried_expired")
            if d:
                obs = [o for o in replay(nct, d) if o.kind == "carried_expired"]
                rows.append((d, nct, obs[0].days_public_before_now if obs else None))
        rows.sort()
        print(f"{'first observable':<18} {'trial':<14} days expired at that point")
        for d, nct, days in rows:
            print(f"{d.isoformat():<18} {nct:<14} {days}")
        print(f"\n{len(rows)} of {len(cached_trials())} cached trials carried an "
              f"already-passed registered completion date at some point.")
        return

    if not args.nct:
        demo()
        return

    cutoff = _parse_date(args.as_of) if args.as_of else date.today()
    print(f"Replay of {args.nct} as of {cutoff}, using only versions submitted "
          f"on or before that date.\n")
    known = as_known_on(args.nct, cutoff)
    print(f"  versions visible: {len(known)} of {len(_versions(args.nct))}")
    for o in replay(args.nct, cutoff):
        print(f"\n  [{o.kind}]\n    {o.detail}")
    if not known:
        print("  nothing had been filed yet.")


if __name__ == "__main__":
    main()
