# The principle, and what it forbids

## The claim, in one sentence

> **This system measures whether public, dated, self-authored commitments were kept,
> revised, superseded, or allowed to expire without reconciliation. It does not measure
> whether the underlying claim was ever true.**

The second sentence is not a disclaimer. It is half the product, and it is the half that
gets cut first under pressure to make the pitch land, which is exactly why it is written
down here and enforced by a test.

## Why the tempting version is the wrong one

The question everyone actually wants answered in diligence is "does this technology work,
and are these timelines real". It is the right question. It is also not one this system,
or any system reading public records, can answer.

The tempting move is to answer it anyway and hedge. There is a particular word for this,
beginning with c, that reads like caution and functions as a synonym: a feasibility
verdict in a coat. This project must never use it, and the lexicon rejects it in both
directions. A product that claims to monitor that quality gets read as a detector of
deliberate deception no matter what its limits file says, and at that point the
architecture is decoration.

So the system does not answer that question. It answers a narrower one that is genuinely
answerable and, in the cases that matter, gets to the same place.

Theranos is the useful example precisely because of what the tell was **not**. In real
time, no outsider could evaluate the microfluidics. Nobody was going to catch it by
assessing the chemistry. What was visible, publicly and continuously, was a decade of
claims that did not survive contact with their own prior versions: dates that moved,
validations that were promised and then not mentioned again, capabilities described one
way and later described another, with nothing in between reconciling the two.

That pattern is measurable. Feasibility is not. And the pattern was already public,
already timestamped, and nobody was diffing it.

The same is true of the case this project actually demonstrates. Rocket Pharmaceuticals
filed a protocol revision in April 2024 carrying a primary completion date of June 2022,
already expired for 677 days, on a federal registry, machine readable the entire time.
The system does not say that means the gene therapy will not work. It says the sponsor
carried an expired date for 677 days and nothing reconciled it, and it can prove both
halves of that sentence from named records.

## What follows from the principle

**A registry entry is not an observation.** It is a claim, made by an interested party,
that can be revised at any time, where every revision is public and timestamped, and
nobody diffs it. That sentence is the whole idea. ClinicalTrials.gov is one instance of
it.

**Structural pattern, never interpretation.** The system reports that a field was revised,
that a date passed without amendment, that a commitment changed shape. It does not report
what any of that implies about the technology, the people, or the future.

**Slip is only slip when the promise held its shape.** See `engine/promise.py`. Two dates
are only comparable if they describe the same commitment, and establishing that is a
harder problem than the subtraction. Where it cannot be established, the system returns
"requires human adjudication" and no number at all.

## Forbidden claims

Enforced, not documented. `orchestrator/lexicon.py` holds the list, Granite's output is
screened through it at runtime beside the number guard, and `tests/test_lexicon.py` scans
every rendered page and every claim-bearing document. A line that quotes a banned phrase
in order to forbid it carries an exemption marker, and a test checks that the marker only
ever appears on a line that is doing the forbidding.

### Feasibility

- That the technology, science, or platform works, or does not. Nothing here measures it.  [lexicon-exempt]
- That a timeline is reasonable, aggressive, or achievable.  [lexicon-exempt]
- Comparison to "comparable efforts" unless every comparator is itself a named, sourced
  record in the input.
- That a product is a wrapper, or that something will never ship.  [lexicon-exempt]

### Character and intent

- Fraud, deception, misleading, concealment. The system observes records, not motives.  [lexicon-exempt]
- Any named-fraud analogy used predictively.  [lexicon-exempt]
- That management is, or is not, worth believing. Banned in both directions, because the
  reassuring direction is the same claim.
- Any aggregate trust or risk score. A composite is a judgement laundered through  [lexicon-exempt]
  arithmetic, and it is worse than an opinion because it looks like a measurement.

### Causation and prediction

- Why a date moved. Slip has many causes: financing, enrolment, regulatory back and forth,
  honest rescoping. The registry records the move, never the reason.
- That an anomaly predicts an outcome, absent a preregistered out-of-sample validation.  [lexicon-exempt]
  No such study exists here.

### Silence and completeness

- That no amendment exists. Only that none was found in named sources, under a stated  [lexicon-exempt]
  procedure, at a stated time.
- That a company failed to disclose something, absent a specific cited duty.
- That all commitments are captured. Scope is bounded and `docs/LIMITS.md` says by what.  [lexicon-exempt]

### Arithmetic

- Any slip figure computed across records that describe different scopes, endpoints, or
  populations. This is the one the whole promise-identity module exists to prevent.
- Any displayed number not traceable to a named tag, registry version, or record.
- "Financing is required" as a bare conclusion rather than the output of a stated model.

### The ledger

- That it is immutable, or append-only. It is tamper evident, and only given the anchor  [lexicon-exempt]
  was not also rewritten.

## What the model may do

IBM Granite reads the analyst's written rationale and judges which stated assumption a
change breaks. That is a prose task and it is the right use of a model: it is the one step
in the pipeline that is genuinely semantic and genuinely not arithmetic.

It may not: produce a number, decide whether two records describe the same commitment,
decide materiality, supply a causal explanation, or rank anything. Those are deterministic
decisions or human ones. A model deciding "is this the same promise" is precisely the
judgement the number guard exists to exclude, relocated from the value to the match, and
it would be harder to catch there.

## The honest sales pitch

Not "we catch the next Theranos". That sentence is unearned, is forbidden here, and a judge will say so.  [lexicon-exempt]

What is earned:

> Every clinical-stage thesis rests on a date the sponsor sets, can revise at will, and
> nobody reconciles. The revisions are public, timestamped, and undiffed. This watches one
> written belief, detects when a revision contradicts it, drafts the challenge in the
> analyst's own words, and stops. A human decides.

Never ship a sentence that needs the words *works*, *credible*, or *reasonable* to  [lexicon-exempt]
describe what the product does.
