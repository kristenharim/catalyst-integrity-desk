"""The cache write has to be atomic, or one interrupted run poisons a trial forever.

`_cached()` wrote each fetched version straight to its target path. Kill a run
mid-write and the target is left truncated, and every later read of that trial
fails on it, because `_cached()` returns early whenever the path exists. It does
not retry and it cannot tell a short file from a complete one.

Observed twice. Once as `NCT03919071-v356.json`, 20,107 bytes, one file of 335,
which took down five tests that had nothing to do with it. Once as two NIH trials
in the random cohort, `NCT04269902` and `NCT04071223`, which stored a
`JSONDecodeError` in place of a measurement and dropped that stratum's n by two.

This is the test named in the amendment recorded in `docs/BOB_LOG.md`. It fails
against the pre-amendment `_cached()`, which leaves the truncated file in place.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine import ctgov_history


def test_interrupted_cache_write_leaves_no_readable_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(ctgov_history, "CACHE", str(tmp_path))
    monkeypatch.setattr(ctgov_history, "SLEEP", 0.0)
    monkeypatch.setattr(ctgov_history, "_get", lambda url: {"study": {"pcd": "2027-01-01"}})

    target = os.path.join(str(tmp_path), "NCT00000000-v7.json")
    real_dump = json.dump

    def interrupted(obj, fp, *a, **kw):
        fp.write('{"study": {"pcd": "2027-0')   # a real partial body, unparseable
        fp.flush()
        raise KeyboardInterrupt("run interrupted mid-write")

    monkeypatch.setattr(json, "dump", interrupted)
    with pytest.raises(KeyboardInterrupt):
        ctgov_history._cached("NCT00000000", 7)
    monkeypatch.setattr(json, "dump", real_dump)

    assert not os.path.exists(target), (
        "an interrupted write left a truncated cache entry at the target path; "
        "every later read of this trial will raise JSONDecodeError")

    # The point of the fix is the next run, which must fetch cleanly rather than
    # inherit the corpse. Same assertion the two failed cohort trials needed.
    assert ctgov_history._cached("NCT00000000", 7) == {"study": {"pcd": "2027-01-01"}}
    with open(target) as f:
        assert json.load(f) == {"study": {"pcd": "2027-01-01"}}


def test_cache_still_reads_back_what_it_wrote(tmp_path, monkeypatch):
    """Condition 3 of the amendment: no behaviour change on correct input.

    Write once through the network path, read once through the cache path, and
    assert the second call never reaches `_get`.
    """
    monkeypatch.setattr(ctgov_history, "CACHE", str(tmp_path))
    monkeypatch.setattr(ctgov_history, "SLEEP", 0.0)

    calls = []

    def once(url):
        calls.append(url)
        return {"study": {"protocolSection": {"statusModule": {}}}}

    monkeypatch.setattr(ctgov_history, "_get", once)
    first = ctgov_history._cached("NCT00000001", 3)
    second = ctgov_history._cached("NCT00000001", 3)
    assert first == second
    assert len(calls) == 1, "the cached path refetched"
    assert os.path.exists(os.path.join(str(tmp_path), "NCT00000001-v3.json"))
