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

## Theme fit: intelligent systems for the future of work

The work being automated is not analysis. It is **noticing**.

An analyst can compute a funding gap in ten minutes. What no analyst does, across forty
positions, is re-read a registry every week to catch the one sponsor whose date moved, then
check whether that breaks something they wrote down in January. It is not a hard problem
solved badly, it is an easy problem nobody is assigned to. So the system watches a written
belief, detects when a change contradicts it, drafts the challenge in the analyst's own
vocabulary, and stops. The judgement stays human; the vigilance is what gets automated.

## How IBM Bob was used

Bob was the primary development tool. Twelve logged tasks, nine full session transcripts
committed to the repository at `docs/bob-sessions/`, 6.1 MB of them. Every row is backed:
nine transcripts cover twelve rows because three Bob sessions each produced two.

Bob built: the governance port (ledger, challenge, classifier, Granite client), the redline
loop, the entire console including all three views and the test suite, the snapshot
generator, the integrity-badge repair, the ledger anchor, the decision receipt, and the
research panel.

What preceded Bob and is not its work: the three verified engine modules in `engine/`, and
the spec, findings, demo script and prompt pack in `docs/`.

Bob was constrained rather than trusted. `.bob/custom_modes.yaml` puts a `fileRegex` on
edit permission so the three verified engine modules cannot be rewritten, and defines a
reviewer mode with no edit permission at all so a review cannot quietly fix what it is
judging.

`docs/BOB_LOG.md` records every task and separates build work from review passes. Other AI
tools were used for review, which the challenge permits.

Two changes after Bob's build was complete were written by hand with Claude Code, not by
Bob: the unresolved-ticker row on `/contracts`, and the thesis-break timeline, derivation
table and analyst belief form. Both are logged in `docs/BOB_LOG.md` at the same detail as
the Bob rows. The console's three original views, the snapshot generator and the test
suite are Bob's.

## What makes it credible

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
python3 -m pytest tests/ -q   # 39 passed, 1 skipped (40 passed with watsonx credentials)
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

- "Immutable" or "append-only" about the ledger. It is tamper evident, and deletion is
  detectable given the anchor was not also rewritten.
- "Readout date". It is a registered primary-completion expectation, and the two differ by
  two to four months, always optimistically.
- That cash-constrained sponsors revise dates differently. That is an open question this
  project deliberately does not answer.
- "No tool does this". A commercial screener covers the ranking layer and a judge will find
  it. The honest claim is the monitor.
