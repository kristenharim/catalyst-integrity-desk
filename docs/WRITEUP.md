# Most trials carrying an expired commitment have never reconciled a lapsed date

**This document is generated.** Every cohort figure in it is emitted from a field of
snapshot `cohort-5b03269658b8`, frozen 2026-07-22, with point prevalence computed as of that
same date: 240 drawn trials, 60 in each of four sponsor strata, all measured. The id is
content-addressed over the measured rows and the frame together, so it cannot be re-cut
under the same name.

The prose you are reading is a template that carries no numerals of its own, and a test
enforces that over the whole template rather than over selected lines. The exception is a
small table of verbatim quotations from sources outside this study, checked separately so a
measurement cannot launder through it. Every other figure is filled in from a named field by
`research/render_writeup.py`. A test regenerates this file and fails if a single byte
differs, so a figure cannot be edited here at all: it can only be changed by changing the
field it renders. **No figure in this document was copied from the snapshot by a person.**

That closes the class of defect five review rounds kept finding and it does not close
everything. Four residuals, named because the guard this replaced gave a narrower account of
itself than was true. A cell bound to the wrong field renders wrongly and regenerates
identically. A figure small enough to pass as an ordinary constant can be typed into the
generator. A count spelled in words is invisible to a rule about digits, and one shipped in
three documents on the pass that wrote this. And a sentence with no number in it can still
be false; nothing here checks the arguments.

The draw is uniform over the first 3,000 trials in the registry's own ordering within each
stratum, not over the whole stratum. "Randomly drawn" throughout means that and not more.

## The finding: this study cannot separate reconciliation from filing frequency

Most trials carrying an expired commitment have never reconciled a lapsed date: 4 of 5 in
INDUSTRY, 20 of 27 in OTHER_GOV, 15 of 19 in OTHER. The measure that was going to be this
study's headline is built from observed corrections and therefore cannot see them.

**The measured condition is stronger than "has not filed lately", and rather than paraphrase
it this document quotes the code that applies it.** A paraphrase is a second implementation
that no test runs, and the paraphrase this replaces was wrong: it said "no correction since
this date lapsed", which is true of essentially every carrier by construction, since a
correction would have moved the date.

From `research.cohort.silent_carrier`:

```python
def silent_carrier(row: dict, as_of: date) -> bool:
    """Carrying an expired estimate, and invisible to the stretch measure.

    `carried_until_corrected()` emits a stretch only where a later filing
    arrived while an already-passed date was standing, so a trial with no
    stretch at all has never had a lapsed date ended by a later correction at
    any point in its history. Not once.
    """
    return carrying_expired_now(row, as_of) and not row["dead_date_stretches"]
```

and the predicate it composes with, `research.cohort.carrying_expired_now`:

```python
def carrying_expired_now(row: dict, as_of: date) -> bool:
    """The trial's most recent registered primary completion date is in the past
    and is still typed as an estimate.

    An ACTUAL date in the past is the reconciled case, a completed trial
    recording when it completed, and does not count.
    """
    p = _parse_date(row.get("last_pcd"))
    return bool(p is not None and p < as_of
                and (row.get("last_pcd_type") or "").upper() != "ACTUAL")
```

So the condition is: the most recent registered primary completion date is in the past, is
still typed as an estimate, and `research.backtest.carried_until_corrected` has never
emitted a stretch for this trial at any point in its history. Not once. A past date typed
ACTUAL is the reconciled case, a completed trial recording when it completed, and does not
count.

Those dates have stood a long time. The median is 1,101.5 days in INDUSTRY, 2,288.5 days in
OTHER_GOV, 1,178 days in OTHER, which is 3.0 to 6.3 years, and the shortest anywhere is 203
days.

**These are not trials that kept filing while one field went stale.** Not one of the 39
carrying an expired estimate that no correction has ever ended has filed anything at all
since its date passed, and that is by construction rather than by observation: the condition
quoted above is that no stretch was ever emitted, and a stretch is emitted for any filing
arriving over an already-passed date. They are not busy filers in general either. 18 of them
have never filed a second registry version of any kind, and the median across the whole life
of one of these trials is 2 registry versions against a median of 106.5 for an NIH trial.
The busiest filed 10, and an earlier draft used that one trial as an illustration of the
population; it is withdrawn as Correction 11 below.

A trial is **carrying an expired commitment** when the predicate above holds. Measured as of
2026-07-22, against two denominators, beside how often each stratum files at all:

| Stratum | carrying an expired estimate | of trials whose commitment is still open | invisible to the stretch measure | median registry versions | median date revisions |
|---|---:|---:|---:|---:|---:|
| INDUSTRY | 5 of 60 (8.3%) | 5 of 15 (33.3%) | 4 of 5 | 9 | 2 |
| NIH | 0 of 60 (0.0%) | 0 of 18 (0.0%) | 0 of 0 | 106.5 | 3 |
| OTHER_GOV | 27 of 60 (45.0%) | 27 of 29 (93.1%) | 20 of 27 | 2 | 0 |
| OTHER | 19 of 60 (31.7%) | 19 of 28 (67.9%) | 15 of 19 | 4 | 1 |

Both denominators are reported because they answer different questions. Out of all 60 trials
the rate is small and should be: most trials in this frame have finished and recorded an
actual completion date, which is the system working. But 45 of 60 industry trials are in
that state and cannot be carrying an expired estimate by construction. Among those whose
commitment is still open, one in three industry trials is already past its stated date, and
for OTHER_GOV it is 27 of 29. **4 of 5 industry trials currently carrying an expired
estimate are invisible to the measure this project started with**, which is the industry
instance of the finding below.

That is a handful of events. No interval is computed anywhere in this document, and the
conditional column's denominators are smaller still: one trial is 6.7 percentage points at
n=15 and 5.6 percentage points at n=18, so the zero for NIH is 0 of 18.

NIH sponsors file a median of 106.5 registry versions per trial and have **no** trial
currently carrying an expired estimate. OTHER_GOV sponsors file a median of 2 and nearly all
of their open commitments are expired. The ordering is monotone in filing frequency across
all four strata. That is an association across four points, not a tested mechanism, and
nothing here separates filing frequency from any other property that varies alongside it.

**A registry version is any record edit, not a completion-date edit**, and the 53.2x spread
between NIH and OTHER_GOV is mostly edits to fields nobody here is discussing. On date
changes alone the medians are 3 for NIH, 2 for industry, 1 for OTHER and **0** for
OTHER_GOV: the same ordering over a far smaller range. The count excludes the initial
registration, which the underlying `n_pcd_revisions` field includes; an earlier draft of
this column read that field directly and so credited every trial with a revision it had
never made. The last column above carries both so the spread is not read as fifty times more
date maintenance.

**The converse does not hold, and the study can say so.** Among trials that never revised a
date, the share carrying an expired estimate is 4 of 8 for INDUSTRY, 0 of 5 for NIH, 18 of
32 for OTHER_GOV, 15 of 22 for OTHER. Going quiet is common among the trials carrying an
expired commitment; it does not follow that a quiet trial is carrying one.

### The measure that misses them, and why it inverts

The stretch measure, reported in full further down, records a lapse only when a *later
filing* arrives while an already-passed date is standing. A sponsor that lets a date expire
and then files nothing produces no stretch at all and scores as never having carried one.
The silence is exactly what makes it invisible: 20 of 27 of OTHER_GOV's currently expired
trials are invisible that way and 15 of 19 of OTHER's, and 32 of 60 OTHER_GOV trials never
revised a date at all.

The two measures therefore reverse the ordering, with industry and NIH tied at the top of
the first:

| Stratum | ever carried, and filed again | carrying one now | median versions |
|---|---:|---:|---:|
| INDUSTRY | 80.0% | 8.3% | 9 |
| NIH | 80.0% | 0.0% | 106.5 |
| OTHER | 61.7% | 31.7% | 4 |
| OTHER_GOV | 53.3% | 45.0% | 2 |

Read alone, the stretch measure would have said government and academic sponsors lapse and
file again least often. They are the most likely to be carrying an expired date now. A
measure that needs its subject to keep talking cannot see the subject that stops, and any
frequency statistic built from observed corrections has the same blind spot.

## The mechanism, among sponsors that are still filing

That trials run late is documented. Shadbolt et al., JAMA Network Open 2023 find roughly one
in five randomised trials complete on time, with a median delay of 12.2 months. Any measure
of "the registered date passed" is close to a restatement of something already known, and a
study that stops there has measured lateness with extra steps.

The distinction that separates them is **when** the date was revised and **to what**. Every
revision carries how much time the old date still had when it was moved:

- **Revised while the date was still in the future.** The registered date had not yet passed
  when it was replaced. The trial may be very late and the record still never showed a date
  that had expired.
- **Revised after the date had already passed, recording an ACTUAL completion.** For a trial
  that ran late this necessarily lands after the earlier estimate expired, and it is the
  update 42 CFR 11.64(a)(1)(ii) requires within 30 days of actual completion. It is the
  reconciliation event, not its absence.
- **Revised after the date had already passed, with another ESTIMATE.** The sponsor let the
  date pass and then pushed it, with no completion recorded. This is the behaviour this
  project claims to measure.

None of the three describes what anyone knew or intended, which a registry diff cannot show.

| Stratum | dated revisions | after a lapse | of those, recorded ACTUAL | **estimate to estimate** | rate |
|---|---:|---:|---:|---:|---:|
| INDUSTRY | 126 | 66 | 33 | 33 | 26.2% |
| NIH | 181 | 57 | 20 | 37 | 20.4% |
| OTHER_GOV | 48 | 32 | 14 | 18 | 37.5% |
| OTHER | 91 | 49 | 14 | 35 | 38.5% |

At the trial level, the share of trials that revised a date at all and did this at least
once is 24 of 52 for INDUSTRY, 21 of 55 for NIH, 16 of 28 for OTHER_GOV, 21 of 38 for OTHER.

So among sponsors that are still filing, 26.2% of industry revisions are something delay
does not account for. An earlier draft reported the undivided after-lapse rate here, which
counted the mandated update-to-actual filing as a failure to reconcile; that is retracted as
Correction 8.

**This measure is conditional on a revision existing**, which is the same blind spot as the
stretch measure, one level up: a trial that lapses and never files again contributes to
neither the numerator nor the denominator. The excluded set is every trial that never
changed a date at all, which is 8 of 60 for INDUSTRY, 32 of 60 for OTHER_GOV; the subset of
it that matters here, trials carrying an expired estimate and never having revised one, is 4
of 60 for INDUSTRY, 18 of 60 for OTHER_GOV. It is why this section supports the finding
above rather than standing on its own.

Two conventions that move figures by a little, stated because the document already discloses
one that moves nothing. A revision filed on the exact day the date came due has zero days
remaining and is counted as prospective rather than as a lapse; that is 2 of 446 dated
revisions across all four strata and it moves no published figure. And a registry date given
to the month rather than to the day is resolved to the first of that month, so every
days-since-expiry figure for such a trial is inflated by up to the length of a month. That
is 19 of 51 trials carrying an expired estimate, so the medians in the finding section and
in the innocence check are all slightly high, by less than a month each and by less than
that in aggregate.

## What is being measured, and what is not

This is a measurement of **reconciliation**, not of performance.

The system observes whether a public, dated, self-authored commitment was kept, revised,
superseded, or left standing after its date passed without anyone reconciling it. It does
not observe whether the underlying trial was going well, whether the sponsor was in
difficulty, or whether the original date was ever achievable. There is no outcome variable
in this dataset at all.

That boundary has a partial mechanical guard. `orchestrator/lexicon.py` is a list of banned
phrasings checked in CI against every rendered page and every claim-bearing document
including this one, and a sentence matching one of those patterns does not survive the
build. It is a list of phrasings, so it catches the ones someone thought of. It is a floor
under the prose, not the boundary itself.

Two vocabulary points that follow from the same discipline:

- This is the **registered primary-completion expectation**, which is last patient last
  visit for the primary endpoint. Topline results follow it by roughly two to four months, a
  working figure used throughout this project and not one measured here.
- A stretch is **carried**. That a date passed and stayed standing is a fact about the
  record. Whether anyone intended anything by it is not observable from a registry diff, and
  nothing here asserts that they did.

## The frame, which is the denominator

Every rate this project published before this study came from fourteen trials that happened
to be cached, belonging to five companies chosen by hand to illustrate the problem. A sample
selected on the outcome cannot produce a base rate. This is the replacement.

|  |  |
|---|---|
| Study type | Interventional |
| Phase | 2 / 2-3 / 3 |
| Requires | A registered primary completion date |
| First posted | 2016-01-01 to 2023-12-31 |
| Stratified by | Lead sponsor class |
| Drawn | 60 per stratum, seed 20260722 |
| Measured | 240 of 240, after recovering two trials lost to a cache defect (Correction 5) |
| Point prevalence as of | 2026-07-22, pinned in the snapshot, never read from the clock |

The end date is deliberate. A trial first posted in 2024 has had too little time to
accumulate a revision history, and including it would bias every duration downward.

**A limitation, and the frame size is not known:** enumeration is capped at 3,000 trials per
stratum, so within a stratum the draw is uniform over the registry's own ordering rather
than over the whole stratum. What fraction of each stratum that cap represents was not
recorded, so how much this matters is unmeasured rather than small.

## Duration

**Primary: one observation per trial, its longest carry.** A trial that lapsed once
contributes one number regardless of how often its sponsor happened to file afterwards.

| Stratum | trials with a carry | median | p90 | max |
|---|---:|---:|---:|---:|
| INDUSTRY | 48 | **390** | 1,384.4 | 2,104 |
| NIH | 48 | **590** | 1,617.4 | 2,716 |
| OTHER_GOV | 32 | **336** | 726.9 | 2,556 |
| OTHER | 37 | **439** | 998.4 | 1,929 |

Days. NIH against industry at the median: **1.5x**.

**Every duration in this section is measured on completed spells**, meaning lapses that were
eventually ended by a later filing. Excluding open lapses biases every duration
**downward**, and the exclusion is unequal across strata: no NIH trial is excluded on this
ground, against 4 INDUSTRY, 20 OTHER_GOV, 15 OTHER. The cross-stratum ratio is therefore
between differently censored distributions and should be read with that. The open cases,
which are the ones a monitor would actually alert on, contribute no duration at all: this
study counts them and does not say how long they run or where the replacement date lands.
Recorded in `docs/PARKING.md` as the next measurement rather than estimated here.

**Sensitivity, per stretch.** A stretch is emitted per consecutive version pair, so one
lapse spanning many filings contributes many overlapping rows measuring the same expiry to
successively later endpoints, and a frequent filer contributes more of them. One NIH trial,
`NCT02931474`, with 97 versions and 2 date changes, contributes 91 of that stratum's 493
stretches.

| Stratum | stretches | median | p90 | max | ever carried |
|---|---:|---:|---:|---:|---:|
| INDUSTRY | 188 | 239.5 | 995.6 | 2,104 | 80.0% |
| NIH | 493 | 567 | 1,588.8 | 2,716 | 80.0% |
| OTHER_GOV | 50 | 222 | 686.4 | 2,556 | 53.3% |
| OTHER | 96 | 270 | 873.5 | 1,929 | 61.7% |

Percentiles are linearly interpolated and printed to a tenth of a day wherever the
interpolation lands between two days, rather than rounded. Half-integer medians print in
full for the same reason: a rounding format rounds half to even, which drops the half in one
direction and adds one in the other, and both have shipped from this document.

On this unit the NIH against industry ratio is **2.4x** rather than 1.5x. **The gap between
the two is the filing-frequency artifact, not a finding**, which is why the per-trial unit
is primary and this one is labelled as a sensitivity.

### Why the strata are not pooled

Three independent differences, none of which rests on the duration ratio alone:

- **Reconciliation behaviour.** 26.2% of industry revisions replace an already-expired
  estimate, against 20.4% of NIH and 37.5% of OTHER_GOV ones.
- **Point prevalence.** 45.0% of OTHER_GOV trials are carrying an expired estimate now
  against 8.3% of industry trials and none of the NIH ones.
- **Filing frequency**, which varies alongside both and is not separable from either here,
  at a median of 2 registry versions per trial against 106.5. It does not order the
  reconciliation rate: OTHER files more than OTHER_GOV and has the higher
  estimate-to-estimate rate, 38.5% against 37.5%.

`stats()` raises rather than returning a pooled rate, so the figure cannot be computed by
accident.

## Comparability, and why three totals rather than two

A date moving between two registry versions is a delay only if both dates describe the same
commitment. Every transition is classified into three states and refusals carry their
reason:

| Stratum | Transitions | Contingent | Refused | scope changed | superseded | **unreadable** |
|---|---:|---:|---:|---:|---:|---:|
| INDUSTRY | 126 | 7.1% | 39.7% | 34.1% | 5.6% | **0.0%** |
| NIH | 181 | 5.0% | 34.8% | 25.4% | 9.4% | **0.0%** |
| OTHER_GOV | 48 | 2.1% | 25.0% | 22.9% | 2.1% | **0.0%** |
| OTHER | 91 | 3.3% | 33.0% | 24.2% | 8.8% | **0.0%** |

**Contingent** means comparability turns on prose alone: the sponsor reworded a free-text
endpoint in the same filing that moved the date, and no string comparison can tell a reword
from a redefinition. These get bounds and never verdicts. **Refused** means a count or
enumeration changed, which no wording explains away, or the commitment was withdrawn.

The unreadable column is the share of refusals caused by a gap in *our* data rather than by
an event in the sponsor's record, and it is zero in every stratum. The hole this check was
built to find is empty. It was defined narrowly and says nothing about gaps of other shapes;
the adversarial review of this document found two of those.

## The innocence check

If sponsors simply batch their registry housekeeping annually, a median lapse of months is
an artifact of update cadence rather than of anything being ignored.

Annual batching would not be compliant, because the rule for this element is not annual. 42
CFR 11.64(a)(1)(ii):

> "Primary Completion Date must be updated not later than 30 calendar days after the
> clinical trial reaches its actual primary completion date."

**That is a statement about the duty, not a refutation of the behaviour**, and the section
is titled as a check rather than a result for that reason. A roughly annual housekeeping
cycle is consistent with the durations observed here.

An earlier draft claimed the revision timing settled this, on the grounds that a majority of
industry revisions arrive after the date they replace has already expired. That argument
does not work, for two separate reasons. The majority figure counted the mandated
update-to-actual filing and is retracted as Correction 8. And the surviving
estimate-to-estimate subset does not rebut batching either: a sponsor on a yearly cycle
would replace an expired estimate with a fresh one at the next pass, which is exactly what
that subset counts. **A cadence hypothesis is not refuted by evidence that the cadence is
slow.**

**The check ends in three places, and only one of them is resolved.**

*One, the currently-carrying population, excluded everywhere on duration.* Measured on that
population rather than on the silent subset of it, the median date has stood 720 days in
INDUSTRY, 2,028 days in OTHER_GOV, 1,178 days in OTHER. A yearly sweep does not leave a date
standing that long. It is not excluded for all of them: 6 of 51 carriers have been expired
under a year, the shortest 2 days, and for those a slow cycle and a non-reconciliation look
alike.

*Two, industry filing timing: **unresolved**, and this leg was published as resolved.* An
earlier draft read industry's anniversary windows against an even-spread null, found them at
or below it, and called that the absence of an annual signal. The control windows below
retire that null, and a conclusion cannot be drawn from a statistic the same section calls
uninterpretable in three strata and interpretable in the fourth because it came out the
convenient way. Industry does show the table's largest gap between the two window sets, 17
of 126 at the anniversaries against 34 of 126 at the controls, but the control centres sit
at shorter lags than the anniversaries and industry's median interval falls between them, so
that gap is the same distributional artifact. It is also the wrong population: 4 of 5 of the
industry trials carrying an expired estimate have never changed a date, so they contribute
no interval at all.

*Three, closed-spell durations in the other strata: **unresolved**.* An earlier draft
concluded that the batching explanation stood for OTHER and OTHER_GOV because their
intervals bunch near anniversaries. Their closed-spell durations are neither excluded nor
explained by anything measured here.

Both withdrawals are Correction 10. The test is published below because it was run, not
because it settles anything.

### The clustering test, and the control windows that undercut it

The test asks how many gaps between consecutive date-changing filings fall within 45 days of
a one, two or three year multiple, at 365 / 730 / 1,095 days. An interval is the gap between
the submit dates of two consecutive versions that changed the completion date; a trial's
first interval runs from its initial registration. The null is the share of each stratum's
observed interval range covered by the three windows, which is what an even spread would
land in.

**The control windows are the same test run at 182 / 547 / 912 days**, half a year off each
anniversary and the same width. They are not anniversaries, and a yearly housekeeping cycle
gives no reason to expect anything at them. Both window sets have the same total width and
both fall inside every stratum's observed interval range, so they share one null and the
comparison between the two ratios reduces to a comparison of the two counts.

| Stratum | intervals | median interval | within the anniversary windows | within the control windows | even-spread null | anniversary ratio | control ratio |
|---|---:|---:|---:|---:|---:|---:|---:|
| INDUSTRY | 126 | 289 | 17 of 126 (13.5%) | 34 of 126 (27.0%) | 15.3% | **0.88x** | **1.77x** |
| NIH | 181 | 287 | 35 of 181 (19.3%) | 34 of 181 (18.8%) | 12.8% | **1.51x** | **1.47x** |
| OTHER_GOV | 48 | 529 | 10 of 48 (20.8%) | 10 of 48 (20.8%) | 9.8% | **2.13x** | **2.13x** |
| OTHER | 91 | 372 | 18 of 91 (19.8%) | 22 of 91 (24.2%) | 10.8% | **1.83x** | **2.23x** |

**The control windows score no lower than the anniversary windows in three of the four
strata, and lower by a few hundredths in the fourth**, anniversary against control: INDUSTRY
0.88x against 1.77x, NIH 1.51x against 1.47x, OTHER_GOV 2.13x against 2.13x, OTHER 1.83x
against 2.23x. Windows that no cadence hypothesis singles out score about the same as the
ones it does. So the ratio measures the shape of the interval distribution, which is
concentrated at short lags, against a null that assumes an even spread and is therefore
wrong. It does not measure anniversaries. Both the earlier "no annual bunching" conclusion
drawn from industry alone and the later "the explanation stands for OTHER and OTHER_GOV" are
withdrawn, as Correction 9 and Correction 10.

**Nothing survives for any stratum, including the one the earlier draft cleared.**
Industry's anniversary windows hold about half what its control windows do, 17 of 126 at the
anniversaries against 34 of 126 at the controls, which is the largest separation in the
table and is the only direction that would have supported an innocence claim. It is not read
as one here: the control centres sit at systematically shorter lags than the anniversaries,
industry's median interval of 289 days falls between the two, and a distribution
concentrated at short lags produces exactly that deficit with no cadence involved. The test
discriminates or it does not, and this study cannot say which.

**Two further limits, which were already stated and still hold.** The windows stop at three
years while intervals run past the longest anniversary window, so long gaps sit in the
denominator and can never score. And a trial that never changed its date contributes no
interval at all, so the carriers this section is about supply almost none of what is
measured. The test describes the cadence of sponsors that file. It cannot describe the
cadence of sponsors that do not.

**What the regulation does and does not license, precisely.** The rule concerns updating the
date to *actual* once a trial reaches its actual primary completion. Much of what is
observed here is a registered *estimate* that passed and stayed standing. Those overlap but
are not the same event, and this dataset cannot say which happened for any given trial. The
window quoted above is therefore a **reference line on a distribution**, not a test any
trial passes or fails, and no stretch here is called a breach. Naming the duty is what the
claims lexicon requires before any statement touching disclosure obligations is permitted at
all. Naming it is not alleging it was breached.

## The case this project was built around

This project opened on a single company that had published a completion date 677 days after
it passed, sitting on a public registry the whole time. The trial is `NCT04248439`, the date
expired 2022-06-01 and was corrected 2024-04-08. The cohort places that case: the **85th
percentile** of the industry stretches, and the **67th percentile** of the industry trials
counted one observation each. Long, and inside the distribution rather than outside it.

Both figures are the empirical share of observations at or below that duration; 159 of 188
is 84.6%. No observation equals it exactly, so "at or below" versus "below" makes no
difference, and the trial ranks 32 of 48 on the per-trial unit. This is a different
convention from the interpolated percentiles in the tables above, so the two cannot be read
off each other.

The finding was never that one sponsor was unusual. It is that in this frame a lapsed date
routinely stands for months before anything ends it, and that a quarter of industry
revisions replace a date that had already expired. Whether re-reading that field changes any
decision or outcome is not measured here and is not in this dataset.

## Methods, including everything that went wrong

The correction history is the record of what was caught, offered as that and nothing more.
It is incomplete by construction: later review rounds added more corrections after this
section was first written, and two of them are larger than anything that was in it.

**Measured with the product's own code.** The cohort calls the same `fetch_history`,
`from_cache` and `slip_breakdown` the console uses. That argument is sound and it has a cost
worth stating: a defect in the shared measurement code is shared by the product and the
study, so the study cannot act as an independent check on the product. It did not catch
Correction 6.

**Correction 1: n was inflated, in the flattering direction.** The results store is written
by appending and the run is resumable, so a background pass and a manual merge appended
concurrently, and a large minority of rows were duplicates. A figure published mid-run as a
trial count was a row count. This correction was itself first published wrong, pairing a row
count from one moment with a distinct count from a later one. The magnitudes are in
`docs/LIMITS.md` and the git history; they are not snapshot fields, and this document no
longer carries figures that are not.

**Correction 2: an overcorrection, retracted.** An audit of the slip figures treated any
endpoint reword as a scope change and concluded most of the audited trials had unsupported
figures. That was wrong in both directions: it excluded a real multi-year movement because
the sponsor reworded an endpoint in the same filing, and it created a laundering route,
since a sponsor wanting a delay gone from the comparable total need only reword the
endpoint. A guard the subject can defeat by editing prose, in the direction that flatters
them, is not a guard.

**Correction 3: the headline was downgraded**, from calling the anchor case remarkable to
placing it at its percentile, on this project's own evidence.

**Correction 4: a rule stated in prose and violated in code.** The report printed a pooled
all-strata section on every run, for as long as the rule against pooling had existed.

**Correction 5: two trials lost to a bug and recovered.** The version cache wrote each fetch
straight to its target path, so an interrupted run left a truncated file that every later
read of that trial failed on. Two NIH trials stored a parse error in place of a measurement.
Fixed at the source under a written amendment procedure, then re-measured.

**Correction 6: the headline measure could not see silence.** The stretch measure needs a
later filing to close a lapse, so a sponsor that goes quiet scores as clean. Found by an
adversarial reviewer, not by the study. It is now reported as the secondary measure with
that property stated, point prevalence is primary, and the silent population is a result in
its own right rather than a gap.

**Correction 7: a wrong figure, published for one revision, from a filter that never
fired.** The first attempt at point prevalence read the date's ESTIMATED/ACTUAL type from a
helper that did not return it, compared a missing value against the string it was meant to
exclude, and therefore counted every completed trial that had correctly recorded its actual
completion date as carrying a lapsed one. It reported an order-of-magnitude larger
prevalence for industry and a near-universal one for OTHER_GOV. The true figures are 8.3%
and 45.0%. The error was in the flattering direction, produced a dramatic result, and passed
a manual review, because a check that silently does not apply looks exactly like a check
that passes. The rank inversion it was offered as evidence for turned out to be real and is
reported above; the magnitudes were an order out. A test now asserts that a past ACTUAL date
does not count.

**Correction 8: half a published headline was the filing the regulation requires.** A draft
reported that 52.4% of industry dated revisions (66 of 126) were filed after the date had
already passed and presented that as non-reconciliation. 33 of 66 set the date to ACTUAL,
which for a late trial necessarily lands after the earlier estimate expired and is exactly
the update 42 CFR 11.64(a)(1)(ii) mandates. The draft therefore quoted a regulation to argue
the behaviour was unlicensed while that regulation licensed half the numerator, and called
the same filing "the system working" in one section and a failure in another. Every number
was arithmetically correct; the sentence they supported was not, so no numeric check could
have caught it. The surviving figure is 26.2%, and it is a supporting mechanism here rather
than the headline. The same draft published the trial-level companion, 43 of 52 industry
trials (82.7%), from the same undivided numerator; under the split it is 24 of 52 (46.2%).
**Both figures are retracted.** Found by an adversarial reviewer on its second pass over the
same document.

**Correction 9: a four-stratum conclusion drawn from one stratum.** The clustering test was
first published as the industry row alone, under the sentence "there is no annual bunching".
The other three strata sat above their nulls and were not shown. Publishing all four was the
fix at the time; Correction 10 is what happened when the test was given a control.

**Correction 10: the clustering conclusion is withdrawn in both directions.** With all four
strata published, the section concluded that the batching explanation stood for OTHER and
OTHER_GOV, whose intervals sat well above an even-spread null near anniversaries. Running
the identical test on control windows half a year off each anniversary returns a count at
least as high in three of the four strata, and in the fourth a count lower by a single
interval. The ratio therefore measures a right-skewed interval distribution against a null
that assumes an even spread, and says nothing about anniversaries. Nothing about the test
was wrong arithmetically; it had no control, and a comparison with no control is not
evidence. The innocence check now ends unresolved for those strata rather than conceding to
them.

**Correction 11: an anecdote the store refutes, published as an illustration.** A draft
named the busiest of these trials and wrote that it had filed its 10 registry versions
*while* sitting past its date, offered as evidence that the silent carriers keep filing
other things and stop touching one field. The version count is real and it is a **lifetime**
count. The timing is not merely unsupported, which is how this correction first read: it is
contradicted, and contradicted by construction. A trial is in that population only if
`dead_date_stretches` is zero, and that field counts every consecutive version pair where a
filing arrived over an already-passed date, across all cached versions rather than only
date-changing ones. Zero stretches therefore means **no filing of any kind arrived after the
date had passed**. Checked on the trial itself: every one of its versions was submitted
before its registered date, the last of them weeks before it. The draft selected the maximum
of a population as an illustration of that population, and the fact it illustrated was the
opposite of what the population shows.

The generated form did not prevent this and would not have. The version count is emitted
from a field in the replacement sentence above; the word "while" was the error, and it
carries no digits. That is the residual the banner names, arriving in the correction log of
the same pass that built the guard.

**A note on what the corrections have in common.** Most of them were found by breaking
something or by an outside reader, and two were found only on a second pass over material
the same reviewer had already read without catching it. One round of review would have
shipped both. Correction 10 is the first one found by giving an existing test a control
rather than by reading its output.

## What this does not license

- **No outcome claim.** There is no outcome variable here. This study does not know which of
  these trials succeeded, which sponsors raised money, or what any of it preceded.
- **No prediction.** Nothing here has been validated out of sample against anything.
- **No motive.** Why a date moved, or did not, is not observable from a registry diff. Slip
  has many ordinary causes: enrolment, regulators, honest rescoping, financing.
- **No time series.** Every rate is one look at the registry. Whether this is getting better
  or worse is a different study.
- **No uncertainty quantification.** At this stratum size the trial-level resolution is 1.7
  percentage points, and the conditional-prevalence column is far coarser at 6.7 percentage
  points at n=15 and 5.6 percentage points at n=18, and no interval is computed anywhere.
  The equal ever-carried frequencies for industry and NIH should not be read as an estimate
  of equality. The revision-level rates are worse: they are computed over revisions, not
  trials, and revisions within a trial are not independent, since the industry revisions
  come from fewer than half as many trials. No clustered interval is computed, so every
  cross-stratum difference in this document is described, not tested.
- **Not novel terrain.** Trial delay is documented (Shadbolt et al., JAMA Network Open
  2023). Registry version histories have been assembled at far larger scale by others.
  Adjacent published work links trial timing and firm behaviour (Guenzel & Liu, RFS 2026),
  running the causal arrow the other way. What we could not find, in searches recorded in
  `docs/FINDINGS.md`, is work on how long a lapsed date is carried as a disclosure behaviour
  in its own right. That is a statement about our search, not about the literature.

## Reproducing this

```bash
python3 -m research.cohort --report            # prints the snapshot id beside the figures
python3 -m research.render_writeup --check     # fails if this document is stale
python3 -m pytest tests/test_cohort_store.py tests/test_prose_figures.py -q
```

The report refuses to describe the snapshot as current if the store has moved since the
freeze. The store is `data/cohort/results.jsonl`, one row per trial; superseded measurements
are kept in `results-archive.jsonl`. The frozen figures are in `data/cohort/snapshot.json`
under the id `cohort-5b03269658b8`, and a test recomputes every one of them from the store,
field by field, against the snapshot's own pinned as-of date. This document is written from
those fields by `research/render_writeup.py` and is regenerated whenever the snapshot is
frozen.
