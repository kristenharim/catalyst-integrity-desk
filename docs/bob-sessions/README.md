# Bob task exports

Raw transcripts of the IBM Bob sessions that built this project, exported with
`Bob: Export Current Task`. They are the record of what Bob did, kept because a
summary written afterwards is not evidence of anything.

Each file is one task: the prompt, every file read, every command run, every
edit, and the reasoning between them. `docs/BOB_LOG.md` says which rows are Bob's
work and which preceded it; these files are what that log is checked against.

| file | phase | what it covers |
|---|---|---|
| `phase2-governance-port.json` | Phase 2, Prompt 1 | The governance port. Copies the ledger, challenge, classifier and Granite modules out of the fallback project, rewrites the two prompt strings for catalyst vocabulary, and keeps `_fabricated()` byte for byte. Adds `engine/contract.py`, the flattener from a `CatalystContract` to the packet `scan_breaches` reads. |
| `phase3-repair-and-widening.json` | Phase 3, repair and widening | The integrity badge. `GET /redline/confirm` had been reading its badge from `?intact=` in the URL, set once at decision time, so the tamper demo showed green on a corrupted ledger. Bob wrote the failing test first and watched it fail before fixing the handler to call `verify()` at render time. Also the `--displays` flag, `/redline` added to the provenance test, and a `PORT` env var because macOS ControlCenter holds 5000. Built on the second Bob trial: the first hit its cap partway through this same task, after reading the files and before writing anything. Also contains the widening that followed in the same task: `TICKERS` extended to BEAM and SRPT, a live Granite rebuild, and the first row the flagged section has ever rendered. One Bob task, so one file, exported twice and kept at its fuller version. |
| `phase3-console.json` | Phase 3, Prompt 3 | The console, all of it. One task that was told to stop after sub-task 1 and carried on through sub-task 6: `make_snapshot.py`, `app.py`, five templates, `test_console.py`. Contains the rate-limit episode, where free-tier congestion on watsonx forced the retry-with-backoff design rather than a silent stub fallback. Also contains the provenance check being seen to fail: a literal `9999` planted in the detail template, the test naming that token, then its removal. |
| `phase2-redline-loop.json` | Phase 2, Prompt 2 | The redline loop: `as_directions`, `ContractDelta`, `run_redline`, and the fabrication tests. Read the second half. Two tests passed while proving nothing: one asserted Granite had not fabricated without checking Granite had been reached, so the stub fallback satisfied it, and the other imported `run_redline` and never called it. Both were reported, both were fixed, and Bob ran the bad-endpoint probe itself rather than taking the report on trust. |

## Credentials

These exports are committed, so they are checked for secrets first. Bob runs with
"Respect .gitignore" on and so cannot read `.env` at all. The only matches for
the credential names are the `...` placeholders in the `granite.py` docstring.

Scan before adding a new export. The pattern deliberately excludes a literal
`...` so a placeholder does not read as a finding:

```bash
grep -oE '(WATSONX_[A-Z_]+)=[^.<"\ ]{6,}' docs/bob-sessions/*.json
```

Anything returned other than a `WATSONX_URL` pointing at a public regional
endpoint is a real credential and must not be committed.
