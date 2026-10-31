"""Small, scheduler-independent AAII operational readouts."""

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from market_data_pipeline.aaii.io.parquet import current_snapshot
from market_data_pipeline.aaii.io.warehouse import Warehouse


def weekly_window(now: datetime, overlap_days: int = 28) -> tuple[str, str]:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("weekly window requires a timezone-aware time")
    if type(overlap_days) is not int or not 7 <= overlap_days <= 90:
        raise ValueError("overlap_days must be in [7,90]")
    end = now.astimezone(ZoneInfo("America/New_York")).date()
    return (end - timedelta(days=overlap_days)).isoformat(), end.isoformat()


def health_report(root: Path, *, dsn=None, now=None, max_age_days=10) -> dict:
    now = now or datetime.now(UTC)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("health cutoff requires a timezone")
    if type(max_age_days) is not int or max_age_days < 1:
        raise ValueError("max_age_days must be positive")
    if not (root / ".warehouse.json").exists():
        return {"healthy": False, "reasons": ["warehouse_not_initialized"]}
    with Warehouse(root, dsn) as warehouse:
        versions, runs = warehouse.versions(), warehouse.runs()
    reasons = []
    latest = max((r["survey_date"] for r in versions), default=None)
    last = runs[-1] if runs else None
    if last is None or last["status"] != "succeeded":
        reasons.append("latest_run_" + (last["status"] if last else "missing"))
    transport_failures = [
        json.loads(path.read_text())["captured_at"]
        for path in (root / "operations/transport").glob("*.json")
    ]
    last_transport_failure = max(transport_failures, default=None)
    if last_transport_failure and (last is None or last_transport_failure > last["captured_at"]):
        reasons.append("latest_transport_failed")
    today = now.astimezone(ZoneInfo("America/New_York")).date()
    age = (today - date.fromisoformat(latest)).days if latest else None
    if age is None or age > max_age_days:
        reasons.append("source_stale")
    successful = [r for r in runs if r["status"] == "succeeded"]
    captured = successful[-1]["captured_at"] if successful else None
    capture_age = (
        (now - datetime.fromisoformat(captured.replace("Z", "+00:00"))).total_seconds() / 86400
        if captured
        else None
    )
    if capture_age is None or capture_age > max_age_days:
        reasons.append("capture_stale")
    try:
        snapshot = current_snapshot(root)
        if not all(
            (snapshot / f"{name}.parquet").is_file() for name in ("silver", "gold", "audit")
        ):
            reasons.append("publication_unavailable")
    except (OSError, ValueError, KeyError):
        reasons.append("publication_unavailable")
    return {
        "healthy": not reasons,
        "reasons": reasons,
        "latest_reported_date": latest,
        "reported_age_days": age,
        "last_successful_capture": captured,
        "last_transport_failure": last_transport_failure,
        "latest_run_status": last["status"] if last else None,
        "silver_versions": len(versions),
    }
