# Amending a protected module

`engine/runway.py`, `engine/ctgov_history.py` and `engine/gap.py` are verified against live
APIs and `CLAUDE.md` says not to rewrite them. That rule has held and is worth keeping: it
is the reason the arithmetic underneath every displayed figure has stayed stable through
four rounds of self-audit.

It needed a procedure the first time a real defect turned up inside one, which it now has.
`_cached()` writes a fetched version straight to its target path, so an interrupted run
leaves a truncated file that breaks every later read of that trial. One such file out of
335 took down five unrelated tests. The fix is a temp-file write and an atomic rename:
three lines, no interface change, no behaviour change on the happy path.

"Do not touch" gave no way to make that fix, so the choice was between violating the rule
and shipping a known corruption path. Neither is right, and the reason the rule exists is
to prevent *unreviewed* change, not all change. So:

## When an amendment is allowed

All four must hold. Any one missing and it is not an amendment, it is a rewrite.

1. **A defect, demonstrated.** A failing test or a reproduced corruption, not a
   readability preference and not a refactor.
2. **No interface change.** Same signatures, same return shapes, same field names. A
   caller cannot tell the difference except that the bug is gone.
3. **No behaviour change on correct input.** The fix changes only what happens on the
   failure path. Verified by running the module's own `demo()` gate before and after and
   diffing the output.
4. **The three engine gates pass**, plus every test that touches the module.

## What the amendment must carry

- A test that fails before and passes after, named in the commit.
- A comment at the changed line stating the defect and the date, so the next reader knows
  the line was argued rather than casually edited.
- A row in `docs/BOB_LOG.md` recording it as an amendment to a protected module, with the
  four conditions checked off explicitly.
- An entry in `docs/LIMITS.md` if the defect had any chance of having affected a published
  figure.

## What stays forbidden regardless

- Changing what a number means, how it is computed, or which XBRL tag or registry field it
  resolves through.
- Adding a dependency, including on anything in `evidence/`, which would break the
  layering check in `tests/test_layering.py`.
- Widening an interface to make a caller's life easier. That is the caller's problem.
- Tidying. If the diff would still be worth making with the bug already fixed, it is not
  an amendment.

## The first invocation, 2026-07-22

The `_cached()` non-atomic write was the case this procedure was written for, and it has
now been applied under it, with the owner's approval. Recorded here because a procedure
nobody has run is a document, not a control.

How each condition was met, and how it was checked rather than asserted:

| Condition | Evidence |
|---|---|
| 1. A defect, demonstrated | Two cohort trials, `NCT04269902` and `NCT04071223`, stored a `JSONDecodeError` in place of a measurement, on top of the earlier `NCT03919071-v356.json` case. A test reproduces it by interrupting a write. |
| 2. No interface change | Same signature, same return, same cache path. |
| 3. No behaviour change on correct input | All four module gates captured before and after the edit and diffed. Byte identical. |
| 4. Gates pass, plus every test touching the module | Four gates green, full suite green, two new tests in `tests/test_ctgov_cache.py`. |

The test named in the commit is
`tests/test_ctgov_cache.py::test_interrupted_cache_write_leaves_no_readable_entry`. It was
watched failing against the pre-amendment module, where the truncated file survives at the
target path, which is the whole defect.

Two things learned that are worth keeping for the next amendment.

The before-and-after gate diff is the condition that does the work. It is the only one that
cannot be satisfied by reading the diff and feeling confident, and it is cheap: capture the
output, edit, capture again, diff.

And the defect had already been degraded around. `engine/dimensions.py` and
`research/backtest.py` were hardened to skip an unreadable entry, which was the correct
temporary answer, and the temporary answer is what made the permanent one easy to defer.
The graceful degradation stays: it is still right for a cache entry corrupted some other
way. But it silently lowered the number of versions a comparison could see, which fails
toward refusing to state a number rather than toward stating a wrong one, and that is
exactly the kind of safe failure that survives a long time without being fixed.
