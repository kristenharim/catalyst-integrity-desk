"""The seam is a convention until something checks it.

The whole argument for demo mode being evidence about the product is that both
modes run one computation path. That holds only while the compute layer cannot
tell where its inputs came from -- and "cannot" has to mean structurally, not
"nobody has done it yet".

So: walk the imports. `engine/` and `orchestrator/` may not import `evidence`,
because the moment one of them does, it can branch on `origin == "live"` and the
two modes are free to drift while every test stays green.

Verified failing before it was trusted: adding `from evidence import
EvidenceSnapshot` to `engine/gap.py` fails this with the file named.
"""
from __future__ import annotations

import ast
import os

REPO = os.path.join(os.path.dirname(__file__), "..")

# Packages that do arithmetic on evidence. They accept a snapshot; they never
# fetch one, and they never learn which kind it is.
COMPUTE = ("engine", "orchestrator")

# The acquisition boundary itself, plus anything that only it may reach.
ACQUISITION = ("evidence",)


def _parse(path: str) -> ast.Module:
    with open(path) as f:
        try:
            return ast.parse(f.read(), filename=path)
        except SyntaxError as exc:                      # pragma: no cover
            raise AssertionError(f"{path} does not parse: {exc}") from exc


def _names(nodes) -> set[str]:
    found: set[str] = set()
    for node in nodes:
        if isinstance(node, ast.Import):
            for a in node.names:
                found.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                found.add(node.module.split(".")[0])
    return found


def _imports(path: str) -> set[str]:
    """Every import anywhere in the file, including inside functions.

    Deliberately includes function-level imports: a lazy import still creates
    the dependency, and hiding a boundary violation inside a function would
    defeat the check this file exists for.
    """
    return _names(ast.walk(_parse(path)))


def _module_level_imports(path: str) -> set[str]:
    """Imports executed when the module is merely imported.

    Distinct from the above because the two answer different questions. The
    boundary check cares about any dependency at all; the lazy-import check
    cares only about what loading the module drags in with it.
    """
    return _names(_parse(path).body)


def _py_files(pkg: str) -> list[str]:
    root = os.path.join(REPO, pkg)
    out = []
    for dirpath, _dirs, files in os.walk(root):
        if "__pycache__" in dirpath:
            continue
        out.extend(os.path.join(dirpath, f) for f in files if f.endswith(".py"))
    return out


def test_compute_layer_cannot_reach_the_acquisition_layer():
    """engine/ and orchestrator/ must not import evidence/.

    If this fails, the failure is not a style violation. It means a module that
    computes a displayed number is able to ask whether it is running against a
    frozen file or a live API, and therefore able to answer differently.
    """
    offenders = []
    for pkg in COMPUTE:
        for path in _py_files(pkg):
            leaked = _imports(path) & set(ACQUISITION)
            if leaked:
                offenders.append(f"{os.path.relpath(path, REPO)} imports {sorted(leaked)}")
    assert not offenders, (
        "the compute layer reached across the seam:\n  "
        + "\n  ".join(offenders)
        + "\nOne computation path is the reason the demo is evidence about the "
          "product. A module that can see 'origin' can branch on it."
    )


def test_the_seam_itself_is_where_the_engine_is_imported():
    """evidence/provider.py is allowed to import the engine, and is the only
    place in that package that does. Stated as a test so the dependency runs one
    way and the direction is not quietly reversed later.
    """
    provider = os.path.join(REPO, "evidence", "provider.py")
    assert "engine" not in _module_level_imports(provider), (
        "engine imports in provider.py must stay inside the function that uses "
        "them, so importing the module does not pull in the network stack"
    )
    with open(provider) as f:
        body = f.read()
    assert "from engine." in body, (
        "provider.py is the adapter to the verified engine modules; if it no "
        "longer calls them, the live path has grown its own arithmetic"
    )


def test_no_compute_module_reads_the_clock_for_classification():
    """`date.today()` inside the compute layer is how a committed artifact
    silently reinterprets itself. `engine/gap.py` still has one, deliberately and
    documented in LIMITS.md, so this pins the count rather than banning it: a new
    one has to be argued for.
    """
    hits = []
    for pkg in COMPUTE:
        for path in _py_files(pkg):
            with open(path) as f:
                for i, line in enumerate(f, 1):
                    if "date.today()" in line and not line.lstrip().startswith("#"):
                        hits.append(f"{os.path.relpath(path, REPO)}:{i}")
    assert len(hits) <= 2, (
        f"wall-clock reads in the compute layer grew to {len(hits)}: {hits}. "
        "Each one makes a stored result depend on when it is read. See the "
        "'Lapsed-versus-future' section of docs/LIMITS.md before adding another."
    )
