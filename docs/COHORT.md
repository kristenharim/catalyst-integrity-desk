# The random cohort, and what it does to the headline

Every rate this project has quoted ran on fourteen trials that happened to be cached, and
those fourteen were the trials of five companies picked by hand to illustrate the problem.
A sample selected on the outcome cannot produce a base rate. This is the first attempt at
one.

**Status: complete and frozen.** All 240 drawn trials are measured, 60 in every stratum,
none failed. Frozen as snapshot **`cohort-65fdf1f71b1d`** on 2026-07-22. Every number below
is a statement about that snapshot and nothing else, and the id is content-addressed, so
changing one measured row changes it.

## The correction history, which is the reason to trust the numbers

Three corrections, all of them to figures this file had already published, all shipped in
place rather than quietly restated. They belong at the top rather than in a footnote,
because a measurement's error history is the only evidence available that anyone was
actually checking.

**One: n was inflated by 29%.** A revision of this file reported n=169. It was 131 distinct
trials. The store is append-only and resumable, a background pass and a manual merge
appended concurrently, and 49 trials were counted twice. Every rate computed from the
inflated n was slightly wrong. `load_results()` now deduplicates on read, the store is
compacted to one row per trial with the superseded rows archived, and a test fails if any
shipped module reads the store directly. The inflation was invisible in exactly the way
that matters: more rows reads as more data, never as a bug, and it moved the headline in
the flattering direction.

**Two: the contingency rate was overstated about 3.5x**, reported as "roughly a quarter"
from a convenience sample and measured at 7.1% of INDUSTRY transitions here. Detailed
below, because it changes a product decision rather than a number.

**Three: an overcorrection was retracted.** An audit of the slip figures treated any
endpoint reword as a scope change and concluded that five of seven trials had unsupported
figures. That was wrong in a way that mattered: an endpoint is free prose, an exact string
comparison cannot tell a reword from a redefinition, and a guard the subject can defeat by
editing prose is not a guard. The three-state classification in `docs/LIMITS.md` replaced it.

**And the two smaller ones from closing this study.** The report printed a pooled
all-strata section on every run, against a rule this file already stated, for as long as the
rule had existed; it is gone and `stats()` now refuses to compute one. And two NIH trials
had stored a `JSONDecodeError` instead of a measurement, because of the non-atomic cache
write recorded in `docs/LIMITS.md`. Both were recovered once that was fixed at the source,
which is what closed NIH from 58 to 60.

## The frame, which is the denominator

Interventional studies, phases 2 / 2-3 / 3, with a registered primary completion date,
first posted between 2016-01-01 and 2023-12-31, stratified by lead-sponsor class, seed
20260722.

The end date is deliberate: a trial first posted in 2024 has had too little time to
accumulate a revision history, and including it would bias every duration downward. The
enumeration is capped at 3,000 per stratum, so within a stratum the draw is uniform over
the registry's own ordering rather than over the whole stratum, which is a real limitation
and not a rounding one.

## Results, complete, from snapshot `cohort-65fdf1f71b1d`

| Stratum | n | Carried a dead date | Dead-date days p50 / p90 / max | Transitions | Contingent | Refused | of which scope | superseded | unreadable |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| INDUSTRY | 60 | **80.0%** | **240** / 996 / 2104 | 126 | 7.1% | 39.7% | 34.1% | 5.6% | **0%** |
| NIH | 60 | **80.0%** | **567** / 1589 / 2716 | 181 | 5.0% | 34.8% | 25.4% | 9.4% | **0%** |
| OTHER_GOV | 60 | 53.3% | 222 / 686 / 2556 | 48 | 2.1% | 25.0% | 22.9% | 2.1% | **0%** |
| OTHER | 60 | 61.7% | 270 / 874 / 1929 | 91 | 3.3% | 33.0% | 24.2% | 8.8% | **0%** |

There is deliberately no ALL row. See below.

**What moved from the last published version, and what did not.** INDUSTRY did not move at
all: same n, same 80.0%, same 240 / 996 / 2104. It was already complete at 60 when those
figures were published, so finishing the draw could not touch it, and that is the stratum
the headline rests on.

NIH moved, because it went from 57 measured to 60. Its frequency went 80.7% to 80.0%, its
median dead-date stretch 580 days to 567, its superseded share 9.8% to 9.4%. Small, and
still a correction: the previous figures described 57 trials and were published as though
they described the stratum.

OTHER_GOV and OTHER moved a great deal, from n=6 each to n=60, and their earlier figures
should be treated as having said nothing. They were labelled badly under-measured at the
time and they were.

## The strata differ, so every rate stays labelled

On the complete draw, NIH and INDUSTRY sponsors carry a dead date at the *same* frequency,
80.0% each, to three significant figures, and NIH carries it **2.4 times as long**: median
567 days against 240. The frequencies converging as both strata filled out is the more
striking version of the result, not a weaker one. Whatever produces this is not specific to
commercial sponsors.

Duration is where they separate, and they separate by more than a factor of two. So the
80.0% figure is written as an INDUSTRY number everywhere it appears, and **no all-strata
average exists anywhere in this project**. Two populations that differ this much on duration
cannot be pooled into one "sponsors do this" claim without describing a population that does
not exist.

That rule was stated here and violated in the code: `report()` printed a pooled ALL section
on every run for as long as the rule had existed, and nobody noticed because the section
looked like a summary. It is gone, and `stats()` now raises on any stratum name outside the
four, so the pooled figure cannot be computed rather than merely not printed. The two
government and academic strata are reported because they are the contrast that says whether
this is a property of commercial sponsors, and on this evidence it is not.

## The refusal bundle is resolved in every stratum, and the hole was empty

An earlier version of this file flagged "refused, 39.6%" as uninterpretable, because it
mixed a finding about the sponsor (a count changed) with a gap in our own data (a dimension
was unreadable). Those are different things and one number cannot carry both. Recording the
reason per transition settles it, and it is now settled for all four strata rather than one:

| Stratum | transitions | scope changed | superseded | **unreadable** |
|---|---:|---:|---:|---:|
| INDUSTRY | 126 | 34.1% | 5.6% | **0.0%** |
| NIH | 181 | 25.4% | 9.4% | **0.0%** |
| OTHER_GOV | 48 | 22.9% | 2.1% | **0.0%** |
| OTHER | 91 | 24.2% | 8.8% | **0.0%** |

**Zero unreadable, everywhere.** Every refusal is a real event in the record: either a count
or enumeration genuinely changed, or the commitment was withdrawn or terminated. The bundle
was not corrupted; it was correct and unlabelled.

Worth stating plainly, because a check that comes back clean is evidence too, and the honest
outcome of looking for a hole is sometimes that there is not one. It also retires the last
hedge: INDUSTRY's 39.7% was published as an upper bound pending this re-measure, and it
turns out to have been the real figure all along.

`freeze()` refuses to cut a snapshot while any stratum still has refusals measured before
the split, so this cannot regress into a published upper bound wearing a measurement's
clothes.

## Two things this contradicts

### Carrying a dead date is normal, not anomalous

**80.0% of industry-sponsored trials in this sample carried an already-passed registered
completion date at some point**, with a median stretch of 240 days.

Rocket's 677 days sits at the **85th percentile** of the 188 industry stretches in the
snapshot. It is not an outlier. It is a long but ordinary instance of something four in five
sponsors do.

This is the most important result here and it cuts against how this project has been
presented. The README opens on 677 days as though it were remarkable. On this evidence the
remarkable part is not that Rocket did it; it is that **nobody reconciles any of it,
across an entire registry, as a matter of course**. That is a better claim and a bigger
one, but it is a different claim, and the framing has to change to match.

What survives unchanged: the reconciliation failure. A thesis anchored to a date nobody
re-reads is broken whether or not the sponsor was unusual in letting the date lapse. What
does not survive: any suggestion that a carried dead date singles a company out.

### The contingency rate was overstated by roughly 3.5x

Measured on the convenience sample, 7 of 29 substantive transitions were contingent on
prose alone, and I reported "roughly a quarter". On the complete cohort it is **7.1% of
INDUSTRY transitions**, 9 of 126, and 5.0% of NIH transitions, 9 of 181. Stated per stratum
rather than pooled, like everything else here.

That materially changes the product question from the last round. An adjudication queue at
25% would need staffing; at 7% it is a small, occasional task. The expert-rationing design
is right, and the load it has to ration is much lighter than the convenience sample
implied.

## The innocence check: is there a boring explanation?

Before "nobody reconciles this" goes anywhere external, the dull hypothesis has to be
ruled out. If sponsors batch their registry updates annually, a median lapse of 240 days
is an artifact of update cadence and not of anyone ignoring anything.

It is not. **42 CFR 11.64(a)(1)(ii)** sets a field-specific deadline for exactly this
field:

> "Primary Completion Date must be updated not later than 30 calendar days after the
> clinical trial reaches its actual primary completion date."

Thirty days. The observed industry median is 240 days, eight times the window, and the
p90 of 996 days is about thirty-three times it. Whatever explains the distribution, it is
not an annual update cycle, because the rule for this element is not annual.

**What that does and does not license, precisely.** The rule concerns updating the date to
*actual* once a trial reaches its actual primary completion. What is observed here is a
registered *estimated* date that passed and stayed standing. Those overlap but are not the
same event: a trial that did not complete on its estimated date owes a revision, and a
trial that did owes an update to actual, but this data does not say which happened. So:

- The batching explanation is ruled out as a *complete* explanation of the distribution.
- No individual stretch is called a breach, because that would need to know whether the
  trial actually completed on the registered date, and it is not in this dataset.
- The duty can be *named*, which is what `orchestrator/lexicon.py` requires before any
  statement touching disclosure obligations is allowed at all.

The 30-day window is therefore used as a reference line on a distribution, not as a test
any trial passes or fails. `research/sponsor_profile.py` renders it that way and says so
in the output.

## What this does not license

No claim about outcomes. The cohort measures registry behaviour and nothing else: it does
not know which of these trials succeeded, which sponsors raised money, or what any of it
predicted. There is no outcome variable in this dataset at all, so no statement about what
a dead date implies can be supported from it, and `orchestrator/lexicon.py` rejects one.

## Next, in order

The first three items on this list are done, and are left visible rather than deleted
because what a study planned to do next is part of its record.

1. ~~Finish the draw.~~ Done. 240 of 240, 60 per stratum, none failed.
2. ~~Record the refusal reason per transition.~~ Done, in all four strata. Zero unreadable
   everywhere.
3. ~~Re-percentile the Rocket case against the completed distribution.~~ Done: the 85th
   percentile of 188 industry stretches, stated as such rather than as an anomaly.

What is genuinely still open:

4. **The enumeration cap is a real limitation.** The frame is capped at 3,000 per stratum,
   so within a stratum the draw is uniform over the registry's own ordering rather than over
   the whole stratum. This is recorded in the snapshot's frame block and it is not a
   rounding issue.
5. **Nothing here is a time series.** Every rate is measured as of one look at the registry.
   Whether dead-date duration is getting longer or shorter is a different study and this one
   cannot speak to it.
6. **No outcome variable exists**, so the question everyone asks next, whether any of this
   predicts anything, cannot be answered from this dataset at all. See below.
