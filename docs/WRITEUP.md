# The sponsors carrying expired commitments are the ones that stopped filing

**Every cohort figure in this document is a field of snapshot `cohort-8326c1c1e964`, frozen
2026-07-22, with point prevalence computed as of that same date: 240 drawn trials, 60 in each
of four sponsor strata, all measured.** The id is content-addressed over the measured rows
and the frame together, so it cannot be re-cut under the same name, and a test recomputes
every field from the store and fails if the two disagree.

Three classes of figure here are **not** snapshot fields, and are named rather than implied.
The 677-day case is `NCT04248439`, expired 2022-06-01 and corrected 2024-04-08, derived in
`docs/BACKTEST.md` and asserted by `tests/test_backtest.py`. The correction history in the
methods section is sourced from `docs/BOB_LOG.md`, `docs/LIMITS.md` and the git history, and
none of its figures are in the snapshot. The two percentile ranks for the 677-day case,
159 of 188 stretches and 32 of 48 trials, are computed from the store rather than read from a
snapshot field and no test asserts them; they are traceable because the snapshot id is
content-addressed over that store, and they are not pinned.

**Nothing checks that a figure was copied from the snapshot into this prose correctly**, so
the audit that verifies this document is a person, and a person does not rerun on commit.

The draw is uniform over the first 3,000 trials in the registry's own ordering within each
stratum, not over the whole stratum. "Randomly drawn" throughout means that and not more.

## The finding: this study cannot separate reconciliation from filing frequency

The trials carrying an expired commitment are overwhelmingly the ones whose sponsors stopped
filing, and the measure that was going to be this study's headline cannot see them.

A trial is **carrying an expired commitment** when its most recent registered primary
completion date is in the past and still typed as an estimate. A past date typed ACTUAL is the
reconciled case, a completed trial recording when it completed, and does not count. Measured as
of 2026-07-22, against two denominators, beside how often each stratum files at all:

| Stratum | carrying an expired estimate | of trials whose commitment is still open | invisible to the stretch measure | median registry versions | median date revisions |
|---|---:|---:|---:|---:|---:|
| NIH | 0 of 60 (0.0%) | 0 of 18 (**0.0%**) | 0 | 106.5 | 4 |
| INDUSTRY | 5 of 60 (8.3%) | 5 of 15 (33.3%) | **4 of 5** | 9 | 3 |
| OTHER | 19 of 60 (31.7%) | 19 of 28 (67.9%) | 15 of 19 | 4 | 2 |
| OTHER_GOV | 27 of 60 (45.0%) | 27 of 29 (**93.1%**) | 20 of 27 | 2 | 1 |

Both denominators are reported because they answer different questions. Out of all 60 trials
the rate is small and should be: most trials in this frame have finished and recorded an actual
completion date, which is the system working. But 45 of the 60 industry trials are in that
state and cannot be carrying an expired estimate by construction. Among those whose commitment
is still open, one in three industry trials is already past its stated date, and for OTHER_GOV
it is 27 of 29. **Four of the five industry trials currently carrying an expired estimate are
invisible to the measure this project started with**, which is the industry instance of the
finding below.

Five trials is five events. No interval is computed anywhere in this document, and the
conditional column's denominators are smaller still: one trial is 6.7 percentage points at
n=15 and 5.6 at n=18, so the bolded 0.0% for NIH is a zero out of eighteen.

NIH sponsors file a median of 106.5 registry versions per trial and have **no** trial currently
carrying an expired estimate. OTHER_GOV sponsors file a median of 2 and nearly all of their
open commitments are expired. The ordering is monotone in filing frequency across all four
strata. That is an association across four points, not a tested mechanism, and nothing here
separates filing frequency from any other property that varies alongside it.

**A registry version is any record edit, not a completion-date edit**, and the 53x spread
between NIH and OTHER_GOV is mostly edits to fields nobody here is discussing. On date
revisions alone the medians are 4, 3, 2 and 1: the same ordering over a far smaller range. The
last column above carries both so the spread is not read as fifty times more date maintenance.

**The converse does not hold, and the study can say so.** Of the 32 OTHER_GOV trials that never
revised a date, 18 carry an expired estimate and 14 do not; for industry it is 4 of 8, for
OTHER 15 of 22, and none of the 5 NIH non-revisers carry one. Going quiet is common among the
trials carrying an expired commitment; it does not follow that a quiet trial is carrying one.

### The measure that misses them, and why it inverts

The stretch measure, reported in full further down, records a lapse only when a *later filing*
arrives while an already-passed date is standing. A sponsor that lets a date expire and then
files nothing produces no stretch at all and scores as never having carried one. The silence is
exactly what makes it invisible: 20 of OTHER_GOV's 27 currently-expired trials and 15 of
OTHER's 19 are invisible that way, and 32 of 60 OTHER_GOV trials never revised a date at all.

The two measures therefore rank the four strata in **exactly opposite order**:

| Stratum | ever carried, and filed again | carrying one now | median versions |
|---|---:|---:|---:|
| INDUSTRY | 80.0% | 8.3% | 9 |
| NIH | 80.0% | 0.0% | 106.5 |
| OTHER | 61.7% | 31.7% | 4 |
| OTHER_GOV | 53.3% | 45.0% | 2 |

Read alone, the stretch measure would have said government and academic sponsors lapse and file
again least often. They are the most likely to be carrying an expired date now. A measure that
needs its subject to keep talking cannot see the subject that stops, and any frequency
statistic built from observed corrections has the same blind spot.

## The mechanism, among sponsors that are still filing

That trials run late is documented. Shadbolt et al., JAMA Network Open 2023, find roughly one
in five randomised trials complete on time, with a median delay of 12.2 months. Any measure of
"the registered date passed" is close to a restatement of something already known, and a study
that stops there has measured lateness with extra steps.

The distinction that separates them is **when** the date was revised and **to what**. Every
revision carries how much time the old date still had when it was moved:

- **Revised while the date was still in the future.** The registered date had not yet passed
  when it was replaced. The trial may be very late and the record still never showed a date
  that had expired.
- **Revised after the date had already passed, recording an ACTUAL completion.** For a trial
  that ran late this necessarily lands after the earlier estimate expired, and it is the update
  42 CFR 11.64(a)(1)(ii) requires within 30 days of actual completion. It is the reconciliation
  event, not its absence.
- **Revised after the date had already passed, with another ESTIMATE.** The sponsor let the
  date pass and then pushed it, with no completion recorded. This is the behaviour this project
  claims to measure.

None of the three describes what anyone knew or intended, which a registry diff cannot show.

| Stratum | dated revisions | after a lapse | of those, recorded ACTUAL | **estimate → estimate** | rate |
|---|---:|---:|---:|---:|---:|
| INDUSTRY | 126 | 66 | 33 | **33** | **26.2%** |
| NIH | 181 | 57 | 20 | 37 | 20.4% |
| OTHER_GOV | 48 | 32 | 14 | 18 | 37.5% |
| OTHER | 91 | 49 | 14 | 35 | 38.5% |

At the trial level, 24 of the 52 industry trials that revised a date at all (46.2%) did this at
least once. The comparable figures are 21 of 55 for NIH, 16 of 28 for OTHER_GOV and 21 of 38
for OTHER.

So among sponsors that are still filing, a quarter of industry revisions are something delay
does not account for. An earlier draft of this document reported 52.4% here, which counted the
mandated update-to-actual filing as a failure to reconcile; that is retracted as Correction 8.

**This measure is conditional on a revision existing**, which is the same blind spot as the
stretch measure, one level up: a trial that lapses and never files again contributes to neither
the numerator nor the denominator. It is not small, at 8 of 60 industry trials and 32 of 60
OTHER_GOV trials, and it is why this section supports the finding above rather than standing on
its own.

A boundary convention: a revision filed on the exact day the date came due has zero days
remaining and is counted as prospective rather than as a lapse. That is 2 of the 446 dated
revisions across all four strata and it moves no published figure.

## What is being measured, and what is not

This is a measurement of **reconciliation**, not of performance.

The system observes whether a public, dated, self-authored commitment was kept, revised,
superseded, or left standing after its date passed without anyone reconciling it. It does not
observe whether the underlying trial was going well, whether the sponsor was in difficulty,
or whether the original date was ever achievable. There is no outcome variable in this
dataset at all.

That boundary has a partial mechanical guard. `orchestrator/lexicon.py` is a list of banned
phrasings checked in CI against every rendered page and every claim-bearing document
including this one, and a sentence matching one of those patterns does not survive the build.
It is a list of phrasings, so it catches the ones someone thought of. It is a floor under the
prose, not the boundary itself.

Two vocabulary points that follow from the same discipline:

- This is the **registered primary-completion expectation**, which is last patient last visit
  for the primary endpoint. Topline results follow it by roughly two to four months, a
  working figure used throughout this project and not one measured here.
- A stretch is **carried**. That a date passed and stayed standing is a fact about the record.
  Whether anyone intended anything by it is not observable from a registry diff, and nothing
  here asserts that they did.

## The frame, which is the denominator

Every rate this project published before this study came from fourteen trials that happened
to be cached, belonging to five companies chosen by hand to illustrate the problem. A sample
selected on the outcome cannot produce a base rate. This is the replacement.

| | |
|---|---|
| Study type | Interventional |
| Phase | 2, 2/3, or 3 |
| Requires | A registered primary completion date |
| First posted | 2016-01-01 to 2023-12-31 |
| Stratified by | Lead sponsor class |
| Drawn | 60 per stratum, seed 20260722 |
| Measured | 240 of 240, after recovering two trials lost to a cache defect (Correction 5) |
| Point prevalence as of | 2026-07-22, pinned in the snapshot, never read from the clock |

The end date is deliberate. A trial first posted in 2024 has had too little time to accumulate
a revision history, and including it would bias every duration downward.

**A limitation, and the frame size is not known:** enumeration is capped at 3,000 trials per
stratum, so within a stratum the draw is uniform over the registry's own ordering rather than
over the whole stratum. What fraction of each stratum that cap represents was not recorded, so
how much this matters is unmeasured rather than small.

## Duration

**Primary: one observation per trial, its longest carry.** A trial that lapsed once contributes
one number regardless of how often its sponsor happened to file afterwards.

| Stratum | trials with a carry | median | p90 | max |
|---|---:|---:|---:|---:|
| INDUSTRY | 48 | **390** | 1,384 | 2,104 |
| NIH | 48 | **590** | 1,617 | 2,716 |
| OTHER_GOV | 32 | 336 | 727 | 2,556 |
| OTHER | 37 | 439 | 998 | 1,929 |

Days. NIH/industry ratio at the median: **1.5x**.

**Every duration in this section is measured on completed spells**, meaning lapses that were
eventually ended by a later filing. Excluding open lapses biases every duration **downward**,
and the exclusion is unequal across strata: no NIH trial is excluded on this ground, against 5
industry, 19 OTHER and 27 OTHER_GOV. The 1.5x cross-stratum ratio is therefore between
differently censored distributions and should be read with that. The open cases, which are the ones a monitor would actually alert on, contribute no
duration at all: this study counts them and does not say how long they run or where the
replacement date lands. Recorded in `docs/PARKING.md` as the next measurement rather than
estimated here.

**Sensitivity, per stretch.** A stretch is emitted per consecutive version pair, so one lapse
spanning many filings contributes many overlapping rows measuring the same expiry to
successively later endpoints, and a frequent filer contributes more of them. One NIH trial
with 97 versions and three date revisions contributes 91 of that stratum's 493 stretches.

| Stratum | stretches | median | p90 | max | ever carried |
|---|---:|---:|---:|---:|---:|
| INDUSTRY | 188 | 240 | 996 | 2,104 | 80.0% |
| NIH | 493 | 567 | 1,589 | 2,716 | 80.0% |
| OTHER_GOV | 50 | 222 | 686 | 2,556 | 53.3% |
| OTHER | 96 | 270 | 874 | 1,929 | 61.7% |

Percentiles linearly interpolated and reported to the nearest day: industry median 239.5 as
240 and p90 995.6 as 996, OTHER p90 873.5 as 874, OTHER_GOV per-trial p90 726.9 as 727. NIH
median registry versions is 106.5 and is printed as such rather than rounded, because `:.0f`
rounds half to even and would show 106.
On this unit the NIH/industry ratio is 2.4x rather than 1.5x. **The gap between 1.5x and 2.4x
is the filing-frequency artifact, not a finding**, which is why the per-trial unit is primary
and this one is labelled as a sensitivity.

### Why the strata are not pooled

Three independent differences, none of which rests on the duration ratio alone:

1. **Reconciliation behaviour.** 26.2% of industry revisions replace an already-expired
   estimate, against 20.4% of NIH and 37.5% of OTHER_GOV ones.
2. **Point prevalence.** 45.0% of OTHER_GOV trials are carrying an expired estimate now
   against 0.0% of NIH trials.
3. **Filing frequency**, which orders both and is not separable from either here, at a median
   of 2 registry versions per trial against 106.5, or 1 date revision against 4.

`stats()` raises rather than returning a pooled rate, so the figure cannot be computed by
accident.

## Comparability, and why three totals rather than two

A date moving between two registry versions is a delay only if both dates describe the same
commitment. Every transition is classified into three states and refusals carry their reason:

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

The unreadable column is the share of refusals caused by a gap in *our* data rather than by an
event in the sponsor's record, and it is zero in every stratum. The hole this check was built
to find is empty. It was defined narrowly and says nothing about gaps of other shapes; the
adversarial review of this document found two of those.

## The innocence check

If sponsors simply batch their registry housekeeping annually, a median lapse of months is an
artifact of update cadence rather than of anything being ignored.

Annual batching would not be compliant, because the rule for this element is not annual.
42 CFR 11.64(a)(1)(ii):

> "Primary Completion Date must be updated not later than 30 calendar days after the clinical
> trial reaches its actual primary completion date."

**That is a statement about the duty, not a refutation of the behaviour**, and the section is
titled as a check rather than a result for that reason. A roughly annual housekeeping cycle is
consistent with the durations observed here. Testing it properly means looking for clustering
of update intervals near a year, which this study has not done, so batching is **not** ruled
out as a description of the cadence.

An earlier draft claimed the revision timing settled this, on the grounds that a majority of
industry revisions arrive after the date they replace has already expired. That argument does
not work, for two separate reasons. The majority figure was 52.4%, which counted the mandated
update-to-actual filing and is retracted as Correction 8. And the surviving 26.2%
estimate-to-estimate subset does not rebut batching either: a sponsor on a yearly cycle would
replace an expired estimate with a fresh one at the next pass, which is exactly what that
subset counts. **A cadence hypothesis is not refuted by evidence that the cadence is slow.**

So this section does not deliver a result. What would settle it is in the data and has not
been run: if batching were operating, update intervals would cluster near multiples of a year.
Until someone looks, the honest position is that annual housekeeping remains a live
explanation for the durations here, and that it would not be a compliant one.

**What the regulation does and does not license, precisely.** The rule concerns updating the
date to *actual* once a trial reaches its actual primary completion. Much of what is observed
here is a registered *estimate* that passed and stayed standing. Those overlap but are not the
same event, and this dataset cannot say which happened for any given trial. The 30-day window
is therefore a **reference line on a distribution**, not a test any trial passes or fails, and
no stretch here is called a breach. Naming the duty is what the claims lexicon requires before
any statement touching disclosure obligations is permitted at all. Naming it is not alleging
it was breached.

## The case this project was built around

This project opened on a single company that had published a completion date 677 days after it
passed, sitting on a public registry the whole time. The cohort places that case: the **85th
percentile** of the 188 industry stretches, and the **67th percentile** of the 48 industry
trials counted one observation each. Long, and inside the distribution rather than outside it.

Both figures are the empirical share of observations at or below 677 days; 159 of 188 is 84.6%,
reported as the 85th. No observation equals exactly 677, so "at or below" versus "below" makes
no difference. This is a different convention from the interpolated percentiles in the tables
above, so the two cannot be read off each other.

The finding was never that one sponsor was unusual. It is that in this frame a lapsed date
routinely stands for months before anything ends it, and that a quarter of industry revisions
replace a date that had already expired. Whether re-reading that field changes any decision or
outcome is not measured here and is not in this dataset.

## Methods, including everything that went wrong

The correction history is the record of what was caught, offered as that and nothing more. It
is incomplete by construction: an adversarial review added four more corrections after this
section was first written, and two of them are larger than anything that was in it.

**Measured with the product's own code.** The cohort calls the same `fetch_history`,
`from_cache` and `slip_breakdown` the console uses. That argument is sound and it has a cost
worth stating: a defect in the shared measurement code is shared by the product and the study,
so the study cannot act as an independent check on the product. It did not catch Correction 6.

**Correction 1: n was inflated by about 37%, in the flattering direction.** The results store
is written by appending and the run is resumable, so a background pass and a manual merge
appended concurrently. At the commit where the fix landed the store held 179 rows and 131
distinct trials, 48 counted twice. The figure published mid-run as "169 trials measured" was a
row count: those 169 rows were 123 distinct trials. This correction was itself first published
wrong, as "n=169 was really 131, inflated by 29%", which paired a row count from one moment
with a distinct count from a later one.

**Correction 2: an overcorrection, retracted.** An audit of the slip figures treated any
endpoint reword as a scope change and concluded five of seven trials had unsupported figures.
That was wrong in both directions: it excluded a real 1,430-day movement because the sponsor
reworded an endpoint in the same filing, and it created a laundering route, since a sponsor
wanting a delay gone from the comparable total need only reword the endpoint. A guard the
subject can defeat by editing prose, in the direction that flatters them, is not a guard.

**Correction 3: the headline was downgraded**, from "677 days is remarkable" to "677 days is
the 85th percentile", on this project's own evidence.

**Correction 4: a rule stated in prose and violated in code.** The report printed a pooled
all-strata section on every run, for as long as the rule against pooling had existed.

**Correction 5: two trials lost to a bug and recovered.** The version cache wrote each fetch
straight to its target path, so an interrupted run left a truncated file that every later read
of that trial failed on. Two NIH trials stored a parse error in place of a measurement. Fixed
at the source under a written amendment procedure, then re-measured.

**Correction 6: the headline measure could not see silence.** The stretch measure needs a
later filing to close a lapse, so a sponsor that goes quiet scores as clean. Found by an
adversarial reviewer, not by the study. It is now reported as the secondary measure with that
property stated, point prevalence is primary, and the silent population is a result in its own
right rather than a gap.

**Correction 7: a wrong figure, published for one revision, from a filter that never fired.**
The first attempt at point prevalence read the date's ESTIMATED/ACTUAL type from a helper that
did not return it, compared `None` against `"ACTUAL"`, and therefore counted every completed
trial that had correctly recorded its actual completion date as carrying a lapsed one. It
reported 83.3% for industry and 96.7% for OTHER_GOV. The true figures are 8.3% and 45.0%. The
error was in the flattering direction, produced a dramatic result, and passed a manual review,
because a check that silently does not apply looks exactly like a check that passes. The rank
inversion it was offered as evidence for turned out to be real and is reported above; the
magnitudes were an order out. A test now asserts that a past ACTUAL date does not count.

**Correction 8: half a published headline was the filing the regulation requires.** A draft
reported that 52.4% of industry dated revisions were filed after the date had already passed
and presented that as non-reconciliation. Half of them, 33 of 66, set the date to ACTUAL,
which for a late trial necessarily lands after the earlier estimate expired and is exactly the
update 42 CFR 11.64(a)(1)(ii) mandates. The draft therefore quoted a regulation to argue the
behaviour was unlicensed while that regulation licensed half the numerator, and called the
same filing "the system working" in one section and a failure in another. Every number was
arithmetically correct; the sentence they supported was not, so no numeric check could have
caught it. The surviving figure is 26.2%, and it is a supporting mechanism here rather than
the headline. The same draft published the trial-level companion, 43 of 52 industry trials
(82.7%), from the same undivided numerator; under the split it is 24 of 52 (46.2%). **Both
figures are retracted.** Found by an adversarial reviewer on its second pass over the same
document.

**A note on what the corrections have in common.** Six of the eight were found by breaking
something or by an outside reader, and two of those (6 and 8) were found only on a second pass
over material the same reviewer had already read without catching it. One round of review would have shipped
both.

## What this does not license

- **No outcome claim.** There is no outcome variable here. This study does not know which of
  these trials succeeded, which sponsors raised money, or what any of it preceded.
- **No prediction.** Nothing here has been validated out of sample against anything.
- **No motive.** Why a date moved, or did not, is not observable from a registry diff. Slip
  has many ordinary causes: enrolment, regulators, honest rescoping, financing.
- **No time series.** Every rate is one look at the registry. Whether this is getting better or
  worse is a different study.
- **No uncertainty quantification.** With 60 trials per stratum the trial-level resolution is
  1.7 percentage points, and the conditional-prevalence column is far coarser: 6.7 points per
  trial at n=15 and 5.6 at n=18 and no interval is computed anywhere. The equal 80.0% frequencies for
  industry and NIH should not be read as an estimate of equality. The revision-level rates are
  worse: they are computed over revisions, not trials, and revisions within a trial are not
  independent, since 126 industry revisions come from 52 trials. No clustered interval is
  computed, so every cross-stratum difference in this document is described, not tested.
- **Not novel terrain.** Trial delay is documented (Shadbolt et al., 2023). Registry version
  histories have been assembled at far larger scale by others. Adjacent published work links
  trial timing and firm behaviour (Guenzel & Liu, RFS 2026), running the causal arrow the
  other way. What we could not find, in searches recorded in `docs/FINDINGS.md`, is work on
  how long a lapsed date is carried as a disclosure behaviour in its own right. That is a
  statement about our search, not about the literature.

## Reproducing this

```bash
python3 -m research.cohort --report     # prints the snapshot id beside the figures
python3 -m pytest tests/test_cohort_store.py -q
```

The report refuses to describe the snapshot as current if the store has moved since the
freeze. The store is `data/cohort/results.jsonl`, one row per trial; superseded measurements
are kept in `results-archive.jsonl`. The frozen figures are in `data/cohort/snapshot.json`
under the id `cohort-8326c1c1e964`, and a test recomputes every one of them from the store,
field by field, against the snapshot's own pinned as-of date. Every cohort figure quoted in
this document is one of those fields; the two classes that are not are named in the opening
section.
