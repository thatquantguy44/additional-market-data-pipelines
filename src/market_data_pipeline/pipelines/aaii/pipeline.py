import logging
from datetime import UTC, date, datetime
from pathlib import Path

from market_data_pipeline.pipelines.aaii.data.csv import normalize
from market_data_pipeline.pipelines.aaii.data.xls import normalize_xls, selection
from market_data_pipeline.pipelines.aaii.io.bronze import archive
from market_data_pipeline.pipelines.aaii.io.parquet import publish
from market_data_pipeline.pipelines.aaii.io.warehouse import Warehouse
from market_data_pipeline.pipelines.aaii.manifest import load_manifest
from market_data_pipeline.shared.files import atomic_json, writer_lock

logger = logging.getLogger(__name__)
MAX_INPUT_BYTES = 20 * 1024 * 1024


def promote_capture(root, envelope, payload, manifest, bronze_path, dsn=None):
    run_id = envelope["run_id"]
    with Warehouse(root, dsn) as warehouse:
        warehouse.record_run(envelope, str(bronze_path))
        try:
            if envelope["http_status"] is not None and envelope["http_status"] != 200:
                raise ValueError(f"AAII download returned HTTP {envelope['http_status']}")
            captured_date = datetime.fromisoformat(
                envelope["retrieved_at"].replace("Z", "+00:00")
            ).date()
            quarantined = []
            quality_message = None
            if manifest.format == "xls":
                bounds = envelope.get("selection", {})
                is_backfill = envelope["parser_version"] == "aaii-xls-v2"
                use_quarantine = is_backfill and bounds.get("on_invalid") == "quarantine"
                rows = normalize_xls(
                    payload,
                    manifest,
                    captured_date,
                    selection(
                        bounds.get("start"), bounds.get("end"), max_days=None if is_backfill else 90
                    ),
                    quarantine=quarantined if use_quarantine else None,
                )
                if is_backfill:
                    gaps = [
                        {
                            "previous_reported_date": a.survey_date,
                            "reported_date": b.survey_date,
                            "gap_days": (
                                date.fromisoformat(b.survey_date)
                                - date.fromisoformat(a.survey_date)
                            ).days,
                        }
                        for a, b in zip(rows, rows[1:], strict=False)
                        if (
                            date.fromisoformat(b.survey_date) - date.fromisoformat(a.survey_date)
                        ).days
                        > 8
                    ]
                    atomic_json(
                        bronze_path / "quality.json",
                        {
                            "accepted_rows": len(rows),
                            "quarantined": quarantined,
                            "gaps": gaps,
                            "selection": bounds,
                        },
                    )
                    if quarantined:
                        quality_message = (
                            f"Historical backfill: {len(quarantined)} rows quarantined; "
                            "review quality.json"
                        )
            else:
                rows = normalize(payload, manifest, captured_date)
            inserted = warehouse.promote(rows, envelope, quality_message=quality_message)
        except Exception as exc:
            # Validation messages contain row/rule details, never data or credentials.
            message = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            warehouse.status(run_id, "failed", message=message)
            if isinstance(exc, ValueError):
                atomic_json(bronze_path / "promotion.json", {"accepted": False, "reason": message})
            logger.error(
                "dataset=%s run_id=%s status=failed reason=%s", manifest.dataset, run_id, message
            )
            raise
        try:
            atomic_json(
                bronze_path / "promotion.json",
                {
                    "accepted": True,
                    "row_count": len(rows),
                    "inserted_versions": inserted,
                    "quarantined_rows": len(quarantined),
                },
            )
            snapshot = publish(root, warehouse)
        except Exception as exc:
            warehouse.status(
                run_id,
                "partial",
                len(rows),
                inserted,
                f"Parquet export failed: {type(exc).__name__}",
            )
            logger.error(
                "dataset=%s run_id=%s status=partial stage=parquet", manifest.dataset, run_id
            )
            raise
    result = {
        "run_id": run_id,
        "status": "partial" if quarantined else "succeeded",
        "row_count": len(rows),
        "quarantined_rows": len(quarantined),
        "inserted_versions": inserted,
        "snapshot": snapshot,
    }
    logger.info(
        "dataset=%s run_id=%s status=%s rows=%s versions=%s",
        manifest.dataset,
        run_id,
        result["status"],
        len(rows),
        inserted,
    )
    return result


def run(
    input_path: Path,
    manifest_path: Path,
    root: Path,
    *,
    dsn: str | None = None,
    captured_at: datetime | None = None,
    start: str | None = None,
    end: str | None = None,
) -> dict:
    manifest = load_manifest(manifest_path)
    if manifest.format == "xls":
        selection(start, end)
    elif start is not None or end is not None:
        raise ValueError("--start/--end selection applies to the XLS contract only")
    with input_path.open("rb") as file:
        payload = file.read(MAX_INPUT_BYTES + 1)
    if len(payload) > MAX_INPUT_BYTES:
        raise ValueError("input exceeds 20 MiB limit")
    root = Path(root)
    with writer_lock(root):
        envelope, directory = archive(
            root,
            payload,
            manifest,
            input_path,
            captured_at or datetime.now(UTC),
            date_selection={"start": start, "end": end} if start else None,
        )
        return promote_capture(root, envelope, payload, manifest, directory, dsn)


def export(root: Path, *, dsn: str | None = None) -> str:
    with writer_lock(root), Warehouse(root, dsn) as warehouse:
        return publish(root, warehouse)
