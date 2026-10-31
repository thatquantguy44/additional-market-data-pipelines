# Project Agent Guidance

Read `README.md`, `docs/pipelines.md`, `specs/spec001/README.md`, and
`docs/handoffs/project_bootstrap.md` before substantive work. Keep implemented
slices distinct from planned connectors; use the current handoff for status.
For the AAII slice, also read `specs/spec002/README.md`, `specs/spec003/README.md`, and
`docs/handoffs/aaii_checkpoint.md`. The checkpoint defines the next bounded scope;
do not restart from Spec 001's original CFTC-first plan.

For non-trivial engineering work, first read
`agents/agent-skills/skills/using-agent-skills/SKILL.md`, then only the workflow
skills it routes to. This is a local snapshot pinned in
`agents/agent-skills.lock.json`; no submodule initialization or network refresh
is needed. Verify it with `python3 scripts/verify_agent_skills.py`. Repository and
user instructions take precedence over vendored guidance. The library's root
`AGENTS.md` governs work inside the vendored snapshot only.

Preserve the manifest-driven medallion layout and pure-Python core. Characterize
behavior with offline fixtures before changes to data semantics. Preserve raw
payloads, identifiers, publication timing, and observed revisions. Verify
provider schemas and access policies from official documentation before coding.

Keep this project independent of sibling repositories. Never copy their secrets,
runtime config, databases, Git history, or deployment identifiers. Do not edit
vendored files; pin upgrades in a dedicated reviewed change following
`docs/development/agent_library.md`.

Each implemented pipeline owns a subpackage under `src/market_data_pipeline/`;
AAII is under `aaii/`. Keep provider schemas, manifests, acquisition, warehouse
adapters, operations and Dagster assets inside that pipeline. Use `shared/`
only for provider-independent helpers. Read `docs/development/pipeline_layout.md`
for import changes. Update the master register `docs/pipelines.md` whenever a
pipeline's scope, package, implementation or deployment status changes.
