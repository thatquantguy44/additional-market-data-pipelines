from datetime import UTC, datetime
from pathlib import Path

import pytest

from market_data_pipeline.pipelines.aaii.io.warehouse import Warehouse
from market_data_pipeline.pipelines.aaii.pipeline import run
from market_data_pipeline.pipelines.aaii.recovery import backup, restore, retain_snapshots


def populated(root):
    run(
        Path("tests/fixtures/aaii/sentiment.csv"),
        Path("manifests/aaii-investor-sentiment.yml"),
        root,
        captured_at=datetime(2026, 10, 26, tzinfo=UTC),
    )


def test_backup_restore_preserves_versions_gold_and_original_bytes(tmp_path):
    source = tmp_path / "source"
    populated(source)
    package = tmp_path / "backup"
    result = backup(source, package)
    assert result["files"] > 0
    restored = tmp_path / "restored"
    restore(package, restored)
    with Warehouse(source) as a, Warehouse(restored) as b:
        assert a.versions() == b.versions()
        assert a.gold() == b.gold()
        assert all(Path(r["bronze_path"]).is_dir() for r in b.runs())
    with pytest.raises(ValueError, match="empty"):
        restore(package, restored)
    raw = next((package / "bronze").rglob("payload.csv"))
    raw.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="digest"):
        restore(package, tmp_path / "bad")
    assert not (tmp_path / "bad").exists()


def test_retention_requires_apply_and_protects_current_and_bronze(tmp_path):
    root = tmp_path / "source"
    populated(root)
    manifest = Path("manifests/aaii-investor-sentiment.yml")
    fixture = Path("tests/fixtures/aaii/sentiment.csv")
    for day in (27, 28):
        run(fixture, manifest, root, captured_at=datetime(2026, 10, day, tzinfo=UTC))
    pointer = (root / "parquet/current.json").read_bytes()
    dry = retain_snapshots(root, keep=1)
    assert len(dry["remove"]) == 2
    assert len(list((root / "parquet/snapshots").iterdir())) == 3
    applied = retain_snapshots(root, keep=1, apply=True)
    assert applied["applied"]
    assert len(list((root / "parquet/snapshots").iterdir())) == 1
    assert (root / "parquet/current.json").read_bytes() == pointer
    assert len(list((root / "bronze").rglob("metadata.json"))) == 3
