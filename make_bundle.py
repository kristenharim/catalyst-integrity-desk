"""Concatenate the handoff into one file, for chats that cannot read the filesystem.

A Claude Code session in this repo needs none of this: it reads the files itself, and
attaching copies just invites the pasted version and the on-disk version to drift apart.
This exists for a plain chat window, where the alternative is attaching nine files and
hoping the read order survives.

Regenerate after editing any doc:  python3 make_bundle.py
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "BUNDLE.md")

# Order matters. It is the read order from HANDOFF.md, with the code last so the model
# has the framing before it sees anything it might be tempted to rewrite.
FILES = [
    "HANDOFF.md",
    "docs/SPEC.md",
    "docs/FINDINGS.md",
    "docs/PORT.md",
    "docs/BOB_PROMPTS.md",
    "docs/DEMO.md",
    "engine/runway.py",
    "engine/ctgov_history.py",
    "engine/gap.py",
]

HEADER = """# Catalyst Integrity Desk: complete handoff bundle

Every handoff document and every line of verified engine code, concatenated. Generated
by `make_bundle.py`; the repo at `~/projects/catalyst-integrity-desk` is the source of
truth and this file is a snapshot of it.

Read in the order given. The three engine modules at the end are working, verified
against live SEC and ClinicalTrials.gov data, and are not to be rewritten.

"""


def build() -> str:
    parts = [HEADER]
    for rel in FILES:
        path = os.path.join(ROOT, rel)
        with open(path) as f:
            body = f.read().rstrip()
        fence = "```python\n" + body + "\n```" if rel.endswith(".py") else body
        parts.append(f"\n---\n\n# ==== {rel} ====\n\n{fence}\n")
    return "\n".join(parts)


def main() -> None:
    text = build()
    with open(OUT, "w") as f:
        f.write(text)
    # A bundle missing a section is worse than no bundle, because nobody checks.
    for rel in FILES:
        assert f"# ==== {rel} ====" in text, rel
    assert "677" in text, "the Rocket finding should survive bundling"
    print(f"{OUT}\n{len(text):,} chars, {len(text.split()):,} words, {len(FILES)} files")


if __name__ == "__main__":
    main()
