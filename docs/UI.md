# UI: decision inbox and evidence contract

The contract for the interface work. Phase 1 (the state architecture) is built and
committed. Everything under "Phase 2" below is specification, not code, and no page
template for it exists yet.

The product should read like IBM Carbon, GitHub pull requests, and an audit workpaper. It
should not read like a futuristic AI terminal.

## The three state axes

Built. A decision carries three states that fail independently and are never collapsed
into one badge.

| Axis | Values | Computed where | Source |
|---|---|---|---|
| Evidence | `intact`, `review_required`, `contingent`, `unavailable` | build time, into the snapshot | `console/states.py` |
| Workflow | `unrecorded`, `open`, `in_review`, `deferred`, `resolved`, `retired` | request time | `console/review.py` |
| Record integrity | `intact`, `tampered`, `truncated` | request time | `orchestrator/anchor.py` |

`console/states.py` imports nothing from `engine.ledger` or `orchestrator.anchor`, and a
test parses its import graph to keep it that way. A tampered ledger must never be able to
render as a broken thesis.

Two values in the workflow vocabulary are declared and never returned. `in_review` and
`deferred` describe a human picking a task up or pushing it out, and nothing stores either
fact. They are named so templates and tests share one vocabulary, and synthesising them
from a snapshot would fabricate a workflow that does not exist.

There is no fourth record state. A missing anchor is folded into `truncated` by
`anchor.check`, so an `anchor_unavailable` label would have nothing behind it.

### Evidence precedence, and why ordering differs

```text
required evidence or identity missing        -> unavailable
else deterministic approved condition failed -> review_required
else comparison needs semantic judgment      -> contingent
else                                         -> intact
```

Deterministic failure outranks contingent. Rocket reads `review_required` with its
contingent trigger listed beneath rather than replacing it.

Reading order is a different question and uses a different ranking. `INBOX_RANK` puts
`review_required` first and `unavailable` third, because an unavailable row needs its data
fixed and cannot be acted on today, while a breached one needs a judgement now. Ranking
`unavailable` first put a row nobody can act on above the one that broke.

Approaching a threshold is a `watch` trigger and forces `intact`. The contract still holds,
so the badge may not say it broke; the trigger stays visible underneath.

## Routes

Current status as of the Phase 1 commit.

| Route | Status | Behaviour |
|---|---|---|
| `/` | unchanged | redirects to `/contract/RCKT` |
| `/demo` | added | redirects to `/contract/RCKT`, deterministically |
| `/inbox` | added | the decision inbox, one item per decision, triggers grouped |
| `/receipts/<entry_id>` | added | the decision integrity receipt for one ledger entry |
| `/decisions/<card_id>/review` | added | one decision read end to end; adjudication for the one challenge, evidence only for the rest |
| `/activity` | added | the decision history: ledger events and review-log rejections, in the order the record holds them |
| `/queue` | unchanged | serves the queue rows |
| `/redline` | unchanged | serves the pending challenge |
| `/contracts`, `/contract/<ticker>` | unchanged | list and detail |
| `/belief/new`, `/workspace` | unchanged | belief entry and intake |

Intended structure. The first five are built; the rest are Phase 2 work not yet done:

```text
/inbox                     Decision Inbox                          built
/demo                      deterministic Rocket demonstration      built
/receipts/<entry_id>       Decision Integrity Receipt              built
/decisions/<card_id>/review    Decision Review                     built
/activity                  decision history                        built
/decisions                 decision portfolio
/evidence/<contract_id>    Evidence Explorer
```

A decision is addressed by the id of the belief card recorded for it, and by the ticker
when no belief is recorded. Exactly one challenge exists and it is written in Python inside
`make_snapshot.py`, so every other decision has no card id to carry, and minting one would
put an identifier on screen that names no record. `review.card_ticker` reads both shapes,
which is why they share a route. The Inbox's one action per item leads there under both of
its labels, Adjudicate for the challenge and Review evidence for the rest, and `/redline`
is unchanged: it is where docs/DEMO.md sends the room, and a second door onto one challenge
is only safe while the first one still opens.

The inbox is at `/inbox` and not at `/`. The root redirect to the Rocket detail is
documented in README.md as the demo's opening frame and measured at 1280x800 by
`tests/test_demo_frame.py`. Moving the front door would falsify a claim the submission
makes about itself, and the inbox needs no help from the address to be found.
`/redline/confirm` keeps rendering the receipt for the decision just taken;
`/receipts/<entry_id>` is the addressable form of the same record, selected by the entry's
own hash. Both compose the receipt through one function, so they cannot describe the same
entry differently. The confirm page links to that address, using the hash of the receipt it
already rendered, so the link is the same selection by `card_id` rather than a second path
to the same fact and a later unrelated write cannot move it. The link exists only where the
receipt does: nothing to link to before a ruling, and nothing after a rejection, which
writes to the review log and not to the ledger.

Legacy routes may redirect once the destinations render. They are not removed until
compatibility tests exist.

`/demo` stays deterministic and must not depend on Rocket sorting first in the Inbox. A
recorded presentation that relies on sort order is one snapshot away from opening on the
wrong company.

## UI invariants

These hold for every screen.

- One Inbox item per decision, with its triggers grouped beneath it. Never one row per
  trigger.
- Evidence state, workflow state and record integrity never collapse into one indicator.
- Evidence state is not conveyed through colour alone.
- "Comparison refused" is visually more prominent than the number it refuses.
- Record integrity stays quiet unless it fails.
- No arithmetic in templates. Every displayed figure is a pre-formatted snapshot field, so
  it appears verbatim in the JSON.
- One primary action per card.
- Technical evidence uses progressive disclosure.
- Missing provenance renders as unresolved, never as a guessed link.
- A receipt exists only after a human action.
- "Record decision" is allowed. "Start monitoring" is not, until the reconciliation loop
  exists.
- The screen distinguishes decisions a human recorded from states computed from the frozen
  snapshot.

### Recorded is not monitored

Persisted: belief cards, human decisions, ledger events, receipts, rationales.

Computed from the frozen snapshot: inbox rows, evidence states, triggers, current
contract, provenance chain, dependency map.

A belief written through the form is recorded and not yet watched. Nothing rereads it.
`console/make_snapshot.py` contains no reference to `BeliefLedger` or `decisions.jsonl`, so
no rebuild picks a card up, and the one belief the system challenges is written in Python
at `make_snapshot.py`. Acting on a recorded belief stays a human's job until the
reconciliation loop is built, and the interface says exactly that.

The precise capability today: **recorded** yes, **projected from the frozen snapshot** yes,
**manually rebuildable** no for beliefs, **automatically monitored** no.

## Phase 2 direction

Specified in `docs/plans/phase2-inbox-spec.md`, which maps every proposed element to the
backend field that feeds it and lists in its section 8 the elements nothing feeds. Four
screens of it are built: the Decision Inbox with its empty state, the Decision Integrity
Receipt with its tampered and truncated states, the Decision Review with its
adjudication, evidence-only, contingent, refused and unavailable states, and the Activity
history with its empty, tampered and truncated states. The rest is not started.

Activity answers one question and stays inside it: what decisions were recorded, reviewed,
changed or retired, and in what order. It is decision history and not evidence-change
history, and it says so on the page, because there are no historical evidence runs here to
be a history of. Every row is one entry in the decision record; a rejection appears as a row
with no entry hash and no receipt, because it writes to the review log and leaves the ledger
untouched. The one challenge the snapshot carries is a computed state rather than something
a human did, and it is not rendered here at all. The list is oldest to newest and says so
above itself; no sorting control is offered, because this page cannot reorder anything.

Timestamps on Activity and on the receipt are both composed by `review.ts_display`, which
returns a display state rather than a string. The card the approve path seeds carries
`ts=0.0`, a marker rather than a moment, and it now reads "Seeded baseline / Original
timestamp unavailable" instead of a date in 1970. The stored entry is unchanged: the
interpretation is in the projection, and the templates render the label and the note they
are given rather than deciding for themselves what a zero means.

The Decision Review reads in one order at every width: what changed, why that needs a
human, the approved belief, the current contract, then the evidence under all four. Above
1024px the three panels are placed into a 25/45/30 row without moving in the markup, so the
centre panel is the widest thing on the page and a screen reader still travels the argument
in the order it is argued. The deterministic account sits above the Granite memo, never
below it. A decision with no challenge behind it renders no control at all, disabled ones
included, and offers the way back to the evidence instead.

- No Figma file exists. The specification is the interaction-design source of truth, and
  it says so and why.
- IBM Carbon is the visual and accessibility grammar. The g100 tokens are declared as CSS
  custom properties in `base.html`; no Carbon package is installed and nothing is fetched
  at render time.
- Flask and Jinja remain the authoritative renderer. No React rewrite.
- HTMX only later, for bounded server-driven interactions.
- A server-rendered `/_components` gallery.
- Playwright screenshot tests and axe-core accessibility checks. Built for the Phase 2
  decision spine in `tests/test_inbox_receipt.py`: the inbox, the receipt, the redline and
  the confirmation. axe-core is installed rather than vendored, and the scan is skipped when
  the browser or the axe source is absent. `npm run test:a11y` is the command that requires
  it instead, and which pages are scanned is keyed on the `url_map`, so a new screen has to
  be scanned or named as out of scope before the suite passes. The Phase 1 screens are named
  as out of scope, which is a gap in coverage rather than a statement that they pass.
- IBM Bob for one bounded component at a time.

### Components to design before any page template

Decision Inbox, empty Inbox, Decision Review, multiple-trigger review item, contingent
adjudication, refused comparison, Evidence Explorer, Decision Integrity Receipt, tampered
record, truncated or replaced record, unavailable evidence, long thesis text, mobile
layout.

Each needs: default, hover, keyboard focus, selected, loading, empty, unavailable, error,
contingent, refused, tampered.

The edge states are the product, not secondary polish. A screen that only looks right when
the evidence is clean is a screen that hides its hard cases.
