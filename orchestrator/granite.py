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
from dataclasses import dataclass
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

# A number is fabricated if it did not come from the input. Quoting a figure that the
# card's own claim already contains ("acceptable up to ~32%") is not invention, it is
# quotation, and rejecting it throws away good judgment. What must never survive is a
# figure the model produced on its own.
# Compared as whole numbers, not as substrings. Substring containment let real
# fabrications through: a model writing "5%" passed because the input mentioned
# var_95_1d_dollar, and "3%" passed because it mentioned a 30-day window. Both
# were invented trade sizes presented as if measured.
_NUMBER_RUN = re.compile(r"\d+(?:\.\d+)?")


def _numbers_in(text: str) -> set[str]:
    return set(_NUMBER_RUN.findall(text))

# Spans that carry digits but name a record rather than measure anything: a
# registry id, an ISO date, a fiscal quarter, an SEC form name, a filer id.
# Those digits are part of a name, so they may not authorise a quantity.
#
# Left unmasked they did. The live Rocket card's driver reads "SEC XBRL
# liquidity (Q1-2026 10-Q)", which licensed the model to write "2026 days of
# cash remaining" and "a 1 month delay", because "2026" and "1" both appear in
# it. Neither figure was ever measured; both would have reached the user as a
# number the engine never computed, which is the one thing this project may not
# do. The guard stays "a number absent from the input" and gets a stricter
# reading of what counts as an input number.
_IDENTIFIER = re.compile(
    r"NCT\d+"                       # registry id
    r"|\d{4}-\d{2}-\d{2}"           # ISO date
    r"|\bQ\d[-\s]?\d{4}\b"          # fiscal quarter
    r"|\b\d{1,2}-[A-Z]\b"           # SEC form name, 10-Q and 8-K
    r"|\bCIK[\s:]*\d+"              # filer id
)


# Number words carry magnitudes that a digit scan never sees. "thirty months"
# is as much a fabricated quantity as "30 months".
_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
    "eleven": "11", "twelve": "12", "thirteen": "13", "fourteen": "14",
    "fifteen": "15", "sixteen": "16", "seventeen": "17", "eighteen": "18",
    "nineteen": "19", "twenty": "20", "thirty": "30", "forty": "40",
    "fifty": "50", "sixty": "60", "seventy": "70", "eighty": "80",
    "ninety": "90", "hundred": "100", "thousand": "1000",
}
_WORD_RUN = re.compile(r"\b(" + "|".join(_WORDS) + r")\b", re.I)

# The units this desk actually measures in. A magnitude with a unit outside this
# set is not comparable to anything in the card, so it is treated as unitless
# and judged on its value alone.
_UNITS = {
    "month": "months", "months": "months", "mo": "months",
    "day": "days", "days": "days", "d": "days",
    "year": "years", "years": "years", "yr": "years",
    "week": "weeks", "weeks": "weeks",
    "quarter": "quarters", "quarters": "quarters",
    "percent": "%", "%": "%",
}

_QUANTITY = re.compile(
    r"(?P<sign>[-+−])?\s*"
    r"(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>%|[A-Za-z]+)?"
)


@dataclass(frozen=True)
class Quantity:
    """One measurement, as the guard understands it.

    value  canonical decimal text, "14.5" or "30"
    unit   canonical unit, "months" | "days" | "years" | "weeks" | "quarters"
           | "%" | "" when the number carried no unit this desk measures in
    sign   "-" for a negative magnitude, "" otherwise
    """

    value: str
    unit: str
    sign: str

    def __str__(self) -> str:
        return f"{self.sign}{self.value}{' ' + self.unit if self.unit else ''}"


def _typed(text: str) -> set[Quantity]:
    """Every magnitude in `text`, bound to its unit and sign.

    Identifier spans are typed out first: the digits in NCT04248439, 2026-05-05
    and "10-Q" name a record and measure nothing, so they never become a
    Quantity and can never authorise one.
    """
    cleaned = _IDENTIFIER.sub(" ", text)
    cleaned = _WORD_RUN.sub(lambda m: _WORDS[m.group(1).lower()], cleaned)
    out: set[Quantity] = set()
    for m in _QUANTITY.finditer(cleaned):
        raw_unit = (m.group("unit") or "").lower()
        unit = _UNITS.get(raw_unit, "")
        sign = "-" if m.group("sign") in ("-", "−") else ""
        out.add(Quantity(m.group("value"), unit, sign))
    return out


def _quantities_in(text: str) -> set[str]:
    """Bare values only, kept for the action-draft guard's coarser question."""
    return {q.value for q in _typed(text)}

# "1." at the start of a line is an option enumerator, not a claim about the book.
# Stripped before the number guard runs so numbered options do not read as fabrication.
_LIST_MARKER = re.compile(r"^\s*\d+[.)]\s+", re.M)


def _fabricated(rationale: str, card: BeliefCard, breach: Breach) -> list[str]:
    """Numbers in the rationale that appear nowhere in what the model was given."""
    source = " ".join(str(x) for x in (
        card.claim, card.driver, card.metric, card.confidence,
        breach.observed, breach.expected_low, breach.expected_high,
        # the model sees these rounded in the prompt, so allow both renderings
        round(breach.observed), round(breach.expected_low), round(breach.expected_high),
    ))
    # The rule stays "a number absent from the input". What tightened is the
    # reading of "the same number": a magnitude matches only when its value and
    # its sign both appear in the input, and its unit is one the input actually
    # measures in. A band edge of 10 months does not licence "10 days", and a
    # shortfall of -15 does not licence "+15".
    given = _typed(source)
    values = {(q.value, q.sign) for q in given}
    units = {q.unit for q in given if q.unit} | _metric_units(card.metric)
    return [str(q) for q in _typed(rationale)
            if (q.value, q.sign) not in values or (q.unit and q.unit not in units)]


def _metric_units(metric: str) -> set[str]:
    """The unit a metric name declares, so a bare input value can be quoted with it.

    `gap_months` is months. The engine hands the model bare floats, so without
    this every correctly-united sentence about the gap would be refused, and a
    guard that rejects correct output is a guard someone switches off.
    """
    return {u for tail, u in (("_months", "months"), ("_days", "days"),
                              ("_years", "years"), ("_pct", "%"))
            if metric.endswith(tail)}

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
Your rationale must contain NO digits. Not one. Do not restate the reading, do not quote \
the band, do not echo a figure that appears in the claim itself. The desk's engine owns \
every number and renders them beside your text; a number written by you is treated as \
fabricated and your entire answer is discarded.

Say it in words instead:
- NOT "gap_months is -5.2, below the approved floor of 0.0"
- YES "the contract now sits below its approved floor"
- NOT "conviction is 2 out of 5"
- YES "the desk's conviction in this driver is weak"

Reply with JSON only, no prose and no code fences:
{"label": "<one label>", "confidence": <0.0-1.0>, "rationale": "<two or three sentences, no digits>"}"""


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
        allowed = _quantities_in(brief)
        invented = [n for n in
                    _NUMBER_RUN.findall(_IDENTIFIER.sub(" ", _LIST_MARKER.sub("", text)))
                    if n not in allowed]
        if invented:
            raise ValueError(f"model invented {invented} in the action draft")
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
        invented = _fabricated(rationale, card, breach)
        if invented:
            raise ValueError(f"model invented {invented}, provenance broken: {rationale!r}")

        # Second structural guard, same treatment as the first.  _fabricated()
        # stops the model inventing a number; this stops it making a claim the
        # evidence does not support -- feasibility, intent, causation, or
        # silence asserted as fact.  A model that says "this looks like fraud"
        # has broken provenance exactly as badly as one that says "47.2 months",
        # so it is discarded the same way and the deterministic stub answers.
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
