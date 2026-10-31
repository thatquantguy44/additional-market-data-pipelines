import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from market_data_pipeline.io.warehouse import Warehouse
from market_data_pipeline.pipeline import export, run
from market_data_pipeline.replay import replay

MANIFEST = Path("manifests/aaii-investor-sentiment.yml")
FIXTURE = Path("tests/fixtures/aaii/sentiment.csv")


def at(day):
    return datetime(2026, 10, day, 12, tzinfo=UTC)


def test_parquet_revisions_reversion_asof_and_replay(tmp_path):
    root = tmp_path / "original"
    first = run(FIXTURE, MANIFEST, root, captured_at=at(26))
    assert first["inserted_versions"] == 2
    assert run(FIXTURE, MANIFEST, root, captured_at=at(27))["inserted_versions"] == 0
    corrected = tmp_path / "revised.csv"
    corrected.write_bytes(FIXTURE.read_bytes().replace(b"40.0%,20.0%,40.0%", b"45.0%,20.0%,35.0%"))
    assert run(corrected, MANIFEST, root, captured_at=at(28))["inserted_versions"] == 1
    with Warehouse(root) as warehouse:
        assert warehouse.gold()[1]["spread_change_pp"] == pytest.approx(-20)
        assert warehouse.gold("2026-10-27T23:59:00.000000Z")[1][
            "spread_change_pp"
        ] == pytest.approx(-10)
        assert warehouse.gold()[1]["gap_days"] == 14
    assert run(FIXTURE, MANIFEST, root, captured_at=at(29))["inserted_versions"] == 1
    pointer = json.loads((root / "parquet/current.json").read_text())
    silver = pq.read_table(root / pointer["snapshot"] / "silver.parquet")
    gold = pq.read_table(root / pointer["snapshot"] / "gold.parquet")
    assert silver.num_rows == 4
    assert gold.num_rows == 2
    assert str(silver.schema.field("provider_published_at").type) == "timestamp[us, tz=UTC]"
    restored = tmp_path / "restored"
    result = replay(root, restored)
    assert result["succeeded"] == 4
    with Warehouse(root) as original, Warehouse(restored) as rebuilt:
        assert original.versions() == rebuilt.versions()
        assert original.gold() == rebuilt.gold()
    with pytest.raises(ValueError, match="empty"):
        replay(root, restored)


def test_invalid_capture_keeps_raw_and_cannot_replace_parquet(tmp_path):
    run(FIXTURE, MANIFEST, tmp_path, captured_at=at(26))
    pointer = (tmp_path / "parquet/current.json").read_bytes()
    bad = tmp_path / "bad.csv"
    bad.write_text("<html>Login required</html>")
    with pytest.raises(ValueError):
        run(bad, MANIFEST, tmp_path, captured_at=at(27))
    assert pointer == (tmp_path / "parquet/current.json").read_bytes()
    assert any(
        p.read_bytes() == bad.read_bytes() for p in (tmp_path / "bronze").rglob("payload.csv")
    )
    with Warehouse(tmp_path) as warehouse:
        assert len(warehouse.versions()) == 2
        assert warehouse.runs()[-1]["status"] == "failed"
        assert warehouse.runs()[-1]["dq_message"]


def test_export_failure_is_partial_and_repairable(tmp_path, monkeypatch):
    import market_data_pipeline.pipeline as pipeline

    def fail(*args):
        raise OSError("simulated disk full")

    monkeypatch.setattr(pipeline, "publish", fail)
    with pytest.raises(OSError):
        run(FIXTURE, MANIFEST, tmp_path, captured_at=at(26))
    with Warehouse(tmp_path) as warehouse:
        assert len(warehouse.versions()) == 2
        assert warehouse.runs()[0]["status"] == "partial"
    monkeypatch.undo()
    assert Path(export(tmp_path)).exists()


def test_manifest_failure_has_no_side_effects_and_archive_tampering_is_rejected(tmp_path):
    invalid = tmp_path / "invalid.yml"
    invalid.write_text("source: invalid")
    root = tmp_path / "output"
    with pytest.raises(ValueError):
        run(FIXTURE, invalid, root)
    assert not root.exists()
    run(FIXTURE, MANIFEST, root, captured_at=at(26))
    next((root / "bronze").rglob("payload.csv")).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="digest"):
        replay(root, tmp_path / "restored")


def test_replay_retains_rejections_and_never_promotes_an_out_of_order_capture(tmp_path):
    root = tmp_path / "source"
    run(FIXTURE, MANIFEST, root, captured_at=at(26))
    run(FIXTURE, MANIFEST, root, captured_at=at(28))
    revised = tmp_path / "revised.csv"
    revised.write_bytes(FIXTURE.read_bytes().replace(b"40.0%,20.0%,40.0%", b"45.0%,20.0%,35.0%"))
    with pytest.raises(ValueError, match="chronological"):
        run(revised, MANIFEST, root, captured_at=at(27))
    result = replay(root, tmp_path / "replayed")
    assert result["succeeded"] == 2
    assert len(result["rejected"]) == 1
    with Warehouse(tmp_path / "replayed") as rebuilt:
        assert len(rebuilt.versions()) == 2
        assert len(rebuilt.runs()) == 3


def test_warehouse_root_cannot_be_reused_for_another_backend(tmp_path):
    run(FIXTURE, MANIFEST, tmp_path, captured_at=at(26))
    with pytest.raises(ValueError, match="different warehouse"):
        Warehouse(tmp_path, "postgresql://unused.invalid/never_connect")


def test_asof_cutoff_normalizes_offsets_and_rejects_naive_timestamps(tmp_path):
    run(FIXTURE, MANIFEST, tmp_path, captured_at=at(26))
    with Warehouse(tmp_path) as warehouse:
        assert warehouse.gold("2026-10-26T08:00:00-04:00") == warehouse.gold()
        assert warehouse.gold("2026-10-26T07:59:59-04:00") == []
        with pytest.raises(ValueError, match="timezone"):
            warehouse.gold("2026-10-26")


def test_overlapping_local_runs_serialize_without_duplicate_versions(tmp_path):
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(run, FIXTURE, MANIFEST, tmp_path) for _ in range(2)]
        results = [future.result() for future in futures]
    assert sorted(result["inserted_versions"] for result in results) == [0, 2]
    with Warehouse(tmp_path) as warehouse:
        assert len(warehouse.versions()) == 2
        assert all(record["status"] == "succeeded" for record in warehouse.runs())


def test_partial_parquet_generation_never_changes_current_pointer(tmp_path, monkeypatch):
    run(FIXTURE, MANIFEST, tmp_path, captured_at=at(26))
    pointer = (tmp_path / "parquet/current.json").read_bytes()
    original = pq.write_table

    def fail_gold(table, where, **kwargs):
        if Path(where).name == "gold.parquet":
            raise OSError("simulated failure after Silver file closes")
        return original(table, where, **kwargs)

    monkeypatch.setattr(pq, "write_table", fail_gold)
    with pytest.raises(OSError):
        run(FIXTURE, MANIFEST, tmp_path, captured_at=at(27))
    assert (tmp_path / "parquet/current.json").read_bytes() == pointer


def test_reported_date_contract_cannot_silently_mix_with_existing_survey_dates(tmp_path):
    from market_data_pipeline.aaii.manifest import load_manifest
    from market_data_pipeline.io.bronze import load_archive

    run(FIXTURE, MANIFEST, tmp_path, captured_at=at(26))
    envelope, _ = load_archive(next((tmp_path / "bronze").rglob("metadata.json")).parent)
    envelope["manifest"]["date_basis"] = "reported_date"
    envelope["run_id"] = "f" * 32
    envelope["retrieved_at"] = "2026-10-27T00:00:00.000000Z"
    from market_data_pipeline.aaii.data.csv import normalize

    with Warehouse(tmp_path) as warehouse:
        warehouse.record_run(envelope, "not-promoted")
        with pytest.raises(ValueError, match="date_basis"):
            warehouse.promote(
                normalize(FIXTURE.read_bytes(), load_manifest(MANIFEST), at(27).date()), envelope
            )
        assert len(warehouse.versions()) == 2
