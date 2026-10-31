import json
import uuid
from datetime import date, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from market_data_pipeline.aaii.io.warehouse import GOLD_COLUMNS, RUN_COLUMNS, SILVER_COLUMNS
from market_data_pipeline.shared.files import atomic_json

TIMESTAMPS = {
    "first_seen_at",
    "retrieved_at",
    "provider_published_at",
    "captured_at",
    "completed_at",
}
DATES = {"survey_date", "previous_survey_date"}
FLOATS = {"bullish", "neutral", "bearish", "bull_bear_spread_pp", "spread_change_pp"}
INTEGERS = {"gap_days", "row_count", "inserted_versions"}


def _table(rows, columns):
    schema = pa.schema(
        [
            (
                key,
                pa.timestamp("us", tz="UTC")
                if key in TIMESTAMPS
                else pa.date32()
                if key in DATES
                else pa.float64()
                if key in FLOATS
                else pa.int64()
                if key in INTEGERS
                else pa.string(),
            )
            for key in columns
        ]
    )
    converted = []
    for row in rows:
        values = dict(row)
        for key in TIMESTAMPS & values.keys():
            if values[key] is not None:
                values[key] = datetime.fromisoformat(values[key].replace("Z", "+00:00"))
        for key in DATES & values.keys():
            if values[key] is not None:
                values[key] = date.fromisoformat(values[key])
        converted.append(values)
    return pa.Table.from_pylist(converted, schema=schema)


def publish(root: Path, warehouse) -> str:
    """Only current.json makes a fully written immutable snapshot visible.

    https://arrow.apache.org/docs/python/generated/pyarrow.parquet.write_table.html
    """
    snapshot = root / "parquet" / "snapshots" / uuid.uuid4().hex
    snapshot.mkdir(parents=True)
    # Read under a DB transaction, so one snapshot cannot mix warehouse states.
    with warehouse.transaction():
        versions, gold, runs = warehouse.versions(), warehouse.gold(), warehouse.runs()
    for name, rows, columns in (
        ("silver", versions, SILVER_COLUMNS),
        ("gold", gold, GOLD_COLUMNS),
        ("audit", runs, RUN_COLUMNS),
    ):
        pq.write_table(_table(rows, columns), snapshot / f"{name}.parquet", compression="zstd")
    atomic_json(
        snapshot / "manifest.json",
        {
            "dataset": "aaii-investor-sentiment",
            "silver_rows": len(versions),
            "gold_rows": len(gold),
            "schema_version": 1,
        },
    )
    relative = str(snapshot.relative_to(root))
    atomic_json(root / "parquet/current.json", {"snapshot": relative, "schema_version": 1})
    return str(snapshot)


def current_snapshot(root: Path) -> Path:
    pointer = json.loads((root / "parquet/current.json").read_text())
    if pointer.get("schema_version") != 1:
        raise ValueError("unsupported snapshot schema")
    snapshot = (root / pointer["snapshot"]).resolve()
    if not snapshot.is_relative_to((root / "parquet/snapshots").resolve()):
        raise ValueError("invalid snapshot path")
    return snapshot
