# Handoff: superseded, kept as a record

> **Status as of 2026-07-21: this document is out of date and describes the pre-Bob
> state of the repo.** Everything it calls unbuilt has since been built. The governance
> port, redline loop, console, ledger and research panel all exist and are on disk.
> For the current state read `README.md`, then `docs/STATUS.md` and `docs/BOB_LOG.md`.
> This file is retained because it records the original framing and the eight-gotcha
> warning, not because its task list is live. Do not plan work from it.

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
revise it at any time, and the revision is not reconciled against the thesis that
depended on the old date.

The Catalyst Integrity Desk treats that as a contract: this company has capital to reach
this readout by this date. Python computes both sides from filed tags and registry
records, with no model near a number. Granite reads the analyst's written rationale and
reports which stated assumption a new filing or amendment breaks. The analyst approves,
and the decision hash chains into a tamper evident ledger.

So the desk carries a third column: how the sponsor has behaved toward its own date.

## How to frame it, exactly

**"An auditable monitor for when a portfolio's cash-to-catalyst assumption breaks."**

Not "a novel dataset" and not "a new finding". Both of those lose under one question:

- The catalyst screen is a shipping commercial product. BiopharmaWatch filters 11,000+
  readouts by cash runway and burn across 949 companies, including a trial-change field.
- The revision panel is a published dataset: 4.3M per-version rows across ~583k trials.
- The finance-and-trial-timing link is adjacent published work (Guenzel & Liu, RFS 2026).

See `docs/FINDINGS.md` section 2. What survives is the *monitor*: a contract that is
recomputed deterministically, breached visibly, judged against its own written rationale,
and changed only by a human whose decision is hash chained. That is a real thing to build
and an honest thing to claim.

## What must not be claimed

That cash constrained sponsors revise their readout dates differently than solvent ones.
**Hypothesis, untested, and adjacent work already exists.** Say "we could not find" and
never "nobody has".

State the identification problem out loud: low runway correlates with small, under
resourced companies that slip more anyway, which pushes the opposite way from the
strategic story. A judge who hears an honest "here is the panel, here is why the causal
claim is hard" scores it above a confident result that dies to one question.

Also: say **registered primary-completion expectation**, not readout date. They are not
the same thing and the difference is a systematic 2 to 4 month optimistic bias.
