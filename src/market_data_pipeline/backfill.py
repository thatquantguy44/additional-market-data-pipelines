"""Explicit local-file historical import; never downloads historical data implicitly."""

from datetime import UTC, datetime
from pathlib import Path

from market_data_pipeline.catalogs.manifest import load_manifest
from market_data_pipeline.data.aaii_xls import selection
from market_data_pipeline.io.bronze import archive, writer_lock
from market_data_pipeline.pipeline import MAX_INPUT_BYTES, promote_capture


def backfill(
    input_path: Path,
    manifest_path: Path,
    root: Path,
    *,
    start: str,
    end: str,
    quarantine=False,
    dsn=None,
    captured_at=None,
) -> dict:
    manifest = load_manifest(manifest_path)
    if manifest.format != "xls":
        raise ValueError("historical backfill requires the explicit XLS manifest")
    bounds = selection(start, end, max_days=None)
    captured_at = captured_at or datetime.now(UTC)
    if bounds[1] > captured_at.date():
        raise ValueError("backfill selection cannot end after capture date")
    with input_path.open("rb") as file:
        payload = file.read(MAX_INPUT_BYTES + 1)
    if len(payload) > MAX_INPUT_BYTES:
        raise ValueError("input exceeds 20 MiB limit")
    with writer_lock(root):
        envelope, directory = archive(
            root,
            payload,
            manifest,
            input_path,
            captured_at,
            date_selection={
                "start": start,
                "end": end,
                "mode": "backfill",
                "on_invalid": "quarantine" if quarantine else "error",
            },
        )
        return promote_capture(root, envelope, payload, manifest, directory, dsn)
