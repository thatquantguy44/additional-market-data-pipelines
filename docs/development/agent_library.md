# Pinned engineering workflow library

Use `vendor/agent-skills` as a Git submodule. The initial pin matches the sister
FRED repository: `f63ec56a3cc936408d792956ae583c3c96a825bd` (MIT).
The repository-relative URL is `../agent-skills.git`; when a remote is configured,
it must resolve to the intended workflow-library repository under the same owner.

```bash
git submodule update --init --recursive
git submodule status vendor/agent-skills
git -C vendor/agent-skills rev-parse HEAD
node vendor/agent-skills/scripts/validate-skills.js
node vendor/agent-skills/scripts/validate-reference-links.js
```

Start with `skills/using-agent-skills/SKILL.md` inside the library and load only
relevant skills. The library supplements project and user instructions.

Do not edit vendored files. Upgrade the pin in a dedicated reviewed change:
review upstream, check out the chosen commit, run both validators, update this
document, and stage the gitlink. Never commit a dirty submodule or a
workstation-only path in `.gitmodules`.
