# Catalyst Integrity Desk

An auditable monitor for when a biotech investment thesis no longer matches its approved evidence contract.

Catalyst Integrity Desk does not decide whether an investment thesis is true. It records the evidence and assumptions behind a thesis, detects when later public records no longer match them, drafts a constrained challenge, and routes the decision to a human.

A belief entered through the console is hash-chained into a ledger. The system does not silently revisit or rewrite it.

## At a glance

- **What it does:** tracks whether a biotech sponsor's public, dated commitments (trial completion dates in ClinicalTrials.gov, cash runway from SEC filings) were kept, revised or quietly allowed to expire, and flags when a thesis built on them no longer holds.
- **Headline finding:** Rocket Pharmaceuticals revised trial `NCT04248439` in April 2024 with a completion date that had already passed 648 to 677 days earlier. Re-anchored to the current catalyst, the same runway math flips from **+8.4 months, funded** to **-14.5 months, financing required**.
- **Wider sample:** in a random sample of 240 Phase 2 and 3 trials, most expired commitments were never reconciled (for example, 20 of 27 in the `OTHER_GOV` stratum).
- **How it stays honest:** every belief is hash-chained into a ledger, model output is limited to a fixed vocabulary, and a human makes every decision.
- **Built for:** the IBM AI Builders Challenge, July 2026, with IBM Bob under explicit edit constraints.
- **Try it:** `pip install -r requirements.txt && python3 -m console.app` (no keys or network needed; see [Quickstart](#quickstart)).

## Issue background

In April 2024, Rocket Pharmaceuticals filed a protocol revision for trial `NCT04248439` that still listed a primary-completion date of June 2022. Because the registry records only a month, that commitment had already been expired for between 648 and 677 days when the revision was filed.

The important finding is not that Rocket is unusual. It is that this kind of mismatch can remain public, machine-readable, and unaddressed because no system is assigned to compare a new registry version with the thesis built on the earlier one.

A random sample of 240 Phase 2, Phase 2/3, and Phase 3 trials supports that concern. The study cannot separate reconciliation from filing frequency, but most trials with an expired commitment had never reconciled it: 4 of 5 in `INDUSTRY`, 20 of 27 in `OTHER_GOV`, and 15 of 19 in `OTHER`.

Among still-open commitments, 27 of 29 in the `OTHER_GOV` stratum had already expired. NIH-sponsored trials showed a median of 106.5 registry versions per trial and no currently expired completion dates; `OTHER_GOV` sponsors showed a median of 2 versions. The ordering is monotone across four strata, but it is an association across four points—not a tested causal relationship.

That changes the measure the project began with. Counting only lapses later corrected makes frequent filers look like the best reconcilers, because a lapse becomes visible only when its sponsor files again. A measure that requires its subject to keep reporting cannot observe the subject that stops.

Among sponsors still filing, at least 22.2% of industry completion-date revisions replaced an estimate that had already expired. The first-of-month convention produces 26.2% (33 of 126). Of industry trials that revised a date at all, 24 of 52 (46.2%) did so at least once.

Industry point prevalence was 8.3% across all trials and 33.3% among trials with an open commitment. For the Rocket anchor case, the 677-day first-of-month reading sits at the 85th percentile of 188 comparable stretches. The percentile is reported with the same date convention used to calculate it.

`docs/WRITEUP.md` contains the standalone study, and `docs/COHORT.md` contains the working record.

Every cohort figure in the claim documents is rendered from snapshot `cohort-5b03269658b8` by `research/render_writeup.py`: 240 trials, 60 in each sponsor stratum, measured as of 2026-07-22. A test regenerates each generated block and fails on a one-byte difference.

## Main claim

> **This system measures whether public, dated, self-authored commitments were kept, revised, superseded, or allowed to expire without reconciliation. It does not measure whether the underlying claim was ever true.**

Diligence wants a verdict on the science and on whether a stated date will hold. A system reading public records cannot provide either without turning opinion into evidence.

What it can answer is narrower and useful: whether a sponsor’s current public record still reconciles with its prior commitments.

Theranos illustrates the distinction. A public-record system could not have settled the feasibility of its technology in real time. It could, however, have tracked claims that no longer reconciled with earlier claims. That pattern is measurable; feasibility is not.

`docs/PRINCIPLE.md` defines this boundary, and `orchestrator/lexicon.py` enforces it across model output, rendered pages, and claim-bearing documents.

## The problem

Every clinical-stage biotech thesis contains a timing assumption:

```text
funding gap = runway exhaustion date - registered primary completion date
```

Cash runway comes from SEC filings. The clinical commitment comes from ClinicalTrials.gov, where a sponsor can revise a date at any time. Each version is public and timestamped, but the registry does not compare a revision with the investment thesis that depended on the earlier date.

A registry record is not an observation. It is a self-authored claim by an interested party, capable of revision. ClinicalTrials.gov is one instance of that broader pattern.

This project treats the thesis as a contract and audits both sides of it.

## Two modes, one computation path

```text
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

`tests/test_layering.py` walks the AST and fails if `engine/` or `orchestrator/` imports that layer. A module that calculates a displayed value therefore cannot behave differently because it knows whether it is running against frozen or live evidence.

That separation makes the demo evidence about the product rather than a mock of it.

`/workspace` runs the live flow without credentials because committed bundles and live fetches share one schema.

## Quickstart

The demo requires no credentials, API keys, or network access.

```bash
git clone https://github.com/kristenharim/catalyst-integrity-desk.git
cd catalyst-integrity-desk
pip install -r requirements.txt
python3 -m console.app            # http://localhost:8050
python3 -m pytest tests/ -q
```

Run it as a module from the repository root. Set `PORT` to use a port other than 8050.

The console reads only the committed `data/snapshot.json`. It makes no network call and reads no credential.

### Test tiers

The available test count depends on which optional tooling and research cache are present.

| Tier | Requirements | Command | Result |
|---|---|---|---|
| Base | `pip install -r requirements.txt` | `CID_BASE_DEPS_ONLY=1 python3 -m pytest tests/ -q` | **534 passed, 19 skipped** |
| Playwright | Base plus Playwright and Chromium | `python3 -m pytest tests/ -q` | **535 passed, 18 skipped** |
| Playwright + axe | Playwright plus `npm ci` | `npm run test:a11y` | **537 passed, 16 skipped** |
| Cache-backed research | Playwright plus populated `data/cache/` | `python3 -m pytest tests/ -q` | **550 passed, 3 skipped** |

On a clean clone without optional tooling, the base tier is the expected result. `CID_BASE_DEPS_ONLY=1` pins that result on machines that also carry optional dependencies.

The cache changes available research data rather than adding a software dependency. The browser test checks the demo’s opening frame, and the accessibility suite runs axe-core over the Phase 2 decision spine: inbox, receipt, redline, confirmation, decision review, and activity history.

The responsive screens are measured at 1440×1000, 1024×768, and 390×844 because a breakpoint can create a defect that is absent on either side of it.

`package.json` and `package-lock.json` pin axe-core and nothing else. The product is Flask and Jinja; there is no frontend build step. axe-core is loaded from disk rather than a CDN, preserving the demo’s no-network guarantee.

`npm run test:a11y` fails closed: it exits nonzero if axe-core is unavailable, if no pages are scanned, or if a violation is found. Routes are keyed to the app’s `url_map`, so every route must either be scanned or named in `A11Y_NOT_SCANNED` with a reason.

The scanned Phase 2 pages report zero axe violations. This is not whole-application accessibility coverage; Phase 1 surfaces are explicitly named as out of scope in `docs/LIMITS.md`.

### The 90-second tour

| Location | What it shows |
|---|---|
| `/` | Redirects to the Rocket detail. The expired commitment is the opening example. |
| Red node | An April 2024 revision carrying a June 2022 completion date. |
| Detail table | Every input and the XBRL tag through which it resolved. |
| `/contracts` | Ranked contracts, unreliable rows kept visible but unranked, and contracts that could not be produced. |
| `/redline` | The approved thesis, its breach, and Granite’s constrained memo. |
| `/workspace` | A ticker becomes a recorded contract; identity and empty queries are shown before candidates. |
| `/belief/new` | The analyst records a thesis, trial, and invalidating funding gap. |
| Accept | Writes a hash-chained ledger entry and recomputes the integrity badge. |
| `/inbox` | One task per decision, ordered by urgency, with reasons grouped under each item. |
| `/receipts/<entry hash>` | A single decision record, addressed by its own hash and checked at render time. |
| `/evidence/<contract id>` | The provenance chain behind a displayed figure and the places where that chain stops. |

### Tamper demonstration

Accept the redline, edit any byte inside the `card` object in `data/decisions.jsonl`, and reload the confirmation page.

The badge changes from `✓ intact` to `✗ tampered` because the page calls `verify()` at render time rather than trusting the redirect that led to it.

### Reset between runs

```bash
rm -f data/decisions.jsonl data/review_log.jsonl data/ledger.anchor
```

These are gitignored live-state files created during a demo. The committed `data/snapshot.json` is frozen evidence and should not be removed.

### Frozen evidence

The snapshot was built from live SEC XBRL company facts, live ClinicalTrials.gov version history, and a live IBM Granite call. The Granite classification is recorded with `source: "granite"`.

Rebuilding requires credentials and does not occur during a demo. `docs/bob-sessions/` contains the build transcripts.

## The theme: intelligent systems for the future of work

The work being automated here is not analysis. It is **noticing**.

An analyst can calculate a funding gap quickly. What does not happen reliably across a portfolio is rereading a registry every week, detecting a revised date, and checking whether it breaks a thesis written months earlier.

The system records a belief against a frozen evidence contract, detects when a rebuild contradicts that belief, drafts a challenge in the analyst’s vocabulary, and stops. A human accepts or rejects the result; the decision is then hash-chained into a tamper-evident ledger.

Judgment remains human. Vigilance is what gets automated.

## The AI approach

**Python computes. Granite judges prose. Humans decide.**

IBM Granite on watsonx does not produce a number. It reads the analyst’s written rationale beside the recomputed contract and identifies which stated assumption has been challenged. Every figure displayed by the product comes from Python arithmetic over filed data.

That rule is enforced rather than asserted.

`_quantitative()` rejects model output containing quantitative expressions: digits, number words, percentages, ratios, signs, durations, and date forms that express a quantity without a digit. A response that trips the rule is discarded whole and replaced by a deterministic stub. It is never edited in place, because deleting a number can change a sentence’s meaning.

An earlier rule prohibited only numbers absent from the input. That rule was retired after audit: a bare number in an analyst’s thesis could authorize that magnitude in an unrelated metric unit. `docs/LIMITS.md` records the reasoning and the remaining limitation.

`_quantitative()` prevents the model from measuring. `orchestrator/lexicon.py` prevents it from making claims the evidence cannot support: feasibility verdicts, claims of intent, causal explanations, or assertions that silence is evidence. The same lexicon scans model output, pages, and claim-bearing documents.

### Promise identity

A slip is only a slip if the promise retained its identity.

`engine/promise.py` classifies registry revisions as unchanged, date-only, scope revision, supersession, or uncertain. Only unchanged and date-only revisions can produce a definitive delay number.

If a revision changes a primary endpoint, it may describe a different commitment. Subtracting the dates would not establish a delay. The system therefore distinguishes established, contingent, and refused movements.

### Supporting rules

**Every displayed number names its source.** `Runway.provenance` records the XBRL tag used for each component because issuers do not use uniform tags. The console displays the tag beside the figure.

**A lapsed completion date is never a catalyst.** The system retains expired dates as integrity signals. It does not treat an event that should already have happened as a future funding target.

## How IBM Bob was used

IBM Bob built the original governance port, redline loop, analyst console, snapshot generator, SVG revision timeline, and initial test suite. It also repaired the integrity badge test-first.

The governance port includes the Ledger, Challenge, Classifier, and Granite modules adapted from an earlier project. Prompts were rewritten for Catalyst terminology, while `_fabricated()` was preserved byte-for-byte. Bob also added `engine/contract.py`, which flattens a contract into the packet used by the breach scanner.

The three verified modules in `engine/`, along with the specifications, findings, demo script, and prompt pack in `docs/`, predate Bob. They were validated against live SEC and ClinicalTrials.gov data before the build began.

Bob was constrained rather than trusted. `.bob/custom_modes.yaml` limits edit access with `fileRegex`, protecting the verified engine modules, and defines a read-only reviewer mode so review cannot quietly alter what it assesses.

Other AI tools were used only for permitted review, with each pass recorded separately in `docs/BOB_LOG.md`.

Later work was implemented by hand with Claude Code and logged at the same level of detail. It includes the evidence seam, promise identity, claims lexicon, workspace mode, cohort study, decision-state model, non-quantitative Granite policy, locked ledger append, accessibility and test-isolation fixes, and the Phase 2 decision screens: inbox, receipts, review, activity history, evidence explorer, desk, and memo views.

In short: Bob built the original governance, redline, console, receipt, and research-panel foundations. Later extensions and adversarial corrections were implemented separately with Claude Code. Representing that division accurately matters more than claiming a single tool made the whole project.

## How it was verified

Every meaningful defect in this project initially had the same symptom: the suite was green.

A model test can pass through a stub fallback. A helper can be imported but never called. A snapshot can omit a computed property. For that reason, no guard is trusted until it has been deliberately made to fail.

- The fabrication guard runs against live Granite rather than a mock. It was checked with an invalid endpoint and failed on `source == "granite"` rather than passing through the stub fallback.
- The number-provenance test was checked by placing `9999` in a template and confirming that the test identified it.
- The ledger-badge test was written before its repair and observed failing first.
- Console checks were deliberately re-broken after repair: the marker class was renamed, `stub` was forced into a memo, and `days_expired` changed from 677 to 123. Each check failed as expected.

`docs/LIMITS.md` states what each safeguard proves and what it does not.

## What it found

**Rocket Pharmaceuticals.** In April 2024, `NCT04248439` was revised with a primary-completion date that had already expired for between 648 and 677 days. That date has since passed.

The binding catalyst is now `NCT06092034`, with a registered primary-completion date of 2028-04. Against that date, the same runway calculation produces **-14.5 months: financing required**. Against the earlier date, the thesis read **+8.4 months: funded**.

No later registry version reconciled the lapsed expectation. The date simply arrived and passed.

The project also corrected its own earlier net-slip figures. Summing every date movement without checking whether the commitment remained the same produced claims the system could not support.

- **`NCT06092034`: 943 days reported, 0 days established.** The revision changed enrolment from 12 to 14, so the promise changed.
- **`NCT04248439`: 1,008 days reported, -422 days established, +1,430 days contingent, upper bound 1,008 days.** The endpoint wording changed in a way that may be a clarification or may be a redefinition. The registry text alone cannot settle that question.

The 677-day result remains valid because it concerns one registry version carrying a date that had already passed; it does not require comparing two potentially different commitments.

The research panel requests 12 clinical-stage, pre-revenue companies. Seven of them reach `research/panel.csv`, and all seven carry a rankable runway band. The other five produced no contract in that run, because of the sponsor-name join, not anything about those companies.

Burn is reported as a band rather than a point estimate because a single quarter can be distorted by a partnership upfront. Rows with unreliable burn remain visible, with their reason attached, but are never ranked.

## What this is not

This is not a claim that cash-constrained sponsors revise dates differently from solvent sponsors. That remains an open question.

This is not a novel registry dataset or a commercial screener. Existing adjacent work is cited in `docs/DEMO.md`.

The claim is the monitor.

The system says **registered primary-completion expectation**, not “readout date.” Those concepts differ systematically, often by months, and treating them as interchangeable would be optimistic.

## Layout

```text
evidence/                 EvidenceSnapshot, frozen and live providers
engine/promise.py         promise identity; refuses unsupported slip numbers
engine/dimensions.py      endpoint and enrolment by registry version
engine/runway.py          cash runway from SEC XBRL company facts, as a band
engine/ctgov_history.py   registry history, notice, and expiry metrics
engine/gap.py             catalyst-contract join
engine/ledger.py          hash-chained belief ledger
orchestrator/             redline loop, challenge builder, Granite client
orchestrator/lexicon.py   forbidden-claims policy for model, pages, and docs
console/                  Flask console and snapshot generator
research/                 monitoring-queue panel, CSV, and figures
tests/                    automated checks; no network or credentials required
data/snapshot.json        frozen demo artifact
docs/PRINCIPLE.md         core claim and forbidden-claims policy
docs/WORKSPACE.md         two-mode design
docs/BOB_LOG.md           what Bob built and what preceded it
docs/bob-sessions/        Bob task exports supporting the log
docs/FINDINGS.md          data gotchas, prior art, and attack surface
docs/DEMO.md              demo script
```

Read `docs/FINDINGS.md` before writing extraction code. Each documented gotcha produces a plausible wrong number rather than an error, and one previously created a 49× mistake that looked exactly like a company about to run out of money.
```
