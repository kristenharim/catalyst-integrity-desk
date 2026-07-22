# Parking

Things found while doing something else, written down instead of built. A discovery made
mid-workstream is almost always out of scope for that workstream, and the cost of acting on
it is not the code, it is that the workstream stops being the thing that was reviewed.

Nothing here is a commitment to do it. Several of these are deliberately not worth doing and
say so.

## From closing the bio cohort, 2026-07-22

**The amendment leaves a temp file behind on a failed write.** `_cached()` writes to
`path.<pid>.tmp` and renames. If `json.dump` raises, the temp file stays. It is harmless:
readers only ever look at the target path, `data/cache/` is gitignored, and the next attempt
at the same version by the same process overwrites it. Not cleaned up because a try/except
would take the amendment past the three-line change the procedure approved, and widening an
amendment to make it tidier is exactly what `AMENDING_PROTECTED_MODULES.md` forbids. Revisit
only if crash-loops start filling the cache directory.

**NIH trials carry far more revision episodes than industry ones.** 493 dead-date stretches
across 60 NIH trials against 188 across 60 industry trials, from `cohort-8326c1c1e964`.
That is 2.6x the episodes on top of 2.4x the duration, and nothing in this study explains
it. Plausibly it is just version count, since NIH trials in the sample carry many more
protocol versions, two of them over 300. Worth one afternoon to check whether normalising by
version count collapses the difference, because if it does not, it is a second finding
rather than a restatement of the first.

**Is the enumeration cap doing anything?** The frame is capped at 3,000 per stratum, so the
draw is uniform over the registry's own ordering within a stratum rather than over the whole
stratum. Currently disclosed as a limitation and untested. The cheap check is to draw a
second sample under a different ordering and see whether the rates move.

**No time series.** Every rate is one look at the registry. Whether lapse duration is
growing or shrinking is a genuinely different study and the more interesting one, and it
needs the frame rebuilt as of several historical dates. Out of scope here, and the single
most obvious follow-up.

**The version-cache read is a full directory glob per trial.** `measure()` now calls
`_versions()` to get the true latest registered date and its ESTIMATED/ACTUAL type, which
globs every cached file for that trial. On a 700-version trial that is 700 file reads for two
fields. It is fast enough on a local cache and it is the correct source, so it stays. If a
re-measure ever becomes a routine operation rather than a rare one, cache the last version per
trial instead.

**The `--compact` command is one-time by design and nothing schedules it.** After the next
resumable run appends duplicates, `test_store_holds_one_row_per_trial` will fail until
someone runs it. That is intentional: a store that silently self-compacts is a store that
can silently discard, and a failing test is a better prompt than a cron job. Noted so the
failure is recognised as the design rather than as a bug.

## Guarded but not written

**The AI/absorption domain content.** `orchestrator/lexicon.py` now rejects roadmap
predictions about model vendors and unlabelled waste magnitudes, and the guards were built
before any such content exists rather than after. The quantification memo may enter `docs/`
only with every figure labelled contingent and its assumption on the same line, which the
lexicon enforces mechanically. Nothing has been written yet and the guards do not oblige
anyone to write it.
