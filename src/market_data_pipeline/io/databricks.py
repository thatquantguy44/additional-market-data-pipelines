"""Publish a committed snapshot to Unity Catalog Delta tables using an existing Spark session.

https://docs.databricks.com/aws/en/delta/merge
https://docs.databricks.com/aws/en/volumes/volume-files
"""

import json
import re
import uuid
from pathlib import Path

from market_data_pipeline.io.warehouse import RUN_COLUMNS, SILVER_COLUMNS


def _identifier(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError("catalog and schema must be simple SQL identifiers")
    return f"`{value}`"


def publish_delta(spark, snapshot: Path, catalog: str, schema: str) -> dict[str, str]:
    """Insert immutable revisions, then derive Gold from all persisted revisions.

    The caller supplies an existing UC schema and a shared /Volumes snapshot.
    Each Delta commit is atomic independently; retry after cross-table failure.
    """
    namespace = f"{_identifier(catalog)}.{_identifier(schema)}"
    snapshot = Path(snapshot)
    if not str(snapshot).startswith("/Volumes/"):
        raise ValueError(
            "Databricks publishing requires a snapshot in a Unity Catalog /Volumes path"
        )
    manifest = json.loads((snapshot / "manifest.json").read_text())
    if manifest.get("dataset") != "aaii-investor-sentiment" or manifest.get("schema_version") != 1:
        raise ValueError("unsupported snapshot manifest")
    tables = {}
    for name, columns, key in (
        ("silver", SILVER_COLUMNS, "version_id"),
        ("audit", RUN_COLUMNS, "run_id"),
    ):
        frame = spark.read.parquet(str(snapshot / f"{name}.parquet"))
        if set(frame.columns) != set(columns):
            raise ValueError(f"unexpected {name} Parquet schema")
        if frame.filter(f"{key} IS NULL").limit(1).count():
            raise ValueError(f"null {name} key")
        count = frame.count()
        if frame.select(key).distinct().count() != count:
            raise ValueError(f"duplicate {name} keys")
        if name == "silver" and count != manifest["silver_rows"]:
            raise ValueError("snapshot row count mismatch")
        stage = f"aaii_stage_{uuid.uuid4().hex}"
        table = (
            f"{namespace}.`aaii_{name}_versions`"
            if name == "silver"
            else f"{namespace}.`aaii_pipeline_runs`"
        )
        frame.createOrReplaceTempView(stage)
        try:
            spark.sql(
                f"CREATE TABLE IF NOT EXISTS {table} USING DELTA AS "
                f"SELECT * FROM {stage} WHERE false"
            )
            spark.sql(
                f"MERGE INTO {table} t USING {stage} s ON t.{key} = s.{key} "
                "WHEN NOT MATCHED THEN INSERT *"
            )
        finally:
            spark.catalog.dropTempView(stage)
        tables[name] = table
    gold = f"{namespace}.`aaii_gold_latest`"
    silver_columns = ", ".join(SILVER_COLUMNS)
    spark.sql(f"""CREATE OR REPLACE VIEW {gold} AS
        WITH ranked AS (
            SELECT *, ROW_NUMBER() OVER (
                PARTITION BY dataset, survey_date ORDER BY first_seen_at DESC, version_id DESC
            ) AS revision_rank FROM {tables["silver"]}
        ), latest AS (SELECT {silver_columns} FROM ranked WHERE revision_rank=1),
        history AS (
            SELECT *, (bullish-bearish)*100 AS bull_bear_spread_pp,
                LAG(survey_date) OVER (
                    PARTITION BY dataset ORDER BY survey_date) previous_survey_date,
                LAG(version_id) OVER (
                    PARTITION BY dataset ORDER BY survey_date) previous_version_id,
                LAG((bullish-bearish)*100) OVER (
                    PARTITION BY dataset ORDER BY survey_date
                ) previous_spread
            FROM latest
        ) SELECT {silver_columns}, bull_bear_spread_pp, previous_survey_date,
            DATEDIFF(survey_date, previous_survey_date) gap_days,
            bull_bear_spread_pp-previous_spread spread_change_pp, previous_version_id FROM history
    """)
    return {**tables, "gold": gold}
