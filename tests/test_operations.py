import io
from datetime import UTC, datetime
from pathlib import Path

import pytest

from market_data_pipeline.operations import health_report, weekly_window
from market_data_pipeline.pipeline import run


def test_weekly_window_uses_new_york_date_and_bounded_overlap():
    assert weekly_window(datetime(2026, 10, 30, 1, tzinfo=UTC), 28) == ("2026-10-01", "2026-10-29")
    with pytest.raises(ValueError):
        weekly_window(datetime(2026, 10, 30), 28)
    with pytest.raises(ValueError):
        weekly_window(datetime(2026, 10, 30, tzinfo=UTC), 100)


def test_freshness_reports_missing_stale_and_failed_state(tmp_path):
    assert not health_report(tmp_path, now=datetime(2026, 10, 30, tzinfo=UTC))["healthy"]
    fixture = Path("tests/fixtures/aaii/sentiment.csv")
    manifest = Path("manifests/aaii-investor-sentiment.yml")
    run(fixture, manifest, tmp_path, captured_at=datetime(2026, 10, 26, tzinfo=UTC))
    assert health_report(tmp_path, now=datetime(2026, 10, 30, tzinfo=UTC))["healthy"]
    stale = health_report(tmp_path, now=datetime(2026, 11, 15, tzinfo=UTC))
    assert not stale["healthy"] and "source_stale" in stale["reasons"]
    bad = tmp_path / "bad.csv"
    bad.write_text("bad")
    with pytest.raises(ValueError):
        run(bad, manifest, tmp_path, captured_at=datetime(2026, 10, 30, tzinfo=UTC))
    assert (
        "latest_run_failed"
        in health_report(tmp_path, now=datetime(2026, 10, 30, tzinfo=UTC))["reasons"]
    )


def test_transient_retry_archives_each_http_response_without_duplicate_versions(tmp_path):
    from market_data_pipeline.sources.aaii import run_live

    data = Path("tests/fixtures/aaii/synthetic.xls").read_bytes()
    sleeps = []
    attempts = []

    class Response(io.BytesIO):
        def __init__(self, status, payload):
            super().__init__(payload)
            self.code = status
            self.headers = {"Retry-After": "0"}

    def transport(*args, **kwargs):
        attempts.append(1)
        return Response(503, b"try later") if len(attempts) == 1 else Response(200, data)

    result = run_live(
        Path("manifests/aaii-investor-sentiment-xls.yml"),
        tmp_path,
        start="2026-10-01",
        end="2026-10-26",
        transport=transport,
        clock=lambda: datetime(2026, 10, 30, tzinfo=UTC),
        max_attempts=3,
        sleeper=sleeps.append,
    )
    assert result["inserted_versions"] == 3
    assert len(attempts) == 2
    assert len(list((tmp_path / "bronze").rglob("metadata.json"))) == 2


def test_live_schedule_is_stopped_and_skips_without_access_ack(monkeypatch):
    import dagster as dg

    from market_data_pipeline.orchestration.dagster_defs import live_schedule

    monkeypatch.delenv("MARKET_MEDALLION_CONFIG", raising=False)
    assert live_schedule.default_status == dg.DefaultScheduleStatus.STOPPED
    context = dg.build_schedule_context(scheduled_execution_time=datetime(2026, 10, 30, tzinfo=UTC))
    assert live_schedule.evaluate_tick(context).skip_message


def test_transport_failure_makes_recent_data_unhealthy_until_next_success(tmp_path):
    from urllib.error import URLError

    from market_data_pipeline.sources.aaii import run_live

    fixture = Path("tests/fixtures/aaii/synthetic.xls")
    manifest = Path("manifests/aaii-investor-sentiment-xls.yml")
    run(
        fixture,
        manifest,
        tmp_path,
        start="2026-10-01",
        end="2026-10-26",
        captured_at=datetime(2026, 10, 26, tzinfo=UTC),
    )

    def failed(*args, **kwargs):
        raise URLError("offline")

    with pytest.raises(ValueError, match="transport failed"):
        run_live(
            manifest,
            tmp_path,
            start="2026-10-01",
            end="2026-10-26",
            transport=failed,
            clock=lambda: datetime(2026, 10, 27, tzinfo=UTC),
        )
    assert (
        "latest_transport_failed"
        in health_report(tmp_path, now=datetime(2026, 10, 28, tzinfo=UTC))["reasons"]
    )
    run(
        fixture,
        manifest,
        tmp_path,
        start="2026-10-01",
        end="2026-10-26",
        captured_at=datetime(2026, 10, 28, tzinfo=UTC),
    )
    assert health_report(tmp_path, now=datetime(2026, 10, 29, tzinfo=UTC))["healthy"]


def test_schedule_requires_configured_ack_then_uses_dynamic_overlap(tmp_path, monkeypatch):
    import dagster as dg

    from market_data_pipeline.orchestration.dagster_defs import live_schedule

    config = tmp_path / "runtime.yml"
    config.write_text("warehouse: sqlite\noperations:\n  scheduled_live_access: false\n")
    monkeypatch.setenv("MARKET_MEDALLION_CONFIG", str(config))
    context = dg.build_schedule_context(
        scheduled_execution_time=datetime(2026, 11, 5, 15, tzinfo=UTC)
    )
    assert live_schedule.evaluate_tick(context).skip_message
    config.write_text(
        "warehouse: sqlite\noperations:\n  overlap_days: 21\n  scheduled_live_access: true\n"
    )
    request = live_schedule.evaluate_tick(context).run_requests[0]
    options = request.run_config["ops"]["aaii_sentiment"]["config"]
    assert (options["start"], options["end"]) == ("2026-10-15", "2026-11-05")
    assert options["live"] is True and options["config_path"] == str(config)


def test_retry_after_long_wait_is_not_shortened(tmp_path):
    from market_data_pipeline.sources.aaii import run_live

    class Response(io.BytesIO):
        code = 429
        headers = {"Retry-After": "120"}

    sleeps = []
    with pytest.raises(ValueError, match="HTTP 429"):
        run_live(
            Path("manifests/aaii-investor-sentiment-xls.yml"),
            tmp_path,
            start="2026-10-01",
            end="2026-10-26",
            transport=lambda *a, **kw: Response(b"throttled"),
            clock=lambda: datetime(2026, 10, 30, tzinfo=UTC),
            sleeper=sleeps.append,
            max_attempts=3,
        )
    assert sleeps == []
    assert len(list((tmp_path / "bronze").rglob("metadata.json"))) == 1
