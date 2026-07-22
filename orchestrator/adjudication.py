"""Contingent transitions, formatted as a question a human can answer in seconds.

Roughly a quarter of substantive transitions end contingent: only the endpoint
prose changed, and a reword is indistinguishable from a redefinition by any
comparison this system is allowed to make. That is honest and, left there, it is
also useless. Amber that nobody resolves is amber forever.

The resolution is cheap for the right person and impossible for the machine. A
domain reader looking at "Phenotypic correction of bone marrow colony forming
units" beside "Bone Marrow Colony-Forming Cell Mitomycin-C resistance" answers in
under a minute, because MMC resistance is how phenotypic correction is measured.
So the system's output for a contingent case is not a verdict. It is the question,
with both texts side by side and the consequence of each answer stated.

Three properties this deliberately has:

**Expert time is rationed.** Only transitions that are contingent AND carry
movement worth resolving reach a human. A reword on a revision where the date did
not move changes no number and is not worth anyone's minute.

**The answer is stored, not just applied.** Every ruling is labelled ground truth:
two endpoint texts and a human's judgement of whether they name one measurement.
That is the only asset here nobody can copy, and it accumulates.

**A ruling is a decision, so it hash-chains.** It changes a displayed figure,
which makes it the same class of act as accepting a redline, and it is recorded
the same way rather than in a side file nobody audits.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

SAME = "same"
DIFFERENT = "different"
UNSURE = "unsure"
RULINGS = (SAME, DIFFERENT, UNSURE)


@dataclass(frozen=True)
class Question:
    """One contingent transition, posed rather than decided."""
    trial: str
    from_version: int | None
    to_version: int | None
    submitted: str | None
    moved_days: int | None
    before_text: str
    after_text: str

    @property
    def key(self) -> str:
        return f"{self.trial}:v{self.from_version}->v{self.to_version}"

    @property
    def consequence(self) -> dict:
        """What each answer does to the number, stated before it is given.

        Shown to the human on purpose. A question whose stakes are hidden invites
        an answer optimised for getting through the queue.
        """
        d = self.moved_days
        return {
            SAME: (f"the {d:+d} day movement becomes established" if d is not None
                   else "the movement becomes established"),
            DIFFERENT: (f"the {d:+d} days are refused; the commitment changed"
                        if d is not None else "the movement is refused"),
            UNSURE: "stays contingent, and the figure keeps both bounds",
        }


@dataclass
class Ruling:
    """A human's answer, and everything needed to audit it later."""
    key: str
    trial: str
    ruling: str
    author: str
    before_text: str
    after_text: str
    note: str = ""
    ts: str = field(default_factory=lambda:
                    datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def __post_init__(self):
        if self.ruling not in RULINGS:
            raise ValueError(f"ruling must be one of {RULINGS}, got {self.ruling!r}")
        if not self.author:
            raise ValueError("a ruling with no author cannot be audited")


def questions_from(contract: dict) -> list[Question]:
    """Every contingent transition in one contract's histories, worth asking.

    Skips revisions where the date did not move: a reword that changes no number
    is not worth a human minute, and this is the rationing rule in one line.
    """
    out: list[Question] = []
    histories = [contract.get("history")] + list(contract.get("lapsed_history") or [])
    for hist in histories:
        if not hist:
            continue
        revs = hist.get("revisions") or []
        for prev, rev in zip(revs, revs[1:]):
            if rev.get("transition") != "text_revised":
                continue
            moved = rev.get("moved_days")
            if not moved:
                continue
            out.append(Question(
                trial=hist.get("nct", ""),
                from_version=prev.get("version"),
                to_version=rev.get("version"),
                submitted=rev.get("submitted"),
                moved_days=moved,
                before_text=prev.get("primary_outcome") or "",
                after_text=rev.get("primary_outcome") or "",
            ))
    return out


class RulingStore:
    """Append-only JSONL of human rulings. Ground truth, accumulating."""

    def __init__(self, path: str):
        self.path = path

    def all(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        with open(self.path) as f:
            return [json.loads(line) for line in f if line.strip()]

    def by_key(self) -> dict[str, dict]:
        """Last ruling wins, so a correction supersedes without deleting."""
        out = {}
        for r in self.all():
            out[r["key"]] = r
        return out

    def add(self, ruling: Ruling) -> dict:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        row = asdict(ruling)
        with open(self.path, "a") as f:
            f.write(json.dumps(row) + "\n")
        return row


def apply_rulings(contract: dict, rulings: dict[str, dict]) -> dict:
    """Fold answered questions back into the totals.

    Returns the adjusted numbers WITHOUT mutating the contract, and always
    alongside the unresolved counts. A total that silently absorbed human rulings
    would be indistinguishable from one the machine established on its own, and
    those are different kinds of claim.
    """
    established = contingent = 0
    resolved_same = resolved_diff = unresolved = 0

    histories = [contract.get("history")] + list(contract.get("lapsed_history") or [])
    for hist in histories:
        if not hist:
            continue
        established += hist.get("slip_established_days") or 0
        revs = hist.get("revisions") or []
        for prev, rev in zip(revs, revs[1:]):
            if rev.get("transition") != "text_revised":
                continue
            moved = rev.get("moved_days") or 0
            if not moved:
                # A reword that moved no date changes no number, so it is not a
                # question and must not be counted as one waiting. The same
                # rationing rule as questions_from(), and the two have to agree
                # or the queue length and the unresolved count disagree.
                continue
            key = f"{hist.get('nct')}:v{prev.get('version')}->v{rev.get('version')}"
            r = rulings.get(key, {}).get("ruling")
            if r == SAME:
                established += moved
                resolved_same += 1
            elif r == DIFFERENT:
                resolved_diff += 1
            else:
                contingent += moved
                unresolved += 1

    return {
        "established_days": established,
        "contingent_days": contingent,
        "upper_bound_days": established + contingent,
        "resolved_same": resolved_same,
        "resolved_different": resolved_diff,
        "unresolved": unresolved,
    }


def demo() -> None:
    """Self-check, offline."""
    contract = {
        "history": {
            "nct": "NCT00000001",
            "slip_established_days": 100,
            "revisions": [
                {"version": 0, "primary_outcome": "response rate", "pcd": "2025-01-01"},
                {"version": 1, "primary_outcome": "objective response rate",
                 "transition": "text_revised", "moved_days": 400, "pcd": "2026-02-05"},
                # A reword that moved nothing: must never reach a human.
                {"version": 2, "primary_outcome": "ORR per RECIST",
                 "transition": "text_revised", "moved_days": 0, "pcd": "2026-02-05"},
            ],
        }
    }
    qs = questions_from(contract)
    assert len(qs) == 1, "a reword that moved no date must not be queued"
    q = qs[0]
    assert q.moved_days == 400
    assert "established" in q.consequence[SAME]
    assert "refused" in q.consequence[DIFFERENT]

    # Unresolved: the figure keeps both bounds.
    n = apply_rulings(contract, {})
    assert n == {"established_days": 100, "contingent_days": 400,
                 "upper_bound_days": 500, "resolved_same": 0,
                 "resolved_different": 0, "unresolved": 1}, n

    # Ruled the same: the days become established.
    n = apply_rulings(contract, {q.key: {"ruling": SAME}})
    assert n["established_days"] == 500 and n["contingent_days"] == 0
    assert n["resolved_same"] == 1 and n["unresolved"] == 0

    # Ruled different: the days are refused, not silently added.
    n = apply_rulings(contract, {q.key: {"ruling": DIFFERENT}})
    assert n["established_days"] == 100 and n["upper_bound_days"] == 100
    assert n["resolved_different"] == 1

    # The rationing rule must be identical in both directions: a reword that
    # moved no date is neither queued nor counted as waiting. Caught by this
    # assertion when the two disagreed.
    assert apply_rulings(contract, {})["unresolved"] == len(qs)

    # A ruling must name an author and a valid verdict.
    for bad in [dict(ruling="maybe", author="a"), dict(ruling=SAME, author="")]:
        try:
            Ruling(key="k", trial="t", before_text="x", after_text="y", **bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"accepted a bad ruling: {bad}")
    print("ok")


if __name__ == "__main__":
    demo()
