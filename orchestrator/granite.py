"""IBM Granite (watsonx.ai) plugged into the classifier seam.

Same `.classify(card, breach, context)` signature as StubClassifier, so swapping
it in is a one-line change at the call site and the pipeline, ledger, and UI are
untouched.

What Granite is actually for here: the stub compares numbers, which is a Python
`if`. Granite's job is the semantic step the stub cannot do — read the card's
claim and driver and judge whether the breach changes the *story*. A contract can
sit outside its numeric band and still be fine if the thesis said so, and a small
drift can be fatal if it contradicts the stated rationale. That judgment is the
whole reason a model is in this loop.

Provenance rule: Granite emits NO numbers. Every figure in the final artifact is
rendered by application code from the engine's own output. A rationale containing
a digit is rejected as fabrication risk and the run falls back to the stub. See
`_NUMBER` below.

Credentials (never hardcode):
    export WATSONX_API_KEY=...
    export WATSONX_PROJECT_ID=...
    export WATSONX_URL=https://us-south.ml.cloud.ibm.com   # your region
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

from engine.ledger import BeliefCard, Breach
from orchestrator import lexicon
from orchestrator.classifier import (
    LABELS, Classification, StubClassifier,
    DIRECT_CONTRADICTION, ASSUMPTION_WEAKENED, ASSUMPTION_STRENGTHENED, NEW_MATERIAL_EVIDENCE,
)

IAM_URL = "https://iam.cloud.ibm.com/identity/token"
API_VERSION = "2024-10-08"
# granite-3-8b-instruct still answers but watsonx returns a withdrawn-state warning for
# it, and a withdrawn model can be pulled. Not something to discover while recording the
# submission demo.
DEFAULT_MODEL = "ibm/granite-4-h-small"

# ---------------------------------------------------------------------------
# The quantitative-expression policy
# ---------------------------------------------------------------------------
# Granite does not emit quantities. Not one it invented, and not one it was
# given. Every figure on screen is rendered by Python and Jinja from a
# deterministic field beside the model's prose, so the model has no reason to
# carry a number and no way to be trusted with one.
#
# What this replaces, and why it had to go. The previous rule authorised a
# magnitude by binding it to a unit and a sign, refusing any value absent from
# the input. That reads as provenance and is not: the binding carried no
# *field*, so any bare digit anywhere in the input licensed that magnitude in
# the metric's own unit. An audit demonstrated it against ordinary analyst
# prose. A thesis reading "Phase 3 readiness across 12 sites and 2 arms"
# authorised "3 months", "12 months" and "2 months", and the card's own
# conviction score authorised a fourth. Quantity(value, unit, sign) never
# established which field a number described, and no further unit arithmetic
# was going to establish it.
#
# So the question stops being "which numbers may the model repeat" and becomes
# "the model does not do numbers". A response carrying any quantity is
# discarded whole and the deterministic stub answers. Nothing is partially
# sanitised: a sentence with its number deleted is a sentence whose meaning
# nobody has checked.
#
# This governs MODEL prose only. The stub fallback states engine-computed
# values by design, because it is Python reading the same fields the page
# renders, and `Classification.source` records which of the two answered.

_DIGIT_RUN = re.compile(r"[-+\u2212]?\d[\d.,:]*(?:[eE][-+]?\d+)?%?")

# Number words carry magnitudes a digit scan never sees. "thirty days" is as
# quantitative as "30 days", and an earlier guard shipped blind to exactly that.
_WORDS = {
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty",
    "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred",
    "thousand", "million", "billion",
    "half", "twice", "double", "triple", "dozen", "percent",
}

# Ordinals and month names build a date without ever using a digit, which is
# how "March fifth" slips past every numeric scan ever written.
#
# "first" and "second" are deliberately absent. Both are ordinary discourse in
# this vocabulary -- "the first assumption", "on second reading" -- and a guard
# that fires on correct qualitative prose is a guard someone switches off. So
# is "May", a modal verb far more often than a month here. The exclusions are
# narrow and cheap: a real date almost always carries a digit or another month
# word alongside, so it is caught anyway, and the demonstrated attack ("March
# fifth") is caught twice over.
_ORDINAL_WORDS = {
    "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth",
    "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth",
    "sixteenth", "seventeenth", "eighteenth", "nineteenth", "twentieth",
    "thirtieth", "thirty-first",
}
_MONTH_WORDS = {
    "january", "february", "march", "april", "june", "july", "august",
    "september", "october", "november", "december",
}

_QUANT_WORD = re.compile(
    r"\b(" + "|".join(sorted(_WORDS | _ORDINAL_WORDS | _MONTH_WORDS)) + r")\b",
    re.I,
)

# "1." at the start of a line is an option enumerator, not a claim about a
# quantity. Stripped before the scan so formatting is not read as fabrication.
_LIST_MARKER = re.compile(r"^\s*\d+[.)]\s+", re.M)


def _quantitative(text: str) -> list[str]:
    """Every quantitative expression in `text`. Empty means the prose is clean.

    Covers digits in any shape -- signed, decimal, percentage, ratio, scientific
    notation, and the digits inside an identifier -- and quantities written as
    words, including the ordinals and month names by which a date arrives with
    no digit in it at all.

    Identifiers are refused rather than exempted. Granite has no need to repeat
    an NCT number: the page renders it from the contract, where it is checkable.
    """
    found = {m.group(0) for m in _DIGIT_RUN.finditer(text)}
    found |= {m.group(0).lower() for m in _QUANT_WORD.finditer(text)}
    return sorted(found)


SYSTEM_PROMPT = """\
You are the challenge partner on a catalyst integrity desk. A deterministic engine has \
already recomputed a catalyst contract and detected that something has left its approved \
range. You do not compute, restate, or estimate any number.

Your job is the judgment the arithmetic cannot make: read the standing belief's claim \
and its driver, then decide what the drift does to that belief's story.

METRIC DEFINITIONS (so you know what the sign means before you classify):
- gap_months: signed months of runway surplus at the registered primary completion date. \
Negative means cash is exhausted BEFORE the readout. It does not mean the trial is \
running late. A negative gap is a funding shortfall, not a clinical delay.
- runway_months_low: months until cash exhaustion at the conservative (high-burn) end of \
the burn band. Lower is worse.
- burn_ttm_annual: trailing-twelve-month annualised operating cash outflow. Higher means \
the company is spending more.
- pcd_revisions: cumulative count of times the sponsor revised the registered completion \
date. Rising means more revisions.
- max_days_expired: longest continuous stretch in days that the registry showed a \
completion date that had already passed. Higher means the sponsor carried a stale date \
longer.

Choose exactly one label:
- direct_contradiction: the reading is incompatible with the claim as written.
- assumption_weakened: the claim can still hold, but the reasoning behind it is eroding.
- assumption_strengthened: the drift is in the direction the claim predicted.
- new_material_evidence: the drift raises something the claim never accounted for.

Rules:
- Reason from the claim's wording and its driver, not from how far the number moved. \
A contract outside its band may still be acceptable if the claim anticipated the \
condition; a small move can be serious if it undercuts the stated reason for the belief.
- Weigh conviction: a low-conviction driver supporting a strong conclusion is a \
weaker story than a high-conviction one.

HARD CONSTRAINT ON THE RATIONALE — this one is not stylistic, it is a correctness rule:
Your rationale must contain NO QUANTITIES OF ANY KIND. No digits. No numbers written as \
words. No percentages, ratios, confidence scores, dates, durations, or arithmetic. Do not \
quote a figure even when it appears in the claim or in the reading you were given: the \
desk's engine owns every number and renders them from its own fields beside your text. A \
quantity written by you discards your entire answer and a deterministic fallback replaces \
it, so the desk loses your judgment and keeps its arithmetic.

Explain WHAT changed and in WHICH DIRECTION, never by how much:
- NOT "gap_months is -5.2, below the approved floor of 0.0"
- YES "the current value sits below the approved value"
- NOT "the shortfall widened by three months"
- YES "the shortfall widened"
- NOT "conviction is 2 out of 5"
- YES "the desk's conviction in this driver is weak"
- NOT "the completion date moved to 2028"
- YES "the registered expectation moved later"

Refer to readings only as "the approved value", "the current value", "above the \
threshold", or "below the threshold". Naming the metric in words is fine; measuring it \
is not.

Reply with JSON only, no prose and no code fences. The confidence field is a number \
because it is a field, not prose; the rationale must carry no quantity at all:
{"label": "<one label>", "confidence": <0.0-1.0>, "rationale": "<two or three sentences, no quantities>"}"""


ACTION_PROMPT = """\
You are the integrity desk's preparation partner. A scenario has been specified by a \
human and priced by a deterministic engine. Your job is the last step: argue what the \
desk should decide NOW, while nothing is happening and nobody is panicking.

Write three short parts, plain prose, no headings other than the ones given:

WHAT THIS ACTUALLY DOES TO THE CONTRACT
One paragraph. Say plainly what the impact figures mean for the funded-to-catalyst \
claim. If a metric IMPROVES while the contract becomes more strained, say so directly \
and explain why it is an artifact of the measurement convention rather than a genuine \
improvement. Do not let a reassuring number pass without comment.

OPTIONS
Two or three concrete choices the desk could pre-commit to, each with what it costs and \
what it gives up. Include the option of deliberately doing nothing where that is defensible. \
These are options for a human to choose between, not a recommendation to execute.

WHAT WOULD HAVE TO BE TRUE
State the trigger that should make the desk act, and the observation that would tell it \
this scenario is actually starting rather than noise.

HARD CONSTRAINT ON NUMBERS — this is a correctness rule, not a style note:
Your draft must contain NO digits at all. Not one.

You have deliberately been given directions rather than values, because the desk's engine \
owns every figure and renders them beside your text. You do not know the numbers, so you \
cannot state them, size a trade with them, or do arithmetic on them. Any digit in your \
draft is therefore something you invented, and the entire draft is discarded.

Write quantities in words instead:
- NOT "the gap has narrowed to -5 months"
- YES "the contract now shows a negative gap — the money runs out before the readout"
- NOT "burn is 180,000,000 per year"
- YES "the burn rate has increased materially"

Other rules:
- You cannot trade, execute, or approve anything. Everything you write is a proposal a \
human must accept, edit, or reject.
- No headings beyond the three above, no bullet symbols, no markdown."""


def _user_prompt(card: BeliefCard, breach: Breach, context: dict) -> str:
    # Numbers go IN (the model needs the reading to judge it) but never come back out.
    parts = [
        f"STANDING BELIEF ({card.card_id}, version {card.version})",
        f"  scope: {card.scope}",
        f"  claim: {card.claim}",
        f"  driver: {card.driver}",
        f"  conviction in that driver: {card.confidence} out of 5",
        f"  approved band for {card.metric}: {breach.expected_low} to {breach.expected_high}",
        "",
        "ENGINE READING",
        f"  {breach.metric} is now {breach.observed}, which is {breach.direction} the band.",
    ]
    # Directions come from redline.as_directions: what moved, in words, never values.
    # Giving the model the direction of every metric lets it reason about the full
    # picture without any figure it could echo or do arithmetic on.
    if context.get("directions"):
        parts += ["", "WHAT MOVED (directions only — the engine owns every value)"]
        parts += [context["directions"]]
    if context.get("news"):
        parts += ["", "EVIDENCE (verbatim, do not paraphrase as fact)"]
        parts += [f"  - {snippet}" for snippet in context["news"]]
    parts += ["", "Does this drift change the belief's story? Reply with the JSON object only."]
    return "\n".join(parts)


def _post(url: str, body: bytes, headers: dict, timeout: int) -> dict:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _extract_json(text: str) -> dict:
    """Models wrap JSON in fences or chatter often enough to be worth one line of defense."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"no JSON object in model output: {text[:200]!r}")
    return json.loads(text[start:end + 1])


class GraniteClassifier:
    """Granite over the watsonx.ai chat API. Falls back to the stub on any failure —
    a broken key must never take down the challenge loop mid-demo."""

    def __init__(self, api_key: str | None = None, project_id: str | None = None,
                 url: str | None = None, model_id: str | None = None,
                 transport=None, fallback=None, timeout: int = 30):
        self.api_key = api_key or os.environ.get("WATSONX_API_KEY", "")
        self.project_id = project_id or os.environ.get("WATSONX_PROJECT_ID", "")
        self.url = (url or os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")).rstrip("/")
        self.model_id = model_id or os.environ.get("WATSONX_MODEL_ID", DEFAULT_MODEL)
        self.timeout = timeout
        # transport(messages) -> raw chat response dict. Injected in tests so the
        # prompt and parsing are checked against recorded output, no credentials.
        self._transport = transport or self._call_watsonx
        self._fallback = fallback or StubClassifier()
        self._token = ""
        self._token_expires = 0.0

    # --- auth ---
    def _bearer(self) -> str:
        # ponytail: refresh a minute early rather than handling a 401 retry path.
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        if not self.api_key:
            raise RuntimeError("WATSONX_API_KEY is not set")
        body = urllib.parse.urlencode({
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": self.api_key,
        }).encode()
        data = _post(IAM_URL, body,
                     {"Content-Type": "application/x-www-form-urlencoded"}, self.timeout)
        self._token = data["access_token"]
        self._token_expires = time.time() + data.get("expires_in", 3600)
        return self._token

    # --- transport ---
    def _call_watsonx(self, messages: list[dict]) -> dict:
        if not self.project_id:
            raise RuntimeError("WATSONX_PROJECT_ID is not set")
        body = json.dumps({
            "model_id": self.model_id,
            "project_id": self.project_id,
            "messages": messages,
            # A cap, not a target: classification stops after a sentence or two, while
            # the scenario Action needs room for three sections. Sized for the longer
            # of the two so the draft never lands truncated mid-sentence.
            "max_tokens": 900,
            "temperature": 0,     # the same breach must classify the same way every run
        }).encode()
        return _post(
            f"{self.url}/ml/v1/text/chat?version={API_VERSION}", body,
            {"Content-Type": "application/json", "Accept": "application/json",
             "Authorization": f"Bearer {self._bearer()}"},
            self.timeout,
        )

    # --- scenario Action step ---
    def draft_action(self, scenario, result) -> str:
        """Draft the Action half of Trigger -> Transmission -> Impact -> Action.

        The engine has already computed the impact; Granite argues what the desk
        should do about it, in advance. Numbers are handed in already formatted and
        must be echoed rather than recomputed, so the same provenance rule applies:
        a figure that was not in the brief did not come from the engine.

        Returns "" on any failure. The caller renders the computed impact either
        way, so a dead model costs the narrative, never the numbers.
        """
        breaches = result.new_breaches
        breach_line = (
            "None. Every standing belief stays inside its approved range through this shock."
            if not breaches else
            "Breaks: " + ", ".join(f"{b.card_id} ({b.metric})" for b in breaches)
        )
        # Directions, not figures. See ScenarioResult.as_directions for why.
        brief = (
            f"SCENARIO: {scenario.name}\n\n"
            f"TRIGGER\n{scenario.trigger.strip()}\n\n"
            f"TRANSMISSION\n{scenario.transmission.strip()}\n\n"
            f"IMPACT (computed by the desk's engine; you are given directions, not values)\n"
            f"{result.as_directions()}\n\n"
            f"STANDING BELIEFS THIS WOULD BREAK\n  {breach_line}\n\n"
            "Write the ACTION step: what the desk should decide now, before this happens."
        )
        # Two attempts. The watsonx chat endpoint has been seen returning an empty
        # completion for no stated reason, and losing the Action step to one bad
        # round trip during a recording is not worth the saved call.
        last = None
        for attempt in range(2):
            try:
                return self._draft_once(brief)
            except Exception as e:                              # noqa: BLE001
                last = e
        print(f"[granite] no action draft: {type(last).__name__}: {last}", file=sys.stderr)
        return ""

    def _draft_once(self, brief: str) -> str:
        """One attempt, raising rather than degrading so the retry can see why."""
        raw = self._transport([
            {"role": "system", "content": ACTION_PROMPT},
            {"role": "user", "content": brief},
        ])
        text = raw["choices"][0]["message"]["content"].strip()
        if not text:
            # An empty completion is not a draft. Left unchecked it returns "" and the
            # caller reports the model as unavailable, which is both wrong and silent.
            raise ValueError("model returned an empty action draft")

        # The brief carries directions, never measured values, so the model has no
        # figure to echo and nothing to do arithmetic on. The digits it did see are
        # window metadata ("30d", "95"), fine to repeat; anything else it produced
        # itself. Option enumerators are formatting, not claims.
        quantities = _quantitative(_LIST_MARKER.sub("", text))
        if quantities:
            raise ValueError(f"model emitted quantities {quantities} in the action draft")
        return text

    # --- the seam ---
    def classify(self, card: BeliefCard, breach: Breach, context: dict) -> Classification:
        try:
            raw = self._transport([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _user_prompt(card, breach, context)},
            ])
            return self._parse(raw, card, breach)
        except Exception as e:                                  # noqa: BLE001
            print(f"[granite] falling back to stub: {type(e).__name__}: {e}", file=sys.stderr)
            return self._fallback.classify(card, breach, context)

    def _parse(self, raw: dict, card: BeliefCard, breach: Breach) -> Classification:
        content = raw["choices"][0]["message"]["content"]
        obj = _extract_json(content)

        label = str(obj.get("label", "")).strip().lower()
        if label not in LABELS:
            raise ValueError(f"unknown label from model: {label!r}")

        rationale = str(obj.get("rationale", "")).strip()
        if not rationale:
            raise ValueError("model returned an empty rationale")
        quantities = _quantitative(rationale)
        if quantities:
            raise ValueError(
                f"model emitted quantities {quantities}; Granite prose must be "
                f"non-quantitative and the engine renders every figure: {rationale!r}"
            )

        # Second structural guard, same treatment as the first.  _quantitative()
        # stops the model measuring anything; this stops it making a claim the
        # evidence does not support -- feasibility, intent, causation, or
        # silence asserted as fact.  They are separate controls for separate
        # failures: a model that says "this looks like fraud" has broken
        # provenance exactly as badly as one that says "47.2 months", and the
        # quantity guard would not have noticed, so it is discarded here the
        # same way and the deterministic stub answers.
        banned = lexicon.scan(rationale)
        if banned:
            raise ValueError(
                "model made a claim the evidence does not support: "
                + "; ".join(str(v) for v in banned)
                + f" in {rationale!r}"
            )

        confidence = float(obj.get("confidence", 0.5))
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"confidence out of range: {confidence}")

        return Classification(label, round(confidence, 2), rationale, source="granite")
