# Can this system name three historical failures it would have caught?

The honest answer is **no, not the three usually named**, and the reason is more useful
than a yes would have been.

This file exists because the question was asked as a pressure test, and a project whose
entire claim is that it does not flatter itself has to answer it with evidence rather than
argument.

## The three named cases, checked rather than reasoned about

### Theranos

Queried ClinicalTrials.gov for Theranos as sponsor, 2026-07-22:

```
sponsor "Theranos"        1 study    NCT01144793, lead sponsor STANFORD UNIVERSITY
sponsor "Elizabeth Holmes"  0 studies
```

**Theranos never registered a trial as sponsor.** The single record that mentions it is
Stanford's. There is no dated, versioned, self-authored commitment to compare against
anything, so there is nothing for this system to diff. It would return "queried, nothing
found", which is exactly what `NegativeResult` is for. That is a statement about the
registry, and the system must never let it become a statement about the company.

### Nikola

```
sponsor "Nikola"          5 studies   all of them physicians named Nikola
```

Zero. Nikola Corporation has no registry footprint, because trucks are not registered on
ClinicalTrials.gov. Its central misrepresentation, a truck rolling downhill in a video,
was never a dated commitment filed to any registry with version history. The company had
SEC filings, but the claim in question lived in a promotional video, not in a tagged field
of a versioned document.

### A thin-application-layer AI startup

There is no registry at all. No dated self-authored commitment, no versions, nothing to
diff. Not in scope by any reading.

## Why that is the useful answer

The admission test a domain has to pass, before this system can say anything about it:

1. the interested party authored the claim, not a regulator or a journalist
2. the claim resolves to a specific date
3. publication time is independently and durably recorded
4. historical versions are retrievable
5. the promised object has stable identity across revisions
6. completion has an externally observable meaning
7. a correction is distinguishable from a substantive revision
8. silence is distinguishable from absence of data

ClinicalTrials.gov passes all eight, which is why the project starts there. Theranos fails
2 through 5 for every claim that mattered. Nikola fails 1 through 5. A pitch deck fails all
eight.

So the sentence **"catches Theranos-class failures"** is not one this project can ship. It
is in `orchestrator/lexicon.py` as a banned claim, and `tests/test_lexicon.py` fails the
build if it appears in a doc or on a page.

**One Theranos signal is in scope, and it is not the one people reach for.** Not "the
chemistry is wrong", which no outsider could evaluate. Rather: a diagnostics company whose
peers all register trials, which registers none, over a decade. That is conspicuous absence
and it is measurable. This system already records the shape of it (`NegativeResult`: a
source queried, and empty, at a stated time) but does not yet compare a company's registry
footprint against a peer set, which is what would turn the absence into a signal. Named
here as the next research task rather than claimed as a capability.

## What is demonstrated instead

Something narrower and, unlike the above, actually verified: **period-accurate replay.**

ClinicalTrials.gov keeps every version a sponsor ever submitted with its submission date,
so a backtest here is honest rather than simulated. `research/backtest.py` takes a cutoff
date, discards every version submitted after it, and evaluates. Nothing after the cutoff
can leak, because nothing after the cutoff is in the input, and
`tests/test_backtest.py` asserts that blindness at five cutoffs across every cached trial.
Verified by mutation: flipping the comparison so the future leaks fails with the offending
version named.

### The Rocket case, replayed

The project's headline result, re-derived from raw versions rather than quoted:

```
$ python3 -m research.backtest NCT04248439 --as-of 2023-09-01

  versions visible: 2 of 4

  [carried_expired]
    the registered primary completion is 2022-06, which passed 457 days before
    this date, and version 1 (submitted 2020-11-23) still carries it
```

The signal became publicly observable on **2022-06-02**, the day after the registered date
passed, on a day when nothing was filed and nothing happened. The sponsor did not correct
it until **2024-04-08**. That is **677 days**, reached independently of the engine, which
computes the same figure by a different route.

Detection latency is the claim. Not prediction: no observation asserts an outcome or a
cause, and a test scans every replay output through the forbidden-claims lexicon. That test
was verified by planting a forbidden causal phrase into a replay observation and  [lexicon-exempt]
watching the lexicon name it.

### Across the cached trials

Six of fourteen carried an already-passed registered completion date at some point, in
fourteen separate stretches:

| Days carried | Trial | Expired | Corrected |
|---:|---|---|---|
| 677 | NCT04248439 | 2022-06-01 | 2024-04-08 |
| 392 | NCT05654623 | 2025-01-31 | 2026-02-27 |
| 360 | NCT06246513 | 2025-03-04 | 2026-02-27 |
| 349 | NCT05654623 | 2025-01-31 | 2026-01-15 |
| 173 | NCT06206837 | 2025-09-05 | 2026-02-25 |
| 150 | NCT05654623 | 2025-01-31 | 2025-06-30 |
| 127 | NCT06246513 | 2025-03-04 | 2025-07-09 |

`NCT05654623` is the one to look at. The same registered date, 2025-01-31, went past and
was left standing through four successive filings: the sponsor updated the record at 40,
150, 349 and 392 days after the date had died, and corrected something else each time.

This is a description of registry behaviour. It is not a claim about those sponsors,
those programmes, or what happens next, and the lexicon is what stops it becoming one.

## What would have to be true to reach further

Ranked by how much has to hold, least first.

**Within the current source.** Compare a company's registry footprint to a peer set, so
conspicuous absence becomes measurable. Requires a defensible peer-set definition, which is
a judgement and would have to be shown rather than hidden in a score.

**Adjacent structured sources**, in descending order of how cleanly they pass the admission
test: FDA postmarketing commitments (careful: some dates are regulator-set, not
sponsor-authored, and the two must not be mixed); federal award periods of performance
against "on track for Phase II" claims; patent prosecution status against "patent pending".
Each is a new base-rate table, not a rebuild, because the claim schema is the same shape.

**The hard boundary.** Everything above stays inside "the party authored a dated commitment
to a registry that keeps versions". Pitch decks, benchmark claims and demo videos are on
the other side of it. Extending there means deciding which prose claims are the same claim,
revised, and that decision is a semantic judgement no guard in this project can currently
police. It is the same failure that `engine/promise.py` exists to prevent, one layer
further out and much harder, and doing it badly would produce confident wrong answers with
provenance trails attached.

The honest position: this system covers one failure class well, has a demonstrated
period-accurate replay for it, and does not reach the three cases usually named. Saying
otherwise would be the exact failure the project was built to catch.
