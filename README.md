# MarketMedallion

Repository: [market-medallion](https://github.com/thatquantguy44/market-medallion).

Independent, manifest-driven **Bronze → Silver → Gold** pipelines for market
data. The first executable slice imports an authorized local **AAII Investor
Sentiment Survey CSV or official XLS**, stores observed revisions in SQLite or PostgreSQL, and
publishes typed Parquet snapshots. Dagster provides the initial orchestration.

**Status:** local CSV ingestion, replay, Parquet, PostgreSQL adapter, CLI, and
Dagster definitions and bounded official XLS downloads are implemented. A live
four-observation load to PostgreSQL was verified. The Databricks Delta publisher
has not been exercised in a workspace. No cloud infrastructure or running schedule
is deployed. Other sources remain planned.

## Run the first slice

Python 3.12 is the tested baseline. From the repository root:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
.venv/bin/python -m market_data_pipeline validate
.venv/bin/python -m market_data_pipeline run \
  --input tests/fixtures/aaii/sentiment.csv --root data/aaii-demo
.venv/bin/python -m market_data_pipeline gold --root data/aaii-demo
```

The fixture contains **invented test values**, not actual AAII history. For real
data, supply an authorized CSV with the manifest's mapped headers:

```csv
Date,Bullish,Neutral,Bearish
```

Use `MM/DD/YYYY` and percentage values such as `36.0` or `36.0%`. Edit a copy of
[the manifest](manifests/aaii-investor-sentiment.yml) for different headers, ISO
dates, or fractional units; pass it with `--manifest`. No automatic unit guessing
is performed. The official XLS path below preserves the original workbook. Keep the original when converting
an authorized download to CSV. AAII historical access, automation, and reuse
permissions still require verification; see the [source review](docs/catalog/README.md).

Each run archives exact input bytes and its manifest before parsing. Unchanged
observations create no new Silver versions; corrections and reversions do.
Gold exposes bullish-minus-bearish spread, prior-survey spread change, and date
gaps. Publication time stays null when unknown. As-of queries use the versions
actually captured by this pipeline, not reconstructed historical vintages.

```bash
.venv/bin/python -m market_data_pipeline gold --root data/aaii-demo \
  --as-of 2026-10-26T23:59:59-04:00
.venv/bin/python -m market_data_pipeline replay \
  --source-root data/aaii-demo --root data/aaii-replayed
```

Replay requires an empty destination. Rejected captures remain rejected and are
reported with a nonzero CLI exit status. See [the runbook](docs/deployment/aaii_runbook.md)
for failure recovery and PostgreSQL/Databricks instructions.

## Parquet and warehouses

| Target | Behavior |
| --- | --- |
| SQLite | Default local transactional warehouse; no service needed |
| Parquet | Every successful run writes Silver, Gold, and audit snapshots |
| PostgreSQL | `--warehouse postgres`, DSN from `MARKET_DATA_POSTGRES_DSN` |
| Databricks/Delta | Publish a committed snapshot staged in a Unity Catalog volume |

Always read `parquet/current.json` to select the committed snapshot. Glob-reading
all snapshots duplicates history. [Architecture](docs/deployment/architecture.md)
explains transaction boundaries and storage layout.

## Database configuration and bounded live runs

Copy [the runtime example](config/postgres.example.yml) to ignored
`config/config.yaml` and set host, port, database, login `user`, optional effective
`role`, and `schema`. The schema/role must already exist with suitable permissions.
Set the password in the environment variable named by `password_env`; an actual
password is never stored in YAML. Relative output paths resolve against the config
file's directory. Explicit `--root` and `--warehouse` flags override the file.
Configured PostgreSQL settings take precedence over the legacy DSN environment variable.

```bash
# Load this project's trusted local .env into your shell, or inject the password externally.
set -a
source .env
set +a
.venv/bin/python -m market_data_pipeline run --live \
  --config config/config.yaml \
  --manifest manifests/aaii-investor-sentiment-xls.yml \
  --start 2026-10-01 --end 2026-10-26
.venv/bin/python -m market_data_pipeline gold --config config/config.yaml
```

Live selection is limited to 90 days. The entire original XLS response is archived
with HTTP provenance and the selected date bounds. XLS dates are **Reported Date**
labels and are preserved without shifting to survey-week-ending dates. A warehouse
contract prevents mixing these two date conventions. Routine scheduled downloads
remain disabled; this command is an explicit bounded fetch.

The verified local service uses `127.0.0.1:55438`, database `additional_market_data`,
login `market_data`, effective role `aaii_writer`, and schema `aaii`. Its actual
settings are in ignored `config/config.yaml`; credentials are in ignored `.env`.
The checked-in example keeps the generic port 55432 and public schema.
These database and Docker identifiers are preserved across the repository rename
so existing volumes and DBeaver connections continue to use the same data.

## Dagster

The lockfile includes the optional Dagster dependencies. For a minimal runtime,
install `.[dagster,postgres]` instead. Start the UI from the repository root:

```bash
mkdir -p .dagster
DAGSTER_HOME="$PWD/.dagster" .venv/bin/dagster dev \
  -m market_data_pipeline.orchestration.dagster_defs
```

Launch `aaii_sentiment_job` using [the example run configuration](resources/dagster-aaii.yml).
The Thursday 10:00 America/New_York schedule is **stopped by default**. It imports
a supplied local CSV; it does not fetch data from AAII. Dagster owns execution,
retry visibility, and materialization metadata. Pure transforms and the pipeline
remain callable independently, allowing later Airflow or Mage wrappers without
changing data semantics. See [the orchestration decision](docs/development/adr001-dagster.md).
For an explicit bounded live job, use [the live run config](resources/dagster-aaii-live.yml)
and inject the password into the worker environment. This does not enable the schedule.

## Verification and project context

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m build --no-isolation
```

PostgreSQL tests require a dedicated empty test database; instructions are in
[development](docs/development/README.md). Tests never require a live AAII service.

- [Spec 002: executable AAII slice](specs/spec002/README.md)
- [Spec 001: original broader design](specs/spec001/README.md)
- [Roadmap and full source backlog](docs/roadmap.md)
- [Current handoff](docs/handoffs/project_bootstrap.md)
- [Stopping checkpoint and next scoped task](docs/handoffs/aaii_checkpoint.md)
- [Data dictionary](docs/dictionary/data_dictionary.md)
- [Pinned engineering workflow library](docs/development/agent_library.md)

The workflow library is vendored directly under `agents/agent-skills/`, with its
exact upstream revision and content checksum in `agents/agent-skills.lock.json`.
No submodule setup or GitHub refresh is needed. Verify the local snapshot with
`python3 scripts/verify_agent_skills.py`. This project has no runtime imports,
secrets, databases, or deployment identifiers inherited from sibling repositories.

## Repository name and local checkout

The project is named **MarketMedallion**; the GitHub repository and Python
distribution use `market-medallion`. The Python import path
`market_data_pipeline` and existing `market-data` command remain supported.
Installing the package also provides the `market-medallion` command.

The local checkout is `pipelines/market-medallion`. The previous checkout path is
retained as a compatibility symlink for historical absolute Bronze/audit paths
and existing workspace references. New clones can use the new name directly.
