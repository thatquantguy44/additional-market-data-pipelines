# AAII slice verification

Verified 2026-10-26 (America/New_York), Python 3.12 on macOS.

- **54 tests passed** with `MARKET_DATA_TEST_POSTGRES_DSN` pointing to a dedicated
  disposable PostgreSQL 17.6 container; no live AAII request is part of the suite.
- Pure validation covers explicit units, rounding tolerance, missing/non-finite
  values, schema drift, duplicate/future dates, and malformed manifest fields.
- Local integration covers unchanged reruns, correction and reversion, as-of
  cutoff offsets, historical-feature recomputation, raw retention, replay,
  archive tampering, original rejection preservation, and root/backend binding.
- Snapshot tests cover typed dates/timestamps, row counts, partial publication,
  pointer stability after a mid-write failure, recovery export, and overlapping
  local writers without duplicate versions.
- PostgreSQL test verifies actual persistence, idempotency, revisions/reversion,
  failed-DQ isolation, Gold/as-of results, and transaction rollback.
- Dagster job materializes the fixture in process, exposes run metadata, and
  loads its stopped schedule. The CLI is tested via subprocess entrypoints.
- Ruff lint and formatting, `pip check`, and source/wheel package builds pass.
  Source distribution includes manifests and test fixtures.
- The README demo was executed and wrote a synthetic Bronze/Silver/Gold/audit
  dataset with committed Parquet files under ignored `data/aaii-demo`.

Review fixes included a root-anchored data ignore rule (source transformation
modules were previously hidden), strict chronological capture promotion,
promotion receipts so replay cannot accept previously rejected captures, and
warehouse identity checks. No vendored files or sibling configuration changed.

Not verified: recurring automatic download entitlement, hosted
GitHub CI execution, a deployed Dagster daemon/run launcher, or live Databricks
Delta/Unity Catalog behavior. Delta tests currently exercise input boundaries;
they do not establish live MERGE correctness. The runbook lists live acceptance
steps. No production services, schedules, accounts, or remote repository were created.

## Bounded live verification and configured PostgreSQL

An explicitly authorized live request to
https://www.aaii.com/files/surveys/sentiment.xls returned a real XLS workbook.
The inspected `SENTIMENT` sheet has a `Reported` label above the row-4
Date/Bullish/Neutral/Bearish header. Shares are fractions and the selected dates
are preserved exactly. Original response bytes, HTTP metadata, manifest and
selection bounds are retained in Bronze. Synthetic offline fixtures contain no
copied provider observations.

Live run ID: `2e02a48857a247918da76b6dd1a8c8cf`.

| Check | Verified result |
| --- | --- |
| Requested reported-date window | 2026-10-01 through 2026-10-26 |
| Persisted observation count | 4 Silver revisions and 4 Gold rows |
| Stored first/last reported dates | 2026-10-01 / 2026-10-22 |
| PostgreSQL endpoint | 127.0.0.1:55438 (container internal port 5432) |
| Database/schema | additional_market_data / aaii |
| Authenticated login / effective role | market_data / aaii_writer |
| Writer privileges | NOLOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE; owns aaii schema |
| Reimport of original bytes | 0 additional revisions |
| Parquet | Silver and Gold each contain 4 rows |
| Raw lineage | All four revisions match original byte SHA-256 |
| Publication timestamp | null; Reported Date is not an exact timestamp |

The local persistent Compose project `additional-market-data-live` is left
running. Its generated password is in ignored `.env` with mode 0600; runtime
settings are in ignored `config/config.yaml`. A machine-readable evidence record
is in `data/aaii-live/verification.json`. No credentials are present in this
record, tracked config, logs, or the package. The independent disposable test
database is removed after verification.

New offline checks cover config precedence, escaping of secret values, invalid
ports/roles/schema/SSL settings, XLS bounds and missing/error cells, schema drift,
reported-date isolation, and retention of HTTP failure responses. Routine
scheduled acquisition remains disabled pending entitlement review.

## Local workflow snapshot and stopping checkpoint

The original workflow submodule was replaced by 188 ordinary files/symlinks at
the identical revision `f63ec56a3cc936408d792956ae583c3c96a825bd` under `agents/`.
The original parent gitlink and checkout HEAD matched before export. Every copied
file/symlink was compared with that clean checkout. The offline checksum and
both library validators passed (24 skills, no errors). There is no remaining
gitlink or `.gitmodules`; CI now verifies the local snapshot without refreshing it.

The final read-only database check confirmed four Silver and four Gold rows,
reported dates 2026-10-01 through 2026-10-22, with the local live service healthy.
Snapshot verification, Ruff and staged/unstaged whitespace checks passed at
closeout. `docs/handoffs/aaii_checkpoint.md` records the next recommended scope
and the local resources left in place. No new AAII request was made for closeout.
