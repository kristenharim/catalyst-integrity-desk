# Bob prompt pack

Sequenced. Run them in order, one per working session, and check the acceptance criteria
before moving on. Each prompt is written to be pasted whole.

Why this shape: the challenge requires IBM Bob as the primary development tool and a
README section describing that use. So Bob must do genuinely substantial work, and the
work must be describable honestly. These prompts hand Bob bounded, verifiable builds
rather than "improve the codebase", because a bounded build produces a reviewable diff
and a vague one produces churn.

**Export the session transcripts.** They are the evidence for the README section.

---

## Prompt 1: port the governance layer

> Read `docs/PORT.md` in this repo, then copy the four listed modules from
> `~/projects/deliberate-risk-desk` into this project, preserving their structure.
>
> Do not modify `~/projects/deliberate-risk-desk` in any way. It is a working fallback.
>
> Change only what `docs/PORT.md` says to change: comments in `ledger.py`, and the two
> prompt strings in `granite.py`. Keep `_fabricated()` byte for byte, including its
> rule that fabrication means a number absent from the input rather than any digit at
> all.
>
> Then write `engine/contract.py` that turns a `CatalystContract` from `engine/gap.py`
> into the flat `{metric_id: value}` dict that `scan_breaches` consumes. Include a
> `demo()` with asserts, matching the style of the three existing engine modules.

**Accept when:** all four original demos still pass, `python3 -m engine.contract` passes,
and a contract packet round trips through `scan_breaches` producing a breach on a
deliberately out of range gap.

---

## Prompt 2: the redline loop

> Build `orchestrator/redline.py`. Given a `CatalystContract` recomputed after a change,
> and the previously approved version of the same contract, produce a `ChallengeCard`
> using the ported `build_challenge`.
>
> Critical constraint: Granite receives the contract's rationale text and a description
> of what moved **in directions, not values** ("the funding gap falls sharply", never
> "the gap fell 9.2 months"). The application renders every figure. Read
> `as_directions()` in `~/projects/deliberate-risk-desk/engine/scenario.py` for the
> pattern, then implement the equivalent here.
>
> Write a test that feeds Granite a breach and asserts no figure appears in its output
> that was not in its input.

**Accept when:** the fabrication test passes against live Granite, and a scripted
amendment produces a challenge card with a classification and a drafted memo.

---

## Prompt 3: the console

> Build a web console over the existing engine. Three views only:
>
> 1. Contract list, ranked by funding gap. Flagged rows visible but visually separated
>    and unranked, with the flag reason shown.
> 2. Contract detail: the gap calculation with every input labeled by its source tag or
>    registry version, plus the trial's date revision timeline as a horizontal chart.
>    Mark any revision where the sponsor carried an already expired date.
> 3. Pending redline: the challenge card, Granite's classification and memo, and
>    accept / edit / reject controls.
>
> Server side rendering with a small framework, no build step if avoidable. Read from a
> local JSON snapshot, never a live API call during rendering. Every number displayed
> must come from the engine, never recomputed in the view layer.

**Accept when:** all three views render from a frozen snapshot with the network
disabled, and the ledger tamper demo is visible in the UI.

### Prompt 3, continuation: sub-tasks 2 to 6

Sub-task 1 is built and verified. This is the rest of Prompt 3, and it is the last
substantial Bob spend on this project, so it is one conversation and not five.

> Read `docs/plans/console.md`, then implement the Sub-task 1 addendum and sub-tasks
> 2 through 6 in that order. Sub-task 1 itself is done: `data/snapshot.json` exists,
> was built against live Granite, and must not be regenerated. The addendum adds
> display strings to it without any network call.
>
> Four things decide whether this is right:
>
> Do the addendum first. Sub-task 6's number-provenance test cannot pass until the
> rounded strings a reader sees are in the snapshot, and discovering that at sub-task
> 6 costs a rewrite of every template.
>
> No template formats a number. Every figure prints a `display.*` string. If you
> reach for `round()` or a Jinja number filter in a template, the snapshot is missing
> a field and that is where the fix goes.
>
> `/` opens on the Rocket revision timeline and the 677-day carried-expired node is
> visible without scrolling and marked distinctly from ordinary revisions. If a
> layout choice would bury it, the layout loses.
>
> Sub-task 6 step 8 is not optional and not a formality: hardcode a `9999` into the
> detail template, watch the provenance test fail and name that token, then remove
> it. Three checks on this project have looked correct and been hollow. A check
> nobody has seen fail is not evidence.
>
> Do not regenerate `data/snapshot.json`, do not call watsonx, and do not edit
> anything in `engine/`.

**Accept when:** `pytest tests/test_console.py` passes, the provenance test has been
seen failing on a planted token, `make_snapshot.py --displays` is idempotent, and
`/` lands on the timeline with the 677 row above the fold.

### Prompt 3, repair: the integrity badge

Verification of sub-tasks 2 to 6 found one defect and three smaller ones. The defect
is the tamper demo itself. Nothing in this task calls watsonx, so the rate-limit
episode that ate the last budget cannot repeat here.

Items are in priority order. If anything goes wrong, stopping after item 2 still
leaves the demo intact.

> Read the verification section of `docs/STATUS.md` first.
>
> **1. The integrity badge is decorative.** `GET /redline/confirm` reads `intact`
> from the query string, set once at decision time by the POST handler. Tamper the
> ledger and reload, which is exactly what the page instructs, and the badge still
> reads intact. Measured: `BeliefLedger.verify()` returns `False` on disk while the
> page returns `✓ intact`. The confirm handler must open the ledger and call
> `verify()` itself, at render time.
>
> Write the test before the fix and watch it fail. It must POST a decision, tamper a
> byte the hash actually covers, and assert the badge flips. Note that the verdict
> word lives in `data/review_log.jsonl`, not the ledger, so editing `approve` changes
> nothing hashed and `verify()` stays `True`. That was a real false negative during
> verification. Change something inside the `card` payload instead.
>
> **2. The app cannot bind its port.** `app.run(port=5000)` collides with macOS
> ControlCenter, so `python3 console/app.py` fails to start on the demo machine. Read
> the port from the `PORT` environment variable, defaulting to something free.
>
> **3. Add a `--displays` flag to `make_snapshot.py`.** Display strings are currently
> produced inside `_serialise_runway` and `_serialise_contract`, so the only way to
> change a display format is a full rebuild, and a full rebuild needs Granite. Extract
> the formatting into a function that takes a loaded snapshot dict and adds the display
> fields, call it from both the build path and a new `--displays` flag that loads
> `data/snapshot.json`, applies it, and writes it back. No credential check on that
> path, it needs none. Running it twice must leave the file byte-identical.
>
> **4. Close the provenance gap.** `redline.html` still formats numbers in the template
> with `%.1f`, and `/redline` is missing from the provenance test's route list. It
> passes today only because those digits happen to appear in the snapshot. Give the
> breach its display strings, render those, add `/redline` to the parametrize, and
> refresh the file with `--displays`.
>
> Do not regenerate `data/snapshot.json`, do not call watsonx, do not edit `engine/`.

**Accept when:** the badge test fails before the fix and passes after, `pytest tests/`
is green, `--displays` is idempotent, and `/redline` is in the provenance parametrize.

### Prompt 3, hardening: the documented entry point

Small and optional. `python3 -m console.app` already works, so this is robustness for
someone who types the file path instead, plus the check that would have caught it.

> `python3 console/app.py` fails with `ModuleNotFoundError: No module named 'engine'`.
> Run as a file, `console/` becomes `sys.path[0]` and the repo root is not importable.
> `console/make_snapshot.py` and `tests/test_console.py` both already solve this the
> same way, with a `sys.path.insert` of the parent directory. Do it the way they do
> it rather than inventing a second pattern.
>
> Then write the check that would have caught this, in `tests/test_console.py`. It has
> to launch the documented command in a subprocess, not import the app: every existing
> test inserts the repo root itself, which is exactly why this survived. Spawn
> `[sys.executable, "console/app.py"]` from the repo root with `PORT` set to a free
> port, poll until it answers or time out, assert `GET /` returns 302, then terminate
> it. Watch it fail before you add the `sys.path` line.

**Accept when:** `python3 console/app.py` serves, `python3 -m console.app` still serves,
the new test fails without the fix, and `pytest tests/` is green.

### Prompt 3, widening: a real ranked list and a real flagged row

The console demonstrates two invariants it cannot currently show. The contract list has
two rows, so "ranked" is not visible. And no row anywhere is flagged, so "unreliable rows
are shown, never ranked, never silently dropped" is a claim with no example, even though
it appears in `AGENTS.md`, the README, the definition of done, and `DEMO.md` tells the
presenter to point at the flagged rows on camera.

Candidates were checked before writing this, so do not go hunting. `SRPT` builds a real
contract and comes back `reliable=False` with the note "cash-positive operating quarter(s)
in TTM window ... likely a one-time inflow". `BEAM` builds clean with a gap near 20 months.
`ARWR`, `ALNY`, `NTLA` and `DYN` have no live pivotal trial and `build()` returns None for
them, which is correct behaviour, not a bug to work around.

> **1.** Widen `TICKERS` in `console/make_snapshot.py` to
> `["SANA", "PRME", "RCKT", "BEAM", "SRPT"]`. SANA still drops out with no live pivotal
> trial and that is expected.
>
> **2.** Rebuild the snapshot. This one **does** call Granite, so source `.env` first and
> expect the retry-with-backoff path to earn its keep:
> `set -a; . ./.env; set +a; python3 console/make_snapshot.py`. The generator already
> asserts the 677-day row survives; do not weaken that assertion to make a rebuild pass.
>
> **3.** The flagged section of `contracts.html` has never rendered a row, because until
> now there were none. Check it actually displays SRPT with its flag reason from
> `runway.notes`, with no rank number, below the separator. Fix it if it does not, and
> add a test that asserts the flagged section contains SRPT and that SRPT carries no rank.
>
> **4.** Confirm the ranked rows are sorted by gap ascending and that the provenance test
> still passes on the widened `/contracts` page. Every new figure needs its display
> string, which `apply_displays` should handle on the rebuild.
>
> Do not touch `engine/`. Do not weaken any existing assertion.

**Accept when:** `/contracts` shows three ranked rows and one flagged row with a readable
reason, `pytest tests/` is green with `.env` sourced, and the 677 row is still on
`/contract/RCKT`.

---

### Prompt 4, reduced: the panel the demo actually needs

`docs/SPEC.md` Phase 4 specifies a 60 to 100 company panel assembled from SEC DERA
quarterly ZIPs. That is three days of work and it is cut. But `docs/DEMO.md` allocates
2:20 to 2:50 to the panel and its own cut list says to keep the panel no matter what, so
the script and the artifact currently disagree.

This is the reduced version: it fills the demo beat honestly, in one session, using data
the engine already produces. Do this one first. The full DERA panel below stays available
if budget and days allow.

> Build `research/panel.py`. For the twelve tickers already in `engine/runway.py`'s demo
> list, join each company's runway band to the full registry revision history of its live
> trials, and emit a tidy CSV, one row per revision, with the sponsor's cash position and
> whether that revision carried an already-expired date.
>
> Then produce one figure for the demo: the distribution of registered-date revisions
> against runway, with the carried-expired revisions marked. Matplotlib, written to
> `research/figures/`, no interactivity, legible at video resolution.
>
> Say the sample size out loud in the caption. Twelve companies is twelve companies, not
> "the sector". Descriptive statistics only: no regression, no causal language, and no
> claim that cash-constrained sponsors behave differently. That question is open and
> `docs/FINDINGS.md` section 2 says exactly how it must be described.

**Accept when:** the CSV exists with one row per revision, the figure renders legibly, the
caption states the sample size, and nothing in the output implies a causal result.

---

## Prompt 4: the panel, full version

Only after the reduced panel above is working. Large downloads, long runtime, and
eight documented gotchas in the way.

> Build `research/panel.py`. Download the SEC DERA Financial Statement Data Sets
> quarterly ZIPs, filter `sub.txt` to SIC 2834, 2835, 2836 with US filers and 10-Q or
> 10-K forms, and rebuild the company universe **as of each historical quarter** so that
> companies which later delisted remain in the cross sections where they belong.
>
> Read `docs/FINDINGS.md` section 1 before writing any extraction code. It documents
> eight failure modes that each produce a wrong number rather than an error, including
> the year to date cash flow trap that makes "quarterly" filtering return Q1 of four
> consecutive years.
>
> For 60 to 100 companies with live Phase 2 or 3 trials, join quarterly runway to full
> registry revision histories. Emit a tidy CSV, one row per revision, with sponsor cash
> position at the revision date.
>
> Produce descriptive statistics only. Do not run a causal regression and do not report
> a relationship as established.

**Accept when:** the CSV exists, coverage and match rate are reported explicitly,
delisted companies appear in their historical quarters, and the reversal filter from
finding 1.7 is applied.

---

## Prompt 5: the README and the Bob section

> Write the README. Include a section describing how IBM Bob was used, drawn from the
> exported session transcripts, and describe the split accurately: the three engine
> modules in `engine/` predate Bob, and the governance port, redline loop, console, and
> panel were built with it.
>
> Do not overstate. An honest split reads as confidence; a vague claim of "built with
> Bob" invites the question you least want asked.
