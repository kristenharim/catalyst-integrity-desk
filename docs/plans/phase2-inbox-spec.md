# Phase 2 — Decision Inbox UI foundation: interaction and design specification

Status: specification only. No production template, CSS, route, or JavaScript is
written or changed by this document. Nothing here modifies a frozen artifact. This is the
document a designer would build the Figma from and an engineer would build the templates
from, grounded field-by-field in the backend that already exists at HEAD
`9e70920` (`pre-phase2-stable`).

The Figma MCP in the authoring session was unauthenticated, so no Figma file was created.
This markdown is the source-of-truth artifact instead: structured, complete, and mapped to
real backend fields. When a Figma is built, it is built from section 7 (the mapping table),
not from imagination.

## What is already built, and what this specifies

Phase 1 built the state architecture and the four current views. The evidence axis is
computed at build time into `data/snapshot.json` (`console/states.py`); the workflow and
record axes are computed at request time (`console/review.py`, `orchestrator/anchor.py`).
The Decision Inbox machinery itself already exists in the backend and is wired to **no
route**: `review.build_tasks()` returns one task per decision, worst first, with triggers
grouped; `review.open_tasks()` filters it; `review.ReviewTask` is the row model. Phase 2 is
the UI foundation that surfaces those functions, plus the receipt/activity/evidence views
around them. This spec does **not** build reconciliation of recorded beliefs, scheduled
refresh, notifications, persistent assignment or due dates, auth, private-document
ingestion, or any new evidence source. Where a required screen would need one of those, it
is listed in section 8, not invented.

### Permanent boundaries this spec encodes (from CLAUDE.md and docs/UI.md)

- Three axes — evidence, workflow, record integrity — stay on separate wires and never
  collapse into one badge. `console/states.py` imports nothing from `engine.ledger` or
  `orchestrator.anchor`; `tests/test_layering.py` enforces it.
- One Inbox item per decision, triggers grouped beneath it. Never one row per trigger.
- No arithmetic in templates. Every number is a pre-formatted snapshot field and appears
  verbatim in the JSON (`tests/test_prose_figures.py`, `test_console.py`).
- Model prose stays non-quantitative. Refused values never render as established. Missing
  evidence renders as unavailable/unknown, never as a guessed value.
- Newly recorded beliefs are described as **recorded**, not monitored. "Record decision" is
  allowed; "Start monitoring" is not, until the reconciliation loop exists.
- `/demo` stays deterministic and independent of Inbox sort order.
- The retired `redline.no_amendment_filed` key stays unread. The receipt/reconciliation UI
  reads the derived `registry_reconciliation` state from `console/review.py` instead.

---

## 1. Screen inventory

| # | Screen | Route (status) | Purpose |
|---|---|---|---|
| S1 | Decision Inbox | `/` (proposed; today redirects to `/contract/RCKT`) | This morning's work: one row per decision that needs a human, worst first, triggers grouped. Backed by `review.build_tasks` / `open_tasks`. |
| S1e | Empty Inbox | `/` when `open_tasks` is empty | Confirms nothing is open without implying the desk is watching. |
| S2 | Demo landing | `/demo` (built) | Deterministic Rocket demonstration; redirects to `/contract/RCKT`, never depends on Inbox sort. Unchanged. |
| S3 | Decisions portfolio | `/decisions` (proposed) | All decisions with a trigger, open and resolved and retired, as a table. Backed by `review.build_tasks` (which retains retired via `_latest_cards`). |
| S4 | Decision Review | `/decisions/<card_id>/review` (proposed; today the single pending redline is `/redline`) | The adjudication surface: the breach story, the derivation drawer, the Granite memo, the analyst claim redline, and the accept/reject form. Fully backed only for the one pending redline (RCKT); see section 8. |
| S4m | Multiple-trigger review item | S4 / S1 state | A decision carrying more than one trigger (RCKT carries three). Rendered as grouped trigger rows under one item, precedence badge on top. |
| S4c | Contingent adjudication | S4 state | A `contingent` evidence state (endpoint reworded / comparison refused). The refused magnitude is shown and marked not-comparable; the number is visually subordinate to the refusal. Display backed; the *act* of adjudicating is unbacked (section 8). |
| S4r | Refused comparison | S4 / detail state | `comparison_refused` trigger and `slip_refused_revisions`: reported movement shown struck as refused, "Do not treat as delay." Backed. |
| S4u | Unavailable / unknown evidence | S4 / S1 state | `unavailable` evidence state (SRPT: unreliable burn) and `registry_reconciliation == unknown`. Rendered as unavailable, shown, never ranked. Backed. |
| S5 | Decision Integrity Receipt | `/receipts/<entry_id>` (proposed; today `/redline/confirm`) | Who decided, what changed, thesis state, prev/entry hash, and the record-integrity badge. Backed by ledger entries + `anchor.check`. |
| S5t | Tampered record state | S5 state | `integrity_status == "tampered"`: a hashed byte was edited. Backed by `anchor.check`. |
| S5x | Truncated / replaced record state | S5 state | `integrity_status == "truncated"`: chain verifies but disagrees with the anchor, or anchor missing. Backed. |
| S6 | Activity history | `/activity` (proposed) | Reverse-chronological ledger events (`CREATE`/`UPDATE`/`RETIRE`) and review-log rejections. Backed by `ledger._entries()` + `ReviewLog.all()`. |
| S7 | Evidence Explorer (narrow) | `/evidence/<contract_id>` (proposed; today folded into `/contract/<ticker>`) | The provenance surface for one contract: derivation table, runway provenance, revision timeline. Backed by `contract.derivation`, `runway.provenance`, `history.revisions`. |
| S8 | Component gallery | `/_components` (proposed) | Server-rendered gallery of every component in every state, from fixtures. No live data needed by design. |
| S9 | Contract detail | `/contract/<ticker>` (built) | The demo centrepiece: lapsed-date timeline, thesis-break SVG, derivation. Unchanged; extended visually, not replaced. |
| S10 | Contract list | `/contracts` (built) | Ranked reliable, flagged-not-ranked, unresolved. Unchanged. |
| S11 | Queue (legacy) | `/queue` (built) | Per-reason rows. Redirect target once `/` becomes the Inbox; kept until compatibility tests exist. |
| S12 | Belief entry | `/belief/new` (built) | Analyst writes a thesis, trial, and floor gap; recorded to the ledger. Unchanged. |
| S13 | Workspace intake | `/workspace` + `/discover`/`/select`/`/approve` (built) | Ticker in, recorded contract out, through the evidence seam. Unchanged. |

Mobile variants (section 5) are not separate screens; they are responsive states of S1,
S4, S5, S7, S9.

Legacy routes (`/queue`, `/contract/<ticker>` as list-entry) redirect only once the new
destinations render, and are not removed until compatibility tests exist (docs/UI.md).

---

## 2. Component inventory

Each component names its Carbon basis. Carbon is the grammar (tokens, type scale, grid,
focus, contrast); no Carbon library is imported — tokens are declared in CSS (section 6).

| Component | Carbon basis | Used on | Notes |
|---|---|---|---|
| C1 Command bar | Carbon UI shell header + tabular figure | all (base.html context processor) | `snapshot_cmd_bar`: monitored / active_breaches / lapsed_expectations. Already built; migrate colors to Carbon support tokens. |
| C2 Global nav | Carbon UI Shell side/top nav | all | Workspace / Queue / Contracts / Pending Redline / New Belief; add Inbox, Decisions, Activity. |
| C3 Decision Inbox item | Carbon `Tile` (expandable) + `StructuredList` | S1, S3 | One decision. Header: ticker, company, evidence badge, worst-severity, gap. Body: grouped trigger rows. One primary action. Never one tile per trigger. |
| C4 Evidence badge | Carbon `Tag` (status variants) | S1, S3, S4, S9 | Evidence axis only: `intact` / `review_required` / `contingent` / `unavailable`. Never conveys state by colour alone — always a text label + icon. |
| C5 Trigger row | Carbon `StructuredListRow` | inside C3, S4 | `kind` label, severity, and the finished `detail` sentence. Contingent/refused rows carry the not-comparable treatment (C11). |
| C6 Record-integrity badge | Carbon `InlineNotification` / `Tag` | S5, S5t, S5x, and any decision surface that reads the ledger | `intact` (quiet) / `tampered` / `truncated`. Stays quiet unless `failed`. Distinct wire from C4 — never merged. |
| C7 Workflow-state chip | Carbon `Tag` (subtle) | S1, S3, S6 | `unrecorded` / `open` / `resolved` / `retired`. `in_review` and `deferred` exist in the vocabulary but are never rendered (not computable). |
| C8 Derivation table | Carbon `DataTable` (static) | S4, S7, S9 | Existing `_derivation.html`. Step / value / source (tag vs note vs calc vs result) / record. No arithmetic. |
| C9 Provenance tag | Carbon `Tag` (`gray`) | C8, timelines | An XBRL tag name or a numbered registry version. Missing provenance renders as an unresolved note, never a guessed link. |
| C10 Revision timeline (SVG) | Carbon data-vis palette, hand-rolled SVG | S4, S7, S9 | Coordinates precomputed as `svg_x`. Carried-expired node lifted + red; wording-only ring amber; not-comparable ring red. `role="img"` + `aria-label`. |
| C11 Refused / not-comparable marker | Carbon `Tag` (`red`/`magenta`) + strikethrough | S4c, S4r, C5, C10 | The refusal is visually **more prominent** than the number it refuses (UI invariant). |
| C12 Thesis-break panel (SVG) | Carbon data-vis, hand-rolled SVG | S4, S9 | Cash bar vs registered dates on one axis; `thesis_timeline`. Every label precomputed. |
| C13 Three-column breach story | Carbon `Grid` (3-col) | S4 | Thesis-as-approved / What-changed / Thesis-status. Existing `redline.html`. |
| C14 Granite memo card | Carbon `Tile` + info accent | S4 | `without_model_confidence(memo)`. Accent = Granite provenance; carries no model number. |
| C15 Reconciliation statement | Carbon `InlineNotification` (info/warning) | S4, S5 | Three sentences from `registry_reconciliation`: no-later-version / reconciled / unknown. The unknown case is rendered, not hidden. |
| C16 Decision form | Carbon `Form` + `Button` (primary/danger) | S4 | Accept (primary) / Reject (danger) + optional reason. One primary action per card. |
| C17 Receipt panel | Carbon `Tile` + `DataTable` | S5 | Author / timestamp / card / what-changed / thesis-state, then prev-hash / entry-hash. |
| C18 Hash-chain strip | Carbon breadcrumb-style row | S5 | observation → Granite memo → human decision → hash verified/FAILED/replaced. |
| C19 Empty state | Carbon empty-state pattern | S1e, S6 empty | "No decisions are open" without asserting active monitoring. |
| C20 Unresolved row | Carbon `DataTable` (notice) | S10 | Requested ticker, no contract, with reason. Shown, never dropped. |
| C21 Progressive disclosure drawer | Carbon `Accordion` / native `<details>` | S4, S7, S9 | Technical evidence hidden by default; the derivation opens under the headline figure. Native `<details>`, no script. |
| C22 Long-thesis text block | Carbon `body-long` type token | S4, S12 | A claim paragraph that may be several hundred characters; wraps, never truncates silently. |

---

## 3. State matrix

Every required screen crossed with the states it must render. "Backed" = a real snapshot
field or request-time function produces it today; "Unbacked" = section 8. The four
committed contracts supply a natural coverage set:

- **PRME** — `review_required`, reliable, gap −35.6, **one** trigger (funding_threshold_crossed): the single-trigger breach.
- **RCKT** — `review_required`, reliable, gap −14.5, **three** triggers (crossed, expired, comparison_refused): multiple-trigger + contingent, and the one pending redline.
- **BEAM** — `intact`, reliable, gap +20.2, **zero** triggers: healthy; absent from the Inbox (`build_tasks` skips no-trigger contracts).
- **SRPT** — `unavailable`, unreliable burn, gap 2.6 (not rankable), triggers incl. runway_unreliable + two expired + refused: the unavailable row.

| Screen \ State | Loaded | Empty | Multiple-trigger | Contingent | Refused | Unavailable / unknown | Tampered | Truncated |
|---|---|---|---|---|---|---|---|---|
| S1 Inbox | PRME/RCKT/SRPT rows, worst first (backed) | S1e when `open_tasks==[]` (backed) | RCKT: 3 grouped triggers (backed) | RCKT contingent trigger listed under review_required (backed) | RCKT `comparison_refused` row (backed) | SRPT `unavailable` row, shown never ranked, `gap_1f=None` (backed) | n/a (record axis not on Inbox rows unless a card exists; C6 shown per row only when a ledger card is present) | n/a |
| S3 Portfolio | all triggered decisions incl. resolved/retired (backed) | none-triggered → empty table (backed) | RCKT (backed) | RCKT (backed) | RCKT/SRPT (backed) | SRPT (backed) | via C6 when a card exists (backed) | via C6 (backed) |
| S4 Review | RCKT full breach story + memo + form (backed) | no pending redline → "nothing to adjudicate" (backed by absence) | RCKT 3 triggers (backed) | endpoint-continuity / refused; refusal dominant (display backed; resolve action **unbacked**) | RCKT `slip_refused_revisions` (backed) | `registry_reconciliation==unknown` sentence rendered (backed); non-RCKT review is evidence-only (**unbacked** challenge) | C6 reads `record_integrity` at render (backed) | C6 (backed) |
| S5 Receipt | approve → full receipt (backed) | reject → verdict only, no hash panel (backed) | n/a | n/a | n/a | `what_changed` empty for non-breach entries (**partially unbacked**) | `integrity_status=="tampered"` (backed) | `integrity_status=="truncated"`, incl. missing anchor (backed) |
| S6 Activity | ledger events + rejections, newest first (backed) | no events → empty state (backed) | n/a | rejection with reason (backed) | n/a | n/a | a tampered chain still lists rows; C6 flags it (backed) | truncation reduces the list; C6 flags it (backed) |
| S7 Evidence Explorer | derivation + provenance + timeline (backed) | contract with no history → derivation only (backed) | n/a | wording-only ring on timeline (backed) | not-comparable ring + refused total (backed) | runway `notes`, unresolved provenance rendered as note (backed) | n/a (no ledger read here) | n/a |
| S9 Detail | RCKT lapsed timeline + thesis-break + derivation (backed) | contract w/o lapsed → no lapsed section (backed) | n/a | contingent slip block (backed) | refused slip block (backed) | runway `notes` (backed) | n/a | n/a |

Per docs/UI.md every component additionally specifies: default, hover, keyboard focus,
selected, loading, empty, unavailable, error, contingent, refused, tampered. The edge
states are the product, not polish.

---

## 4. Interaction flows

### 4.1 Inbox → Review → Receipt (the spine)

```
S1 Decision Inbox  (/)
  row = one decision, worst first (review.build_tasks / open_tasks)
  each row: evidence badge (C4) + worst severity + grouped triggers (C5)
        |
        |  click the decision's single primary action ("Review")
        v
S4 Decision Review  (/decisions/<card_id>/review ; today /redline for RCKT)
  three-column breach story (C13) + reconciliation statement (C15)
  + derivation drawer (C21/C8) + Granite memo (C14) + analyst-claim redline
        |
        |  Accept (primary)                 |  Reject (danger)
        v                                    v
  ledger.update -> version bump          review_log.append (belief stands)
  anchor_record(...)                     ledger untouched
        |                                    |
        v                                    v
S5 Receipt  (/receipts/<entry_id> ; today /redline/confirm?verdict=)
  record-integrity read FRESH at render (anchor.check), receipt built
  from the ledger's last entry FOR THIS card_id (not "whichever was last")
```

Branches, each real in the backend today:

- **Accept, ledger not yet seeded.** `/redline/decide` seeds the original approved card
  (`snapshot:seed`, ts 0.0) before the `update`, so version bumps from a real predecessor.
  The receipt shows `thesis_state = financing required before catalyst` when
  `expected_low < 0`, else `funded to catalyst`.
- **Reject.** Receipt renders verdict-only: no hash panel, no receipt table. The belief
  stands; nothing hash-chains. S5 must not imply a record was written.
- **Duplicate belief.** `ledger.create` raises `Conflict` (409). The form re-renders with
  "A belief for <ticker> on <nct> already exists. Retire it before writing a new one."
- **Concurrent accept.** `_append` reads the tail under an flock; the loser raises
  `Conflict` and appends nothing, so the chain never self-accuses of tampering.
- **Receipt identity.** The confirm handler selects the ledger entry by `card_id`, so
  recording another belief via `/belief/new` after an approval cannot make the receipt
  render a different card's hashes under this redline's summary
  (`tests/test_receipt_identity.py`).

### 4.2 Reconciliation statement (centre column of Review, S4/C15)

`review.registry_reconciliation(redline, contract, as_of)` returns exactly one of three
states, rendered as three distinct sentences:

- `no_later_registry_version_before_expiry` → "No later registry version reconciled the
  registered expectation before the date passed," with the trial and `as_of` named, and the
  explicit scope caveat (registry versions only; press wires and SEC filings were not
  queried).
- `reconciled_before_expiry` → "A later registry version moved the registered expectation
  before the date passed."
- `unknown` → "Registry reconciliation unavailable for <trial>: <why>." **Rendered, not
  hidden** — a screen that goes quiet when its evidence runs out reads exactly like one
  whose evidence held.

The retired `redline.no_amendment_filed` literal is never read; the sentence is derived
from committed version history at render time.

### 4.3 Tamper demonstration (S5 → S5t → S5x)

1. Accept a redline → S5 shows `✓ intact` (C6).
2. Edit one byte inside `data/decisions.jsonl`, reload → `anchor.check` returns
   `tampered`, badge and hash-chain strip flip to failed. (`verify()` recomputes the chain
   at render; it never trusts the redirect.)
3. Delete the last line, reload → `truncated`. The head hash / entry count disagree with
   `data/ledger.anchor` even though `verify()` still passes.
4. Delete the anchor too, reload → still `truncated` (a missing anchor with entries folds
   into truncated), so it never falsely reads intact.

### 4.4 Workspace and belief entry (unchanged, S12/S13)

- **Belief:** `/belief/new` form → review (shows what the desk computes against the belief)
  → commit (`ledger.create` + `anchor_record`) → done. Stages: `form` / `review` / `done`.
- **Workspace:** `/workspace` → `discover` (identity join + negatives shown *before* any
  candidate) → `select` (propose a contract; a lapsed date is refused at intake, 400) →
  `review` → `approve` (`ledger.create` + `anchor_record`) → done. Stages: `ticker` /
  `discover` / `review` / `done`. The analyst's edited wording wins over the proposal.

These record beliefs; nothing rereads them. The UI says "recorded," never "monitoring."

---

## 5. Responsive behavior

Carbon 16-column grid. Breakpoints follow Carbon: `sm` 320, `md` 672, `lg` 1056, `xlg`
1312, `max` 1584. The page body never scrolls horizontally; wide content (tables, SVG
timelines, hash strings) scrolls inside its own `overflow-x:auto` container (already the
pattern in `detail.html` and `_derivation.html`).

| Screen | Desktop (`lg`+) | Tablet (`md`) | Mobile (`sm`) |
|---|---|---|---|
| S1 Inbox | Full-width tiles; header row + grouped triggers inline; command bar horizontal | Tiles stack; trigger rows wrap; severity stays on the header line | Single column; evidence badge + gap on top line, triggers as a stacked list; command bar counts wrap to 2×2 |
| S4 Review | Three-column breach story (C13) side by side; memo + claim redline two-up | Breach story collapses to a single column, in reading order approved → changed → status; memo/claim stack | Same single column; derivation drawer closed by default; SVG panels scroll-x |
| S5 Receipt | Verdict + integrity badge on one row; receipt table + hash strip full width | Badge drops under verdict; hash strip wraps | Hashes `word-break:break-all`; hash-chain strip wraps to vertical |
| S7 Evidence Explorer | Derivation table + timeline stacked, both full width | unchanged, table scroll-x | timeline scroll-x, table scroll-x |
| S9 Detail | as built (1100–1220px SVGs in scroll containers) | scroll-x preserved | scroll-x; consequence panel full width |

The 677-day demo constraint holds at 1280×800: the carried-expired node sits red and
raised above the axis with the gap table below, no scrolling (`tests/test_demo_frame.py`).
The Inbox must not regress this — `/` at demo time still lands on `/contract/RCKT` via
`/demo`, which is deterministic and independent of Inbox sort.

---

## 6. Accessibility requirements

Carbon-grounded, and asserted by Playwright + axe-core (the spec says what gets asserted;
it does not write the tests).

### 6.1 Carbon tokens to declare (dark theme, current app is dark)

Migrate the ad-hoc GitHub-dark palette in `base.html` to Carbon Gray-100 tokens, preserving
the existing **semantic** colour meanings. Declared as CSS custom properties; no library
import.

| Semantic role (today) | Today's hex | Carbon token | Carbon g100 value |
|---|---|---|---|
| page background | `#0f1117` | `$background` | `#161616` |
| layer / card | `#161b22` | `$layer-01` | `#262626` |
| inset / code | `#0d1117` | `$layer-02` / `$field-01` | `#393939` |
| subtle border | `#30363d` / `#21262d` | `$border-subtle` | `#393939` |
| primary text | `#e6edf3` / `#c9d1d9` | `$text-primary` | `#f4f4f4` |
| secondary text | `#8b949e` | `$text-secondary` | `#c6c6c6` |
| healthy / funded (emerald) | `#10b981` | `$support-success` | `#42be65` |
| breach / integrity failure (red) | `#f85149` | `$support-error` | `#fa4d56` |
| contingent / lapsed (amber) | `#d29922` / `#f59e0b` | `$support-warning` | `#f1c21b` |
| Granite provenance (blue) | `#60a5fa` | `$support-info` | `#4589ff` |
| link | `#58a6ff` | `$link-primary` | `#78a9ff` |
| focus ring | (none explicit) | `$focus` | `#ffffff` (2px) |

Type: IBM Plex Sans for prose, IBM Plex Mono for figures/hashes/tags (the app is already
monospace-forward; keep mono for tabular numbers via `font-variant-numeric: tabular-nums`,
already used on `.cmd-bar-count`). Carbon type tokens: `heading-01`/`heading-03`,
`body-01`/`body-long-01`, `label-01`, `code-01`. Spacing: Carbon `$spacing-01..09` (2px
step scale) rather than raw px.

### 6.2 What axe-core asserts (per screen, per state)

- **Colour is never the only signal.** Evidence, workflow, and record states each carry a
  text label and an icon, not just a hue (UI invariant; axe `color-contrast` plus a
  structural assertion that each badge contains text).
- **Contrast.** All text ≥ Carbon AA (4.5:1 body, 3:1 large). Assert on every token pairing
  above, both the quiet (`intact`) and alarm (`tampered`) record states.
- **Landmarks and headings.** One `main`, nav as `nav`, heading order without skips. The
  command bar is a labelled region, not a bare `div` row.
- **Forms.** The decision form (C16) and belief/workspace forms have programmatic labels;
  Accept is the single primary; reason input has an associated `<label>`.
- **SVG.** Every timeline SVG has `role="img"` and a meaningful `aria-label` (already true
  for the thesis-break SVG; extend to revision timelines). Decorative strokes are
  `aria-hidden`.
- **No trap, full keyboard path.** Tab reaches every Inbox item, the disclosure drawer
  (native `<details>` is focusable), and both decision buttons; visible `$focus` ring on
  each.
- **`<details>` disclosure** is operable by keyboard and exposes expanded/collapsed state.

### 6.3 What Playwright asserts (regression grammar)

- The 677 demo frame at 1280×800: carried-expired node present, red, above the axis, gap
  table visible without scrolling (extends `test_demo_frame.py`).
- Provenance: every number rendered in the HTML appears verbatim in `snapshot.json`
  (extends `test_prose_figures.py` to the new routes — the same substring check that once
  caught a planted `9999`).
- Record-integrity states flip on file mutation: intact → tampered on a byte edit → truncated
  on a line delete, asserted through the rendered badge, not the function return.
- Reject renders no hash panel; approve renders exactly the ledger's last entry for that
  `card_id`.
- The reconciliation `unknown` sentence is present (not absent) when history cannot answer.

---

## 7. Mapping table — every UI element to its backend source

The core of this document. Every element names the existing field or function that feeds
it. Snapshot fields are in `data/snapshot.json` via `console/make_snapshot.py`;
request-time fields are computed in `console/review.py` / `orchestrator/anchor.py`; the
context processor in `console/app.py` injects `snapshot_cmd_bar`, `snapshot_id`,
`snapshot_as_of` into every template.

| UI element | Source (field / function) | Kind |
|---|---|---|
| Command bar: monitored / breaches / lapsed | `snapshot.cmd_bar.{monitored,active_breaches,lapsed_expectations}` (`make_snapshot._cmd_bar`) | build-time |
| Snapshot id in footer | `review.snapshot_digest(SNAPSHOT_PATH)` → `snapshot_id` | request-time |
| Snapshot as-of | `snapshot.as_of` → `snapshot_as_of` | build-time |
| **Inbox item (one per decision)** | `review.build_tasks(snapshot, ledger, review_log, snapshot_id)`; `review.open_tasks(...)` for the open subset | request-time |
| Inbox row: ticker / company | task `ticker`; `name` (from `contract.runway.name`) | build+request |
| Inbox row: evidence badge | `contract.decision.evidence` / `evidence_label` (`states.build_decision`) | build-time |
| Inbox row: worst severity | `contract.decision.severity` / `severity_rank` | build-time |
| Inbox row order (worst first) | `contract.decision.sort_key` = `[INBOX_RANK, SEVERITY_RANK, -n_triggers]`; `build_tasks` sorts by `(sort_key, ticker)` | build+request |
| Inbox row: gap | task `gap_1f` = `contract.gap_months_1f` when `runway.reliable` else `None` | build+request |
| Grouped trigger rows | `contract.decision.triggers[]` each `{kind,state,severity,detail,label}` (`states.build_triggers`) | build-time |
| Trigger count | `contract.decision.n_triggers` | build-time |
| Workflow-state chip | `review.workflow_state(card, resolved_at)` via `ReviewTask.state`/`label` (`unrecorded`/`open`/`resolved`/`retired`) | request-time |
| "Recorded" vs computed marker | `ReviewTask.recorded` (`card_id is not None`) | request-time |
| Task id | `ReviewTask.task_id = f"{ticker}:{snapshot_id[:12]}"` | request-time |
| **Evidence badge (C4)** | `contract.decision.evidence` ∈ {`intact`,`review_required`,`contingent`,`unavailable`} | build-time |
| **Record-integrity badge (C6)** | `review.record_integrity(ledger, anchor_path)` → `{state,label,failed}`, or `anchor.check` directly on S5 | request-time |
| **Reconciliation statement (C15)** | `review.registry_reconciliation(redline, contract, as_of)` → `{state,trial,expectation,as_of,why}` | request-time |
| Three-column breach story | `snapshot.redline.{prior_trial,prior_pcd,current_trial,current_pcd,proposed_card.claim}` | build-time |
| Funding gap at approval / now | `redline.lapse_display.{prior_gap_1f,current_gap_1f}` | build-time |
| Observed gap + band | `redline.breach.display.{observed_1f,expected_low_1f,expected_high_1f}` | build-time |
| Breach metric tag | `redline.breach.metric` | build-time |
| Classification label | `redline.classification.label`; source `redline.classification.source` | build-time |
| Granite memo (no model number) | `orchestrator.challenge.without_model_confidence(redline.memo)` | request-time |
| Analyst claim + proposed change | `redline.proposed_card.claim`; `redline.redline` (diff string) | build-time |
| Derivation table (C8) | `contract.derivation[]` each `{step,value,source,kind,record}` (`make_snapshot._derivation`) | build-time |
| Provenance tag (C9) | `runway.provenance` per figure; derivation `source` when `kind=="tag"` | build-time |
| Revision timeline node x | `history.revisions[].svg_x` (and `lapsed_history[].revisions[].svg_x`) | build-time |
| Carried-expired node | revision `carried_expired`, `days_expired` (patched from live `@property` in `_serialise_history`) | build-time |
| Wording-only / not-comparable ring | revision `transition` (`text_revised`), `slip_days is None` | build-time |
| Slip figures (established / contingent / refused / upper) | `history.slip_established_days`, `slip_contingent_days`, `slip_contingent_revisions`, `slip_refused_revisions`, `slip_upper_bound_days`, `slip_reported_days` | build-time |
| Thesis-break panel (C12) | `contract.thesis_timeline.*` (all coords + label strings precomputed) | build-time |
| Runway band | `runway.display.{months_low_1f,months_high_1f}` | build-time |
| Runway dollar figures | `runway.display.{cash_m,securities_m,liquidity_m,burn_*_annual_m}` | build-time |
| Flagged-not-ranked reason | `runway.reliable == False` + `runway.notes[]` | build-time |
| Unresolved rows (C20) | `snapshot.unresolved[]` `{ticker,name,reason}` | build-time |
| Queue rows/counts (legacy S11) | `snapshot.queue.{rows,counts,needs_attention}` | build-time |
| **Receipt (C17)** | ledger last entry for `redline.card_id`: `author`, `ts`, `card.card_id`, `prev_hash`, `entry_hash`; `what_changed` from `redline.breach.metric` + `classification.label`; `thesis_state` from `card.expected_low` sign | request-time |
| Hash-chain strip (C18) | `integrity_status` = `anchor.check(ledger, anchor_path)` | request-time |
| **Activity history (S6)** | `ledger._entries()` (CREATE/UPDATE/RETIRE, ts, author, triggered_by, reason, hashes) + `ReviewLog.all()` (rejections) | request-time |
| Belief form fields | `console.app._form_errors` / `_card_from_form` → `BeliefCard` | request-time |
| Workspace identity join | `intake.entity(snap)` (`state`, `explained`) | request-time |
| Workspace candidates | `intake.candidates(snap)` (`selectable`, `lapsed`, `slip_days`, `refused_revisions`, `transitions`) | request-time |
| Workspace monitorability rows | `intake._monitors(snap)` (`available` true/false + `why`) | request-time |
| Workspace negatives / missing | `intake.summary(snap)` (`negatives`, `missing`, `complete`, `sources`) | request-time |

---

## 8. Unbacked elements — proposed but lacking a real data source

Everything below is required by, or natural to, the screen list but has **no field or
function feeding it today**. None is invented into the UI; each names what it would need.
This is the Phase 2 / Phase 3 seam.

| Proposed element | Where it would appear | Why it is unbacked | What it would require |
|---|---|---|---|
| **Per-decision Review for a non-RCKT belief** | S4 for any card other than the one pending redline | Exactly one challenge exists, written in Python in `make_snapshot._build_rckt_redline`. `make_snapshot.py` never reads the ledger, so a recorded belief produces no breach, no Granite memo, no accept/reject-to-ledger. | The reconciliation loop: recompute a recorded belief's contract, `scan_breaches`, `build_challenge`. Explicitly Phase 3. Until then S4 for other rows is evidence-only (triggers + derivation), and the item's action is "Review evidence," not "Adjudicate." |
| **Contingent adjudication action** | S4c | The contingent *display* is backed (`slip_contingent_*`, `endpoint_continuity` trigger), but recording a human ruling that "these two endpoint descriptions name the same commitment" (which would move contingent days into established) has **no store**. | A ruling store keyed by trial + revision pair, plus a ledger event type. Not in Phase 2. Today the UI shows the contingent total and the two readings; it cannot resolve them. |
| **Task age / "opened N days ago"** | S1, S3 | `ReviewTask.opened_at` is `None` and stays `None` — a task opens when a trigger first fires, which needs two snapshots to compare, and there is only ever one. | A trigger-history store across snapshots (Phase 3 scheduled refresh). The UI shows no age. |
| **`in_review` / `deferred` workflow chips** | S1, S3 | Declared in `WORKFLOW_STATES` but not in `COMPUTABLE`; nothing stores a human picking a task up or deferring it. `workflow_state` never returns them. | Persistent assignment/defer store. Out of Phase 2 scope. Never render these two. |
| **Assignment (owner) / due date** | S1, S3 | No field anywhere. | Multi-user model + assignment store. Out of scope. |
| **`what_changed` for a non-breach receipt** | S5 for a `CREATE` (belief) or `RETIRE` entry | `what_changed` is composed from `redline.breach.metric` + `classification.label`, which only exist for the one challenge. A belief created via `/belief/new` has a receipt-able ledger entry but no breach to describe. | A per-event summary derived from the ledger entry's `event` + `card`, independent of the snapshot redline. Small, but not present today. |
| **Portfolio rows for intact, no-trigger contracts** | S3 | `build_tasks` skips contracts with no triggers (`if not triggers: continue`), so BEAM (intact, +20.2) appears on `/contracts` but never in the portfolio. A recorded belief on such a contract also would not surface. | Either iterate the ledger's cards directly, or emit a zero-trigger decision. A design choice for Phase 3; note it so the portfolio is not mistaken for "all beliefs." |
| **Notifications / unread markers** | S1, global | No event stream, no read-state store. | Phase 3 notifications. Out of scope. |
| **Scheduled / live refresh, "as of now"** | all | The snapshot is frozen and `as_of` is pinned; the console makes no network call at render. | Phase 3 refresh loop. The UI must keep saying "as of <as_of>," never "live." |
| **Evidence Explorer as a distinct route** | S7 | The data (derivation, provenance, timeline) exists but is currently rendered inside `/contract/<ticker>`; `/evidence/<contract_id>` is not a route yet. | A thin route slicing the same contract fields — backed data, unbuilt route. Listed here only because the route does not exist yet, not because data is missing. |
| **Activity as a distinct route** | S6 | Same: `ledger._entries()` + `ReviewLog.all()` back it, but `/activity` is not a route yet. | A thin route folding the two stores newest-first — backed data, unbuilt route. |

---

## Appendix — Figma note

No Figma file was produced: the Figma MCP available in the authoring session was
unauthenticated. This document is the buildable substitute. A designer should mirror
section 2 as a Figma component set, section 3 as component variants, and section 6.1 as
Figma design tokens (Carbon g100), then wire frames to the routes in section 1. Every frame
must be traceable to a row in section 7 or explicitly declared in section 8; a frame with no
backing row is a frame the renderer cannot fill.
