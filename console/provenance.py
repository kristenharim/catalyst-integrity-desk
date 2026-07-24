"""The evidence chain behind one displayed claim, and the point where it stops.

The Decision Review screen says what the desk computed. This module answers the
next question: which stored record supplied each input, which of those links
this application has actually resolved, and which are names it has not been able
to follow. Nothing here fetches anything. Every field read is already committed:
`data/snapshot.json` for the contract and its derivation, and the frozen
evidence bundle under `data/evidence/` for the source records the derivation
cites.

Three provenance states exist and they are never blurred:

  source_linked          the stored source record carries the named field, and
                         the value on that record is the value this snapshot
                         computed from.
  named_but_unresolved   the artifact names a source or a record, and this page
                         has not resolved the displayed value against it.
  unavailable            the record, the field or the identity cannot be
                         established from what is committed here.

`_state` is the only function that decides one, and it is the only function that
may name `SOURCE_LINKED` at all. That is asserted mechanically in
`tests/test_evidence_explorer.py` by walking this module's syntax tree, because
a second place to mint the strongest state is a second place for a guess to be
promoted into a link, and returning the constant, assigning it and passing it to
the tag formatter are the same defect by three routes. Every downgrade is free;
there is no upgrade path at all.

The provenance state is a different question from the evidence axis in
`console/states.py`, and both use the word "unavailable". The evidence axis says
whether a thesis can be read at all; a provenance state says whether a figure
can be traced to the record it names. The page labels each one where it renders
it, because two vocabularies sharing a word is how a reader ends up merging
them.
"""
from __future__ import annotations

from console.review import card_ticker
from evidence import Incomplete

# ---------------------------------------------------------------------------
# The three states
# ---------------------------------------------------------------------------

SOURCE_LINKED = "source_linked"
NAMED_BUT_UNRESOLVED = "named_but_unresolved"
UNAVAILABLE = "unavailable"

STATE_LABELS = {
    SOURCE_LINKED: "source linked",
    NAMED_BUT_UNRESOLVED: "named, not resolved",
    UNAVAILABLE: "unavailable",
}

STATE_NOTES = {
    SOURCE_LINKED: ("the stored source record names this field and carries the "
                    "value this snapshot computed from"),
    NAMED_BUT_UNRESOLVED: ("a source is named and this page has not resolved the "
                           "displayed value against it"),
    UNAVAILABLE: ("the source record, the field or the identity cannot be "
                  "established from what is committed here"),
}

# Weakest first. `_weakest` picks from this order and can only return a state it
# was given, so folding a record's fields into one state cannot invent a
# stronger one than the fields carry.
_ORDER = [UNAVAILABLE, NAMED_BUT_UNRESOLVED, SOURCE_LINKED]


def _state(record_named: bool, field_named: bool, value_resolved: bool) -> str:
    """The one place a provenance state is decided.

    Three inputs, and each is a question about stored bytes rather than about
    plausibility:

      record_named    a source record with an identity is committed here
      field_named     that record names the field or tag the figure came from
      value_resolved  the value stored on that record is the value this
                      snapshot computed from

    All three, and only all three, produce `source_linked`.
    """
    if not record_named:
        return UNAVAILABLE
    if not (field_named and value_resolved):
        return NAMED_BUT_UNRESOLVED
    return SOURCE_LINKED


def _weakest(states: list[str]) -> str:
    """One state for a record carrying several fields, never stronger than they are."""
    if not states:
        return UNAVAILABLE
    return min(states, key=_ORDER.index)


def _tagged(state: str, **extra) -> dict:
    return {"state": state, "state_label": STATE_LABELS[state],
            "state_note": STATE_NOTES[state], **extra}


# ---------------------------------------------------------------------------
# The committed evidence bundle
# ---------------------------------------------------------------------------

def _bundle(provider, ticker: str):
    """The committed bundle for this ticker, or the reason there is none.

    Matched on the ticker, which is the key the bundle is filed under and the
    key the snapshot's contracts are filed under. The snapshot does not record
    which bundle digest it was built from, so this is the identity the artifacts
    share and not an assertion that this bundle produced this contract; the page
    says so under missing evidence.
    """
    if provider is None:
        return None, "no evidence provider is configured for this console"
    try:
        return provider.get(ticker), ""
    except Incomplete:
        return None, f"no committed evidence bundle is stored for {ticker}"
    except ValueError as exc:                          # a digest that no longer recomputes
        return None, str(exc)


def _record(bundle, source: str, locator: str | None = None):
    if bundle is None:
        return None
    for r in bundle.records:
        if r.source == source and (locator is None or r.locator == locator):
            return r
    return None


# ---------------------------------------------------------------------------
# Level three: the source records
# ---------------------------------------------------------------------------

# The three figures the SEC record supplies, each with the runway field the
# snapshot stores it in and the provenance key naming its XBRL tag.
_SEC_FIELDS = [
    ("Cash", "cash", "cash", "cash_m", "$"),
    ("Short-term securities", "securities", "securities", "securities_m", "$"),
    ("Operating cash flow, annualised", "burn_recent_annual", "burn",
     "burn_recent_annual_m", "$"),
]


def _sec_source(c: dict, bundle) -> dict:
    """SEC XBRL company facts: one record, three tagged figures.

    Resolution is an equality: the bundle's stored raw figure against the raw
    figure this snapshot's runway was computed from. Equal means the displayed
    figure descends from that record's field rather than from something that
    merely looks like it.
    """
    runway = c["runway"]
    prov = runway.get("provenance") or {}
    rec = _record(bundle, "sec.xbrl")
    payload = (rec.payload if rec else {}) or {}

    fields = []
    for label, runway_key, prov_key, display_key, unit in _SEC_FIELDS:
        tag = prov.get(prov_key)
        stored = payload.get(runway_key)
        fields.append(_tagged(
            _state(rec is not None, bool(tag),
                   stored is not None and stored == runway.get(runway_key)),
            label=label,
            field=tag or "no XBRL tag is stored for this figure",
            value=f"{unit}{runway['display'][display_key]}M",
        ))

    # The trailing-window figure rides on the same tag and is the other end of
    # the band, so it is listed rather than left out of the record it came from.
    ttm = payload.get("burn_ttm_annual")
    fields.append(_tagged(
        _state(rec is not None, bool(prov.get("burn")),
               ttm is not None and ttm == runway.get("burn_ttm_annual")),
        label="Operating cash flow, trailing twelve months",
        field=prov.get("burn") or "no XBRL tag is stored for this figure",
        value=f"${runway['display']['burn_ttm_annual_m']}M",
    ))

    return _tagged(
        _weakest([f["state"] for f in fields]),
        key="sec.xbrl",
        type="SEC XBRL company facts",
        record=(rec.locator if rec else f"CIK {runway.get('cik')} companyfacts"),
        record_present=rec is not None,
        identity=f"CIK {runway.get('cik')}",
        effective=(rec.published_at if rec else None) or runway.get("as_of"),
        effective_label="filing as of",
        fetched=rec.fetched_at if rec else None,
        parser_version=rec.parser_version if rec else None,
        fields=fields,
        limitation=(
            "The record stores one figure per tag as of the filing date. Which "
            "quarterly facts were annualised into the two cash-flow figures is "
            "not stored, so those two resolve to this record and not to the "
            "individual periods behind them."
        ),
    )


def _study_source(c: dict, bundle) -> dict:
    """The sponsor-name query that produced the trial list.

    A query is not a filing and has no publication date, which is stored as
    `published_at: null` and rendered as the absence it is.
    """
    trial = c["trial"]
    rec = _record(bundle, "clinicaltrials.v2")
    trials = ((rec.payload if rec else {}) or {}).get("trials") or []
    stored = next((t for t in trials if t.get("nct") == trial.get("nct")), None)

    fields = [_tagged(
        _state(rec is not None, bool(trial.get("nct")),
               stored is not None and stored.get("pcd") == trial.get("pcd")),
        label="Registered primary completion, as returned by the query",
        field=trial.get("nct") or "no trial identifier is stored",
        value=trial.get("pcd") or "unavailable",
    )]
    return _tagged(
        _weakest([f["state"] for f in fields]),
        key="clinicaltrials.v2",
        type="ClinicalTrials.gov study query",
        record=(rec.locator if rec else
                f"query.spons={c['runway'].get('name')}"),
        record_present=rec is not None,
        identity=trial.get("nct", ""),
        effective=rec.published_at if rec else None,
        effective_label="published",
        fetched=rec.fetched_at if rec else None,
        parser_version=rec.parser_version if rec else None,
        fields=fields,
        limitation=(
            "A sponsor-name query carries no publication date, so this record "
            "has no date on which the source says it became current. It is the "
            "set the query returned when it ran, under the sponsor string named "
            "above."
        ),
    )


def _versions_source(h: dict, bundle, binding: bool) -> dict:
    """One registry version-history record, for one trial.

    Resolved against the last version this snapshot stored: the bundle has to
    carry a version with the same number, the same submission date and the same
    registered date. Anything less is a named record whose value this page has
    not followed.
    """
    nct = h.get("nct")
    rec = _record(bundle, "clinicaltrials.versions", nct)
    stored_revs = h.get("revisions") or []
    last = stored_revs[-1] if stored_revs else {}
    payload_revs = ((rec.payload if rec else {}) or {}).get("revisions") or []
    twin = next((r for r in payload_revs
                 if r.get("version") == last.get("version")), None)

    resolved = bool(twin) and (twin.get("submitted") == last.get("submitted")
                               and twin.get("pcd") == last.get("pcd"))
    fields = [_tagged(
        _state(rec is not None, last.get("version") is not None, resolved),
        label="Registered primary completion, set by this version",
        field=(f"version {last.get('version')}, submitted {last.get('submitted')}"
               if last else "no registry version is stored"),
        value=last.get("pcd") or "unavailable",
    )]

    versions = []
    for r in stored_revs:
        versions.append({
            "version": r.get("version"),
            "submitted": r.get("submitted"),
            "pcd": r.get("pcd"),
            "pcd_type": (r.get("pcd_type") or "").lower(),
            "transition": (r.get("transition") or "").replace("_", " "),
        })

    return _tagged(
        _weakest([f["state"] for f in fields]),
        key=f"clinicaltrials.versions:{nct}",
        type="ClinicalTrials.gov version history",
        record=(rec.locator if rec else nct or "unavailable"),
        record_present=rec is not None,
        identity=nct or "",
        binding=binding,
        effective=(rec.published_at if rec else None) or last.get("submitted"),
        effective_label="latest stored version submitted",
        fetched=rec.fetched_at if rec else None,
        parser_version=rec.parser_version if rec else None,
        fields=fields,
        versions=versions,
        n_versions=h.get("n_versions"),
        n_stored=len(stored_revs),
        sponsor=h.get("sponsor", ""),
        limitation=(
            "The versions stored here are the ones that carried a different "
            "registered date. The registry counts more of them than this "
            "artifact keeps, so a version not listed cannot be read either way."
        ),
    )


def _histories(c: dict) -> list[tuple[dict, bool]]:
    out = []
    if c.get("history"):
        out.append((c["history"], True))
    for h in c.get("lapsed_history") or []:
        out.append((h, False))
    return out


def _sources(c: dict, bundle) -> list[dict]:
    return ([_sec_source(c, bundle), _study_source(c, bundle)]
            + [_versions_source(h, bundle, binding) for h, binding in _histories(c)])


# ---------------------------------------------------------------------------
# Level two: the deterministic derivation
# ---------------------------------------------------------------------------

def _steps(c: dict, by_key: dict) -> list[dict]:
    """The committed derivation, each step pointed at the record it cites.

    A step naming an XBRL tag or the binding trial resolves to the record that
    supplies it and inherits that record's state. A step whose source is a
    calculation over the steps above it names no record and carries no
    provenance state at all, which is the honest shape: it is Python's
    arithmetic over inputs already stated above, and giving it a source tag
    would put a record behind a step that has none.
    """
    prov = c["runway"].get("provenance") or {}
    tag_to_key = {tag: key for key, tag in prov.items()}
    nct = (c.get("trial") or {}).get("nct")
    sec = by_key.get("sec.xbrl")
    registry = by_key.get(f"clinicaltrials.versions:{nct}")

    steps = []
    for row in c.get("derivation") or []:
        step = {"step": row["step"], "value": row["value"], "source": row["source"],
                "kind": row["kind"], "record": row["record"]}
        if row["kind"] != "tag":
            step.update(computed=True, source_key=None, state=None)
            steps.append(step)
            continue

        held = None
        if row["source"] in tag_to_key and sec is not None:
            # First match, which for the cash-flow tag is the annualised recent
            # quarter: the same order the record lists its fields in, and the
            # figure this derivation row carries.
            held = next((f for f in sec["fields"] if f["field"] == row["source"]), None)
            step["source_key"] = sec["key"]
        elif row["source"] == nct and registry is not None:
            held = registry["fields"][0]
            step["source_key"] = registry["key"]
        else:
            step["source_key"] = None

        state = (held["state"] if held
                 else _state(bool(row["record"]), bool(row["source"]), False))
        step.update(computed=False, **_tagged(state))
        steps.append(step)
    return steps


# ---------------------------------------------------------------------------
# Level one: the displayed results
# ---------------------------------------------------------------------------

def _results(c: dict) -> list[dict]:
    """The four things a reader came to inspect, and no fifth one.

    Every value is a preformatted snapshot field. Nothing here scores, ranks or
    concludes: a result that is not shown says why it is not shown, which for
    the funding gap is that the burn estimate under it was flagged unusable and
    a gap over an unusable burn looks comparable and is not.
    """
    runway = c["runway"]
    decision = c.get("decision") or {}
    reliable = bool(runway.get("reliable"))
    notes = "; ".join(runway.get("notes") or [])

    gap = {
        "label": "Funding gap",
        "value": f"{c.get('gap_months_1f')} months" if reliable else None,
        "shown": reliable,
        "note": ("Runway exhaustion against the registered primary completion "
                 "still ahead."),
    }
    if not reliable:
        gap["note"] = (
            "Not shown and not ranked. The burn estimate this figure rests on "
            f"was flagged unusable: {notes}. A gap computed over it would look "
            "comparable with the others and is not."
        )

    return [
        gap,
        {"label": "Registered primary-completion expectation",
         "value": c.get("catalyst_date"), "shown": True,
         "note": (f"{(c.get('trial') or {}).get('nct')}, recorded as "
                  f"{(c.get('trial') or {}).get('pcd')} and typed "
                  f"{((c.get('trial') or {}).get('pcd_type') or '').lower()}. A "
                  "month-only value is read as the first of that month.")},
        {"label": "Runway", "value": (f"{runway['display']['months_low_1f']} to "
                                      f"{runway['display']['months_high_1f']} months"),
         "shown": True,
         "note": ("Reliable" if reliable else "Flagged unusable") +
                 f", from the filing as of {runway.get('as_of')}."
                 + (f" {notes}" if notes else "")},
        {"label": "Review condition", "value": decision.get("evidence_label"),
         "shown": True,
         "note": ("Computed in the snapshot from the triggers listed below. It "
                  "is the evidence axis, not a provenance state.")},
    ]


# ---------------------------------------------------------------------------
# Level four: what is missing, negative, or refused
# ---------------------------------------------------------------------------

def _negatives(bundle) -> list[dict]:
    """Queries that ran and found nothing. Recorded, so they can be shown."""
    if bundle is None:
        return []
    return [{"source": n.source, "locator": n.locator, "reason": n.reason,
             "fetched": n.fetched_at} for n in bundle.negatives]


def _gaps(c: dict, sources: list[dict], bundle, bundle_error: str) -> list[dict]:
    """Every dimension this page could not establish, each with what it would need."""
    out = []
    if bundle_error:
        out.append(_tagged(
            UNAVAILABLE, label="Committed evidence bundle",
            detail=(f"{bundle_error}. Every source record below is unresolved "
                    "for that reason, and the derivation above is the snapshot's "
                    "own account with nothing behind it to check it against."),
        ))

    for s in sources:
        if not s["key"].startswith("clinicaltrials.versions"):
            continue
        covered = s["n_versions"] is not None and s["n_versions"] == s["n_stored"]
        detail = (f"The registry counts {s['n_versions']} versions for this trial "
                  f"and this artifact stores {s['n_stored']}, the ones that "
                  "carried a different registered date.")
        out.append(_tagged(
            _state(s["record_present"], s["n_versions"] is not None, covered),
            label=f"Registry version coverage, {s['identity']}",
            detail=detail + (
                " Every counted version is stored, so the movement of this date "
                "can be read across the whole history the registry reports."
                if covered else
                " A version this artifact does not store cannot be read either "
                "way from here, which is why a claim about what no other version "
                "did is refused rather than answered."),
        ))

    for s in sources:
        if not s["key"].startswith("clinicaltrials.versions"):
            continue
        queried = (c["runway"].get("name") or "")
        sponsor = s.get("sponsor") or ""
        out.append(_tagged(
            _state(bool(sponsor), bool(queried), sponsor == queried),
            label=f"Sponsor-to-issuer identity, {s['identity']}",
            detail=(f"The registry stores the sponsor of this trial as "
                    f"'{sponsor}'. The evidence for this contract was gathered "
                    f"under '{queried}', the issuer's SEC legal name. This page "
                    "compares the two strings and does not normalise them, so a "
                    "difference of any size leaves the attribution named and "
                    "not resolved."),
        ))

    out.append(_tagged(
        UNAVAILABLE, label="The bundle this snapshot was built from",
        detail=("The snapshot does not record the digest of the evidence bundle "
                "it was computed from. The bundle read here is the one filed "
                "under the same ticker, which is the identity the two artifacts "
                "share."),
    ))
    out.append(_tagged(
        UNAVAILABLE, label="Sources outside the two named above",
        detail=("Press wires, investor decks, correspondence, and SEC filings "
                "other than the XBRL company facts named above were never "
                "queried here. Nothing on this page is evidence about them in "
                "either direction, which is a different fact from a query that "
                "ran and returned nothing."),
    ))
    return out


def _refused(c: dict) -> list[dict]:
    """Readings this desk found and declined to use, with the refusal first."""
    out = []
    for l in c.get("lapsed") or []:
        out.append({
            "label": f"Lapsed registered expectation, {l.get('nct')}",
            "refusal": "never a catalyst",
            "figure": l.get("pcd"),
            "detail": ("A date that has already arrived cannot be a funding "
                       "target, so this one is not the binding catalyst. It is "
                       "kept and reported as a date-integrity signal rather "
                       "than dropped."),
        })
    for h, _binding in _histories(c):
        if h.get("slip_refused_revisions"):
            out.append({
                "label": f"Comparison refused, {h.get('nct')}",
                "refusal": "not comparable, and not to be read as delay",
                "figure": f"{h.get('slip_reported_days')} days reported",
                "detail": (f"A count or an enumeration changed across "
                           f"{h.get('slip_refused_revisions')} revision(s), so "
                           "subtracting the two dates would describe two "
                           "different commitments rather than one that moved. "
                           "Not comparable, and not to be read as delay."),
            })
        if h.get("slip_contingent_revisions"):
            out.append({
                "label": f"Comparison contingent, {h.get('nct')}",
                "refusal": "outside every established total until a human reads it",
                "figure": f"{h.get('slip_contingent_days')} days contingent",
                "detail": (f"{h.get('slip_contingent_revisions')} revision(s) "
                           "changed only the endpoint wording. A reword and a "
                           "redefinition are indistinguishable from the text, so "
                           "a human has to read the two descriptions; nothing "
                           "here records an answer, and the days stay outside "
                           "every established total."),
            })
    return out


# ---------------------------------------------------------------------------
# The view
# ---------------------------------------------------------------------------

def explorer(snapshot: dict, contract_id: str, provider) -> dict | None:
    """Everything the evidence explorer renders for one contract.

    `contract_id` is the identity the Decision Review screen uses: the recorded
    card's id where one exists, and the ticker where none does. `card_ticker`
    reads both, so one route serves either without a second lookup table, and an
    id naming no contract in this snapshot returns None rather than the nearest
    match. Guessing which contract a reader meant is how one contract's evidence
    ends up under another contract's name.
    """
    if not contract_id:
        return None
    ticker = card_ticker(contract_id)
    c = (snapshot.get("contracts") or {}).get(ticker)
    if c is None:
        return None

    bundle, bundle_error = _bundle(provider, ticker)
    sources = _sources(c, bundle)
    by_key = {s["key"]: s for s in sources}

    return {
        "contract_id": contract_id,
        "ticker": ticker,
        "name": c["runway"]["name"],
        "c": c,
        "decision": c.get("decision") or {},
        "review_href": f"/decisions/{contract_id}/review",
        "results": _results(c),
        "steps": _steps(c, by_key),
        "sources": sources,
        "negatives": _negatives(bundle),
        "queried_sources": sorted({r.source for r in bundle.records}) if bundle else [],
        "gaps": _gaps(c, sources, bundle, bundle_error),
        "refused": _refused(c),
        "bundle": {
            "present": bundle is not None,
            "error": bundle_error,
            "as_of": bundle.as_of if bundle else None,
            "origin": bundle.origin if bundle else None,
            "digest": bundle.digest if bundle else None,
            "entity_state": (bundle.entity or {}).get("state") if bundle else None,
            "entity_method": (bundle.entity or {}).get("method") if bundle else None,
            "complete": bundle.complete if bundle else False,
            "missing": list(bundle.missing) if bundle else [],
        },
    }
