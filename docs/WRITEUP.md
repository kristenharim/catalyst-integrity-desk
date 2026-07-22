# More than half of industry trial-date revisions are filed only after the date has already passed

**Every cohort figure in this document comes from snapshot `cohort-c2de38f09698`, frozen
2026-07-22, with point prevalence computed as of that same date: 240 drawn trials, 60 in
each of four sponsor strata, all measured.** The id is content-addressed over the measured
rows and the frame together, so it cannot be re-cut under the same name, and a test
recomputes it from the store and fails if the two disagree.

Figures from outside the cohort, which includes the 677-day case and the correction history,
are cited where they appear. A test recomputes the snapshot from the store. **Nothing checks
that a figure was copied from the snapshot into this prose correctly**, so the audit that
verifies this document is a person, and a person does not rerun on commit.

The draw is uniform over the first 3,000 trials in the registry's own ordering within each
stratum, not over the whole stratum. "Randomly drawn" throughout means that and not more.

## The finding, and why it is not the delay literature

That trials run late is documented. Shadbolt et al., JAMA Network Open 2023, find roughly one
in five randomised trials complete on time, with a median delay of 12.2 months. Any measure
of "the registered date passed" is therefore close to a restatement of something already
known, and a study that stops there has measured lateness with extra steps.

The distinction that separates them is **when the sponsor revised the date**, and the registry
records it exactly. Every revision carries how much time the old date still had when it was
moved:

- **Revised while the date was still in the future.** The sponsor is forecasting. The trial
  may be very late and the public record is still honest, because it was corrected before it
  became false.
- **Revised only after the date had already passed.** For that whole interval the registry
  carried a commitment its own author had stopped believing, and anyone reading it was
  reading a claim the sponsor already knew was wrong.

Lateness is the first. Non-reconciliation is the second, and it is the only one this project
claims to measure.

**In industry-sponsored trials, 66 of 126 dated revisions, 52.4%, were filed only after the
date had already passed.** At the trial level, of the 52 industry trials that revised a date
at all, **43 (82.7%) let at least one date lapse before touching it**, and only 9 (17.3%)
revised prospectively every time.

| Stratum | dated revisions | filed after the date lapsed | trials revising, ≥1 after a lapse |
|---|---:|---:|---:|
| INDUSTRY | 126 | 66 (**52.4%**) | 43 of 52 (82.7%) |
| NIH | 181 | 57 (31.5%) | 32 of 55 (58.2%) |
| OTHER_GOV | 48 | 32 (66.7%) | 23 of 28 (82.1%) |
| OTHER | 91 | 49 (53.8%) | 27 of 38 (71.1%) |

So the answer to "is this just delay?" is no, and it is measured rather than argued. A
majority of industry revisions, and a large majority of industry trials, are reconciled only
in arrears. NIH sponsors are the exception and revise prospectively about two-thirds of the
time, which is the first of three reasons the strata are not pooled.

## How many are carrying an expired date right now

The primary frequency measure is point prevalence: a trial whose most recent registered
primary completion date is in the past **and still typed as an estimate** rather than an
actual. A past date typed ACTUAL is the reconciled case, a completed trial recording when it
completed, and does not count.

| Stratum | carrying an expired estimate, 2026-07-22 | of which invisible to the stretch measure | median registry versions |
|---|---:|---:|---:|
| INDUSTRY | 5 of 60 (8.3%) | 4 | 9 |
| NIH | 0 of 60 (0.0%) | 0 | 106 |
| OTHER | 19 of 60 (31.7%) | 15 | 4 |
| OTHER_GOV | 27 of 60 (45.0%) | 20 | 2 |

This is a much smaller number than the stretch-based rate below, and it should be. It counts
open commitments at one instant rather than everything that ever happened to a trial over up
to ten years. Most trials in this frame have finished and recorded an actual completion date,
which is the system working.

## The sponsors that lapse and go quiet

**This is a first-class result and it was nearly missed, because the measure that was going
to be the headline cannot see it.**

The stretch measure below records a lapse only when a *later filing* arrives while an
already-passed date is standing. A sponsor that lets a date expire and then files nothing
produces no stretch at all and scores as never having carried one. The silence is exactly
what makes it invisible.

Twenty of OTHER_GOV's 27 currently-expired trials are invisible that way, and 15 of OTHER's
19. The consequence is that the two measures rank the four strata in **exactly opposite
order**:

| Stratum | ever carried, and filed again | carrying one now | median versions |
|---|---:|---:|---:|
| INDUSTRY | 80.0% | 8.3% | 9 |
| NIH | 80.0% | 0.0% | 106 |
| OTHER | 61.7% | 31.7% | 4 |
| OTHER_GOV | 53.3% | 45.0% | 2 |

The ordering is filing frequency. NIH trials carry a median of 106 registry versions and
never end up sitting on an expired estimate, because something always comes along to
reconcile it. OTHER_GOV trials carry a median of 2, and nearly half are sitting on one now.

Read alone, the stretch measure would have said government and academic sponsors do this
least. They do it most. A measure that needs its subject to keep talking cannot see the
subject that stops.

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

Industry median 239.5 reported as 240, p90 995.6 as 996; percentiles linearly interpolated.
On this unit the NIH/industry ratio is 2.4x rather than 1.5x. **The gap between 1.5x and 2.4x
is the filing-frequency artifact, not a finding**, which is why the per-trial unit is primary
and this one is labelled as a sensitivity.

### Why the strata are not pooled

Three independent differences, none of which rests on the duration ratio alone:

1. **Reconciliation behaviour.** 52.4% of industry revisions are filed after a lapse against
   31.5% of NIH ones.
2. **Point prevalence.** 45.0% of OTHER_GOV trials are carrying an expired estimate now
   against 0.0% of NIH trials.
3. **Filing frequency**, which drives both, at a median of 2 versions per trial against 106.

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

What the 52.4% figure does bear on is different and stronger: whatever the cadence, a majority
of industry revisions arrive after the date they replace has already expired.

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
routinely stands for months before anything ends it, and that a majority of revisions arrive
only after the fact. What survives about the case is narrower than it looks: an investment
thesis anchored to a date nobody re-reads is anchored to a claim its author may have stopped
believing. Whether re-reading it changes any decision or outcome is not measured here and is
not in this dataset.

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

## What this does not license

- **No outcome claim.** There is no outcome variable here. This study does not know which of
  these trials succeeded, which sponsors raised money, or what any of it preceded.
- **No prediction.** Nothing here has been validated out of sample against anything.
- **No motive.** Why a date moved, or did not, is not observable from a registry diff. Slip
  has many ordinary causes: enrolment, regulators, honest rescoping, financing.
- **No time series.** Every rate is one look at the registry. Whether this is getting better or
  worse is a different study.
- **No uncertainty quantification.** With 60 trials per stratum the resolution is 1.7
  percentage points and no interval is computed anywhere. The equal 80.0% frequencies for
  industry and NIH should not be read as an estimate of equality.
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
under the id `cohort-c2de38f09698`, and a test recomputes every one of them from the store,
field by field, against the snapshot's own pinned as-of date.
