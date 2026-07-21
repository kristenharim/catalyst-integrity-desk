"""Sponsor forecast revisions, reconstructed from ClinicalTrials.gov version history.

Registered trials carry a primary completion date (PCD). Sponsors may revise it at
any time, and every revision is kept as a numbered protocol version. Nobody diffs
them, so the revision path is a free, timestamped record of how a sponsor's own
forecast moved -- and of how long it held a date it was going to miss.

Two endpoints, neither in the public v2 docs, both unauthenticated:

    /api/int/studies/{nct}/history          -> every version, with a change date
    /api/int/studies/{nct}/history/{n}      -> the full protocol snapshot at version n

The listing is one request. Snapshots are one request each, so a 95-version trial is
95 requests if fetched naively. Two things keep that bounded: `moduleLabels` names
which modules changed in each version, and PCD lives in the status module, so any
version that did not touch it cannot have moved the date. Snapshots are cached on
disk, keyed by (nct, version), because history is immutable once written.

The derived quantity that matters is not the total slip. It is `held_days`: how close
the then-current date was when the sponsor finally moved it. A sponsor that pushes a
date out eighteen months in advance is forecasting. One that moves it eleven days
before it arrives was holding a date it had stopped believing.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, asdict
from datetime import date, datetime

BASE = "https://clinicaltrials.gov/api/int/studies"
# SEC and NIH both ask for a contact in the UA. Same courtesy here.
UA = os.environ.get("CTGOV_UA", "catalyst-integrity-desk (kris10harim@gmail.com)")
CACHE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cache")
SLEEP = float(os.environ.get("CTGOV_SLEEP", "0.12"))  # ~8 req/s, well inside tolerance

# The module that carries primaryCompletionDateStruct. A version whose moduleLabels
# omits this cannot have moved the date, so its snapshot is never fetched.
STATUS_LABEL = "Study Status"


def _get(url: str, retries: int = 3) -> dict:
    """Fetch JSON via curl.

    Not urllib, and this is not a style choice. The endpoint is gated on TLS
    fingerprint, not on headers: every urllib request returns 403 while the identical
    request through curl returns 200, including with a browser User-Agent, an explicit
    Accept, and gzip encoding. Tested four header combinations against a curl control.
    So `requests` will fail here too -- it shares OpenSSL's fingerprint. The options are
    shelling out to curl or adding curl_cffi; curl ships with macOS and needs no
    dependency, so the crawler shells out.
    """
    for attempt in range(retries):
        p = subprocess.run(
            ["curl", "-sS", "--fail", "--max-time", "30", "-H", f"User-Agent: {UA}", url],
            capture_output=True, text=True,
        )
        if p.returncode == 0:
            try:
                return json.loads(p.stdout)
            except json.JSONDecodeError:
                pass  # truncated body, worth one more try
        if attempt == retries - 1:
            raise RuntimeError(f"GET {url} failed: {p.stderr.strip() or p.returncode}")
        time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def _cached(nct: str, version: int) -> dict:
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{nct}-v{version}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    time.sleep(SLEEP)
    d = _get(f"{BASE}/{nct}/history/{version}")
    with open(path, "w") as f:
        json.dump(d, f)
    return d


def _parse_date(s: str | None) -> date | None:
    """Registry dates come as YYYY-MM-DD or YYYY-MM. Month-only means the sponsor
    did not commit to a day; treat it as the first, and do not pretend otherwise."""
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


@dataclass
class Revision:
    """One version at which the registered primary completion date changed."""
    version: int
    submitted: str          # when the sponsor filed this revision
    pcd: str                # the date as of this version
    pcd_type: str           # ESTIMATED or ACTUAL
    status: str
    moved_days: int | None  # how far the date moved vs the previous version
    held_days: int | None   # days remaining on the OLD date when it was moved

    @property
    def is_late_move(self) -> bool:
        """Moved with under 90 days left on a date the sponsor had been showing.
        Not proof of anything on its own; it is the observation the study counts."""
        return self.held_days is not None and 0 <= self.held_days < 90

    @property
    def carried_expired(self) -> bool:
        """The date being replaced had ALREADY PASSED when the sponsor replaced it.

        A stronger signal than a late move, and a different one. A late revision can
        be a genuine surprise late in a trial. A date left standing after it lapsed
        means the public registry showed a completion date the sponsor had already
        missed, for `-held_days` days, with no correction. Rocket Pharmaceuticals
        carried a 2022-06 date until 2024-04 -- 677 days expired.
        """
        return self.held_days is not None and self.held_days < 0

    @property
    def days_expired(self) -> int:
        return -self.held_days if self.carried_expired else 0


@dataclass
class TrialHistory:
    nct: str
    sponsor: str
    phases: list[str]
    n_versions: int
    revisions: list[Revision]

    @property
    def first_pcd(self) -> str | None:
        return self.revisions[0].pcd if self.revisions else None

    @property
    def last_pcd(self) -> str | None:
        return self.revisions[-1].pcd if self.revisions else None

    @property
    def total_slip_days(self) -> int | None:
        a, b = _parse_date(self.first_pcd), _parse_date(self.last_pcd)
        return (b - a).days if a and b else None

    @property
    def n_late_moves(self) -> int:
        return sum(r.is_late_move for r in self.revisions)

    @property
    def n_expired_carried(self) -> int:
        return sum(r.carried_expired for r in self.revisions)

    @property
    def max_days_expired(self) -> int:
        """Longest stretch this trial showed a completion date that had already passed."""
        return max((r.days_expired for r in self.revisions), default=0)

    def as_dict(self) -> dict:
        d = asdict(self)
        d.update(first_pcd=self.first_pcd, last_pcd=self.last_pcd,
                 total_slip_days=self.total_slip_days, n_late_moves=self.n_late_moves)
        return d


def fetch_history(nct: str) -> TrialHistory:
    """Walk one trial's version history and return only the versions that moved the
    primary completion date."""
    listing = _get(f"{BASE}/{nct}/history")
    changes = listing.get("changes", [])
    if not changes:
        raise ValueError(f"{nct}: no version history returned")

    # Version 0 is always fetched (it establishes the first date); after that only
    # versions that touched the status module can have moved it.
    candidates = [c for c in changes
                  if c["version"] == 0 or STATUS_LABEL in (c.get("moduleLabels") or [])]

    sponsor, phases = "", []
    revisions: list[Revision] = []
    prev_pcd: date | None = None
    prev_raw = ""

    for c in candidates:
        snap = _cached(nct, c["version"])
        proto = snap.get("study", snap).get("protocolSection", {})
        status_mod = proto.get("statusModule", {})
        pcd_struct = status_mod.get("primaryCompletionDateStruct") or {}
        raw = pcd_struct.get("date")
        pcd = _parse_date(raw)
        if pcd is None:
            continue

        if not sponsor:
            sponsor = (proto.get("sponsorCollaboratorsModule", {})
                       .get("leadSponsor", {}).get("name", ""))
            phases = proto.get("designModule", {}).get("phases", []) or []

        if prev_pcd is not None and pcd == prev_pcd:
            continue  # status module changed for some other reason

        submitted = _parse_date(c.get("lastUpdateSubmitQcDate") or c.get("date"))
        moved = (pcd - prev_pcd).days if prev_pcd else None
        # How much runway the OLD date still had when the sponsor moved it. Negative
        # means they moved it after it had already passed, which is its own signal.
        held = (prev_pcd - submitted).days if prev_pcd and submitted else None

        revisions.append(Revision(
            version=c["version"],
            submitted=submitted.isoformat() if submitted else "",
            pcd=raw,
            pcd_type=pcd_struct.get("type", ""),
            status=c.get("status", ""),
            moved_days=moved,
            held_days=held,
        ))
        prev_pcd, prev_raw = pcd, raw

    return TrialHistory(nct=nct, sponsor=sponsor, phases=phases,
                        n_versions=len(changes), revisions=revisions)


def demo() -> None:
    """Self-check against a trial whose history is known to be long and messy."""
    h = fetch_history("NCT04613596")
    assert h.n_versions > 50, h.n_versions
    assert h.sponsor, "lead sponsor should resolve"
    assert len(h.revisions) >= 4, f"expected several PCD moves, got {len(h.revisions)}"
    # First recorded date must precede the last, or the walk is out of order.
    assert h.revisions == sorted(h.revisions, key=lambda r: r.version)
    # moved_days is None only on the first revision.
    assert all(r.moved_days is not None for r in h.revisions[1:])

    print(f"{h.nct}  {h.sponsor}  {'/'.join(h.phases) or 'n/a'}")
    print(f"  {h.n_versions} versions, {len(h.revisions)} of them moved the date")
    print(f"  {h.first_pcd} -> {h.last_pcd}   total slip {h.total_slip_days} days")
    print(f"  late moves (<90d notice): {h.n_late_moves}")
    print()
    print(f"  {'ver':>4} {'submitted':>11} {'PCD':>11} {'type':>10} {'moved':>7} {'held':>6}")
    for r in h.revisions:
        print(f"  {r.version:>4} {r.submitted:>11} {r.pcd:>11} {r.pcd_type:>10} "
              f"{'' if r.moved_days is None else f'{r.moved_days:+d}':>7} "
              f"{'' if r.held_days is None else r.held_days:>6}"
              f"{'  <- late' if r.is_late_move else ''}")
    print("\nok")


if __name__ == "__main__":
    demo()
