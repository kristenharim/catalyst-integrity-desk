# Status — 2026-07-21

Where the build stands and what a session with no prior context needs to know.
Read `HANDOFF.md` for the idea, `AGENTS.md` for the rules, this for the state.

## The submission

IBM AI Builders Challenge, Wildcard track. **Deadline Jul 31, 11:59pm EST.** The
Wildcard runs again with an Aug 31 cycle, so a second entry is possible.

Required, from the rules rather than the plan:

- A working prototype **using IBM Bob as the primary development tool**
- A README covering problem, solution, AI approach, theme, and **how Bob was used**
- A video, **maximum 3 minutes**
- A SkillsBuild learning activity completed

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
| 2 — governance port + redline loop | done, both transcripts in `docs/bob-sessions/` |
| 3 — console, sub-task 1 (snapshot generator) | **done and verified** |
| 3 — console, sub-tasks 2 to 6 (views, tests) | **next** |
| 3 — sub-task 7 (manual acceptance) | do by hand, costs nothing |
| 4 — the panel (Prompt 4) | **cut**, budget |
| 5 — README (Prompt 5) | **cut from Bob**, Claude writes it from `BOB_LOG.md` |

To continue: same or fresh Bob conversation, mode **Catalyst builder**,
"Implement sub-tasks 2 through 6 of docs/plans/console.md."

## The rule that outranks the rest

The demo opens on the Rocket revision timeline, not the contract list. The
677-day expired-date row is the only thing in this demo the room has not seen
before. It must be visible without scrolling and without a click, and marked
distinctly from ordinary revisions. `/` redirects to `/contract/RCKT` for exactly
this reason. If a layout decision would bury it, the layout loses.

## Budget, which is now the binding constraint

Bob is on a trial with a **$40 cap, roughly $10 left**. It is the mandatory tool,
so running dry before the console is filmable is the worst available outcome.

What that means in practice:

- Sub-tasks 2 to 6 are the last real Bob spend. Protect it.
- Reviews go to Claude, not Bob. Reviewing is not building.
- Sub-task 7 is manual and free.
- If it tightens: sub-tasks 2 to 5 are the demo, the tests in 6 are what to
  protect next, and everything else is already cut.
- Most of the last task's spend went on a rate limit episode, not on code. When
  something external is failing, stop Bob and diagnose it in Claude. Every Bob
  retry costs money; every Claude retry does not.

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

## Still open

- The confirm-page integrity badge, and a test for it
- Who the console is attributed to. `docs/BOB_LOG.md` names Claude Code for
  sub-tasks 1 through 6 and for Prompt 2, leaving one row attributed to Bob. But
  `docs/bob-sessions/phase2-redline-loop.json` is a genuine Bob task export whose
  title is Prompt 2 verbatim, so that row and its transcript disagree. The README
  is written from this log, the challenge requires Bob as the primary development
  tool, and the Bob budget is still unspent. Resolve the attribution before the
  README, not after.
- The contract list has only two rows: SANA has no live pivotal trial. Thin for a
  view about ranking, but the list is not the demo beat. Revisit only if cheap.
- The README, written from `docs/BOB_LOG.md` rather than from memory
- The 3 minute video, cut from `docs/DEMO.md`
- **The fourth kill gate is still untested**: say the Rocket fact out loud to a
  real person in twenty seconds and watch whether it lands. `SPEC.md` calls it the
  gate people skip and the one that decides the outcome. It costs nothing.
