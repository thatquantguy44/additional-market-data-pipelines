from pathlib import Path

import pytest

from market_data_pipeline.io.databricks import publish_delta


@pytest.mark.parametrize("catalog,schema", [("x; DROP TABLE t", "aaii"), ("main", "a.b")])
def test_delta_publisher_rejects_sql_identifier_injection(catalog, schema):
    with pytest.raises(ValueError, match="identifiers"):
        publish_delta(None, Path("/Volumes/example/export"), catalog, schema)


def test_delta_publisher_requires_volume_staging():
    with pytest.raises(ValueError, match="Volumes"):
        publish_delta(None, Path("data/aaii/parquet"), "main", "market_data")
