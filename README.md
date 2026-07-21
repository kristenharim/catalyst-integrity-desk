# Catalyst Integrity Desk

Can a clinical-stage biotech fund itself to its own next readout, and has it been honest
about when that readout is?

The first half is arithmetic on filed numbers. The second half is the part nobody
checks: the readout date lives on ClinicalTrials.gov, the sponsor sets it, the sponsor
can revise it at any time, and every revision is public, timestamped, and undiffed.

```
funding gap = runway exhaustion date - registered primary completion date
```

Python computes both sides from filed tags and registry records. Granite reads the
analyst's written rationale and reports which stated assumption a change breaks, and it
never produces a number. The analyst decides, and the decision hash chains into a tamper
evident ledger.

## Status

Engine built and verified against live APIs. Governance layer, console, and panel are
specified and unbuilt, by design: see `HANDOFF.md`.

```
python3 -m engine.runway          # cash runway from SEC XBRL, as a band, with provenance
python3 -m engine.ctgov_history   # registry revision history for one trial
python3 -m engine.gap             # the join: funding gap plus date integrity
```

No dependencies beyond the standard library and `curl`.

## What it found on the first real run

Rocket Pharmaceuticals, trial `NCT04248439`: in April 2024 the sponsor revised a primary
completion date of June 2022. **That date had been expired for 677 days while sitting on
the public registry.**

Mirati's `NCT04613596`: 95 protocol versions, 6 of which moved the completion date, net
slip of 2,193 days, including one +1,317 day move reversed two months later.

Across 12 clinical-stage, pre-revenue companies, all 12 produced rankable runway bands:
Sana 8.1 to 9.2 months, Prime Medicine 9.5 to 10.4, Rocket 9.5 to 9.6.

## Design rules

**Python computes, Granite judges prose, humans decide.** Enforced by scanning model
output for figures absent from its input, not asserted in a readme.

**Every number names its source.** `Runway.provenance` records which XBRL tag each
component resolved through, because the tags are not uniform across filers and a
numerator you cannot identify is not auditable.

**Burn is a band.** A partnership upfront or a Phase 3 ramp makes any single quarter
unrepresentative. Rows whose burn estimate is unreliable stay visible with the reason
attached and never carry a rank. A screen that silently drops its hard cases is worse
than one that shows them.

**Say what is a hypothesis.** Whether cash constrained sponsors revise their dates
differently than solvent ones is an open question, not a result. This repo assembles the
panel that would answer it.

## Layout

```
engine/runway.py          cash runway from SEC XBRL company facts
engine/ctgov_history.py   registry revision history, notice and expiry metrics
engine/gap.py             the catalyst contract join
docs/SPEC.md              four phase build spec
docs/FINDINGS.md          eight data gotchas, prior art, attack surface
docs/PORT.md              which governance modules to port and what changes
docs/BOB_PROMPTS.md       sequenced build prompts
docs/DEMO.md              three minute script
HANDOFF.md                start here
```

Read `docs/FINDINGS.md` before writing extraction code. Each gotcha in it produces a
wrong number rather than an error, and one of them caused a 49x error that looked
exactly like a company about to run out of money.
