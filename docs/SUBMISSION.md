# Submission pack

Everything the challenge asks for, in one place, written to be pasted.

**Platform:** https://aibuilderschallenge-bobhub.bemyapp.com/#/projects
**Track:** Wild Card, Intelligent Systems for the Future of Work
**Deadline:** 11:59pm ET on the last day of the month. July 31 for this cycle, and the
Wild Card runs again in August if you want a second pass.

## Where each requirement stands

| Requirement | State |
|---|---|
| Published Project Page, all sections complete | **not started**. Unblocked now, the repo link exists. Only Kristen can publish it. |
| Working prototype using IBM Bob | done |
| Public GitHub repository with a README | **done 2026-07-22**, https://github.com/kristenharim/catalyst-integrity-desk |
| Public demo video, max 3 minutes | **not started**, script is `docs/DEMO.md` |
| SkillsBuild completion certificate | obtained, **not yet uploaded** |

Order mattered: publish the repo, then create the page, because the page wants the link.
The repo is up, so the page is the next move. The three open items all need a human with
an account: the page, the video, and the certificate upload.

---

## Project name

Catalyst Integrity Desk

## One-line tagline

An auditable monitor for when a biotech investment thesis no longer matches its approved
evidence contract.

## The product boundary

The system does not determine whether a thesis is true. It identifies when the public
evidence no longer matches the assumptions recorded in the evidence contract and routes
that change to a human. A belief written through the console is recorded and hash-chained;
no rebuild re-reads it, so nothing entered there is watched without a human asking again.

## The claim, in one sentence

This system measures whether public, dated, self-authored commitments were kept, revised,
superseded, or allowed to expire without reconciliation. It does not measure whether the
underlying claim was ever true.

The second sentence is half the product. Diligence wants a verdict on the underlying
science and on whether the stated dates will hold; no system reading public records can
give one, and a model that pretends to is an opinion dressed as evidence. What is
answerable, and already public, is whether the promises survived contact with their own
prior versions. `docs/PRINCIPLE.md` states the rule and the claims that follow from it,
and `orchestrator/lexicon.py` enforces them on the model, the pages and the docs.

## Short description

Every clinical-stage biotech thesis rests on a date: the company has cash into month X,
the trial completes before month X, therefore it is funded to its catalyst and does not
need to raise.

The left side of that sentence comes from SEC filings. The right side comes from
ClinicalTrials.gov, where the sponsor sets the date, can revise it whenever it likes, and
nothing reconciles that revision against the thesis that depended on the old date. Every
revision is public, timestamped, and undiffed.

This treats the thesis as a contract and audits both sides. Python computes the funding
gap from named XBRL tags and registry versions. IBM Granite reads the analyst's written
rationale and reports which stated assumption a change breaks, and is structurally
prevented from producing a number. A human accepts or rejects, and the decision
hash-chains into a tamper-evident ledger.

## The problem, in one example

<!-- generated: anchor -->
In April 2024, Rocket Pharmaceuticals filed a protocol revision for trial `NCT04248439`
carrying a primary completion date of June 2022. That date names a month, not a day, so read
at its latest it **had already been expired for at least 648 days** when the revision was
filed, and at its earliest 677 days. Either way it stood in public, on a federal registry,
machine readable the entire time.
<!-- /generated -->

The revision landed in the registry, and nothing in the thesis that depended on that date
moved.

Then that date passed too. A thesis anchored to it read plus 8.4 months, funded to
catalyst. The nearest registered completion still in the future puts the same company at
minus 14.5 months, financing required. No later registry version reconciled the registered
expectation. The date simply arrived, and passed.

**Rocket is ordinary, and the actual finding is about the registry.**

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

Counting only lapses that a later filing corrected inverts that ranking, because a lapse
becomes visible only when the sponsor files again. A measure that needs its subject to keep
talking cannot see the subject that stops.

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

<!-- generated: provenance -->
Every cohort figure in the claim documents is emitted from a field of snapshot
`cohort-5b03269658b8` by `research/render_writeup.py`: 240 trials, 60 in each of four
sponsor strata, all measured, point prevalence as of 2026-07-22. The prose around them
contains no numerals and a test regenerates every generated block and fails on a one-byte
difference.
<!-- /generated -->

`docs/COHORT.md` has the frame and the limits; `docs/WRITEUP.md` is the write-up.

## The architecture that makes the demo mean something

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

`evidence/` is the only layer that knows where bytes came from. `tests/test_layering.py`
walks the AST and fails if `engine/` or `orchestrator/` imports it, so no module that
computes a displayed number can ask whether it is running live and answer differently.
That is what makes a frozen demo evidence about the product instead of a mock of it, and
`/workspace` runs the real ticker-to-contract flow with no credentials because the
committed bundles and a live fetch are the same schema.

## The AI approach

**Python computes. Granite judges prose. Humans decide.**

Granite never produces a number. It is given the direction a metric moved, never the
value, so it has nothing to echo and nothing to do arithmetic on. `_quantitative()` scans
model output for any quantitative expression at all, not merely one absent from its input,
and discards the whole response in favour of a deterministic stub if it finds one. Digit
forms, number words, percentages, ratios, signs, durations and word-form dates are all
refused, and nothing is partially sanitised. That guard is tested against live Granite, and
the test is itself checked by pointing it at an invalid endpoint, where it fails rather than
silently passing on the stub.

Two supporting rules: every displayed number names the XBRL tag or registry version it came
from, and a lapsed completion date is never treated as a catalyst, because you cannot run
out of money before an event that already happened.

## What it found in its own numbers, twice

The most useful result this project produced is a correction to itself, and then a
correction to that correction.

`total_slip_days` subtracts registered dates across registry versions. That is a delay only
if both dates describe the same commitment, and nothing checked. `engine/promise.py` now
does, and reports three totals rather than one: **established** where the commitment
provably held, **contingent** where only free prose changed, **refused** where a count or
enumeration changed.

Two Rocket trials, failing differently:

- `NCT06092034`: reported 943 days, established 0. Its enrolment moved from 12 to 14. A
  count, so no reading of any text rescues it.
- `NCT04248439`: reported 1,008, established -422, contingent +1,430, upper bound **1,008**.
  Its endpoint was reworded from phenotypic correction of bone marrow colony forming units
  to Mitomycin-C resistance of bone marrow colony-forming cells. In Fanconi anaemia those
  may name the same endpoint more precisely, so the movement waits on a human reading both.

A first version of this audit called the second one unsupported and stopped. That
overstated it, and worse, it meant a sponsor could remove a delay from the comparable total
by rewording an endpoint in the same filing. A guard a subject can defeat by editing prose,
in the direction that flatters them, is not a guard.

Unaffected, and stated so neither correction is read as bigger than it is: the 677-day
expired-date result is one version carrying an already-passed date, with no comparison
between commitments. So is the funding gap. `docs/LIMITS.md` has the table.

## Theme fit: intelligent systems for the future of work

The work being automated is not analysis. It is **noticing**.

An analyst can compute a funding gap in ten minutes. What no analyst does, across forty
positions, is re-read a registry every week to catch the one sponsor whose date moved, then
check whether that breaks something they wrote down in January. It is not a hard problem
solved badly, it is an easy problem nobody is assigned to. So the system records a written
belief against a frozen evidence contract, detects when a rebuild contradicts a belief it
already carries, drafts the challenge in the analyst's own vocabulary, and stops. The
judgement stays human; the vigilance is what gets automated.

## How IBM Bob was used

Bob was the primary development tool. Twelve logged tasks, nine full session transcripts
committed at `docs/bob-sessions/`.

IBM Bob built the original governance, redline, console, receipt, and research-panel
foundations: the governance port (ledger, challenge, classifier, Granite client), the
redline loop, the entire original console including all three views and the test suite, the
snapshot generator, the integrity-badge repair, the ledger anchor and the decision receipt.
Later extensions and adversarial corrections were implemented separately with Claude Code
and are recorded in the project log.

What preceded Bob: the three verified engine modules in `engine/`, and the spec, findings,
demo script and prompt pack in `docs/`.

Bob was constrained rather than trusted. `.bob/custom_modes.yaml` puts a `fileRegex` on
edit permission so the three verified engine modules cannot be rewritten, and defines a
reviewer mode with no edit permission at all so a review cannot quietly fix what it is
judging.

Work after Bob's build was done by hand with Claude Code, logged in `docs/BOB_LOG.md` at
the same detail as the Bob rows: the unresolved-ticker row, the thesis-break timeline, the
derivation table, the belief form, the monitoring queue, and the pass that added the
evidence seam, promise identity, the enforced claims lexicon and workspace mode, the random
cohort study, the three-axis decision state model, the non-quantitative Granite policy and
the locked ledger append. That is substantial product code, not a review pass over Bob's,
and it includes the correction to this project's own slip figures. Bob's foundations and
the later work are both on the record, at the same detail, in the same file.

## What makes it checkable

Every real defect in this project had the same shape: everything stayed green. A test
narrowed around a known bug. A live-model test that passed without reaching the model,
because the stub answered and stubs do not fabricate. A demo centrepiece missing from the
snapshot because `dataclasses.asdict` serialises fields and not properties.

So no check here is trusted until it has been watched failing. The provenance test was
confirmed by planting a `9999` in a template. The badge test was written before its fix.
The ledger anchor exists because a three-model adversarial review predicted that a bare
hash chain cannot detect deletion, and the prediction held: deleting an entry, and
replacing the file with a forged chain, both returned "intact" before it.

`docs/LIMITS.md` states what every guard does and does not prove, including where each one
is weaker than it looks. The project records known limits and corrections in place, and its
controls target the classes of overclaim demonstrated during review.

## Tech stack

Python 3, Flask, matplotlib. IBM Granite on watsonx.ai for classification and memo drafting.
SEC XBRL company-facts API and the ClinicalTrials.gov v2 API with full version history. No
build step, no external CSS or JS, no network access at render time.

## How to run it

```bash
pip install -r requirements.txt
python3 -m console.app        # http://localhost:8050
python3 -m pytest tests/ -q   # 422 passed, 19 skipped
```

No credentials and no network. The console renders entirely from a committed snapshot, so a
judge can clone and run it with no IBM account.

The count depends on what the machine carries. A clone installs `requirements.txt` and
nothing else, so four groups skip: fifteen tests that replay registry version history out
of the gitignored `data/cache/`, one credential-gated live Granite check, one
browser-geometry check needing Playwright, and two accessibility checks needing Playwright
and axe-core. Four tiers, each adding one thing to the one above it, each with its own
command:

| tier | what it needs | command | result |
|---|---|---|---|
| base | `pip install -r requirements.txt` | `CID_BASE_DEPS_ONLY=1 python3 -m pytest tests/ -q` | **422 passed, 19 skipped** |
| Playwright | base, plus `pip install playwright && python3 -m playwright install chromium` | `python3 -m pytest tests/ -q` | **423 passed, 18 skipped** |
| Playwright + axe | Playwright, plus `npm ci` | `npm run test:a11y` | **425 passed, 16 skipped** |
| cache-backed research | Playwright, plus a populated `data/cache/` | `python3 -m pytest tests/ -q` | **438 passed, 3 skipped** |

Base is what a judge gets, and on a clone with nothing extra installed the plain command
produces it. The last tier shares a command with the second because the cache is data
rather than a dependency. Running the axe command with the cache present runs both and
leaves the credentialed Granite check as the only skip, at 440 passed and 1 skipped. That
figure and the cache-backed row were off this page for two commits, because at the counts
they carried then both passed counts were also renderings of a cohort field and
`tests/test_prose_figures.py` cannot tell the two apart. The decision review screen and the
activity history have moved the counts twice since, and neither collides, so both stay
printed. Measure the base and
Playwright tiers with `node_modules/` absent: the scan runs wherever it finds axe-core, so a
machine that has run `npm ci` reports one tier higher than the row it thinks it is running.
The fifteen cache tests verify the cohort research rather than the console, so nothing on
the demo path depends on them.

`package.json` and `package-lock.json` pin axe-core and nothing else, so `npm ci` installs
the exact version these numbers were measured against. No frontend build step, no bundler,
no framework: the product is Flask and Jinja. axe-core is MPL-2.0 and is installed rather
than vendored, so no third-party source is committed here, and the tests read it from disk
rather than a CDN so the tier runs offline.

`npm run test:a11y` is the whole accessibility command and it sets `CID_AXE_REQUIRED=1`
itself, so the strict requirement is not something a reader has to remember. It exits
nonzero on a missing axe-core, on zero scans executed, and on any violation, because a
`skip` and a `pass` look identical in a summary line. Which pages get scanned is keyed on
the app's own `url_map` rather than typed into the test: every route is either scanned or
named with a reason for not being, so a new screen fails the suite until it is classified.
Seven pages are scanned across six routes, at 1440x1000, 1024x768 and 390x844 for the two
whose layout changes with the width, and all of them report zero violations. That is
coverage of the Phase 2 surfaces and not of the whole app; the Phase 1 screens are
named as unscanned and `docs/LIMITS.md` says what is open on them.

## Links

- GitHub repository: **https://github.com/kristenharim/catalyst-integrity-desk**
  Public, `main`, README at the root. Published 2026-07-22.
- Demo video: _pending. Script is `docs/DEMO.md`, maximum 3 minutes._
- SkillsBuild certificate: _obtained, still to upload to the project page._

Clone and run, for a judge with no IBM account:

```bash
git clone https://github.com/kristenharim/catalyst-integrity-desk.git
cd catalyst-integrity-desk
pip install -r requirements.txt
python3 -m console.app        # http://localhost:8050
```

---

## If a field asks for something not covered here

Pull it from `README.md` first, `docs/LIMITS.md` for anything about guarantees, and
`docs/CONJECTURE.md` for anything asking where this could go next. Do not write a new claim
from memory: every figure in this file traces to `data/snapshot.json` or `docs/BOB_LOG.md`.

## Do not say

- "Immutable" or "append-only" about the ledger. It is tamper evident, and deletion is  [lexicon-exempt]
  detectable given the anchor was not also rewritten.
- "Readout date". It is a registered primary-completion expectation, and the two differ by  [lexicon-exempt]
  two to four months, always optimistically.
- That cash-constrained sponsors revise dates differently. That is an open question this
  project deliberately does not answer.
- That the technology works, that a timeline will hold, or anything with the word that  [lexicon-exempt]
  means believable-about-management. Those are feasibility verdicts and this system does  [lexicon-exempt]
  not make them. `orchestrator/lexicon.py` is the enforced list.  [lexicon-exempt]
- A net-slip figure without saying how many revisions were not comparable. The audited
  trials include established, contingent, and refused movements, and a net-slip total is
  not usable unless promise identity holds across the revisions being compared. Do not
  resurrect the first audit's single count of unsupported trials; the three-state audit
  retracted it.
- "No tool does this". A commercial screener covers the ranking layer and a judge will find
  it. The honest claim is the monitor.
