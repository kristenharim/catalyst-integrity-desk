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

---

## Prompt 4: the panel

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
