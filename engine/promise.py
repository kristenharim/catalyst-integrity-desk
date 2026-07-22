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

    unchanged           nothing moved
    date_only           the date moved; nothing else did
    text_revised        only free prose changed, so a reword and a redefinition
                        are indistinguishable. Movement is CONTINGENT.
    scope_revision      a count or enumeration changed. Unambiguous.
    supersession        this commitment was replaced or withdrawn
    uncertain           cannot be established from the record

        statable:    unchanged, date_only
        contingent:  text_revised, reported in its own total
        refused:     scope_revision, supersession, uncertain

`text_revised` exists because of a correction. An earlier version treated any
endpoint difference as a scope revision, which had two failure modes: a real
delay was excluded because the sponsor happened to reword the endpoint, and,
worse, a sponsor could remove a delay from the total by rewording deliberately.
A guard that a subject can defeat by editing prose, in the direction that
flatters them, is not a guard.

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
TEXT_REVISED = "text_revised"
SCOPE_REVISION = "scope_revision"
SUPERSESSION = "supersession"
UNCERTAIN = "uncertain"

# Only these two describe a commitment whose shape provably held, so only these
# two permit "the date moved by N days" to be stated as a fact about one promise.
COMPARABLE = frozenset({UNCHANGED, DATE_ONLY})

# Dimensions that are counts or enumerations. A difference here is unambiguous:
# an enrolment of 12 is not an enrolment of 14, and no rewording makes it so.
STRUCTURED_DIMENSIONS = ("actor", "subject", "milestone", "scope", "population")

# Dimensions that are free prose. A difference here is NOT a finding, and this
# is the correction to an earlier version of this module that treated it as one.
#
# "Phenotypic correction of bone marrow colony forming units after infusion of
# RP-L102" became "Bone Marrow (BM) Colony-Forming Cell (CFC) Mitomycin-C (MMC)
# resistance". In Fanconi anaemia gene therapy, MMC resistance of bone marrow
# colony-forming cells is how phenotypic correction is measured. Those two
# strings may name the same endpoint, described more precisely the second time.
# An exact comparison cannot tell, a normalised one cannot either, and a model
# deciding it is the judgement this whole module exists to exclude.
#
# Treating a prose difference as a scope revision had two failure modes pointing
# in opposite directions, and the second is worse:
#
#   false refusal  a real delay is excluded from the total because the sponsor
#                  reworded the endpoint at the same time
#   laundering     a sponsor who wants a delay to disappear from the comparable
#                  total need only reword the endpoint, and the guard obliges
#
# So a prose-only change now produces its own state: the movement is CONTINGENT,
# reported separately, and never silently folded into either total.
FREE_TEXT_DIMENSIONS = ("endpoint",)

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

    @property
    def contingent_days(self) -> int | None:
        """Days that count only if a human rules the reword cosmetic.

        Kept separate from `slip_days` on purpose. Folding it in would restate
        the bug this state was created to fix; dropping it would let a sponsor
        launder a delay out of the total by rewording an endpoint.
        """
        return self.moved_days if self.kind == TEXT_REVISED else None


def _dim_changes(a: Promise, b: Promise) -> tuple[list[str], list[str], list[str]]:
    """(structured changes, free-text changes, unreadable dimensions).

    `None != None` is enforced deliberately: if a dimension could not be read
    from either version, the honest answer is that continuity was not
    established, not that it was.
    """
    structured, freetext, unknown = [], [], []
    for name in STRUCTURED_DIMENSIONS + FREE_TEXT_DIMENSIONS:
        bucket = structured if name in STRUCTURED_DIMENSIONS else freetext
        av, bv = getattr(a, name), getattr(b, name)
        if av is None or bv is None:
            if not (av is None and bv is None):
                bucket.append(name)
            elif name in ("endpoint", "population", "scope"):
                # Both unknown on a dimension that decides comparability.
                unknown.append(name)
        elif av != bv:
            bucket.append(name)
    return structured, freetext, unknown


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

    structured, freetext, unknown = _dim_changes(before, after)

    if structured:
        return Transition(
            SCOPE_REVISION,
            "the commitment changed shape: " + ", ".join(structured)
            + ". These are counts and enumerations, so the difference is not a "
              "matter of wording. A date difference across them is not slip.",
            changed=structured,
        )

    if freetext:
        # The correction. A prose difference is not evidence the commitment
        # changed, and it is not evidence it held. The movement is reported as
        # contingent on a human reading the two descriptions, and counted in its
        # own total so that rewording cannot make a delay disappear.
        moved = (None if before.due is None or after.due is None
                 else (after.due - before.due).days)
        return Transition(
            TEXT_REVISED,
            "only free-text changed (" + ", ".join(freetext) + "). A reword and a "
            "redefinition are indistinguishable here, so the movement is "
            "contingent: it counts only if a human reads the two descriptions as "
            "the same commitment.",
            moved_days=moved,
            changed=freetext,
        )

    if unknown:
        return Transition(
            UNCERTAIN,
            "continuity could not be established; "
            + ", ".join(unknown)
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
    """(days that may be stated, count of revisions that may not).

    Kept two-valued for callers that predate the contingent state. Prefer
    `slip_breakdown`, which does not hide the contingent days inside "refused".
    """
    b = slip_breakdown(transitions)
    return b["established"], b["refused"] + b["contingent_revisions"]


def slip_breakdown(transitions: list[Transition]) -> dict:
    """Established, contingent, and refused, reported separately.

    Three numbers because there are three situations, and collapsing them is how
    both failure modes happen:

      established   the commitment provably held its shape. Statable.
      contingent    only free text changed. Counts if and only if a human reads
                    the descriptions as the same commitment. Reporting it as
                    zero lets a sponsor launder a delay by rewording; reporting
                    it as established restates the original bug.
      refused       a count or enumeration changed, or the commitment ended, or
                    continuity was unreadable. Not statable at any confidence.
    """
    established = sum(t.slip_days or 0 for t in transitions if t.comparable)
    contingent = sum(t.contingent_days or 0 for t in transitions
                     if t.kind == TEXT_REVISED)
    return {
        "established": established,
        "contingent": contingent,
        "contingent_revisions": sum(1 for t in transitions if t.kind == TEXT_REVISED),
        "refused": sum(1 for t in transitions
                       if not t.comparable and t.kind != TEXT_REVISED),
        "upper_bound": established + contingent,
    }


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

    # scope_revision: a COUNT changed, which no rewording can explain away.
    after = dict(base, population="120")
    t = classify(Promise(**base, due=date(2025, 9, 1)),
                 Promise(**after, due=date(2028, 4, 1)))
    assert t.kind == SCOPE_REVISION, t
    assert t.slip_days is None, "a changed enrolment must not produce a slip number"

    # text_revised: only prose changed. Not statable, not zero, CONTINGENT.
    after = dict(base, endpoint="overall survival")
    t = classify(Promise(**base, due=date(2025, 9, 1)),
                 Promise(**after, due=date(2028, 4, 1)))
    assert t.kind == TEXT_REVISED, t
    assert t.slip_days is None, "a reworded endpoint is not established movement"
    assert t.contingent_days == 943, "and it must not vanish either"

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

    # The laundering attack, stated as a test: a sponsor pushes the date out and
    # rewords the endpoint in the same filing. The days must NOT disappear.
    b = slip_breakdown([
        Transition(DATE_ONLY, "", 100),
        Transition(TEXT_REVISED, "", 1430),
        Transition(SCOPE_REVISION, "", 900),
    ])
    assert b["established"] == 100
    assert b["contingent"] == 1430, "a reworded endpoint must not launder a delay"
    assert b["refused"] == 1
    assert b["upper_bound"] == 1530
    print("ok")


if __name__ == "__main__":
    demo()
