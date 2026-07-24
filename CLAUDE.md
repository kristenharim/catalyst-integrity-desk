# CLAUDE.md

Rules for any Claude session in this repo. These are standing constraints, not
suggestions, and they hold whether or not anyone invokes anything.

Read `README.md` first for the current state, then `docs/STATUS.md`. Read
`docs/FINDINGS.md` before writing extraction code. `HANDOFF.md` describes the pre-Bob
repo and is kept as a record only. Do not plan work from it.

## Your role: you may build, and every build is logged as yours

This project is an entry in the IBM AI Builders Challenge, which requires **IBM Bob as
the primary development tool** and a README section describing that use. Bob's build is
already on the record: twelve logged tasks and nine session transcripts in
`docs/bob-sessions/`. Counted from the rows tagged `IBM Bob` in `docs/BOB_LOG.md` and the
files in that directory, which `tests/test_claim_integrity.py` re-counts on every run, so
this line cannot go stale again. That requirement is met by work already done, so you are
no longer restricted to verification.

You may write new code, including in areas Bob built. You still own kill gates,
acceptance criteria, adversarial verification, docs, and prior-art checks.

**The prompts in `docs/BOB_PROMPTS.md` are addressed to Bob, not to you.** They are a
historical record of how Bob was driven. Do not execute them as if you were Bob.

**The logging requirement is not optional and does not change.** Every line you write
goes into `docs/BOB_LOG.md` as hand work, attributed to Claude Code, on the same commit
that writes the code. The README's Bob section is written from that file, not from
memory, and it currently states that other AI tools "wrote no product code". The moment
you write product code, that sentence is updated in the same pass. A submission that
describes its own authorship inaccurately is a worse failure than one that admits a
second tool touched it.

## Never break these

**Python computes, Granite judges prose, humans decide.** No model-produced number
reaches the user. `_quantitative()` in `orchestrator/granite.py` enforces it: Granite
prose carries no quantity of any kind, and a response containing one is discarded whole
in favour of the deterministic stub. Never partially sanitise.

**Do not loosen this back to "a number absent from the input".** That was the rule here
until 2026-07-23 and this file used to defend it. An audit retired it: it authorised any
magnitude whose digits appeared anywhere in the analyst's own free-text claim, so a thesis
reading "Phase 3 readiness across 12 sites" licensed "3 months" and "12 months". The
intermediate `Quantity(value, unit, sign)` binding did not fix that and never established
semantic-field binding; that claim is withdrawn. `docs/LIMITS.md` carries the full
reasoning and the exact residual. Every displayed figure is rendered by Python and Jinja
from a named field, which is what makes a non-quantitative model affordable.

**Every displayed number traces to a named XBRL tag or a specific registry version.**
`Runway.provenance` exists for this. Do not add a figure that cannot name its source.

**Unreliable rows are shown, never ranked and never silently dropped.** A screen that
hides its hard cases is worse than one that shows them. See `Runway.reliable`.

**A lapsed completion date is never a catalyst.** You cannot run out of money before an
event that already happened. The binding catalyst is the nearest registered primary
completion still in the future. Lapsed dates are retained and surfaced as date-integrity
signals on the company, which is the point of the project, not discarded and not treated
as a funding target.

## Claim discipline

The engine modules in `engine/` are verified against live APIs. Do not rewrite them,
clean them up, or change their interfaces. Run all three before and after any change:

```
python3 -m engine.runway
python3 -m engine.ctgov_history
python3 -m engine.gap
```

Say **registered primary-completion expectation**, never "readout date". They differ by a
systematic two to four months.

Whether cash-constrained sponsors revise dates differently than solvent ones is an
**untested hypothesis** with adjacent published work (Guenzel & Liu, RFS 2026). Say "we
could not find", never "nobody has". The screen is a commercial product and the revision
panel is a published dataset; both are cited in `docs/DEMO.md` and named voluntarily.

The claim is **the monitor**. Not a novel dataset, not a finding.

## Do not touch

`~/projects/deliberate-risk-desk` is a separate working project and the fallback demo.
Read it, copy the four files named in `docs/PORT.md` at Phase 2, and change nothing in it.

## Voice

Plain. No em dashes, no filler, no AI attribution in commits or docs. Commit as
kristenharim with plain messages.
