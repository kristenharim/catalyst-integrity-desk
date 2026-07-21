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
