# Bob log

Running record of what IBM Bob built versus what was done by hand. The README's Bob
section gets written from this file, not from memory.

Rule: every entry names the tool. If a line says "by hand", it is not Bob's work and must
not be described as Bob's work in the README.

Corrected 2026-07-21. Three rows read "Claude Code" for work Bob did: the redline loop
and both console tasks. Bob writes its own row and had been naming the wrong tool, which
understated it on the one requirement the submission cannot lose. Checked against the task
exports, the commit messages, and the changed-file list of the session before changing them.
`AGENTS.md` now tells Bob what it is called, so the next row should not need this.

## Build

| Date | Tool | What | Transcript |
|---|---|---|---|
| 2026-07-21 | by hand (pre-Bob) | `engine/runway.py`, `engine/ctgov_history.py`, `engine/gap.py`. Phase 1, verified against live SEC and ClinicalTrials.gov. | n/a |
| 2026-07-21 | by hand (pre-Bob) | `HANDOFF.md`, `docs/SPEC.md`, `docs/FINDINGS.md` 1.1-1.8 and section 2, `docs/PORT.md`, `docs/DEMO.md`, `docs/BOB_PROMPTS.md`. | n/a |
| 2026-07-21 | by hand (pre-Bob) | `AGENTS.md` and `.bob/custom_modes.yaml`. Bob reads AGENTS.md by default and this repo had none, so it would have read CLAUDE.md, which is addressed to a different tool. The modes put a fileRegex on edit permission so the three verified engine modules cannot be rewritten. | n/a |
| 2026-07-21 | IBM Bob | Prompt 1, the governance port. Copied `ledger.py`, `challenge.py`, `classifier.py`, `granite.py` from the risk desk, rewrote the two prompt strings for catalyst vocabulary, kept `_fabricated()` byte for byte. Wrote `engine/contract.py`, the flattener from `CatalystContract` to the packet `scan_breaches` reads, with a round-trip demo. | `docs/bob-sessions/phase2-governance-port.json` |
| 2026-07-22 | IBM Bob | Prompt 2, the redline loop. Wrote `orchestrator/redline.py`: `as_directions()` translates before/after metric packets into word-only direction labels (the `scenario.py` pattern); `ContractDelta` pairs approved and recomputed contracts; `run_redline()` detects a gap breach and calls `build_challenge`. Extended `granite.py` SYSTEM_PROMPT with metric definitions (gap_months sign, max_days_expired meaning) so a live call cannot misread negative gap as a late trial; extended `_user_prompt` to surface the directions block. Wrote `tests/test_redline_fabrication.py`: fabrication-guard test (fake transport injects invented figure, stub fallback fires), scripted-amendment test (synthetic packets, offline), live Granite test (asserts no invented figure in returned rationale). All three pass. | `docs/bob-sessions/phase2-redline-loop.json` |
| 2026-07-22 | IBM Bob | Console sub-task 1. Wrote `console/make_snapshot.py`: serialises SANA/PRME/RCKT engine output to `data/snapshot.json` (runway fields + provenance, trial dict, `TrialHistory.as_dict()` with `svg_x` positions computed on a 1100px canvas), scripted +9-month RCKT amendment, Granite redline with 5-attempt exponential backoff (30s base, doubles). Asserts `source == "granite"`, exits non-zero on stub or missing credentials. `--verify` flag prints gap_months, revision count, and source. Removed `data/snapshot.json` from `.gitignore` (demo artifact, committed so judges can run without credentials). | `docs/bob-sessions/phase3-console.json` |
| 2026-07-22 | IBM Bob | Console sub-tasks 2–6. `requirements.txt` (flask>=3.0). `console/app.py`: loads snapshot at startup, four GET routes + POST /redline/decide + GET /redline/confirm, no arithmetic in handlers. Templates: `base.html` (dark monospace layout, nav), `contracts.html` (ranked reliable rows + flagged section), `detail.html` (SVG revision timeline with carried-expired node in red at cy=72, gap calculation table with XBRL tag sources), `redline.html` (classification badge, breach table, Granite memo, Accept/Reject form), `confirm.html` (verdict + ledger verify badge + tamper-demo blockquote). `tests/test_console.py`: 9 tests — routing, 677 marker, carried-expired CSS class, granite/no-stub in memo, number-provenance parametrized over both routes. Provenance failure was verified (9999 injection named the token and the route). Display values pre-formatted in snapshot (`display` sub-dict + `gap_months_1f`) so every rendered number is a verbatim substring of the JSON. | `docs/bob-sessions/phase3-console.json` |
| 2026-07-22 | IBM Bob | Prompt 3 repair: the integrity badge. Fixed `GET /redline/confirm` to call `BeliefLedger.verify()` at render time instead of reading `?intact=` from the URL. Added `test_badge_flips_on_tampered_ledger`: POSTs a decision, mutates a byte inside the card payload (not the verdict word, which is in review_log.jsonl and not hashed), asserts the badge flips; seen failing before the fix. Added `--displays` flag to `make_snapshot.py` via `apply_displays()`: loads snapshot, recomputes all display sub-dicts from raw numerics, writes back; idempotent. Used it to add `breach.display` strings to the existing snapshot. Replaced all `%.1f` filters in `redline.html` with `display.*` strings. Added `/redline` to the provenance parametrize (was absent, passing only because the snapshot happened to contain those digit strings). `PORT` env var on `app.run`, defaulting 8050. | pending export |

## Not yet started

Prompts 1, 2 and 3 are done. Prompt 4, the panel, is cut for budget. Prompt 5, the
README, is written from this file.

## What counts as Bob's work

Bob's, and describable as Bob's:
- the governance port and `engine/contract.py` (Prompt 1)
- `orchestrator/redline.py` and the fabrication test (Prompt 2)
- the console, all three views, the snapshot generator and the console tests (Prompt 3)

Not Bob's, and must be described as preceding it:
- the three `engine/` modules
- the spec, findings, port plan, demo script, prompt pack
- gate checks, verification runs and review passes, which wrote no product code

## Review passes

Not build work, and not anyone's contribution to the prototype. No product code was
written in any of these. They are listed so the build rows above can be trusted, and
because a review that found nothing is worth the same as one that found something only
if both are on the record.

The README describes how Bob was used. It does not need to enumerate these, and naming
a review tool there would answer a question nobody asked while diluting the one claim
that matters.

| Date | What |
|---|---|
| 2026-07-21 | Ran the three engine demos (all pass). Ran the Join kill gate over the full 12 name set: 8/12 joined, gate passes. Found and quantified findings 1.9 and 1.10, written into `docs/FINDINGS.md`. Created this file. |
| 2026-07-21 | Badge repair verification. Reverted the confirm handler to the query-string version and to a hardcoded `True`; the new badge test failed both times, so it is anchored to behaviour. Re-ran the four original console mutations, all still caught. Confirmed `--displays` byte-identical across runs and credential-free, the Granite block unregenerated, and the four engine gates green. Walked the tamper demo in a browser: accept, edit one byte, reload, badge flips to tampered. Noted that the provenance check matches by substring, so a truncating format passes for free. |
| 2026-07-21 | Console verification. Found the plan's display formats contradicted its own provenance test on 12 of 16 displayed figures, and amended `docs/plans/console.md` before the build reached it. Mutation-tested all four console checks (planted `9999`, renamed marker class, `stub` in the memo, `days_expired` 677 to 123); all four caught. Confirmed every display string recomputes from its source value and the Granite redline block was never regenerated. Found the confirm page reads its integrity badge from `?intact=1` rather than the ledger, so the tamper demo shows green on a corrupted file; queued the repair as Prompt 3 repair. Corrected the three misattributed rows above. |
