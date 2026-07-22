"""The planted defects the council found, committed as fixtures.

Every one of these was written by an adversarial reviewer against the real
files, and every one of them passed some earlier version of the guard. They are
kept here rather than reconstructed, because a mutation corpus the author
invents is a corpus shaped around what the author already checks: the first
guard was mutation-tested against three cases it happened to catch and declared
working, then failed nineteen of nineteen written by the seats.

Each entry is (name, target, find, replace, why). `target` is a claim document
or the generator itself; `find` must still be present in it, and a fixture that
no longer matches is a stale fixture that fails the corpus test rather than
silently passing.

**Round seven retargeted this corpus and then found it vacuous.** The documents
are generated now, so a defect typed into one is caught by the byte comparison
the moment it is planted, and the document-level fixtures below prove that the
comparison covers every line rather than probing anything subtle. Seat 3 moved
its own `106.5`-printed-as-`106` fixture to the generator, on the grounds that
the document is no longer where that error can originate.

Then the seat that attacked the guard showed the score was hollow: twenty-two of
twenty-three fixtures were caught by staleness alone, and deleting the digit rule
and the whole residual scan still gave twenty-three of twenty-three. Including
the generator fixtures, because a stale document is what a developer clears by
re-rendering, which is the first thing anyone does after editing a generator. So
the corpus test now re-renders a generator mutation before checking it, and the
seven fixtures at the end are that seat's own demonstrated holes, each watched
publishing a wrong or invented figure with the suite green.
"""

GENERATOR = "research/render_writeup.py"

# Seat 3's fourteen, retargeted onto the generated text.
SEAT_3 = [
    ("s3-off-by-one-restored", "docs/WRITEUP.md",
     "| OTHER_GOV | 27 of 60 (45.0%) | 27 of 29 (93.1%) | 20 of 27 | 2 | 0 |",
     "| OTHER_GOV | 27 of 60 (45.0%) | 27 of 29 (93.1%) | 20 of 27 | 2 | 1 |",
     "the shipped off-by-one, restored"),
    ("s3-nih-date-changes-old-value", "docs/WRITEUP.md",
     "| NIH | 0 of 60 (0.0%) | 0 of 18 (0.0%) | 0 of 0 | 106.5 | 3 |",
     "| NIH | 0 of 60 (0.0%) | 0 of 18 (0.0%) | 0 of 0 | 106.5 | 4 |",
     "the pre-fix value from n_pcd_revisions"),
    ("s3-industry-prevalence", "docs/WRITEUP.md",
     "| INDUSTRY | 5 of 60 (8.3%)", "| INDUSTRY | 5 of 60 (9.7%)",
     "a rate that is in no field"),
    ("s3-median-off-by-one-day", "docs/WRITEUP.md",
     "The median is 1,101.5 days in INDUSTRY",
     "The median is 1,101 days in INDUSTRY",
     "one day out"),
    ("s3-strata-swapped", "docs/WRITEUP.md",
     "The median is 1,101.5 days in INDUSTRY, 2,288.5 days in\nOTHER_GOV",
     "The median is 2,288.5 days in INDUSTRY, 1,101.5 days in\nOTHER_GOV",
     "right values, wrong strata"),
    ("s3-min-off-by-one", "docs/WRITEUP.md",
     "the shortest anywhere is 203", "the shortest anywhere is 202",
     "one day out on the minimum"),
    ("s3-min-wrong-population", "docs/WRITEUP.md",
     "the shortest anywhere is 203", "the shortest anywhere is 2",
     "the minimum of a different population"),
    ("s3-clustering-count", "docs/WRITEUP.md",
     "| INDUSTRY | 126 | 289 | 17 of 126 (13.5%)",
     "| INDUSTRY | 126 | 289 | 18 of 126 (13.5%)",
     "the near-year count, one out"),
    ("s3-readme-industry-silent", "README.md",
     "4 of 5 in INDUSTRY", "3 of 5 in INDUSTRY",
     "a count that is in no field"),
    ("s3-readme-govt-silent-up", "README.md",
     "20 of 27 in OTHER_GOV", "21 of 27 in OTHER_GOV",
     "a count that is in no field"),
    ("s3-readme-govt-silent-down", "README.md",
     "20 of 27 in OTHER_GOV", "19 of 27 in OTHER_GOV",
     "a count that is in no field, the other direction"),
    ("s3-readme-median-typo", "README.md",
     "a median of 1,101.5 days in INDUSTRY, 2,288.5 days in",
     "a median of 1,101.5 days in INDUSTRY, 2,880 days in",
     "transposed digits on a continuation line"),
    # Retargeted in round seven. The document cannot originate this error any
    # more, so the fixture attacks the formatter that would.
    ("s3-nih-versions-rounded", GENERATOR,
     "    if float(v) == int(v):\n        return f\"{int(v):,}\"\n    return f\"{v:,}\"",
     "    if float(v) == int(v):\n        return f\"{int(v):,}\"\n    return f\"{v:,.0f}\"",
     "the 106.5-as-106 error, at the formatter that would cause it"),
    ("s3-clustering-rate", "docs/WRITEUP.md",
     "| INDUSTRY | 126 | 289 | 17 of 126 (13.5%)",
     "| INDUSTRY | 126 | 289 | 27 of 126 (21.4%)",
     "count and rate both wrong"),
]

# Seat 1's five.
SEAT_1 = [
    ("s1-govt-silent-inflated", "docs/WRITEUP.md",
     "20 of 27 in OTHER_GOV", "26 of 27 in OTHER_GOV",
     "the headline count inflated"),
    ("s1-invisible-wrong-denominator", "docs/WRITEUP.md",
     "| 4 of 5 | 9 | 2 |", "| 4 of 9 | 9 | 2 |",
     "a denominator that is a real field, in the wrong cell"),
    ("s1-silent-median-inflated", "docs/WRITEUP.md",
     "The median is 1,101.5 days in INDUSTRY",
     "The median is 1,502 days in INDUSTRY",
     "a median that is in no field"),
    ("s1-readme-medians-inflated", "README.md",
     "a median of 1,101.5 days in INDUSTRY, 2,288.5 days in",
     "a median of 1,902 days in INDUSTRY, 2,988 days in",
     "both medians wrong on a continuation line"),
    ("s1-retired-phrase", "docs/COHORT.md",
     "reverse the ordering", "rank the four strata in exactly opposite order",
     "a phrase retracted three rounds running"),
]

# Round seven, against the generator. This is where a figure defect can still
# originate now that nothing is retyped.
SEAT_7 = [
    ("g7-cell-bound-to-the-wrong-field", GENERATOR,
     '          _of(S[c]["carrying_now_invisible_to_stretches"], S[c]["carrying_now"]),',
     '          _of(S[c]["open_estimates"], S[c]["carrying_now"]),',
     "the headline's silent-carrier cell rendering a real but different field"),
    ("g7-numeral-in-prose", GENERATOR,
     "The prose you are reading is a template that carries no numerals of its own",
     "The prose you are reading is a template that carries no numerals of its own, "
     "over all 240 trials",
     "a figure typed into a prose template, which is what the whole rule forbids"),
    ("g7-figure-as-a-literal", GENERATOR,
     '    f["silent_min"] = _n(min(S[c]["silent_carrier_days_min"] for c in carriers))',
     '    f["silent_min"] = _n(203)',
     "a correct figure hard-coded, so it stops tracking the field"),
    ("g7-ratio-inverted", GENERATOR,
     '    f["trial_ratio"] = _ratio(S["NIH"]["trial_days_p50"],\n'
     '                              S["INDUSTRY"]["trial_days_p50"])',
     '    f["trial_ratio"] = _ratio(S["INDUSTRY"]["trial_days_p50"],\n'
     '                              S["NIH"]["trial_days_p50"])',
     "a ratio computed the wrong way round, which shipped once while this was "
     "being written and rendered 0.7x for 1.5x"),

    # The seven below were demonstrated by the seat that attacked the guard
    # rather than the figures. Every one of them was watched publishing a wrong
    # or invented figure with the whole suite green, and every one is committed
    # here rather than described, because a hole a reviewer found and nobody
    # wrote down is a hole that comes back.
    ("g7-wrong-field-outside-a-table", GENERATOR,
     '    f["industry_lapse_counts"] = _of(S["INDUSTRY"]["revisions_after_lapse_to_estimate"],',
     '    f["industry_lapse_counts"] = _of(S["INDUSTRY"]["revisions_after_lapse"],',
     "the same defect as the headline cell, in a sentence that is in no table; "
     "it doubled the published count and read as its own contradiction"),
    ("g7-arithmetic-literal", GENERATOR,
     '    f["window"] = _n(clus["window_half_width_days"])',
     '    f["window"] = _n(4 * 31)',
     "a figure assembled from literals small enough to pass a magnitude rule, "
     "publishing a methodology parameter the test did not run at"),
    ("g7-citation-invents-a-rate", GENERATOR,
     '    "guenzel": {\n        "cite": "Guenzel & Liu, RFS 2026",\n    },',
     '    "guenzel": {\n        "cite": "Guenzel & Liu, RFS 2026",\n    },\n'
     '    "desk": {"cite": "internal desk note", "quote": "about 9.7% of industry trials"},',
     "a cohort rate laundered through the citation table, which is exempt from "
     "the digit rule and used to reject only figures that matched a real field"),
    ("g7-backticked-figure", "README.md",
     "Nobody was watching",
     "Industry point prevalence is `8.3%` of all trials.\n\nNobody was watching",
     "a live figure retyped in a code span, which the residual scan used to blank "
     "before looking"),
    ("g7-linked-figure", "README.md",
     "Nobody was watching",
     "The NIH median carry is [1,101.5 days](docs/WRITEUP.md).\n\nNobody was watching",
     "the same, in markdown link text"),
    ("g7-malformed-marker", "docs/STATUS.md",
     "<!-- generated: primary_measures -->",
     "<!-- generated: primary_measures  -->",
     "one space, and the block is never substituted again; the document freezes "
     "on whatever it said and render() reports success"),
    ("g7-unguarded-document", "docs/LIMITS.md",
     "| INDUSTRY | 80.0% | 8.3% | 4 | 9 |",
     "| INDUSTRY | 80.0% | 21.7% | 13 | 9 |",
     "a prevalence table in the one document whose purpose is accuracy about "
     "what went wrong, and it was in neither guard's document list"),
]

CORPUS = SEAT_3 + SEAT_1 + SEAT_7
