# Databricks notebook source
# Install this repository's built wheel on the job cluster first.
# Copy the entire data root (Bronze + committed Parquet snapshots) to a UC volume.
from pathlib import Path

from market_data_pipeline.aaii.io.databricks import publish_delta

dbutils.widgets.text("snapshot", "")  # noqa: F821
dbutils.widgets.text("catalog", "")  # noqa: F821
dbutils.widgets.text("schema", "")  # noqa: F821
result = publish_delta(
    spark,  # noqa: F821
    Path(dbutils.widgets.get("snapshot")),  # noqa: F821
    dbutils.widgets.get("catalog"),  # noqa: F821
    dbutils.widgets.get("schema"),  # noqa: F821
)
print(result)
