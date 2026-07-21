# Bob log

Running record of what IBM Bob built versus what was done by hand. The README's Bob
section gets written from this file, not from memory.

Rule: every entry names the tool. If a line says "by hand", it is not Bob's work and must
not be described as Bob's work in the README.

| Date | Tool | What | Transcript |
|---|---|---|---|
| 2026-07-21 | by hand (pre-Bob) | `engine/runway.py`, `engine/ctgov_history.py`, `engine/gap.py`. Phase 1, verified against live SEC and ClinicalTrials.gov. | n/a |
| 2026-07-21 | by hand (pre-Bob) | `HANDOFF.md`, `docs/SPEC.md`, `docs/FINDINGS.md` 1.1-1.8 and section 2, `docs/PORT.md`, `docs/DEMO.md`, `docs/BOB_PROMPTS.md`. | n/a |
| 2026-07-21 | Claude Code | Verification and gate checks only, no repo code written. Ran the three engine demos (all pass). Ran the Join kill gate over the full 12 name set: 8/12 joined, gate passes. Found and quantified findings 1.9 and 1.10 below; wrote them into `docs/FINDINGS.md`. Created this file. | this session |
| 2026-07-21 | by hand (pre-Bob) | `AGENTS.md` and `.bob/custom_modes.yaml`. Bob reads AGENTS.md by default and this repo had none, so it would have read CLAUDE.md, which is addressed to a different tool. The modes put a fileRegex on edit permission so the three verified engine modules cannot be rewritten. | n/a |
| 2026-07-21 | IBM Bob | Prompt 1, the governance port. Copied `ledger.py`, `challenge.py`, `classifier.py`, `granite.py` from the risk desk, rewrote the two prompt strings for catalyst vocabulary, kept `_fabricated()` byte for byte. Wrote `engine/contract.py`, the flattener from `CatalystContract` to the packet `scan_breaches` reads, with a round-trip demo. | `docs/bob-sessions/` |
| 2026-07-22 | Claude Code | Prompt 2, the redline loop. Wrote `orchestrator/redline.py`: `as_directions()` translates before/after metric packets into word-only direction labels (the `scenario.py` pattern); `ContractDelta` pairs approved and recomputed contracts; `run_redline()` detects a gap breach and calls `build_challenge`. Extended `granite.py` SYSTEM_PROMPT with metric definitions (gap_months sign, max_days_expired meaning) so a live call cannot misread negative gap as a late trial; extended `_user_prompt` to surface the directions block. Wrote `tests/test_redline_fabrication.py`: fabrication-guard test (fake transport injects invented figure, stub fallback fires), scripted-amendment test (synthetic packets, offline), live Granite test (asserts no invented figure in returned rationale). All three pass. | this session |

## Not yet started

Phase 2 Prompt 2 is done. Prompt 3, the console, is next.

## What counts as Bob's work

Bob's, and describable as Bob's:
- the governance port and `engine/contract.py` (Prompt 1)
- `orchestrator/redline.py` and the fabrication test (Prompt 2)
- the console (Prompt 3)
- `research/panel.py` (Prompt 4)

Not Bob's, and must be described as preceding it:
- the three `engine/` modules
- the spec, findings, port plan, demo script, prompt pack
- gate checks and verification runs
