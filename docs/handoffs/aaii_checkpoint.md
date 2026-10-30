# AAII checkpoint and next scoped work

Implementation checkpoint: 2026-10-26, America/New_York.
Repository identity updated 2026-10-30 to **MarketMedallion** (`market-medallion`).
This is a deliberate stopping point:
the first AAII slice, configured PostgreSQL live run, and local workflow snapshot
are complete. Do not resume by rebuilding the scaffold or adding another source.

## Read first

1. Root `AGENTS.md` and `README.md`.
2. `specs/spec002/README.md` (active implementation contract); Spec 001 describes
   the broader future CFTC/FINRA/OFR scope.
3. This checkpoint, `tasks/todo.md`, and `docs/deployment/aaii_runbook.md`.
4. `agents/agent-skills/skills/using-agent-skills/SKILL.md`, then the routed skills.

The master handoff and roadmap retain all 14 additional source IDs. This focused
checkpoint does not replace that inventory or authorize expanding source scope.

## Completed and verified

- Manifest-driven CSV and bounded official XLS ingestion, exact-byte Bronze,
  transactional Silver revisions and Gold, audit, typed Parquet snapshots, and
  offline replay. Date bounds and original HTTP metadata survive replay.
- SQLite and PostgreSQL use the same pipeline contract. Runtime YAML configures
  host, port, database, login user, effective role, schema, SSL mode and timeout.
  Passwords resolve from the named environment variable, not YAML.
- A Dagster asset/job supports local and explicit bounded live execution. The
  default Thursday schedule remains stopped and configured for local input.
- A Delta publisher/notebook exists but has not been verified in Databricks.
- Workflow library: 188 ordinary files/symlinks in `agents/agent-skills/`, pinned
  to `f63ec56a3cc936408d792956ae583c3c96a825bd`. There is no Git submodule or
  nested Git metadata. `agents/agent-skills.lock.json` records provenance and
  content integrity; the local verifier needs no GitHub access.

Last full application verification: **54 tests passed**, including the dedicated
PostgreSQL integration test. Lint, formatting, package build, dependency checks,
and the two library validators passed. At closeout the snapshot checksum, lint,
formatting and staged/unstaged whitespace checks were also verified. Application
tests contain no live provider requests. See `docs/development/verification.md`.

## Local data and service left in place

| Setting | Value |
| --- | --- |
| Compose project / container | `additional-market-data-live` / `additional-market-data-live-postgres-1` |
| Endpoint | `127.0.0.1:55438` (container internal port 5432) |
| Database / schema | `additional_market_data` / `aaii` |
| Login / effective writer | `market_data` / `aaii_writer` |
| Runtime settings | ignored `config/config.yaml` |
| Password | `AAII_POSTGRES_PASSWORD` in ignored `.env`; do not print or commit |
| Bronze / Parquet / evidence | ignored `data/aaii-live/`, including `verification.json` |

Live run `2e02a48857a247918da76b6dd1a8c8cf` stored four observations, reported
dates October 1, 8, 15 and 22, 2026. A same-payload rerun inserted zero revisions.
Read-only closeout inspection confirmed the service healthy and four Silver/four
Gold rows. The live service and its persistent volume are left available for
DBeaver; the independent disposable test container is removed after checks.

Fresh checkouts do not include `.env`, the local config, volumes or data. Use the
checked-in examples and runbook to configure a new environment; do not borrow
credentials or deployment settings from sibling repositories.

## Semantics to preserve

- XLS `Date` is the provider's **Reported Date** label. Do not shift it to a
  survey-week-ending date or fabricate a publication timestamp. The compatibility
  column is named `survey_date`; warehouse date-basis contracts prevent mixing
  reported and survey dates. Unknown publication times remain null.
- `aaii_gold_latest` holds the latest observed version **per ingested date**, not
  just the newest week. New weeks append dates; corrections change that date's
  Gold row and retain prior Silver versions. Unchanged observations add no version.
- Select versions by availability before calculating historical features.
  Historical downloads do not establish historical publication vintages.
- Read Parquet using `current.json`; do not combine all snapshot generations.
  Partial publication is repairable with `export`. Replay preserves rejection
  receipts and stops on unresolved promotion outcomes.

## Next recommended scope: offline coverage of the live Dagster path

This work is **not started**. Keep it limited to testing the existing bounded
AAII XLS path and making small injection changes needed for deterministic tests.
The current Dagster success test exercises CSV input; XLS tests characterize
synthetic cells and HTTP failures, while successful real XLS ingestion was a
manual live verification. Close that specific automated coverage gap.

Acceptance criteria:

1. Add a small synthetic XLS fixture with the verified header/date-cell layout;
   document its provenance and do not commit the provider's actual workbook.
2. Execute the Dagster job's `live: true` path with injected HTTP/clock behavior,
   an explicit bounded window and runtime YAML. No provider or cloud access.
3. Assert original response/HTTP/selection retention, unshifted reported dates,
   Silver/Gold counts, Parquet publication and materialization metadata.
4. Re-run unchanged input to prove no duplicate versions; exercise a correction
   and verify the previous version remains selectable by an as-of cutoff.
5. Verify blocking failure leaves prior published data intact and the schedule
   stopped. Reuse the isolated PostgreSQL test setup where useful; never write
   tests into the live `additional_market_data` database.

Likely files: `tests/test_entrypoints.py`, `tests/test_live_aaii.py`, synthetic
fixtures, and only if necessary `sources/aaii.py` or `orchestration/dagster_defs.py`.
Update the active spec/tasks before changing behavior. Stop after these criteria
pass; additional sources, rolling features, schema redesign, scheduler enabling,
cloud deployment and Databricks provisioning are separate scopes.

## Repository and resumption checks

The user requested the work be committed and pushed as a series: local workflow
snapshot, AAII core, platform adapters/resources, CI, then checkpoint/docs. Inspect
`git status --short`, `git log --oneline -5`, and branch tracking before editing;
preserve any subsequent user changes. The configured destination is this project's
`origin/main`. No force-push or automatic submodule refresh is part of resumption.

The first four checkpoint commits are `73f38d7` (local workflow snapshot),
`aeb20cb` (AAII core), `173823d` (platform adapters/resources), and `5568fb5`
(CI). `c422c5d` contains the main documentation checkpoint. A final documentation
follow-up records the hosted-CI block below; use `git log` for its revision.

### Hosted CI status at the original 2026-10-26 push

The initial five-commit series was pushed to `origin/main`. The
[hosted run](https://github.com/thatquantguy44/market-medallion/actions/runs/40434195208)
for `c422c5d` failed **before any steps started**: GitHub reported recent account
payments failed or the Actions spending limit must be increased. This is an
account-level execution block, not a test or workflow-code failure. Local
verification remains 54 passing tests; do not describe hosted CI as passing.

This was the execution status at the original checkpoint, not a code failure.
The successful 2026-10-30 rename run below supersedes the execution block. No
billing settings or verification gates were changed by the agent. The recommended
engineering task remains the offline bounded live Dagster coverage above.

### Repository rename

Use `https://github.com/thatquantguy44/market-medallion.git` for `origin` and
`pipelines/market-medallion` for the local checkout. The former local directory
name is a compatibility symlink so historical absolute raw/audit pointers remain
resolvable. Do not rewrite immutable Bronze metadata or alter the live database
or volume names to match branding. Both CLI entrypoints and the existing Python
import path remain valid. The next data-engineering task above is unchanged.

```bash
python3 scripts/verify_agent_skills.py
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Without `MARKET_DATA_TEST_POSTGRES_DSN`, the PostgreSQL test skips. With a fresh,
dedicated test database, the last complete suite had 54 passing tests. Creating a
new test database is described in the development guide. Do not start with a new
live fetch, overwrite local configuration, reset a persistent volume, or enable
a recurring download; recurring entitlement and reuse review remain open.

Hosted verification for rename commit `88e0354` passed on 2026-10-30:
[run 41113974074](https://github.com/thatquantguy44/market-medallion/actions/runs/41113974074).
All 54 tests (including PostgreSQL), the local snapshot check, lint/formatting,
and source/wheel builds succeeded. The next scoped task can resume directly;
there is no outstanding CI-execution prerequisite at this checkpoint.
