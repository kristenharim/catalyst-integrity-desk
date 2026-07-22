"""The acquisition boundary: the only place in this system that knows whether
evidence came from a frozen file or a live API.

Everything downstream -- normalisation, promise identity, the funding-gap
arithmetic, the Granite guard, the ledger -- accepts an `EvidenceSnapshot` and
has no concept of a "mode". That is the whole point. The demo is only evidence
about the product if the demo and the product run the same code, and the
cheapest way to guarantee that is to make the compute layer structurally
incapable of asking where its inputs came from.

    ticker or snapshot id
             |
             v
      SnapshotProvider          <- the seam, two implementations
             |
             v
      EvidenceSnapshot          <- immutable, content-addressed, one schema
             |
             v
      normalise -> promise identity -> metrics -> guarded prose -> ledger
                          (no network, no credentials, no mode)

`tests/test_layering.py` asserts the boundary holds by walking imports: the
compute packages may not import this one. A convention that is not checked is
a convention that has already been broken somewhere you have not looked.
"""
from evidence.snapshot import (
    EvidenceSnapshot,
    SourceRecord,
    NegativeResult,
    snapshot_digest,
)
from evidence.provider import (
    SnapshotProvider,
    FrozenSnapshotProvider,
    LiveSnapshotProvider,
    Incomplete,
)

__all__ = [
    "EvidenceSnapshot",
    "SourceRecord",
    "NegativeResult",
    "snapshot_digest",
    "SnapshotProvider",
    "FrozenSnapshotProvider",
    "LiveSnapshotProvider",
    "Incomplete",
]
