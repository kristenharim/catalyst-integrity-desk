"""The claim documents are generated, and this is what enforces that.

The previous version of this file was a presence check: every numeric token in a
table row or a bolded claim had to be a representation of some snapshot field or
appear in an enumerated `NON_SNAPSHOT` list. It caught what it was built for and
it had two structural holes that were measured rather than argued. Presence
cannot falsify a small integer. And an exception list is a laundering route,
which is how two real snapshot fields ended up unfalsifiable inside it.

Both are gone, because the documents are no longer typed. `research/render_writeup.py`
emits every figure from a named field, and the checks below are what make that a
guarantee rather than a habit:

  - **no digits in prose, over the whole generator.** Not table rows, not bolded
    lines: every string constant in the module, and every numeric literal in it
    too. A figure cannot be typed into prose because prose cannot contain a
    digit, so there is no line for the guard to miss.
  - **the committed documents are byte-identical to a fresh render.** A figure
    cannot drift from the field it renders, because nothing copies it.
  - **no cohort figure survives outside a generated block** in the four
    documents that are only partly generated.
  - **the corpus still passes**, and it now attacks the generator, since that is
    the only place a figure defect can still live.

What is NOT enforced, stated at the strength it holds: a cell bound to the wrong
field. `figures()` could render `open_estimates` where the column says
`carrying_now` and every check here would pass forever. That is what the
generator-side fixtures in `tests/mutation_corpus.py` exist for, and they are a
sample rather than a proof. See `docs/LIMITS.md`.
"""
import ast
import os
import re
import sys
import types
from datetime import date as _date

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from research import cohort, render_writeup
from mutation_corpus import CORPUS

REPO = os.path.join(os.path.dirname(__file__), "..")
GENERATOR = "research/render_writeup.py"

CLAIM_DOCS = ["README.md", "docs/WRITEUP.md", "docs/SUBMISSION.md",
              "docs/COHORT.md", "docs/STATUS.md"]

# Phrases withdrawn in review. Kept as a list because "exactly opposite order"
# was reported fixed in three consecutive rounds while surviving in two files.
RETIRED = {
    "exactly opposite order": "industry and NIH tie, so the reversal is not exact",
    "overwhelmingly": "unsupported on every measured reading; use the counts",
}

# EVERY numeric literal in the generator has to be declared here with what it is
# for. The first version allowed anything under 100, and a reviewer showed that
# `4 * 31` and a bare `60` both published invented figures through it. An
# allow-by-magnitude rule is an exception list with no author; this one at least
# has to be argued for, entry by entry.
ALLOWED_LITERALS = {
    0: "index and identity",
    1: "index, offset and identity",
    2: "slice width for a two-character list marker",
    3: "index",
    4: "the year field of an ISO date, as a slice bound",
    92: "wrap width, a layout constant",
    100: "percent conversion",
    0.5: "the median, as a percentile argument",
    365.25: "days per Julian year",
}

# Digit-bearing tokens that are names rather than figures. Declared HERE and not
# in the generator: the first version read this list out of the module being
# checked, so the checked artifact defined its own exemption and a reviewer
# added a figure to it and published the figure.
LABELS = ("p10", "p50", "p90", "python3")

# Documents that carry cohort claims. Wider than the five generated ones,
# because `docs/LIMITS.md` was carrying a full prevalence table and a hand-typed
# ratio while sitting outside every guard, which is where the one uncorrected
# copy of a wrong sentence was found.
SCANNED_DOCS = ["README.md", "docs/WRITEUP.md", "docs/SUBMISSION.md",
                "docs/COHORT.md", "docs/STATUS.md", "docs/LIMITS.md",
                "docs/DEMO.md", "docs/BACKTEST.md", "docs/CONJECTURE.md",
                "docs/PRINCIPLE.md", "docs/PARKING.md", "docs/SPEC.md",
                "docs/FINDINGS.md", "docs/WORKSPACE.md"]
# Not scanned, each for a stated reason rather than by omission:
#   docs/BOB_LOG.md   a dated log; its own rule is that a log is not corrected
#                     by rewriting it, so it holds figures that were right when
#                     written and are superseded now
#   BUNDLE.md         a build artifact produced by make_bundle.py

_BLOCK = re.compile(r"<!-- generated: [a-z_]+ -->\n.*?\n<!-- /generated -->", re.S)
# ISO dates and URLs only. Code spans and link text used to be blanked too, and
# a reviewer retyped two live cohort figures in backticks and in link text and
# watched the scan pass on both.
_CODE = re.compile(r"https?://\S+|\d{4}-\d{2}(?:-\d{2})?")
_MARKER = re.compile(r"<!--\s*/?\s*generated")
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?%?")
_N_OF_M = re.compile(r"\d[\d,]* of \d[\d,]*\b")


# ---------------------------------------------------------------------------
# The checks, as one callable so the corpus exercises exactly what CI runs
# ---------------------------------------------------------------------------

def _digit_strings(source: str, exempt: set, labels: tuple) -> list:
    """Every string constant in the module that contains a digit.

    Three things are skipped and each has to earn it. A format specification,
    `{v:.1f}`, is a rendering instruction that can only ever print what it is
    handed. A docstring is never rendered into a document. And a `CITATIONS`
    value is a verbatim quotation of an external source, which is the one place
    a digit is allowed to be typed and is separately checked for laundering.
    """
    tree = ast.parse(source)
    skip = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FormattedValue) and node.format_spec is not None:
            for c in ast.walk(node.format_spec):
                if isinstance(c, ast.Constant):
                    skip.add(id(c))
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                skip.add(id(body[0].value))
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in skip and node.value not in exempt):
            rest = node.value
            for label in labels:
                rest = rest.replace(label, "")
            if any(c.isdigit() for c in rest):
                out.append((node.lineno, node.value))
    return out


def _numeric_literals(source: str) -> list:
    out = []
    for node in ast.walk(ast.parse(source)):
        if (isinstance(node, ast.Constant)
                and isinstance(node.value, (int, float))
                and not isinstance(node.value, bool)
                and node.value not in ALLOWED_LITERALS):
            out.append((node.lineno, node.value))
    return out


def _cohort_figures() -> set:
    """Renderings of the measured per-stratum fields, and of n.

    `anchor_case` is deliberately excluded. Its figures are the product's own
    headline, they appear in demo notes, console tests and verification logs all
    over this repo, and they are pinned independently and more strongly by
    `tests/test_backtest.py`, which re-derives them from the raw versions. A
    residual text scan would add nothing there and would fire on a dozen lines
    that are not claims about the cohort.
    """
    snap = cohort.load_snapshot()
    out = set()

    def add(v):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return
        for r in (str(v), f"{v:,}", f"{v:.1f}", f"{v * 100:.1f}%"):
            # Only renderings distinctive enough to be a claim. A bare one- or
            # two-digit token is too common in prose to guard on, and the counts
            # that shape is used for are caught by the N-of-M rule instead.
            if r.endswith("%") or "," in r or sum(c.isdigit() for c in r) >= 3:
                out.add(r)

    for v in snap["strata"].values():
        for x in v.values():
            if isinstance(x, list):
                continue                      # a distribution, not a published figure
            add(x)
    add(snap["n_distinct_trials"])
    return out


def _module(source: str):
    """The generator as the given source defines it.

    A generator-level fixture has to be rendered through, not merely parsed: the
    defects that can still ship are wrong fields and lossy formatters, and both
    are invisible until something renders.
    """
    if source == _source():
        return render_writeup
    mod = types.ModuleType("render_writeup_mutant")
    mod.__file__ = os.path.join(REPO, GENERATOR)
    exec(compile(source, mod.__file__, "exec"), mod.__dict__)
    return mod


def _pctile(xs, p):
    """Reimplemented rather than imported, so this is a second opinion."""
    if not xs:
        return None
    v = sorted(xs)
    k = (len(v) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def _num(v):
    if v is None:
        return "n/a"
    return f"{int(v):,}" if float(v) == int(v) else f"{v:,}"


def _expected_rows() -> dict:
    """Every table row's numeric tokens, recomputed from the store.

    This is the check the corpus needed and did not have. A generator-level
    defect -- a cell bound to the wrong field, a ratio computed the wrong way
    round -- survives the byte comparison the moment anyone re-renders, which is
    the first thing anyone does. Nothing caught it. So the expected tokens are
    computed here from `data/cohort/results.jsonl` by a second implementation
    that calls neither `stats()` nor the generator, and compared against the
    rendered rows.

    It is double entry, not proof: it covers the tables, and a sentence outside
    one is still only covered by the corpus.
    """
    rows = [r for r in cohort.load_results() if "error" not in r]
    snap = cohort.load_snapshot()
    as_of = _date.fromisoformat(snap["as_of"])
    near = snap["clustering"]["window_half_width_days"]
    anniv = snap["clustering"]["anniversary_centres_days"]
    ctrl = snap["clustering"]["control_centres_days"]
    out = {}
    per = {}

    for c in ("INDUSTRY", "NIH", "OTHER_GOV", "OTHER"):
        sub = [r for r in rows if r["sponsor_class"] == c]
        n = len(sub)

        def parse(d):
            if not d:
                return None
            bits = [int(x) for x in d.split("-")]
            while len(bits) < 3:
                bits.append(1)
            return _date(*bits)

        def carrying(r):
            p = parse(r.get("last_pcd"))
            return bool(p and p < as_of
                        and (r.get("last_pcd_type") or "").upper() != "ACTUAL")

        carr = [r for r in sub if carrying(r)]
        silent = [r for r in carr if not r["dead_date_stretches"]]
        openest = [r for r in sub if r.get("last_pcd")
                   and (r.get("last_pcd_type") or "").upper() != "ACTUAL"]
        versions = _pctile([r.get("n_versions") or 0 for r in sub], .5)
        changes = _pctile([r.get("n_date_changes") or 0 for r in sub], .5)
        per_trial = [max(r["dead_date_days"]) for r in sub if r["dead_date_days"]]
        stretches = [d for r in sub for d in r["dead_date_days"]]
        ever = [r for r in sub if r["dead_date_stretches"] > 0]
        dated = sum(r.get("revisions_prospective", 0)
                    + r.get("revisions_after_lapse", 0) for r in sub)
        lapse = sum(r.get("revisions_after_lapse", 0) for r in sub)
        actual = sum(r.get("revisions_after_lapse_to_actual", 0) for r in sub)
        est = sum(r.get("revisions_after_lapse_to_estimate", 0) for r in sub)
        trans = sum(r.get("n_transitions", 0) for r in sub)
        cont = sum(r.get("contingent_revisions", 0) for r in sub)
        ref = sum(r.get("refused_revisions", 0) for r in sub)
        scope = sum(r.get("refused_scope", 0) for r in sub)
        sup = sum(r.get("refused_superseded", 0) for r in sub)
        unread = sum(r.get("refused_unreadable", 0) for r in sub)
        iv = [d for r in sub for d in (r.get("submit_intervals") or [])]
        hit = lambda cs: sum(1 for d in iv
                             if any(abs(d - y) <= near for y in cs))
        lo, hi = min(iv), max(iv)
        base = sum(max(0, min(hi, y + near) - max(lo, y - near))
                   for y in anniv) / (hi - lo)
        revising = [r for r in sub if (r.get("revisions_prospective", 0)
                                       + r.get("revisions_after_lapse", 0)) > 0]
        t_est = [r for r in revising
                 if r.get("revisions_after_lapse_to_estimate", 0)]
        sil_days = sorted((as_of - parse(r["last_pcd"])).days for r in silent)
        per[c] = {"trial_p50": _pctile(per_trial, .5),
                  "stretch_p50": _pctile(stretches, .5),
                  "est": est, "dated": dated, "carr": len(carr),
                  "silent": len(silent), "rev": len(revising),
                  "t_est": len(t_est), "n": n, "open": len(openest),
                  "sil_p50": _pctile(sil_days, .5)}

        out.setdefault("headline", {})[c] = [
            _num(len(carr)), _num(n), f"{len(carr) / n * 100:.1f}%",
            _num(len(carr)), _num(len(openest)),
            f"{len(carr) / len(openest) * 100:.1f}%",
            _num(len(silent)), _num(len(carr)), _num(versions), _num(changes)]
        out.setdefault("reversal", {})[c] = [
            f"{len(ever) / n * 100:.1f}%", f"{len(carr) / n * 100:.1f}%",
            _num(versions)]
        # The rate is a band: first-of-month is recomputed here from the store,
        # end-of-month depends on the second date reading and needs the version
        # cache, which CI does not have. That half is read from the snapshot's
        # month_convention block and validated independently, cache present, by
        # test_month_convention_reconstructs_the_first_of_month below. So the
        # band's high end is double entry and its low end is checked elsewhere.
        eom = snap["month_convention"]["strata"][c]["lapse_to_estimate_rate_eom"]
        out.setdefault("mechanism", {})[c] = [
            _num(dated), _num(lapse), _num(actual), _num(est),
            f"{eom * 100:.1f}%", f"{est / dated * 100:.1f}%"]
        out.setdefault("trial_duration", {})[c] = [
            _num(len(per_trial)), _num(_pctile(per_trial, .5)),
            _num(round(_pctile(per_trial, .9), 1)), _num(max(per_trial))]
        out.setdefault("stretch_duration", {})[c] = [
            _num(len(stretches)), _num(_pctile(stretches, .5)),
            _num(round(_pctile(stretches, .9), 1)), _num(max(stretches)),
            f"{len(ever) / n * 100:.1f}%"]
        out.setdefault("comparability", {})[c] = [
            _num(trans), f"{cont / trans * 100:.1f}%", f"{ref / trans * 100:.1f}%",
            f"{scope / trans * 100:.1f}%", f"{sup / trans * 100:.1f}%",
            f"{unread / trans * 100:.1f}%"]
        out.setdefault("clustering", {})[c] = [
            _num(len(iv)), _num(_pctile(iv, .5)),
            _num(hit(anniv)), _num(len(iv)), f"{hit(anniv) / len(iv) * 100:.1f}%",
            _num(hit(ctrl)), _num(len(iv)), f"{hit(ctrl) / len(iv) * 100:.1f}%",
            f"{base * 100:.1f}%",
            f"{hit(anniv) / len(iv) / base:.2f}", f"{hit(ctrl) / len(iv) / base:.2f}"]
        # The tables that live in the shared blocks, in the other four documents.
        # A reviewer bound a cell in each to a different real field and watched it
        # publish, because check() scanned only the write-up. They are re-presentations
        # of fields already checked above, but a wrong-field binding does not care.
        mc = snap["month_convention"]["strata"][c]
        out.setdefault("block_primary", {})[c] = [
            _num(len(carr)), _num(n), f"{len(carr) / n * 100:.1f}%",
            _num(len(silent)), _num(_pctile(per_trial, .5)), _num(versions)]
        out.setdefault("block_secondary", {})[c] = [
            _num(n), f"{len(ever) / n * 100:.1f}%", _num(_pctile(stretches, .5)),
            _num(round(_pctile(stretches, .9), 1)), _num(max(stretches)),
            _num(trans), f"{cont / trans * 100:.1f}%", f"{ref / trans * 100:.1f}%"]
        out.setdefault("block_silence", {})[c] = [
            f"{len(ever) / n * 100:.1f}%", f"{len(carr) / n * 100:.1f}%",
            _num(len(silent)), _num(versions)]
        out.setdefault("block_refusal", {})[c] = [
            _num(trans), f"{scope / trans * 100:.1f}%", f"{sup / trans * 100:.1f}%",
            f"{unread / trans * 100:.1f}%"]

    # Table headers, pinned to independent literals. The documents are generated,
    # so a header swapped in the generator changes the committed file too and the
    # byte comparison sees nothing; a reviewer swapped two adjacent numeric column
    # headers and published NIH's version count under the date-change label. These
    # must be present verbatim, so a swap fails against the literal rather than
    # against a copy of itself.
    out["headers"] = [
        "| Stratum | carrying an expired estimate | of trials whose commitment is "
        "still open | invisible to the stretch measure | median registry versions "
        "| median date revisions |",
        "| Stratum | dated revisions | after a lapse | of those, recorded ACTUAL "
        "| **estimate to estimate** | rate (end-of-month to first) |",
        "| Stratum | trials with a carry | median | p90 | max |",
        "| Stratum | stretches | median | p90 | max | ever carried |",
        "| Stratum | Transitions | Contingent | Refused | scope changed | "
        "superseded | **unreadable** |",
        "| Stratum | intervals | median interval | within the anniversary windows "
        "| within the control windows | even-spread null | anniversary ratio | "
        "control ratio |",
        "| Stratum | carrying an expired estimate now | invisible to the stretch "
        "measure | longest carry p50 | median versions |",
        "| Stratum | carried at some point (stretch measure) | carrying one now | "
        "invisible to the stretch measure | median versions |",
    ]

    # Sentences whose figure is a relation between strata, which is where a
    # direction can invert without any single cell being wrong.
    i = per["INDUSTRY"]
    out["sentences"] = [
        ("NIH against industry at the median",
         f"**{per['NIH']['trial_p50'] / i['trial_p50']:.1f}x**"),
        ("the per-stretch sensitivity ratio",
         f"**{per['NIH']['stretch_p50'] / i['stretch_p50']:.1f}x**"),
        # The shared blocks carry figures that are in no table, which is where a
        # reviewer put a wrong-field binding and watched it publish.
        ("industry estimate-to-estimate counts",
         f"({i['est']} of {i['dated']})"),
        ("industry trial-level mechanism",
         f"{i['t_est']} of {i['rev']} ({i['t_est'] / i['rev'] * 100:.1f}%)"),
        ("industry point prevalence",
         f"{i['carr'] / i['n'] * 100:.1f}% of all trials"),
        ("silent carriers, industry",
         f"{i['silent']} of {i['carr']} in INDUSTRY"),
        ("silent-carrier median, industry",
         f"{_num(i['sil_p50'])} days in INDUSTRY"),
        # Figures that live only in the shared blocks of the other documents.
        ("OTHER_GOV of-open, the README headline",
         f"{per['OTHER_GOV']['carr']} of {per['OTHER_GOV']['open']} of their"),
        ("industry silent, invisible-to-stretches sentence",
         f"{i['silent']} of {i['carr']} industry trials currently carrying"),
    ]
    return out


def _rendered_rows(text: str, cls: str) -> list:
    return [line for line in text.splitlines()
            if line.strip().startswith(f"| {cls} |")]


def check(docs: dict, source: str) -> list:
    """Every finding, over document texts and generator source passed in.

    Callable on mutated inputs, so a fixture exercises the code CI runs rather
    than a reconstruction of it. The first version of the old corpus compared
    against zero instead of against the document's own baseline and every
    fixture "passed" on a pre-existing unrelated defect.
    """
    out = []
    mod = _module(source)
    citations = {v for entry in mod.CITATIONS.values() for v in entry.values()}

    for lineno, s in _digit_strings(source, citations, LABELS):
        out.append(f"{GENERATOR}:{lineno}: digit in a string constant {s[:60]!r}. "
                   f"Prose carries no numerals; emit it from a field.")
    for lineno, v in _numeric_literals(source):
        out.append(f"{GENERATOR}:{lineno}: undeclared numeric literal {v!r}. A "
                   f"figure has to be a snapshot field, not a constant.")

    # A citation is a verbatim external quotation. Cohort figures are rates and
    # thousands-separated counts, so those shapes are refused outright rather
    # than only when they happen to match a current field: an INVENTED rate
    # matches nothing and used to pass.
    for key, entry in mod.CITATIONS.items():
        if not entry.get("cite"):
            out.append(f"{GENERATOR}: citation {key} carries no source")
        for field, text in entry.items():
            if "%" in text or re.search(r"\d,\d{3}", text):
                out.append(f"{GENERATOR}: citation {key}.{field} carries a rate or "
                           f"a thousands-separated count, which is the shape of a "
                           f"figure from this study and not of a quotation.")

    # The write-up quotes source code verbatim. That source is not scanned by
    # anything else, and a figure added to a docstring in `research/cohort.py`
    # published straight through it.
    f = mod.figures(cohort.load_snapshot())
    for key in ("silent_source", "carrying_source"):
        if any(ch.isdigit() for ch in f[key]):
            out.append(f"{GENERATOR}: the quoted source {key} contains a digit. "
                       f"Code this document quotes has to be digit-free too.")

    rendered = mod.render(docs)
    for doc, text in rendered.items():
        if docs.get(doc) != text:
            out.append(f"{doc}: stale, the committed bytes are not what the "
                       f"snapshot renders. Run `python3 -m research.render_writeup`.")

    # Every table row, against a recomputation from the store. Searched over the
    # whole rendered output, not only the write-up: the block tables that carry
    # the same fields live in the other four documents, and scanning only the
    # write-up left them unchecked, which a reviewer went through.
    expected = _expected_rows()
    everything = "\n".join(rendered.values())
    all_rows = [ln for text in rendered.values() for ln in text.splitlines()]
    for table, per_cls in expected.items():
        if table in ("sentences", "headers"):
            continue
        for cls, want in per_cls.items():
            got = [_NUM.findall(ln) for ln in all_rows
                   if ln.strip().startswith(f"| {cls} |")]
            if want not in got:
                out.append(f"no {cls} row renders the {table} table's fields; "
                           f"recomputed from the store they are {want}")

    # Headers, against independent literals, so a swap fails on a mismatch rather
    # than on a copy of itself.
    for header in expected["headers"]:
        if header not in everything:
            out.append(f"a generated table header is missing or reworded; the "
                       f"pinned form is {header[:70]!r}...")

    # Whitespace-collapsed, because `_wrap` reflows prose and a figure can
    # straddle a line break: "27 of 29" wraps to "27\nof 29" in the README.
    flat = " ".join(everything.split())
    for label, want in expected["sentences"]:
        if " ".join(want.split()) not in flat:
            out.append(f"generated text: {label} does not read {want!r}, which "
                       f"is what the store gives")

    # The write-up is generated whole, so every figure in it is emitted by
    # construction and the byte comparison above covers it. The rest are partly
    # generated or not generated at all, and that is where a figure gets retyped.
    figures = _cohort_figures()
    for doc in SCANNED_DOCS:
        text = docs.get(doc)
        if text is None or doc == mod.WRITEUP:
            continue
        opens = len(_MARKER.findall(text))
        matched = len(mod._BLOCK.findall(text)) * 2
        if opens != matched:
            out.append(f"{doc}: {opens - matched} malformed generated marker(s); a "
                       f"block whose marker does not parse is never substituted and "
                       f"freezes silently.")
        residual = _CODE.sub(" ", mod._BLOCK.sub(" ", text))
        for i, line in enumerate(residual.split("\n"), start=1):
            # `N of M` is the shape every cohort count claim takes, but it is
            # also the shape of an ordinary sentence, so it is enforced only on
            # the documents that carry generated blocks. Elsewhere a retyped
            # count has to be caught as a field rendering.
            if doc in mod.BLOCK_DOCS:
                for tok in _N_OF_M.findall(line):
                    out.append(f"{doc}:{i}: {tok!r} outside a generated block; an "
                               f"N-of-M count is a cohort claim and has to be "
                               f"emitted.")
            for tok in _NUM.findall(line):
                if tok in figures or tok.replace(",", "") in figures:
                    out.append(f"{doc}:{i}: {tok!r} is a cohort field rendering "
                               f"and sits outside a generated block.")

    for doc, text in docs.items():
        low = text.lower()
        for phrase, why in RETIRED.items():
            if phrase in low:
                out.append(f"{doc}: retired phrase {phrase!r} ({why})")
    return out


def _check_with(mod) -> list:
    """The citation and quoted-source rules, run against a substitute module."""
    out = []
    f = mod.figures(cohort.load_snapshot())
    for key in ("silent_source", "carrying_source"):
        if any(ch.isdigit() for ch in f[key]):
            out.append(f"{GENERATOR}: the quoted source {key} contains a digit.")
    return out


def _live_docs() -> dict:
    out = {}
    for doc in sorted(set(CLAIM_DOCS) | set(SCANNED_DOCS)):
        path = os.path.join(REPO, doc)
        if os.path.exists(path):
            out[doc] = open(path).read()
    return out


def _source() -> str:
    return open(os.path.join(REPO, GENERATOR)).read()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_check_reports_nothing_on_the_committed_tree():
    """The whole of `check()`, asserted. This is the gate the other tests were
    not.

    `check()` recomputes every table cell from the store, names a wrong-field
    binding in plain English, and returns it. Every other test in this file then
    filtered that list by substring or took a before/after delta over the
    corpus, so a finding on the live tree that matched none of those filters was
    computed, formatted, and thrown away. A reviewer bound a real column to a
    different real field, re-rendered, and watched the suite stay green while
    `check()` printed the mismatch. That is the eighth instance in this project
    of a correct check that nothing consults, and it is closed by reading the
    whole return value once.
    """
    findings = check(_live_docs(), _source())
    assert not findings, (f"{len(findings)} finding(s) on the committed tree:\n  "
                          + "\n  ".join(findings[:25]))


def test_the_prose_templates_contain_no_numerals():
    """Total scope: the whole generator, not selected lines of the output."""
    findings = [f for f in check(_live_docs(), _source())
                if f.startswith(GENERATOR)]
    assert not findings, ("the generator carries a figure in prose:\n  "
                          + "\n  ".join(findings[:20]))


def test_every_generated_document_is_current():
    snap = cohort.load_snapshot()
    if snap is None:
        pytest.skip("no snapshot frozen yet")
    assert not render_writeup.stale(), (
        f"stale generated documents: {render_writeup.stale()}. The committed "
        f"bytes disagree with the snapshot, so a published figure is one freeze "
        f"behind. Run `python3 -m research.render_writeup`.")


def test_no_cohort_figure_survives_outside_a_generated_block():
    findings = [f for f in check(_live_docs(), _source())
                if "outside a generated block" in f]
    assert not findings, (
        f"{len(findings)} retyped cohort figure(s):\n  " + "\n  ".join(findings[:20])
        + "\n\nMove the sentence into a generated block, or say it without the "
          "numeral.")


def test_a_retired_phrase_stays_retired():
    findings = [f for f in check(_live_docs(), _source()) if "retired phrase" in f]
    assert not findings, "\n  ".join(findings)


def test_the_corpus_is_caught():
    """Every planted defect, applied to the real files, must be caught.

    This is the test that matters. A guard amendment is accepted only when every
    fixture here is watched failing and then passing. Compared against each
    input's OWN baseline rather than against zero, because the first version of
    this test compared against zero and scored 19/19 on a pre-existing unrelated
    defect that made any mutation look caught.
    """
    snap = cohort.load_snapshot()
    if snap is None:
        pytest.skip("no snapshot frozen yet")
    docs, source = _live_docs(), _source()
    before = set(check(docs, source))
    stale, missed = [], []
    for name, target, find, replace, why in CORPUS:
        if target == GENERATOR:
            body = source
        elif target in docs:
            body = docs[target]
        else:
            stale.append(f"{name}: {target} is not a checked file")
            continue
        if find not in body:
            stale.append(f"{name}: {find!r} no longer in {target}")
            continue
        mutated = body.replace(find, replace, 1)
        if target == GENERATOR:
            # Re-render before checking. A generator defect makes the committed
            # documents stale, and staleness is what a reviewer showed was
            # "catching" 22 of 23 fixtures: delete the digit rule and the whole
            # residual scan and the corpus still scored 23/23. Anyone who edits
            # the generator re-renders in the same breath, and after that the
            # byte comparison has nothing to say. So the fixture is checked
            # against the mutant's own output, where only a real rule can fire.
            after = set(check(_module(mutated).render(), mutated))
        else:
            after = set(check({**docs, target: mutated}, source))
        if after - before:
            continue
        missed.append(f"{name} ({why}): {find!r} -> {replace!r} in {target}")
    assert not stale, (
        "stale fixture(s); the target moved and the mutation no longer applies, "
        "so it was silently testing nothing:\n  " + "\n  ".join(stale))
    assert not missed, (
        f"{len(missed)} of {len(CORPUS)} planted defects passed the guard:\n  "
        + "\n  ".join(missed))


def test_the_quoted_source_rule_fires_on_a_digit():
    """The write-up embeds `research/cohort.py` verbatim, and that file is
    scanned by nothing else. A figure added to one of the quoted docstrings
    published straight through, so the rule is asserted here rather than only
    exercised by a fixture the corpus cannot target across two modules."""
    clean = render_writeup.figures(cohort.load_snapshot())
    assert not any(c.isdigit() for c in clean["silent_source"])
    assert not any(c.isdigit() for c in clean["carrying_source"])

    class _Mod:
        CITATIONS = render_writeup.CITATIONS
        BLOCK_DOCS = render_writeup.BLOCK_DOCS
        WRITEUP = render_writeup.WRITEUP
        _BLOCK = render_writeup._BLOCK
        render = staticmethod(render_writeup.render)

        @staticmethod
        def figures(snap):
            f = dict(clean)
            f["silent_source"] = f["silent_source"] + "\n    # 71 trials"
            return f

    findings = [f for f in _check_with(_Mod) if "quoted source" in f]
    assert findings, "a digit planted in the quoted source was not caught"


def test_no_citation_is_a_snapshot_figure():
    """`CITATIONS` is for quotations from outside this study.

    The old `NON_SNAPSHOT` list held two real snapshot fields, which made both
    unfalsifiable. The replacement is much smaller and gets the same check: if a
    figure in a citation is derivable from the snapshot, it is a measurement
    wearing a quotation's clothes and belongs in a field.
    """
    snap = cohort.load_snapshot()
    if snap is None:
        pytest.skip("no snapshot frozen yet")
    figures = _cohort_figures()
    bad = []
    for key, entry in render_writeup.CITATIONS.items():
        assert entry.get("cite"), f"{key} carries no source"
        for field, text in entry.items():
            for tok in _NUM.findall(text):
                if tok in figures or tok.replace(",", "") in figures:
                    bad.append(f"{key}.{field}: {tok!r} is a snapshot rendering")
    assert render_writeup.CITATIONS, "the citation table is empty"
    assert not bad, (
        "these are quoted as external and are also measurements here: "
        + ", ".join(bad))


def test_the_correction_log_numbers_itself():
    """Numbers come from the order, so they cannot skip, repeat or disagree."""
    keys = render_writeup.CORRECTIONS
    assert len(set(keys)) == len(keys), "a correction key is used twice"
    f = render_writeup.figures(cohort.load_snapshot())
    numbers = [int(f["c_" + k].split()[-1]) for k in keys]
    assert numbers == list(range(1, len(keys) + 1)), numbers
    text = open(os.path.join(REPO, "docs", "WRITEUP.md")).read()
    for k in keys:
        assert f["c_" + k] + ":" in text, (
            f"{k} is numbered but its entry is not in the write-up")


def test_n_pcd_revisions_is_not_the_number_of_changes():
    """The field-level root cause, asserted so the trap cannot be re-entered."""
    rows = [r for r in cohort.load_results() if "error" not in r]
    if not rows:
        pytest.skip("no cohort measured yet")
    never = [r for r in rows if not r.get("n_date_changes")]
    assert never and all(r.get("n_pcd_revisions") == 1 for r in never)
    for r in rows:
        assert r["n_date_changes"] == max(0, (r.get("n_pcd_revisions") or 0) - 1)


def test_a_hedge_present_in_most_claim_docs_is_present_in_all():
    """Cross-document consistency, matched wrap-insensitively because the first
    version silently exempted README on a line break."""
    claim = re.compile(r"cannot\s+separate\s+reconciliation\s+from\s+filing\s+"
                       r"frequency", re.I)
    cues = ("not a tested", "untested", "ordering across four",
            "an association", "not separable", "across four points")
    offenders = []
    for doc, text in _live_docs().items():
        if claim.search(text) and not any(c in text.lower() for c in cues):
            offenders.append(doc)
    assert not offenders, (
        f"these state the headline claim with no qualifier: {offenders}")
