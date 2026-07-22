# Limits

What each guard actually proves, stated at the strength the evidence supports and no
higher. Everything here was found by breaking the thing and watching what happened, not
by reading the code and reasoning about it.

This file exists because the project's pitch is that it does not flatter itself. A judge
who finds one of these unaided has found a hole. A judge who reads them here has found a
team that already looked.

## The ledger detects modification, and now deletion, with one caveat

`verify()` walks the hash chain and recomputes each link. It catches any edit to a byte
inside a hashed payload. On its own that is all it catches: a bare hash chain proves the
**presented** chain is self-consistent, never that it is the **original** chain.

Verified before the anchor existed: deleting the newest entry left `verify()` returning
`True`, and replacing the whole file with a freshly built valid chain whose claim read
"Rocket is comfortably funded and no financing is required" also returned `True`.

`orchestrator/anchor.py` closes that by recording the head hash and entry count outside
the chain and comparing on render. Verified by running each attack:

| Attack | Badge |
|---|---|
| clean ledger | intact |
| edit one byte inside a hashed payload | tampered |
| delete the newest entry | truncated or replaced |
| replace the file with a valid chain | truncated or replaced |
| delete the anchor file itself | truncated or replaced |

The last row matters: a missing anchor fails closed rather than green.

**The residual limit, and it is real.** The anchor lives in `data/ledger.anchor`, which the
same process writes. An attacker who rewrites the ledger and the anchor together defeats
it. This raises the bar from "edit one file" to "edit two consistently"; it does not make
the record immutable. Say "detects tampering, deletion and replacement of recorded
decisions, given the anchor was not also rewritten". Never say "immutable" or
"append-only". Closing this properly needs the anchor somewhere the writer does not own:
a commit, a signature, or a second machine.

## The fabrication guard catches invented magnitudes, not wrong units

`_fabricated()` flags any number in the model's output that appears nowhere in its input.
The rule is deliberately not "no digits", because quoting a figure from the belief's own
claim text is quotation rather than invention.

Verified behaviour, given an input containing `-14.5` and `10.4`:

| Model output | Flagged |
|---|---|
| "The gap is 47.2 months" | yes, caught |
| "The funding gap is -14.5 **years**" | no |
| "The shortfall is 14.5 **million dollars**" | no |
| "Runway fell 10.4**%**" | no |
| "The gap is roughly **fourteen** months" | no |
| "Runway ends about **twice as long** as assumed" | no |

So a correct magnitude wearing the wrong unit, scale, or sign passes, as does any
quantitative claim expressed in words. The guard bounds invention. It does not bound
misuse of a number it was legitimately given, and it cannot see numbers that are not
digits.

Stronger versions, in increasing cost: normalise Unicode and detect number words before
scanning; require quoted figures to carry the unit and entity from a single contiguous
source span; or forbid quantitative expressions in generated prose entirely and render
every figure from the application.

## The provenance test detects unintended displayed literals

It parses rendered HTML, extracts every number-like token from text nodes, and asserts
each appears in `data/snapshot.json`. It caught a planted `9999` and a template-computed
value, both watched failing.

What it does not establish:

- **Substring, not equality.** `"%.3f"` of `-0.5913757700205339` renders `-0.591`, a
  literal prefix of the stored value, and passes.
- **Text nodes only.** SVG coordinates, stroke widths and other attribute values are never
  examined. This is deliberate, since geometry is not a claim about the world.
- **Presence, not correspondence.** A number can be real, present in the snapshot, and
  attached to the wrong row, field, unit or sign. The check cannot tell.
- **Rendering fidelity is unproven.** Verified by mutation: setting `prior_gap_months` to
  `99.9` while the page still displayed `8.4` left every test green, as did setting
  `runway.cash` to `1.0` while the page still displayed `$50M`.

The upgrade is per-element binding: every semantic figure carries the record and field
path it came from, and the test resolves that path and asserts the formatter's exact
output. Global substring matching then stays as defence in depth.

## Lapsed-versus-future is decided at build time, and the date is now pinned

`build()` splits pivotal trials on `date.today()` unless an `as_of` is passed. Two
consequences:

- A committed snapshot's classification is a statement about the day it was built. Rebuild
  it later and rows can move from future to lapsed without any source data changing.
- Equality is not pinned. A completion date falling exactly on the build date currently
  counts as future, by `>=`, and that choice is incidental rather than argued.

Month-only registry dates (`2028-04`) are parsed to the first of the month, which is the
conservative direction, but it is a parser default doing policy work.

**Half closed.** The snapshot now carries its own `as_of`, written once by
`apply_displays()` and never re-read from the clock, and everything derived from it reads
that field. The thesis-break timeline's "today" marker is that pinned date, so a committed
snapshot draws the same picture next year that it draws today, and a test asserts the two
agree. What is still open is the split itself: `build()` is called during a rebuild, which
needs credentials and a network, and it is that call that still reads the wall clock. So
the file no longer reinterprets itself on read, and a rebuild still reclassifies.

## The derivation names a record; nothing resolves it

Each row of the funding-gap table now carries the record it came from: an XBRL tag with
the CIK and filing date, or a numbered ClinicalTrials.gov version with the date the
sponsor submitted it. That is a real improvement over "this number is in the snapshot
somewhere", and it is less than it looks.

The test asserts that a row claiming a tag carries a non-empty record string. It does not
fetch the filing, resolve the tag, or check that the value on that record equals the value
in the row. The record is an assertion the builder makes about itself. A row that named
the wrong version would pass every check here.

The two things that are checked, and were watched failing:

- the result row equals the contract's own `gap_months_1f` (mutated the timeline's gap to
  `-99.9`, three tests failed)
- every rendered figure is a substring of the snapshot (planted `8888` in the derivation
  partial and in an SVG label; the provenance test named both)

The upgrade is the same one the provenance section already names: resolve the record and
assert the formatter's exact output against the field it claims.

## The timeline is drawn from the snapshot, and its geometry is unchecked

The thesis-break timeline recomputes the exhaustion date and the lapsed-anchor gap from
raw fields rather than copying the contract's strings, on purpose: an independent
recomputation that disagrees is a defect worth catching, and a test asserts the agreement.
That test caught a mutated gap.

Not checked: whether the picture is legible. Marker x positions are asserted to fall
inside the axis, and nothing more. Two markers a few days apart overlap, their labels
collide, and every test stays green. On RCKT the filing and lapsed markers sit 39px apart
and are readable only because they were given different label rows by hand. A contract
whose dates cluster differently will draw badly and say nothing about it.

## The queue is a second opinion, and shows only what one snapshot can say

The monitoring queue is a second computation over the same contracts, so it can disagree
with the first one. Two checks exist to make that disagreement loud rather than quiet: its
breach and lapse counts must equal the command bar's, which reaches them by a different
route (`verdict` versus the sign of `gap_months`), and every contract in the snapshot must
appear in it. Both were watched failing.

What it deliberately does not have:

- **No "newly", and no "since last week".** Every such state is a comparison against a
  previous look, and there is one committed snapshot with nothing to diff against. The
  first version of the state list said "newly breached" and could not have known. A test
  now rejects `newly`, `since last` and `moved since` in any state label, and the page
  states the absence rather than leaving it to be noticed.
- **No changed-SEC-tag-path state**, for the same reason. `Runway.provenance` records which
  tag each figure resolved through, so the check becomes possible the moment a second
  snapshot exists, and it does not exist yet.

One defect it shipped with, found by looking at the page rather than by a test: rows whose
burn estimate is unreliable printed a gap figure beside "burn estimate unreliable". No
column called it a rank, and the existing no-rank test passed on it, because that test
looks for a plain-integer rank cell on `/contracts`. Printing `2.6 mo` next to a row the
system says is not rankable ranks it in the reader's head anyway.

The interesting part is the test, not the bug. `test_srpt_has_no_rank_number` was checking
one page for one shape of violation, so the rule it was supposed to protect could be broken
somewhere else and stay green. Confirmed rather than assumed: adding a gap column to the
flagged table on `/contracts` still passes it today. The rule is now stated once and
checked over every page that lists contracts, and the narrow test is kept as defence in
depth rather than replaced.

A second check was hollow the same way. The number-provenance test ran over four routes,
all of which render a negative funding gap, so the positive branch of the derivation
partial was never on a tested page. A literal planted in that branch went undetected, and
was briefly mistaken for a limit of the provenance check itself. It was not: the branch was
simply never rendered. `/contract/BEAM` is now in the parametrize because BEAM is the only
reliable contract with a positive gap, and the same planted literal now fails.

Both are the same lesson, which is the lesson this whole file exists for: a check that has
only ever been watched passing on the one case it was written for is not yet evidence.

The threshold for "approaching breach" is six months. That is a judgement, not a finding:
a quarter is too tight to act on and a year is not news. Nothing validates it.

## The reported slip figures were not established, and five of seven still are not

This is the largest thing an audit of this project has found, and it was found by a guard
this project built to catch exactly it.

`total_slip_days` is computed by subtracting registered completion dates across successive
registry versions. That is only a delay if both dates describe the same commitment. Until
`engine/promise.py` existed, nothing checked, because the fetcher reads each version's
status module for the date and never read the endpoint or the enrolment, which were
sitting unread in the same cached response.

Applying promise identity to the committed snapshot:

| Trial | Reported | Established | Refused |
|---|---|---|---|
| PRME NCT06559176 | 122 | 122 | 0 |
| BEAM NCT05885464 | -1826 | -1826 | 0 |
| RCKT NCT06092034 | 943 | 0 | 1 |
| RCKT NCT04248439 | 1008 | -422 | 1 |
| SRPT NCT03992430 | 760 | 33 | 2 |
| SRPT NCT06246513 | 32 | -27 | 1 |
| SRPT NCT06128564 | -2463 | -1031 | 1 |

The clearest case is `NCT04248439`. Of its 1,008 reported days, a single revision
contributes +1,430 -- and at that revision the primary endpoint changed from "Phenotypic
correction of bone marrow colony forming units after infusion of RP-L102" to "Bone Marrow
Colony-Forming Cell Mitomycin-C resistance". Those are different endpoints, so those are
different promises, so that is not slip. The supported figure is -422 days across the two
revisions where the commitment held its shape.

**What this does not touch, stated plainly so the finding is not read as bigger than it
is.** The 677-day expired-date result is about one version carrying an already-passed
date, not a comparison across two commitments, and is unaffected. The funding gap is
computed from the current registered date against the runway, not from slip, and is
unaffected. What is affected is every sentence in this repo that quoted a net-slip number
as though it were a measured delay.

Both figures are now shown wherever either was, the non-comparable revisions carry an
amber ring on the timeline, and `tests/test_promise.py` pins the numbers above so a doc
cannot quote a figure the code no longer produces.

**The residual limit.** Establishing continuity needs `data/cache/`, which is gitignored,
so the classification is computed at build time and committed. A revision whose version is
not cached classifies as uncertain and produces no number, which is the correct answer for
a version nobody has read. Three dimensions are compared -- phase, primary outcome,
enrolment -- and a sponsor can change what a trial is measuring in ways none of them
capture. The guard bounds one failure. It does not certify continuity.

## Untested, and known to be

- ~~The decision receipt's two hashes.~~ Closed. The receipt used to travel in the query
  string and a hand-written URL could forge every field; it is now read from the ledger's
  last entry at render time, with a test that requests the page carrying forged values and
  asserts the real ones render.
- Whether a rebuild is reproducible. Nothing asserts that building twice from the same
  inputs produces the same bytes, so a hand-edited snapshot would not be detected.
- Concurrency anywhere. Two decisions appended at once are untested; the ledger has no
  compare-and-swap on the head. This applies to the analyst belief form too: two analysts
  confirming at the same moment both read the same head hash and both append.
- Whether a belief written through the form is ever monitored. `POST /belief/new` appends
  a real CREATE entry to the real chain, and the redline loop still runs off the committed
  snapshot rather than off the ledger's live cards. So the form records a belief, and
  nothing yet re-reads it on the next rebuild. Say "records a belief", never "starts
  monitoring it", which is what the button used to imply.

## Where these came from

The first four sections were produced by a three-model adversarial review (Claude, Cursor,
Codex) asked specifically which existing checks were hollow, and then every claim it made
was run against the code before being written down here. Two of its predictions were
right, verified above. The transcript is in `runtime/council/` in the vault repo.
