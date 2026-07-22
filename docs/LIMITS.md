# Limits

What each guard actually proves, stated at the strength the evidence supports and no
higher. Everything here was found by breaking the thing and watching what happened, not
by reading the code and reasoning about it.

This file exists because the project's pitch is that it does not flatter itself. A judge
who finds one of these unaided has found a hole. A judge who reads them here has found a
team that already looked.

## The ledger detects modification, and now deletion, with one caveat

`verify()` walks the hash chain and recomputes each link. It catches any edit to a byte
inside a hashed payload. On its own that is all it catches: a bare hash chain proves the
**presented** chain is self-consistent, never that it is the **original** chain.

Verified before the anchor existed: deleting the newest entry left `verify()` returning
`True`, and replacing the whole file with a freshly built valid chain whose claim read
"Rocket is comfortably funded and no financing is required" also returned `True`.

`orchestrator/anchor.py` closes that by recording the head hash and entry count outside
the chain and comparing on render. Verified by running each attack:

| Attack | Badge |
|---|---|
| clean ledger | intact |
| edit one byte inside a hashed payload | tampered |
| delete the newest entry | truncated or replaced |
| replace the file with a valid chain | truncated or replaced |
| delete the anchor file itself | truncated or replaced |

The last row matters: a missing anchor fails closed rather than green.

**The residual limit, and it is real.** The anchor lives in `data/ledger.anchor`, which the
same process writes. An attacker who rewrites the ledger and the anchor together defeats
it. This raises the bar from "edit one file" to "edit two consistently"; it does not make
the record immutable. Say "detects tampering, deletion and replacement of recorded
decisions, given the anchor was not also rewritten". Never say "immutable" or
"append-only". Closing this properly needs the anchor somewhere the writer does not own:
a commit, a signature, or a second machine.

## The fabrication guard catches invented magnitudes, not wrong units

`_fabricated()` flags any number in the model's output that appears nowhere in its input.
The rule is deliberately not "no digits", because quoting a figure from the belief's own
claim text is quotation rather than invention.

Verified behaviour, given an input containing `-14.5` and `10.4`:

| Model output | Flagged |
|---|---|
| "The gap is 47.2 months" | yes, caught |
| "The funding gap is -14.5 **years**" | no |
| "The shortfall is 14.5 **million dollars**" | no |
| "Runway fell 10.4**%**" | no |
| "The gap is roughly **fourteen** months" | no |
| "Runway ends about **twice as long** as assumed" | no |

So a correct magnitude wearing the wrong unit, scale, or sign passes, as does any
quantitative claim expressed in words. The guard bounds invention. It does not bound
misuse of a number it was legitimately given, and it cannot see numbers that are not
digits.

Stronger versions, in increasing cost: normalise Unicode and detect number words before
scanning; require quoted figures to carry the unit and entity from a single contiguous
source span; or forbid quantitative expressions in generated prose entirely and render
every figure from the application.

## The provenance test detects unintended displayed literals

It parses rendered HTML, extracts every number-like token from text nodes, and asserts
each appears in `data/snapshot.json`. It caught a planted `9999` and a template-computed
value, both watched failing.

What it does not establish:

- **Substring, not equality.** `"%.3f"` of `-0.5913757700205339` renders `-0.591`, a
  literal prefix of the stored value, and passes.
- **Text nodes only.** SVG coordinates, stroke widths and other attribute values are never
  examined. This is deliberate, since geometry is not a claim about the world.
- **Presence, not correspondence.** A number can be real, present in the snapshot, and
  attached to the wrong row, field, unit or sign. The check cannot tell.
- **Rendering fidelity is unproven.** Verified by mutation: setting `prior_gap_months` to
  `99.9` while the page still displayed `8.4` left every test green, as did setting
  `runway.cash` to `1.0` while the page still displayed `$50M`.

The upgrade is per-element binding: every semantic figure carries the record and field
path it came from, and the test resolves that path and asserts the formatter's exact
output. Global substring matching then stays as defence in depth.

## Lapsed-versus-future is decided at build time, and the date is now pinned

`build()` splits pivotal trials on `date.today()` unless an `as_of` is passed. Two
consequences:

- A committed snapshot's classification is a statement about the day it was built. Rebuild
  it later and rows can move from future to lapsed without any source data changing.
- Equality is not pinned. A completion date falling exactly on the build date currently
  counts as future, by `>=`, and that choice is incidental rather than argued.

Month-only registry dates (`2028-04`) are parsed to the first of the month, which is the
conservative direction, but it is a parser default doing policy work.

**Half closed.** The snapshot now carries its own `as_of`, written once by
`apply_displays()` and never re-read from the clock, and everything derived from it reads
that field. The thesis-break timeline's "today" marker is that pinned date, so a committed
snapshot draws the same picture next year that it draws today, and a test asserts the two
agree. What is still open is the split itself: `build()` is called during a rebuild, which
needs credentials and a network, and it is that call that still reads the wall clock. So
the file no longer reinterprets itself on read, and a rebuild still reclassifies.

## The derivation names a record; nothing resolves it

Each row of the funding-gap table now carries the record it came from: an XBRL tag with
the CIK and filing date, or a numbered ClinicalTrials.gov version with the date the
sponsor submitted it. That is a real improvement over "this number is in the snapshot
somewhere", and it is less than it looks.

The test asserts that a row claiming a tag carries a non-empty record string. It does not
fetch the filing, resolve the tag, or check that the value on that record equals the value
in the row. The record is an assertion the builder makes about itself. A row that named
the wrong version would pass every check here.

The two things that are checked, and were watched failing:

- the result row equals the contract's own `gap_months_1f` (mutated the timeline's gap to
  `-99.9`, three tests failed)
- every rendered figure is a substring of the snapshot (planted `8888` in the derivation
  partial and in an SVG label; the provenance test named both)

The upgrade is the same one the provenance section already names: resolve the record and
assert the formatter's exact output against the field it claims.

## The timeline is drawn from the snapshot, and its geometry is unchecked

The thesis-break timeline recomputes the exhaustion date and the lapsed-anchor gap from
raw fields rather than copying the contract's strings, on purpose: an independent
recomputation that disagrees is a defect worth catching, and a test asserts the agreement.
That test caught a mutated gap.

Not checked: whether the picture is legible. Marker x positions are asserted to fall
inside the axis, and nothing more. Two markers a few days apart overlap, their labels
collide, and every test stays green. On RCKT the filing and lapsed markers sit 39px apart
and are readable only because they were given different label rows by hand. A contract
whose dates cluster differently will draw badly and say nothing about it.

## The queue is a second opinion, and shows only what one snapshot can say

The monitoring queue is a second computation over the same contracts, so it can disagree
with the first one. Two checks exist to make that disagreement loud rather than quiet: its
breach and lapse counts must equal the command bar's, which reaches them by a different
route (`verdict` versus the sign of `gap_months`), and every contract in the snapshot must
appear in it. Both were watched failing.

What it deliberately does not have:

- **No "newly", and no "since last week".** Every such state is a comparison against a
  previous look, and there is one committed snapshot with nothing to diff against. The
  first version of the state list said "newly breached" and could not have known. A test
  now rejects `newly`, `since last` and `moved since` in any state label, and the page
  states the absence rather than leaving it to be noticed.
- **No changed-SEC-tag-path state**, for the same reason. `Runway.provenance` records which
  tag each figure resolved through, so the check becomes possible the moment a second
  snapshot exists, and it does not exist yet.

One defect it shipped with, found by looking at the page rather than by a test: rows whose
burn estimate is unreliable printed a gap figure beside "burn estimate unreliable". No
column called it a rank, and the existing no-rank test passed on it, because that test
looks for a plain-integer rank cell on `/contracts`. Printing `2.6 mo` next to a row the
system says is not rankable ranks it in the reader's head anyway.

The interesting part is the test, not the bug. `test_srpt_has_no_rank_number` was checking
one page for one shape of violation, so the rule it was supposed to protect could be broken
somewhere else and stay green. Confirmed rather than assumed: adding a gap column to the
flagged table on `/contracts` still passes it today. The rule is now stated once and
checked over every page that lists contracts, and the narrow test is kept as defence in
depth rather than replaced.

A second check was hollow the same way. The number-provenance test ran over four routes,
all of which render a negative funding gap, so the positive branch of the derivation
partial was never on a tested page. A literal planted in that branch went undetected, and
was briefly mistaken for a limit of the provenance check itself. It was not: the branch was
simply never rendered. `/contract/BEAM` is now in the parametrize because BEAM is the only
reliable contract with a positive gap, and the same planted literal now fails.

Both are the same lesson, which is the lesson this whole file exists for: a check that has
only ever been watched passing on the one case it was written for is not yet evidence.

The threshold for "approaching breach" is six months. That is a judgement, not a finding:
a quarter is too tight to act on and a year is not news. Nothing validates it.

## The reported slip figures, audited twice, and the second audit corrected the first

`total_slip_days` subtracts registered completion dates across successive registry
versions. That is a delay only if both dates describe the same commitment, and nothing
checked, because the fetcher reads each version's status module for the date and never
read the endpoint or the enrolment sitting unread in the same cached response.

**The first audit overstated its own finding, and this is the more instructive half.**
It treated any endpoint difference as a scope revision, and reported that five of seven
trials had unsupported figures. But an endpoint is free prose, and an exact string
comparison cannot tell a reword from a redefinition. On `NCT04248439` the endpoint went
from "Phenotypic correction of bone marrow colony forming units after infusion of RP-L102"
to "Bone Marrow (BM) Colony-Forming Cell (CFC) Mitomycin-C (MMC) resistance". In Fanconi
anaemia gene therapy, MMC resistance of bone marrow colony-forming cells is *how*
phenotypic correction is measured. Those may be the same endpoint, named more precisely.

That mattered in two directions, and the second is worse than the first:

- **false refusal**: a real 1,430-day movement was excluded from the total because the
  sponsor reworded the endpoint in the same filing
- **laundering**: a sponsor wanting a delay gone from the comparable total need only
  reword the endpoint, and the guard would oblige. A guard the subject can defeat by
  editing prose, in the direction that flatters them, is not a guard.

So the classification now separates a change to a **count or enumeration**, which no
wording explains away, from a change to **free prose**, which cannot be adjudicated from
the text at all. Three totals, never two:

| Trial | Reported | Established | Contingent | Upper bound | Refused |
|---|---:|---:|---:|---:|---:|
| PRME NCT06559176 | 122 | 122 | 0 | 122 | 0 |
| BEAM NCT05885464 | -1826 | -1826 | 0 | -1826 | 0 |
| RCKT NCT04248439 | 1008 | -422 | 1430 | **1008** | 0 |
| RCKT NCT06092034 | 943 | 0 | 0 | 0 | 1 |
| SRPT NCT03992430 | 760 | 33 | 0 | 33 | 2 |
| SRPT NCT06246513 | 32 | -27 | 0 | -27 | 1 |
| SRPT NCT06128564 | -2463 | -1031 | 0 | -1031 | 1 |

Read the two Rocket rows together, because they fail differently:

- **NCT04248439 is contingent, not refused.** Its upper bound is exactly the reported
  1,008 days. If a human reads those two endpoint descriptions as the same commitment,
  the original figure was right all along. The first audit said the supported figure was
  -422 and stopped there, which was an overcorrection.
- **NCT06092034 is genuinely refused.** Its enrolment went from 12 to 14. That is a count,
  and no reading of any endpoint text rescues it.

**What this does not touch.** The 677-day expired-date result is one version carrying an
already-passed date: one version, one date, one clock, no comparison between commitments.
The funding gap compares the current registered date to the runway. Neither depends on
promise identity and neither is affected by any of the above.

**The residual limits, and there are four.** Establishing continuity needs `data/cache/`,
which is gitignored, so the classification is computed at build time and committed; an
uncached version classifies as uncertain. Only three dimensions are compared. A sponsor
can change what a trial measures in ways none of them capture. And the contingent state is
honest but unresolved: it hands the reword question to a human and nothing here makes that
judgement cheap.

## A non-atomic cache write, found by interrupting one, and now fixed at the source

`_cached()` in `engine/ctgov_history.py` wrote a fetched version straight to its target
path. Killing a run mid-write therefore left a truncated JSON file that parses as corrupt,
and every later read of that trial failed on it, because `_cached()` returns early whenever
the path exists and cannot tell a short file from a complete one. Found by timing out a
cohort run: one file of 335, `NCT03919071-v356.json`, 20,107 bytes, and it took down five
tests that had nothing to do with it.

It cost measurements as well as tests. Two NIH trials in the random cohort, `NCT04269902`
and `NCT04071223`, stored a `JSONDecodeError` in place of a result and dropped that
stratum's n by two. Both were re-measured successfully once the fix was in.

**Closed 2026-07-22**, at the source, under `docs/AMENDING_PROTECTED_MODULES.md` and with
the owner's approval. The write goes to a temp file beside the target and is renamed, which
is atomic on POSIX. All four conditions were checked, including a byte-for-byte diff of
every module gate's output before and after, and the test
(`tests/test_ctgov_cache.py::test_interrupted_cache_write_leaves_no_readable_entry`) was
watched failing against the old code.

The graceful degradation stays and is still doing work: `engine/dimensions.py` and
`research/backtest.py` skip an unreadable entry and classify that version as unestablished,
which is the same answer they give for a version nobody has fetched. A cache entry can be
corrupted by something other than an interrupted write. But it is worth being clear about
what it costs, because it is the reason this sat unfixed: a corrupt entry silently lowers
the number of versions a comparison can see, so it makes continuity harder to establish
rather than easier. It fails toward refusing to state a number, and a failure in the safe
direction is one that can survive a long time without anyone minding.

## An append-only store that inflated its own n

`data/cohort/results.jsonl` is append-only and the run is resumable, which is right for a
long fetch-bound job and wrong for counting. A trial measured twice appends twice. A
background pass and a manual merge overlapped, 49 of 180 rows were duplicates, and a
published report of n=169 was really 131 distinct trials. Every rate computed from it was
slightly off, all in the flattering direction, and nothing looked wrong: more rows reads as
more data.

It is the same shape as the ledger problem this project already solved and the same shape
as the truncated cache entry above. A store that only ever grows will eventually be read as
if growth were evidence.

Closed: `load_results()` deduplicates on read, last row wins, and a row carrying refusal
reasons beats one that predates them regardless of write order. The report prints distinct
trials beside stored rows so the two are visible together. Three tests assert they cannot
diverge, including one asserting the printed n equals the distinct count.

**The residual is now closed too, 2026-07-22.** Deduplicating on read fixed the readers this
project owns and left the inflated view sitting in the file for anyone else. The store is
compacted to one row per trial and the 123 superseded rows are appended to
`data/cohort/results-archive.jsonl`, so nothing is destroyed: an earlier measurement of the
same trial is evidence about the measurement process even when it is not evidence about the
trial. Three tests hold it there. One asserts the raw file agrees with the deduplicated
read. One asserts every archived trial is still measured in the live store, so compaction
can never be the thing that loses a measurement. One scans the shipped modules and fails if
anything outside `research/cohort.py` reads the store directly, which is what keeps a future
consumer from reintroducing the inflated view after the next resumable run appends.

Compaction moved no published figure, which was checked by reporting before and after rather
than reasoned about.

**And the compaction itself shipped with the project's own defect pattern, caught before
release.** Its first version selected winners by calling `load_results()`, which re-reads the
file, then compared object identity against rows it had not loaded. It matched nothing and
archived all 363 rows. It failed loudly, printing "0 rows kept", and the store was restored
from the archive it had just written. The root cause was two copies of the deduplication
rule, one in `load_results()` and one implied by `compact()`. There is now one, `_dedupe()`,
and both call it. A cohort study measured by a second implementation measures the second
implementation, and the same is true of a cohort store compacted by one.

## The dead-date measure cannot see a sponsor that lapses and goes quiet

**Found 2026-07-22 by an adversarial review of the cohort write-up, confirmed against the
store, and open. It affects published figures and it is the most serious item in this file.**

`carried_until_corrected()` walks consecutive registry versions and emits a stretch for each
pair where the earlier version's completion date had already passed when the later one was
filed. Every stretch therefore needs **a later filing to close it**. A trial whose date
lapsed and that never filed again produces no stretch at all and is counted as never having
carried a dead date.

So the quantity actually measured is not "carried an already-passed date". It is **"carried
an already-passed date and subsequently filed something"**. The purest instance of the
behaviour this project exists to surface, a sponsor that lets a date expire and then goes
silent, scores as clean.

That is not a hypothetical. Counting trials whose most recent registered date is in the past
and still typed ESTIMATED, as of the snapshot date 2026-07-22:

| Stratum | carried at some point (stretch measure) | carrying one now | invisible to the stretch measure | median versions |
|---|---:|---:|---:|---:|
| INDUSTRY | 80.0% | 8.3% | 4 | 9 |
| NIH | 80.0% | 0.0% | 0 | 106.5 |
| OTHER | 61.7% | 31.7% | 15 | 4 |
| OTHER_GOV | **53.3%** | **45.0%** | **20** | 2 |

**These figures replace wrong ones published for one revision of this file**, which read
83.3% / 70.0% / 85.0% / 96.7%. That version read the date's ESTIMATED/ACTUAL type from a
helper that did not return it, compared `None` against `"ACTUAL"`, and so counted every
completed trial that had correctly recorded its actual completion date as carrying a lapsed
one. The filter never fired. It is the same defect shape as the `status` bug three paragraphs
down and as everything else in this file: a check that silently does not apply is
indistinguishable from a check that passes, and this one produced a more dramatic number in
the flattering direction and survived a manual review. Corrected 2026-07-22 under snapshot
`cohort-8326c1c1e964`; a test now asserts a past ACTUAL date does not count.

**The cross-stratum comparison is inverted by this**, and on the corrected figures the two
measures reverse the ordering, with industry and NIH tied at the top of the stretch
measure. OTHER_GOV is lowest on the stretch
measure and highest on point prevalence, with 20 of its 27 currently-expired trials invisible
to the stretch measure because they lapsed and never filed again. `docs/COHORT.md` and
`docs/WRITEUP.md` both said government and academic sponsors "did it less often". On this
evidence they do it more, and the measure could not see it.

The ordering follows filing frequency, across four strata and untested as a relationship. The spread is large: median registry versions per trial is 2
for OTHER_GOV, 4 for OTHER, 9 for INDUSTRY and **106.5** for NIH.

**What survives.** The Rocket 677-day case is untouched, because it is one version carrying
one already-passed date against one clock and needs no later filing to exist. **Resolved
2026-07-22:** point prevalence is now the primary frequency measure, the stretch measure is
retained and labelled "lapsed and subsequently filed again", and the silent population is
reported as a result rather than as a gap.

**What does not survive.** Any statement ranking strata by how often they carry a dead date.

## Every published duration is measured on completed spells

Both duration measures, per-stretch and per-trial longest carry, are computed from lapses that
a later filing ended. A lapse still open contributes no duration, so the distributions describe
lapses that are over and are length-biased toward those that resolved. The trials a monitor
would actually alert on, the ones carrying an expired estimate right now, are counted in the
point-prevalence figures and appear in no duration figure anywhere.

What that forecloses: any statement about how long an open lapse will run, or where the
replacement date lands when it arrives. Neither is measured and neither can be estimated from
this data. Recorded in `docs/PARKING.md` as the next measurement.

## A stretch is not an episode, and the 2.4x is largely a filing-frequency artifact

**Found in the same review, confirmed, and open.**

`docs/WRITEUP.md` claimed "a trial contributes one stretch per episode". That is false. A
stretch is emitted per consecutive version pair, so one lapse spanning many filings
contributes many overlapping rows measuring the same expiry to successively later endpoints.
They are nested prefixes, not independent observations.

`NCT02931474` has 97 registry versions, **3** completion-date revisions, and **91** stretches,
with durations running 42, 114, 356, 357, 359, 364, 400, 402 and upward. At most three real
episodes produced 91 rows, and that single trial is 18% of the NIH stratum's entire duration
distribution. The top five NIH trials are 49% of it.

Because the row count tracks how often a sponsor files for unrelated reasons while a date
sits dead, the duration distribution is weighted toward frequent filers. Measuring one
observation per trial, its longest carry, closes most of the gap:

| | INDUSTRY | NIH | ratio |
|---|---:|---:|---:|
| median over all stretches (published) | 240 | 567 | **2.4x** |
| median of per-trial longest carry | 390 | 590 | **1.5x** |
| p90 over all stretches (published) | 996 | 1,589 | 1.6x |
| p90 of per-trial longest carry | 1,384 | 1,617 | 1.2x |

The "2.4 times longer" figure appears in `README.md`, `docs/SUBMISSION.md`,
`docs/COHORT.md` and `docs/WRITEUP.md`, and in each place it is offered as the justification
for the rule that strata may not be pooled. **The rule is probably still right**, since the
frequencies also differ once the measure above is corrected, but the specific evidence
offered for it is unit-dependent and roughly halves under the per-trial unit.

Note also that the industry median itself is unit-dependent: 240 days per stretch, 390 days
per trial. Neither is wrong. Only one of them is currently labelled.

**Both were resolved by the owner on 2026-07-22.** Point prevalence became the primary
frequency measure and per-trial longest carry the primary duration measure, with the
stretch-based figures retained as a labelled sensitivity. "2.4x" is removed as a headline
everywhere and the no-pooling rule is re-justified on three independent differences:
reconciliation behaviour, point prevalence, and filing frequency. The store was re-measured
and the snapshot re-frozen as `cohort-8326c1c1e964`.

**Why this is the same lesson as everything else in this file.** The cohort deliberately
measures with the product's own code, on the argument that a study measured by a
reimplementation measures the reimplementation. That argument is sound and it has a cost
nobody stated: a defect in `carried_until_corrected()` is shared by the product and the
study, so the study cannot act as an independent check on the product. It did not catch
this. An adversarial reader did.

## The prose guard, and exactly what it proves

Prose was the last unguarded surface here. Four rounds of adversarial review found the
measured figures clean every time and the retyped ones wrong repeatedly: a median printed as
106 where the field holds 106.5, fixed in one file and missed in five others; "at least"
silently dropped from a count; a median-date-changes column off by one because the field it
was typed from counts the initial registration; and a phrase reported as corrected in two
consecutive rounds whose replacement never matched and did nothing.

`tests/test_prose_figures.py` is the console's number-provenance test pointed at markdown.
Every numeric token in a table row or a bolded claim in the five claim documents must be a
representation of a snapshot field or appear in an enumerated `NON_SNAPSHOT` list with its
source. That list is the enforced version of the write-up's "figures that are not snapshot
fields" paragraph, which drifted out of date twice while it lived only in prose.

**What it does not prove, verified by mutation rather than assumed.** It is a presence check,
so it cannot catch a small-integer error: reverting the median-date-changes column from 0 back
to 1 passed it, because "1" appears somewhere in the snapshot and in the regulation citation.
That is the same limit this file already records for the console's provenance test, and it is
exactly the defect class that shipped. The headline table's last two columns are therefore
additionally bound cell-by-cell to the fields they claim to render, by name, and restoring the
off-by-one fails that test. Every other table in the document is presence-checked only.

Also guarded mechanically, because it failed once: a hedge present in four claim documents and
absent from the fifth. One fix pass deleted the only qualifier in `docs/SUBMISSION.md`, the
most externally facing of the five, while the other four kept theirs.

The remaining exposure is a figure that is correct, present in the snapshot, and attached to
the wrong row or label. Presence is not correspondence, and only two columns have
correspondence.

## The reconciliation split conditions on a revision existing

**Found 2026-07-22 by the second council round, confirmed, and disclosed rather than fixed.**

The `held_days` split counts revisions, so a trial that lets a date lapse and never files
again contributes to neither the numerator nor the denominator. The measure of
non-reconciliation is therefore computed only over sponsors that reconciled at some point,
which is Correction 6's defect one level up.

It is not small. Trials that never revised a date at all: 8 of 60 for INDUSTRY, 5 of 60 for
NIH, 22 of 60 for OTHER, and **32 of 60 for OTHER_GOV**. The worst-reconciled trials in the
frame are structurally excluded from the reconciliation statistic, which is why point
prevalence is reported beside it and why the two must be read together.

## A revision filed after a lapse is not automatically a failure to reconcile

**Found 2026-07-22 by the second council round. It halved a published headline.**

An earlier draft reported that 52.4% of industry date revisions were filed after the date had
already passed, and presented that as non-reconciliation. Half of those revisions, 33 of 66,
set the date to ACTUAL: the sponsor recording when the trial finished. For a trial that ran
late that filing necessarily lands after the earlier estimate expired, and it is the update
42 CFR 11.64(a)(1)(ii) requires within 30 days of actual completion.

So the draft quoted a regulation to argue the behaviour was unlicensed while that regulation
licenses half the observations, and it called the same filing "the system working" in one
section and a failure in another, a hundred lines apart. The arithmetic was correct
throughout; the sentence it supported was not, and no numeric check could have caught it.

The surviving claim is the estimate-to-estimate subset: 33 of 126 industry revisions, 26.2%,
and 24 of the 52 industry trials that revised at all. Both are snapshot fields now
(`revisions_after_lapse_to_estimate`, `trials_with_lapse_to_estimate`) rather than derived in
prose, because a figure that is not a snapshot field is a figure no test can check.

## No pooled all-strata rate, and the report used to print one

NIH sponsors carry a dead date about as often as industry ones and roughly two and a half
times as long, so the strata are not poolable and every published rate is labelled by
stratum. That was stated in `docs/COHORT.md` and violated in the code: `report()` iterated
`STRATA + ("ALL",)` and printed a pooled section, on every run, for as long as the rule had
existed.

It is the same failure this file keeps recording. A rule that lives only in prose has
already been broken somewhere nobody looked.

Closed by removing the section and by making `stats()` raise on any stratum name outside the
four, so a pooled figure cannot be produced at all rather than merely not being printed. Two
tests: one asserts the report prints no pooled section, one asserts the frozen snapshot's
strata are exactly the four measured ones.

## Every published rate cites a snapshot id

A rate with no version is a claim about whatever the store happened to contain the day
somebody read it. `data/cohort/snapshot.json` freezes the measurement under a
content-addressed id (currently `cohort-5b03269658b8`, 240 trials, 60 per stratum), hashed
over the measured rows and the frame together, because a rate means nothing without the
denominator that produced it.

What this establishes: a figure citing an id can be checked against the store that produced
it, and a snapshot cannot be quietly re-cut under the same name, because changing one
measured row changes the id. A test recomputes the id from the store and fails when the two
disagree, so a citation cannot rot silently.

What it does not establish: that the figure was copied into the prose correctly. The
snapshot is checked field by field against a recomputation from the store, and the prose is
not checked against the snapshot. That is the same gap the rendering-fidelity section above
describes, in a different place.

## Untested, and known to be

- ~~The decision receipt's two hashes.~~ Closed. The receipt used to travel in the query
  string and a hand-written URL could forge every field; it is now read from the ledger's
  last entry at render time, with a test that requests the page carrying forged values and
  asserts the real ones render.
- Whether a rebuild is reproducible. Nothing asserts that building twice from the same
  inputs produces the same bytes, so a hand-edited snapshot would not be detected.
- Concurrency anywhere. Two decisions appended at once are untested; the ledger has no
  compare-and-swap on the head. This applies to the analyst belief form too: two analysts
  confirming at the same moment both read the same head hash and both append.
- Whether a belief written through the form is ever monitored. `POST /belief/new` appends
  a real CREATE entry to the real chain, and the redline loop still runs off the committed
  snapshot rather than off the ledger's live cards. So the form records a belief, and
  nothing yet re-reads it on the next rebuild. Say "records a belief", never "starts
  monitoring it", which is what the button used to imply.

## Where these came from

The first four sections were produced by a three-model adversarial review (Claude, Cursor,
Codex) asked specifically which existing checks were hollow, and then every claim it made
was run against the code before being written down here. Two of its predictions were
right, verified above. The transcript is in `runtime/council/` in the vault repo.
