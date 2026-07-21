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
