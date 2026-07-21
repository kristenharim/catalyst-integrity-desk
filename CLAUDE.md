# CLAUDE.md

Rules for any Claude session in this repo. These are standing constraints, not
suggestions, and they hold whether or not anyone invokes anything.

Read `HANDOFF.md` first. Then `docs/FINDINGS.md` before writing extraction code.

## Your role: verify, do not build

This project is an entry in the IBM AI Builders Challenge, which requires **IBM Bob as
the primary development tool** and a README section describing that use. That is a
compliance requirement with no partial credit, so the division of labour is fixed:

| Bob owns | You own |
|---|---|
| new builds (the prompts in `docs/BOB_PROMPTS.md`) | kill gates and acceptance criteria |
| the governance port, redline loop, console, panel | adversarial verification of Bob's output |
| | defect fixes in pre-Bob engine code |
| | docs, `docs/BOB_LOG.md`, prior-art checks |

**The prompts in `docs/BOB_PROMPTS.md` are addressed to Bob, not to you.** Do not execute
them. If asked to, say so and stop.

If you find yourself writing substantial new code because it would be faster, stop and
say so. That tradeoff is Kristen's, not yours. Small fixes to code that predates Bob are
yours and do not need asking.

Log what Bob built versus what was changed by hand, in `docs/BOB_LOG.md`, as it happens.
The README's Bob section is written from that file, not from memory.

## Never break these

**Python computes, Granite judges prose, humans decide.** No model-produced number
reaches the user. `_fabricated()` in the ported `granite.py` enforces it and is ported
byte for byte. Do not tighten it to ban all digits, which rejects correct output quoting
a figure from a belief's own claim text. Do not loosen it. The rule is "a number absent
from the input".

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
