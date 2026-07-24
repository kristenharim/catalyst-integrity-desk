"""Granite prose carries no quantities, and the whole response goes if it does.

This replaces the span-typing guard, which authorised a magnitude by binding it
to a unit and a sign. That was strictly weaker than it read. The binding carried
no *field*, so any bare digit anywhere in the input licensed that magnitude in
the metric's own unit, and an audit demonstrated it against ordinary analyst
prose: a thesis reading "Phase 3 readiness across 12 sites and 2 arms" authorised
"3 months", "12 months" and "2 months", and the card's own conviction score
authorised a fourth. Those four cases are pinned at the bottom of this file,
because they are the reason the policy changed.

The rule now is that the model does not measure. Python and Jinja render every
figure from a deterministic field; Granite says which assumption moved and in
which direction. A response carrying any quantity is discarded whole and the
stub answers, so nothing is ever partially sanitised.
"""
from __future__ import annotations

import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.ledger import BeliefCard, Breach                       # noqa: E402
from orchestrator.granite import (                                  # noqa: E402
    GraniteClassifier, _quantitative, SYSTEM_PROMPT, ACTION_PROMPT,
)

REPO = os.path.join(os.path.dirname(__file__), "..")


@pytest.fixture
def live():
    card = BeliefCard(
        card_id="rckt:funded_to_catalyst", scope="trial:NCT04248439",
        claim="Rocket reaches the registered primary completion before runway "
              "exhaustion, with a non-negative funding gap.",
        metric="gap_months", expected_low=0.0, expected_high=10.4,
        driver="SEC XBRL liquidity (Q1-2026 10-Q) vs ClinicalTrials.gov registered PCD",
        confidence=3, source="10-Q", as_of="2026-07-21")
    breach = Breach(card_id="rckt:funded_to_catalyst", metric="gap_months",
                    observed=-14.5, expected_low=0.0, expected_high=10.4,
                    direction="under")
    return card, breach


# ---------------------------------------------------------------------------
# Refused: every shape a quantity arrives in
# ---------------------------------------------------------------------------

REFUSED = [
    ("plain magnitude",        "The gap is 3 months."),
    ("magnitude in words",     "Three months remain."),
    ("duration in words",      "The shortfall is thirty days."),
    ("confidence score",       "Confidence is 3 out of 10."),
    ("percentage",             "The result fell by 20%."),
    ("ratio",                  "The ratio is 2:1."),
    ("scientific notation",    "The value is 1e3."),
    ("bare year",              "Completion is expected in 2027."),
    ("date without a digit",   "The deadline is March fifth."),
    ("identifier",             "NCT04248439 no longer supports the claim."),
    ("input magnitude, right unit", "The gap is -14.5 months."),
    ("input magnitude, wrong unit", "The gap is 14.5 years."),
    ("input magnitude, wrong sign", "The gap is +14.5 months."),
    ("non-ASCII decimal digits",    "Completion is expected in ２０２７."),
    # A magnitude written as an inflection of a word the policy already refuses.
    # Refusing "double" while passing "doubled" is a spelling, not a policy.
    ("multiplicative inflection",   "The shortfall doubled."),
    ("fractional inflection",       "The runway halved."),
    ("fold compound",               "Revisions increased tenfold."),
    ("plural magnitude",            "The date slipped by hundreds of days."),
]


# ---------------------------------------------------------------------------
# Dates composed out of words the guard deliberately allows on their own
# ---------------------------------------------------------------------------
# "may", "first" and "second" are ordinary discourse here and are excluded from
# the word scan by design. The exclusions compose: every part of "May first" is
# allowed, so the phrase carried a registered completion date past every scan.
# These are the phrase, not the words, and several months are covered so this
# pins a date rule rather than one memorised string.

REFUSED_DATES = [
    "May first",
    "May the first",
    "May second",
    "May the second",
    "the first of May",
    "the second of May",
    "completion is expected May first",
    "The binding date is the first of May.",
    "June first",
    "the second of April",
    "March fifth",
    "Re-register by March first.",
    "Sept. second",
    "september first",
    "THE SECOND OF JANUARY",
]


@pytest.mark.parametrize("text", REFUSED_DATES)
def test_word_form_dates_are_refused(text):
    assert _quantitative(text), f"{text!r} is a date and carried no detected quantity"


# The other half of the same rule. A guard that fires on correct qualitative
# prose is a guard someone switches off, so the ordinary senses of the same
# words must survive it.
ACCEPTED_DISCOURSE = [
    "The evidence may require review.",
    "The first assumption no longer holds.",
    "The second condition requires review.",
    "The sponsor may revise the registered expectation again.",
    "The first and second revisions both moved later.",
    # "the first of X" only composes into a date when X is a month. Note the
    # phrasing avoids "one", which is a number word and refused on its own.
    "The first of the objections is the objection that matters.",
    "A couple of assumptions remain unverified.",
    "The comparison may not be establishable at all.",
]


@pytest.mark.parametrize("text", ACCEPTED_DISCOURSE)
def test_ordinary_discourse_survives_the_date_rule(text):
    found = _quantitative(text)
    assert not found, f"{text!r} is qualitative prose and was refused, naming {found}"


@pytest.mark.parametrize("label,text", REFUSED, ids=[r[0] for r in REFUSED])
def test_quantities_are_refused(label, text):
    found = _quantitative(text)
    assert found, f"{label}: {text!r} carried no detected quantity"


# ---------------------------------------------------------------------------
# Accepted: the qualitative judgment the model is actually for
# ---------------------------------------------------------------------------

ACCEPTED = [
    ("assumption named",  "The approved funding assumption no longer holds."),
    ("direction only",    "The current evidence is below the analyst-defined threshold."),
    ("evidence class",    "The registered expectation changed."),
    ("review required",   "Human review is required."),
    ("refusal",           "The comparison cannot be established from the available evidence."),
]


@pytest.mark.parametrize("label,text", ACCEPTED, ids=[a[0] for a in ACCEPTED])
def test_qualitative_statements_are_accepted(label, text):
    found = _quantitative(text)
    assert not found, f"{label}: {text!r} was refused, naming {found}"


# ---------------------------------------------------------------------------
# The laundering cases that ended the previous policy
# ---------------------------------------------------------------------------

LAUNDERED = [
    ("'Phase 3' licensed 3 months",   "The gap has narrowed to 3 months of headroom."),
    ("'12 sites' licensed 12 months", "Cash runs out 12 months before the readout."),
    ("'2 arms' licensed 2 months",    "Only 2 months of runway remain."),
    ("confidence=3 licensed 3 months", "The shortfall is 3 months."),
]


@pytest.mark.parametrize("label,text", LAUNDERED, ids=[l[0] for l in LAUNDERED])
def test_semantic_laundering_is_refused(label, text):
    """Each of these passed the span-typing guard. None may pass this one."""
    assert _quantitative(text), f"{label}: {text!r} was authorised again"


# ---------------------------------------------------------------------------
# Whole-response discard, never partial sanitisation
# ---------------------------------------------------------------------------

def _transport(rationale, label="direct_contradiction", confidence=0.9):
    def call(messages):
        return {"choices": [{"message": {"content": json.dumps(
            {"label": label, "confidence": confidence, "rationale": rationale})}}]}
    return call


def test_a_quantitative_response_falls_back_whole(live):
    card, breach = live
    bad = "The gap is 3 months, which is below the approved floor."
    g = GraniteClassifier(api_key="x", project_id="y",
                          transport=_transport(bad))
    result = g.classify(card, breach, {})
    assert result.source == "stub", "a quantitative rationale must not reach the user"
    assert result.rationale != bad, "the model's text must be discarded, not reused"
    assert "3 months" not in result.rationale, (
        "the offending phrase survived; the guard must discard the response "
        "rather than edit the number out of it"
    )


def test_a_qualitative_response_is_kept(live):
    card, breach = live
    good = ("The approved funding assumption no longer holds. The current value "
            "sits below the approved value, so human review is required.")
    g = GraniteClassifier(api_key="x", project_id="y",
                          transport=_transport(good))
    result = g.classify(card, breach, {})
    assert result.source == "granite", f"clean prose was rejected: {result.rationale!r}"
    assert result.rationale == good


# ---------------------------------------------------------------------------
# _draft_once: what is scanned is what is returned
# ---------------------------------------------------------------------------
# `draft_action` is dormant. Nothing in `console/` or `research/` calls it, so
# none of this ships today. It is fixed anyway, because the defect was that the
# guard scanned list-marker-stripped text and returned the unstripped original,
# and a dormant path with a hole in its provenance guard is a path that goes
# live with the hole in it.

def _draft_transport(text):
    def call(messages):
        return {"choices": [{"message": {"content": text}}]}
    return call


DRAFT_REFUSED = [
    ("leading year",        "2028. The registered expectation moved later."),
    ("leading integer",     "12. Human review is required."),
    ("leading decimal",     "1.5. The shortfall widened."),
    ("parenthesised marker", "3) The approved assumption no longer holds."),
    ("non-ASCII marker",    "２. The current value sits below the approved value."),
    ("marker mid-draft",    "The shortfall widened.\n2028. And then it lapsed."),
]


@pytest.mark.parametrize("label,text", DRAFT_REFUSED, ids=[d[0] for d in DRAFT_REFUSED])
def test_a_leading_numeral_is_scanned_not_stripped(label, text):
    g = GraniteClassifier(api_key="x", project_id="y", transport=_draft_transport(text))
    with pytest.raises(ValueError, match="quantities"):
        g._draft_once("brief")


DRAFT_ACCEPTED = [
    "The approved funding assumption no longer holds.",
    "The registered expectation moved later, so the shortfall widened.\n\n"
    "Human review is required before anything is pre-committed.",
]


@pytest.mark.parametrize("text", DRAFT_ACCEPTED)
def test_an_accepted_draft_is_returned_byte_identical(text):
    g = GraniteClassifier(api_key="x", project_id="y", transport=_draft_transport(text))
    returned = g._draft_once("brief")
    assert returned == text, (
        "the returned draft is not the text that was scanned; a guard that "
        "checks one string and returns another checks nothing"
    )


def test_draft_action_is_still_dormant():
    """Pins the claim made in this file's comment and in docs/LIMITS.md.

    If something starts calling `draft_action`, this fails and tells whoever
    wired it that the Action path now ships model prose to a human.
    """
    callers = []
    for sub in ("console", "research", "engine", "orchestrator"):
        base = os.path.join(REPO, sub)
        for root, _dirs, names in os.walk(base):
            if "__pycache__" in root:
                continue
            for name in names:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(root, name)
                src = open(path).read()
                if "draft_action" in src and not path.endswith("granite.py"):
                    callers.append(os.path.relpath(path, REPO))
    assert not callers, (
        f"draft_action now has callers {callers}; it is no longer dormant, so "
        "docs/LIMITS.md and the comments in tests/test_quantity_policy.py have "
        "to stop saying it is"
    )


# ---------------------------------------------------------------------------
# The shipped artifact and the shipped prompt
# ---------------------------------------------------------------------------

def test_the_frozen_rationale_survives_the_policy():
    """The committed demo memo must not need regenerating to satisfy this.

    If it did, the policy would be changing a displayed figure, and the frozen
    snapshot is not F2's to move.
    """
    snap = json.load(open(os.path.join(REPO, "data", "snapshot.json")))
    rationale = snap["redline"]["classification"]["rationale"]
    assert snap["redline"]["classification"]["source"] == "granite"
    found = _quantitative(rationale)
    assert not found, (
        f"the frozen Granite rationale carries quantities {found}, so adopting "
        f"this policy would require rebuilding the demo snapshot: {rationale!r}"
    )


def test_the_prompt_asks_for_what_the_guard_enforces():
    """A guard the prompt does not warn about is a guard that fires constantly."""
    for phrase in ("NO QUANTITIES OF ANY KIND", "the approved value",
                   "the current value", "below the threshold"):
        assert phrase in SYSTEM_PROMPT, f"prompt no longer says {phrase!r}"
    # "No digits." survives as one item in the broader list. What must not
    # survive is the retired rule that digits were the whole of it.
    assert "must contain NO digits" not in SYSTEM_PROMPT, (
        "the prompt still states the retired digits-only rule as the constraint"
    )


# ---------------------------------------------------------------------------
# Prompt policy and runtime policy state the same rule
# ---------------------------------------------------------------------------
# ACTION_PROMPT used to instruct the model to "write quantities in words
# instead" while `_quantitative()` refused number words, so the prompt asked
# for output the guard was built to discard. That is worse than either rule
# alone: the model complies and the desk still loses the draft.
#
# This is checked structurally rather than by pinning sentences. Every worked
# example in both prompts is run through the guard, so a future edit that adds
# a "YES" the guard refuses, or a "NOT" it waves through, fails here.

PROMPTS = {"SYSTEM_PROMPT": SYSTEM_PROMPT, "ACTION_PROMPT": ACTION_PROMPT}

_EXAMPLE = re.compile(r'^- (YES|NOT) "(.+)"$', re.M)


@pytest.mark.parametrize("name", sorted(PROMPTS))
def test_prompt_examples_agree_with_the_guard(name):
    examples = _EXAMPLE.findall(PROMPTS[name])
    assert examples, f"{name} has no worked examples left to check"
    for verdict, text in examples:
        found = _quantitative(text)
        if verdict == "YES":
            assert not found, (
                f"{name} offers {text!r} as acceptable output, but the guard "
                f"refuses it, naming {found}. The prompt is asking for prose "
                f"the runtime discards."
            )
        else:
            assert found, (
                f"{name} offers {text!r} as forbidden output, but the guard "
                f"accepts it. The prompt is stricter than the runtime, so the "
                f"example teaches a rule nothing enforces."
            )


@pytest.mark.parametrize("name", sorted(PROMPTS))
def test_no_prompt_authorises_a_quantity_in_words(name):
    prompt = PROMPTS[name]
    assert "NO QUANTITIES OF ANY KIND" in prompt, (
        f"{name} no longer states the enforced policy in the terms the guard "
        f"implements"
    )
    for retired in ("Write quantities in words instead",
                    "must contain NO digits at all",
                    "NO digits at all"):
        assert retired not in prompt, (
            f"{name} still carries {retired!r}, a rule the runtime contradicts"
        )


# The phrasing the policy leaves available. If the guard ever refuses one of
# these, the model has been left with no way to say anything at all.
ALLOWED_PHRASING = [
    "the approved value",
    "the current value",
    "above the threshold",
    "below the threshold",
    "the shortfall widened",
    "the registered expectation moved later",
    "human review is required",
]


@pytest.mark.parametrize("phrase", ALLOWED_PHRASING)
def test_the_allowed_vocabulary_survives_the_guard(phrase):
    found = _quantitative(phrase)
    assert not found, f"{phrase!r} is the sanctioned phrasing and was refused: {found}"
