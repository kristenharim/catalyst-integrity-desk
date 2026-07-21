# AGENTS.md — for IBM Bob

`CLAUDE.md` sits beside this file and is addressed to a different tool. Where the
two disagree about who builds what, this file governs your work.

**You are the primary development tool on this project.** The build prompts in
`docs/BOB_PROMPTS.md` are addressed to you. Claude verifies your output, runs the
kill gates, and writes docs; it does not execute those prompts.

Read `HANDOFF.md` first, then `docs/SPEC.md`. Read `docs/FINDINGS.md` before
touching any extraction code: it records eight failure modes found empirically,
and every one of them produces a wrong number rather than an error.

## What this is

Every biotech thesis rests on a date. The company has cash into X, the trial
reads out before X, therefore they are funded to the catalyst. The left side
comes from SEC filings. The right side comes from ClinicalTrials.gov, where the
sponsor sets it, can revise it whenever it likes, and nothing reconciles that
revision against the thesis that depended on the old date.

This project treats that as a contract and audits it.

## The rule everything follows

**Python computes. Granite judges prose. Humans decide.**

No model-produced number reaches the user. `_fabricated()` in the ported
`granite.py` enforces it and is ported byte for byte:

- Do **not** tighten it to ban all digits. That rejects correct output quoting a
  figure from the belief's own claim text, which is quotation, not invention.
- Do **not** loosen it. The rule is "a number absent from the input".

## Do not rewrite the engine

`engine/runway.py`, `engine/ctgov_history.py` and `engine/gap.py` predate you and
are verified against live SEC and ClinicalTrials.gov data. They are the reason
this project is credible. Run all three before and after any change:

```bash
python3 -m engine.runway
python3 -m engine.ctgov_history
python3 -m engine.gap
```

If a change of yours needs one of them modified, stop and say so rather than
editing it. That has been the right call every time it has come up.

## Four invariants

**Every displayed number traces to a named XBRL tag or a specific registry
version.** `Runway.provenance` exists for this. A figure that cannot name its
source does not get displayed.

**Unreliable rows are shown, never ranked, never silently dropped.** A screen
that hides its hard cases is worse than one that shows them. See
`Runway.reliable`. Arrowhead computes to a 1,116 month runway in this engine
because of a partnership upfront; the answer is to flag it, not to hide it.

**A lapsed completion date is never a catalyst.** You cannot run out of money
before an event that already happened. The binding catalyst is the nearest
registered primary completion still in the future. Lapsed dates are retained and
surfaced as date-integrity signals, which is the entire point of the project.

**Burn is a band, not a point.** One quarter containing a partnership upfront is
unrepresentative, and a single number would hide that.

## Language

Say **registered primary-completion expectation**, never "readout date". They
differ systematically by two to four months and the gap is always optimistic.

Say "we could not find", never "nobody has". A commercial screener and a
published revision dataset both exist and are cited in `docs/DEMO.md`. The claim
is the monitor, not a novel dataset and not a finding.

## Voice and commits

Comments say why, not what. No em dashes. Plain language, no filler. Commit as
kristenharim with plain messages, and never add AI attribution, `Co-Authored-By`,
or generated-with footers to any commit or file.

## Never touch

`~/projects/deliberate-risk-desk` is a separate working project and the fallback
demo for this submission. Phase 2 copies four files out of it, listed in
`docs/PORT.md`. Read those. Change nothing there, ever.

## Log what you build

Add a row to `docs/BOB_LOG.md` for each task, naming the tool. The README's Bob
section is written from that file rather than from memory, so a line that says
"by hand" must never be described later as yours.
