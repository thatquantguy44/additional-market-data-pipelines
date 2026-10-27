import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from market_data_pipeline.data.gold import features
from market_data_pipeline.io.bronze import atomic_json

SILVER_COLUMNS = (
    "version_id",
    "source",
    "dataset",
    "survey_date",
    "bullish",
    "neutral",
    "bearish",
    "provider_published_at",
    "first_seen_at",
    "retrieved_at",
    "content_hash",
    "raw_run_id",
    "raw_sha256",
    "parser_version",
)
GOLD_COLUMNS = (
    *SILVER_COLUMNS,
    "bull_bear_spread_pp",
    "previous_survey_date",
    "gap_days",
    "spread_change_pp",
    "previous_version_id",
)
RUN_COLUMNS = (
    "run_id",
    "dataset",
    "captured_at",
    "status",
    "row_count",
    "inserted_versions",
    "dq_message",
    "bronze_path",
    "completed_at",
)

SILVER_DDL = """
    version_id TEXT PRIMARY KEY, source TEXT NOT NULL, dataset TEXT NOT NULL,
    survey_date TEXT NOT NULL, bullish DOUBLE PRECISION NOT NULL CHECK (bullish BETWEEN 0 AND 1),
    neutral DOUBLE PRECISION NOT NULL CHECK (neutral BETWEEN 0 AND 1),
    bearish DOUBLE PRECISION NOT NULL CHECK (bearish BETWEEN 0 AND 1),
    provider_published_at TEXT, first_seen_at TEXT NOT NULL, retrieved_at TEXT NOT NULL,
    content_hash TEXT NOT NULL, raw_run_id TEXT NOT NULL,
    raw_sha256 TEXT NOT NULL, parser_version TEXT NOT NULL
"""


class Warehouse:
    """The same AAII persistence contract on stdlib SQLite or optional psycopg.

    https://www.psycopg.org/psycopg3/docs/basic/transactions.html
    """

    def __init__(self, root: Path, dsn: str | None = None):
        if dsn is not None and not dsn.strip():
            raise ValueError("PostgreSQL DSN must not be empty")
        self.root = Path(root)
        self.postgres = dsn is not None
        self.root.mkdir(parents=True, exist_ok=True)
        identity_path = self.root / ".warehouse.json"
        identity = json.loads(identity_path.read_text()) if identity_path.exists() else None
        backend = "postgres" if self.postgres else "sqlite"
        if identity and identity["backend"] != backend:
            raise ValueError("data root belongs to a different warehouse; use a separate root")
        if dsn:
            import psycopg
            from psycopg.conninfo import conninfo_to_dict
            from psycopg.rows import dict_row

            params = conninfo_to_dict(dsn)
            params.setdefault("connect_timeout", "15")
            self.connection = psycopg.connect(**params, autocommit=True, row_factory=dict_row)
        else:
            self.connection = sqlite3.connect(
                self.root / "warehouse.sqlite3", timeout=30, isolation_level=None
            )
            self.connection.row_factory = sqlite3.Row
        try:
            self._initialize(identity, identity_path, backend)
        except BaseException:
            self.connection.close()
            raise

    def _initialize(self, identity, identity_path, backend):
        with self.transaction():
            self.execute("CREATE TABLE IF NOT EXISTS pipeline_identity (id TEXT PRIMARY KEY)")
            stored = self.execute("SELECT id FROM pipeline_identity").fetchone()
            if stored is None:
                self.execute("INSERT INTO pipeline_identity (id) VALUES (?)", (uuid.uuid4().hex,))
                stored = self.execute("SELECT id FROM pipeline_identity").fetchone()
            warehouse_id = dict(stored)["id"]
            if identity and identity["warehouse_id"] != warehouse_id:
                raise ValueError("data root belongs to another warehouse; use a separate root")
            self.execute(f"CREATE TABLE IF NOT EXISTS aaii_silver_versions ({SILVER_DDL})")
            self.execute(f"""CREATE TABLE IF NOT EXISTS aaii_gold_latest ({SILVER_DDL},
                bull_bear_spread_pp DOUBLE PRECISION, previous_survey_date TEXT,
                gap_days INTEGER, spread_change_pp DOUBLE PRECISION, previous_version_id TEXT)""")
            self.execute("""CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id TEXT PRIMARY KEY, dataset TEXT NOT NULL, captured_at TEXT NOT NULL,
                status TEXT NOT NULL, row_count INTEGER NOT NULL,
                inserted_versions INTEGER NOT NULL,
                dq_message TEXT, bronze_path TEXT NOT NULL, completed_at TEXT)""")
            self.execute("""CREATE INDEX IF NOT EXISTS aaii_revision_lookup
                ON aaii_silver_versions (dataset, survey_date, first_seen_at)""")
            self.execute("""CREATE TABLE IF NOT EXISTS pipeline_dataset_contract (
                dataset TEXT PRIMARY KEY, date_basis TEXT NOT NULL)""")
        if not identity:
            atomic_json(identity_path, {"warehouse_id": warehouse_id, "backend": backend})

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.connection.close()

    def execute(self, sql, params=()):
        return self.connection.execute(sql.replace("?", "%s") if self.postgres else sql, params)

    @contextmanager
    def transaction(self):
        if self.postgres:
            with self.connection.transaction():
                # One dataset writer; transaction scoped, released even on failure.
                self.execute("SELECT pg_advisory_xact_lock(721049002)")
                yield
        else:
            self.execute("BEGIN IMMEDIATE")
            try:
                yield
                self.execute("COMMIT")
            except BaseException:
                self.execute("ROLLBACK")
                raise

    def _insert(self, table, columns, values):
        # Table/column names are internal constants. All external values are parameters.
        self.execute(
            f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
            values,
        )

    def versions(self) -> list[dict]:
        return [
            dict(row)
            for row in self.execute(
                "SELECT * FROM aaii_silver_versions ORDER BY first_seen_at, version_id"
            ).fetchall()
        ]

    def runs(self) -> list[dict]:
        return [
            dict(row)
            for row in self.execute(
                "SELECT * FROM pipeline_runs ORDER BY captured_at, run_id"
            ).fetchall()
        ]

    def gold(self, as_of: str | None = None) -> list[dict]:
        return features(self.versions(), as_of)

    def record_run(self, envelope: dict, bronze_path: str):
        self._insert(
            "pipeline_runs",
            RUN_COLUMNS,
            (
                envelope["run_id"],
                envelope["manifest"]["dataset"],
                envelope["retrieved_at"],
                "running",
                0,
                0,
                None,
                bronze_path,
                None,
            ),
        )

    def status(self, run_id, status, rows=0, inserted=0, message=None):
        self.execute(
            """UPDATE pipeline_runs SET status=?, row_count=?, inserted_versions=?,
                     dq_message=?, completed_at=? WHERE run_id=?""",
            (
                status,
                rows,
                inserted,
                message,
                datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z"),
                run_id,
            ),
        )

    def promote(self, rows, envelope) -> int:
        with self.transaction():
            dataset = envelope["manifest"]["dataset"]
            basis = envelope["manifest"].get("date_basis", "survey_date")
            existing = self.execute(
                "SELECT date_basis FROM pipeline_dataset_contract WHERE dataset=?", (dataset,)
            ).fetchone()
            if existing is None:
                # Existing v1 records were imported under the original survey-date contract.
                initial_basis = "survey_date" if self.versions() else basis
                self.execute(
                    "INSERT INTO pipeline_dataset_contract (dataset,date_basis) VALUES (?,?)",
                    (dataset, initial_basis),
                )
            else:
                initial_basis = dict(existing)["date_basis"]
            if basis != initial_basis:
                raise ValueError(
                    "date_basis differs from warehouse contract; use a separate warehouse"
                )
            captured = envelope["retrieved_at"]
            prior_captures = [
                r["captured_at"] for r in self.runs() if r["status"] in {"succeeded", "partial"}
            ]
            if prior_captures and captured <= max(prior_captures):
                raise ValueError(
                    "captures must be promoted in chronological order; replay to rebuild"
                )
            current = {row["survey_date"]: row for row in self.gold()}
            count = 0
            for row in rows:
                prior = current.get(row.survey_date)
                if prior and prior["content_hash"] == row.content_hash:
                    continue
                version_id = hashlib.sha256(
                    f"{envelope['run_id']}:{row.survey_date}:{row.content_hash}".encode()
                ).hexdigest()
                version = {
                    **asdict(row),
                    "version_id": version_id,
                    "source": "aaii",
                    "dataset": envelope["manifest"]["dataset"],
                    "first_seen_at": captured,
                    "retrieved_at": captured,
                    "content_hash": row.content_hash,
                    "raw_run_id": envelope["run_id"],
                    "raw_sha256": envelope["sha256"],
                    "parser_version": envelope["parser_version"],
                }
                self._insert(
                    "aaii_silver_versions",
                    SILVER_COLUMNS,
                    tuple(version[k] for k in SILVER_COLUMNS),
                )
                count += 1
            self.execute("DELETE FROM aaii_gold_latest")
            for row in self.gold():
                self._insert("aaii_gold_latest", GOLD_COLUMNS, tuple(row[k] for k in GOLD_COLUMNS))
            self.status(envelope["run_id"], "succeeded", len(rows), count)
        return count
