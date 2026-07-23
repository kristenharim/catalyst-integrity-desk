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
| `/queue` | unchanged | serves the queue rows |
| `/redline` | unchanged | serves the pending challenge |
| `/contracts`, `/contract/<ticker>` | unchanged | list and detail |
| `/belief/new`, `/workspace` | unchanged | belief entry and intake |

Intended structure, to be built in Phase 2:

```text
/                          Decision Inbox
/demo                      deterministic Rocket demonstration
/decisions                 decision portfolio
/decisions/<card_id>/review    decision review
/receipts/<entry_id>       Decision Integrity Receipt
/evidence/<contract_id>    Evidence Explorer
/activity                  decision history
```

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

A belief written through the form is recorded and not yet watched. The redline loop runs
off the committed snapshot and does not read the ledger's live cards, so a new card is
picked up at the next rebuild rather than immediately, and the interface says so.

## Phase 2 direction

Not started.

- Figma is the interaction-design source of truth.
- IBM Carbon is the visual and accessibility grammar.
- Flask and Jinja remain the authoritative renderer. No React rewrite.
- HTMX only later, for bounded server-driven interactions.
- A server-rendered `/_components` gallery.
- Playwright screenshot tests and axe-core accessibility checks.
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
