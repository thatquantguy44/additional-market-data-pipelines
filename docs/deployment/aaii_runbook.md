# AAII operation and recovery

## Input and local execution

CSV imports accept exports through access you are authorized to use. The bounded
live command also reads AAII's official XLS download; it does not log in or parse
a protected webpage. The current workbook was inspected and loaded on 2026-10-26.
Routine automation and redistribution rights remain unverified.

The supported import is UTF-8 CSV, with one date and three shares per row.
Default headers are `Date,Bullish,Neutral,Bearish`. The manifest specifies
`%m/%d/%Y` and percent units. Both `36.0` and `36.0%` mean 36 percent. Fraction
units require a manifest change and prohibit percent suffixes. Duplicate dates,
missing/non-finite shares, unexpected columns, or invalid totals reject the
entire capture. The default total tolerance is 0.002 in fraction units to allow
display rounding. Input size is limited to 20 MiB.

Convert only the observation table when using a workbook; retain the original
download separately, and do not turn summary averages/highs into observations.
Do not substitute a spreadsheet's file modification time for publication time.

```bash
.venv/bin/python -m market_data_pipeline run \
  --input data/inbox/aaii.csv --root data/aaii
```

Capture time is when this pipeline imports the file. No historical publication
time is inferred. Gold spread changes use the preceding available survey and
include `gap_days`. Percentiles and rolling windows are not implemented.

## Read the committed Parquet snapshot

```python
from pathlib import Path
import pyarrow.parquet as pq
from market_data_pipeline.io.parquet import current_snapshot

snapshot = current_snapshot(Path("data/aaii"))
silver = pq.read_table(snapshot / "silver.parquet")
gold = pq.read_table(snapshot / "gold.parquet")
audit = pq.read_table(snapshot / "audit.parquet")
```

Keep old snapshots for rollback and inspection. Do not glob all snapshot files
as one dataset. The pointer is the publication boundary; never use an incomplete
generation after a failed export. Retention/garbage collection is manual.
Audit Parquet reflects the last published snapshot; inspect warehouse audit and
Bronze receipts for trailing failed/partial runs until the next successful export.

## PostgreSQL

Use `--config config/config.yaml` to resolve typed runtime settings from YAML.
See `config/postgres.example.yml`: `user` is the authenticated login; optional
`role` selects the effective PostgreSQL role through startup settings, and
`schema` selects its search path. The login needs permission to assume that role;
the role needs privileges in an existing schema. No roles/databases are silently
created by the Python importer. `connect_timeout` and `sslmode` are configurable.
Set `password_env: null` to use libpq's standard credential mechanisms, such as
a properly secured passfile. Default behavior requires the named password variable.

The local Compose service reads database name, user, published port and bind host
from `AAII_POSTGRES_DATABASE`, `AAII_POSTGRES_USER`, `AAII_POSTGRES_PORT` and
`AAII_POSTGRES_BIND_HOST`. Match these with runtime YAML; Compose and the client
file serve different processes. The container's internal port stays 5432.
Changing initialization variables does not rename an already initialized database,
alter its users, or reset its password. Keep existing volumes intact.

Use a dedicated database and a separate filesystem root from a SQLite run.
The role needs CREATE TABLE/INDEX and SELECT/INSERT/UPDATE/DELETE privileges in
its schema. Table creation is automatic for this initial schema; there is no
general schema migration framework yet. Use a service-specific role/search path
and TLS configuration on a remote database. DSNs stay in the worker environment.

For a local persistent service, set `AAII_POSTGRES_PASSWORD` in an ignored `.env`
file or the shell, then start the supplied Compose service:

```bash
docker compose --env-file .env -f resources/compose.postgres.yml up -d --wait
```

Set `MARKET_DATA_POSTGRES_DSN` for the Python process to
`postgresql://market_data:<URI-encoded-password>@127.0.0.1:55432/additional_market_data`,
then run:

```bash
.venv/bin/python -m market_data_pipeline run \
  --input data/inbox/aaii.csv --root data/aaii-postgres --warehouse postgres
.venv/bin/python -m market_data_pipeline gold \
  --root data/aaii-postgres --warehouse postgres
```

The CLI does not automatically load `.env`; export the DSN or inject it through
your runtime's secret mechanism. Reuse this warehouse's root for later runs.
Back up both PostgreSQL and Bronze. Do not delete the Compose volume to perform
routine restarts. `docker compose ... down` preserves the named volume.

### Verified live local target

The completed live run is in the persistent Compose project
`additional-market-data-live`, container `additional-market-data-live-postgres-1`,
on localhost port **55438**. The role `aaii_writer` is NOLOGIN/NOSUPERUSER and owns
schema `aaii`; login `market_data` can assume it. Four reported dates, October 1,
8, 15 and 22, 2026, were saved. Reimporting the original payload added zero
versions. Inspect `data/aaii-live/verification.json` for the run ID and evidence.

To restart this specific service without changing its persistent volume:

```bash
docker compose --project-name additional-market-data-live --env-file .env \
  -f resources/compose.postgres.yml up -d --wait
```

For a new bounded fetch, export this project's password environment variable,
then use the README's `run --live --config ... --start ... --end ...` example.
The default CSV manifest must be replaced with the XLS manifest for this command.
For an offline rerun, pass the archived `payload.xls` with `--input` and the same
XLS manifest/start/end selection. Replay preserves original capture selection
and HTTP metadata. The selected dates are reported-date labels, not inferred
survey ending dates or exact publication timestamps.

## Dagster execution

Run `dagster dev` as shown in the README, then launch `aaii_sentiment_job` with
`resources/dagster-aaii.yml`. Point `input_path` to the authorized export when
moving beyond the synthetic demo. For PostgreSQL, set `warehouse: postgres` and
inject the DSN into the worker. All workers must share the persistent Bronze and
Parquet root. One writer topology per warehouse is required.

The schedule is stopped by default. Enabling it only schedules local CSV imports.
Use atomically delivered input files so readers cannot capture a partially
written export. Validation failures do not retry automatically; other asset
failures retry twice, 30 seconds apart. A failed/partial run is visible in Dagster
and the warehouse. Provider freshness alerts, stale-file sensors, a production
run launcher/daemon, and external alert destinations are not configured.
For a manual bounded live execution, use `resources/dagster-aaii-live.yml`.
For a local XLS execution, set the XLS manifest plus explicit `start` and `end`.

## Replay and failure recovery

```bash
.venv/bin/python -m market_data_pipeline replay \
  --source-root data/aaii --root data/aaii-rebuilt
```

The destination directory and warehouse must be empty. Replay makes no network
requests, validates raw digests, and preserves capture times and IDs. Original
rejections are copied as failed audit rows and returned in `rejected`; the CLI
returns nonzero so they cannot be mistaken for a fully clean reconstruction.

| Outcome | Recovery |
| --- | --- |
| Manifest invalid or input unreadable | Fix the manifest/input; no dataset promotion occurred |
| CSV/DQ failure | Inspect raw capture and `dq_message`; correct the input and import again |
| Warehouse failure before commit | Preserve Bronze, inspect warehouse audit, fix the service and retry |
| Parquet failure after commit (`partial`) | Fix filesystem capacity/permissions and run `export` |
| Missing promotion receipt / `running` audit after interruption | Reconcile run ID, Silver lineage, and warehouse outcome before replay |
| Corrupted Bronze digest or unsupported parser version | Restore trusted archive/parser; replay stops before destination promotion |

```bash
.venv/bin/python -m market_data_pipeline export --root data/aaii
# Add --warehouse postgres for a PostgreSQL root.
```

An export repairs publication, but does not rewrite historical partial status.
Reconcile an interrupted receipt by checking `pipeline_runs` and Silver
`raw_run_id` in the original warehouse. A committed successful zero-change run
has no new Silver rows, so use its audit counts as well. Preserve the original
capture metadata. For an accepted run, the receipt must record `accepted: true`,
`row_count`, and `inserted_versions`; for a known rejection it records
`accepted: false` and its reason. Do not manufacture receipts when the warehouse
outcome is unknown. No automatic crash reconciler is implemented.

## Databricks / Delta

This is an implemented publishing adapter and notebook, **not a live-tested
deployment**. It needs an existing Databricks Spark session with Delta, a Unity
Catalog schema, a volume, and privileges to create/merge tables and create a view.
Build/install the repository wheel on the job cluster. Stage the immutable
snapshot selected by `current.json`, together with the Bronze archive, under
an authorized `/Volumes/<catalog>/<schema>/<volume>/...` path. Copying a snapshot
alone preserves raw IDs/digests but does not make raw payloads available there.

Open `notebooks/publish_aaii_delta.py` and set the `snapshot`, `catalog`, and
`schema` widgets, or invoke:

```python
from pathlib import Path
from market_data_pipeline.io.databricks import publish_delta

publish_delta(
    spark,
    Path("/Volumes/research/market_data/aaii/parquet/snapshots/<snapshot_id>"),
    catalog="research",
    schema="market_data",
)
```

This creates `aaii_silver_versions`, `aaii_pipeline_runs`, and the
`aaii_gold_latest` view in the selected schema. Immutable insert-only merges
preserve all observed states; Gold is calculated from persisted Delta Silver
so an older snapshot cannot overwrite Gold with an older state. One publisher
per target is required. A multi-table failure can be repaired by rerunning.

Live acceptance requires publishing twice without duplicate versions, publishing
a correction and reversion, checking Gold/as-of SQL results and raw lineage,
and retrying a deliberately interrupted publish. No workspace or job is created
by this repository's local commands.
