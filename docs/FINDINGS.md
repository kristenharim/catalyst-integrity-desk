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

### 1.9 `query.spons` matches collaborators, so a partner's trial becomes your catalyst

The v2 search parameter `query.spons` is not a lead-sponsor filter. It matches the
sponsor/collaborator block as a whole, so a trial another company runs comes back under
your issuer's name and `engine/gap.py` assigns it as that issuer's binding catalyst.

Observed: `find_trials("ARVINAS, INC.")` returns `NCT05654623` first. Its `leadSponsor`
is **Pfizer**; Arvinas Estrogen Receptor, Inc. is a collaborator. Arvinas's funding gap
was therefore computed against a Pfizer-run trial.

One of 8 joined names in the 12 name set. It does not error and it does not look wrong on
screen, because the trial is real and the drug is genuinely theirs.

**Fix:** after searching, keep only trials whose `leadSponsor.name` matches the issuer,
normalising the suffix noise (`Inc.`/`Inc`/`, Inc`/`AG`/`Corp`). The registry's lead
sponsor string differs from EDGAR's registrant name in 3 of 8 joins even when correct
(`Rocket Pharmaceuticals Inc.` vs `ROCKET PHARMACEUTICALS, INC.`), so match normalised,
not literal.

### 1.10 The nearest registered completion is usually the most stale one

`find_trials` sorts ascending by primary completion date and `build` takes `trials[0]`,
which is the *earliest* date, not the *next* one. Because sponsors carry lapsed dates
(finding 1.7 and the Rocket case), the earliest date is frequently already in the past,
so the selection rule is biased toward exactly the stalest record in the set.

Three of 8 joined names picked an already-passed completion date on 2026-07-21: ARVN
(2025-01-31), EDIT (2025-08), RCKT (2026-05-05).

This one is not cosmetic. Rocket is the demo's hero row. Against its picked date the gap
is **+8.4 months, "funded to catalyst"**. Against its nearest *future* registered
completion (`NCT06092034`, 2028-04) the same runway gives **-14.5 months, "financing
required"**. Same company, same filing, opposite verdict, decided entirely by which
registered date is treated as binding.

**Fix is a definition, not a patch, and it is Kristen's call:** decide whether the binding
catalyst is the nearest completion date still in the future, or the nearest one whose
trial is still live regardless of a lapsed date. The second is defensible and is arguably
the project's whole point, but then the gap must be presented against a date the sponsor
has already missed, and the demo has to say so out loud rather than print
"funded to catalyst".

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
