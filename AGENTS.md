# Project Agent Guidance

Read `README.md`, `specs/spec001/README.md`, and
`docs/handoffs/project_bootstrap.md` before substantive work. This repository is
at the specification stage; do not describe planned connectors as implemented.

For non-trivial engineering work, first read
`vendor/agent-skills/skills/using-agent-skills/SKILL.md`, then only the workflow
skills it routes to. Initialize the pinned submodule if absent. Repository and
user instructions take precedence over vendored guidance. The library's root
`AGENTS.md` governs work inside the submodule only.

Preserve the manifest-driven medallion layout and pure-Python core. Characterize
behavior with offline fixtures before changes to data semantics. Preserve raw
payloads, identifiers, publication timing, and observed revisions. Verify
provider schemas and access policies from official documentation before coding.

Keep this project independent of sibling repositories. Never copy their secrets,
runtime config, databases, Git history, or deployment identifiers. Do not edit
vendored files; pin upgrades in a dedicated reviewed change following
`docs/development/agent_library.md`.
