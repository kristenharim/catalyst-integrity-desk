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
