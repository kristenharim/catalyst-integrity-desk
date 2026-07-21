# Catalyst Integrity Desk: complete handoff bundle

Every handoff document and every line of verified engine code, concatenated. Generated
by `make_bundle.py`; the repo at `~/projects/catalyst-integrity-desk` is the source of
truth and this file is a snapshot of it.

Read in the order given. The three engine modules at the end are working, verified
against live SEC and ClinicalTrials.gov data, and are not to be rewritten.



---

# ==== HANDOFF.md ====

# Handoff: start here

This repo is a de-risked starting point, not a finished project. Three engine modules
are built and verified against live SEC and ClinicalTrials.gov data. Everything else is
specified but unbuilt, and that is deliberate: the unbuilt parts are what IBM Bob should
build, because the challenge requires Bob to be the primary development tool.

## What to do with the IBM chat you already have open

Pause it. Do not redirect it mid thread.

That thread's context is saturated with the portfolio risk framing, so a correction
inside it will keep drifting back to belief cards about VaR. A pivot this size wants a
clean context whose first input is a written spec.

Also: do not touch `~/projects/deliberate-risk-desk`. It runs, it talks to live Granite,
and it is the fallback demo if this build stalls. Its value is that it exists.

**Open a new chat and paste this as the first message:**

> I am building the Catalyst Integrity Desk for the IBM AI Builders Challenge, with IBM
> Bob as the primary development tool. The repo is at `~/projects/catalyst-integrity-desk`.
>
> Read these first, in order: `HANDOFF.md`, `docs/SPEC.md`, `docs/FINDINGS.md`,
> `docs/PORT.md`. `docs/FINDINGS.md` contains eight data gotchas that were found
> empirically and each one will cost you a day if you rediscover it.
>
> The three modules in `engine/` are verified working. Do not rewrite them. Run
> `python3 -m engine.runway`, `python3 -m engine.ctgov_history`, and `python3 -m engine.gap`
> to confirm before you change anything.
>
> Start with Phase 1 in `docs/SPEC.md`. Use `docs/BOB_PROMPTS.md` for the sequenced
> build prompts.

## What is verified working, right now

Run these. They hit live APIs and assert on real data.

```
python3 -m engine.runway          # cash runway from SEC XBRL, 12 clinical-stage names
python3 -m engine.ctgov_history   # registry revision history for one trial
python3 -m engine.gap             # the join: funding gap + date integrity
```

Measured on 2026-07-21:

- `NCT04613596` (Mirati): 95 protocol versions, 6 of which moved the primary
  completion date, net slip +2,193 days.
- `NCT04248439` (Rocket Pharmaceuticals): **carried a completion date that had already
  passed for 677 days** before correcting it.
- 12 of 12 clinical-stage, pre-revenue names produced rankable runway bands. Sana
  8.1-9.2 months, Prime Medicine 9.5-10.4, Rocket 9.5-9.6.

## The one paragraph version of the idea

Every biotech thesis rests on a date: the company has cash into X, the trial reads out
before X, therefore they are funded to the catalyst. The left side comes from SEC
filings. The right side comes from ClinicalTrials.gov, where the sponsor sets it, can
revise it at any time, and the revision is not reconciled against the thesis that
depended on the old date.

The Catalyst Integrity Desk treats that as a contract: this company has capital to reach
this readout by this date. Python computes both sides from filed tags and registry
records, with no model near a number. Granite reads the analyst's written rationale and
reports which stated assumption a new filing or amendment breaks. The analyst approves,
and the decision hash chains into a tamper evident ledger.

So the desk carries a third column: how the sponsor has behaved toward its own date.

## How to frame it, exactly

**"An auditable monitor for when a portfolio's cash-to-catalyst assumption breaks."**

Not "a novel dataset" and not "a new finding". Both of those lose under one question:

- The catalyst screen is a shipping commercial product. BiopharmaWatch filters 11,000+
  readouts by cash runway and burn across 949 companies, including a trial-change field.
- The revision panel is a published dataset: 4.3M per-version rows across ~583k trials.
- The finance-and-trial-timing link is adjacent published work (Guenzel & Liu, RFS 2026).

See `docs/FINDINGS.md` section 2. What survives is the *monitor*: a contract that is
recomputed deterministically, breached visibly, judged against its own written rationale,
and changed only by a human whose decision is hash chained. That is a real thing to build
and an honest thing to claim.

## What must not be claimed

That cash constrained sponsors revise their readout dates differently than solvent ones.
**Hypothesis, untested, and adjacent work already exists.** Say "we could not find" and
never "nobody has".

State the identification problem out loud: low runway correlates with small, under
resourced companies that slip more anyway, which pushes the opposite way from the
strategic story. A judge who hears an honest "here is the panel, here is why the causal
claim is hard" scores it above a confident result that dies to one question.

Also: say **registered primary-completion expectation**, not readout date. They are not
the same thing and the difference is a systematic 2 to 4 month optimistic bias.


---

# ==== docs/SPEC.md ====

# Catalyst Integrity Desk: build spec

Ten days. Four phases. Phase 1 is done. Phases 2 to 4 are what Bob builds.

Division of labor, which is the credibility backbone and must hold everywhere:
**Python computes. Granite judges prose. Humans decide.** No model produced number ever
reaches the user, and that is enforced by scanning model output for figures absent from
its input, not merely asserted in a README.

## Phase 1: deterministic engine (DONE, do not rewrite)

`engine/runway.py` cash runway from SEC XBRL, as a band, with provenance and
reliability flags.
`engine/ctgov_history.py` registry revision history per trial, with notice and expiry
metrics.
`engine/gap.py` the join: funding gap plus date integrity, as a `CatalystContract`.

Each has a `demo()` that asserts against live data. Run all three before changing
anything.

## Phase 2: governance layer, ported (2 days)

Port four modules from `~/projects/deliberate-risk-desk`. They are domain agnostic. See
`docs/PORT.md` for exactly what changes. Do not copy `metrics.py` or `scenario.py`.

The unit of belief becomes the catalyst contract:

```yaml
id: RCKT-FA-2026
claim: >
  Rocket reaches the Fanconi anemia primary completion on cash in hand, without
  a dilutive raise, and the readout resolves the gene therapy platform thesis.
metric: gap_months
range: [0, null]
driver: "9.5 months runway against a 2026-05 registered completion"
conviction: medium
invalidation:
  - registered completion date moves beyond runway exhaustion
  - burn band widens past 3x
  - securities tag path changes between quarters
```

A breach fires when a recomputed contract leaves its approved range. `scan_breaches`
already takes a flat `{metric_id: value}` dict, so a contract packet plugs in unchanged.

## Phase 3: the monitoring loop and the console (3 days)

**Redline.** A registry amendment or a new 10-Q lands. Python recomputes the contract.
If the gap crosses zero, build a challenge card: which approved assumption broke, with
the before and after figures rendered by the application, never by the model.

**Granite's job.** Given the contract's own rationale text and a description of the
breach *in directions rather than values* ("gap falls sharply", not "gap fell 9.2
months"), classify into the four labels and draft the memo. Handing it values means it
quotes them and then does arithmetic on them, which is the fabrication path the risk
desk already hit and fixed. Give it nothing to echo.

**Human verdict.** Accept, edit, or reject. Accepts append to the hash chained ledger,
rejects go to a separate review log with the reason.

**Console.** A web view, because a terminal recording is not a product. Three screens:
the contract list ranked by gap, one contract detail with its revision timeline, and the
pending redline awaiting approval. This is the highest visual payoff work in the project
and it carries zero risk to the engine.

## Phase 4: the panel and the demo (3 days)

**Assemble the panel.** For 60 to 100 clinical-stage companies (not the universe, and
say so out loud rather than implying full coverage): quarterly runway from DERA, joined
to full revision histories for their live Phase 2 and 3 trials.

Ship the descriptive panel. The causal claim is stated as the open question with its
identification problem named. See `HANDOFF.md`, "What must not be claimed".

**Freeze a snapshot.** The demo reads from a local JSON snapshot, never a live API. Live
registry calls on stage are the most common demo failure there is.

**Record a backup video.** Non negotiable.

## Scope discipline

In scope: one ranked contract list, one contract detail with revision timeline, one
scripted redline event, human approve and reject, the descriptive panel, hash chained
ledger with visible tamper detection.

Out of scope, and say so if asked rather than pretending: full universe coverage,
valuation, competitor analysis, probability of success modeling, multi user, the causal
result.

## 48 hour kill gates

Run these before committing the remaining eight days. If a gate fails, fall back to the
Deliberate Risk Desk rather than spending the week discovering the same thing slower.

| Gate | Pass condition | On failure |
|---|---|---|
| History | 10 candidate trials yield at least 3 material primary-completion-date revisions | fall back to A |
| Join | at least 5 clean issuer to sponsor to SEC filing joins | fall back to A |
| Finance | runway reconciles to the filing by hand, with provenance, for one company | manual single-company demo, or A |
| Demo | one breach explains itself in 20 seconds, out loud, to someone else | simplify before adding anything |

The demo gate is the one people skip and the one that decides the outcome. A judge has
two or three minutes. If the breach does not land in twenty seconds, no amount of
governance architecture behind it will help.

## Definition of done

- [ ] `python3 -m engine.gap` still passes after every change
- [ ] Ledger `verify()` returns false on a one byte edit, on camera
- [ ] Granite emits no figure absent from its input, with a test that proves it
- [ ] Every displayed number traces to a named XBRL tag or a registry version
- [ ] Flagged rows are visible and unranked, never silently dropped
- [ ] Demo runs from a frozen snapshot with the network off
- [ ] README describes what Bob built versus what preceded it, accurately


---

# ==== docs/FINDINGS.md ====

# Findings: data gotchas, prior art, attack surface

Everything in section 1 was found by running code against the live APIs on 2026-07-21,
not read in documentation. Each one silently produces a wrong number rather than an
error, which is the expensive kind.

## 1. Data gotchas, each with the fix

### 1.1 The registry history endpoint is TLS fingerprint gated

`/api/int/studies/{nct}/history` returns 403 to `urllib` and will do the same to
`requests`, because both share OpenSSL's TLS fingerprint. It returns 200 to `curl`
with any User-Agent, including a bare one.

Tested four header combinations (bare UA, curl-style UA, browser UA, browser UA plus
gzip and Accept) against a curl control. All four urllib variants 403, curl 200. It is
not the headers.

**Fix:** shell out to curl, which ships with macOS and needs no dependency. See
`engine/ctgov_history.py::_get`. `curl_cffi` would also work and adds a dependency.

### 1.2 A cash tag can go stale while the company is fine

Arrowhead stopped filing `CashAndCashEquivalentsAtCarryingValue` in 2024 and moved to
`CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents`. A first-wins tag
waterfall returned the last value of the abandoned tag: **$69M as of 2024-06-30, when
the real figure was $3,377M as of 2026-03-31.** A 49x error, and it dated the entire
record to 2024, which then broke the securities match too.

This does not look like a bug. It looks like a company about to die, which is exactly
the row a distress screen puts at the top.

**Fix:** evaluate every cash tag and take the one with the most recent balance date,
not the first that exists. Net out restricted cash when the winning tag bundles it.

### 1.3 Cash flow facts are year-to-date, so "quarterly" filtering lies

Cash flow statements are cumulative within a fiscal year. Q1 is natively a 90 day fact,
Q2 arrives as a 6 month figure, Q3 as 9 month, Q4 inside the 10-K as 12 month. So
filtering XBRL duration facts to a 60-120 day span does not return the last four
quarters. **It returns Q1 of four consecutive years**, and summing those produces a
plausible looking annual burn that is the trailing twelve months of nothing.

Observed directly: Moderna's "quarterly" facts came back as 2026-03-31, 2025-03-31,
2024-03-31, 2023-03-31.

**Fix:** facts within one fiscal year share a `start`, so group on `start`, sort by
`end`, and take consecutive differences. See `engine/runway.py::_quarterly_flows`.

### 1.4 Short term investments have no single tag, and it matters most where it matters

There is no `CashCashEquivalentsAndShortTermInvestments` tag. It is never filed. Real
coverage across clinical-stage filers is roughly 45%, split across at least three tags:
`ShortTermInvestments`, `MarketableSecuritiesCurrent`,
`AvailableForSaleSecuritiesDebtSecuritiesCurrent`. All four appear in the 12 name test
set, and Ionis uses two at once.

Part of the 45% is genuine (small companies hold only cash) and part is fragmentation.
Either way the missing half skews toward the well capitalized companies whose runway is
most interesting.

**Fix:** sum across all securities tags, but only those struck on the same date as the
cash balance, or the numerator mixes two quarters. Record which path resolved.

### 1.5 `company_tickers.json` is missing live filers

The file is complete (10,426 entries, 870 KB) and Amicus Therapeutics (FOLD) is simply
not in it. Neither is Verve.

**Fix:** the ticker map is a demo convenience only. The universe comes from the DERA
Financial Statement Data Sets quarterly ZIP, keyed on CIK and SIC code, where no ticker
is involved. Use SIC 2834, 2835, 2836. SIC 8731 is a red herring: 15 filings against
412 at 2834.

### 1.6 Operating cash flow is not burn for a company with revenue

Arrowhead's trailing year contains an $825M partnership inflow, netting its burn to near
zero and computing a **1,116 month runway**. Arithmetically correct, financially
meaningless.

**Fix:** flag any cash-positive operating quarter in the trailing window and any case
where the two burn estimates disagree by more than 3x. Flagged rows stay visible with
the reason attached but never carry a rank. On the correct population (clinical-stage,
pre-revenue) the flag rate went from 5 of 8 commercial names to 0 of 12.

### 1.7 Sponsors revise dates backwards, and it is a typo

`NCT04613596` moved its completion date +1,317 days at version 92 and then -1,317 days
at version 94, two months later. That is data entry, not a forecast revision. Any
statistic over revision magnitudes needs a reversal filter.

### 1.8 The sponsor to CIK join is the real engineering tax

`leadSponsor.name` is free text with no CIK. Forward matching (EDGAR name to registry)
runs about 83% naively, and most misses are correct rejections (animal health, cannabis,
shell companies). Sana and Intellia both failed to match in the demo. Realistic ceiling
with an alias table plus hand review of the top 300 by market cap is 90-95%.

Budget a full day for this. It is the single largest unbudgeted cost in the project.

## 2. Prior art, stated honestly

**The screen is not novel.** [BiopharmaWatch Catalyst Sync](https://www.biopharmawatch.com/catalyst-sync)
sells exactly it: filter 11,000+ upcoming readouts by cash runway and burn rate across
949 companies. BioPharmCatalyst, Biomedtracker/Citeline, and Stifel's weekly biopharma
update all occupy adjacent ground. EY Beyond Borders publishes the aggregate annually
(33% of public biotechs under one year of runway at end 2025).

Do not pitch the screen. A judge finds BiopharmaWatch in one search.

**The revision panel is also not novel, and this was an overclaim in an earlier draft of
this document.** [brbk/clinical_trials_history](https://huggingface.co/datasets/brbk/clinical_trials_history)
is 4,333,631 rows across roughly 583,000 trials, every version, with
`primary_completion_date` as a per-version field, built off the same internal endpoint.
Do not say "nobody has assembled this."

Operationally this is good news: it removes the single largest engineering cost in the
project. Crawling histories directly is roughly 50 to 100 requests per trial. Use the
dataset for the panel and keep `engine/ctgov_history.py` for live single-trial checks in
the demo, where fetching from the source is the point. Note the licence is CC-BY-NC-4.0,
which covers a hackathon but not a commercial product.

**The finance-and-trial-timing link is adjacent, not empty.**
[Guenzel & Liu, Excess Commitment in R&D, RFS 39(7) 2026](https://doi.org/10.1093/rfs/hhag026)
uses clinical trial project data and finds that delays reduce subsequent project
termination, instrumented with trial site congestion, moderated by CEO stock-price
sensitivity. That is the opposite arrow from this project's hypothesis (delay causing
firm behaviour, versus firm finances causing date revision behaviour), but it means the
territory is occupied and "no paper connects finance and trial timing" is indefensible.
Cite it, distinguish the arrow, and never claim empty terrain.

**What still appears open,** stated as a search result rather than a fact: we could not
find work on sponsor liquidity predicting *disclosure* behaviour toward the registered
date specifically, meaning how long a lapsed date is carried and how much notice a
revision gives. That is narrower than "the intersection is unoccupied" and it is the
most that can be honestly claimed without a systematic review.

Background that does exist: the trial delay literature
([Shadbolt et al., JAMA Netw Open 2023](https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2800488),
about 1 in 5 RCTs complete on time, median delay 12.2 months), the primary outcome
switching literature, and the biotech financing literature
([Lerner, Shane & Tsai, JFE 2003](https://www.sciencedirect.com/science/article/abs/pii/S0304405X02002568)).

## 3. The five hardest questions

**"Your burn number is wrong for exactly the companies that matter."**
Correct. A Phase 3 ramp burns above the trailing rate; a partnership upfront shows a
positive quarter. That is why burn is a band and unstable rows are excluded from
ranking rather than silently included. Publish the sensitivity.

**"Primary completion date is not a readout."**
Correct, and it is a systematic bias, not noise. PCD is last patient last visit for the
primary endpoint; topline follows by weeks to months. The gap is optimistic by roughly
2 to 4 months on every row. The honest reframe is that the number is the sponsor's own
registered expectation, which is weaker as a product and stronger as research, because
the sponsor's stated belief is precisely the object of study.

**"Companies raise opportunistically, not at zero cash."**
Concede fully. This is why "negative gap predicts financing" is close to tautological: a
company with six months of cash raises within six months regardless. It also strengthens
the real hypothesis, because if raising is window dependent then a company facing a
closed window has a stronger reason to manage the visible date.

**"Survivorship."**
Real. The public biotech universe shrank from 977 to 758 companies between 2021 and
2025, and the missing names are non randomly the negative gap tail. DERA is available
per quarter back to 2009, so rebuild the universe as of each historical quarter. One
afternoon, and it is the difference between a snapshot and a panel.

**"The interesting companies are the ones your arithmetic fails on."**
Royalty monetization, non dilutive upfronts, debt facilities with milestone tranches,
priority review voucher sales. Every one breaks cash divided by burn. This is the best
justification for the model in the architecture: not to extract numbers, but to read the
going concern and subsequent events footnotes and emit a categorical flag. Company
guided runway versus computed runway is itself a chart worth showing.


---

# ==== docs/PORT.md ====

# Porting the governance layer

Four modules move from `~/projects/deliberate-risk-desk`. They were written for a
portfolio risk desk and are domain agnostic anyway, which is why this pivot is a port
and not a rewrite. Line counts verified 2026-07-21.

**Copy the source repo, do not move it.** `deliberate-risk-desk` runs, talks to live
Granite, and is the fallback demo.

| File | Lines | Domain coupling | Change needed |
|---|---|---|---|
| `engine/ledger.py` | 174 | one docstring example, the `scope` field comment | comments only |
| `orchestrator/challenge.py` | 135 | none | none |
| `orchestrator/classifier.py` | 68 | none | none |
| `orchestrator/granite.py` | 318 | `SYSTEM_PROMPT` and `ACTION_PROMPT` text | rewrite two prompt strings |

695 lines, of which the only real work is two prompts.

## Why it drops in cleanly

`scan_breaches(cards, packet_flat)` takes a flat `{metric_id: value}` dict and knows
nothing about what produced it. A catalyst contract packet looks like:

```python
{
  "gap_months": -5.2,
  "runway_months_low": 9.5,
  "burn_ttm_annual": 180_000_000,
  "pcd_revisions": 4,
  "max_days_expired": 677,
}
```

That satisfies the existing interface with no changes to the ledger.

`BeliefCard` already carries claim, metric, range, driver, and conviction, which is
exactly the catalyst contract's shape. `scope` becomes `"company:RCKT"` or
`"trial:NCT04248439"` instead of `"position:NVDA"`.

`Classification`'s four labels (`direct_contradiction`, `assumption_weakened`,
`assumption_strengthened`, `new_material_evidence`) carry over unchanged. A trial
amendment that pushes completion past runway exhaustion is a direct contradiction of a
"funded to catalyst" claim, in exactly the sense the labels already mean.

## The two prompts that need rewriting

`SYSTEM_PROMPT` currently opens "You are the challenge partner on a portfolio risk
desk." The replacement frames the same job in the new domain: a deterministic engine has
recomputed a catalyst contract and something left its approved range; judge whether the
drift breaks the written rationale.

**Keep the fabrication guard exactly as it is.** `_fabricated()` scans model output for
numeric runs absent from its input and discards the whole response on a hit. It already
caught Granite quoting supplied impact figures and then subtracting them to state a loss
it was never given. The structural fix was to hand the model directions instead of
values, and that pattern must survive the port. Do not loosen it to "ban all digits"
either: an earlier version did, and it rejected Granite for correctly quoting a figure
out of the belief's own claim text. The rule is "a number absent from the input", which
is what fabrication actually means.

## What does not come across

`engine/metrics.py` and `engine/scenario.py` are finance specific and have no analogue
here. Leave them.

There is also a substantive reason not to reuse `scenario.py`'s approach. Its shock
scales each ticker's whole price history by a constant, which leaves returns and the
covariance matrix unchanged, so every metric that moves does so only because position
weights moved. That makes its headline result an artifact of the shock convention rather
than a measurement. Nothing in this project should inherit that shape: here both sides
of the gap come from filed values and dated registry records, and there is no assumption
doing the work.


---

# ==== docs/BOB_PROMPTS.md ====

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


---

# ==== docs/DEMO.md ====

# Demo script, three minutes

Runs from a frozen local snapshot. Network off. Backup video recorded.

The structure is deliberate: open on a fact nobody in the room knows, show the machine
catching it, hand the decision to a human, then zoom out to the panel. The reveal comes
before the product, because a product demo that opens on a dashboard has already lost
the room.

---

**0:00 to 0:25, the hook.**

> Every biotech thesis rests on a date. They have cash into Q1 2028, the Phase 3 reads
> out in Q3 2027, therefore they are funded to the catalyst.
>
> The left side of that sentence comes from SEC filings. The right side comes from
> ClinicalTrials.gov, where the company sets it, can change it whenever it likes, and
> nothing reconciles that change against the thesis that depended on the old date.

**0:25 to 0:50, the fact.**

Show the Rocket Pharmaceuticals revision timeline.

> Here is a real trial. Four revisions. In April 2024 they updated a primary completion
> date of June 2022. That date had already passed, six hundred and seventy seven days
> earlier, and it sat on the public registry the entire time.
>
> No press release. No 8-K. Nothing in the thesis that depended on it moved.

**0:50 to 1:20, the contract.**

> So we treat the catalyst as a contract: this company has capital to reach this readout
> by this date. Runway comes from XBRL tags, and every figure names the tag it came
> from. The readout date comes from the sponsor's own filing, with its full revision
> history attached. Python computes both sides. No model touches a number.

Point at the burn band and the flagged rows.

> Burn is a range, not a point, because a partnership upfront makes one quarter
> unrepresentative. Rows we cannot trust stay on screen with the reason attached. They
> just do not get a rank.

**1:20 to 1:55, the break.**

Fire the scripted amendment.

> An amendment lands and pushes primary completion out nine months. Python recomputes.
> The funding gap flips negative.
>
> Granite reads the analyst's own written rationale for this position and reports which
> stated assumption just broke. It is given the direction of the move, never the values,
> so it has nothing to echo and nothing to do arithmetic on. Any figure in its output
> that was not in its input discards the whole response.

**1:55 to 2:20, the human gate.**

> The analyst approves or rejects. The decision hash chains into the ledger.

Edit one byte of the ledger file on camera. Run `verify()`. It returns false.

> The thesis is never trusted. It is reviewable.

**2:20 to 2:50, the panel.**

> Every revision is timestamped, so we joined the revision panel to sponsor cash position
> across the sector. Here is the distribution.
>
> The open question is whether companies that cannot fund their way to a readout hold
> optimistic dates longer than solvent ones. We are not claiming that. Low runway
> correlates with small under resourced companies that slip anyway, and separating those
> needs a within firm design. There is adjacent published work on trial delays and firm
> incentives, and the revision data itself is public. What is ours is the monitor.

**2:50 to 3:00, the close.**

> Built with IBM Bob on watsonx and Granite. The registry is not a data source. It is a
> disclosure channel with incentives, and now it has an auditor.

---

## The prior art slide

Put this in the deck, visible, before Q&A. Naming your own priors reads as confidence.
Having them named for you reads as unaware. Same underlying novelty, opposite scores.

Title it **"What already exists"** and do not apologise for any of it.

| Layer | Who owns it |
|---|---|
| The screen: rank companies by runway against catalyst | [BiopharmaWatch Catalyst Sync](https://www.biopharmawatch.com/catalyst-sync), 11,000+ readouts filtered by cash runway and burn across 949 companies, including a trial-change field |
| Catalyst calendars and analyst-adjusted dates | [Biomedtracker / Citeline](https://www.evaluate.com/solutions/biomedtracker/), [BioPharmCatalyst](https://www.biopharmcatalyst.com/calendars/fda-calendar) |
| Sector runway aggregates | EY Beyond Borders, 33% of public biotechs under one year of runway at end 2025; Stifel publishes weekly |
| The per-version registry panel | [brbk/clinical_trials_history](https://huggingface.co/datasets/brbk/clinical_trials_history), 4,333,631 rows across ~583,000 trials, `primary_completion_date` per version, CC-BY-NC-4.0 |
| Registry-derived dates used to study firm behaviour | [Guenzel & Liu, *Excess Commitment in R&D*, RFS 39(7) 2026](https://doi.org/10.1093/rfs/hhag026): delays reduce project termination, instrumented by trial-site congestion, moderated by CEO stock-price sensitivity |
| Trial delay base rates | [Shadbolt et al., *JAMA Netw Open* 2023](https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2800488): about 1 in 5 RCTs complete on time, median delay 12.2 months |
| Biotech financing cycles | [Lerner, Shane & Tsai, *JFE* 2003](https://www.sciencedirect.com/science/article/abs/pii/S0304405X02002568) |

Then one line, spoken:

> None of that is what we built. What we built is the monitor: the contract that gets
> recomputed when one of those inputs changes, judged against the rationale someone
> actually wrote down, and changed only by a human whose decision is hash chained.

## Q&A one-liners

Rehearse these. Each is under fifteen seconds.

**"Isn't this BiopharmaWatch?"**
Their screen is better than ours and larger. A screen tells you the gap today. It does
not hold a written thesis, detect when a registry amendment breaks it, or record who
decided what. That is the difference between a filter and a monitor.

**"Guenzel and Liu already did this."**
They ran the opposite arrow: delay causing firms to keep funding projects, moderated by
CEO pay. Ours is firm liquidity possibly affecting how a date gets disclosed. Their paper
is why we know the measurement works, and we cite it.

**"The revision data is already published."**
It is, and we use it. Assembling it was never the contribution.

**"So what is new?"**
Honestly, the monitor and one narrow open question about disclosure behaviour, which we
have not tested and are not claiming.

**"Isn't primary completion date just the readout?"**
No, and that is a systematic bias, not noise. It is last patient last visit for the
primary endpoint; topline follows by weeks to months. Every gap we show is optimistic by
roughly two to four months, uniformly.

**"Your burn number is wrong for the interesting companies."**
Yes. That is why it is a band and why unreliable rows are shown but never ranked.
Arrowhead's partnership upfront computes to a 1,116 month runway in our own engine, and
we flag it rather than print it.

## Cuts, if you run long

Drop in this order: the burn band explanation at 1:20, then the ledger tamper demo. Keep
the Rocket fact and the panel no matter what. Those are the two things the room has not
seen before.

## Do not

- Do not open on the dashboard.
- Do not claim the causal result.
- Do not say "no tool does this". BiopharmaWatch sells a runway filtered catalyst
  screener across 949 companies and a judge will find it. The honest line is that the
  screen is a product and the revision panel is not.


---

# ==== engine/runway.py ====

```python
"""Cash runway from SEC XBRL company facts. Deterministic, from filed tags only.

No model computes any number here. Every figure traces to a us-gaap tag in a specific
filing, and `Runway.provenance` names which tag each component came from, because the
tags are not uniform across filers and a runway number whose numerator you cannot
identify is not auditable.

The numerator is the hard part, and it is the opposite of what you would guess. Burn
(`NetCashProvidedByUsedInOperatingActivities`) is tagged by ~99% of clinical-stage
filers. Liquid securities are not: there is no single tag, and roughly half of filers
use none of them because they hold only cash. The ones that DO hold securities are the
well-capitalized companies whose runway matters most, so the tag waterfall below is
load-bearing rather than defensive. `CashCashEquivalentsAndShortTermInvestments` looks
like the right tag and is never filed -- do not reach for it.

Burn is reported as a BAND, not a point. A company that just dosed first patient in a
pivotal trial will burn well above its trailing rate; one that just booked a partnership
upfront shows a positive operating quarter. A single point estimate implies a precision
the filings do not support, and a ranked screen whose order flips under a 25% burn
perturbation is not a screen. Rank on the interval.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import date, datetime

SEC = "https://data.sec.gov"
# SEC's access policy requires a real contact string in the User-Agent.
UA = os.environ.get("SEC_UA", "catalyst-integrity-desk kris10harim@gmail.com")
CACHE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cache")
SLEEP = 0.12  # SEC allows 10 req/s

# Tried in order; first hit wins, and the winner is recorded in provenance.
CASH_TAGS = [
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
]
# Summed, not first-wins: a filer can report several distinct securities buckets.
SECURITIES_TAGS = [
    "ShortTermInvestments",
    "MarketableSecuritiesCurrent",
    "AvailableForSaleSecuritiesDebtSecuritiesCurrent",
]
# Counted toward runway only when opted in. Companies include >12mo maturities in
# their own runway guidance, but calling it "liquidity" without saying so is a stretch.
LONG_TERM_TAGS = ["LongTermInvestments", "MarketableSecuritiesNoncurrent"]

BURN_TAG = "NetCashProvidedByUsedInOperatingActivities"
# Fallback for the ~1% that omit the cash-flow tag: opex is an upper bound on cash burn
# (it includes non-cash stock comp), so a runway built on it is conservative.
BURN_FALLBACK_TAGS = ["OperatingExpenses", "ResearchAndDevelopmentExpense"]

DAYS_PER_MONTH = 365.25 / 12


def _curl_json(url: str, retries: int = 3) -> dict:
    """SEC's edge blocks some non-browser clients; curl with a contact UA is accepted.
    Same shell-out rationale as the registry crawler."""
    for attempt in range(retries):
        p = subprocess.run(
            ["curl", "-sS", "--fail", "--compressed", "--max-time", "60",
             "-H", f"User-Agent: {UA}", url],
            capture_output=True, text=True,
        )
        if p.returncode == 0:
            try:
                return json.loads(p.stdout)
            except json.JSONDecodeError:
                pass
        if attempt == retries - 1:
            raise RuntimeError(f"GET {url} failed: {p.stderr.strip() or p.returncode}")
        time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def _cached(name: str, url: str) -> dict:
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    time.sleep(SLEEP)
    d = _curl_json(url)
    with open(path, "w") as f:
        json.dump(d, f)
    return d


def ticker_to_cik() -> dict[str, str]:
    """SEC's own ticker map. CIKs are zero-padded to 10 digits in the API paths."""
    d = _cached("company_tickers.json", "https://www.sec.gov/files/company_tickers.json")
    return {v["ticker"].upper(): f"{int(v['cik_str']):010d}" for v in d.values()}


def company_facts(cik: str) -> dict:
    return _cached(f"facts-{cik}.json", f"{SEC}/api/xbrl/companyfacts/CIK{cik}.json")


def _d(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _usd(facts: dict, tag: str) -> list[dict]:
    return facts.get("facts", {}).get("us-gaap", {}).get(tag, {}).get("units", {}).get("USD", [])


def _latest_instant(facts: dict, tag: str) -> tuple[float, str] | None:
    """Most recent point-in-time value (balance-sheet items have no `start`)."""
    pts = [f for f in _usd(facts, tag) if "start" not in f and f.get("end")]
    if not pts:
        return None
    best = max(pts, key=lambda f: (f["end"], f.get("fy") or 0))
    return float(best["val"]), best["end"]


def _quarterly_flows(facts: dict, tag: str) -> list[dict]:
    """True quarterly values, newest first, recovered by differencing the YTD series.

    Cash-flow statements are cumulative within a fiscal year. A 10-Q reports
    year-to-date, so the only fact that is natively ~90 days long is Q1; Q2 arrives as
    a 6-month figure, Q3 as 9-month, Q4 inside the 10-K as 12-month. Filtering on a
    60-120 day span therefore does NOT return the last four quarters -- it returns Q1
    of four consecutive years, and summing those produces a plausible-looking annual
    burn that is not the trailing twelve months of anything.

    Facts within one fiscal year share a `start`, so grouping on `start` recovers the
    cumulative progression, and consecutive differences recover the quarters:

        Q1 = YTD(3mo)                Q3 = YTD(9mo) - YTD(6mo)
        Q2 = YTD(6mo) - YTD(3mo)     Q4 = FY(12mo) - YTD(9mo)
    """
    by_start: dict[str, dict[str, float]] = {}
    for f in _usd(facts, tag):
        if not (f.get("start") and f.get("end")):
            continue
        # Later filings restate; keep the most recently reported value for each period.
        by_start.setdefault(f["start"], {})[f["end"]] = float(f["val"])

    quarters: list[dict] = []
    for start, ends in by_start.items():
        prev_end, prev_val = start, 0.0
        for end in sorted(ends):
            span = (_d(end) - _d(prev_end)).days
            if 60 <= span <= 120:      # one quarter's worth of elapsed time
                quarters.append({"start": prev_end, "end": end,
                                 "val": ends[end] - prev_val})
            prev_end, prev_val = end, ends[end]

    seen, uniq = set(), []
    for q in sorted(quarters, key=lambda q: q["end"], reverse=True):
        if q["end"] not in seen:
            seen.add(q["end"])
            uniq.append(q)
    return uniq


@dataclass
class Runway:
    ticker: str
    cik: str
    name: str
    as_of: str
    cash: float
    securities: float
    burn_ttm_annual: float        # trailing four quarters, annualized
    burn_recent_annual: float     # most recent quarter, annualized
    provenance: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    inflow_quarters: list[str] = field(default_factory=list)

    @property
    def liquidity(self) -> float:
        return self.cash + self.securities

    def _months(self, annual_burn: float) -> float | None:
        if annual_burn <= 0:
            return None  # cash-flow positive over this window; runway is not the binding question
        return self.liquidity / (annual_burn / 12)

    @property
    def months_low(self) -> float | None:
        """Shorter runway of the two burn estimates -- the conservative end."""
        got = [m for m in (self._months(self.burn_ttm_annual),
                           self._months(self.burn_recent_annual)) if m is not None]
        return min(got) if got else None

    @property
    def months_high(self) -> float | None:
        got = [m for m in (self._months(self.burn_ttm_annual),
                           self._months(self.burn_recent_annual)) if m is not None]
        return max(got) if got else None

    @property
    def burn_unstable(self) -> bool:
        """True when the two burn estimates disagree by more than 3x.

        This is the honest answer to "your burn number is wrong for exactly the
        companies that matter". A collaboration upfront, a milestone, or a Phase 3
        ramp makes one quarter unrepresentative, and the disagreement between the
        trailing-year and most-recent-quarter estimates is the cheapest available
        detector. A row flagged here must not be ranked on its point estimate.
        """
        lo, hi = self.months_low, self.months_high
        return lo is not None and hi is not None and lo > 0 and hi / lo > 3

    @property
    def reliable(self) -> bool:
        """Whether this row may be RANKED, as opposed to merely reported.

        Cash divided by burn is only a runway when the denominator is an operating
        burn. A partnership upfront or milestone inside the trailing year makes it
        something else: Arrowhead's 2025 Sarepta payment nets its trailing burn to
        near zero and produces a 1,100-month runway, which is arithmetically correct
        and financially meaningless. Those rows stay visible with the reason attached,
        because a screen that silently drops its hard cases is worse than one that
        shows them -- but they never carry a rank.
        """
        return (self.months_low is not None
                and not self.inflow_quarters
                and not self.burn_unstable)

    def exhaustion(self, months: float | None) -> date | None:
        if months is None:
            return None
        return _d(self.as_of) + __import__("datetime").timedelta(days=months * DAYS_PER_MONTH)

    def __str__(self) -> str:
        if self.months_low is None:
            return f"{self.ticker:6} {self.name[:28]:28} cash-flow positive over both windows"
        flag = "  UNSTABLE BURN" if self.burn_unstable else ""
        return (f"{self.ticker:6} {self.name[:28]:28} "
                f"${self.liquidity/1e6:8,.0f}M  "
                f"runway {self.months_low:5.1f}-{self.months_high:5.1f} mo  "
                f"(to {self.exhaustion(self.months_low)}){flag}")


def compute_runway(ticker: str, cik_map: dict[str, str] | None = None,
                   include_long_term: bool = False) -> Runway:
    cik_map = cik_map or ticker_to_cik()
    ticker = ticker.upper()
    if ticker not in cik_map:
        raise KeyError(f"{ticker} not in SEC ticker map")
    cik = cik_map[ticker]
    facts = company_facts(cik)

    prov, notes = {}, []

    # Pick the cash tag with the MOST RECENT balance date, not the first one that
    # exists. Filers migrate between tags: Arrowhead stopped filing
    # CashAndCashEquivalentsAtCarryingValue in 2024 and moved to the restricted-cash-
    # inclusive tag, so a first-wins waterfall silently returned a two-year-old $69M
    # balance instead of the current $1.8B, and dated the whole record to 2024. A
    # stale numerator does not look wrong -- it looks like a company about to die,
    # which is precisely the row a screen like this puts on screen first.
    candidates = [(tag, hit) for tag in CASH_TAGS if (hit := _latest_instant(facts, tag))]
    cash, as_of = 0.0, ""
    if candidates:
        tag, (cash, as_of) = max(candidates, key=lambda c: c[1][1])
        prov["cash"] = tag
        # This tag bundles restricted cash, which cannot fund operations. Net it out
        # when the filer reports it separately on the same date.
        if "RestrictedCash" in tag:
            r = _latest_instant(facts, "RestrictedCashAndCashEquivalentsAtCarryingValue")
            if r and r[1] == as_of:
                cash -= r[0]
                prov["cash"] += " less RestrictedCashAndCashEquivalentsAtCarryingValue"
    else:
        notes.append("no cash tag found")

    securities, sec_tags = 0.0, []
    for tag in SECURITIES_TAGS + (LONG_TERM_TAGS if include_long_term else []):
        hit = _latest_instant(facts, tag)
        # Only count a securities balance struck on the same date as the cash balance,
        # or the numerator mixes two different quarters.
        if hit and hit[1] == as_of:
            securities += hit[0]
            sec_tags.append(tag)
    prov["securities"] = "+".join(sec_tags) if sec_tags else "none"
    if not sec_tags:
        notes.append("no securities tag on the cash date (cash-only, or fragmented tagging)")

    flows = _quarterly_flows(facts, BURN_TAG)
    prov["burn"] = BURN_TAG
    if not flows:
        for tag in BURN_FALLBACK_TAGS:
            flows = [{**f, "val": -abs(float(f["val"]))} for f in _quarterly_flows(facts, tag)]
            if flows:
                prov["burn"] = f"{tag} (fallback, upper bound on cash burn)"
                notes.append("cash-flow tag absent; burn approximated from expense tag")
                break
    if not flows:
        raise ValueError(f"{ticker}: no usable burn tag")

    ttm = flows[:4]
    # Operating cash flow is negative for a company that burns. Flip the sign so a
    # positive burn number means money going out, which is what the ratio expects.
    burn_ttm_annual = -sum(float(f["val"]) for f in ttm) * (4 / len(ttm))
    burn_recent_annual = -float(flows[0]["val"]) * 4
    if len(ttm) < 4:
        notes.append(f"only {len(ttm)} quarters available; TTM scaled up")
    inflow_quarters = [f["end"] for f in ttm if float(f["val"]) > 0]
    if inflow_quarters:
        # A cash-positive quarter inside the trailing year is almost always a
        # partnership upfront or milestone, not a change in operating economics.
        # It deflates the burn estimate and inflates runway; say so on the row.
        notes.append(f"cash-positive operating quarter(s) in TTM window: "
                     f"{', '.join(inflow_quarters)} - likely a one-time inflow")

    return Runway(
        ticker=ticker, cik=cik, name=facts.get("entityName", ""),
        as_of=as_of or flows[0]["end"], cash=cash, securities=securities,
        burn_ttm_annual=burn_ttm_annual, burn_recent_annual=burn_recent_annual,
        provenance=prov, notes=notes, inflow_quarters=inflow_quarters,
    )


def demo() -> None:
    """Self-check on real filers. Values are not hardcoded -- the assertions check
    internal consistency and sane magnitudes, so this keeps passing as filings roll."""
    cik_map = ticker_to_cik()
    assert len(cik_map) > 5000, len(cik_map)
    assert "MRNA" in cik_map

    # company_tickers.json lags: it is missing live filers (Amicus/FOLD is absent from
    # all 10,426 entries). Fine for a demo list, wrong as a universe source -- the
    # universe comes from DERA sub.txt by SIC code, keyed on CIK, with no ticker.
    # Clinical-stage and pre-revenue on purpose. Commercial names (MRNA, SRPT, IONS,
    # ALNY, ARWR) get flagged constantly because product revenue and partnership
    # upfronts land in operating cash flow, which is correct behaviour and also the
    # wrong population: for a company with no product, operating cash flow IS burn.
    tickers = ["BEAM", "NTLA", "SANA", "RCKT", "DYN", "KYMR", "NUVL", "PRME",
               "ARVN", "EDIT", "CRSP", "VOR"]
    rows = []
    for t in tickers:
        try:
            rows.append(compute_runway(t, cik_map))
        except (KeyError, ValueError) as e:
            print(f"  {t}: skipped ({e})")

    assert rows, "no company resolved"
    for r in rows:
        assert r.cash >= 0 and r.securities >= 0
        assert r.liquidity >= r.cash
        if r.months_low is not None:
            assert r.months_low <= r.months_high
        assert r.provenance.get("cash"), r.ticker
    # Only rankable rows must be sane. Unreliable ones are allowed to be absurd --
    # that is what makes them unreliable, and the flag is the point.
    for r in [r for r in rows if r.reliable]:
        assert 0 < r.months_low < 600, (r.ticker, r.months_low)

    rankable = [r for r in rows if r.reliable]
    flagged = [r for r in rows if not r.reliable]
    assert rankable, "every row was flagged; the guards are too aggressive"

    print(f"RANKED  ({len(rankable)} of {len(rows)} rows carry a rank)")
    for r in sorted(rankable, key=lambda r: r.months_low):
        print(f"  {r}")
    if flagged:
        print(f"\nREPORTED, NOT RANKED  ({len(flagged)})")
        for r in flagged:
            print(f"  {r}")
            for n in r.notes:
                print(f"         {n}")
    print()
    for r in rows:
        print(f"  {r.ticker:6} as_of {r.as_of}  cash={r.provenance['cash']}  "
              f"sec={r.provenance['securities']}")
        for n in r.notes:
            print(f"         note: {n}")
    print("\nok")


if __name__ == "__main__":
    demo()
```


---

# ==== engine/ctgov_history.py ====

```python
"""Sponsor forecast revisions, reconstructed from ClinicalTrials.gov version history.

Registered trials carry a primary completion date (PCD). Sponsors may revise it at
any time, and every revision is kept as a numbered protocol version. Nobody diffs
them, so the revision path is a free, timestamped record of how a sponsor's own
forecast moved -- and of how long it held a date it was going to miss.

Two endpoints, neither in the public v2 docs, both unauthenticated:

    /api/int/studies/{nct}/history          -> every version, with a change date
    /api/int/studies/{nct}/history/{n}      -> the full protocol snapshot at version n

The listing is one request. Snapshots are one request each, so a 95-version trial is
95 requests if fetched naively. Two things keep that bounded: `moduleLabels` names
which modules changed in each version, and PCD lives in the status module, so any
version that did not touch it cannot have moved the date. Snapshots are cached on
disk, keyed by (nct, version), because history is immutable once written.

The derived quantity that matters is not the total slip. It is `held_days`: how close
the then-current date was when the sponsor finally moved it. A sponsor that pushes a
date out eighteen months in advance is forecasting. One that moves it eleven days
before it arrives was holding a date it had stopped believing.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, asdict
from datetime import date, datetime

BASE = "https://clinicaltrials.gov/api/int/studies"
# SEC and NIH both ask for a contact in the UA. Same courtesy here.
UA = os.environ.get("CTGOV_UA", "catalyst-integrity-desk (kris10harim@gmail.com)")
CACHE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cache")
SLEEP = float(os.environ.get("CTGOV_SLEEP", "0.12"))  # ~8 req/s, well inside tolerance

# The module that carries primaryCompletionDateStruct. A version whose moduleLabels
# omits this cannot have moved the date, so its snapshot is never fetched.
STATUS_LABEL = "Study Status"


def _get(url: str, retries: int = 3) -> dict:
    """Fetch JSON via curl.

    Not urllib, and this is not a style choice. The endpoint is gated on TLS
    fingerprint, not on headers: every urllib request returns 403 while the identical
    request through curl returns 200, including with a browser User-Agent, an explicit
    Accept, and gzip encoding. Tested four header combinations against a curl control.
    So `requests` will fail here too -- it shares OpenSSL's fingerprint. The options are
    shelling out to curl or adding curl_cffi; curl ships with macOS and needs no
    dependency, so the crawler shells out.
    """
    for attempt in range(retries):
        p = subprocess.run(
            ["curl", "-sS", "--fail", "--max-time", "30", "-H", f"User-Agent: {UA}", url],
            capture_output=True, text=True,
        )
        if p.returncode == 0:
            try:
                return json.loads(p.stdout)
            except json.JSONDecodeError:
                pass  # truncated body, worth one more try
        if attempt == retries - 1:
            raise RuntimeError(f"GET {url} failed: {p.stderr.strip() or p.returncode}")
        time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def _cached(nct: str, version: int) -> dict:
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{nct}-v{version}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    time.sleep(SLEEP)
    d = _get(f"{BASE}/{nct}/history/{version}")
    with open(path, "w") as f:
        json.dump(d, f)
    return d


def _parse_date(s: str | None) -> date | None:
    """Registry dates come as YYYY-MM-DD or YYYY-MM. Month-only means the sponsor
    did not commit to a day; treat it as the first, and do not pretend otherwise."""
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


@dataclass
class Revision:
    """One version at which the registered primary completion date changed."""
    version: int
    submitted: str          # when the sponsor filed this revision
    pcd: str                # the date as of this version
    pcd_type: str           # ESTIMATED or ACTUAL
    status: str
    moved_days: int | None  # how far the date moved vs the previous version
    held_days: int | None   # days remaining on the OLD date when it was moved

    @property
    def is_late_move(self) -> bool:
        """Moved with under 90 days left on a date the sponsor had been showing.
        Not proof of anything on its own; it is the observation the study counts."""
        return self.held_days is not None and 0 <= self.held_days < 90

    @property
    def carried_expired(self) -> bool:
        """The date being replaced had ALREADY PASSED when the sponsor replaced it.

        A stronger signal than a late move, and a different one. A late revision can
        be a genuine surprise late in a trial. A date left standing after it lapsed
        means the public registry showed a completion date the sponsor had already
        missed, for `-held_days` days, with no correction. Rocket Pharmaceuticals
        carried a 2022-06 date until 2024-04 -- 677 days expired.
        """
        return self.held_days is not None and self.held_days < 0

    @property
    def days_expired(self) -> int:
        return -self.held_days if self.carried_expired else 0


@dataclass
class TrialHistory:
    nct: str
    sponsor: str
    phases: list[str]
    n_versions: int
    revisions: list[Revision]

    @property
    def first_pcd(self) -> str | None:
        return self.revisions[0].pcd if self.revisions else None

    @property
    def last_pcd(self) -> str | None:
        return self.revisions[-1].pcd if self.revisions else None

    @property
    def total_slip_days(self) -> int | None:
        a, b = _parse_date(self.first_pcd), _parse_date(self.last_pcd)
        return (b - a).days if a and b else None

    @property
    def n_late_moves(self) -> int:
        return sum(r.is_late_move for r in self.revisions)

    @property
    def n_expired_carried(self) -> int:
        return sum(r.carried_expired for r in self.revisions)

    @property
    def max_days_expired(self) -> int:
        """Longest stretch this trial showed a completion date that had already passed."""
        return max((r.days_expired for r in self.revisions), default=0)

    def as_dict(self) -> dict:
        d = asdict(self)
        d.update(first_pcd=self.first_pcd, last_pcd=self.last_pcd,
                 total_slip_days=self.total_slip_days, n_late_moves=self.n_late_moves)
        return d


def fetch_history(nct: str) -> TrialHistory:
    """Walk one trial's version history and return only the versions that moved the
    primary completion date."""
    listing = _get(f"{BASE}/{nct}/history")
    changes = listing.get("changes", [])
    if not changes:
        raise ValueError(f"{nct}: no version history returned")

    # Version 0 is always fetched (it establishes the first date); after that only
    # versions that touched the status module can have moved it.
    candidates = [c for c in changes
                  if c["version"] == 0 or STATUS_LABEL in (c.get("moduleLabels") or [])]

    sponsor, phases = "", []
    revisions: list[Revision] = []
    prev_pcd: date | None = None
    prev_raw = ""

    for c in candidates:
        snap = _cached(nct, c["version"])
        proto = snap.get("study", snap).get("protocolSection", {})
        status_mod = proto.get("statusModule", {})
        pcd_struct = status_mod.get("primaryCompletionDateStruct") or {}
        raw = pcd_struct.get("date")
        pcd = _parse_date(raw)
        if pcd is None:
            continue

        if not sponsor:
            sponsor = (proto.get("sponsorCollaboratorsModule", {})
                       .get("leadSponsor", {}).get("name", ""))
            phases = proto.get("designModule", {}).get("phases", []) or []

        if prev_pcd is not None and pcd == prev_pcd:
            continue  # status module changed for some other reason

        submitted = _parse_date(c.get("lastUpdateSubmitQcDate") or c.get("date"))
        moved = (pcd - prev_pcd).days if prev_pcd else None
        # How much runway the OLD date still had when the sponsor moved it. Negative
        # means they moved it after it had already passed, which is its own signal.
        held = (prev_pcd - submitted).days if prev_pcd and submitted else None

        revisions.append(Revision(
            version=c["version"],
            submitted=submitted.isoformat() if submitted else "",
            pcd=raw,
            pcd_type=pcd_struct.get("type", ""),
            status=c.get("status", ""),
            moved_days=moved,
            held_days=held,
        ))
        prev_pcd, prev_raw = pcd, raw

    return TrialHistory(nct=nct, sponsor=sponsor, phases=phases,
                        n_versions=len(changes), revisions=revisions)


def demo() -> None:
    """Self-check against a trial whose history is known to be long and messy."""
    h = fetch_history("NCT04613596")
    assert h.n_versions > 50, h.n_versions
    assert h.sponsor, "lead sponsor should resolve"
    assert len(h.revisions) >= 4, f"expected several PCD moves, got {len(h.revisions)}"
    # First recorded date must precede the last, or the walk is out of order.
    assert h.revisions == sorted(h.revisions, key=lambda r: r.version)
    # moved_days is None only on the first revision.
    assert all(r.moved_days is not None for r in h.revisions[1:])

    print(f"{h.nct}  {h.sponsor}  {'/'.join(h.phases) or 'n/a'}")
    print(f"  {h.n_versions} versions, {len(h.revisions)} of them moved the date")
    print(f"  {h.first_pcd} -> {h.last_pcd}   total slip {h.total_slip_days} days")
    print(f"  late moves (<90d notice): {h.n_late_moves}")
    print()
    print(f"  {'ver':>4} {'submitted':>11} {'PCD':>11} {'type':>10} {'moved':>7} {'held':>6}")
    for r in h.revisions:
        print(f"  {r.version:>4} {r.submitted:>11} {r.pcd:>11} {r.pcd_type:>10} "
              f"{'' if r.moved_days is None else f'{r.moved_days:+d}':>7} "
              f"{'' if r.held_days is None else r.held_days:>6}"
              f"{'  <- late' if r.is_late_move else ''}")
    print("\nok")


if __name__ == "__main__":
    demo()
```


---

# ==== engine/gap.py ====

```python
"""The catalyst contract: can this company fund itself to its own next readout?

    funding gap = runway exhaustion date - registered primary completion date

Negative means the money runs out first. Both sides are deterministic and sourced:
the left from SEC XBRL tags, the right from the sponsor's own registry filing. No
model contributes a number to either.

What makes this more than a subtraction is the third column. The registry date is not
an observation, it is a *claim the sponsor can revise at will*, and every revision is
timestamped. So alongside the gap we carry the sponsor's revision behaviour: how many
times the date moved, and how much notice was given each time. A company that pushes a
readout eighteen months out with a year of warning is forecasting. One that moves it
three weeks before it arrives was showing a date it had stopped believing -- and if
that behaviour turns out to cluster in cash-constrained sponsors, the registry is not
a data source, it is a disclosure channel with incentives.

That last claim is a hypothesis, not a result. This module assembles the panel needed
to test it. It does not test it, and nothing here should be presented as if it had.
"""
from __future__ import annotations

import json
import urllib.parse
from dataclasses import dataclass
from datetime import date

from engine.ctgov_history import TrialHistory, _get, _parse_date, fetch_history
from engine.runway import Runway, compute_runway, ticker_to_cik

V2 = "https://clinicaltrials.gov/api/v2/studies"
# Phase 2/3 only. Early-phase trials are not value-inflection points, and including
# them buries the catalyst in a pile of dose-escalation studies.
PIVOTAL_PHASES = {"PHASE2", "PHASE3", "PHASE2_PHASE3"}
LIVE = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING"}


def find_trials(sponsor: str, limit: int = 40) -> list[dict]:
    """Live pivotal-ish trials for one lead sponsor.

    The sponsor field is free text with no CIK, so this join is the engineering tax
    of the whole project: matching is by name, and names drift (subsidiaries, "Inc."
    vs "Inc", post-merger renames). Good enough to demo one company; a universe run
    needs an alias table and hand review of the largest names.
    """
    q = urllib.parse.urlencode({
        "query.spons": sponsor,
        "fields": ",".join([
            "protocolSection.identificationModule.nctId",
            "protocolSection.identificationModule.briefTitle",
            "protocolSection.statusModule.overallStatus",
            "protocolSection.statusModule.primaryCompletionDateStruct",
            "protocolSection.designModule.phases",
            "protocolSection.sponsorCollaboratorsModule.leadSponsor",
        ]),
        "pageSize": limit,
    })
    out = []
    for s in _get(f"{V2}?{q}").get("studies", []):
        p = s.get("protocolSection", {})
        phases = set(p.get("designModule", {}).get("phases", []) or [])
        status = p.get("statusModule", {}).get("overallStatus", "")
        pcd = p.get("statusModule", {}).get("primaryCompletionDateStruct", {}) or {}
        if not (phases & PIVOTAL_PHASES) or status not in LIVE or not pcd.get("date"):
            continue
        out.append({
            "nct": p["identificationModule"]["nctId"],
            "title": p["identificationModule"].get("briefTitle", ""),
            "status": status,
            "pcd": pcd["date"],
            "pcd_type": pcd.get("type", ""),
            "phases": sorted(phases),
            "sponsor": p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name", ""),
        })
    return sorted(out, key=lambda t: t["pcd"])


@dataclass
class CatalystContract:
    """One testable claim: this company reaches this readout on this money."""
    runway: Runway
    trial: dict
    history: TrialHistory | None = None

    @property
    def catalyst_date(self) -> date | None:
        return _parse_date(self.trial["pcd"])

    @property
    def gap_months(self) -> float | None:
        """Months of runway left at the registered readout date. Negative = short.

        Computed against the CONSERVATIVE end of the burn band. Reporting the
        optimistic end would flatter every row in the same direction.
        """
        end = self.runway.exhaustion(self.runway.months_low)
        cat = self.catalyst_date
        if end is None or cat is None:
            return None
        return (end - cat).days / (365.25 / 12)

    @property
    def verdict(self) -> str:
        g = self.gap_months
        if g is None:
            return "not computable"
        if not self.runway.reliable:
            return "not rankable (burn estimate unreliable)"
        return "funded to catalyst" if g >= 0 else "financing required before catalyst"

    def lines(self) -> list[str]:
        r, t = self.runway, self.trial
        g = self.gap_months
        out = [
            f"{r.ticker}  {r.name}",
            f"  liquidity      ${r.liquidity/1e6:,.0f}M  ({r.provenance['cash']} + {r.provenance['securities']}, as of {r.as_of})",
            f"  burn band      ${r.burn_ttm_annual/1e6:,.0f}M/yr trailing, ${r.burn_recent_annual/1e6:,.0f}M/yr most recent quarter",
            f"  runway         {r.months_low:.1f}-{r.months_high:.1f} months, exhausted {r.exhaustion(r.months_low)}",
            f"  catalyst       {t['nct']}  {'/'.join(t['phases'])}  {t['status']}",
            f"                 {t['title'][:70]}",
            f"                 primary completion {t['pcd']} ({t['pcd_type'].lower()})",
            f"  FUNDING GAP    {'n/a' if g is None else f'{g:+.1f} months'}   -> {self.verdict}",
        ]
        if self.history and self.history.revisions:
            h = self.history
            out += [
                f"  date integrity {len(h.revisions)} revisions across {h.n_versions} versions, "
                f"net slip {h.total_slip_days:+d} days, {h.n_late_moves} moved with under 90 days notice",
            ]
            if h.n_expired_carried:
                out.append(f"  *** EXPIRED     showed an already-passed completion date for up to "
                           f"{h.max_days_expired} days before correcting it")
            for rev in h.revisions[-4:]:
                if rev.carried_expired:
                    notice = f"{rev.days_expired:>4}d EXPIRED"
                elif rev.held_days is None:
                    notice = ""
                else:
                    notice = f"{rev.held_days:>5}d notice"
                moved = "" if rev.moved_days is None else f"{rev.moved_days:+5d}d"
                out.append(f"                 v{rev.version:<4} {rev.submitted}  -> {rev.pcd}  {moved}  {notice}")
        for n in r.notes:
            out.append(f"  note           {n}")
        return out


def build(ticker: str, cik_map=None, with_history: bool = True) -> CatalystContract | None:
    r = compute_runway(ticker, cik_map)
    trials = find_trials(r.name)
    if not trials:
        return None
    # The nearest live pivotal readout is the binding catalyst.
    trial = trials[0]
    hist = None
    if with_history:
        try:
            hist = fetch_history(trial["nct"])
        except (RuntimeError, ValueError):
            pass  # history is an enrichment, not a precondition
    return CatalystContract(runway=r, trial=trial, history=hist)


def demo() -> None:
    cik_map = ticker_to_cik()
    built = 0
    for ticker in ["SANA", "PRME", "RCKT", "NTLA"]:
        c = build(ticker, cik_map)
        if c is None:
            print(f"{ticker}: no live pivotal trial matched by sponsor name\n")
            continue
        built += 1
        assert c.runway.ticker == ticker
        assert c.trial["nct"].startswith("NCT")
        if c.gap_months is not None:
            # Gap must equal exhaustion minus catalyst, to the day.
            recomputed = (c.runway.exhaustion(c.runway.months_low) - c.catalyst_date).days
            assert abs(recomputed / (365.25 / 12) - c.gap_months) < 1e-9
        print("\n".join(c.lines()))
        print()
    assert built, "no contract assembled"
    print("ok")


if __name__ == "__main__":
    demo()
```
