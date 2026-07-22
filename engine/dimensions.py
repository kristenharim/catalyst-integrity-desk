"""Read the dimensions that decide whether two registry versions are the same promise.

`engine/ctgov_history.py` fetches each version's full study record and extracts
the status module, because the date is what it needs. The rest of the record --
the primary outcome measure, the enrolment, the phase -- is already on disk in
`data/cache/`, unread.

That gap has a consequence the project had not stated. `total_slip_days` is
computed by subtracting registered dates across versions, which is only slip if
the commitment held its shape. Without the outcome and enrolment per version,
that was never checked. `engine/promise.py` refuses to state a slip number it
cannot establish, so before this module existed every revision classified as
`uncertain` and the headline slip figures were unsupported rather than wrong.

This module closes that, without touching the three verified engine modules or
their interfaces. It reads the same cache, offline, and says which versions it
could not establish rather than assuming they held.

    python3 -m engine.dimensions NCT06092034
"""
from __future__ import annotations

import glob
import json
import os
import sys
from dataclasses import dataclass

from engine.ctgov_history import CACHE

# Fields whose change means the commitment changed shape rather than slipped.
# Deliberately few: each one has to be readable from every version, or it
# produces `uncertain` for the whole trial and helps nobody.
@dataclass(frozen=True)
class Dimensions:
    version: int
    phase: str | None
    endpoint: str | None
    enrollment: str | None
    status: str | None

    @property
    def complete(self) -> bool:
        """Whether continuity can be decided from this version at all."""
        return all(x is not None for x in (self.phase, self.endpoint, self.enrollment))


def _proto(doc: dict) -> dict:
    return doc.get("study", doc).get("protocolSection", {})


def _endpoint(proto: dict) -> str | None:
    """The primary outcome measures, joined and normalised.

    Joined rather than compared element-wise on purpose: a sponsor adding a
    co-primary endpoint has changed what is being promised, and treating that as
    "the first one still matches" would let a scope revision through as slip.
    """
    outcomes = (proto.get("outcomesModule") or {}).get("primaryOutcomes") or []
    measures = [str(o.get("measure", "")).strip() for o in outcomes]
    measures = [m for m in measures if m]
    return " | ".join(sorted(measures)) if measures else None


def _enrollment(proto: dict) -> str | None:
    info = (proto.get("designModule") or {}).get("enrollmentInfo") or {}
    count = info.get("count")
    return None if count is None else str(count)


def _phase(proto: dict) -> str | None:
    phases = (proto.get("designModule") or {}).get("phases") or []
    return "/".join(sorted(phases)) if phases else None


def _status(proto: dict) -> str | None:
    return (proto.get("statusModule") or {}).get("overallStatus") or None


def from_cache(nct: str) -> dict[int, Dimensions]:
    """Dimensions per cached version. Offline; unread versions are simply absent.

    Absence is the honest outcome for a version this system has not seen. The
    caller reports it as unestablished rather than filling it in.
    """
    out: dict[int, Dimensions] = {}
    for path in sorted(glob.glob(os.path.join(CACHE, f"{nct}-v*.json"))):
        base = os.path.basename(path)
        try:
            version = int(base.rsplit("-v", 1)[1][: -len(".json")])
        except (IndexError, ValueError):
            continue
        with open(path) as f:
            proto = _proto(json.load(f))
        out[version] = Dimensions(
            version=version,
            phase=_phase(proto),
            endpoint=_endpoint(proto),
            enrollment=_enrollment(proto),
            status=_status(proto),
        )
    return out


def enrich(history_dict: dict) -> dict:
    """Attach dimensions to each revision of a serialised TrialHistory.

    Returns a new dict; the input is not mutated, so a snapshot that was already
    written stays byte-identical unless it is rebuilt on purpose. Revisions whose
    version is not cached are returned unchanged and will classify as
    `uncertain`, which is the correct answer for a version nobody has read.
    """
    nct = history_dict.get("nct", "")
    dims = from_cache(nct)
    out = dict(history_dict)
    revisions = []
    for rev in history_dict.get("revisions") or []:
        rev = dict(rev)
        d = dims.get(rev.get("version"))
        if d is not None:
            rev["phase"] = d.phase
            rev["primary_outcome"] = d.endpoint
            rev["enrollment"] = d.enrollment
            # The status module is already read by the fetcher for the date, but
            # not carried onto the revision, and promise identity needs it to
            # detect a terminated commitment.
            rev.setdefault("status", d.status)
            rev["dimensions_established"] = d.complete
        else:
            rev["dimensions_established"] = False
        revisions.append(rev)
    out["revisions"] = revisions
    out["dimensions_established"] = all(
        r.get("dimensions_established") for r in revisions
    ) if revisions else False
    return out


def coverage(nct: str, versions: list[int]) -> tuple[int, int]:
    """(versions with complete dimensions, versions asked about)."""
    dims = from_cache(nct)
    have = sum(1 for v in versions if v in dims and dims[v].complete)
    return have, len(versions)


def demo() -> None:
    """Self-check against whatever is cached, with no network."""
    cached = sorted({os.path.basename(p).rsplit("-v", 1)[0]
                     for p in glob.glob(os.path.join(CACHE, "*-v*.json"))})
    assert cached, f"no cached versions under {CACHE}; nothing to check"

    checked = 0
    for nct in cached[:20]:
        dims = from_cache(nct)
        if not dims:
            continue
        checked += 1
        for v, d in dims.items():
            assert d.version == v
            # Every field is either a non-empty string or None. An empty string
            # would compare equal across versions and manufacture continuity.
            for name in ("phase", "endpoint", "enrollment", "status"):
                val = getattr(d, name)
                assert val is None or (isinstance(val, str) and val), (nct, v, name, val)

    assert checked, "no trial produced any dimensions"

    # The demo centrepiece must be establishable, or the slip figure this
    # project reports for it stays unsupported.
    rckt = from_cache("NCT06092034")
    assert rckt, "NCT06092034 is not cached"
    complete = [v for v, d in rckt.items() if d.complete]
    assert complete, "no NCT06092034 version has readable dimensions"
    print(f"ok, {checked} trials, NCT06092034 complete on versions {sorted(complete)}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        for v, d in sorted(from_cache(sys.argv[1]).items()):
            print(f"v{v:<3} phase={d.phase} enrol={d.enrollment} "
                  f"status={d.status}\n      endpoint={(d.endpoint or '')[:90]}")
    else:
        demo()
