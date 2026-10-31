# Pipeline package organization

User-authorized follow-up to AAII completion, 2026-10-30. Keep this on the
current completion branch; CFTC implementation remains separate.

Contract: each implemented pipeline owns its source-specific manifest, parsing,
transforms, acquisition, warehouse/publishers, operations, recovery, CLI and
Dagster assets beneath one subpackage of `src/market_data_pipeline/pipelines/`. Extract
only genuinely reusable file/YAML helpers. Root commands and the Dagster module
stay supported. Data semantics, manifests, parser versions, archives, tables,
root identities, live data and schedules stay unchanged.

1. [x] Move pure AAII contracts/transforms and extract shared file/YAML helpers.
2. [x] Move remaining AAII implementation; migrate imports, notebook and tests;
   retain root CLI/Dagster entrypoints and add a pipeline-owned module command.
3. [x] Populate `docs/pipelines.md` as the master register for implemented,
   planned, draft and candidate sources. Link the roadmap, specs and handoffs.
4. [x] Run offline and isolated PostgreSQL tests, lint/format, package and pinned
   snapshot checks. Verify installed entrypoints and record migration/pickup.
5. [x] Commit and push scoped changes, preserving other docs/spec work.

No new connectors, schema changes, live downloads, scheduler enablement or
cloud deployment. Internal library imports migrate with their files; all owned
consumers are updated and the import mapping is documented. Rollback is a code
revert; no data migration is required.


Verified: 69 tests passed including isolated PostgreSQL. Clean-wheel and installed
entrypoints, AST body comparison, lint/format, dependencies, pinned snapshot and
read-only existing warehouse/Parquet checks passed. The register retains all 20
concrete IDs. Source organization and register are committed/pushed separately
from existing roadmap/FX/web specification drafts. See the verification document
and import migration guide for details and pickup.


## Pipelines namespace follow-up — 2026-10-30

- [x] Nest AAII under `src/market_data_pipeline/pipelines/aaii/` and add the
  namespace package; migrate all owned imports and pipeline module commands.
- [x] Require future pipelines at `pipelines/<pipeline_name>/` in root agent
  guidance, the register, layout guide and planned FX/web-traffic package paths.
- [x] Verify the offline suite (72 passed, two PostgreSQL tests skipped),
  lint/formatting, dependencies, source/wheel builds and isolated wheel CLI/Dagster
  entrypoints. Compare all 21 moved modules' behavior trees excluding imports.

This follow-up changes package placement only; the prior PostgreSQL results above
are historical evidence, not a claim that those two tests ran again.
