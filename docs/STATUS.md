# Status — 2026-07-22

Where the build stands and what a session with no prior context needs to know.
Read `HANDOFF.md` for the idea, `AGENTS.md` for the rules, this for the state.

## The submission

IBM AI Builders Challenge, Wildcard track. **Deadline Jul 31, 11:59pm EST.** The
Wildcard runs again with an Aug 31 cycle, so a second entry is possible.

Required, taken from the official FAQ rather than the plan:

- A published Project Page with all sections marked complete
- A working prototype **using IBM Bob as the primary development tool**
- A **public GitHub repository** with a README
- A public demo video, **maximum 3 minutes**
- A SkillsBuild completion certificate, uploaded. It must be one of exactly two
  activities: "How IBM Bob and AI Tools Are Changing the Way Solutions Are Built"
  or "Lab: Troubleshoot Your Code Using IBM Bob"

Other AI tools are explicitly allowed. FAQ question 7: "You may use additional AI
tools during development. However, IBM Bob must be your primary development tool."
So the review passes in `BOB_LOG.md` are permitted and worth keeping honest, not a
liability to be scrubbed.

Judged on Technical Execution, Innovation, Feasibility, Challenge Fit, Real-World
Impact.

## Why this project and not the other one

`~/projects/deliberate-risk-desk` is a complete, working, Granite-live system with
46 checks and its own Bob transcripts. It was the July candidate until 2026-07-21.

It lost on the hook. Its finding is that a book can drop thirteen percent while
every risk measure improves and nothing pages anyone. That is intellectually the
better result and it needs a paragraph of setup, and its naive reading is "your
system missed a loss". The person who read it that way first was the person who
built it.

This project's hook needs nothing: a company published a completion date that had
already passed six hundred and seventy seven days earlier, and it sat on a public
registry the entire time. In a three minute video judged by non specialists, that
difference decides it.

The risk desk is **frozen as the fallback and the port source**. Do not build in
it. Its governance layer is what `orchestrator/` here was copied from.

## Where the build is

| phase | state |
|---|---|
| 1 — engine (`runway`, `ctgov_history`, `gap`) | done, verified against live SEC and registry data, **do not rewrite** |
| 2 — governance port + redline loop | done, both Bob transcripts filed |
| 3 — console, all sub-tasks | done, Bob built it, transcript filed |
| 3 — repair, the integrity badge | done, verified by mutation and in a browser |
| 4 — the panel (Prompt 4) | **cut**, budget |
| 5 — README (Prompt 5) | **next**, Claude writes it from `BOB_LOG.md` |

The code is finished. What is left is the submission: the README, a public GitHub
repo, the Project Page, the video, and the SkillsBuild certificate.

## The rule that outranks the rest

The demo opens on the Rocket revision timeline, not the contract list. The
677-day expired-date row is the only thing in this demo the room has not seen
before. It must be visible without scrolling and without a click, and marked
distinctly from ordinary revisions. `/` redirects to `/contract/RCKT` for exactly
this reason. If a layout decision would bury it, the layout loses.

## Budget, and what happened to the first trial

The first trial hit its 40 Bobcoin cap partway into the badge repair, after Bob had
read the files and before it wrote anything. That spend bought nothing.

The sanctioned fix, from FAQ question 8 and confirmed by a BeMyApp moderator, is
that IBM does not extend or reset trials: you create a new Bob trial account on a
different email and sign out of the old one in the app. Done on 2026-07-21, and the
repair was built on the new trial with 40 fresh Bobcoins and 30 days.

What that cost us is the old account's task history, which does not follow you.
That is survivable only because the transcripts were already exported into
`docs/bob-sessions/` and committed. **Export a Bob task the moment it finishes, not
later.** A trial can die between the work and the export, and the export is the
evidence the submission rests on.

Standing habits worth keeping:

- Reviews go to Claude, not Bob. Reviewing is not building, and the FAQ allows it.
- When something external is failing, stop Bob and diagnose it in Claude. Every Bob
  retry costs money; every Claude retry does not. Most of one task's spend went on
  a rate limit episode rather than on code.

## watsonx rate limits

The free tier returns `429 consumption_limit_reached` when the shared concurrent
pool for a model is full. It is congestion across all free tier users, not a
quota, and it clears on its own. `granite-3-8b-instruct` gives
`rate_limit_reached_requests` instead; the 3.x variants are `model_not_supported`
on this plan.

This is why the demo runs from a frozen snapshot. `data/snapshot.json` is
committed on purpose: it is the demo artifact, not a build product, and a judge
cloning this repo must be able to run the console with no credentials and no live
API. Never regenerate it during a demo. `data/decisions.jsonl` stays gitignored,
because that is live state written on camera.

## The defect pattern, across both projects

Every real defect found so far has the same shape: **everything stays green.**

- A test assertion narrowed around a bug the author had already noticed in a comment
- A belief that never fired because seeding only ran on an empty ledger
- A cache check that passed with the cache deleted, because the model is deterministic
- A live Granite test that passed without reaching Granite, because the stub fallback
  answered and stubs do not fabricate
- A function imported into its own test and never called
- `carried_expired` dropped from the snapshot because it is a property and
  `dataclasses.asdict` serialises fields only. Granite answered, the source was
  right, the memo was right, and the demo centrepiece simply was not in the file

None of these announced themselves. The question worth asking of any new check is
**what would still pass if this were broken**, and the answer has to be found by
breaking it, not by reasoning about it.

Working method: Bob builds, Claude verifies by mutation. Break the thing the check
claims to protect and confirm the check fails. Three checks this session looked
correct and were hollow until mutated.

## Bob, calibrated

Implements well, self-verifies poorly. It has caught subtle traps unprompted and
matched the house style closely. It has also written a test narrowed around a bug
it had already noted in a comment, and written two tests that could not fail.

Told precisely where it is wrong, it has four times now diagnosed why its own
approach was mistaken rather than patching the symptom, and twice produced a
better fix than the one asked for. It responds well to being corrected and badly
to being trusted.

`.bob/custom_modes.yaml` enforces the boundaries:

- **Catalyst builder** — cannot edit the three engine modules. That `fileRegex` is
  why "do not rewrite the engine" is a fact rather than a hope. Note it constrains
  the edit tool, not the shell: Bob has routed around it with shell commands for
  benign files.
- **Catalyst reviewer** — no edit permission at all, so a review cannot quietly fix
  what it is judging.

Settings that matter: **Mode auto-approve off**, or Bob switches itself into
unrestricted Agent mode and the boundary above becomes voluntary. **Respect
.gitignore on**, so Bob cannot read `.env` and credentials never enter a
transcript.

## Commands

```bash
cd ~/projects/catalyst-integrity-desk
set -a; . ./.env; set +a          # credentials, required for anything live

python3 -m engine.runway          # all three must pass before and after any change
python3 -m engine.ctgov_history
python3 -m engine.gap
python3 -m engine.contract

python3 -m pytest tests/ -q
python3 console/make_snapshot.py  # only when Granite is clear; asserts the 677 row
```

Scan every Bob transcript before committing it:

```bash
grep -oE '(WATSONX_[A-Z_]+)=[^.<"\ ]{6,}' docs/bob-sessions/*.json
```

Anything other than a `WATSONX_URL` pointing at a public region is a real
credential and must not be committed.

## Verification of sub-tasks 2 to 6, 2026-07-21

The console was built while a Claude session was open alongside it. Nine tests
pass. Green proves nothing here, so each check was broken to see whether it
screams. All four caught it: a planted `9999` in the detail template, the
carried-expired class renamed, the word `stub` put into the memo, and
`days_expired` changed from 677 to 123. Every display string in the snapshot
recomputes from its own source value, so none was typed by hand.

The snapshot diff is purely additive. The Granite redline block is byte for byte
what the live classification produced, so nothing was regenerated and no watsonx
call was spent.

The demo constraint holds. `/` lands on the Rocket timeline, and at 1280x800 the
677-day node sits red and raised off the axis with the whole gap table below it,
no scrolling. Every page rendered with no credentials in the shell, which is the
network-disabled criterion proved rather than asserted.

**One defect, and it is the demo's own beat.** `GET /redline/confirm` reads the
integrity badge from `?intact=1` in the URL, set once at decision time. Tamper the
ledger and reload, which is exactly what the page instructs, and the badge still
reads intact. Measured: `BeliefLedger.verify()` returns `False` on disk while the
page returns `✓ intact`. The ledger itself is sound, verified separately against a
tampered hashed byte. The fix is for the confirm handler to open the ledger and
call `verify()` itself. No test covers this, because sub-task 6 never asked for
one, so a test belongs with the fix.

Three smaller ones. `/redline` is absent from the provenance test's route list and
`redline.html` still formats numbers with `%.1f` in the template; it passes today
only because those digits happen to appear in the file. Dollars render to whole
millions, so cash shows `$50M` against a 10-Q reading 49.61. `app.run(port=5000)`
collides with macOS ControlCenter on this machine and will not bind on demo day.

## The badge repair, verified 2026-07-21

Bob's fix is right and its test is real. Reverting the handler to the query-string
version fails the new test, and so does hardcoding `verify()` to `True`, so the
check is anchored to the behaviour and not to the shape of the code. The four
original console mutations still fail as they should, so nothing regressed.
`--displays` is byte-identical across two runs and needed no credentials. The
Granite redline block was not regenerated. All four engine gates pass. 13 tests.

Confirmed end to end in a browser, which is the only version that matters here:
accept the redline, edit one byte of `data/decisions.jsonl`, reload the same URL,
and the badge goes from green `✓ intact` to red `✗ tampered`.

Two things to know rather than fix:

The provenance check detects unintended displayed literals. It does not prove every
rendered value is correctly formatted, and it should never be described as though it
does. It matches by substring, so `"%.3f"` of `-0.5913757700205339` renders `-0.591`,
a literal prefix of the stored value, and passes. It walks text nodes only, so
attribute values such as SVG coordinates and stroke widths are never examined. Both
exclusions are deliberate. Within them it catches a number that entered the page from
somewhere other than the snapshot, which is the job.

The app now reads `PORT` and defaults to 8050, because 5000 is held by macOS
ControlCenter.

Correction, found afterwards: I claimed in the same breath that `python3
console/app.py` works again. It does not, and never has. That file imports
`engine.ledger` but has no `sys.path` guard, unlike `make_snapshot.py` and
`tests/test_console.py`, which both insert the repo root. Run as a file, `console/`
is `sys.path[0]` and the import fails. Every check missed it because the tests and
the preview launcher both insert the root themselves, so nothing ever exercised the
documented command. Same defect pattern as everything else here: the check did not
touch the path it claimed to cover. `python3 -m console.app` works today and is what
the README now says.

## The real breach, verified 2026-07-21

The scripted amendment is gone. `/redline` now shows an event that actually happened:
the thesis was approved against `NCT04248439` at 2026-05-05 for +8.4 months funded, that
date passed, the binding catalyst became `NCT06092034` at 2028-04, and the same runway
gives -14.5. The centre column says it plainly: **no amendment was filed, the registered
completion date passed.** That is the strongest sentence in the project, and it removes
the last invented element.

Verified internally consistent: `breach.observed` is -14.5 against a `[0.0, 10.4]` band
anchored to the approved thesis, and Granite's memo quotes the same two figures. No
scripted leftovers. Classification is live Granite. 17 tests, four engine gates, tamper
demo still flips on reload, 677 row still above the fold.

**An untested gap, found by mutation and still open.** Display strings can drift from the
values they claim to render and nothing catches it. Setting `prior_gap_months` to 99.9
while the page kept showing 8.4 left all 17 tests green, as did setting `runway.cash` to
1.0 while the page kept showing $50M. The provenance test proves a rendered number came
from the snapshot; it does not prove the string is a faithful rendering of the field it
labels. That was checked by hand, twice, and a hand check rots. The fix is a test that
recomputes every display string from its source and asserts equality.

Cosmetic leftover: one literal `--` remains in the consequence sentence prose on the
detail page.

## The live Granite test, verified 2026-07-21

With `.env` sourced the suite is **14 passed, no skips**, including
`test_no_fabrication_live`. That test is not hollow: pointed at an invalid
`WATSONX_URL` it fails on the `source == "granite"` assertion, with the stub
fallback visible in stderr. So a pass means the call actually reached Granite,
which is the exact failure this project already hit once and fixed.

Run it that way before filming:

```bash
set -a; . ./.env; set +a; python3 -m pytest tests/ -q
```

Without credentials it skips, and a judge running `pytest` cold sees 13 passed
and 1 skipped. That is correct behaviour, not a defect, but the README should not
lean on a check the reader watches skip.

## Attribution, resolved 2026-07-21

Bob built the console. One Bob session did sub-task 1 and sub-tasks 2 to 6 in a
single run past its stopping point: `make_snapshot.py`, `app.py`, all five
templates, `test_console.py`, `requirements.txt`.

`docs/BOB_LOG.md` had said Claude Code for that work and for the redline loop.
Bob writes its own log row and was naming the wrong tool. The correct split is
now three Bob rows plus the governance port, against one genuine Claude row for
verification and gate checks. `AGENTS.md` now states what Bob is called, which is
where the fix belongs, since correcting rows afterwards does not stop the next one.

That leaves the console defensibly Bob's, which is the requirement with no partial
credit. Export the two console sessions into `docs/bob-sessions/` and the two
`pending export` rows become real. Scan them first:

```bash
grep -oE '(WATSONX_[A-Z_]+)=[^.<"\ ]{6,}' docs/bob-sessions/*.json
```

## The cohort study, closed 2026-07-22

The random cohort is finished and frozen. Every drawn trial is measured and none failed.

<!-- generated: provenance -->
Every cohort figure in the claim documents is emitted from a field of snapshot
`cohort-5b03269658b8` by `research/render_writeup.py`: 240 trials, 60 in each of four
sponsor strata, all measured, point prevalence as of 2026-07-22. The prose around them
contains no numerals and a test regenerates every generated block and fails on a one-byte
difference.
<!-- /generated -->

`docs/WRITEUP.md` is the publishable write-up and is itself generated;
`docs/COHORT.md` is the working record with the full correction history.

What closing it required, in case any of it recurs:

- **The first amendment to a protected engine module**, under
  `docs/AMENDING_PROTECTED_MODULES.md`, which had never been invoked. The `_cached()`
  non-atomic write is fixed at the source. The condition that did the work was the
  before-and-after gate diff: it is the only one of the four that cannot be satisfied by
  reading the diff and feeling confident.
- **The store compacted**, one row per trial, superseded rows archived rather than deleted.
  A test now fails if any shipped module reads the store around `load_results()`.
- **A rule that was written down and violated in code.** The report printed a pooled
  all-strata section on every run, for as long as the rule against pooling had existed.
  Same lesson as everything else in this file: prose does not enforce anything.

- **An adversarial council found what the study could not find about itself.** Three seats
  blocked the write-up. Two objections were measurement defects, not wording: the stretch
  measure needs a later filing to close a lapse, so it cannot see a sponsor that goes quiet,
  and a stretch is counted per filing rather than per lapse, so duration tracked filing
  frequency. Both were resolved by the owner and the study re-measured.
- **A wrong figure of my own, published for one revision and retracted.** The first point
  prevalence read the ESTIMATED/ACTUAL type from a helper that did not return it, so the
  filter never fired and every completed trial that had correctly recorded its completion
  date counted as carrying a lapsed one. It read an order of magnitude high for industry,
  and the corrected figures are in `docs/WRITEUP.md`.
  The defect pattern this file has documented six times over, committed again: a check that
  silently does not apply looks exactly like a check that passes, and this one was in the
  flattering direction.

**Where the study now stands, after seven council rounds.** The headline is the
registry-level result:

<!-- generated: headline -->
In a random sample of 240 phase 2 / 2-3 / 3 trials, **this study cannot separate
reconciliation from filing frequency, and most trials carrying an expired commitment have
never reconciled a lapsed date** — 4 of 5 in INDUSTRY, 20 of 27 in OTHER_GOV, 15 of 19 in
OTHER, dates that have stood a median of 1,101.5 days in INDUSTRY, 2,288.5 days in
OTHER_GOV, 1,178 days in OTHER. NIH sponsors file a median of 106.5 registry versions per
trial and have **zero** trials currently carrying an expired completion date. Government
sponsors outside NIH file a median of 2, and **27 of 29 of their still-open commitments have
already expired**. The ordering is monotone in filing frequency across all four strata,
which is an association across four points rather than a tested relationship.
<!-- /generated -->

<!-- generated: mechanism -->
The supporting mechanism, among sponsors still filing: **26.2% of industry completion-date
revisions replace an estimate that had already expired** (33 of 126), and 24 of 52 (46.2%)
industry trials that revised a date at all did it at least once. That is narrower than
running late, which is well documented, and narrower than the raw after-lapse count, because
a revision recording an *actual* completion is the update the regulation requires rather
than a failure to file it.

Industry point prevalence is 8.3% of all trials, and 33.3% of those whose commitment is
still open. The anchor case's 677 days sits at the **85th percentile** of 188 such
stretches: long, but not the tail.
<!-- /generated -->

A draft published the undivided after-lapse rate for that mechanism, which counted the
mandated update-to-actual filing as a failure to reconcile; it is retracted in the write-up's
correction log.

<!-- generated: primary_measures -->
Primary frequency is point prevalence, 8.3% of all industry trials and 33.3% of those whose
commitment is still open. Primary duration is per-trial longest carry, NIH 590 days against
industry 390, a ratio of 1.5x, and every duration here is measured on completed spells only.
The stretch-based figures are a labelled secondary and cannot see a sponsor that stops
filing. **No all-strata average exists anywhere**, and the no-pooling rule rests on three
differences rather than on one ratio.
<!-- /generated -->

**No all-strata average exists
anywhere**, and the no-pooling rule now rests on three differences rather than one ratio.

## Still open

- ~~The breach-moment Bob task has no transcript.~~ Closed 2026-07-21. All twelve rows
  are backed by nine transcripts, three sessions having produced two rows each. Two
  things were learned doing it. Exports were twice re-runs of an already-committed task,
  caught by hashing the payload with `exportedAt` stripped rather than trusting the
  filename, so check that before filing a new one. And the export that finally arrived
  was not the missing row at all: it was the console planning pass, a real Bob task with
  no row in the log, which is now logged. The breach-moment work turned out to live
  inside `phase3-real-breach.json`, attributed on artifact evidence: `_cmd_bar`,
  `lapsed_history`, `Integrity memo` and `test_snapshot_no_lapsed_catalyst` all appear
  there at their highest counts, alongside 23 write operations, and the two later
  sessions treat those artifacts as already existing.
- ~~**Publish the repo on GitHub.**~~ Done 2026-07-22, public at
  https://github.com/kristenharim/catalyst-integrity-desk. Full history, 58 commits,
  not a squashed snapshot. Re-scanned before pushing: `.env` never committed on any
  branch, no key literals in tracked files or in the Bob transcripts. The initial push
  needed `http.postBuffer` raised against the 5.2 MB payload, set in this repo's local
  config only. Note that commits carry three author emails, one of them the placeholder
  `kristenharim@example.com`, so those show as unattributed on GitHub. Cosmetic, and
  fixing it means rewriting every hash.
- ~~The SkillsBuild certificate.~~ Obtained 2026-07-21. Still has to be *uploaded* with
  the submission, so it is not done until it is attached to the Project Page.
- The Project Page on the platform, all sections marked complete.
- The 3 minute video, cut from `docs/DEMO.md`
- **The fourth kill gate is still untested**: say the Rocket fact out loud to a
  real person in twenty seconds and watch whether it lands. `SPEC.md` calls it the
  gate people skip and the one that decides the outcome. It costs nothing.
