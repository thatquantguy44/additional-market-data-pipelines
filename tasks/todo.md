# AAII tasks

- [x] Pure manifest/CSV/Gold contracts; offline validation, explicit units and rounding.
- [x] Bronze, warehouse, Parquet and replay; revisions/reversion, as-of, failures,
  atomic snapshot pointer, overlapping writers, tampering, and rejection receipts.
- [x] PostgreSQL and Delta publishing; real PostgreSQL integration passed.
  Delta boundary checks passed; live workspace verification remains external.
- [x] CLI and Dagster; fixture execution and stopped schedule verified.
- [x] Documentation, package build, full tests, lint and implementation review.

Verification (2026-10-26 America/New_York): 54 tests passed with a disposable
PostgreSQL 17.6 service. Ruff lint/format passed, package build passed, and the
README fixture demo produced inspectable outputs under `data/aaii-demo`.
See `docs/development/verification.md` for exact scope and remaining external checks.

- [x] Runtime YAML shared by CLI/Dagster; secret resolution, CLI precedence,
  role/schema, port, database and connection policy verified.
- [x] Official XLS inspected, synthetic cells characterized, bounded parsing,
  HTTP-failure retention and reported-date contract isolation tested.
- [x] Four live observations committed to persistent PostgreSQL; database, role,
  schema, Parquet and raw lineage queried; rerun added zero versions.
- [x] Ignored config/config.yaml and .env record the actual local target;
  persistent Compose service remains available on localhost port 55438.

- [x] Replace workflow submodule with an exact local snapshot; lock provenance,
  offline checksums, root guidance and CI verification are in place.
- [x] Record a stopping checkpoint, service/data state, semantics and next scope.

## Authorized AAII completion (Spec 003)

- [x] Synthetic XLS and full offline Dagster integration.
- [x] Weekly window, bounded retries, freshness/status and gated stopped schedule.
- [x] Explicit historical backfill with DQ quarantine and deterministic replay.
- [x] Owned-table/Bronze backups, empty-target restore and safe snapshot retention.
- [x] Isolated PostgreSQL verification, documentation, commits and branch push.
- [ ] Follow-on CFTC branch after AAII completion (separate scope, not implemented here).


Completion verification: 68 tests passed with isolated PostgreSQL, plus verified
local historical backfill, zero-change rerun, backup/restore and replay equality.
Current pickup and external operational prerequisites are in the AAII checkpoint.
CFTC begins on a new branch after review/merge; it is not implemented here.
