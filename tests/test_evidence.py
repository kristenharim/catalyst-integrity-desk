"""The evidence schema: the three properties the seam depends on.

Content addressing, so a hand-edited bundle announces itself. Negative results,
so silence and absence do not render the same way. Two timestamps, so the system
cannot claim to have known something before it looked.

No network. The live provider is exercised by a test that skips without one,
matching how the live Granite test already works in this repo.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from evidence import (  # noqa: E402
    EvidenceSnapshot, FrozenSnapshotProvider, Incomplete, NegativeResult,
    SourceRecord,
)

REPO = os.path.join(os.path.dirname(__file__), "..")


def _snap(**over) -> EvidenceSnapshot:
    base = dict(
        subject="RCKT", as_of="2026-07-21", origin="frozen",
        records=[SourceRecord(
            source="sec.xbrl", locator="CIK 0001281895 companyfacts",
            published_at="2026-03-31", fetched_at="2026-07-21T00:00:00+00:00",
            payload={"cash": 49610000.0},
        )],
        negatives=[NegativeResult(
            source="clinicaltrials.v2", locator="query.spons=Nobody Inc",
            fetched_at="2026-07-21T00:00:00+00:00", reason="zero results",
        )],
        entity={"cik": "0001281895", "state": "exact"},
    )
    base.update(over)
    return EvidenceSnapshot(**base)


# ---------------------------------------------------------------------------
# Content addressing
# ---------------------------------------------------------------------------

def test_digest_is_stable_across_a_round_trip():
    """Serialise, reload, same digest. Without this, "we reran and nothing
    changed" is unfalsifiable."""
    a = _snap()
    b = EvidenceSnapshot.from_dict(json.loads(json.dumps(a.as_dict())))
    assert a.digest == b.digest


def test_an_edited_bundle_is_rejected_on_load():
    """A hand-edited snapshot must not load quietly.

    This is the evidence-layer counterpart of the ledger's hash chain: the file
    is the input to every displayed number, so an undetected edit to it is an
    undetected edit to the conclusion.
    """
    d = _snap().as_dict()
    d["records"][0]["payload"]["cash"] = 1.0
    with pytest.raises(ValueError, match="digest mismatch"):
        EvidenceSnapshot.from_dict(d)


def test_origin_does_not_change_the_digest():
    """The same evidence fetched live and replayed from a file must address the
    same. Otherwise the cross-mode equality claim is untestable by construction.
    """
    assert _snap(origin="live").digest == _snap(origin="frozen").digest


def test_fetch_time_does_change_the_digest():
    """Two runs at different times saw different evidence even when the values
    matched. Reproducibility here means "the same stored bundle always evaluates
    the same way", not "two live fetches are identical", which is false.
    """
    later = SourceRecord(
        source="sec.xbrl", locator="CIK 0001281895 companyfacts",
        published_at="2026-03-31", fetched_at="2026-07-22T00:00:00+00:00",
        payload={"cash": 49610000.0},
    )
    assert _snap(records=[later]).digest != _snap().digest


# ---------------------------------------------------------------------------
# Silence is not absence
# ---------------------------------------------------------------------------

def test_a_queried_source_that_found_nothing_is_distinguishable_from_an_unqueried_one():
    """The whole reason NegativeResult exists.

    `docs/LIMITS.md` forbids "no amendment exists" in favour of "none found in
    source S under procedure P at time T". That sentence is only writable if the
    snapshot records the query that came back empty, and both states render as
    an empty list if you store only what you found.
    """
    queried = _snap()
    assert queried.was_queried("clinicaltrials.v2")
    assert queried.by_source("clinicaltrials.v2") == []

    never = _snap(negatives=[])
    assert not never.was_queried("clinicaltrials.v2")
    assert never.by_source("clinicaltrials.v2") == []

    # Same empty result list; different facts about the world.
    assert queried.by_source("clinicaltrials.v2") == never.by_source("clinicaltrials.v2")
    assert queried.was_queried("clinicaltrials.v2") != never.was_queried("clinicaltrials.v2")


def test_incompleteness_is_a_state_not_an_empty_answer():
    """"found 2 of 7 trials" rendered as a short list is indistinguishable from
    "this company has 2 trials", and the second is a claim the system did not
    earn."""
    partial = _snap(missing=["clinicaltrials.versions:NCT06092034"])
    assert not partial.complete
    assert _snap().complete


def test_two_timestamps_never_one():
    """published_at is when the source says it became true; fetched_at is when
    this system looked. Collapsing them is how a monitor claims foreknowledge."""
    r = _snap().records[0]
    assert r.published_at == "2026-03-31"
    assert r.fetched_at.startswith("2026-07-21")
    assert r.published_at != r.fetched_at


# ---------------------------------------------------------------------------
# The frozen provider
# ---------------------------------------------------------------------------

def test_frozen_provider_round_trips_a_bundle(tmp_path):
    root = str(tmp_path)
    snap = _snap()
    with open(os.path.join(root, "RCKT.json"), "w") as f:
        json.dump(snap.as_dict(), f)

    got = FrozenSnapshotProvider(root).get("rckt")
    assert got.subject == "RCKT"
    assert got.origin == "frozen"
    assert got.digest == snap.digest


def test_frozen_provider_refuses_rather_than_returning_an_empty_bundle(tmp_path):
    """A missing bundle raises. Returning an empty snapshot would render as a
    company with no filings and no trials, which is a finding, not an error."""
    with pytest.raises(Incomplete):
        FrozenSnapshotProvider(str(tmp_path)).get("NOSUCH")


def test_live_provider_does_not_import_the_network_stack_at_module_load():
    """Importing the provider module must not pull in the engine.

    A frozen-only deployment loads this module and must stay credential-free and
    network-free; a module-level engine import would drag urllib and the API
    clients in behind it.
    """
    import importlib
    import evidence.provider as p
    importlib.reload(p)
    assert "engine" not in [m.split(".")[0] for m in dir(p)]
