# The random cohort, and what it does to the headline

Every rate this project has quoted ran on fourteen trials that happened to be cached, and
those fourteen were the trials of five companies picked by hand to illustrate the problem.
A sample selected on the outcome cannot produce a base rate. This is the first attempt at
one.

**Status: partial and resumable.** 169 trials measured of 240 drawn, NIH complete, INDUSTRY
at 62 and awaiting a re-measure. The draw is seeded and stored, so the remainder continues
rather than restarting.

## The frame, which is the denominator

Interventional studies, phases 2 / 2-3 / 3, with a registered primary completion date,
first posted between 2016-01-01 and 2023-12-31, stratified by lead-sponsor class, seed
20260722.

The end date is deliberate: a trial first posted in 2024 has had too little time to
accumulate a revision history, and including it would bias every duration downward. The
enumeration is capped at 3,000 per stratum, so within a stratum the draw is uniform over
the registry's own ordering rather than over the whole stratum, which is a real limitation
and not a rounding one.

## Results

| Stratum | n | Carried a dead date | Dead-date days p50 / p90 / max | Transitions | Contingent | Refused | of which scope | unreadable |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| INDUSTRY | 62 | **80.6%** | **246** / 1018 / 2104 | 130 | 6.9% | 40.0% | not yet split | not yet split |
| NIH | 95 | 82.1% | **619** / 1595 / 2716 | 295 | 6.1% | 35.9% | 25.4% | **0%** |
| OTHER_GOV | 6 | 50.0% | 504 / 606 / 686 | 5 | 0% | 0% | 0% | 0% |
| OTHER | 6 | 50.0% | 323 / 535 / 555 | 6 | 0% | 50.0% | not yet split | not yet split |

## The strata differ, so every rate stays labelled

NIH sponsors carry a dead date about as *often* as industry ones (82.1% against 80.6%) and
roughly **two and a half times as long**: median 619 days against 246.

That is why the 80.6% figure is written as an INDUSTRY number everywhere it appears, and
why an all-strata average would be actively misleading. Two populations that differ this
much on duration should not be pooled into one "sponsors do this" claim, and pooling them
was the sampling bias worth avoiding rather than a completeness detail.

## The refusal bundle is resolved, and the hole was empty

The previous version of this file flagged "refused, 39.6%" as uninterpretable because it
mixed a finding about the sponsor (a count changed) with a gap in our own data (a dimension
was unreadable). Recording the reason per transition settles it, at least for the stratum
that has been re-measured:

    NIH, 295 transitions:   scope changed 25.4%   superseded 10.5%   unreadable 0.0%

**Zero unreadable.** Every refusal is a real event in the record: either a count or
enumeration genuinely changed, or the commitment was withdrawn or terminated. The bundle
was not corrupted; it was correct and unlabelled. Worth stating plainly, because a check
that comes back clean is evidence too, and the honest outcome of looking for a hole is
sometimes that there is not one.

INDUSTRY still shows "measured before the split" and its 40.0% remains an upper bound until
those 62 trials are re-measured. Same command, already running.

## Two things this contradicts

### Carrying a dead date is normal, not anomalous

**80.6% of industry-sponsored trials in this sample carried an already-passed registered
completion date at some point**, with a median stretch of 246 days.

Rocket's 677 days sits somewhere around the 75th to 80th percentile of that distribution.
It is not an outlier. It is an ordinary-to-long instance of something four in five
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
prose alone, and I reported "roughly a quarter". In the random cohort it is **6.7%**, 11
of 164.

That materially changes the product question from the last round. An adjudication queue at
25% would need staffing; at 7% it is a small, occasional task. The expert-rationing design
is right, and the load it has to ration is much lighter than the convenience sample
implied.

## The innocence check: is there a boring explanation?

Before "nobody reconciles this" goes anywhere external, the dull hypothesis has to be
ruled out. If sponsors batch their registry updates annually, a median lapse of 246 days
is an artifact of update cadence and not of anyone ignoring anything.

It is not. **42 CFR 11.64(a)(1)(ii)** sets a field-specific deadline for exactly this
field:

> "Primary Completion Date must be updated not later than 30 calendar days after the
> clinical trial reaches its actual primary completion date."

Thirty days. The observed median stretch is 246, roughly eight times the window, and the
p90 of 1,018 days is about thirty-four times it. Whatever explains the distribution, it is
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

1. Finish the draw. 155 of 240 remain; NIH and OTHER_GOV are badly under-measured because
   their trials carry far more versions and the run is fetch-bound.
2. Record the refusal reason per transition, so scope revisions and unestablishable
   continuity stop being one number.
3. Re-percentile the Rocket case against the completed distribution and state where it
   actually falls, in the README, instead of implying it is exceptional.
