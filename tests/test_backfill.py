import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from market_data_pipeline.aaii.backfill import backfill
from market_data_pipeline.aaii.io.warehouse import Warehouse
from market_data_pipeline.aaii.replay import replay


def test_full_history_is_explicit_strict_by_default_and_quarantine_is_auditable(tmp_path):
    workbook = Path("tests/fixtures/aaii/synthetic.xls")
    manifest = Path("manifests/aaii-investor-sentiment-xls.yml")
    with pytest.raises(ValueError, match="missing"):
        backfill(workbook, manifest, tmp_path / "strict", start="1987-01-01", end="2026-10-26")
    result = backfill(
        workbook,
        manifest,
        tmp_path / "history",
        start="1987-01-01",
        end="2026-10-26",
        quarantine=True,
        captured_at=datetime(2026, 10, 30, tzinfo=UTC),
    )
    assert result["status"] == "partial"
    assert result["row_count"] == 4 and result["quarantined_rows"] == 2
    report = json.loads(next((tmp_path / "history/bronze").rglob("quality.json")).read_text())
    assert [r["reported_date"] for r in report["quarantined"]] == ["1987-06-26", "2010-01-14"]
    assert report["gaps"]
    with Warehouse(tmp_path / "history") as warehouse:
        assert all(
            r["first_seen_at"] == "2026-10-30T00:00:00.000000Z" for r in warehouse.versions()
        )
        assert warehouse.runs()[0]["status"] == "partial"
    replayed = replay(tmp_path / "history", tmp_path / "restored")
    assert len(replayed["partial"]) == 1
    with Warehouse(tmp_path / "restored") as warehouse:
        assert len(warehouse.versions()) == 4
        assert warehouse.runs()[0]["status"] == "partial"
    result = backfill(
        workbook,
        manifest,
        tmp_path / "history",
        start="1987-01-01",
        end="2026-10-26",
        quarantine=True,
        captured_at=datetime(2026, 10, 31, tzinfo=UTC),
    )
    assert result["inserted_versions"] == 0
