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

An auditable monitor for the moment a biotech investment thesis quietly stops being true.

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

In April 2024, Rocket Pharmaceuticals filed a protocol revision carrying a primary
completion date of June 2022. That date had already been expired for 677 days, in public,
on a federal registry, machine-readable the whole time. No press release, no 8-K, and
nothing in the thesis that depended on it moved.

Then that date passed too. A thesis anchored to it read plus 8.4 months, funded to
catalyst. The nearest registered completion still in the future puts the same company at
minus 14.5 months, financing required. Nobody filed an amendment. The date simply arrived,
and passed.

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
value, so it has nothing to echo and nothing to do arithmetic on. `_fabricated()` scans
model output for any figure absent from its input and discards the response in favour of a
deterministic stub if it finds one. That guard is tested against live Granite, and the test
is itself checked by pointing it at an invalid endpoint, where it fails rather than
silently passing on the stub.

Two supporting rules: every displayed number names the XBRL tag or registry version it came
from, and a lapsed completion date is never treated as a catalyst, because you cannot run
out of money before an event that already happened.

## What it found in its own numbers

The most useful result this project produced is a correction to itself.

`total_slip_days` subtracts registered completion dates across successive registry
versions. That is a delay only if both dates describe the same commitment, and nothing
checked. `engine/promise.py` now classifies every revision and refuses to state a movement
it cannot establish. Five of the seven trials in the snapshot turn out to have been
reporting figures the record does not support.

The clearest case: `NCT04248439` reported 1,008 days. A single +1,430-day revision
coincided with the primary endpoint changing from phenotypic correction of bone marrow
colony forming units to Mitomycin-C resistance of bone marrow colony-forming cells.
Different endpoint, different promise, not a delay. The supported figure is -422 days
across the two revisions where the commitment held its shape.

Unaffected, and stated so the finding is not read as bigger than it is: the 677-day
expired-date result is one version carrying an already-passed date, not a comparison
across two commitments. So is the funding gap. `docs/LIMITS.md` has the table.

## Theme fit: intelligent systems for the future of work

The work being automated is not analysis. It is **noticing**.

An analyst can compute a funding gap in ten minutes. What no analyst does, across forty
positions, is re-read a registry every week to catch the one sponsor whose date moved, then
check whether that breaks something they wrote down in January. It is not a hard problem
solved badly, it is an easy problem nobody is assigned to. So the system watches a written
belief, detects when a change contradicts it, drafts the challenge in the analyst's own
vocabulary, and stops. The judgement stays human; the vigilance is what gets automated.

## How IBM Bob was used

Bob was the primary development tool and built the working system. Eleven logged tasks,
nine full session transcripts committed at `docs/bob-sessions/`.

Bob built: the governance port (ledger, challenge, classifier, Granite client), the redline
loop, the entire original console including all three views and the test suite, the
snapshot generator, the integrity-badge repair, the ledger anchor, the decision receipt,
and the research panel.

What preceded Bob: the three verified engine modules in `engine/`, and the spec, findings,
demo script and prompt pack in `docs/`.

Bob was constrained rather than trusted. `.bob/custom_modes.yaml` puts a `fileRegex` on
edit permission so the three verified engine modules cannot be rewritten, and defines a
reviewer mode with no edit permission at all so a review cannot quietly fix what it is
judging.

Work after Bob's build was done by hand with Claude Code, logged in `docs/BOB_LOG.md` at
the same detail as the Bob rows: the unresolved-ticker row, the thesis-break timeline, the
derivation table, the belief form, the monitoring queue, and the pass that added the
evidence seam, promise identity, the enforced claims lexicon and workspace mode. Bob built
the thing that works; what came after is largely the project auditing itself, which is what
produced the correction to its own slip figures.

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
is weaker than it looks. Nothing in this project claims more than it can show.

## Tech stack

Python 3, Flask, matplotlib. IBM Granite on watsonx.ai for classification and memo drafting.
SEC XBRL company-facts API and the ClinicalTrials.gov v2 API with full version history. No
build step, no external CSS or JS, no network access at render time.

## How to run it

```bash
pip install -r requirements.txt
python3 -m console.app        # http://localhost:8050
python3 -m pytest tests/ -q   # 133 passed, 1 skipped (134 passed with watsonx credentials)
```

No credentials and no network. The console renders entirely from a committed snapshot, so a
judge can clone and run it with no IBM account.

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
- A net-slip figure without saying how many revisions were not comparable. Five of seven  [lexicon-exempt]
  trials in the snapshot report totals the record does not support.  [lexicon-exempt]
- "No tool does this". A commercial screener covers the ranking layer and a judge will find
  it. The honest claim is the monitor.
