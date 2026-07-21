# Console plan

## Overview

Build a three-view web console over the existing engine. Server-side rendered with
Flask and Jinja2. No build step. Reads from a frozen JSON snapshot; no live API call
during rendering. Every number displayed traces to the engine — nothing is recomputed
in the view layer.

**Demo layout constraint (outranks everything else):** the console opens on the Rocket
Pharmaceuticals revision timeline (View 2 for RCKT), not the contract list. The 677-day
expired-date row must be visible without scrolling and without a click, and it must be
marked distinctly from ordinary revisions (distinct background, label, and icon).

The three views:

1. **Contract list** — ranked by funding gap. Unreliable rows shown but visually
   separated, unranked, with the flag reason shown.
2. **Contract detail** — gap calculation with every input labeled by XBRL tag or
   registry version, plus the trial's date revision timeline as a horizontal chart.
   Any revision where the sponsor carried an already-expired date is marked distinctly.
3. **Pending redline** — the challenge card, Granite's classification and memo, and
   accept / edit / reject controls.

---

## Sub-task 1: Snapshot generator

**Status:** [ ] pending

**Intent**

Produce a single `data/snapshot.json` that captures the full engine output for the
demo tickers (SANA, PRME, RCKT) in a format the Flask app can load at startup and
serve without touching any live API. This file is also what makes the "network
disabled" acceptance criterion provable.

The snapshot must be built with `GraniteClassifier`, not the stub. The ported
`challenge.py` renders "[stub judgment — IBM Granite drafts this from the RiskPacket
+ news context]" into the memo whenever `source` is not `"granite"`. That sentence
must never appear on camera in an IBM competition demo. `make_snapshot.py` must fail
loudly if Granite credentials are missing rather than silently falling back. Before
writing the file, assert that the serialized classification has `source == "granite"`.

SVG node positions for the revision timeline are computed here, not in the template.
Date-to-pixel arithmetic belongs to the snapshot generator; the template renders the
precomputed coordinates.

**Expected outcomes**

- `data/snapshot.json` exists and is valid JSON.
- Loading it and passing it to the template layer produces the same numbers as
  running the engine live.
- The file contains, per contract: all `Runway` fields and `provenance`, all
  `CatalystContract` fields (`gap_months`, `verdict`, `catalyst_date`), and the
  full `TrialHistory` serialized via `as_dict()` (including every `Revision` with
  `carried_expired`, `held_days`, `moved_days`), plus a `svg_x` float field on
  each revision representing its horizontal pixel position on a 1100-pixel-wide
  canvas.
- A pending redline is serialized: one scripted amendment for RCKT that adds 9
  months to `catalyst_date`, flipping `gap_months` negative. The `ChallengeCard`
  is built using `GraniteClassifier`. The serialized classification must have
  `source == "granite"` — the script asserts this and exits non-zero if not.

**Todo list**

1. Write `console/make_snapshot.py`. It imports `engine.gap.build()`, calls it for
   each ticker in `["SANA", "PRME", "RCKT"]`, and collects results.
2. For each contract, serialize: `runway` (all scalar fields + `provenance` dict +
   `notes` list + `reliable` bool), `trial` dict, `history.as_dict()` if present,
   `gap_months`, `catalyst_date` as ISO string, `verdict`.
3. Compute SVG x positions for each revision: determine the date span from the
   first to last `submitted` date across all revisions, map each `submitted` date
   linearly onto a 1100-pixel canvas (padding 60px each side), and store the result
   as `svg_x` (a float rounded to one decimal) in each revision dict.
4. Produce the scripted amendment: take the RCKT contract, construct a `ContractDelta`
   where `recomputed` has `catalyst_date` shifted +9 months, build a representative
   `BeliefCard`, run `orchestrator.redline.run_redline()` with a `GraniteClassifier`
   instance. Assert `challenge_card.classification.source == "granite"` — raise
   `RuntimeError` if not. Serialize the `ChallengeCard` (breach fields, classification
   label, source, memo, proposed card band changes).
5. Load Granite credentials from environment (the caller runs
   `set -a; . ./.env; set +a` before executing). If `WATSONX_API_KEY` is absent,
   print a clear error and exit with code 1 — no fallback.
6. Write the full dict to `data/snapshot.json` with `indent=2`.
7. Add a `--verify` flag that loads `data/snapshot.json`, prints the RCKT
   `gap_months`, the revision count, and `classification.source`, and asserts
   `source == "granite"`.

**Relevant context**

- `engine/gap.py` — `build()`, `CatalystContract`, `CatalystContract.gap_months`
- `engine/ctgov_history.py` — `TrialHistory.as_dict()`, `Revision.carried_expired`,
  `Revision.days_expired`
- `engine/contract.py` — `to_packet()`
- `orchestrator/redline.py` — `run_redline()`, `ContractDelta`, `as_directions()`
- `orchestrator/challenge.py` — `ChallengeCard`, `build_challenge()`
- `orchestrator/granite.py` — `GraniteClassifier` (credentials via env vars
  `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, `WATSONX_URL`)
- Cached API responses already exist in `data/cache/` — the engine reads from those.
- `.env` at repo root holds Granite credentials; loaded by caller before running
  the script.

---

## Sub-task 1 addendum: display strings

**Status:** [ ] pending

**Intent**

Sub-task 6 asserts that every number in a page's visible text appears verbatim in
`data/snapshot.json`. Sub-tasks 3 and 4 ask for gaps to one decimal and dollars in
millions. On the snapshot as it stands those two requirements contradict each
other. Checked by rendering each figure and searching the file, not by reasoning:

| displayed | stored as | found |
|---|---|---|
| `+8.4` (RCKT gap) | `8.37782340862423` | no |
| `-35.6` (PRME gap) | `-35.58110882956879` | no |
| `49.6` (RCKT cash, $M) | `49610000.0` | no |
| `144.4` (RCKT liquidity, $M) | `144379000.0` | no |
| `9.5` (RCKT runway low) | `9.541723575802969` | yes, by luck of the digits |

Twelve of the sixteen figures the list and detail views show fail. The wrong fix
is to exempt them from the test, which is how this project's other hollow checks
were born. Rounding is computation, and it belongs where `svg_x` already lives:
in the snapshot.

Note this must not trigger a Granite call. The redline block in the file was
produced by a live classification that survived free-tier congestion. Adding
display strings reads numbers that are already in the file.

**Expected outcomes**

- Each contract carries a `display` dict, and `redline` carries one, holding the
  exact strings the templates print.
- `python3 console/make_snapshot.py --displays` rewrites `data/snapshot.json` in
  place with those blocks, makes no network call and no Granite call, and is
  idempotent. Running it twice leaves the file byte-identical.
- The same function is called inside `build_snapshot()` before the write, so a
  future full rebuild produces them without the flag.
- After it runs, every figure in the table above is found in the file.

**Todo list**

1. Add `_add_displays(snapshot: dict) -> dict` to `console/make_snapshot.py`. Pure,
   no I/O, no imports beyond what is already there. For each contract it writes a
   `display` dict from values already in that contract:
   - `gap` = `f"{gap_months:+.1f}"` (explicit sign: `+8.4`, `-35.6`)
   - `months_low`, `months_high` = `f"{v:.1f}"`
   - `cash`, `securities`, `liquidity`, `burn_ttm`, `burn_recent` = `f"{v/1e6:.1f}"`
     (millions, one decimal, no thousands separator; a comma would split into two
     tokens and defeat the check)
   For `redline`, from `breach`: `observed`, `expected_low`, `expected_high`, each
   `f"{v:.1f}"`.
2. Add a `--displays` flag to `main()`: load `SNAPSHOT_PATH`, run `_add_displays`,
   write it back with `indent=2`. No credential check on this path, since it needs
   none.
3. Call `_add_displays(snapshot)` in `build_snapshot()` immediately before returning.
4. Run `python3 console/make_snapshot.py --displays`, then run it a second time and
   confirm `git diff --stat data/snapshot.json` shows no change from the second run.

**Relevant context**

- Templates from here on print `display.*` for every figure. A template that calls
  `round()`, `format()`, or a Jinja number filter is the defect this addendum exists
  to prevent, and sub-task 6 will catch it.
- Dates, tickers, XBRL tags, `days_expired`, `n_versions` and `svg_x` are already
  stored in the form they are shown. They need no display string.

---

## Sub-task 2: Flask app skeleton, routing, and requirements

**Status:** [ ] pending

**Intent**

Stand up the Flask application with correct routing for three views. The app loads
`data/snapshot.json` once at startup and passes slices of it to each template.
No computation in route handlers — they only slice and pass data. Also add
`requirements.txt` so Flask is a recorded dependency.

**Expected outcomes**

- `requirements.txt` exists at the repo root and pins Flask (e.g., `flask>=3.0`).
- `console/app.py` exists and runs with `python3 console/app.py`.
- Three views are routable:
  - `GET /` — redirects to `GET /contract/RCKT` (the demo-opening constraint).
  - `GET /contracts` — contract list view.
  - `GET /contract/<ticker>` — contract detail view (defaults to RCKT on `/`).
  - `GET /redline` — pending redline view.
- All three routes respond with HTML (not JSON) when snapshot is loaded.
- A startup check confirms `data/snapshot.json` exists and is loadable; if missing,
  print a clear error message directing the user to run `make_snapshot.py` first.

**Todo list**

1. Write `requirements.txt` at repo root: `flask>=3.0`.
2. Create `console/` directory with `__init__.py`.
3. Write `console/app.py`:
   - Load `data/snapshot.json` at module level into a `SNAPSHOT` dict.
   - Define routes: `/` redirects to `/contract/RCKT`. `/contracts` renders list
     template. `/contract/<ticker>` renders detail template. `/redline` renders
     redline template.
   - Each route handler extracts only the relevant slice from `SNAPSHOT` and
     passes it to `render_template()`. No arithmetic, no formatting logic in
     route handlers.
4. Create `console/templates/` directory.
5. Create `console/templates/base.html` — minimal layout: page title, a top nav
   with links to "Contracts" and "Pending Redline", and a `{% block content %}`.
   Plain HTML and inline CSS only. No external CSS framework, no JS framework, no
   CDN calls (network is off during demo).
6. Verify the app starts and each route returns 200.

**Relevant context**

- Flask only. No FastAPI, no build step.
- `data/snapshot.json` is the sole data source at render time.
- The DEMO.md constraint: `/` must open on the Rocket revision timeline, not the
  contract list. The redirect to `/contract/RCKT` implements this.

---

## Sub-task 3: Contract list view

**Status:** [ ] pending

**Intent**

Render the ranked contract list. Reliable contracts sorted by `gap_months` ascending
(most stressed first). Unreliable contracts appended below a visual separator with
their flag reason. No rank number shown for unreliable rows.

**Expected outcomes**

- `GET /contracts` renders a table of contracts.
- Reliable rows are ranked (1, 2, 3…) and sorted by `gap_months` ascending.
- Unreliable rows appear below a "Not ranked — see flag" separator with no rank
  number and the flag reason shown (taken from `runway.notes`).
- Each row links to its detail view.
- Funding gap displays as "+X.X mo surplus" (positive) or "-X.X mo shortfall"
  (negative, styled in red).
- No number in the rendered HTML is absent from the snapshot.

**Todo list**

1. Write `console/templates/contracts.html` extending `base.html`.
2. In the route handler, split snapshot contracts into `reliable` and `unreliable`
   lists based on the `reliable` field in the snapshot. Sort `reliable` by
   `gap_months` ascending.
3. Render a ranked table for reliable contracts: columns are Rank, Ticker, Company,
   Gap (months), Runway band (low–high months), Catalyst date, Revisions.
4. Render the unreliable section below a `<hr>` with a heading "Flagged — not
   ranked". Each row shows Ticker, Company, Flag reason (from `runway.notes`), and
   Catalyst date. No rank column.
5. Gap cell: print `{{ c.display.gap }} mo`, green when the string starts with `+`,
   red when it starts with `-`. The sign is already in the string. No rounding, no
   formatting, no arithmetic in the template. Same for the runway band, which is
   `{{ c.display.months_low }}–{{ c.display.months_high }} mo`.
6. The snapshot has two contracts, both reliable: SANA has no live pivotal trial
   and `build()` returns None for it, so it is absent from the file. The flagged
   section will therefore render empty. Build it anyway and have it render nothing
   when the list is empty. Do not fabricate a row to populate it.

**Relevant context**

- `Runway.reliable` — controls ranking vs. flagging
- `Runway.notes` — human-readable flag reason (e.g., "cash-positive quarter in TTM")
- `CatalystContract.gap_months` — signed months; negative = shortfall
- `CatalystContract.verdict` — already-rendered string, can use as tooltip
- AGENTS.md invariant: unreliable rows shown, never silently dropped

---

## Sub-task 4: Contract detail view with revision timeline

**Status:** [ ] pending

**Intent**

Render the contract detail for one ticker. Two panels: (a) the trial's PCD revision
timeline as a horizontal SVG chart (first, above the fold), and (b) the gap
calculation with every input labeled by its XBRL tag or registry version. The
677-day expired-date revision is the focal point of the demo and must be unmissable.

SVG coordinates come from the snapshot (computed in Sub-task 1). The template reads
`revision["svg_x"]` directly — no date arithmetic in the template.

**Expected outcomes**

- `GET /contract/RCKT` renders the Rocket detail with the revision timeline visible
  without scrolling. The timeline is the first thing visible after the page heading.
- The timeline renders as an inline SVG using precomputed `svg_x` values from the
  snapshot. Each revision is a circle node on a horizontal time axis.
- Normal revisions: filled circle, gray or blue.
- Any revision with `carried_expired=True`: filled circle in amber/red, a bold
  label `"carried expired — NNN days"`, and the node positioned above the axis
  baseline to stand out. The 677-day node is legible at demo font sizes.
- The gap calculation panel lists every input with its source label:
  - Cash: dollar value + XBRL tag from `runway.provenance["cash"]`
  - Securities: dollar value + XBRL tag from `runway.provenance["securities"]`
  - Burn band: TTM annual + recent annual + tag from `runway.provenance["burn"]`
  - Runway band: months low–high
  - Catalyst date: the PCD from the registry with NCT ID
  - Funding gap: signed months
- No number displayed is recomputed in the template — all values come from snapshot.

**Todo list**

1. Write `console/templates/detail.html` extending `base.html`.
2. Layout: revision timeline SVG appears first, then the gap calculation table below.
3. Render the SVG using precomputed `svg_x` from snapshot revision dicts:
   - SVG element: `width="1220" height="160"` (or proportional). Axis at y=100.
   - For each revision, place a `<circle>` at `cx="{{ r.svg_x }}" cy="100"`.
   - Normal revision: `fill="#6b7280"` (gray), `r="8"`.
   - `carried_expired=True`: `fill="#dc2626"` (red), `r="11"`, circle at `cy="70"`
     (above axis), plus a `<text>` label `"carried expired — {{ r.days_expired }} days"`
     in bold red anchored at the same x.
   - Label each node with the `submitted` date and `pcd` below the axis.
   - The SVG is inline HTML (no external file, no CDN).
4. Write the gap calculation panel as an HTML table. Every figure in it prints a
   `display.*` string from the snapshot (`$ {{ c.display.cash }}M` and so on). No
   division by a million in the template, no rounding filter.
   - Rows: Cash, Securities, Liquidity total, Burn (TTM annual), Burn (recent
     quarterly ann.), Runway band, Catalyst date (NCT ID + PCD), Funding gap.
   - Each row has a "Source" column showing the XBRL tag or "registry vN" as
     appropriate.
   - The funding gap row cites "engine/gap.py" in the source column.
5. Add a "Back to contract list" link in the page.

**Relevant context**

- `revision["svg_x"]` — precomputed x position, produced by `make_snapshot.py`
- `Revision.carried_expired`, `Revision.days_expired` — expired-date signal
- `Revision.submitted`, `Revision.pcd`, `Revision.moved_days`
- `Runway.provenance` — maps "cash", "securities", "burn" to XBRL tag names
- HANDOFF.md: "NCT04248439 (Rocket Pharmaceuticals): carried a completion date that
  had already passed for 677 days"
- AGENTS.md: "Every displayed number traces to a named XBRL tag or a specific
  registry version"

---

## Sub-task 5: Pending redline view

**Status:** [ ] pending

**Intent**

Render the challenge card for the scripted RCKT amendment: what moved (in directions,
not values), Granite's classification label and memo, and accept / reject controls.
The controls write a decision to a local file and redirect; they do not call any
live API. `data/decisions.jsonl` starts empty and is not committed to git — the
accept is a live action performed on camera.

**Expected outcomes**

- `GET /redline` renders the pending challenge card from the snapshot.
- The memo text contains "drafted by IBM Granite" (or equivalent language confirming
  Granite's authorship) and does not contain "stub".
- The view shows: ticker and trial ID, which breach triggered the challenge
  (`gap_months` outside approved band), Granite's classification label (styled by
  type), the memo text, and the proposed redline (band change).
- Accept / Reject buttons are present and functional:
  - `POST /redline/decide` with `verdict=approve` calls `apply_decision()` and
    writes the ledger entry to `data/decisions.jsonl`.
  - `POST /redline/decide` with `verdict=reject` appends a rejection entry to
    `data/review_log.jsonl`.
  - Either action redirects to a confirmation page showing the decision recorded
    and the ledger `verify()` result as a badge.
- `data/decisions.jsonl` is listed in `.gitignore`.
- The confirmation page displays `verify()` as green "✓ intact" or red "✗ tampered".
  It also includes the tamper-demo instruction as a visible `<blockquote>`.

**Todo list**

1. Write `console/templates/redline.html` extending `base.html`.
2. Display fields, with every figure printed from `redline.display.*` rather than
   formatted in the template: card_id, scope, breach metric + direction, classification label
   (styled: DIRECT_CONTRADICTION in red, ASSUMPTION_WEAKENED in amber, others in
   blue), memo text, and proposed band change from the snapshot's serialized
   `ChallengeCard.redline()` output.
3. Add a two-button form: "Accept" and "Reject" (both POST to `/redline/decide`
   with a hidden `verdict` field). Include a text field for `reason` on the Reject
   path.
4. Write `POST /redline/decide` route in `app.py`:
   - Construct `BeliefLedger` pointing at `data/decisions.jsonl`.
   - Construct `ReviewLog` pointing at `data/review_log.jsonl`.
   - Deserialize the `ChallengeCard` and `Decision` from the form + snapshot.
   - Call `apply_decision()`.
   - Redirect to `GET /redline/confirm`. That handler re-opens the ledger, reads
     the last entry and calls `verify()` there. Do not carry the result through the
     redirect in a session or a query string: the tamper demo depends on the badge
     reflecting the file at the moment the page is reloaded, not at the moment the
     decision was taken. A badge cached from before the tamper would show green on
     a corrupted ledger, which is the demo failing silently in the direction that
     looks fine.
5. Add `data/decisions.jsonl` and `data/review_log.jsonl` to `.gitignore`.
6. Write `console/templates/confirm.html`: shows "Decision recorded", the verdict,
   and the verify badge. Include the tamper-demo instruction as a `<blockquote>`:
   "Edit one byte of data/decisions.jsonl, then reload this page to see verify()
   return false."

**Relevant context**

- `orchestrator/challenge.py` — `ChallengeCard`, `apply_decision()`, `Decision`
- `engine/ledger.py` — `BeliefLedger`, `verify()`
- `orchestrator/challenge.py` — `ReviewLog`
- `orchestrator/classifier.py` — classification label constants
- DEMO.md: "Edit one byte of the ledger file on camera. Run `verify()`. It returns
  false."

---

## Sub-task 6: Automated tests

**Status:** [ ] pending

**Intent**

Provide a fast, no-live-server test suite that verifies all three routes, the
demo-critical content, and the "no recomputation in the view layer" invariant.
Every other phase left automated tests behind; this phase must too.

**Expected outcomes**

- `tests/test_console.py` exists and passes with `pytest tests/test_console.py`.
- The tests require no network access and no running server (Flask `test_client`).
- The following are asserted:
  - Each of the three routes (`/contracts`, `/contract/RCKT`, `/redline`) returns
    HTTP 200.
  - `GET /` returns a redirect to `/contract/RCKT`.
  - The RCKT detail HTML contains the string `"677"` and a carried-expired marker
    (e.g., the CSS class or label text used to mark the expired node).
  - The redline memo HTML contains `"granite"` (or the literal phrase that
    confirms Granite authorship) and does not contain `"stub"`.
  - The number-provenance invariant holds: every number-like token visible in the
    rendered text of `/contract/RCKT` and `/contracts` also appears in
    `data/snapshot.json`. This is the mechanical check for the "no number displayed
    to a user was computed in the view layer" claim.

**Todo list**

1. Write `tests/test_console.py`. Import the Flask app from `console.app` and
   use `app.test_client()`.
2. Fixture: load `data/snapshot.json` once for the session (raw string, for
   substring matching).
3. Test `GET /` — assert status 302 and `Location` header contains `/contract/RCKT`.
4. Test `GET /contracts` — assert status 200 and `Content-Type` is `text/html`.
5. Test `GET /contract/RCKT` — assert status 200, assert `"677"` in response text,
   assert the carried-expired marker string is present (use the exact CSS class or
   label text chosen during Sub-task 4).
6. Test `GET /redline` — assert status 200, assert `"granite"` in response text
   (case-insensitive), assert `"stub"` not in response text.
7. Number-provenance test — implemented as follows, with no judgement calls:
   a. Parse the response HTML with `html.parser` from the standard library. Walk
      all text nodes (not attribute values) and concatenate the visible text.
   b. Extract every token matching `-?\d+(?:\.\d+)?` from that visible text.
      This pattern covers integers (677), decimals (9.5), and signed values (-5.2),
      matching exactly the figures a human reads on screen.
   c. For each token, assert the token string appears in `data/snapshot.json`
      (loaded as a raw string). Fail with a message naming the token and the route.
   d. No exclusions. Attribute values (viewBox, r, stroke-width, font-size) are
      not text nodes and are not reached by the parser. SVG x positions are stored
      in the snapshot (Sub-task 1, step 3) and pass on their own merit. Rounded
      figures pass because the addendum put the rounded strings in the file. If a
      token fails here, the fix is a display string in the snapshot, never an
      exclusion in the test.
8. Failure verification: before finalising the tests, temporarily hardcode a number
   absent from the snapshot into the RCKT detail template (e.g., a literal `9999`
   in a `<td>`), run the provenance test, confirm it fails and names `"9999"` as
   the offending token, then remove the hardcoded value. A provenance check that
   has never been seen failing is not evidence of anything. Document that this was
   done in a comment in the test file.
9. Run `pytest tests/test_console.py` and confirm all tests pass.

**Relevant context**

- Flask `app.test_client()` — no live server needed
- `html.parser` — standard library, no new dependency
- `data/snapshot.json` — ground truth for the number-provenance check; load as
  a raw string so any number format present in the JSON matches by substring
- Sub-task 4 — the exact CSS class or label text for the carried-expired node must
  be documented here once chosen, so the test can reference it

---

## Sub-task 7: Acceptance check

**Status:** [ ] pending

**Intent**

Confirm the console meets the Prompt 3 acceptance criteria and the demo layout
constraint before marking the phase done.

**Expected outcomes**

- All three views render from `data/snapshot.json` with the network interface
  disabled (verified by disabling Wi-Fi and confirming no network calls fire during
  page renders).
- Opening `http://localhost:5000/` lands on the Rocket revision timeline. The
  677-day expired revision node is visible in the viewport without scrolling.
- The ledger tamper demo is accessible from the redline view confirmation page.
- `python3 console/make_snapshot.py --verify` passes and prints `source: granite`.
- `pytest tests/test_console.py` passes.
- A new row is added to `docs/BOB_LOG.md` for this phase.

**Todo list**

1. Start the Flask app, disable network, and visit all three views. Confirm no
   network errors and all numbers match `data/snapshot.json`.
2. Open `/` on a 1280×800 viewport. Confirm the expired-date node is in the
   visible area without scrolling.
3. Complete a full accept flow: click Accept on the redline view, confirm the
   decision is appended to `data/decisions.jsonl`, confirm the verify badge shows
   green "✓ intact".
4. Corrupt one byte of `data/decisions.jsonl`, reload the confirm page, confirm the
   verify badge shows red "✗ tampered".
5. Run `pytest tests/test_console.py`. Confirm all tests pass.
6. Add a row to `docs/BOB_LOG.md` — tool: Bob, phase: console.

**Relevant context**

- BOB_PROMPTS.md Prompt 3 acceptance: "all three views render from a frozen
  snapshot with the network disabled, and the ledger tamper demo is visible in
  the UI."
- DEMO.md: "0:25 to 0:50 — Show the Rocket Pharmaceuticals revision timeline...
  677 days... visible without scrolling."
