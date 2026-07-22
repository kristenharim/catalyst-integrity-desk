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

## The open case

The `_cached()` non-atomic write meets all four conditions and has not been applied. It is
recorded in `docs/LIMITS.md`, the readers this project owns were hardened to skip an
unreadable entry, and the source-level fix is available for a human to approve under this
procedure. Degrading gracefully around a known corruption path is the correct temporary
answer and the wrong permanent one.
