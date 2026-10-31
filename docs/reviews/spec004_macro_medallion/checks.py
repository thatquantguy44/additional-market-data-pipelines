"""Review-only probes against an explicit MacroMedallion checkout.

Uses synthetic records and disposable SQLite files only. Run with the sibling's
Python using -B; no runtime configuration, credentials or live database is loaded.
This is review evidence, not a MarketMedallion runtime dependency or connector.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from decimal import Decimal
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(args.checkout.resolve() / "src"))

    from fred_pipeline.config import Environment, PipelineConfig
    from fred_pipeline.cross_series_config import CrossSeriesDef
    from fred_pipeline.data.silver import build_silver_rows
    from fred_pipeline.io.local_store import LocalWarehouse
    from fred_pipeline.manifest import Manifest, SeriesSpec
    from fred_pipeline.replay import replay_from_bronze
    from fred_pipeline.writer.features import (
        compute_cross_series_features,
        point_in_time_snapshot,
    )

    sid = "ECB:EXR:D.USD.EUR.SP00.A"
    capture = "2026-10-30T12:00:00+00:00"
    config = PipelineConfig(environment=Environment.DEV, fred_api_key="synthetic-unused")
    result = {}

    def payload(value, *, status="A", key="D.USD.EUR.SP00.A", valid_from="", action=""):
        header = "KEY,TIME_PERIOD,OBS_VALUE,OBS_STATUS,VALID_FROM,VALID_TO,ACTION\n"
        return {"data": header + f"EXR.{key},2024-01-02,{value},{status},{valid_from},,{action}\n"}

    def rows(value, **kwargs):
        return build_silver_rows(
            sid,
            payload(value, **kwargs),
            run_id="synthetic-review",
            ingested_at=capture,
            track_vintage=True,
            source="ecb",
        )

    exact = "1.123456789012345678900"
    parsed = rows(exact)[0]
    assert parsed["raw_value"] == exact
    assert Decimal(str(parsed["value"])) != Decimal(exact)
    result["precision"] = {
        "synthetic_raw_value": exact,
        "parsed_value": repr(parsed["value"]),
        "raw_text_preserved": True,
        "numeric_round_trip_exact": False,
    }

    normal = rows("1.2500", status="A")[0]
    changed_status = rows("1.2500", status="E")[0]
    wrong_dimension = rows("1.2500", key="D.JPY.EUR.SP00.A")[0]
    assert normal["row_hash"] == changed_status["row_hash"]
    assert wrong_dimension["series_id"] == sid
    result["metadata"] = {
        "status_only_change_changes_hash": False,
        "mismatched_payload_currency_rejected_by_normalizer": False,
        "silver_fields": sorted(normal),
    }

    with tempfile.TemporaryDirectory(prefix="spec004-fx-review-") as temp:
        warehouse = LocalWarehouse(config, db_path=str(Path(temp) / "revision.db"))
        for i, value in enumerate(["1.25", "1.30", "1.25"], 1):
            batch = rows(value)
            batch[0]["ingested_at"] = f"2026-10-30T12:00:0{i}+00:00"
            warehouse.merge_silver(batch)
        stored = warehouse.query("SELECT raw_value, ingested_at FROM silver_fred_observation")
        assert len(stored) == 1
        assert stored[0]["raw_value"] == "1.25"
        warehouse.merge_silver(rows("1.25"))
        unchanged = warehouse.query("SELECT ingested_at FROM silver_fred_observation")[0]
        assert unchanged["ingested_at"] == stored[0]["ingested_at"]
        result["capture_revisions"] = {
            "synthetic_sequence": ["1.25", "1.30", "1.25"],
            "retained_rows": len(stored),
            "unchanged_rerun_preserves_capture": True,
        }
        warehouse.merge_silver(rows("", action="Delete"))
        assert len(warehouse.query("SELECT * FROM silver_fred_observation")) == 1
        result["withdrawal"] = {"previous_row_still_present_after_delete_payload": True}
        warehouse.close()

        warehouse = LocalWarehouse(config, db_path=str(Path(temp) / "intraday.db"))
        morning = rows("1.25", valid_from="2024-01-02T09:00:00+01:00")
        afternoon = rows("1.30", valid_from="2024-01-02T16:00:00+01:00")
        assert morning[0]["realtime_start"] == afternoon[0]["realtime_start"]
        warehouse.merge_silver(morning)
        warehouse.merge_silver(afternoon)
        count = warehouse.query("SELECT count(*) n FROM silver_fred_observation")[0]["n"]
        assert count == 1
        result["intraday"] = {"two_provider_timestamps_retain_rows": count}
        warehouse.close()

        captured_later = rows("1.25", valid_from="2024-01-02T16:00:00+01:00")
        snapshot = point_in_time_snapshot(captured_later, "2024-01-03")
        assert len(snapshot) == 1
        future = dict(normal, observation_date="2027-01-02")
        assert len(point_in_time_snapshot([future], "2024-01-03")) == 1
        result["as_of"] = {
            "later_capture_returned_for_earlier_cutoff": True,
            "future_observation_with_blank_vintage_returned": True,
        }

        warehouse = LocalWarehouse(config, db_path=str(Path(temp) / "replay.db"))
        old_capture = "2024-01-03T12:00:00+00:00"
        warehouse.write_bronze(
            [
                {
                    "run_id": "synthetic-original",
                    "source": "ecb",
                    "series_id": sid,
                    "response_payload": json.dumps(payload("1.2500")),
                    "ingested_at": old_capture,
                }
            ]
        )
        spec = SeriesSpec(series_id=sid, title="synthetic USD per EUR", frequency="d", source="ecb")
        manifest = Manifest.from_dict({"name": "synthetic", "series": [spec.to_dict()]})
        replay_from_bronze(config, [manifest], warehouse, rebuild_gold=False)
        replayed = warehouse.query("SELECT ingested_at, raw_value FROM silver_fred_observation")[0]
        assert replayed["ingested_at"] != old_capture
        assert replayed["raw_value"] == "1.2500"
        result["replay"] = {
            "original_capture_preserved": False,
            "original_numeric_text_preserved": True,
        }
        warehouse.close()

    definition = CrossSeriesDef(
        name="synthetic_usd_jpy",
        op="ratio",
        frequency="d",
        legs=(("JPY", 1.0), ("USD", 1.0)),
    )
    legs = [
        {"series_id": "JPY", "observation_date": "2024-01-02", "value": 150.0},
        {"series_id": "USD", "observation_date": "2024-01-02", "value": 1.25},
    ]
    cross = compute_cross_series_features(legs, [definition])
    assert len(cross) == 1 and cross[0]["value"] == 120.0
    legs[1]["observation_date"] = "2024-01-03"
    assert compute_cross_series_features(legs, [definition]) == []
    result["cross_rates"] = {
        "same_date_synthetic_usd_jpy": 120.0,
        "different_dates_produce_no_cross": True,
        "returned_fields": sorted(cross[0]),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
