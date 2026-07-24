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

## Granite prose carries no quantities, and that is all this guard proves

**Replaced 2026-07-23. The two rules before it are recorded here because the way each one
failed is the argument for the one that followed.**

The first rule flagged any number in the model's output that appeared nowhere in its
input, deliberately not "no digits", on the reasoning that quoting a figure from the
belief's own claim is quotation rather than invention. It let a correct magnitude through
wearing the wrong unit, the wrong scale or the wrong sign, and it could not see a
magnitude written as a word.

The second rule bound each magnitude to a unit and a sign and refused any value absent
from the input. That closed wrong units, wrong signs and number words. It read as
provenance and was not. The binding carried no **field**, so any bare digit anywhere in
the input authorised that magnitude in the metric's own unit. An audit demonstrated it
against ordinary analyst prose, and the examples are worth keeping because none of them
looks like an attack:

| Text in the analyst's own thesis | Model output it authorised |
|---|---|
| "Phase **3** readiness" | "the gap has narrowed to **3 months**" |
| "across **12** sites" | "cash runs out **12 months** before the readout" |
| "**2** arms" | "only **2 months** of runway remain" |
| conviction recorded as **3** | "the shortfall is **3 months**" |

`Quantity(value, unit, sign)` never established which field a number described, and no
further unit arithmetic was going to. **Any claim that it constituted semantic-field
binding is withdrawn.**

So the rule is now that the model does not measure. **`_quantitative()` rejects
model-authored quantitative expressions.** It covers digit forms, common number words,
dates, durations, percentages, ratios, signs, and contextual word-form dates:

- every decimal digit, signed, decimal, percentage, ratio, scientific notation, and the
  digits inside an identifier. `\d` is Unicode-aware, so non-ASCII decimal digits are
  caught with the ASCII ones;
- quantities written as words, including the plurals and inflections of the roots already
  on that list, so "the shortfall doubled" and "slipped by hundreds of days" are refused
  alongside "double" and "hundred";
- ordinals and month names, by which a date arrives carrying no digit at all;
- **dates composed out of words that are individually allowed.** "may", "first" and
  "second" are ordinary discourse in this vocabulary and are excluded from the word scan
  on purpose. The exclusions used to compose: every part of "May first" was allowed, so a
  registered completion date passed every scan. `_DATE_PHRASE` matches the composition
  directly, which closes "May first", "May the second", "the first of May" and "Sept.
  second" while leaving "the first assumption" and "the sponsor may revise it" clean.

A response containing any of these is discarded whole and the deterministic stub answers.
Nothing is partially sanitised, because a sentence with its number deleted is a sentence
whose meaning nobody has checked.

**What this proves, exactly:** that no quantity authored by the model reaches the page.

**What it does not prove, and each of these is real:**

- **It does not prove the qualitative judgment is correct.** "The approved funding
  assumption no longer holds" passes this guard whether or not it is true. The guard
  bounds the *form* of the model's output and says nothing about its accuracy.
- **It does not independently prevent causal, feasibility or fraud language.** "The
  sponsor is concealing a delay" carries no quantity and passes here. `orchestrator/
  lexicon.py` is the separate control for that, and it runs on the same response; neither
  guard covers the other's failure, and neither should be described as covering it.
- **Comparative language stays allowed, without magnitude.** "widened", "moved later",
  "above the threshold", "below the threshold", "the approved value", "the current value"
  and "human review is required" all pass, by design. That is the vocabulary the model is
  left with, and a guard that took it away would leave the model unable to say anything.
  What is refused is the size of the move, never its direction.
- **Deterministic fields remain the only displayed quantities.** Every figure on screen
  is rendered by Python and Jinja from a named snapshot field. That is what makes this
  policy affordable: the model never needed to carry a number.
- **The classification's confidence was the one model-authored number that still reached
  a human, and it no longer does.** `_quantitative()` scans the rationale, not the JSON
  object around it, so the model's own `confidence` field went straight to the redline
  template, and a second copy travelled inside the memo header `build_challenge` composed
  from the same field. Both render sites are removed. The value is still recorded on
  `Classification` and in the frozen snapshot, because discarding a measurement to tidy a
  display is the wrong direction; it is simply never shown, and `classification.source`
  stays on the page so the reader still sees which of the two answered. It is **not**
  mapped to a high/medium/low label either, since that is the same model-produced
  quantification wearing words. Memos built before this rule carry the token in their
  header, and one of them is in the committed demo snapshot, which is frozen evidence and
  is not rewritten to tidy a string, so `without_model_confidence()` strips it at the read
  site. `tests/test_claim_integrity.py` renders every GET page and fails on the value.
  What that does not prove: it reads the value the snapshot happens to hold, so a memo
  carrying a differently formatted figure would pass. The structural half is the second
  assertion, that `build_challenge` no longer composes the field into prose at all.
- **The stub fallback is quantitative by design and is not scanned.** It states
  engine-computed values because it is Python reading the fields the page renders.
  `Classification.source` records which of the two answered, and the page shows it.
- **Some words and numeral forms are accepted on purpose, and here they are.** Nothing
  below is an oversight; each was measured against the shipped guard rather than assumed.

  *Ambiguous words, standing alone.* "may", "first" and "second" pass on their own,
  because all three are ordinary discourse in this vocabulary and a guard that fires on
  correct qualitative prose is a guard someone switches off. They no longer pass once
  composed into a date. Also accepted: "couple", "score", "fortnight", "pair", "single",
  "nil", "nought", and the vague counts "many", "several", "few". "a couple of issues
  remain" is discourse rather than measurement, and blocking it globally would cost more
  than it buys. "quadrupled" is accepted because its root is not on the word list; the
  rule for that list is that a token belongs there only if its root is already on it, and
  an ever-growing list of individually plausible words is how a guard stops being
  reviewable.

  *Numeral forms outside the decimal-digit category.* Vulgar fractions (`½ ¼ ¾`),
  superscripts and subscripts (`² ₂`), enclosed forms (`② ➂`), and Roman numerals in
  either alphabetic (`XII`, `iii`) or Unicode (`Ⅻ`) form all pass. `\d` matches the Nd
  category and none of these are in it.

  The residual is a real hole and it is bounded by the same thing that makes the whole
  policy affordable: the model has no figure to launder in the first place, since the
  brief hands it directions and the page renders every value from a named field.
- **It is a backstop, not the primary control.** The prompt asks for non-quantitative
  prose in the first place. A model that complies never reaches this code, and the frozen
  demo rationale is digit-free without it. Both prompts now state the same rule the guard
  enforces. `ACTION_PROMPT` previously instructed the model to write quantities in words
  while the guard refused number words, so a compliant model produced a draft the runtime
  was built to discard; `test_prompt_examples_agree_with_the_guard` runs every worked
  example in both prompts through `_quantitative()` so that contradiction cannot recur.
- **`_draft_once` is dormant, and now follows the same scan-and-return invariant.**
  `draft_action` has no callers outside `orchestrator/granite.py`, so no model-authored
  Action prose ships today. It carried a real defect regardless: the guard scanned
  list-marker-stripped text and returned the unstripped original, so "2028. The registered
  expectation moved later." went out with its year intact. The exemption is deleted rather
  than narrowed, because narrowing it to two digits still ships "12. Human review is
  required." **The text scanned is now exactly the text returned**, and a test pins both
  the refusals and the byte-identity of an accepted draft.

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

## The opening frame is now measured, at one viewport, in one browser

**Added 2026-07-23 after the rule below was found broken.** `docs/STATUS.md` calls the
carried-expired row the thing that outranks the rest: visible at 1280x800 without scrolling
or clicking. That was measured true on 2026-07-21 and then stopped being true, because the
thesis-break chart and the binding trial's revision panel were added above it and pushed the
node to y=992 against an 800px fold. Nothing caught it, because the only checks that touched
the page asserted the number appeared *somewhere in the HTML*. Presence is not position, and
the narration would have been spoken over a different trial's smaller figure.

`tests/test_demo_frame.py` now opens a real browser at exactly 1280x800 and reads real
bounding boxes: the anchor row must sit above the fold, the binding trial's much smaller
carried-expired figure must not sit above it, and the refusal label must precede the number
it refuses and be rendered no more quietly.

What it does not establish:

- **One viewport, one engine.** 1280x800 in headless Chromium. A different window size, a
  different browser, or a different default font can move every number here. The demo is
  filmed at one size, which is why one size is pinned.
- **Position, not legibility.** Nothing measures contrast, overlap, or whether two markers
  collide. The section above still applies: markers a few days apart overlap and every test
  stays green.
- **It skips without Playwright**, which is a development extra rather than a
  `requirements.txt` dependency. On a clean clone only the document-order check runs, and
  document order is weaker: a section above could grow tall enough to push the anchor below
  the fold without any reordering. The count guard measures the clean-checkout tier with
  development extras disabled precisely so this skip is visible in the published numbers
  rather than hidden by a developer machine.

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
background pass and a manual merge overlapped, a large minority of rows were duplicates, and
a published trial count was really a row count. Every rate computed from it was
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
and still typed ESTIMATED:

<!-- generated: silence_note -->
Trials whose most recent registered date is in the past and still typed as an estimate,
against the stretch measure that cannot see them, as of 2026-07-22:
<!-- /generated -->

<!-- generated: silence_table -->
| Stratum | carried at some point (stretch measure) | carrying one now | invisible to the stretch measure | median versions |
|---|---:|---:|---:|---:|
| INDUSTRY | 80.0% | 8.3% | 4 | 9 |
| NIH | 80.0% | 0.0% | 0 | 106.5 |
| OTHER_GOV | 53.3% | 45.0% | 20 | 2 |
| OTHER | 61.7% | 31.7% | 15 | 4 |
<!-- /generated -->

**These figures replace wrong ones published for one revision of this file**, which read an
order of magnitude high for industry and near-universal for the government strata. That version read the date's ESTIMATED/ACTUAL type from a
helper that did not return it, compared `None` against `"ACTUAL"`, and so counted every
completed trial that had correctly recorded its actual completion date as carrying a lapsed
one. The filter never fired. It is the same defect shape as the `status` bug three paragraphs
down and as everything else in this file: a check that silently does not apply is
indistinguishable from a check that passes, and this one produced a more dramatic number in
the flattering direction and survived a manual review. Corrected 2026-07-22 under snapshot
`cohort-8326c1c1e964`, which is the historical id frozen at that moment and not the
current one; a test now asserts a past ACTUAL date does not count.

**The cross-stratum comparison is inverted by this**, and on the corrected figures the two
measures reverse the ordering, with industry and NIH tied at the top of the stretch
measure. OTHER_GOV is lowest on the stretch
measure and highest on point prevalence, with 20 of its 27 currently-expired trials invisible
to the stretch measure because they lapsed and never filed again. `docs/COHORT.md` and
`docs/WRITEUP.md` both said government and academic sponsors "did it less often". On this
evidence they do it more, and the measure could not see it.

The ordering follows filing frequency, across four strata and untested as a relationship. The
spread in median registry versions per trial is large and is rendered per stratum in the table
above.

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

`NCT02931474` has 97 registry versions, **2** completion-date changes, and **91** stretches,
with durations that climb from tens of days to years across nested prefixes of the same
lapse. A handful of real episodes produced 91 rows, and that single trial is a sixth of the
NIH stratum's entire duration distribution. (This line read "3 completion-date revisions" for
a while, the `n_pcd_revisions` field that counts the initial registration, which is the exact
off-by-one `docs/WRITEUP.md` warns about; the write-up renders `n_date_changes` and reads 2.)

Because the row count tracks how often a sponsor files for unrelated reasons while a date
sits dead, the duration distribution is weighted toward frequent filers. Measuring one
observation per trial, its longest carry, closes most of the gap:

<!-- generated: unit_table -->
|  | INDUSTRY | NIH | ratio |
|---|---:|---:|---:|
| median over all stretches | 239.5 | 567 | **2.4x** |
| median of per-trial longest carry | 390 | 590 | **1.5x** |
| p90 over all stretches | 995.6 | 1,588.8 | 1.6x |
| p90 of per-trial longest carry | 1,384.4 | 1,617.4 | 1.2x |
<!-- /generated -->

The per-stretch ratio appeared in `README.md`, `docs/SUBMISSION.md`, `docs/COHORT.md` and
`docs/WRITEUP.md`, and in each place it was offered as the justification for the rule that
strata may not be pooled. **The rule is probably still right**, since the
frequencies also differ once the measure above is corrected, but the specific evidence
offered for it is unit-dependent and roughly halves under the per-trial unit.

Note also that the industry median itself is unit-dependent, and the table above carries both.
Neither is wrong. Only one of them was labelled.

**Both were resolved by the owner on 2026-07-22.** Point prevalence became the primary
frequency measure and per-trial longest carry the primary duration measure, with the
stretch-based figures retained as a labelled sensitivity. "2.4x" is removed as a headline
everywhere and the no-pooling rule is re-justified on three independent differences:
reconciliation behaviour, point prevalence, and filing frequency. The store was re-measured
and the snapshot re-frozen as the now historical `cohort-8326c1c1e964`.

**Both ids in this section are historical and are kept as written.** Each names the state
of the store at the moment of the correction it describes, and a correction record that
renames its own subject is not a record. The published snapshot is now
`cohort-5b03269658b8`: later rounds added derived fields, and the id hashes the measured
rows and the frame together, so adding a field does not move it. No figure quoted from
either older id is offered as a current figure; the current figures are in the generated
blocks above, which name their own snapshot.

**Why this is the same lesson as everything else in this file.** The cohort deliberately
measures with the product's own code, on the argument that a study measured by a
reimplementation measures the reimplementation. That argument is sound and it has a cost
nobody stated: a defect in `carried_until_corrected()` is shared by the product and the
study, so the study cannot act as an independent check on the product. It did not catch
this. An adversarial reader did.

## The claim documents are generated, and exactly what that proves

Prose was the last unguarded surface here. Five rounds of adversarial review found the
measured figures clean every time and the retyped ones wrong repeatedly: a median printed as
an integer where the field holds a half, fixed in one file and missed in five others;
"at least"
silently dropped from a count; a median-date-changes column off by one because the field it
was typed from counts the initial registration; and a phrase reported as corrected in two
consecutive rounds whose replacement never matched and did nothing.

The first answer to that was a presence check over the retyped text, with an enumerated
`NON_SNAPSHOT` exception list. It had two structural holes, both measured rather than argued.
Presence cannot falsify a small integer: reverting the median-date-changes column from 0 back
to 1 passed it, because "1" appears somewhere in the snapshot. And an exception list is a
laundering route, which is how two real snapshot fields ended up listed as exceptions,
making both unfalsifiable.

**Both are gone, because the documents are no longer typed.** `research/render_writeup.py`
renders `docs/WRITEUP.md` in full and the figure-bearing blocks of the other four claim
documents, emitting every figure from a named snapshot field. `tests/test_prose_figures.py`
enforces two rules:

- **no numerals in prose, over the whole generator.** Every string constant in the module is
  checked for digits, not selected lines of the output; **every** numeric literal is rejected
  unless it appears in a declared table naming what it is for, indices and layout widths
  included. A figure cannot be typed into prose because prose cannot contain a digit.
- **the committed documents are byte-identical to a fresh render.** A figure cannot drift from
  the field it renders, because nothing copies it.

Several figures that were exceptions became fields instead, which is the difference between
the two designs: the anchor case's days carried and its two percentile ranks (`anchor_case`),
the clustering window parameters (`clustering`), and the two readings of a month-only date
(`month_convention`). A snapshot-wide `figures_hash` covers every published block, so a
hand-edit to one that is not in `strata` is caught even though the snapshot id, which hashes
only the measured rows, does not move.

**What this does not prove, and it is the whole of the residual.** A cell bound to the wrong
field renders wrongly and regenerates identically forever. That defect class is real: several
instances of it were caught during construction and by review, a ratio computed the wrong way
round and a block-table cell rebound to a different real field. The tests recompute every
table's cells, in every document, from the store by a second implementation, and pin the table
headers to independent literals so a header swap fails too. That is double entry, not proof:
where a figure sits in a sentence the recomputation does not cover it is unguarded, and a
shared misunderstanding of what a field means passes both implementations.

**A seventh review round attacked the guard rather than the figures, and it was right about
most of it.** What it demonstrated, each watched publishing a wrong figure with the whole
suite green, and each now a committed fixture:

- **The corpus was vacuous.** Twenty-two of twenty-three fixtures were caught by document
  staleness alone. Deleting the digit rule and the entire residual scan still scored
  twenty-three of twenty-three. Worse, the two fixtures aimed at the generator were caught by
  staleness too, and staleness is what a developer clears by re-rendering, which is the first
  thing anyone does after editing a generator. The corpus now re-renders a generator mutation
  before checking it, so only a real rule can fire, and the rule that fires is recorded.
- **Nothing caught a cell bound to the wrong field.** Now it does: the tests recompute every
  table's cells from `data/cohort/results.jsonl` by a second implementation that calls neither
  `stats()` nor the generator, plus the block-level figures that sit in no table. Double
  entry, not proof.
- **The exemption lists were read out of the module being checked.** The percentile-label list
  lived in the generator, so a reviewer added a figure to it and published the figure. It
  lives in the test now.
- **The literal rule allowed anything under a hundred**, and `4 * 31` published an invented
  minimum while a bare `60` published a methodology parameter the test had not run at. Every
  numeric literal in the generator must now be declared, with no magnitude exemption; a later
  round showed `ord("~")` and `0.5 / 2` slip past a magnitude rule, which is why there is none.
- **`CITATIONS` was `NON_SNAPSHOT` reborn.** Its values are exempt from the digit rule, and
  the laundering check only rejected figures that matched a real field, so an invented rate
  passed by construction. A citation may no longer carry a percentage or a
  thousands-separated count at all: those are the shapes a figure from this study takes.
- **`docs/LIMITS.md` was in neither guard** while carrying a full prevalence table and a
  hand-typed ratio, and it was where the one uncorrected copy of a wrong sentence was found.
  Its tables are generated blocks now and the scan covers fourteen documents rather than five.
- **A code span or a link hid a retyped figure**, because the scan blanked both before
  looking. It blanks ISO dates and URLs only.
- **One extra space in a block marker un-generated the block silently**, and `render()`
  reported success. Malformed markers are counted and refused.
- **The write-up quotes `research/cohort.py` verbatim and that file was scanned by nothing**,
  so a figure added to a quoted docstring published straight through. The quoted source must
  be digit-free.

**An eighth round attacked the hardened guard and the trusted roots.** It found the recompute
layer was inert: `check()` returned findings that no test read, so a wrong-field binding named
in plain English left the suite green. That is the eighth instance in this file of a correct
check nothing consults, and it is closed by one assertion over the whole of `check()`. It also
found that everything in the snapshot outside `strata` was a trusted root, and a hand-edit to
`anchor_case.days_carried` published a fabricated headline; `figures_hash` closes that. And it
confirmed the residuals below rather than refuting them.

**Ninth and tenth rounds hardened the recompute and the freeze.** The recompute layer covered
the write-up's tables and, from the eighth round, the four block tables in the other documents;
what round nine added was the column-oriented unit table, which its stratum-row check could not
see, and the pinning of three headers that were recomputed but unpinned. A wrong-field binding
in the unit table shipped green until then. Every generated table header is now pinned to an
independent literal so a swap fails against the literal rather than a copy of itself. Round
nine also surfaced a real latent bug, found by the wall clock rolling over mid-session:
`freeze()` read the clock each time, so a re-freeze walked every days-since-expiry figure
forward by a day. It now preserves an existing snapshot's `as_of`, which is a study parameter
and not the freeze moment, and because no data check can tell a right point-prevalence date
from a wrong one the date itself is pinned in a test. The end-of-month bound gained an
independent recomputation in the test rather than a comparison against a re-run of the function
that produced it, extended in round ten to the duration medians it first missed. Round ten also
caught the unit table's own column header still unpinned and the hand-edit test tampering only
half the hashed keys; both closed. Round eleven found no defect in a figure, a claim, or a
guard's behaviour: a misattribution in this paragraph, corrected here, and a test that wrote
the committed snapshot as a side effect, redirected to a temp.

**What is still open, and it is the honest residual.** A number spelled in words is invisible
to every rule here, and one shipped on the seventh pass: a count of strata written as "three
of the four" was wrong in three documents. A digit assembled at runtime, `ord("~")` or
`0.5 / 2`, evaluates to a figure with no literal to catch. A figure bound to the wrong field
in a sentence the recomputation does not cover would pass, and the covered set is the tables
and a named list of sentences, not every sentence. And the recomputation is a second
implementation, so a shared misunderstanding of what a field means is invisible to both, which
is the hole the "by construction" retraction went through. `research/sponsor_profile.py` is a
product module scanned only in its module docstring, so a cohort figure in a comment or a
function docstring there would not be caught; it carries no figure today. And the `N of M`
denylist catches "of the" but not "out of", "of those" or a slash, none of which are live. The
rule this file keeps recording applies to the guard as much as to the product: a check watched
passing only on the case it was written for is not yet evidence.

Also guarded mechanically, because it failed once: a hedge present in four claim documents and
absent from the fifth. One fix pass deleted the only qualifier in `docs/SUBMISSION.md`, the
most externally facing of the five, while the other four kept theirs.

## The regulation reaches some strata and not others

**Found 2026-07-22 by an adversarial reviewer checking what the lead-sponsor classes are.**

The write-up used the 42 CFR 11.64(a)(1)(ii) thirty-day window as a reference line against all
four strata. It should not have. Part 11 is U.S. law and binds applicable clinical trials,
broadly those with a U.S. site or a U.S.-regulated product. Industry and NIH are where the duty
plausibly applies.

`OTHER_GOV` in this draw is not U.S. federal agencies. The drawn lead sponsors are non-U.S.
public bodies, a Turkish institute, a Thai ministry, a Mexican social-security system, a
Mozambican health institute. A trial one of them runs with no U.S. arm is generally not an
applicable clinical trial the U.S. rule reaches at all. So the reference line is now drawn
against industry and NIH and explicitly not extended to OTHER_GOV or OTHER; for those strata
the registry facts stand without any regulatory claim.

The registry has a separate lead-sponsor class, `FED`, for U.S. federal agencies other than
NIH, the VA, DoD and CDC among them. That is the stratum where the duty applies most directly,
and this study never drew it. It is recorded in `docs/PARKING.md` as the follow-up. What
survives is a registry fact and not a compliance one: where the U.S. duty plainly applies,
industry still carries an expired estimate at the rate the mechanism table reports; the strata
where no such duty exists carry expired dates more often, not less. That the two facts sit
either side of a jurisdictional line is not evidence the line explains them, and it is not
offered as such, because filing frequency confounds the comparison and this study cannot
separate the two. The write-up states it the same way.

## A month-only date has two readings, and the figures it touches are bounds

**The scope of an earlier disclosure was too narrow, found 2026-07-22.** A registry date given
to the month, `2022-06`, names no day. The engine resolves it to the first of the month, which
is one reading; the last of the month is the other, and the two bound every figure the date
touches. An earlier note disclosed this as affecting days-since-expiry figures only. It affects
more: the same resolved date sets the sign of every after-a-lapse revision, so switching the
reading moves a number of the dated revisions across the prospective boundary and moves the
industry estimate-to-estimate headline down by several points, from its first-of-month reading
to its end-of-month one, both of which the write-up quotes in full. It also shortens each carry
and can drop a stretch that ceases to be a lapse under the later reading.

**The conservative direction is not the same for every figure, and an earlier draft of this
section said it was.** Resolving to the last of the month makes a single carry and the
after-a-lapse rate smaller, so end-of-month is the weaker reading of those and the write-up
quotes it with "at least": the anchor case is "at least" its shorter reading. But it makes the
closed-spell duration medians LARGER, because the shortest carries stop being lapses and drop
out of the set, lifting the median of what remains; there the first-of-month reading is the
smaller one and is what the duration tables print. In both places the figure shown is the
weaker of the two, but they sit at opposite ends of the convention. Both readings are snapshot
fields (`month_convention`), computed from the cache at freeze time the way `anchor_case` is,
and an independent recomputation in the test validates the end-of-month figures rather than
comparing the snapshot to a re-run of the function that produced it.

Direction, stated plainly: every headline survives at its conservative reading. The anchor's
shorter reading is still about twenty-one times the thirty-day window; the industry rate's
lower reading is still better than a fifth of its revisions. The finding never rested on the
optimistic resolution.

## The "filed nothing since it passed" claim was false, and was made stronger under review

**Found 2026-07-22, and it is the instructive one.** A draft said no silent carrier had filed
anything since its date passed, "by construction". The construction does not hold.
`carried_until_corrected` pairs consecutive versions, so it emits no stretch for a trial's
first filing, and nearly half the silent carriers have a single version and so no pair (the
write-up gives the count). For those the zero stretch count is an empty loop, not a clean
record. One of them, `NCT03613558`, registered its single filing years after the date it
recorded had already passed.

The claim is now split by the write-up: the multi-version carriers, none of which filed after a
lapse, and the single-version ones, which filed once at a time relative to expiry that runs
both ways. What makes
this worth its own section is the direction of the error. The prior text said only that the
store failed to support an anecdote, which was true. The version under review upgraded it to
refutation, on a mechanism that does not deliver refutation. A fix written under review pressure
made a true-but-weak claim false, and the recomputation could not catch it because the
recomputation reads `dead_date_stretches` too and shares the misunderstanding.

## The clustering test had no control, and its conclusion is withdrawn

**Found 2026-07-22 by giving an existing test a control rather than by reading its output.**

The batching check counts intervals between consecutive date-changing filings that fall within
a fixed window of a one, two or three year multiple, against a null equal to the share of the
observed interval range those windows cover. Industry came in below that null and the other
three strata above it, and the write-up concluded that annual batching was excluded for
industry and stood as an explanation for OTHER and OTHER_GOV.

Running the identical test on control windows half a year off each anniversary and the same
width scores at least as high in three of the four strata and lower by a single interval in
the fourth. The ratios are rendered per stratum in `docs/WRITEUP.md`.

So the ratio is measuring the shape of the interval distribution, which is concentrated at
short lags, against a null that assumes an even spread and is therefore the wrong null. It is
not measuring anniversaries. Nothing about the arithmetic was wrong. The test had no control,
and a comparison with no control is not evidence.

Both conclusions drawn from it are withdrawn, in the document and here. The innocence check now
ends with one resolved leg, the currently-carrying population excluded on duration alone, and
two **unresolved**: industry's filing timing, which was published as resolved off the retired
null, and the closed-spell durations for OTHER and OTHER_GOV. The table is kept with the control columns beside the anniversary ones, because
a test that cannot separate its signal from a control is worth publishing as exactly that.

## The reconciliation split conditions on a revision existing

**Found 2026-07-22 by the second council round, confirmed, and disclosed rather than fixed.**

The `held_days` split counts revisions, so a trial that lets a date lapse and never files
again contributes to neither the numerator nor the denominator. The measure of
non-reconciliation is therefore computed only over sponsors that reconciled at some point,
which is Correction 6's defect one level up.

It is not small: in the government stratum more than half the trials never revised a date at
all, and the per-stratum counts are rendered in `docs/WRITEUP.md`. The worst-reconciled trials in the
frame are structurally excluded from the reconciliation statistic, which is why point
prevalence is reported beside it and why the two must be read together.

## A revision filed after a lapse is not automatically a failure to reconcile

**Found 2026-07-22 by the second council round. It halved a published headline.**

An earlier draft reported the share of industry date revisions filed after the date had
already passed, and presented that as non-reconciliation. Half of those revisions set the date
to ACTUAL: the sponsor recording when the trial finished. For a trial that ran
late that filing necessarily lands after the earlier estimate expired, and it is the update
42 CFR 11.64(a)(1)(ii) requires within 30 days of actual completion.

So the draft quoted a regulation to argue the behaviour was unlicensed while that regulation
licenses half the observations, and it called the same filing "the system working" in one
section and a failure in another, a hundred lines apart. The arithmetic was correct
throughout; the sentence it supported was not, and no numeric check could have caught it.

The surviving claim is the estimate-to-estimate subset, rendered with its counts in
`docs/WRITEUP.md`. Both are snapshot fields now
(`revisions_after_lapse_to_estimate`, `trials_with_lapse_to_estimate`) rather than derived in
prose, because a figure that is not a snapshot field is a figure no test can check.

## No pooled all-strata rate, and the report used to print one

NIH sponsors carry a dead date about as often as industry ones and substantially longer, so
the strata are not poolable and every published rate is labelled by
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
content-addressed id, hashed
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
  string and a hand-written URL could forge every field. It is now built at render time
  from the ledger's last entry **for the card the page is about**, selected by `card_id`
  rather than by whichever entry happens to be last: record a belief through
  `/belief/new` after an approval and the plain last entry is that belief, so the receipt
  showed one card's hashes under another card's summary. A test requests the page carrying
  forged values and asserts the real ones render, and a second pins the selection.
- Whether a rebuild is reproducible. Nothing asserts that building twice from the same
  inputs produces the same bytes, so a hand-edited snapshot would not be detected.
- ~~Concurrency on the ledger head.~~ Closed for the single-host case. The read and the
  append are one critical section under an exclusive `fcntl.flock`, and a writer whose
  precondition no longer holds raises `Conflict` and appends nothing, so two analysts
  confirming at the same moment no longer produce two entries claiming the same
  predecessor. The section below states what the lock does not cover: it is POSIX only, it
  is advisory rather than mandatory, and over NFS the guarantee is the mount's. Concurrency
  elsewhere in the console is still untested.
- Whether a belief written through the form is ever monitored. It is not. **A newly
  entered belief is recorded, not reconciled.** `POST /belief/new` appends a real CREATE
  entry to the real chain, and the redline loop still runs off the committed snapshot
  rather than off the ledger's live cards, so nothing re-reads that card against fresh
  evidence on the next rebuild or at any other time. Say "records a belief", never "starts
  monitoring it", which is what the button used to imply.
  `tests/test_capability_language.py` enforces the wording on every surface and pins the
  structural fact underneath it, so wiring the rebuild to read the ledger fails that file
  rather than silently making these sentences true.

## The ledger accused itself of tampering, and the lock has a boundary

`BeliefLedger._append` read the chain tail, computed the next `seq` and
`prev_hash`, and only then appended, with nothing holding the file in between.
Two writers released at the same moment read the same tail and wrote two entries
claiming the same predecessor. `verify()` then returned False and
`anchor.check()` returned `tampered`, on a file nobody had edited. Reproduced
five times out of five with four threads on a barrier.

That is the worst false positive this product can produce. Tamper evidence is
the thing the decision record is for, and a guard that fires on two analysts
accepting at the same moment teaches the reader to ignore it.

The read and the write are now one critical section under an exclusive
`fcntl.flock`, and the three writers state their precondition as a function of
the state read inside that lock, so a create that loses a race raises `Conflict`
and appends nothing rather than writing a second entry. The event schema is
unchanged and every public method keeps its signature. `Conflict` subclasses
`ValueError`, which is what the console already caught for a duplicate belief.

What this does not cover, stated rather than implied:

- **`fcntl` is POSIX.** The lock is real on macOS and Linux. On Windows this
  import fails outright, so the console does not run there rather than running
  unlocked, which is the safer of the two failures but is not portability.
- **Network filesystems.** `flock` over NFS depends on the mount and the server,
  and on some configurations it is advisory only or silently a no-op. The ledger
  is one file on one host by design; put it on a share and the guarantee is the
  share's, not this code's.
- **Advisory, not mandatory.** A process that writes to `decisions.jsonl`
  without taking the lock is unaffected by it. Every writer in this repo goes
  through `_append`; anything editing the file directly is tampering, which is
  what the anchor is for.
- **The anchor is still recorded after the append, not inside the lock.** Two
  writers can therefore interleave append and record, leaving the anchor briefly
  behind the head. That reads as `truncated` and not as `tampered`, and it
  resolves on the next successful record.

## The registry-reconciliation line is derived, and it is bounded by one trial's stored history

**Found 2026-07-23.** The centre column of `/redline` states that no later registry version
reconciled the lapsed expectation before its date passed. It used to state that on the
authority of `no_amendment_filed: True`, a literal typed into `console/make_snapshot.py` and
serialised into the snapshot. Deleting or flipping the literal changed the sentence while the
version history it claimed to summarise sat unchanged, which is the wrong way round: a
date-integrity claim whose truth value is typed is a caption, not a finding.

It is now computed by `console.review.registry_reconciliation` at render time, from the
committed version history of the trial the redline is anchored to and the snapshot's own
`as_of`. The field is renamed to the narrower fact it proves,
`no_later_registry_version_before_expiry`. What is computed, stated exactly: **among the
registry versions stored for that one trial, the version that last set the lapsed expectation
had no later stored version, submitted before that expectation's date, that moved it.** The
engine already carries the shape this rests on. A version that replaced a date after it had
already passed is `carried_expired`, so the negation of `carried_expired` on the version after
the setter is a reconciliation inside the window, and the predicate reuses that field rather
than recomputing it.

What it does not establish, and cannot:

- **Nothing about external disclosures.** An amendment can be filed with a regulator, a press
  wire, or an investor deck without any registry version moving. This reads the registry
  version history and only that. It does not show that no press release, 8-K, 10-K/Q, or
  correspondence existed, and it says nothing about whether anyone acted or what a sponsor
  knew or believed. The rendered wording names the registry-history bound for that reason, and
  `orchestrator/lexicon.py`'s silence rules hold the surrounding prose to the same line.
- **Only as far as `as_of`.** When no later version is stored, absence of one has two causes
  that a frozen artifact cannot separate: none was filed, or the snapshot was taken before one
  appeared. So the claim is bounded at the day the artifact froze. If the expectation had not
  yet passed at `as_of`, the window this claim describes has not closed and the state is
  `unknown`, never the claim.
- **Only when the history is complete.** The derivation refuses to answer unless the trial's
  stored revisions account for every registry version the fetch reported
  (`n_versions == len(revisions)`). A version this snapshot never kept cannot be shown not to
  have moved the date, so an incomplete or absent history yields `unknown`. Here the anchored
  trial's `n_versions` equals its four stored revisions, so the history is complete and the
  state is the claim; the incomplete case is handled rather than assumed away.

The three states are `no_later_registry_version_before_expiry`, `reconciled_before_expiry`, and
`unknown`, and the template renders a sentence for each, including `unknown`. A screen that
goes quiet when its evidence runs out reads exactly like one whose evidence held, which is the
failure the whole desk exists to catch, so the refusal is shown rather than hidden. The frozen
snapshot still carries the retired `no_amendment_filed` key; it is byte-identical evidence and
was not rewritten, and nothing reads it. `tests/test_console.py` derives the state against
mutated copies of the snapshot: deleting or flipping the literal changes nothing, a later
reconciliation added to the history withdraws the claim, and an incomplete, absent, or
not-yet-lapsed history produces `unknown`.

## The accessibility tier covers the Phase 2 spine and nothing else

The scan is keyed on the app's own `url_map`, so no route can go unclassified, but the set it
actually drives is seven rules and nine pages: `/inbox`, `/activity`, `/redline`,
`/redline/confirm`, `/receipts/<entry_id>`, the decision review in both of the shapes it
renders, and the evidence explorer for the contract with the longest chain and for the one
whose funding gap is withheld. Everything else is named in `A11Y_NOT_SCANNED` with a reason.
For the Phase 1 screens that reason is that they are outside this tier, and that is a gap in
coverage, not a finding that they pass.

Measured on 2026-07-24 with the same tags the tier uses, and recorded here because leaving it
out would let the tier's green summary read as more than it is: `/contracts` and `/queue`
reported no violations, while `/contract/<ticker>`, `/workspace` and `/belief/new` each
reported at least one, including a `select` with no accessible name on the belief form. None
of those five is scanned, so those readings are a snapshot from one run rather than a
guarantee in either direction.

Every scanned page reports zero violations, and there is no declared-exception map
left. `/redline/confirm` carried three colour-contrast failures when the inventory first
reached it: the record-integrity badge and the hash-verified chip at `#10b981` on `#1a4731`,
`4.16:1` against a `4.5:1` floor, and the prev hash in the receipt table at `#6b7280` on
`#161b22`, `3.57:1`. They were the same two pairings repaired on `/redline` one commit
earlier, and they survived exactly because `/redline` was scanned and `/redline/confirm` was
not. They are repaired with the same two substitutions: the green sits on the darker success
tint `base.html` already declares, `6.44:1`, and the dim grey becomes the page's own secondary
text colour, `5.62:1`. `KNOWN_VIOLATIONS` is deleted rather than emptied, because an empty map
with an assertion that it is empty is one line away from being a licence again, while
re-introducing an exception now means re-introducing the subtraction the scan no longer does.

The repair had one obvious wrong shape, which is to clear a contrast failure by moving every
state onto whichever token passes. Green would have won, and intact, tampered and truncated
would have become one colour with three words. So the colour language is asserted separately
from the contrast, off the template rather than off a render, so it holds in the base tier
where no browser exists: each of the three states keeps its own foreground, both the badge and
the hash-chain chip of a state agree, and every pair clears the floor by computed ratio.

What the tier does not establish, at the strength it holds: axe is a mechanical check at one
viewport in one browser. It does not read a screen, and a page can clear every rule in it and
still be unusable.

## The suite no longer writes the repo's live console state, and what that rests on

`data/decisions.jsonl`, `data/review_log.jsonl` and `data/ledger.anchor` are live demo state.
Eight test modules redirected them into `tmp_path` by hand and one path was missed:
`test_badge_flips_on_tampered_ledger` redirected the ledger and the review log but not the
anchor, so `POST /redline/decide` reached `anchor_record` on the real path and `pytest tests/`
on a clean tree created `data/ledger.anchor`. Per-test patching is fail-open by shape. It
holds for the tests that remembered, and the correction is always written after the leak.

`tests/conftest.py` redirects all three for every test, autouse, so a test written from here
on is isolated without doing anything and a test that patches them itself still wins. It also
redirects `orchestrator.anchor.ANCHOR_PATH`, whose default was bound into the signature at
import and so could not be redirected at all; the functions now resolve it per call, same path
for every caller that passes nothing.

What that does not prove: it redirects two named modules, so a test that opens `data/` by a
literal path of its own is not prevented. The second fixture is why that is still caught. It
hashes the three real files before the session and after it and fails the run on a byte of
difference or on a file that appeared, from any writer, including one this file does not know
about. Prevention is scoped to the seam; detection is not scoped at all.

## Every receipt ever rendered stamped local wall time and called it UTC

Found while extracting one timestamp renderer for the activity screen, fixed in the same
pass, recorded here because it was live on a shipped page rather than caught in review.
`console/app.py::_receipt` built its timestamp with `datetime.fromtimestamp(ts)` and no
timezone, and labelled the result `UTC`. `fromtimestamp` with no `tz` argument reads the
host clock, so the field said UTC and showed whatever wall time the machine rendering it
happened to be on. On the machine this repo is developed on that is seven or eight hours
off, depending on the season, and the season is part of the defect: the error is not a
constant, so two receipts for the same entry rendered either side of a DST boundary
disagree with each other as well as with the label.

Nothing downstream consumed the string, and the ledger stores epoch seconds, so no stored
value was ever wrong and no figure elsewhere in the product was derived from it. That is
why this is a defect note and not a numbered research correction: the affected surface is
the timestamp on the Decision Integrity Receipt, and its magnitude is a fixed offset from
the value that was always correct in the file.

The conversion is now explicit, in `review.ts_display`, which both screens compose through.
`tests/test_activity.py::test_the_utc_conversion_does_not_move_with_the_host_timezone` sets
`TZ` to three zones, one west, one east of the date line's return and one on a half-hour
offset, and asserts the rendered label does not move. What that does not prove: it pins the
formatter, not every future caller, and a page that formats a timestamp of its own is caught
only by the source check beside it.

## The seeded ledger entry has no timestamp, and now says so

`console/app.py` seeds the original belief card with `ts=0.0` so the approve path has an
entry to bump. That zero is a sentinel written into a field that is not optional, and both
screens rendered it as `1970-01-01 00:00:00 UTC`, which on a decision history and a receipt
reads as a corrupted record.

The stored entry is not touched. `review.ts_display` returns a `TimestampDisplay` carrying a
label, a note and an `is_sentinel` flag, so the zero is interpreted once, in the projection,
and both screens agree by construction rather than by two templates being written the same
way. `tests/test_activity.py` asserts the ledger bytes are identical after a render and that
the entry still carries its zero, because the other way to clear a 1970 date is to write a
better timestamp into the record, and a record edited to make its own screen read well is
the failure this console exists to make visible.

What that does not establish: when the seeded card was actually created. Nothing recorded
it, the page says nothing recorded it, and the row keeps its position at the head of the
list because that is where the hash chain puts it, not because a time was inferred.

## Where these came from

The first four sections were produced by a three-model adversarial review (Claude, Cursor,
Codex) asked specifically which existing checks were hollow, and then every claim it made
was run against the code before being written down here. Two of its predictions were
right, verified above. The transcript is in `runtime/council/` in the vault repo.
