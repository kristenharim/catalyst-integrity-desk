# Catalyst Integrity Desk

An auditable monitor for the moment a biotech investment thesis quietly stops being true.

In April 2024, Rocket Pharmaceuticals filed a protocol revision for trial `NCT04248439`
carrying a primary completion date of June 2022. **That date had already been expired for
677 days**, in public, on a federal registry, machine readable the entire time.

Nobody was watching, because nobody's job is to watch.

## The problem

Every clinical-stage biotech thesis rests on a date. The company has cash into month X,
the trial reads out before month X, therefore it is funded to its catalyst and does not
need to raise.

The left side of that sentence comes from SEC filings. The right side comes from
ClinicalTrials.gov, where **the sponsor sets the date, can revise it whenever it likes,
and nothing reconciles that revision against the thesis that depended on the old date.**

Every revision is public, timestamped, and undiffed. The analyst who wrote the thesis in
January is not re-reading the registry in April.

This project treats the thesis as a contract and audits both sides of it.

```
funding gap = runway exhaustion date - registered primary completion date
```

## Quickstart

No credentials, no API keys, no network. The demo runs from a committed snapshot.

```bash
pip install -r requirements.txt
python3 -m console.app            # http://localhost:8050
python3 -m pytest tests/ -q       # 13 tests
```

Run it as a module, from the repo root. Set `PORT` to move it off 8050.

The console opens on the Rocket revision timeline, because the 677-day row is the point.

`data/snapshot.json` is committed on purpose. It is the demo artifact, not a build
product, so anyone cloning this repo sees the same numbers without an IBM account. To
rebuild it against live SEC, registry and Granite APIs you need watsonx credentials in
`.env`, then `python3 console/make_snapshot.py`.

## The theme: intelligent systems for the future of work

The work being automated here is not analysis. It is **noticing**.

An analyst can compute a funding gap in ten minutes. What no analyst does, across forty
positions, is re-read a registry every week to catch the one sponsor that moved a date by
fourteen months, then check whether that breaks something they wrote down in January. The
failure is not a hard problem solved badly. It is an easy problem nobody is assigned to.

So the system watches a written belief, detects when a change contradicts it, drafts the
challenge in the analyst's own vocabulary, and stops. A human accepts or rejects, and the
decision hash-chains into a tamper-evident ledger. The judgement stays human. The
vigilance is what gets automated.

## The AI approach

**Python computes. Granite judges prose. Humans decide.**

IBM Granite on watsonx never produces a number. It reads the analyst's written rationale
alongside the recomputed contract and reports which stated assumption a change breaks, and
how badly. Every figure on screen comes from Python arithmetic over filed data.

That rule is enforced rather than asserted. `_fabricated()` scans model output for any
figure absent from its input and falls back to a deterministic stub if it finds one. The
guard deliberately does not ban all digits: quoting a number from the belief's own claim
text is quotation, not invention. The rule is "a number absent from the input".

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
was written as the work happened, and every Bob row is backed by a full task export in
`docs/bob-sessions/`.

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

Other AI tools were used for review, which the challenge permits. They wrote no product
code, and `docs/BOB_LOG.md` records those passes separately from the build.

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
  precise way an earlier version of it lied. With credentials the suite is 14
  passed; without them that one test skips and you see 13 passed, 1 skipped.
- The number-provenance test asserts that every figure in the rendered HTML appears
  verbatim in the snapshot. It was confirmed by planting a `9999` in a template and
  watching the test name that token.
- The ledger badge test was written before its fix, and watched to fail.
- Each console check was re-broken afterwards: the marker class renamed, `stub` forced
  into the memo, `days_expired` changed from 677 to 123. All four failed as they should.

One honest limit. The provenance check matches by substring, so a format that truncates a
full-precision value passes for free. It catches planted literals and computed values,
which is what it is for. It is not proof that no template formats anything.

## What it found

**Rocket Pharmaceuticals, `NCT04248439`:** a completion date revised in April 2024 that
had already been expired for 677 days. Four revisions, 1,008 days of net slip.

**Mirati, `NCT04613596`:** 95 protocol versions, 6 of which moved the completion date,
2,193 days of net slip, including a +1,317 day move reversed two months later.

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

The system says **registered primary-completion expectation**, never "readout date". They
differ systematically by two to four months, and the gap is always optimistic.

## Layout

```
engine/runway.py          cash runway from SEC XBRL company facts, as a band
engine/ctgov_history.py   registry revision history, notice and expiry metrics
engine/gap.py             the catalyst contract join
engine/ledger.py          hash-chained belief ledger
orchestrator/             redline loop, challenge builder, Granite client
console/                  Flask console, three views, snapshot generator
tests/                    13 tests, no network, no credentials
data/snapshot.json        the frozen demo artifact
docs/BOB_LOG.md           what Bob built versus what preceded it
docs/bob-sessions/        full Bob task exports, the evidence behind that log
docs/FINDINGS.md          eight data gotchas, prior art, attack surface
docs/DEMO.md              three minute script
```

Read `docs/FINDINGS.md` before writing extraction code. Each gotcha in it produces a wrong
number rather than an error, and one of them caused a 49x error that looked exactly like a
company about to run out of money.
