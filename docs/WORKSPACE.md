# Workspace mode: ticker in, recorded contract out

**Nothing in this file is built.** It is a design, written at the same discipline as the
rest of the repo: what exists is marked as existing, what is proposed is marked as
proposed, and the problems that have no answer yet are named rather than skipped.
`docs/CONJECTURE.md` covers where the *idea* could go. This file covers where the
*product* could go, which is a narrower and more concrete question.

Read `docs/LIMITS.md` first. Several things proposed here are only possible because
workspace mode fixes a limitation the demo has, and several are impossible for reasons
that file already states.

## The problem with what exists

The console is a museum exhibit, and that is on purpose.

```
SEC + ClinicalTrials.gov
          |
          v
   make_snapshot.py          credentials, network, one live Granite call
          |
          v
   data/snapshot.json        committed, frozen, 5 companies
          |
          v
   Flask reads it            no network, no credentials, identical every time
```

That is close to mandatory for a competition. A judge clones the repo and sees exactly
what the README describes. Tests do not fail because the SEC restated a filing overnight.
Screenshots stay true.

It is also not how anyone would use it. The five companies were chosen by whoever wrote
`TICKERS`. An analyst arrives with a ticker and a thesis, not with this list.

## The split

Same engine, same views, two sources of evidence.

```
DEMO MODE                            WORKSPACE MODE

data/snapshot.json                   ticker
        |                                |
        |                                v
        |                          live SEC + ClinicalTrials.gov
        |                                |
        v                                v
    the same views, the same arithmetic, the same ledger
```

The rule that makes this worth doing: **one code path, two data sources.** The moment
demo mode and workspace mode compute a funding gap differently, the demo stops being
evidence about the product. Everything downstream of "produce a `CatalystContract`" must
be shared, and the split lives entirely above that line.

Concretely, the seam is already in the right place. `engine/gap.py::build()` returns a
`CatalystContract`; `console/make_snapshot.py` serialises one into the snapshot dict;
every view reads that dict. Workspace mode produces the same dict from a live call
instead of from a file. Nothing below the seam changes, which matters because the three
`engine/` modules are verified against live APIs and are not to be rewritten.

## The flow

The analyst types one thing.

```
  ticker
    |
    v
  resolve to CIK and legal name          engine/runway.py::ticker_to_cik  [exists]
    |
    v
  fetch XBRL facts, compute runway band  engine/runway.py::compute_runway [exists]
    |
    v
  search trials by sponsor name          engine/gap.py::find_trials      [exists]
    |
    v
  fetch each trial's version history     engine/ctgov_history.py::fetch_history [exists]
    |
    v
  split future from lapsed               engine/gap.py::build            [exists]
    |
    v
  ANALYST CONFIRMS WHICH TRIAL                                            [proposed]
    |
    v
  propose a contract, show the derivation                                 [proposed]
    |
    v
  ANALYST APPROVES                                                        [proposed]
    |
    v
  BeliefCard into the hash-chained ledger  engine/ledger.py::create      [exists]
```

Everything marked `[exists]` is already verified against live APIs and already runs. The
new work is the two human gates and the intake layer around them.

### Why the analyst must pick the trial

A ticker does not determine a thesis. Rocket has several pivotal trials and the thesis
rests on one of them. The system can rank candidates and recommend the nearest registered
primary completion still in the future, which is exactly what `build()` already does, but
recommending is not deciding.

```
We found 3 candidate catalysts for Rocket Pharmaceuticals.

  (o) NCT06092034   Danon disease          registered completion 2028-04
  ( ) NCT04248439   Fanconi anemia         LAPSED 2026-05-05, never amended
  ( ) NCT0xxxxxxx   PKD                    registered completion 2029-09

Which one underwrites your thesis?
```

The lapsed row is listed and cannot be selected as a catalyst. A lapsed completion date is
never a catalyst, which is a rule this project does not bend; it is shown because a
sponsor carrying an expired date is the signal the project exists to surface.

### Why the system proposes the thesis

Making an analyst type "cash lasts until the catalyst" is worse than showing them a
proposal to edit. The proposal is deterministic prose assembled from fields, not generated
text:

```
Proposed contract

  Company            Rocket Pharmaceuticals          CIK 0001281895
  Trial              NCT06092034                     Danon disease
  Metric             gap_months
  Breach below       0 months                        unbounded above

  Claim
  "Current liquidity reaches the registered primary completion of NCT06092034
   (2028-04) without additional financing."

  Monitor for
   [x] the registered completion moving later
   [x] the registered completion lapsing
   [x] runway falling below the stated minimum
   [x] the burn band becoming unreliable
   [ ] the SEC XBRL tag path changing        (needs a second run; see below)
```

Every field is editable before approval. The claim text is what Granite reads when a
breach fires, so it is the analyst's words that get judged, not a template's.

`/belief/new` already does a two-stage version of this: form, review, commit. Workspace
mode replaces the hand-typed fields with discovered ones and inserts the trial-selection
step. The validation, the review gate, and the ledger write are already built and tested.

### The evidence page

This is where the project has the most room to improve, and where it is furthest along.

**What exists:** `_derivation()` builds a linear row list from filed data to the funding
gap, and every row names its record: an XBRL tag with CIK and filing date, or a numbered
ClinicalTrials.gov version with its submission date. It renders on `/contract/<ticker>`
and behind the headline figure on `/redline`.

**What is proposed:** the same content as a graph rather than a table, with each node
expandable.

```
   Cash $50M ──┐
               ├── Liquidity $144M ──┐
  Securities   │                     │
       $95M ───┘                     ├── Runway 9.5 months ──┐
                                     │                       │
  Operating cash flow ── Burn $182M/yr                       ├── Gap -14.5 months
                                                             │
  NCT06092034 v3 ──────── Registered completion 2028-04 ─────┘
```

Click `Burn $182M/yr`:

```
  Tag        NetCashProvidedByUsedInOperatingActivities
  Filing     10-Q, CIK 0001281895, period ending 2026-03-31
  Window     most recent quarter, annualised
  Why this   the conservative end of the band; the trailing-twelve-month
             figure is $180M/yr and would flatter the row
```

The honest caveat, which `docs/LIMITS.md` states: the derivation currently *names* a
record and nothing *resolves* it. The record is an assertion the builder makes about
itself. Workspace mode makes resolving it cheap, because the raw API response is in hand
at build time rather than months earlier, so the upgrade is to store the response and
assert the rendered figure against the exact field it claims.

## Documents

An uploaded memo supplies **qualitative context only**. This is not a nicety, it is the
project's central rule applied to a new input.

```
  ALLOWED                              FORBIDDEN
  extract stated assumptions           extract any figure and use it
  extract which trial matters          extract a date and treat it as registered
  extract invalidation conditions      extract a cash balance
```

Every number continues to come from SEC XBRL and from a specific registry version.
`_fabricated()` already enforces that a model cannot introduce a figure absent from its
input, and it is ported byte for byte from the prior project. Document intake does not
change it.

What the model returns is a checklist for a human:

```
Assumptions found in RCKT-initiation-2026-01.pdf

  [x] Liquidity reaches the selected trial expectation without financing
  [x] The Danon disease programme is the thesis-bearing asset
  [x] No dilutive financing before the catalyst
  [ ] Peak sales above $1.2B                (out of scope: this desk does not model revenue)

Create a monitoring contract from the checked items?
```

The last row matters. A document contains assumptions this system cannot monitor, and
saying so is better than silently dropping them.

## Monitoring, and the morning inbox

`/queue` already answers "which beliefs need attention", against the frozen snapshot. In
workspace mode it answers it against last night's run.

```
  every night, per contract

  fetch SEC + registry  ->  rebuild CatalystContract  ->  compare to the approved card
                                                             |
                                              still in band? |
                                                   yes ------+------ no
                                                    |                 |
                                                 nothing        run_redline()
                                                                      |
                                                             Granite classifies
                                                                      |
                                                            queued for a human
```

`orchestrator/redline.py` and `orchestrator/challenge.py` already do everything from
"compare" rightward, and are tested. The new part is the scheduler and the storage.

**Two queue states become possible that are impossible today.** `docs/LIMITS.md` records
that "newly breached", "moved since last look", and "SEC tag path changed" were left out
because one committed snapshot has nothing to diff against. Workspace mode stores a run
per night, so a diff exists, and those states can be computed honestly rather than
implied. This is the single strongest product argument for the split.

## What to build

Around the protected engine, not through it.

```
console/intake.py            ticker validation, discovery, candidate assembly,
                             document handling, proposed-contract construction
console/templates/
    new_contract.html        ticker and optional document
    select_trial.html        candidate selection, lapsed rows shown and unselectable
    review_contract.html     derivation, proposed claim, approve gate
data/contracts.jsonl         approved analyst contracts, or SQLite when querying bites
data/runs/<date>/            one stored snapshot per nightly run; the diff source
```

Routes:

```
GET   /contracts/new           ticker form
POST  /contracts/discover      resolve, fetch, rank candidates       (slow: show progress)
POST  /contracts/select-trial  analyst picks the binding trial
POST  /contracts/preview       proposed contract + full derivation
POST  /contracts/approve       BeliefCard -> ledger, anchor recorded
GET   /contract/<card_id>      the recorded contract over time
```

`/belief/new` becomes the manual path and stays, because an analyst who already knows the
trial should not be made to walk a wizard.

## The problems this does not solve

Listed because a design that only lists its wins is not a design.

**Sponsor-to-issuer identity is the gating problem.** `find_trials()` matches on free-text
sponsor name and there is no CIK in the registry. Names drift across subsidiaries,
punctuation and post-merger renames. In demo mode a bad match is invisible: SANA produced
no contract and, until recently, silently vanished from the page. In workspace mode a bad
match is *the analyst's first impression*, so a confidence score, an alias table and a
review queue stop being a nice-to-have. Nothing else on this page matters if the wrong
company's trials come back.

**The clock.** The snapshot now pins its own `as_of` and never re-reads the wall clock,
but `build()` still splits lapsed from future on `date.today()` during a rebuild. A nightly
run must stamp its own `as_of` and every diff must be between two stamped runs, or
"the date lapsed overnight" and "we rebuilt at a different hour" become indistinguishable.

**Concurrency.** The ledger has no compare-and-swap on the head. Two analysts approving at
the same moment both read the same head hash and both append. Untested today, and
untestable to ignore once there is more than one analyst.

**The anchor is still self-owned.** `data/ledger.anchor` is written by the same process
that writes the ledger. Multi-user makes this worse, not better: the honest fix is a
signature or a second machine, not a second file.

**Reproducibility.** Nothing asserts that building twice from the same inputs produces the
same bytes. Workspace mode makes this load-bearing, because a diff between two runs is
only meaningful if a no-change night produces no diff.

**Rate limits and cost.** SEC and ClinicalTrials.gov both throttle. Forty contracts a
night is fine; four hundred needs caching and backoff, and the version-history endpoint is
the expensive one.

## What must not change

Carried forward verbatim, because the value of this project is that these hold.

- Python computes, Granite judges prose, humans decide. No model-produced number reaches
  the user.
- Every displayed figure names a specific XBRL tag or a specific registry version.
- Unreliable rows are shown, never ranked, and never silently dropped. That includes not
  printing a gap figure beside a row the system calls unrankable.
- A lapsed completion date is never a catalyst. It is retained and surfaced as a
  date-integrity signal.
- Say "registered primary-completion expectation", never "readout date".  [lexicon-exempt]
- The claim is the monitor. Not a novel dataset, and not a finding.
