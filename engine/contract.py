"""Flatten a CatalystContract into the {metric_id: value} dict that scan_breaches
consumes.

The contract already computes everything; this module is the translation layer that
names each computed value with a stable metric_id so the ledger can address it.

Five metrics cover the funded-to-catalyst claim:

    gap_months           signed runway surplus at the registered readout date
                         (negative means the money runs out first)
    runway_months_low    conservative runway endpoint (higher-burn estimate)
    burn_ttm_annual      trailing-twelve-month burn, annualised, in dollars
    pcd_revisions        number of times the registered completion date moved
    max_days_expired     longest stretch the registry showed a date that had passed

The first two come from Runway; the third from Runway as well; the last two come from
TrialHistory. When history was not fetched (enrichment is optional), pcd_revisions and
max_days_expired are absent from the packet rather than zero — zero would look like "no
revisions ever recorded", which is a different claim.
"""
from __future__ import annotations

from engine.gap import CatalystContract


def to_packet(contract: CatalystContract) -> dict[str, float]:
    """Return the flat {metric_id: value} dict for one CatalystContract.

    Only computable values are included. Callers that need to detect a missing
    metric should check for key absence rather than a sentinel value.
    """
    r = contract.runway
    packet: dict[str, float] = {}

    gap = contract.gap_months
    if gap is not None:
        packet["gap_months"] = gap

    if r.months_low is not None:
        packet["runway_months_low"] = r.months_low

    # burn_ttm_annual is always present (compute_runway raises if no burn tag found).
    packet["burn_ttm_annual"] = r.burn_ttm_annual

    h = contract.history
    if h is not None:
        packet["pcd_revisions"] = float(len(h.revisions))
        packet["max_days_expired"] = float(h.max_days_expired)

    return packet


def demo() -> None:
    """Round-trip: build a contract, flatten it, confirm scan_breaches fires on a
    deliberately out-of-range gap.

    The live network calls are the same ones gap.demo() already makes — the cache
    covers them after the first run, so repeated runs are offline and instant.
    """
    from engine.gap import build
    from engine.ledger import BeliefCard, BeliefLedger, scan_breaches
    import tempfile, os

    # --- build a real contract ---
    from engine.runway import ticker_to_cik
    cik_map = ticker_to_cik()
    contract = None
    for ticker in ["RCKT", "NTLA", "SANA", "PRME"]:
        contract = build(ticker, cik_map)
        if contract is not None:
            break
    assert contract is not None, "no contract assembled"

    packet = to_packet(contract)

    # gap_months and runway_months_low must be present when computable.
    assert "burn_ttm_annual" in packet, "burn always present"
    if contract.gap_months is not None:
        assert "gap_months" in packet
        # Value must equal the contract's own property, to floating-point identity.
        assert packet["gap_months"] == contract.gap_months
    if contract.runway.months_low is not None:
        assert "runway_months_low" in packet
        assert packet["runway_months_low"] == contract.runway.months_low
    if contract.history is not None:
        assert "pcd_revisions" in packet
        assert "max_days_expired" in packet
        assert packet["pcd_revisions"] == len(contract.history.revisions)

    # All values must be plain floats (scan_breaches compares them with card thresholds).
    for k, v in packet.items():
        assert isinstance(v, float), f"{k}: expected float, got {type(v).__name__}"

    print(f"packet for {contract.runway.ticker}:")
    for k, v in sorted(packet.items()):
        print(f"  {k:<24} {v:>12.2f}")

    # --- breach round-trip ---
    # Seed a card whose approved range sits ABOVE the actual gap_months value so
    # that the packet triggers a breach deterministically, regardless of the live number.
    gap = packet.get("gap_months", -1.0)
    # Force an "under" breach: approve [gap + 5, gap + 20], then supply gap as the reading.
    approved_low = gap + 5.0
    approved_high = gap + 20.0

    card = BeliefCard(
        card_id="test:funded_to_catalyst",
        scope=f"company:{contract.runway.ticker}",
        claim="This company reaches its primary readout before runway exhaustion.",
        metric="gap_months",
        expected_low=approved_low,
        expected_high=approved_high,
        driver="SEC XBRL liquidity vs ClinicalTrials.gov registered PCD",
        confidence=4,
        source="engine.contract.demo",
        as_of=contract.runway.as_of,
    )

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        ledger_path = f.name
    try:
        ledger = BeliefLedger(ledger_path)
        ledger.create(card)
        assert ledger.verify(), "fresh ledger should verify"

        breaches = scan_breaches(ledger.current(), packet)
        assert len(breaches) == 1, f"expected exactly one breach, got {len(breaches)}"
        b = breaches[0]
        assert b.card_id == "test:funded_to_catalyst"
        assert b.metric == "gap_months"
        assert b.direction == "under"
        assert b.observed == gap
        assert b.expected_low == approved_low
    finally:
        os.unlink(ledger_path)

    print(f"\nbreach on gap_months = {gap:.2f} (approved floor {approved_low:.2f}): ok")
    print("ok")


if __name__ == "__main__":
    demo()
