"""The one schema both providers write into.

An `EvidenceSnapshot` is a record of *what was asked, of whom, when, and what
came back* -- including what did not come back. Three properties matter and each
one exists because leaving it out produces a specific lie:

**Content addressed.** The digest covers the source payloads, so two runs that
saw the same evidence produce the same digest and a hand-edited snapshot does
not. Without it, "we reran and nothing changed" is unfalsifiable.

**Negative results are recorded.** A source that was queried and returned
nothing is a different fact from a source that was never queried, and both
render as an empty list if you only store what you found. `docs/LIMITS.md`
already forbids saying "no amendment exists" rather than "no amendment found in
source S under procedure P at time T"; this is the structure that makes the
honest sentence writable.

**Two timestamps, never one.** `published_at` is when the source says the fact
became true. `fetched_at` is when this system looked. Collapsing them is how a
monitor claims to have known something before it did.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Any

# Bumped when the shape of a SourceRecord payload changes in a way that would
# make an older snapshot parse differently. Stored in every snapshot so a stale
# artifact announces itself instead of being silently reinterpreted.
SCHEMA_VERSION = 1


def _canonical(obj: Any) -> str:
    """Stable JSON: sorted keys, no incidental whitespace, so a digest over it
    depends on content and not on dict ordering or formatting."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


@dataclass(frozen=True)
class SourceRecord:
    """One thing that was fetched, and everything needed to find it again.

    `locator` must be specific enough to re-request exactly this record: a URL
    with its query, an XBRL tag on a CIK, a numbered registry version. "the SEC"
    is not a locator.
    """
    source: str              # "sec.xbrl" | "clinicaltrials.v2" | ...
    locator: str             # the exact thing requested
    published_at: str | None  # when the SOURCE says this became true
    fetched_at: str          # when this system looked
    payload: Any             # the parsed response, as stored
    parser_version: int = SCHEMA_VERSION

    @property
    def digest(self) -> str:
        return hashlib.sha256(_canonical(asdict(self)).encode()).hexdigest()


@dataclass(frozen=True)
class NegativeResult:
    """A query that ran and found nothing.

    This is evidence. An empty `records` list with no negative result beside it
    means "we never looked", and the two must never render the same way.
    """
    source: str
    locator: str
    fetched_at: str
    reason: str              # "zero results" | "404" | "no matching sponsor" ...


@dataclass
class EvidenceSnapshot:
    """Everything one evaluation is allowed to see.

    `complete` is deliberately not a computed property. Whether a bundle is
    complete depends on what was asked for, which the provider knows and the
    snapshot does not. An incomplete bundle is a first-class surfaced state, not
    an empty result dressed as "no findings" -- see `Incomplete`.
    """
    subject: str                                    # the ticker or entity asked about
    as_of: str                                      # the pinned classification date
    origin: str                                     # "frozen" | "live"
    records: list[SourceRecord] = field(default_factory=list)
    negatives: list[NegativeResult] = field(default_factory=list)
    entity: dict[str, Any] = field(default_factory=dict)   # resolved identity + confidence
    missing: list[str] = field(default_factory=list)       # asked for, not obtained
    schema_version: int = SCHEMA_VERSION

    # -- lookup ------------------------------------------------------------

    def by_source(self, source: str) -> list[SourceRecord]:
        return [r for r in self.records if r.source == source]

    def one(self, source: str, locator: str) -> SourceRecord | None:
        for r in self.records:
            if r.source == source and r.locator == locator:
                return r
        return None

    def was_queried(self, source: str) -> bool:
        """True if this source was reached at all, found or not.

        The question "did we look" has to be answerable separately from "did we
        find", or silence and absence collapse into each other.
        """
        return any(r.source == source for r in self.records) or any(
            n.source == source for n in self.negatives
        )

    @property
    def complete(self) -> bool:
        return not self.missing

    # -- identity ----------------------------------------------------------

    @property
    def digest(self) -> str:
        return snapshot_digest(self)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["digest"] = self.digest
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "EvidenceSnapshot":
        stored = d.get("digest")
        snap = cls(
            subject=d["subject"],
            as_of=d["as_of"],
            origin=d["origin"],
            records=[SourceRecord(**r) for r in d.get("records", [])],
            negatives=[NegativeResult(**n) for n in d.get("negatives", [])],
            entity=d.get("entity", {}),
            missing=list(d.get("missing", [])),
            schema_version=d.get("schema_version", SCHEMA_VERSION),
        )
        if stored is not None and stored != snap.digest:
            raise ValueError(
                f"snapshot digest mismatch for {snap.subject}: stored {stored[:12]}, "
                f"recomputed {snap.digest[:12]}. The file was edited after it was "
                f"written, or the schema changed without a version bump."
            )
        return snap


def snapshot_digest(snap: EvidenceSnapshot) -> str:
    """Content address over the evidence, not over the wrapper.

    `origin` is excluded on purpose: the same evidence fetched live and replayed
    from a file must produce the same digest, or the cross-mode equality test
    below can never pass and the seam cannot be verified.

    `fetched_at` rides inside each record and DOES affect the digest, because two
    runs at different times genuinely saw different evidence even when the values
    match. Reproducibility here means "the same stored bundle always evaluates
    the same way", not "two live fetches are identical", which is not true and
    should not be claimed.
    """
    body = {
        "subject": snap.subject,
        "as_of": snap.as_of,
        "schema_version": snap.schema_version,
        "records": sorted(r.digest for r in snap.records),
        "negatives": sorted(_canonical(asdict(n)) for n in snap.negatives),
        "entity": snap.entity,
        "missing": sorted(snap.missing),
    }
    return hashlib.sha256(_canonical(body).encode()).hexdigest()
