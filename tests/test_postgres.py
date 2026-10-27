import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from market_data_pipeline.io.warehouse import Warehouse
from market_data_pipeline.pipeline import run


@pytest.mark.postgres
def test_real_postgres_revision_and_transaction_contract(tmp_path):
    dsn = os.environ.get("MARKET_DATA_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("set MARKET_DATA_TEST_POSTGRES_DSN to a dedicated empty test database")
    manifest = Path("manifests/aaii-investor-sentiment.yml")
    fixture = Path("tests/fixtures/aaii/sentiment.csv")
    with Warehouse(tmp_path, dsn) as warehouse:
        assert not warehouse.runs() and not warehouse.versions(), "test database must be empty"
    first = run(
        fixture, manifest, tmp_path, dsn=dsn, captured_at=datetime(2026, 10, 26, tzinfo=UTC)
    )
    assert first["inserted_versions"] == 2
    assert (
        run(fixture, manifest, tmp_path, dsn=dsn, captured_at=datetime(2026, 10, 27, tzinfo=UTC))[
            "inserted_versions"
        ]
        == 0
    )
    revised = tmp_path / "corrected.csv"
    revised.write_bytes(fixture.read_bytes().replace(b"40.0%,20.0%,40.0%", b"45.0%,20.0%,35.0%"))
    assert (
        run(revised, manifest, tmp_path, dsn=dsn, captured_at=datetime(2026, 10, 28, tzinfo=UTC))[
            "inserted_versions"
        ]
        == 1
    )
    with Warehouse(tmp_path, dsn) as warehouse:
        assert len(warehouse.versions()) == 3
        assert warehouse.gold()[1]["spread_change_pp"] == pytest.approx(-20)
        assert warehouse.gold("2026-10-27T23:59:00.000000Z")[1][
            "spread_change_pp"
        ] == pytest.approx(-10)
        with pytest.raises(RuntimeError), warehouse.transaction():
            warehouse.execute("DELETE FROM aaii_silver_versions")
            raise RuntimeError("force rollback")
        assert len(warehouse.versions()) == 3
    assert (
        run(fixture, manifest, tmp_path, dsn=dsn, captured_at=datetime(2026, 10, 29, tzinfo=UTC))[
            "inserted_versions"
        ]
        == 1
    )
    invalid = tmp_path / "invalid.csv"
    invalid.write_text("<html>not an export</html>")
    with pytest.raises(ValueError):
        run(invalid, manifest, tmp_path, dsn=dsn, captured_at=datetime(2026, 10, 30, tzinfo=UTC))
    with Warehouse(tmp_path, dsn) as warehouse:
        assert len(warehouse.versions()) == 4
        assert len(warehouse.gold()) == 2
        assert warehouse.runs()[-1]["status"] == "failed"
