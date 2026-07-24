# Catalyst Integrity Desk

An auditable monitor for when a biotech investment thesis no longer matches its approved
evidence contract.

**The boundary, stated before anything else.** The system does not determine whether a
thesis is true. It identifies when the public evidence no longer matches the assumptions
recorded in the evidence contract and routes that change to a human. A belief written
through the console is recorded and hash-chained; nothing re-reads it on its own.

<!-- generated: anchor -->
In April 2024, Rocket Pharmaceuticals filed a protocol revision for trial `NCT04248439`
carrying a primary completion date of June 2022. That date names a month, not a day, so read
at its latest it **had already been expired for at least 648 days** when the revision was
filed, and at its earliest 677 days. Either way it stood in public, on a federal registry,
machine readable the entire time.
<!-- /generated -->

Nobody was watching, because nobody's job is to watch.

**And Rocket is not unusual. The actual finding is about the registry, not the sponsor.**

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

That inverts the measure this project started with. Counting lapses that a later filing
corrected, government sponsors look like the *best* reconcilers, because a lapse only becomes
visible when the sponsor files again. A measure that needs its subject to keep talking cannot
see the subject that stops.

<!-- generated: mechanism -->
The supporting mechanism, among sponsors still filing: **at least 22.2% of industry
completion-date revisions replace an estimate that had already expired**, a bound because a
month-only date has two readings and this is the smaller; the first-of-month reading is
26.2% (33 of 126). 24 of 52 (46.2%) industry trials that revised a date at all did it at
least once. That is narrower than running late, which is well documented, and narrower than
the raw after-lapse count, because a revision recording an *actual* completion is the update
the regulation requires rather than a failure to file it.

Industry point prevalence is 8.3% of all trials, and 33.3% of those whose commitment is
still open. The anchor case stood expired for at least 648 days; under the first-of-month
convention, the 677-day reading sits at the **85th percentile** of 188 such stretches. The
rank is quoted with the reading it was computed from, because a percentile and the duration
it ranks have to come off the same convention, and an earlier draft of this block paired the
end-of-month duration with a first-of-month rank. Long, and inside the distribution rather
than outside it.
<!-- /generated -->

`docs/WRITEUP.md` is the standalone write-up and `docs/COHORT.md` the
working record.

<!-- generated: provenance -->
Every cohort figure in the claim documents is emitted from a field of snapshot
`cohort-5b03269658b8` by `research/render_writeup.py`: 240 trials, 60 in each of four
sponsor strata, all measured, point prevalence as of 2026-07-22. The prose around them
contains no numerals and a test regenerates every generated block and fails on a one-byte
difference.
<!-- /generated -->

## The claim, in one sentence

> **This system measures whether public, dated, self-authored commitments were kept,
> revised, superseded, or allowed to expire without reconciliation. It does not measure
> whether the underlying claim was ever true.**

The second sentence is half the product. Diligence really wants a verdict on the
underlying science, and on whether the stated dates will hold. No system reading public
records can deliver one, and a model that pretends to is an opinion dressed as evidence.
What is answerable, and already public: whether the promises survived contact with their
own prior versions.

Theranos is the useful example because of what the tell was **not**. In real time nobody
was going to catch it by evaluating the microfluidics. What was visible continuously was a
decade of claims that did not reconcile against their own earlier versions. That pattern
is measurable. Feasibility is not. `docs/PRINCIPLE.md` states the rule and the claims this
system is therefore forbidden from making, and `orchestrator/lexicon.py` enforces them on
the model, the pages and the docs.

## The problem

Every clinical-stage biotech thesis rests on a date. The company has cash into month X,
the trial completes before month X, therefore it is funded to its catalyst and does not
need to raise.

The left side of that sentence comes from SEC filings. The right side comes from
ClinicalTrials.gov, where **the sponsor sets the date, can revise it whenever it likes,
and nothing reconciles that revision against the thesis that depended on the old date.**

Every revision is public, timestamped, and undiffed. The analyst who wrote the thesis in
January is not re-reading the registry in April.

A registry entry is not an observation. It is a claim, made by an interested party, that
can be revised at any time, where every revision is public and timestamped and nobody
diffs it. ClinicalTrials.gov is one instance of that shape.

This project treats the thesis as a contract and audits both sides of it.

```
funding gap = runway exhaustion date - registered primary completion date
```

## Two modes, one computation path

```
DEMO                                  WORKSPACE

data/evidence/*.json                  ticker
committed, no network                     |
        |                                 v
        |                           live SEC + ClinicalTrials.gov
        |                                 |
        +---------> EvidenceSnapshot <----+
                          |
       normalise -> promise identity -> metrics -> guarded prose -> ledger
```

`evidence/` is the seam and the only layer that knows where bytes came from.
`tests/test_layering.py` walks the AST and fails if `engine/` or `orchestrator/` imports
it, so no module that computes a displayed number can ask whether it is running live and
answer differently. That is what makes the frozen demo evidence about the product rather
than a mock of it.

`/workspace` runs the real flow with no credentials, because the committed bundles and a
live fetch are the same schema.

## Quickstart

No credentials, no API keys, no network. The demo runs from a committed snapshot.

```bash
git clone https://github.com/kristenharim/catalyst-integrity-desk.git
cd catalyst-integrity-desk
pip install -r requirements.txt
python3 -m console.app            # http://localhost:8050
python3 -m pytest tests/ -q       # 340 passed, 17 skipped
```

Run it as a module, from the repo root. Set `PORT` to move it off 8050.

**The guarantee:** the console makes no network call and reads no credential. Everything
it renders comes from `data/snapshot.json`, which is committed. Clone, install Flask, run.
Nothing else.

**Three tiers, because the result depends on what your machine carries.** A clone gets
tracked files only and installs `requirements.txt` alone, so three groups skip: fifteen that
replay registry version history out of the gitignored `data/cache/`, one live Granite check
that needs watsonx credentials, and one browser-geometry check that needs Playwright. That
is **340 passed, 17 skipped**, the number above, and the one a judge sees. Install Playwright
alone and the browser-geometry check runs too: **341 passed, 16 skipped**. Add the cache and
Playwright locally and sixteen of those run instead, giving **356 passed, 1 skipped**. The
last skip is the credentialed Granite test; that configuration has not been re-measured for
this commit, so no count is quoted for it. That test is verified not to pass on the stub:
pointed at an invalid endpoint it fails on `source == "granite"`.

The fifteen cache-dependent tests verify the cohort research rather than the console, and
the browser check verifies the demo's opening frame is where the script says it is. Nothing
on the demo path depends on either, which is why a clone can run the whole product with
seventeen tests skipped and still be running the real thing. For the geometry check:

```bash
pip install playwright && python3 -m playwright install chromium
```

**The 90 second tour:**

| | |
|---|---|
| `/` | redirects to the Rocket detail, on purpose. The 677-day row is the point. |
| the red node | a revision filed in April 2024 carrying a completion date from June 2022 |
| the table below it | every input with the XBRL tag it resolved through |
| `/contracts` | the ranked list, unreliable rows shown below it and never ranked, and below those any ticker that produced no contract at all, with the reason |
| `/redline` | the thesis breaking: approved against a date that then lapsed, and Granite's memo about it |
| `/workspace` | ticker in, recorded contract out. Identity and the empty queries are shown before any candidate; a lapsed date is listed and cannot be chosen |
| `/belief/new` | where a belief comes from. The analyst writes the thesis, the trial, and the gap below which they would stop believing it |
| Accept | writes a hash-chained ledger entry, then the badge reads the ledger back |

**The tamper demo:** accept the redline, edit any byte inside the `card` object in
`data/decisions.jsonl`, reload the confirm page. The badge goes from `✓ intact` to
`✗ tampered`, because it calls `verify()` at render time rather than trusting what the
redirect told it.

**Reset between runs:**

```bash
rm -f data/decisions.jsonl data/review_log.jsonl data/ledger.anchor
```

Both are gitignored live state, written during a demo and safe to delete. The snapshot is
not: `data/snapshot.json` is the frozen evidence and is committed deliberately.

**Where the frozen evidence comes from.** The snapshot was built against live SEC XBRL
company facts, live ClinicalTrials.gov version history, and a live IBM Granite call whose
classification is recorded in the file with `source: "granite"`. Rebuilding it requires
credentials and is never done during a demo. The `docs/bob-sessions/` transcripts show it
being built.

## The theme: intelligent systems for the future of work

The work being automated here is not analysis. It is **noticing**.

An analyst can compute a funding gap in ten minutes. What no analyst does, across forty
positions, is re-read a registry every week to catch the one sponsor that moved a date by
fourteen months, then check whether that breaks something they wrote down in January. The
failure is not a hard problem solved badly. It is an easy problem nobody is assigned to.

So the system records a written belief against a frozen evidence contract, detects when a
rebuild contradicts a belief it already carries, drafts the challenge in the analyst's own
vocabulary, and stops. A human accepts or rejects, and the
decision hash-chains into a tamper-evident ledger. The judgement stays human. The
vigilance is what gets automated.

## The AI approach

**Python computes. Granite judges prose. Humans decide.**

IBM Granite on watsonx never produces a number. It reads the analyst's written rationale
alongside the recomputed contract and reports which stated assumption a change breaks, and
how badly. Every figure on screen comes from Python arithmetic over filed data.

That rule is enforced rather than asserted. `_quantitative()` scans model output for any
quantitative expression at all and falls back to a deterministic stub if it finds one. The
guard bans quantities outright rather than only unsourced ones: digit forms, number words,
percentages, ratios, signs, durations, and the dates a month and an ordinal compose without
using a digit. A response carrying one is discarded whole, never edited, because a sentence
with its number deleted is a sentence whose meaning nobody has checked.

The earlier rule was "a number absent from the input", on the reasoning that quoting a
figure from the belief's own claim is quotation rather than invention. An audit retired it.
It carried no *field*, so any bare digit anywhere in the analyst's own prose authorised that
magnitude in the metric's own unit: a thesis reading "Phase 3 readiness across 12 sites"
licensed both "3 months" and "12 months". `docs/LIMITS.md` carries the full reasoning and
the exact residual.

**Two structural guards, not one.** `_quantitative()` stops the model measuring anything.
`orchestrator/lexicon.py` stops it making a claim the evidence does not support: a
feasibility verdict, an accusation of intent, a causal explanation for why a date moved, or
silence asserted as fact. A rationale that trips either guard is discarded and the
deterministic stub answers. The same lexicon scans every rendered page and every
claim-bearing document, so the rule cannot hold in the code and drift in the pitch. It
caught three violations already shipped in this repo when it was first run.

**Slip is only slip when the promise held its shape.** `engine/promise.py` classifies every
registry revision as unchanged, date-only, a scope revision, a supersession, or uncertain,
and only the first two may produce a number. A revision that also changed the primary
endpoint describes a different commitment, and subtracting its dates is not a delay. The
audited trials include established, contingent, and refused movements. A net-slip total is
not usable unless promise identity holds across the revisions being compared. The first
version of this audit reported a single count of unsupported trials; the three-state audit
retracted it, and `docs/LIMITS.md` carries both the count and why it was withdrawn.

Two supporting rules do the rest of the work.

**Every displayed number names its source.** `Runway.provenance` records which XBRL tag
each component resolved through, because tags are not uniform across filers and a
numerator you cannot identify is not auditable. The console prints the tag beside the
figure.

**A lapsed completion date is never a catalyst.** You cannot run out of money before an
event that already happened. Lapsed dates are retained and surfaced as date-integrity
signals, which is the entire point of the project, rather than discarded or treated as a
funding target.

## How IBM Bob was used

Bob was the primary development tool. The split below comes from `docs/BOB_LOG.md`, which
was written as the work happened. Every Bob row there is backed by a full task export in
`docs/bob-sessions/`: nine transcripts covering twelve rows, because three Bob sessions
each produced two logged rows.

**Built with Bob:**

- **The governance port.** Ledger, challenge, classifier and Granite modules brought over
  from a prior project, with the prompt strings rewritten for catalyst vocabulary and
  `_fabricated()` kept byte for byte. Plus `engine/contract.py`, the flattener from a
  contract to the packet the breach scanner reads.
- **The redline loop.** `as_directions()` translates before and after metric packets into
  word-only direction labels, so the model never sees a number it could echo back as its
  own. `run_redline()` detects a breach and calls the challenge builder.
- **The console.** All three views, the snapshot generator, the SVG revision timeline, and
  the test suite.
- **The integrity badge repair**, test first.

**Preceded Bob and is not its work:** the three modules in `engine/`, verified against
live SEC and ClinicalTrials.gov data before the build started, and the specs, findings,
demo script and prompt pack in `docs/`.

Bob was constrained rather than trusted. `.bob/custom_modes.yaml` puts a `fileRegex` on
edit permission so the three verified engine modules cannot be rewritten, and defines a
reviewer mode with no edit permission at all, so a review cannot quietly fix what it is
judging. Those boundaries held.

Other AI tools were used for review, which the challenge permits, and `docs/BOB_LOG.md`
records those passes separately from the build.

Work after Bob's build was completed by hand with Claude Code, not by Bob, and every line
of it is logged in `docs/BOB_LOG.md` at the same detail as the Bob rows. That is: the
unresolved-ticker row on `/contracts`, the thesis-break timeline, the derivation table, the
analyst belief form, the monitoring queue, then the larger pass that added the evidence
seam, promise identity, the enforced claims lexicon and workspace mode, then the random
cohort study: its store, the snapshot the published rates cite, the first amendment to a
protected engine module, and the absorption rules in the lexicon. Most recently, the
three-axis decision state model in `console/states.py` and `console/review.py`, which
separates what the evidence says from what a human is doing and from whether the decision
record is still intact, and then the non-quantitative Granite policy in
`orchestrator/granite.py`: the rule that replaced "a number absent from the input" after an
audit broke it, and the pass that closed the word-form dates the replacement still let
through, aligned both prompts with the rule the runtime actually enforces, and corrected the
test counts three earlier rows had published from memory rather than from a run. Then the
submission reconciliation: the classification's confidence stopped being rendered, the
lexicon's silence rules stopped being keyed on three exact phrasings, and the claims this
file makes about its own percentile, its own retracted audit, and its own Bob counts were
put under `tests/test_claim_integrity.py` rather than left to review. Most recently, the
registry-reconciliation line on `/redline` stopped resting on a typed Boolean: whether a
later registry version ever reconciled the lapsed expectation is now derived in
`console/review.py` from the anchored trial's committed version history and the snapshot's
own `as_of`, renamed to the narrower fact it proves, and rendered as one of three sentences
including an explicit unavailable when the stored history cannot answer.

**IBM Bob built the original governance, redline, console, receipt and research-panel
foundations. Later extensions and adversarial corrections were implemented separately with
Claude Code and are recorded in the project log.** Everything in the original console --
all three views, the snapshot generator, the redline loop, the governance port and the
first test suite -- is Bob's, and `.bob/custom_modes.yaml` shows the constraints it was
built under. What came after is not only review: the evidence seam, promise identity, the
claims lexicon, workspace mode, the cohort study, the decision state model, the
non-quantitative Granite policy and the locked ledger append are all product code written
by hand. Describing that split inaccurately would be a worse failure than admitting a
second tool touched the repo.

## How it was verified

Every real defect found in this project had the same shape: **everything stayed green.** A
test narrowed around a bug the author had already noticed. A live-model test that passed
without ever reaching the model, because the stub fallback answered and stubs do not
fabricate. A function imported into its own test and never called. A demo centrepiece
missing from the snapshot because `dataclasses.asdict` serialises fields and not
properties.

None of them announced themselves. So a check here is not trusted until it has been seen
failing.

- The fabrication guard is tested against live Granite, not a mock. That test is
  itself checked by pointing it at an invalid endpoint: it then fails on the
  `source == "granite"` assertion rather than passing on the stub, which is the
  precise way an earlier version of it gave a false pass. Without credentials that one
  test skips; with them it runs. No count is quoted for the credentialed configuration,
  because none has been measured for this commit.
- The number-provenance test asserts that every figure in the rendered HTML appears
  verbatim in the snapshot. It was confirmed by planting a `9999` in a template and
  watching the test name that token.
- The ledger badge test was written before its fix, and watched to fail.
- Each console check was re-broken afterwards: the marker class renamed, `stub` forced
  into the memo, `days_expired` changed from 677 to 123. All four failed as they should.

`docs/LIMITS.md` states what every guard in this system does and does not prove, at the
strength the evidence supports. It is worth reading before the code, because the honest
version of each claim is narrower than the obvious one, and each limit there was found by
breaking the thing rather than by reasoning about it.

Stated precisely, because it is easy to oversell: the provenance check **detects
unintended displayed literals**. It does not prove every rendered value is correctly
formatted. It matches by substring, so a format that truncates a full-precision value
passes for free, and it walks text nodes only, so attribute values such as SVG
coordinates and stroke widths are never examined. Within those limits it does the job it
exists for, which is catching a number that entered the page from somewhere other than
the snapshot.

## What it found

**Rocket Pharmaceuticals.** A completion date revised in April 2024 that had already been
expired for 677 days, on `NCT04248439`. That date has since passed too, so the binding
catalyst is now `NCT06092034` at 2028-04, against which the same runway gives **-14.5
months, financing required**. Anchored to the old date the thesis read +8.4 months, funded.
No later registry version reconciled the registered expectation. The date simply arrived,
and passed.

**And a correction this project found in its own numbers, then corrected again.** Earlier
versions of this section reported "1,008 days of net slip" on that trial and "a 943 day
move" on its successor, summing every date movement without checking the dates described
the same commitment. `engine/promise.py` now checks, and reports three totals rather than
one:

- **`NCT06092034`: 943 reported, 0 established.** Its revision changed the enrolment from
  12 to 14. A count, not a wording, so no reading rescues it.
- **`NCT04248439`: 1,008 reported, -422 established, +1,430 contingent, upper bound
  1,008.** Its endpoint was reworded from phenotypic correction of bone marrow colony
  forming units to Mitomycin-C resistance of bone marrow colony-forming cells. In Fanconi
  anaemia those may be the same endpoint named more precisely. A reword and a redefinition
  are indistinguishable from the text, so the movement is contingent on a human reading
  both descriptions, and the original figure may have been right.

The second row is the more useful one. A first pass treated the reword as a scope revision
and reported 1,008 as unsupported, which overcorrected. It also meant a sponsor could
delete a delay from the total by rewording an endpoint. A guard the subject can defeat by
editing prose, in the direction that flatters them, is not a guard. `docs/LIMITS.md` has
the full table.

The 677-day result is untouched by this: it is one version carrying an already-passed
date, not a comparison across two commitments. So is the funding gap, which compares the
current registered date to the runway.

Across 12 clinical-stage, pre-revenue companies, all 12 produced rankable runway bands.

Burn is reported as a band, never a point, because one quarter containing a partnership
upfront is unrepresentative. Rows whose burn estimate is unreliable stay visible with the
reason attached and never carry a rank. A screen that silently drops its hard cases is
worse than one that shows them.

## What this is not

Whether cash-constrained sponsors revise their dates differently than solvent ones is an
open question, not a result, and adjacent published work already exists. A commercial
screener and a published revision dataset both exist and are cited in `docs/DEMO.md`.

The claim is the monitor. Not a novel dataset, and not a finding.

The system says **registered primary-completion expectation**, never "readout date". They  [lexicon-exempt]
differ systematically by two to four months, and the gap is always optimistic.

## Layout

```
evidence/                 the seam: EvidenceSnapshot, frozen and live providers
engine/promise.py         promise identity; refuses a slip number it cannot establish
engine/dimensions.py      the endpoint and enrolment per registry version
orchestrator/lexicon.py   the forbidden-claims list, enforced on model and pages
engine/runway.py          cash runway from SEC XBRL company facts, as a band
engine/ctgov_history.py   registry revision history, notice and expiry metrics
engine/gap.py             the catalyst contract join
engine/ledger.py          hash-chained belief ledger
orchestrator/             redline loop, challenge builder, Granite client
console/                  Flask console, four views, snapshot generator
research/                 the monitoring-queue panel, CSV and figure
tests/                    40 tests, no network, no credentials
data/snapshot.json        the frozen demo artifact
docs/PRINCIPLE.md         the one-sentence claim and the forbidden-claims list
docs/WORKSPACE.md         the two-mode design
docs/BOB_LOG.md           what Bob built versus what preceded it
docs/bob-sessions/        full Bob task exports, the evidence behind that log
docs/FINDINGS.md          eight data gotchas, prior art, attack surface
docs/DEMO.md              three minute script
```

Read `docs/FINDINGS.md` before writing extraction code. Each gotcha in it produces a wrong
number rather than an error, and one of them caused a 49x error that looked exactly like a
company about to run out of money.
