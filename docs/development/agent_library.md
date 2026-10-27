# Pinned engineering workflow library

`agents/agent-skills/` is a complete local snapshot stored as ordinary files in
this repository. It is not a Git submodule and contains no nested Git metadata.
Normal checkouts include the skills, references, helper scripts, and MIT license;
using or verifying them requires no GitHub access or refresh.

The pin is `f63ec56a3cc936408d792956ae583c3c96a825bd` from
`https://github.com/thatquantguy44/agent-skills.git`. This is the same revision as
the original submodule, without an upstream upgrade. Git's descriptive label is
`0.6.7-10-gf63ec56` (10 commits after the `0.6.7` tag, not the tag itself).

`agents/agent-skills.lock.json` records the exact revision, original Git tree,
license, file count, and SHA-256 of the local content inventory. The digest covers
relative paths, file bytes, executable status, and symlink targets. The integrity
check uses the Python standard library and does not invoke Git or access a network.

```bash
python3 scripts/verify_agent_skills.py
node agents/agent-skills/scripts/validate-skills.js
node agents/agent-skills/scripts/validate-reference-links.js
```

Start with `skills/using-agent-skills/SKILL.md` inside the library and load only
relevant skills. The library supplements project and user instructions.

Do not edit vendored files during application work. Upgrade the snapshot only in
a dedicated reviewed change: obtain the explicitly chosen upstream commit in a
temporary checkout, review its changes, export its tracked files without `.git`
metadata, and replace the snapshot. Preserve the MIT license. Update the lock's
revision/tree and content digest together, run all three validators, review the
normal-file diff, and update this document. No automated update-on-start or
floating branch is configured.
