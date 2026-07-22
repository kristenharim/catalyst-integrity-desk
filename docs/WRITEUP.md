# Four in five industry-sponsored trials in this sample have carried an already-passed completion date

> [!DANGER] **DRAFT, BLOCKED. DO NOT PUBLISH.**
> A three-seat adversarial review on 2026-07-22 blocked this document. Two of the objections
> are measurement problems rather than wording problems, they are confirmed against the
> store, and resolving them is the owner's call because it changes what the study's headline
> measures. Both are written up in `docs/LIMITS.md`:
>
> 1. **The dead-date measure cannot see a sponsor that lapses and goes quiet.** A stretch
>    needs a later filing to close it, so the published rate is really "carried a dead date
>    and then filed again". This **inverts the cross-stratum comparison**: OTHER_GOV has the
>    lowest published rate (53.3%) and the highest share carrying one right now (96.7%).
> 2. **A stretch is not an episode.** One lapse spanning many filings contributes many
>    overlapping rows, so duration tracks filing frequency. The headline **2.4x** NIH/industry
>    ratio falls to **1.5x** measured one observation per trial.
>
> The industry figures are the least affected and move in the conservative direction. Every
> cross-stratum sentence below is suspect until item 1 is settled. Sections known to be wrong
> are marked inline.

**Every cohort figure in this document comes from snapshot `cohort-65fdf1f71b1d`, frozen
2026-07-22: 240 drawn trials, 60 in each of four sponsor strata, all measured** (two of them
after recovering a cache defect, see Correction 5). The id is content-addressed over the
measured rows and the frame together, so it cannot be re-cut under the same name, and a test
recomputes it from the store and fails if the two disagree.

Figures from outside the cohort, which includes the 677-day case and the whole correction
history below, are cited where they appear. A test recomputes the snapshot from the store.
**Nothing checks that a figure was copied from the snapshot into this prose correctly**, so
the audit that verified this draft was a person, and a person does not rerun on commit.

The draw is uniform over the first 3,000 trials in the registry's own ordering within each
stratum, not over the whole stratum. "Randomly drawn" throughout means that and not more.
Reproduction instructions are at the end.

## The finding

80.0% of industry-sponsored trials in the sample carried a registered primary completion
date that had already passed, at some point in their history. The median stretch was 240
days. Against the 30-day update window that 42 CFR 11.64(a)(1)(ii) sets for this specific
field, that median is eight times the window; the 90th percentile, 996 days, is thirty-three
times it. The longest single stretch in the industry stratum was 2,104 days, just under six
years.

**What "carried" measures, precisely, because it is narrower than it sounds.** A stretch is
recorded only when a later filing arrives while an already-passed date is standing. A trial
that lapsed and then filed nothing produces no stretch and is counted as never having
carried one. So this rate is a **lower bound**, and it is a weaker bound for sponsors who
file rarely. Counting trials whose most recent registered date is in the past and still
typed as an estimate, as of the snapshot date, industry rises from 80.0% to **83.3%**.

> [!WARNING] **This paragraph is wrong and is retained so the correction is visible.** It
> read: "Publicly funded sponsors do it at exactly the same rate and for much longer.
> NIH-sponsored trials also carried a dead date in 80.0% of cases, with a median stretch of
> 567 days, 2.4 times the industry figure. Government and academic sponsors did it less
> often, 53.3% and 61.7%."
>
> Both halves are undercut. The frequency ranking is an artifact of how often a stratum
> files: OTHER_GOV files a median of 2 registry versions per trial and 28 of its 60 trials
> lapsed and never filed again, so its 53.3% is the measure failing to see them, and 96.7% of
> its trials are carrying an unreconciled lapsed date right now. And the 2.4x duration ratio
> falls to 1.5x when each trial contributes one observation instead of one per filing, which
> matters because NIH trials carry a median of 106 registry versions against industry's 9.
>
> What can still be said: the behaviour is not confined to commercial sponsors, and it is
> common in every stratum measured. Any ranking between strata is withdrawn.

## What is being measured, and what is not

This is a measurement of **reconciliation**, not of performance.

The system observes whether a public, dated, self-authored commitment was kept, revised,
superseded, or left standing after its date passed without anyone reconciling it. It does
not observe whether the underlying trial was going well, whether the sponsor was in
difficulty, or whether the original date was ever achievable. There is no outcome variable
in this dataset at all.

That boundary is enforced rather than promised. `orchestrator/lexicon.py` is a list of
claims this system may not make, checked in CI against every rendered page and every
claim-bearing document including this one. A sentence judging whether a timeline was
achievable does not survive the build. It is a list of banned phrasings, so it catches the
phrasings someone thought of. It is a floor under the prose, not the boundary itself.

Two vocabulary points that follow from the same discipline:

- This is the **registered primary-completion expectation**, which is last patient last
  visit for the primary endpoint. Topline results follow it by roughly two to four months,
  a working figure used throughout this project and not one measured here.
  The two are not the same and the difference is systematic, not noise.
- A stretch is **carried**. The observation is that a date passed and stayed standing in a
  public record, which is a fact about the record. Whether anyone intended anything by it is
  not observable from a registry diff, and nothing here asserts that they did.

## The frame, which is the denominator

A rate is meaningless without the population it was drawn from, and every rate this project
published before this study came from fourteen trials that happened to be cached, belonging
to five companies chosen by hand to illustrate the problem. A sample selected on the outcome
cannot produce a base rate. This is the replacement.

| | |
|---|---|
| Study type | Interventional |
| Phase | 2, 2/3, or 3 |
| Requires | A registered primary completion date |
| First posted | 2016-01-01 to 2023-12-31 |
| Stratified by | Lead sponsor class |
| Drawn | 60 per stratum, seed 20260722 |
| Measured | 240 of 240, after recovering two trials lost to a cache defect (Correction 5) |

The end date is deliberate. A trial first posted in 2024 has had too little time to
accumulate a revision history, and including it would bias every duration downward.

**A real limitation, stated as one:** enumeration of the frame is capped at 3,000 trials per
stratum, so within a stratum the draw is uniform over the registry's own ordering rather than
over the whole stratum. This is recorded in the snapshot's own frame block.

## Results

All figures from `cohort-65fdf1f71b1d`. Rates are per stratum. There is no all-strata row:
the strata differ enough on both frequency and duration that a pooled figure would describe
none of them.

| Stratum | n | Carried at some point | Carrying one now | Median per stretch | Median per trial | p90 per stretch | Max | Stretches | Median versions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| INDUSTRY | 60 | 80.0% (48) | 83.3% (50) | 240 | 390 | 996 | 2,104 | 188 | 9 |
| NIH | 60 | 80.0% (48) | 70.0% (42) | 567 | 590 | 1,589 | 2,716 | 493 | 106 |
| OTHER_GOV | 60 | 53.3% (32) | 96.7% (58) | 222 | 336 | 686 | 2,556 | 50 | 2 |
| OTHER | 60 | 61.7% (37) | 85.0% (51) | 270 | 439 | 874 | 1,929 | 96 | 4 |

Durations in days. Percentiles in the "per stretch" columns are linearly interpolated; the
industry median is 239.5 reported as 240 and the p90 is 995.6 reported as 996.

**Read the two frequency columns together, and read the last column before either.** "Carried
at some point" needs a later filing to close the stretch, so it undercounts sponsors that
lapse and go quiet. "Carrying one now" counts trials whose most recent registered date is in
the past and still typed as an estimate, as of the snapshot date, and needs no later filing.
Where a stratum files rarely the two diverge violently: OTHER_GOV files a median of 2 versions
per trial, and 28 of its 60 trials lapsed and never filed again.

**The two median columns are the same reason.** A stretch is emitted per consecutive version
pair, not per episode, so one lapse spanning many filings contributes many overlapping rows
and a frequent filer contributes more of them. One NIH trial with 97 versions and three date
revisions contributes 91 of that stratum's 493 stretches. The per-trial column gives each
trial one observation, its longest carry. The NIH/industry ratio is 2.4x on the first
convention and 1.5x on the second.

Neither convention is wrong and both are reported here because the choice changes the
answer. This is the unresolved item that blocks the document.

### Comparability, and why three totals rather than two

A date moving between two registry versions is a delay only if both dates describe the same
commitment. Where they do not, subtracting them produces a number that looks like slip and
is not. Every transition is therefore classified into one of three states, and refusals are
recorded with their reason:

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

The unreadable column is the one to read. It is the share of refusals caused by a gap in
*our* data rather than by an event in the sponsor's record, and it is zero in every stratum.
An earlier version of this work flagged the refusal bundle as uninterpretable precisely
because it mixed those two things. Splitting them shows the bundle was correct and merely
unlabelled. The hole this check was built to find is empty in all four strata. It was
defined narrowly, as the share of refusals attributable to a dimension we could not read,
and it says nothing about gaps of other shapes. The adversarial review that blocked this
document found two.

The contingency rate matters as a product fact rather than a scientific one. Measured on the
old convenience sample it looked like roughly a quarter of transitions, which would need a
staffed adjudication queue. At 7.1% of industry transitions it is an occasional task.

## The innocence check

Before any of this goes anywhere, the dull explanation has to be ruled out. If sponsors
simply batch their registry housekeeping annually, a median lapse of 240 days is an artifact
of update cadence rather than of anything being ignored.

Annual batching would not be compliant, because the rule for this element is not annual.
42 CFR 11.64(a)(1)(ii):

> "Primary Completion Date must be updated not later than 30 calendar days after the
> clinical trial reaches its actual primary completion date."

The observed industry median is eight times that window and the p90 is thirty-three times
it. Annual batching cannot be a complete explanation of the distribution.

**What that does and does not license, precisely, because this is the sentence most likely
to be overread.** The rule concerns updating the date to *actual* once a trial reaches its
actual primary completion. What is observed here is a registered *estimated* date that
passed and stayed standing. Those overlap but are not the same event, and this dataset
cannot say which happened for any given trial. Therefore:

- The 30-day window is used as a **reference line on a distribution**. It is not a test that
  any individual trial passes or fails, and no stretch in this study is called a breach.
- Naming the duty is what the claims lexicon requires before any statement touching
  disclosure obligations is permitted at all. Naming it is not the same as alleging it was
  breached.

## The case this project was built around

This project opened on a single company that had published a completion date 677 days after
it passed, sitting on a public registry the whole time. The cohort places that case: **the
85th percentile of the 188 industry stretches in the snapshot.** Long, and entirely ordinary.

That cuts against how the project was originally presented, and it makes the claim bigger
rather than smaller. The finding is not that one sponsor let a date lapse. It is that
in this frame a lapsed date routinely stands for months before anything ends it, in four
of five industry trials sampled, and in every other stratum measured too.
What survives unchanged is the consequence: an investment thesis anchored to a date nobody
re-reads is broken whether or not the sponsor was unusual in letting it lapse. What does not
survive is any suggestion that carrying a dead date singles a company out.

## Methods, including everything that went wrong

The correction history belongs in the methods rather than in a footnote, because for a study
run by one person with no external referee, a documented record of catching your own errors
is the record of what was caught, offered as that and nothing more. It is also incomplete
by construction: an adversarial review added two more corrections after this section was
first written, and both are larger than anything in it.

**Measured with the product's own code.** The cohort calls the same `fetch_history`,
`from_cache` and `slip_breakdown` the console uses, not a second implementation. A cohort
study measured by a reimplementation measures the reimplementation.

**Correction 1: n was inflated by about 37%, in the flattering direction.** The results
store is written by appending and the run is resumable, so a background pass and a manual
merge appended concurrently. At the commit where the fix landed the store held 179 rows and
131 distinct trials, 48 counted twice. The figure published mid-run as "169 trials measured"
was a row count: those 169 rows were **123** distinct trials.

This correction was itself published wrong, in an earlier draft of this document, as "n=169
was really 131, inflated by 29%". That paired a row count from one moment with a distinct
count from a later one, which is a smaller version of the same error the correction is
about. Caught by an auditor recomputing it from the git history rather than reading it. Every rate computed from it was slightly wrong. The store now deduplicates on
read, has been compacted to one row per trial with the superseded rows archived rather than
deleted, and a test fails if any shipped module reads it directly. The inflation was
invisible in the way that matters most: more rows reads as more data, never as a bug.

**Correction 2: an overcorrection, retracted.** An audit of the slip figures treated any
endpoint reword as a scope change and concluded five of seven trials had unsupported
figures. That was wrong in both directions. It excluded a real 1,430-day movement because
the sponsor reworded an endpoint in the same filing, and worse, it created a laundering
route: a sponsor wanting a delay gone from the comparable total need only reword the
endpoint. A guard the subject can defeat by editing prose, in the direction that flatters
them, is not a guard. The three-state classification above replaced it.

**Correction 3: the headline was downgraded.** "677 days is remarkable" became "677 days is
the 85th percentile", on this project's own evidence, in the project's own README.

**Correction 4: a rule stated in prose and violated in code.** The report printed a pooled
all-strata section on every run, for as long as the rule against pooling had existed, because
a rule that lives only in a document has already been broken somewhere nobody looked. The
function now refuses to compute a pooled rate rather than merely not printing one.

**Correction 5: two trials lost to a bug and recovered.** The version cache wrote each fetch
straight to its target path, so an interrupted run left a truncated file that every later
read of that trial failed on. Two NIH trials stored a parse error in place of a measurement.
Fixed at the source under a written amendment procedure, then re-measured successfully,
which is what closed the NIH stratum from 58 to 60.

**Rounding.** The industry median is 239.5 days and is reported as 240 throughout. All
percentiles are linearly interpolated.

## What this does not license

- **No outcome claim.** There is no outcome variable here. This study does not know which of
  these trials succeeded, which sponsors raised money, or what any of it preceded.
- **No prediction.** Nothing here has been validated out of sample against anything.
- **No motive.** Why a date moved, or did not, is not observable from a registry diff. Slip
  has many ordinary causes: enrolment, regulators, honest rescoping, financing.
- **No time series.** Every rate is one look at the registry. Whether this is getting better
  or worse is a different study.
- **Not novel terrain, and this is the sharpest objection to the headline.** Trial delay is
  a documented literature: Shadbolt et al., JAMA Network Open 2023, find roughly one in five
  RCTs complete on time, with a median delay of 12.2 months. Four in five not completing on
  time and four in five carrying a passed date are close enough that they have to be
  separated explicitly, and this document does not yet do it. The distinction the measure
  actually turns on is whether the sponsor revised the date **before** it passed, which is
  forecasting, or only after, which is not; a delayed trial whose date is revised
  prospectively every time never contributes a stretch. That distinction is measurable from
  `held_days`, which the engine already computes, and it has not been measured. Until it is,
  the frequency result should be read as consistent with the delay literature rather than as
  additional to it. Registry version histories have been assembled at far larger scale
  than this by others. Adjacent published work links trial timing and firm behaviour
  (Guenzel & Liu, RFS 2026), running the causal arrow the other way. What we could not find
  is work on how long a lapsed date is carried, as a disclosure behaviour in its own right.
  "We could not find" is the strongest form of that claim available without a systematic
  review, and it is the form used here.

## Reproducing this

```bash
python3 -m research.cohort --report     # prints the snapshot id beside the figures
python3 -m pytest tests/test_cohort_store.py -q
```

The report refuses to describe the snapshot as current if the store has moved since the
freeze. The store is `data/cohort/results.jsonl`, one row per trial; superseded measurements
are kept in `results-archive.jsonl`. The frozen figures are in `data/cohort/snapshot.json`
under the id `cohort-65fdf1f71b1d`, and a test recomputes every one of them from the store
and compares field by field.
