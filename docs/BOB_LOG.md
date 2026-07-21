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

## Not yet started

Phase 2 (Prompt 1, the governance port) is unstarted, deliberately. It is Bob's first
build and writing it anywhere else spends the one requirement that has no fallback.

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
