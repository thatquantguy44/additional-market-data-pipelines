# Pipeline package organization

User-authorized follow-up to AAII completion, 2026-10-30. Keep this on the
current completion branch; CFTC implementation remains separate.

Contract: each implemented pipeline owns its source-specific manifest, parsing,
transforms, acquisition, warehouse/publishers, operations, recovery, CLI and
Dagster assets beneath one subpackage of `src/market_data_pipeline/`. Extract
only genuinely reusable file/YAML helpers. Root commands and the Dagster module
stay supported. Data semantics, manifests, parser versions, archives, tables,
root identities, live data and schedules stay unchanged.

1. [x] Move pure AAII contracts/transforms and extract shared file/YAML helpers.
2. [ ] Move remaining AAII implementation; migrate imports, notebook and tests;
   retain root CLI/Dagster entrypoints and add a pipeline-owned module command.
3. [ ] Populate `docs/pipelines.md` as the master register for implemented,
   planned, draft and candidate sources. Link the roadmap, specs and handoffs.
4. [ ] Run offline and isolated PostgreSQL tests, lint/format, package and pinned
   snapshot checks. Verify installed entrypoints and record migration/pickup.
5. [ ] Commit and push scoped changes, preserving other docs/spec work.

No new connectors, schema changes, live downloads, scheduler enablement or
cloud deployment. Internal library imports migrate with their files; all owned
consumers are updated and the import mapping is documented. Rollback is a code
revert; no data migration is required.
