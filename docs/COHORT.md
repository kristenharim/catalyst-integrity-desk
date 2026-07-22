# The random cohort, and what it does to the headline

Every rate this project has quoted ran on fourteen trials that happened to be cached, and
those fourteen were the trials of five companies picked by hand to illustrate the problem.
A sample selected on the outcome cannot produce a base rate. This is the first attempt at
one.

**Status: incomplete and resumable.** 85 trials measured of 240 drawn. The draw is seeded
and stored, so the remainder continues rather than restarting. Reporting at n=85 rather
than waiting, because two of the results contradict things already stated in this repo and
leaving those standing while the run finishes would be the failure this project is about.

## The frame, which is the denominator

Interventional studies, phases 2 / 2-3 / 3, with a registered primary completion date,
first posted between 2016-01-01 and 2023-12-31, stratified by lead-sponsor class, seed
20260722.

The end date is deliberate: a trial first posted in 2024 has had too little time to
accumulate a revision history, and including it would bias every duration downward. The
enumeration is capped at 3,000 per stratum, so within a stratum the draw is uniform over
the registry's own ordering rather than over the whole stratum, which is a real limitation
and not a rounding one.

## Results at n=85

| Stratum | n | Carried a dead date | Dead-date days p50 / p90 / max | Transitions | Contingent | Refused |
|---|---:|---:|---|---:|---:|---:|
| INDUSTRY | 62 | **80.6%** | 246 / 1018 / 2104 | 130 | 6.9% | 40.0% |
| NIH | 11 | 81.8% | 1561 / 1616 / 1672 | 23 | 8.7% | 43.5% |
| OTHER_GOV | 6 | 50.0% | 504 / 606 / 686 | 5 | 0% | 0% |
| OTHER | 6 | 50.0% | 323 / 535 / 555 | 6 | 0% | 50.0% |
| **ALL** | **85** | **76.5%** | 365 / 1602 / 2104 | 164 | **6.7%** | **39.6%** |

INDUSTRY is the population the product is about and the only stratum with an n worth
reading. The others are listed for contrast and are too small to compare.

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

## A defect in this report, named rather than fixed

**"Refused" bundles two different things.** A transition is refused when a count or
enumeration changed, and also when continuity could not be established because a dimension
was unreadable in both versions. The first is a finding about the sponsor; the second is a
gap in the data. Reporting 39.6% as one number conflates them, which is exactly the sort
of thing this project exists to refuse.

A diagnostic pass over the cached versions shows enrolment as the dominant identifiable
driver of genuine scope revisions. Separating the two properly requires re-running the
cohort with the refusal reason recorded per transition, which is the next change to
`research/cohort.py` and is not done here.

Until it is, read 39.6% as an upper bound on genuine scope revisions, not as a measurement
of them.

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
