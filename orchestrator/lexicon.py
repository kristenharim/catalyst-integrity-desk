"""The second structural guard: claims the system is not entitled to make.

`_fabricated()` stops the model inventing a number. This stops it, and the
templates, and the docs, making an assertion no evidence here supports. Both are
enforced the same way and for the same reason: a rule that lives only in a style
guide has already been broken somewhere nobody looked.

The list below is not a tone preference. Each entry is a claim this system
cannot substantiate from public dated records, sorted by the kind of overreach:

  FEASIBILITY  whether the underlying technology works, or a timeline is
               achievable. Nothing here measures that. This is the whole reason
               the project refuses the framing that would sell best.
  CHARACTER    fraud, deception, a named-fraud analogy, or any aggregate
               "credibility" score. A composite score is a judgement laundered
               through arithmetic.
  CAUSATION    why a date moved, or what an anomaly predicts. Slip has many
               causes: financing, enrolment, regulators, honest rescoping.
  SILENCE      "no amendment exists" rather than "none found in source S under
               procedure P at time T". Absence of evidence, stated as evidence.
  COMPLETENESS "all commitments captured", when scope is bounded by LIMITS.md.
  IMMUTABLE    the ledger is tamper evident, not immutable or append-only.

The word "credible" is banned in both directions, and that is the entry most
worth defending. It reads like a hedge, which is exactly what makes it
dangerous: it is a feasibility claim wearing a synonym, and it would let the
product imply the thing the architecture forbids while appearing careful.

Exempting a line: end it with the marker below. That is for prose that QUOTES a
banned phrase in order to forbid it, which `docs/LIMITS.md` does constantly. The
marker is deliberately ugly so it cannot be sprinkled around to silence a real
violation without someone noticing in review.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

EXEMPT_MARKER = "[lexicon-exempt]"


@dataclass(frozen=True)
class Rule:
    kind: str
    pattern: str
    why: str

    @property
    def rx(self) -> re.Pattern:
        return re.compile(self.pattern, re.IGNORECASE)


RULES: list[Rule] = [
    # --- feasibility -----------------------------------------------------
    Rule("feasibility", r"\b(?:the )?(?:technology|science|chemistry|platform|assay)\s+"
         r"(?:actually\s+)?(?:works|does not work|doesn't work|will never work)\b",
         "nothing here measures whether the underlying technology works"),
    Rule("feasibility", r"\btimelines?\s+(?:is|are|seems?|looks?)\s+"
         r"(?:un)?(?:realistic|reasonable|achievable|credible|plausible)\b",
         "judging a timeline is a feasibility claim, not a record comparison"),
    Rule("feasibility", r"\b(?:unrealistic|unachievable)\s+timelines?\b",
         "judging a timeline is a feasibility claim, not a record comparison"),
    Rule("feasibility", r"\bwill\s+(?:never\s+)?(?:ship|deliver|read ?out)\b",
         "the system does not predict delivery"),
    Rule("feasibility", r"\bgpt\s*-?\s*wrapper\b",
         "a capability judgement about someone else's product"),
    Rule("feasibility", r"\bvapou?rware\b", "a feasibility claim"),

    # --- character -------------------------------------------------------
    Rule("character", r"\b(?:fraud|fraudulent|deceptive|deceit|lied|lying|misled|"
         r"misleading)\b",
         "an intent claim; the system observes records, not motives"),
    Rule("character", r"\b(?:another|next|like)\s+theranos\b",
         "a named-fraud analogy used predictively"),
    Rule("character", r"\b(?:not\s+)?credib(?:le|ility)\b",
         "a feasibility claim wearing a synonym, banned in both directions"),
    Rule("character", r"\btrust\s+(?:score|rating)\b",
         "a composite score is a judgement laundered through arithmetic"),
    Rule("character", r"\brisk\s+score\b",
         "a composite score is a judgement laundered through arithmetic"),
    Rule("character", r"\b(?:bad|dishonest|untrustworthy)\s+(?:actor|management|sponsor)\b",
         "an intent claim"),

    # --- causation and prediction ----------------------------------------
    Rule("causation", r"\b(?:because|due to)\s+(?:the\s+)?(?:trial|study|drug)\s+"
         r"(?:failed|is failing)\b",
         "why a date moved is not observable from a registry diff"),
    Rule("causation", r"\b(?:predicts?|will lead to|indicates that .{0,20}will)\b",
         "no preregistered out-of-sample validation supports a prediction"),
    Rule("causation", r"\bearly warning\s+(?:of|that)\b",
         "implies predictive validity that has not been established"),

    # --- silence as evidence ----------------------------------------------
    Rule("silence", r"\bno amendment (?:exists|was ever filed|has ever been filed)\b",
         "say 'none found in source S under procedure P at time T'"),
    Rule("silence", r"\bthe company (?:failed to|did not) disclose\b",
         "asserts a disclosure duty the system has not established"),
    Rule("silence", r"\b(?:hid|concealed|covered up)\b",
         "an intent claim about silence"),

    # --- completeness -----------------------------------------------------
    Rule("completeness", r"\ball (?:commitments|promises|trials) (?:are )?(?:captured|tracked|covered)\b",
         "scope is bounded; say what was queried"),
    Rule("completeness", r"\bcomplete (?:picture|view) of\b",
         "scope is bounded; say what was queried"),

    # --- the ledger --------------------------------------------------------
    Rule("immutable", r"\b(?:immutable|append-only)\b",
         "the ledger is tamper evident given the anchor was not also rewritten"),

    # --- vocabulary the project fixed already ------------------------------
    Rule("vocabulary", r"\breadout date\b",
         "say 'registered primary-completion expectation'; they differ by two "
         "to four months, always optimistically"),
]


@dataclass(frozen=True)
class Violation:
    kind: str
    matched: str
    why: str
    line_no: int | None = None
    line: str | None = None

    def __str__(self) -> str:
        where = f" (line {self.line_no})" if self.line_no else ""
        return f"[{self.kind}] {self.matched!r}{where}: {self.why}"


def scan(text: str) -> list[Violation]:
    """Every banned assertion in a block of prose. Exempt lines are skipped."""
    out: list[Violation] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if EXEMPT_MARKER in line:
            continue
        for rule in RULES:
            for m in rule.rx.finditer(line):
                out.append(Violation(rule.kind, m.group(0), rule.why, i, line.strip()))
    return out


def clean(text: str) -> bool:
    return not scan(text)


def demo() -> None:
    """Self-check: each kind fires, and the exemption works."""
    assert scan("The technology actually works.")[0].kind == "feasibility"
    assert scan("This timeline is unrealistic.")[0].kind == "feasibility"
    assert scan("Looks like another Theranos.")[0].kind == "character"
    assert scan("Management is not credible.")[0].kind == "character"
    assert scan("A risk score of 4.")[0].kind == "character"
    assert scan("No amendment exists.")[0].kind == "silence"
    assert scan("An immutable ledger.")[0].kind == "immutable"
    assert scan("The readout date moved.")[0].kind == "vocabulary"
    assert scan("This is an early warning of trouble.")[0].kind == "causation"

    # The honest phrasings must pass, or the guard would forbid the product.
    for ok in [
        "The registered primary-completion expectation moved 943 days.",
        "No amendment was found in ClinicalTrials.gov version history as of 2026-07-21.",
        "The ledger is tamper evident given the anchor was not also rewritten.",
        "The commitment changed shape, so a date difference is not slip.",
        "Financing is required before the registered completion under the stated model.",
    ]:
        assert clean(ok), (ok, scan(ok))

    # Exemption, for prose that quotes a banned phrase to forbid it.
    assert clean(f'Never say "immutable" about the ledger. {EXEMPT_MARKER}')
    print("ok")


if __name__ == "__main__":
    demo()
