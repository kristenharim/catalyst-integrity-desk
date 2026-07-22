# Conjecture: what this could be

The built thing is a monitor for one company. This is what the same idea supports if it
keeps going, ordered by how much has to be true for each rung to hold.

The discipline of the project applies to this file too. Nothing below is claimed as done,
and nothing is claimed as a finding.

## The insight the whole thing rests on

A registry entry is not an observation. It is a **claim, made by an interested party, that
can be revised at any time, where every revision is public and timestamped and nobody
diffs it.**

That sentence generalises well beyond biotech, and that is the interesting part.

Rocket is the demonstration because it is unarguable: a completion date sat expired on a
federal registry for 677 days, and the thesis that depended on it never moved. No
amendment was filed. The date simply arrived, and passed.

## Rung 0: the same monitor, driven by an analyst instead of by `TICKERS`

Before any of the rungs below, the thing has to be usable by someone who did not write
`TICKERS`. That is a product design rather than a research direction, so it lives in its
own file: `docs/WORKSPACE.md`. The short version is that the console is a frozen exhibit
by design, and the same engine can run live from a ticker without forking the arithmetic.

It is Rung 0 because it is the only rung that does not need a new idea, and because it
makes two queue states computable that one committed snapshot cannot support.

## Rung 1: the same monitor, more contracts

What it takes: the sponsor-to-issuer join, which is the real engineering tax. Names drift
across subsidiaries, punctuation and post-merger renames, and there is no CIK in the
registry. An alias table plus hand review of the largest names gets to a few hundred
companies.

What it buys: the monitoring queue stops being a demo and becomes a morning list. "Which
of my beliefs need attention today" is a job someone currently does badly or not at all.

Honest risk: at scale the burn-band flags stop being rare, and a screen that flags a third
of its rows has moved the problem rather than solved it.

## Rung 2: date-integrity as a published statistic

Every ingredient already exists. The engine computes, per trial, how long a sponsor
carried an already-expired completion date and how much notice each revision gave.

Aggregate that across the sector and you get a descriptive series nobody publishes: how
common expired-date carriage is, how long it typically persists, whether it clusters by
phase, sponsor size or time.

That is a dataset contribution, not a causal claim, and it is defensible precisely because
it stays descriptive. The prior-art slide in `docs/DEMO.md` already names who owns the
adjacent layers.

## Rung 3: the open question, done properly

Whether cash-constrained sponsors hold optimistic dates longer than solvent ones is stated
throughout this repo as untested, and it must stay that way until it is tested.

Doing it properly needs a within-firm design, because the naive cross-section is
confounded: low runway correlates with small, under-resourced companies that slip anyway.
Guenzel and Liu (RFS 2026) ran the opposite arrow with trial-site congestion as an
instrument, which is the strongest evidence that the measurement works at all.

If the answer is yes, the sentence is: **the registry is not a data source, it is a
disclosure channel with incentives.** That is a paper, not a product.

If the answer is no, that is publishable too, and it is the outcome to plan for.

## Rung 4: the pattern, moved off biotech

The machinery is domain-agnostic. A belief with a stated range, a deterministic recompute,
a model that judges prose but never produces a number, a human gate, and a hash-chained
record. Nothing in the governance layer knows what a clinical trial is.

Any domain where a self-reported public claim underwrites somebody's decision fits the
same shape: construction milestones in municipal bond disclosure, emissions targets in
sustainability reporting, delivery dates in defence procurement, covenant compliance in
credit agreements.

The constraint is not the software. It is finding a second domain where the registry is
public, versioned, timestamped, and load-bearing for a decision. Biotech is unusually good
on all four at once, which is why it is the demonstration.

## What would have to be built, in order

1. **An external anchor for the ledger.** Until the expected head hash lives somewhere the
   writer does not own, deletion is undetectable. See `docs/LIMITS.md`. This is the
   cheapest change with the largest effect on what can honestly be claimed.
2. **Per-element provenance binding.** Every figure carries the record and field it came
   from, so the test can assert exact formatter output rather than substring presence.
   This closes the display-drift hole that no current test catches.
3. **Reproducible builds.** The snapshot regenerates byte-identically from pinned inputs,
   so a hand edit is detectable and CI can enforce it.
4. **`as_of` threaded everywhere**, so lapsed-versus-future is a property of the data
   rather than of the day the code ran.
5. **Typed evidence spans** for anything quantitative in model output, which is the only
   version of the fabrication guard that survives a unit swap.

The first four are engineering with known shapes. The fifth is the genuinely hard one and
is where the interesting work is.

## The thing to protect

Every defect this project has had looked fine and kept the tests green. The habit that
caught all of them is one sentence: **what would still pass if this were broken, and have
I watched it fail?**

That habit is more transferable than the code. If any of the rungs above get built, it is
the part to carry forward.
