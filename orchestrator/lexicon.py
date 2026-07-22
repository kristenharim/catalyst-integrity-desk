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
    # A line matching `unless` is not checked against this rule. Distinct from
    # EXEMPT_MARKER, which excuses a quotation: this excuses a claim that has been
    # brought inside what the evidence supports, by labelling it. Only the
    # quantification rules use it, and the label they require is a real constraint
    # rather than a password, because it forces the assumption onto the page beside
    # the figure.
    unless: str | None = None

    @property
    def rx(self) -> re.Pattern:
        return re.compile(self.pattern, re.IGNORECASE)

    @property
    def unless_rx(self) -> re.Pattern | None:
        return re.compile(self.unless, re.IGNORECASE) if self.unless else None


# A Fermi estimate may be published only as a contingent figure whose assumption
# is stated on the same line. Both words are required: "contingent" alone is a
# label anyone can type, and the assumption is the part a reader can argue with.
LABELLED_CONTINGENT = r"(?=.*\bcontingent\b)(?=.*\bassum)"


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

    # --- absorption ---------------------------------------------------------
    # Added before any AI-domain content could render, not after. Every rule here
    # is a claim about a vendor's roadmap or about what a capability will be worth
    # later. This project measures whether dated public commitments were kept. It
    # has no instrument that reads the future of somebody else's product, and the
    # absorption argument is the single most tempting thing to assert without one.
    Rule("absorption",
         r"\b(?:will|going to|about to|bound to|destined to)\s+(?:be\s+|get\s+)?"
         r"(?:absorbed|subsumed|swallowed|commoditi[sz]ed|obsoleted|eaten|"
         r"replaced by (?:the )?model)\b",
         "whether a capability is absorbed is a prediction about a vendor's "
         "roadmap; nothing here measures it"),
    Rule("absorption",
         r"\b(?:absorbed|subsumed|commoditi[sz]ed|folded)\s+(?:in)?to\s+"
         r"(?:the\s+)?(?:model|models|foundation model|base model|platform|"
         r"labs?|frontier)\b",
         "a prediction about where a capability ends up, stated as observed"),
    Rule("absorption", r"\bbecomes?\s+(?:just\s+)?a\s+feature\b",
         "a claim about future product boundaries, not a record comparison"),
    Rule("absorption",
         r"\bfeature,?\s+not\s+a\s+(?:product|company|business|startup)\b",
         "a claim about future product boundaries, not a record comparison"),
    Rule("absorption", r"\btable\s+stakes\b",
         "asserts what the market will require later; unmeasured here"),
    Rule("absorption",
         r"\b(?:claude|chatgpt|gpt-?\d*|gemini|llama|openai|anthropic|deepmind)\b"
         r"[^.]{0,30}?\bwill\b",
         "a claim about another vendor's roadmap; the system observes records, "
         "not plans"),

    # --- unlabelled magnitudes ----------------------------------------------
    # A Fermi estimate is a legitimate thing to publish and an illegitimate thing
    # to publish bare. The quantification memo may state "$XB misallocated" only
    # as a contingent figure with its assumption on the same line, so a reader
    # sees what the number rests on at the moment they see the number.
    Rule("quantification",
         r"\$\s?\d[\d,.]*\s*(?:bn?|mm?|k|billion|million|trillion)?\b"
         r"[^.]{0,40}?\b(?:wasted|burned|burnt|misallocated|squandered|"
         r"thrown away|down the drain)\b",
         "a waste figure is an estimate; label it contingent and state the "
         "assumption it rests on, on the same line",
         LABELLED_CONTINGENT),
    Rule("quantification",
         r"\b(?:wast(?:e|es|ed|ing)|misallocat\w+|squander\w+|burn(?:s|ed|t|ing)?"
         r"\s+through)\b[^.]{0,25}?\$\s?\d",
         "a waste figure is an estimate; label it contingent and state the "
         "assumption it rests on, on the same line",
         LABELLED_CONTINGENT),

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
            ux = rule.unless_rx
            if ux is not None and ux.search(line):
                continue
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

    # The AI-domain rules, each planted and watched being caught. Written before
    # any such content exists, because a guard added after the prose is a guard
    # shaped around the prose it was supposed to judge.
    for planted in [
        "This whole category will be absorbed by the model layer.",
        "Screens like this get subsumed into the platform within a year.",
        "Registry monitoring becomes a feature of the base model.",
        "Honestly it is a feature, not a product.",
        "Provenance checking is table stakes by 2027.",
        "Claude will ship this natively in a release or two.",
        "GPT-5 will do this without a vendor.",
    ]:
        v = scan(planted)
        # `any`, not `[0]`: "Claude will ship this" trips the older feasibility
        # rule too, and which rule names it first does not matter. What matters
        # is that no planted line gets through.
        assert any(x.kind == "absorption" for x in v), (planted,
                                                        [str(x) for x in v])

    for planted in [
        "Roughly $3B is wasted on diligence that reads a stale date.",
        "Investors misallocated $12.4M against dates that had already passed.",
        "That is $900 million burned on a catalyst nobody re-read.",
    ]:
        v = scan(planted)
        assert any(x.kind == "quantification" for x in v), (planted,
                                                            [str(x) for x in v])

    # The same magnitudes are publishable once the label and the assumption are
    # on the line with them. This is the whole point of the rule: it does not ban
    # the estimate, it bans the estimate arriving unaccompanied.
    for ok in [
        "Contingent: about $3B wasted annually, assuming 4,000 diligence hours "
        "at the rates in the memo.",
        "Contingent on the assumption of one stale date per deal, $12M "
        "misallocated.",
    ]:
        assert clean(ok), (ok, [str(v) for v in scan(ok)])

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
