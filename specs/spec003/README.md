# Spec 003 — AAII completion

Status: implementation scope authorized 2026-10-30. Branch: feature/pipeline-completion.
The user selected AAII completion first; CFTC is a separate subsequent branch.

## Completion contract

1. Exercise the real XLS parser through Dagster using synthetic binary workbooks,
   injected transport/clock and temporary warehouses. Verify exact Bronze bytes,
   HTTP/selection provenance, idempotency, correction/reversion, as-of features,
   failures and materialization metadata.
2. Provide a configurable overlapping weekly window, bounded HTTP retries, a
   freshness/failed-run readout and a stopped live schedule. Require an explicit
   configured access acknowledgement for scheduled live acquisition; do not enable
   a daemon or recurring fetch while entitlement is unverified.
3. Add an explicit offline XLS backfill command with start/end dates and a
   historical DQ report. Normal bounded imports remain strict. Historical missing
   or invalid share rows may be excluded only with an explicit quarantine flag,
   with original bytes/date/rule retained and a partial outcome reported. Duplicate
   dates, malformed date labels and header drift remain blocking. First-seen
   remains actual capture time, never a reconstructed historical publication time.
   Replay must reproduce accepted rows and quarantine outcomes deterministically.
4. Add portable application-level backups of pipeline-owned warehouse state,
   Bronze and the committed snapshot, with file digests and no credentials.
   Restore only into an empty directory/warehouse and verify Silver/Gold
   equivalence. Preserve version/run identities and fix physical audit pointers
   for the new destination. Backup excludes database-global roles and unrelated
   tables. Add dry-run-first snapshot retention that never removes current
   publication or Bronze. Verify SQLite and dedicated PostgreSQL recovery.

The pure-Python core and public import path remain stable. Metadata additions
are backward-compatible with Spec 002 archives; legacy v1 XLS archives replay
with the original parser contract. No cloud provisioning, data redistribution,
CFTC implementation or automatic live schedule enablement is in this branch.

## Build order and acceptance

Synthetic XLS fixture/clock boundary → offline Dagster integration → weekly
window/status/retries → explicit backfill/DQ → backup/restore/retention → docs.
Each slice has focused tests before integration. Run pytest, Ruff, package build,
local snapshot verification and isolated PostgreSQL integration. Do not use the
live AAII database as a test target. The existing authorized workbook may be used
for a reviewed explicit local backfill after offline semantics pass.

AAII is ready to hand off when all four capabilities pass their checks. Recurring
provider permission, production alert destinations/daemon deployment and live
Databricks verification are operational prerequisites, not claims of completion.
