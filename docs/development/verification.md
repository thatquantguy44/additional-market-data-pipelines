# AAII slice verification

Initial slice verified 2026-10-26 (America/New_York), Python 3.12 on macOS.
The Spec 003 completion results below supersede these initial counts/state.

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

## Hosted verification after push

The five implementation/checkpoint commits were pushed to `origin/main`.
GitHub Actions run `40434195208` for `c422c5d` was blocked before executing any
steps. Its check annotations report failed recent account payments or an Actions
spending-limit issue. This provides no hosted verdict on installation, tests or
build; the last local full suite passed all 54 tests. The account owner needs to
resolve the execution allowance before retrying CI. No billing settings, tests,
or verification gates were changed in response.

## Repository identity update — 2026-10-30

The repository and Python distribution are named `market-medallion`
(MarketMedallion). The request identifier and documentation use that identity.
The stable `market_data_pipeline` import path and `market-data` CLI are retained;
`market-medallion` is an additional CLI entrypoint. Local PostgreSQL, schema,
roles, Compose project/volume names, archived bytes and historical metadata are
preserved. The renamed checkout retains a compatibility symlink at the previous
path for existing absolute references.

Rename verification passed from the new checkout: GitHub reports
`thatquantguy44/market-medallion`, origin uses its canonical URL, installed
metadata reports `market-medallion` 0.1.0, and both CLI entrypoints validate the
manifest. The offline suite passed 53 tests with the isolated PostgreSQL test
skipped; lint, formatting, dependency checks, source/wheel builds, and workflow
snapshot integrity passed. Read-only inspection confirmed four live Silver and
four Gold rows, and all recorded Bronze/file/snapshot paths still resolve. No
provider data was fetched, and no database, role, port or persistent volume was
renamed.

Hosted verification also passed for rename commit `88e0354` on 2026-10-30:
[GitHub Actions run 41113974074](https://github.com/thatquantguy44/market-medallion/actions/runs/41113974074).
The hosted job passed all 54 tests, including isolated PostgreSQL integration,
snapshot verification, lint/formatting, and source/wheel builds. This supersedes
the original account-level execution block; no billing settings were changed.


## Spec 003 AAII completion — 2026-10-30 America/New_York

- Full suite: **68 passed**, including both real PostgreSQL tests against a
  dedicated disposable PostgreSQL 17.6 instance on localhost 55439. No test
  contacts AAII or writes to the live warehouse. Without the DSN: 66 passed,
  two PostgreSQL tests skipped.
- Synthetic binary XLS workbooks exercise Dagster's real XLS success/failure
  paths, idempotency, correction/reversion, as-of results, materializations and
  exact raw/HTTP/selection retention. Fixture generation uses optional isolated
  xlwt tooling; it adds no runtime dependency. The source package includes XLS.
- Operational tests verify New York overlap, stale/failed/partial state handling,
  connection-failure health, archived transient responses, Retry-After pacing,
  and stopped live schedule gating/dynamic bounds. Configuration defaults keep
  routine acquisition disabled.
- Historical tests verify strict rejection, explicit quarantine, partial status,
  CLI exits, original first-seen times, gaps and deterministic backfill replay.
- Recovery tests verify inventory/digest rejection, empty-target enforcement,
  Silver/Gold equality, physical audit pointers, distinct warehouse identity,
  PostgreSQL isolation and rollback, dry-run retention and current/Bronze protection.
- Ruff lint/formatting, source/wheel build, dependency checks and pinned library
  integrity pass. No dependency or vendored snapshot was changed.

The existing authorized workbook was imported offline into the unchanged live
PostgreSQL target after backing up and restoring the original four-date state to
an isolated PostgreSQL schema. Backfill run `28556d16d7ee4934bf80e8cd5a521120`
accepted 2,046 reported dates, 1987-07-24 through 2026-10-22, inserted 2,042
versions, and quarantined three invalid rows. The repeat import inserted zero.
The completed history was backed up, restored to SQLite and replayed from Bronze;
all Silver versions and Gold results matched. Publication timestamps remain null.
Machine-readable evidence is ignored `data/aaii-live/completion-verification.json`.
Only a dry-run retention was performed on the live root. No new AAII fetch,
schedule enablement, cloud deployment or data redistribution occurred.

The three exclusions are 1987-06-26, 1987-07-17 and 1996-01-11, all
missing/nonnumeric shares. Nine gaps over eight days remain visible. Both
backfill runs have partial audit status; the health readout intentionally reports
that trailing partial outcome until a later clean import. Historical observations
were first seen at the actual import, not reconstructed publication dates.

Recurring AAII acquisition rights, deployed daemon/alert routing, off-machine
backup policy and live Databricks remain external prerequisites. CFTC remains
unimplemented and starts on the next separate branch.
