"""The 19 planted defects the council found, committed as fixtures.

Every one of these was written by an adversarial reviewer against the real
documents, and every one of them passed the first version of the prose guard.
They are kept here rather than reconstructed, because a mutation corpus the
author invents is a corpus shaped around what the author already checks: the
first guard was mutation-tested against three cases it happened to catch and
declared working.

Each entry is (name, doc, find, replace, why). `find` must still be present in
the real document; a fixture that no longer matches is a stale fixture and the
corpus test fails on it rather than silently passing.
"""

# Seat 3's fourteen.
SEAT_3 = [
    ("s3-off-by-one-restored", "docs/WRITEUP.md",
     "| 20 of 27 | 2 | 0 |", "| 20 of 27 | 2 | 1 |",
     "the shipped off-by-one, restored"),
    ("s3-nih-date-changes-old-value", "docs/WRITEUP.md",
     "| 0 of 0 | 106.5 | 3 |", "| 0 of 0 | 106.5 | 4 |",
     "the pre-fix value from n_pcd_revisions"),
    ("s3-industry-prevalence", "docs/WRITEUP.md",
     "| 5 of 60 (8.3%)", "| 5 of 60 (9.7%)",
     "a rate that is in no field"),
    ("s3-median-off-by-one-day", "docs/WRITEUP.md",
     "median is 1,101.5 days in industry", "median is 1,101 days in industry",
     "one day out"),
    ("s3-strata-swapped", "docs/WRITEUP.md",
     "median is 1,101.5 days in industry, 1,178 in OTHER\nand 2,288.5 in OTHER_GOV",
     "median is 2,288.5 days in industry, 1,178 in OTHER\nand 1,101.5 in OTHER_GOV",
     "right values, wrong strata"),
    ("s3-min-off-by-one", "docs/WRITEUP.md",
     "the shortest anywhere is 203 days", "the shortest anywhere is 202 days",
     "one day out on the minimum"),
    ("s3-min-wrong-population", "docs/WRITEUP.md",
     "the shortest anywhere is 203 days", "the shortest anywhere is 2 days",
     "the minimum of a different population"),
    ("s3-clustering-count", "docs/WRITEUP.md",
     "**17 of 126 (13.5%)", "**18 of 126 (13.5%)",
     "the near-year count, one out"),
    ("s3-readme-industry-silent", "README.md",
     "4 of 5 in industry", "3 of 5 in industry",
     "a count that is in no field"),
    ("s3-readme-govt-silent-up", "README.md",
     "20 of 27 for government sponsors", "21 of 27 for government sponsors",
     "a count that is in no field"),
    ("s3-readme-govt-silent-down", "README.md",
     "20 of 27 for government sponsors", "19 of 27 for government sponsors",
     "a count that is in no field, the other direction"),
    ("s3-readme-median-typo", "README.md",
     "a median of 1,101.5 and 2,288.5 days respectively",
     "a median of 1,101.5 and 2,880 days respectively",
     "transposed digits on a continuation line"),
    ("s3-nih-versions-rounded", "docs/WRITEUP.md",
     "| 0 of 0 | 106.5 | 3 |", "| 0 of 0 | 106 | 3 |",
     "the 106.5-as-106 error the guard was written for"),
    ("s3-clustering-rate", "docs/WRITEUP.md",
     "**17 of 126 (13.5%)", "**27 of 126 (21.4%)",
     "count and rate both wrong"),
]

# Seat 1's five.
SEAT_1 = [
    ("s1-govt-silent-inflated", "docs/WRITEUP.md",
     "20 of 27 in OTHER_GOV", "26 of 27 in OTHER_GOV",
     "the headline count inflated"),
    ("s1-invisible-wrong-denominator", "docs/WRITEUP.md",
     "**4 of 5** | 9 | 2 |", "**4 of 9** | 9 | 2 |",
     "a denominator that is a real field, in the wrong cell"),
    ("s1-silent-median-inflated", "docs/WRITEUP.md",
     "median is 1,101.5 days in industry", "median is 1,502 days in industry",
     "a median that is in no field"),
    ("s1-readme-medians-inflated", "README.md",
     "a median of 1,101.5 and 2,288.5 days respectively",
     "a median of 1,902 and 2,988 days respectively",
     "both medians wrong on a continuation line"),
    ("s1-retired-phrase", "docs/COHORT.md",
     "reverse the ordering", "rank the four strata in exactly opposite order",
     "a phrase retracted three rounds running"),
]

CORPUS = SEAT_3 + SEAT_1
