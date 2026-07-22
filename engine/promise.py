"""Promise identity: when are two records the same commitment, revised?

This module exists because of the sharpest objection to the whole project, and
it is worth stating the objection in full before the code, because the code only
makes sense as an answer to it.

The system's credibility rests on: Python computes, a model judges prose and
never emits a number, every figure names its record. The objection is that this
discipline can be defeated one layer upstream. It does not matter that the
subtraction is exact if the two things being subtracted are not the same
promise. `primary_completion_date` moving from 2025-09 to 2028-04 is a slip of
943 days ONLY IF both dates describe the same milestone for the same population
under the same endpoint. If the sponsor also narrowed the enrolment criteria or
swapped the primary endpoint, "943 days of slip" is not a conservative estimate
or a rounding error. It is false, and the provenance trail underneath it makes
it look MORE authoritative, not less.

That is a worse failure than a model inventing a digit. An invented digit is
caught by `_fabricated()`. This one ships with a citation attached.

So: a promise is a first-class object with named dimensions, every revision is
classified into one of five transitions, and only two of them are ever allowed
to produce a slip number. The rest return "requires human adjudication", which
is a worse product and a true one.

    unchanged           nothing material moved
    date_only           the date moved; scope, endpoint and population did not
    scope_revision      the commitment itself changed shape
    supersession        this commitment was replaced or withdrawn
    uncertain           cannot be established from the record

              slip arithmetic allowed:  unchanged, date_only
              slip arithmetic refused:  everything else

The classification is deterministic and reads only structured registry fields.
No model participates. A model deciding "is this the same promise" is exactly
the judgement being excluded, relocated from the value to the match.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from engine.ctgov_history import _parse_date

# The five transitions, worst-understood last.
UNCHANGED = "unchanged"
DATE_ONLY = "date_only"
SCOPE_REVISION = "scope_revision"
SUPERSESSION = "supersession"
UNCERTAIN = "uncertain"

# Only these two describe a commitment whose shape held, so only these two
# permit "the date moved by N days" to be stated as a fact about one promise.
COMPARABLE = frozenset({UNCHANGED, DATE_ONLY})

# Registry statuses that end a commitment rather than revise it. A terminated
# trial's completion date is not a catalyst that slipped; it is a promise that
# stopped existing, and reporting slip on it invents a future that was withdrawn.
TERMINAL_STATUSES = frozenset({
    "WITHDRAWN", "TERMINATED", "SUSPENDED", "NO_LONGER_AVAILABLE",
})


@dataclass(frozen=True)
class Promise:
    """One dated commitment, with the dimensions that decide identity.

    Two records are the same promise when every dimension except `due` matches.
    The dimensions are the ones a registry actually exposes; a dimension that
    cannot be read is `None`, and `None` never counts as a match, because
    "unknown" and "same" are different and collapsing them is how a slip number
    gets invented.
    """
    actor: str                    # the sponsor making the commitment
    subject: str                  # the trial id: stable identity across versions
    milestone: str                # "primary_completion" | "study_completion"
    due: date | None              # the committed date
    scope: str | None = None      # phase, as a proxy for what is being attempted
    endpoint: str | None = None   # primary outcome measure
    population: str | None = None # enrolment count, as a proxy for who
    status: str | None = None     # overall registry status at this version
    version: int | None = None
    submitted: str | None = None  # when the sponsor filed this version

    @property
    def dimensions(self) -> tuple:
        """Everything except the date. Identity lives here."""
        return (self.actor, self.subject, self.milestone,
                self.scope, self.endpoint, self.population)


@dataclass
class Transition:
    """The classification of one revision, and why.

    `comparable` is the only field the arithmetic is allowed to consult. It is
    computed, not set, so a caller cannot opt into a slip number by writing a
    reason string that sounds confident.
    """
    kind: str
    reason: str
    moved_days: int | None = None
    changed: list[str] = field(default_factory=list)

    @property
    def comparable(self) -> bool:
        return self.kind in COMPARABLE

    @property
    def slip_days(self) -> int | None:
        """Days the date moved, or None when the promise did not hold its shape.

        This is the guard. Everything upstream can be correct and this still
        returns None, because a number that describes two different commitments
        is not a conservative estimate, it is a wrong answer with a citation.
        """
        return self.moved_days if self.comparable else None


def _dim_changes(a: Promise, b: Promise) -> list[str]:
    """Named dimensions that differ, treating unknown as a difference.

    `None != None` is enforced deliberately: if a dimension could not be read
    from either version, the honest answer is that continuity was not
    established, not that it was.
    """
    names = ("actor", "subject", "milestone", "scope", "endpoint", "population")
    out = []
    for name in names:
        av, bv = getattr(a, name), getattr(b, name)
        if av is None or bv is None:
            if not (av is None and bv is None):
                out.append(name)
            elif name in ("endpoint", "population", "scope"):
                # Both unknown on a dimension that decides comparability.
                out.append(f"{name}:unknown")
        elif av != bv:
            out.append(name)
    return out


def classify(before: Promise, after: Promise) -> Transition:
    """Classify one revision. Deterministic, structured fields only, no model.

    Order matters and is argued:

    1. A different trial id is not a revision at all. Callers that reach here
       with two subjects have a bug, and silently diffing them would produce the
       most confident wrong number the system can emit.
    2. A terminal status ends the commitment. Slip on a withdrawn trial invents
       a future that was retracted.
    3. Any changed dimension is a scope revision, whether or not the date moved.
    4. Unknown dimensions on both sides are uncertain, never "unchanged". An
       absent endpoint field is not evidence the endpoint held.
    5. Only then: same shape, date moved or did not.
    """
    if before.subject != after.subject:
        return Transition(
            UNCERTAIN,
            f"different subjects ({before.subject} vs {after.subject}); these are "
            f"not two versions of one promise",
            changed=["subject"],
        )

    if (after.status or "").upper() in TERMINAL_STATUSES:
        return Transition(
            SUPERSESSION,
            f"registry status is {after.status}; the commitment ended rather "
            f"than moved",
            changed=["status"],
        )

    changed = _dim_changes(before, after)
    unknown = [c for c in changed if c.endswith(":unknown")]
    real = [c for c in changed if not c.endswith(":unknown")]

    if real:
        return Transition(
            SCOPE_REVISION,
            "the commitment changed shape: " + ", ".join(real)
            + ". A date difference across a changed scope is not slip.",
            changed=real,
        )

    if unknown:
        return Transition(
            UNCERTAIN,
            "continuity could not be established; "
            + ", ".join(u.split(":")[0] for u in unknown)
            + " unreadable in both versions",
            changed=unknown,
        )

    if before.due is None or after.due is None:
        return Transition(
            UNCERTAIN,
            "a committed date is absent, so nothing can be said about movement",
        )

    moved = (after.due - before.due).days
    if moved == 0:
        return Transition(UNCHANGED, "same commitment, same date", moved_days=0)

    return Transition(
        DATE_ONLY,
        f"same commitment; the committed date moved {moved:+d} days",
        moved_days=moved,
    )


# ---------------------------------------------------------------------------
# Reading promises out of a registry history
# ---------------------------------------------------------------------------

def promises_from_history(history, actor: str) -> list[Promise]:
    """One Promise per registry version, in submission order.

    `TrialHistory.revisions` carries the fields the engine already extracts.
    Dimensions the engine does not extract are left `None` on purpose rather
    than defaulted to something agreeable: a default here would manufacture the
    continuity this module exists to refuse. Enriching the fetcher to read the
    outcome measure and enrolment per version is the upgrade, and until it lands
    those revisions classify as `uncertain` and produce no slip number.
    """
    out: list[Promise] = []
    for rev in getattr(history, "revisions", []) or []:
        d = rev if isinstance(rev, dict) else rev.__dict__
        out.append(Promise(
            actor=actor,
            subject=getattr(history, "nct", None) or d.get("nct", ""),
            milestone="primary_completion",
            due=_parse_date(d.get("pcd")),
            scope=d.get("phase"),
            endpoint=d.get("primary_outcome"),
            population=d.get("enrollment"),
            status=d.get("status"),
            version=d.get("version"),
            submitted=d.get("submitted"),
        ))
    return out


def walk(promises: list[Promise]) -> list[Transition]:
    """Classify every consecutive pair."""
    return [classify(a, b) for a, b in zip(promises, promises[1:])]


def net_slip_days(transitions: list[Transition]) -> tuple[int, int]:
    """(days of slip that may be stated, count of revisions that may not).

    The second number is the honest part and must be shown wherever the first
    is. A net slip computed over four comparable revisions while three others
    were refused is not "1,008 days of slip"; it is "1,008 days across the
    revisions where the commitment held its shape, with three not comparable".
    """
    total = sum(t.slip_days or 0 for t in transitions if t.comparable)
    refused = sum(1 for t in transitions if not t.comparable)
    return total, refused


def demo() -> None:
    """Self-check. Every branch of classify(), including the ones that refuse."""
    base = dict(actor="Rocket", subject="NCT06092034",
                milestone="primary_completion", scope="PHASE2",
                endpoint="safety", population="30", status="RECRUITING")

    # date_only: the shape held, the date moved.
    t = classify(Promise(**base, due=date(2025, 9, 1)),
                 Promise(**base, due=date(2028, 4, 1)))
    assert t.kind == DATE_ONLY, t
    assert t.slip_days == 943, t.slip_days

    # unchanged
    t = classify(Promise(**base, due=date(2028, 4, 1)),
                 Promise(**base, due=date(2028, 4, 1)))
    assert t.kind == UNCHANGED and t.slip_days == 0

    # scope_revision: the endpoint changed, so the date difference is not slip.
    after = dict(base, endpoint="overall survival")
    t = classify(Promise(**base, due=date(2025, 9, 1)),
                 Promise(**after, due=date(2028, 4, 1)))
    assert t.kind == SCOPE_REVISION, t
    assert t.slip_days is None, "a changed endpoint must not produce a slip number"

    # supersession: the commitment ended.
    t = classify(Promise(**base, due=date(2025, 9, 1)),
                 Promise(**dict(base, status="TERMINATED"), due=date(2028, 4, 1)))
    assert t.kind == SUPERSESSION and t.slip_days is None

    # uncertain: a dimension is unreadable in both versions.
    thin = dict(actor="Rocket", subject="NCT06092034",
                milestone="primary_completion", scope="PHASE2",
                population="30", status="RECRUITING")
    t = classify(Promise(**thin, endpoint=None, due=date(2025, 9, 1)),
                 Promise(**thin, endpoint=None, due=date(2028, 4, 1)))
    assert t.kind == UNCERTAIN, t
    assert t.slip_days is None, "unknown continuity must not produce a slip number"

    # uncertain: different subjects are not a revision.
    t = classify(Promise(**base, due=date(2025, 9, 1)),
                 Promise(**dict(base, subject="NCT04248439"), due=date(2028, 4, 1)))
    assert t.kind == UNCERTAIN and t.slip_days is None

    # net_slip reports what it refused.
    total, refused = net_slip_days([
        Transition(DATE_ONLY, "", 100), Transition(SCOPE_REVISION, "", 900),
        Transition(DATE_ONLY, "", 8),
    ])
    assert (total, refused) == (108, 1), (total, refused)
    print("ok")


if __name__ == "__main__":
    demo()
