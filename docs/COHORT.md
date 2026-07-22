# The random cohort, and what it does to the headline

Every rate this project has quoted ran on fourteen trials that happened to be cached, and
those fourteen were the trials of five companies picked by hand to illustrate the problem.
A sample selected on the outcome cannot produce a base rate. This is the first attempt at
one.

**Status: complete and frozen.** Every drawn trial is measured and none failed.

<!-- generated: provenance -->
Every cohort figure in the claim documents is emitted from a field of snapshot
`cohort-5b03269658b8` by `research/render_writeup.py`: 240 trials, 60 in each of four
sponsor strata, all measured, point prevalence as of 2026-07-22. The prose around them
contains no numerals and a test regenerates every generated block and fails on a one-byte
difference.
<!-- /generated -->

Every figure below is a statement about that snapshot and nothing else, and the id is
content-addressed, so changing one measured row changes it.

## The correction history, which is the reason to trust the numbers

Three corrections, all of them to figures this file had already published, all shipped in
place rather than quietly restated. They belong at the top rather than in a footnote,
because a measurement's error history is the only evidence available that anyone was
actually checking.

**One: n was inflated, in the flattering direction.** The store is written by appending and
the run is resumable, so a background pass and a manual merge appended concurrently, and a
large minority of rows were duplicates. A figure published mid-run as a trial count was a row
count. This correction was itself first published wrong, pairing a row count from one moment
with a distinct count from a later one; the magnitudes are in the git history and in
`docs/LIMITS.md`, which is not a generated document. `load_results()` now deduplicates on
read, the store is
compacted to one row per trial with the superseded rows archived, and a test fails if any
shipped module reads the store directly. The inflation was invisible in exactly the way
that matters: more rows reads as more data, never as a bug, and it moved the headline in
the flattering direction.

**Two: the contingency rate was overstated several times over**, reported as "roughly a
quarter" from a convenience sample and measured far lower on the cohort. Detailed below,
because it changes a product decision rather than a number.

**Three: an overcorrection was retracted.** An audit of the slip figures treated any
endpoint reword as a scope change and concluded that most of the audited trials had
unsupported figures. That was wrong in a way that mattered: an endpoint is free prose, an exact string
comparison cannot tell a reword from a redefinition, and a guard the subject can defeat by
editing prose is not a guard. The three-state classification in `docs/LIMITS.md` replaced it.

**And the two smaller ones from closing this study.** The report printed a pooled
all-strata section on every run, against a rule this file already stated, for as long as the
rule had existed; it is gone and `stats()` now refuses to compute one. And two NIH trials
had stored a `JSONDecodeError` instead of a measurement, because of the non-atomic cache
write recorded in `docs/LIMITS.md`. Both were recovered once that was fixed at the source,
which is what restored the NIH stratum to its full size.

## The frame, which is the denominator

Interventional studies, with a registered primary completion date, stratified by
lead-sponsor class. The full frame, its phases, its date range, the seed and the enumeration
cap are tabulated in `docs/WRITEUP.md`, which renders them from the snapshot's own frame
block.

The end date is deliberate: a trial first posted after the frame closes has had too little
time to build a revision history, and including it would bias every duration downward. The
enumeration cap means that within a stratum the draw is uniform over the registry's own
ordering rather than over the whole stratum, which is a real limitation and not a rounding
one.

## Secondary results: lapsed and subsequently filed again

<!-- generated: secondary_table -->
| Stratum | n | Carried a dead date | days p50 / p90 / max | Transitions | Contingent | Refused |
|---|---:|---:|---|---:|---:|---:|
| INDUSTRY | 60 | **80.0%** | **239.5** / 995.6 / 2,104 | 126 | 7.1% | 39.7% |
| NIH | 60 | **80.0%** | **567** / 1,588.8 / 2,716 | 181 | 5.0% | 34.8% |
| OTHER_GOV | 60 | **53.3%** | **222** / 686.4 / 2,556 | 48 | 2.1% | 25.0% |
| OTHER | 60 | **61.7%** | **270** / 873.5 / 1,929 | 91 | 3.3% | 33.0% |
<!-- /generated -->

There is deliberately no ALL row. **This table is the secondary measure**, kept because it
is what earlier revisions published and because a duration distribution over stretches is
still informative. It cannot see a sponsor that lapsed and then stopped filing, so it should
never be read as a frequency ranking between strata.

The primary figures are point prevalence and per-trial longest carry:

<!-- generated: primary_table -->
| Stratum | carrying an expired estimate now | invisible to the stretch measure | longest carry p50 | median versions |
|---|---:|---:|---:|---:|
| INDUSTRY | 5 of 60 (8.3%) | 4 | 390 | 9 |
| NIH | 0 of 60 (0.0%) | 0 | 590 | 106.5 |
| OTHER_GOV | 27 of 60 (45.0%) | 20 | 336 | 2 |
| OTHER | 19 of 60 (31.7%) | 15 | 439 | 4 |
<!-- /generated -->

The two frequency measures reverse the ordering, with industry and NIH tied at the top of
the stretch measure, and the ordering is
filing frequency.

## Resolved: the measure changed, and the primary figures with it

An adversarial review on 2026-07-22 found two measurement problems, both confirmed against the
store. The owner resolved them the same day and the study was re-measured and re-frozen
under the id named above.

1. **A stretch needs a later filing to close it**, so a sponsor that lets a date lapse and
   then files nothing scored as never having carried one. **Point prevalence is now the
   primary frequency measure**: a trial whose most recent registered date is in the past and
   still typed as an estimate. The stretch-based rate is retained and labelled "lapsed and
   subsequently filed again". The silent population is a first-class result: the two measures
   reverse the ordering, with industry and NIH tied on the stretch
   measure, and most of OTHER_GOV's currently-expired trials are invisible to the stretch
   measure. The counts are in `docs/WRITEUP.md`.
2. **A stretch is counted per filing, not per lapse.** **Per-trial longest carry is now the
   primary duration measure**; the per-stretch figures are a labelled sensitivity at a
   higher ratio. The per-stretch ratio is removed as a headline everywhere, and the
   no-pooling rule is re-justified on three independent differences rather than on it.

A third finding came out of fixing the first: the initial point-prevalence pass read the
ESTIMATED/ACTUAL type from a helper that did not return it, so the filter never fired and
every completed trial that had correctly recorded its actual completion date was counted as
carrying a lapsed one. For one revision it published an order-of-magnitude larger
prevalence for industry and a near-universal one for OTHER_GOV. The corrected figures are
rendered in `docs/WRITEUP.md`. See `docs/LIMITS.md`.

## The finding the study now leads on: reconciliation tracks filing frequency

<!-- generated: headline -->
In a random sample of 240 phase 2 / 2-3 / 3 trials, **this study cannot separate
reconciliation from filing frequency, and most trials carrying an expired commitment have
never reconciled a lapsed date** — 4 of 5 in INDUSTRY, 20 of 27 in OTHER_GOV, 15 of 19 in
OTHER, dates that have stood a median of 1,101.5 days in INDUSTRY, 2,288.5 days in
OTHER_GOV, 1,178 days in OTHER. NIH sponsors file a median of 106.5 registry versions per
trial and have **zero** trials currently carrying an expired completion date. Non-U.S.
government and institutional sponsors, the OTHER_GOV stratum, file a median of 2, and **27
of 29 of their still-open commitments have already expired**. The ordering is monotone in
filing frequency across all four strata, which is an association across four points rather
than a tested relationship.
<!-- /generated -->

The revision-level split below is the supporting mechanism among sponsors that are still
filing, not the headline.

### The revision-level mechanism

Registered dates are revised, and **when** and **to what** they are revised is the distinction:

<!-- generated: mechanism_table -->
| Stratum | dated revisions | after a lapse | of those, recorded ACTUAL | **estimate to estimate** | rate (end-of-month to first) |
|---|---:|---:|---:|---:|---:|
| INDUSTRY | 126 | 66 | 33 | 33 | 22.2% to 26.2% |
| NIH | 181 | 57 | 20 | 37 | 19.9% to 20.4% |
| OTHER_GOV | 48 | 32 | 14 | 18 | 33.3% to 37.5% |
| OTHER | 91 | 49 | 14 | 35 | 35.2% to 38.5% |
<!-- /generated -->

A revision filed after the old date lapsed is not automatically a failure to reconcile. If it
records an ACTUAL completion date it is the update 42 CFR 11.64(a)(1)(ii) requires, and for a
late trial it necessarily arrives after the estimate expired. Half the industry after-lapse
revisions are that. The claim is the remainder: an expired estimate replaced by another
estimate.

An earlier revision of this file published the undifferentiated after-lapse rate as the
headline. That was wrong, and it was wrong in a way arithmetic could not catch: the regulation quoted two
sections above to argue the behaviour was unlicensed is what licenses half the numerator.

**The measure is conditional on a revision existing.** A trial that lapses and never files
again is in neither column, and in the government stratum that is more than half of them.
Read it with point prevalence, which is the measure that sees them.

## The strata differ, so every rate stays labelled

The strata differ on three independent things, and the no-pooling rule rests on all three
rather than on any single ratio:

1. **Reconciliation behaviour**, the estimate-to-estimate rate.
2. **Point prevalence**, which is near half in OTHER_GOV and zero in NIH.
3. **Filing frequency**, which orders both and is not separable from either here.

Every one of those figures is rendered in `docs/WRITEUP.md` from the snapshot rather than
retyped here. On the primary duration measure NIH carries longer than industry; on the
per-stretch sensitivity the same comparison reads higher still, and the gap between the two
is the filing-frequency artifact rather than a finding. The per-stretch ratio is no longer
used as a headline anywhere.

Duration is where they separate. So the ever-carried figure is written as a per-stratum
number everywhere it appears, and **no all-strata average exists anywhere in this
project**. Two populations that differ this much on duration
cannot be pooled into one "sponsors do this" claim without describing a population that does
not exist.

That rule was stated here and violated in the code: `report()` printed a pooled ALL section
on every run for as long as the rule had existed, and nobody noticed because the section
looked like a summary. It is gone, and `stats()` now raises on any stratum name outside the
four, so the pooled figure cannot be computed rather than merely not printed. The two
non-industry public and institutional strata, OTHER_GOV and OTHER, are reported because they
are the contrast that says whether this is a property of commercial sponsors, and on this
evidence it is not.

## The refusal bundle is resolved in every stratum, and the hole was empty

An earlier version of this file flagged its refusal rate as uninterpretable, because it
mixed a finding about the sponsor (a count changed) with a gap in our own data (a dimension
was unreadable). Those are different things and one number cannot carry both. Recording the
reason per transition settles it, and it is now settled for all four strata rather than one:

<!-- generated: refusal_table -->
| Stratum | transitions | scope changed | superseded | **unreadable** |
|---|---:|---:|---:|---:|
| INDUSTRY | 126 | 34.1% | 5.6% | **0.0%** |
| NIH | 181 | 25.4% | 9.4% | **0.0%** |
| OTHER_GOV | 48 | 22.9% | 2.1% | **0.0%** |
| OTHER | 91 | 24.2% | 8.8% | **0.0%** |
<!-- /generated -->

**Zero unreadable, everywhere.** Every refusal is a real event in the record: either a count
or enumeration genuinely changed, or the commitment was withdrawn or terminated. The bundle
was not corrupted; it was correct and unlabelled.

Worth stating plainly, because a check that comes back clean is evidence too, and the honest
outcome of looking for a hole is sometimes that there is not one. It also retires the last
hedge: the INDUSTRY refusal rate was published as an upper bound pending this re-measure,
and it turns out to have been the real figure all along.

`freeze()` refuses to cut a snapshot while any stratum still has refusals measured before
the split, so this cannot regress into a published upper bound wearing a measurement's
clothes.

## Two things this contradicts

### Carrying a dead date is normal, not anomalous

**Four in five industry-sponsored trials in this sample carried an already-passed registered
completion date at some point.** The rate, the median stretch and the anchor case's
percentile against it are all rendered in `docs/WRITEUP.md`. It is not an outlier. It is a
long but ordinary instance of something four in five sponsors do.

This is the most important result here and it cuts against how this project has been
presented. The README opens on the anchor case as though it were remarkable. On this evidence the
remarkable part is not that Rocket did it; it is that **nobody reconciles any of it,
across an entire registry, as a matter of course**. That is a better claim and a bigger
one, but it is a different claim, and the framing has to change to match.

What survives unchanged: the reconciliation failure. A thesis anchored to a date nobody
re-reads is broken whether or not the sponsor was unusual in letting the date lapse. What
does not survive: any suggestion that a carried dead date singles a company out.

### The contingency rate was overstated several times over

Measured on the convenience sample, roughly a quarter of substantive transitions were
contingent on prose alone. On the complete cohort it is a small single-digit share of
transitions in every stratum, rendered per stratum in `docs/WRITEUP.md` rather than pooled,
like everything else here.

That materially changes the product question from the last round. An adjudication queue at a
quarter of transitions would need staffing; at this rate it is a small, occasional task. The expert-rationing design
is right, and the load it has to ration is much lighter than the convenience sample
implied.

## The innocence check: is there a boring explanation?

Before "nobody reconciles this" goes anywhere external, the dull hypothesis has to be
ruled out. If sponsors batch their registry updates annually, a median lapse of months is
an artifact of update cadence and not of anyone ignoring anything.

It is not compliant, at least. **42 CFR 11.64(a)(1)(ii)** sets a field-specific deadline for
exactly this field:

> "Primary Completion Date must be updated not later than 30 calendar days after the
> clinical trial reaches its actual primary completion date."

Thirty days. The observed medians are many times that window, which is stated with the
figures in `docs/WRITEUP.md`. That is a statement about the duty and not a refutation of the
behaviour: a roughly annual housekeeping cycle is consistent with the durations observed
here, and naming the rule does not rule it out. The write-up's innocence check is where that
is worked through.

**The duty does not reach every stratum, and the write-up scopes it.** 42 CFR Part 11 is
U.S. law and binds applicable clinical trials, broadly those with a U.S. site or a
U.S.-regulated product. Industry and NIH are where it plausibly applies. OTHER_GOV as drawn
here is non-U.S. public bodies, not U.S. federal agencies, so the reference line is drawn
against industry and NIH and not extended to OTHER_GOV or OTHER; for those strata the registry
facts stand without the regulation. The undrawn FED stratum, where the duty applies most
directly, is the recorded follow-up. This is worked through in `docs/WRITEUP.md`.

**What that does and does not license, precisely.** The rule concerns updating the date to
*actual* once a trial reaches its actual primary completion. What is observed here is a
registered *estimated* date that passed and stayed standing. Those overlap but are not the
same event: a trial that did not complete on its estimated date owes a revision, and a
trial that did owes an update to actual, but this data does not say which happened. So:

- The batching explanation is **not** ruled out by the regulation, which is a statement about
  the duty and not about anyone's cadence. It *is* ruled out for the trials currently carrying
  an expired estimate, on duration alone: a yearly sweep does not leave a date standing for
  the medians those carriers show. It is not excluded for all of them, and the write-up gives
  the count that have been expired under a year and the shortest of them, for which a slow
  cycle and a non-reconciliation look alike. An earlier version of this file said the
  explanation was ruled out by the regulation alone, which does not follow.

<!-- generated: clustering_note -->
The clustering test in `docs/WRITEUP.md` reports both anniversary and control windows. The
control windows score at least as high in three of the four strata and lower by a single
interval in the fourth, so the test supports no conclusion about annual batching; the
earlier conclusions drawn from it are withdrawn as Correction 9 and Correction 10.
<!-- /generated -->
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

1. ~~Finish the draw.~~ Done. Every drawn trial measured, none failed.
2. ~~Record the refusal reason per transition.~~ Done, in all four strata. Zero unreadable
   everywhere.
3. ~~Re-percentile the Rocket case against the completed distribution.~~ Done, and the
   percentile is rendered from the snapshot rather than stated as an anomaly.

What is genuinely still open:

4. **The enumeration cap is a real limitation.** The frame is capped per stratum, so within
   a stratum the draw is uniform over the registry's own ordering rather than over the whole
   stratum. This is recorded in the snapshot's frame block and it is not a
   rounding issue.
5. **Nothing here is a time series.** Every rate is measured as of one look at the registry.
   Whether dead-date duration is getting longer or shorter is a different study and this one
   cannot speak to it.
6. **No outcome variable exists**, so the question everyone asks next, whether any of this
   predicts anything, cannot be answered from this dataset at all. See below.
