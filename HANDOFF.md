# Handoff: start here

This repo is a de-risked starting point, not a finished project. Three engine modules
are built and verified against live SEC and ClinicalTrials.gov data. Everything else is
specified but unbuilt, and that is deliberate: the unbuilt parts are what IBM Bob should
build, because the challenge requires Bob to be the primary development tool.

## What to do with the IBM chat you already have open

Pause it. Do not redirect it mid thread.

That thread's context is saturated with the portfolio risk framing, so a correction
inside it will keep drifting back to belief cards about VaR. A pivot this size wants a
clean context whose first input is a written spec.

Also: do not touch `~/projects/deliberate-risk-desk`. It runs, it talks to live Granite,
and it is the fallback demo if this build stalls. Its value is that it exists.

**Open a new chat and paste this as the first message:**

> I am building the Catalyst Integrity Desk for the IBM AI Builders Challenge, with IBM
> Bob as the primary development tool. The repo is at `~/projects/catalyst-integrity-desk`.
>
> Read these first, in order: `HANDOFF.md`, `docs/SPEC.md`, `docs/FINDINGS.md`,
> `docs/PORT.md`. `docs/FINDINGS.md` contains eight data gotchas that were found
> empirically and each one will cost you a day if you rediscover it.
>
> The three modules in `engine/` are verified working. Do not rewrite them. Run
> `python3 -m engine.runway`, `python3 -m engine.ctgov_history`, and `python3 -m engine.gap`
> to confirm before you change anything.
>
> Start with Phase 1 in `docs/SPEC.md`. Use `docs/BOB_PROMPTS.md` for the sequenced
> build prompts.

## What is verified working, right now

Run these. They hit live APIs and assert on real data.

```
python3 -m engine.runway          # cash runway from SEC XBRL, 12 clinical-stage names
python3 -m engine.ctgov_history   # registry revision history for one trial
python3 -m engine.gap             # the join: funding gap + date integrity
```

Measured on 2026-07-21:

- `NCT04613596` (Mirati): 95 protocol versions, 6 of which moved the primary
  completion date, net slip +2,193 days.
- `NCT04248439` (Rocket Pharmaceuticals): **carried a completion date that had already
  passed for 677 days** before correcting it.
- 12 of 12 clinical-stage, pre-revenue names produced rankable runway bands. Sana
  8.1-9.2 months, Prime Medicine 9.5-10.4, Rocket 9.5-9.6.

## The one paragraph version of the idea

Every biotech thesis rests on a date: the company has cash into X, the trial reads out
before X, therefore they are funded to the catalyst. The left side comes from SEC
filings. The right side comes from ClinicalTrials.gov, where the sponsor sets it, can
revise it at any time, and nobody diffs the revisions.

The Catalyst Integrity Desk treats that as a contract: this company has capital to reach
this readout by this date. Python computes both sides from filed tags and registry
records, with no model near a number. Granite reads the analyst's written rationale and
reports which stated assumption a new filing or amendment breaks. The analyst approves,
and the decision hash chains into a tamper evident ledger.

And because the revision history is free and nobody has assembled it, the desk carries a
third column no product has: how the sponsor has behaved toward its own date.

## What must not be claimed

The research hypothesis is that cash constrained sponsors revise their registered
readout dates differently than solvent ones. **That is a hypothesis. It has not been
tested.** The panel needed to test it is what this repo assembles.

Present the dataset and the mechanism. State the identification problem out loud
(low runway correlates with small, under resourced companies that slip more anyway,
which pushes the opposite way from the strategic story). A judge who hears an honest
"here is the panel, here is why the causal claim is hard" will score it above a
confident result that does not survive one question.
