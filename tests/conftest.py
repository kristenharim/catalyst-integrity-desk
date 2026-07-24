"""Runtime-state isolation for the whole suite.

The console writes three files under the repository's real `data/`: the
hash-chained ledger `decisions.jsonl`, the rejection store `review_log.jsonl`,
and the external anchor `ledger.anchor`. All three are live demo state. A test
that writes one leaves the repo carrying a decision nobody made, and the tamper
demo in `README.md` then opens on a console that is already approved, already
tampered, or already truncated.

Eight test modules each monkeypatched those paths by hand, and one path was not
covered: `tests/test_console.py::test_badge_flips_on_tampered_ledger` redirected
the ledger and the review log but not the anchor, so `POST /redline/decide`
reached `anchor_record` on the real `ANCHOR_PATH` and `pytest tests/` on a clean
tree created `data/ledger.anchor`. Per-test patching is fail-open by shape: it
holds for the tests that remembered and for no others, and the correction is
always written after the leak.

So the redirect happens once, here, for every test. Two fixtures, and they do
different jobs:

  `_isolated_runtime_state` prevents the write. It is autouse, so a test written
  from here on is isolated without doing anything, and a test that patches these
  paths itself still wins, because its `monkeypatch` runs after this one.

  `_real_runtime_files_are_untouched` detects any write that got past that, from
  any path, including one this file does not know about. It reads the three real
  paths before the session and again after it, and fails the run on a byte of
  difference or on a file that appeared. It is the check, not the guard: prevent
  first, then prove the prevention held.
"""
from __future__ import annotations

import hashlib
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import console.app as console_app             # noqa: E402
import orchestrator.anchor as anchor          # noqa: E402

# Read at import, before any fixture can redirect them, so the session guard
# below is always looking at the repository's real files.
REAL_RUNTIME_FILES = [
    os.path.abspath(console_app.DECISIONS_PATH),
    os.path.abspath(console_app.REVIEW_LOG_PATH),
    os.path.abspath(console_app.ANCHOR_PATH),
]


def _digest(path: str) -> str | None:
    """The file's content hash, or None when it does not exist."""
    if not os.path.exists(path):
        return None
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


@pytest.fixture(autouse=True)
def _isolated_runtime_state(tmp_path, monkeypatch):
    """Every test's console state lives in its own temp directory."""
    for name in ("DECISIONS_PATH", "REVIEW_LOG_PATH", "ANCHOR_PATH"):
        real = getattr(console_app, name)
        monkeypatch.setattr(console_app, name,
                            str(tmp_path / os.path.basename(real)))
    # `orchestrator.anchor.record` and `.check` fall back to this when a caller
    # passes no path. The console always passes one; a test calling them
    # directly need not, and that is the second door to the same file.
    monkeypatch.setattr(anchor, "ANCHOR_PATH", str(tmp_path / "ledger.anchor"))


@pytest.fixture(scope="session", autouse=True)
def _real_runtime_files_are_untouched():
    before = {path: _digest(path) for path in REAL_RUNTIME_FILES}
    yield
    after = {path: _digest(path) for path in REAL_RUNTIME_FILES}
    changed = sorted(path for path in REAL_RUNTIME_FILES
                     if before[path] != after[path])
    assert not changed, (
        "the test run wrote the repository's live console state, so the demo is "
        "no longer in the state the reader left it in: "
        + ", ".join(f"{os.path.relpath(p)} "
                    f"({'created' if before[p] is None else 'modified'})"
                    for p in changed)
    )
