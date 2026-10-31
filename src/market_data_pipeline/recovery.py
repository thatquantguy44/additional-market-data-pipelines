"""Portable backups of pipeline-owned state, never database-global roles or secrets."""

import hashlib
import json
import re
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

from market_data_pipeline.io.bronze import atomic_json, utc_timestamp, writer_lock
from market_data_pipeline.io.parquet import current_snapshot, publish
from market_data_pipeline.io.warehouse import GOLD_COLUMNS, RUN_COLUMNS, SILVER_COLUMNS, Warehouse


def _inventory(root):
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("backup must not contain symlinks")
        if path.is_file() and path != root / "backup.json":
            files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def verify_backup(package: Path) -> dict:
    metadata = json.loads((package / "backup.json").read_text())
    if metadata.get("format") != "market-medallion-owned-state-v1":
        raise ValueError("unsupported backup format")
    actual = _inventory(package)
    if actual != metadata.get("files"):
        raise ValueError("backup digest/inventory mismatch")
    return metadata


def backup(root: Path, destination: Path, *, dsn=None) -> dict:
    root, destination = Path(root).resolve(), Path(destination).resolve()
    if destination.exists() or destination.is_relative_to(root) or root.is_relative_to(destination):
        raise ValueError("backup requires a new directory separate from the data root")
    if not (root / ".warehouse.json").exists():
        raise ValueError("warehouse does not exist")
    with writer_lock(root), Warehouse(root, dsn) as warehouse:
        destination.mkdir(parents=True, mode=0o700)
        with warehouse.transaction():
            state = {
                "versions": warehouse.versions(),
                "gold": warehouse.gold(),
                "runs": warehouse.runs(),
                "contracts": [
                    dict(row)
                    for row in warehouse.execute(
                        "SELECT * FROM pipeline_dataset_contract"
                    ).fetchall()
                ],
                "warehouse_id": dict(
                    warehouse.execute("SELECT id FROM pipeline_identity").fetchone()
                )["id"],
            }
            if (root / "bronze").exists():
                shutil.copytree(root / "bronze", destination / "bronze", symlinks=True)
            if (root / "parquet/current.json").exists():
                shutil.copytree(current_snapshot(root), destination / "snapshot", symlinks=True)
            atomic_json(destination / "warehouse.json", state)
        files = _inventory(destination)
        atomic_json(
            destination / "backup.json",
            {
                "format": "market-medallion-owned-state-v1",
                "created_at": utc_timestamp(datetime.now(UTC)),
                "files": files,
                "silver_versions": len(state["versions"]),
                "gold_rows": len(state["gold"]),
            },
        )
    verify_backup(destination)
    return {
        "backup": str(destination),
        "files": len(files),
        "silver_versions": len(state["versions"]),
    }


def restore(package: Path, destination: Path, *, dsn=None) -> dict:
    package, destination = Path(package).resolve(), Path(destination).resolve()
    metadata = verify_backup(package)
    if (
        destination == package
        or destination.is_relative_to(package)
        or package.is_relative_to(destination)
    ):
        raise ValueError("restore requires a separate empty destination")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("restore requires an empty destination")
    state = json.loads((package / "warehouse.json").read_text())
    for row in state["runs"]:
        if row["dataset"] != "aaii-investor-sentiment" or not re.fullmatch(
            r"[0-9a-f]{32}", row["run_id"]
        ):
            raise ValueError("invalid backup run identity")
    with writer_lock(destination), Warehouse(destination, dsn) as warehouse:
        if warehouse.versions() or warehouse.runs():
            raise ValueError("restore requires an empty warehouse")
        if (package / "bronze").exists():
            shutil.copytree(package / "bronze", destination / "bronze")
        with warehouse.transaction():
            warehouse.execute("DELETE FROM pipeline_dataset_contract")

            for contract in state["contracts"]:
                warehouse.execute(
                    "INSERT INTO pipeline_dataset_contract (dataset,date_basis) VALUES (?,?)",
                    (contract["dataset"], contract["date_basis"]),
                )
            for row in state["versions"]:
                warehouse._insert(
                    "aaii_silver_versions", SILVER_COLUMNS, tuple(row[k] for k in SILVER_COLUMNS)
                )
            for row in state["runs"]:
                restored = {
                    **row,
                    "bronze_path": str(destination / "bronze" / row["dataset"] / row["run_id"]),
                }
                warehouse._insert(
                    "pipeline_runs", RUN_COLUMNS, tuple(restored[k] for k in RUN_COLUMNS)
                )
            gold = warehouse.gold()
            if gold != state["gold"] or len(warehouse.versions()) != metadata["silver_versions"]:
                raise ValueError("restored state does not match backed-up Silver/Gold")
            for row in gold:
                warehouse._insert(
                    "aaii_gold_latest", GOLD_COLUMNS, tuple(row[k] for k in GOLD_COLUMNS)
                )
        marker = json.loads((destination / ".warehouse.json").read_text())
        log = destination / "operations"
        log.mkdir(exist_ok=True)
        atomic_json(
            log / "restore.json",
            {
                "source_warehouse_id": state["warehouse_id"],
                "destination_warehouse_id": marker["warehouse_id"],
                "at": utc_timestamp(datetime.now(UTC)),
            },
        )
        snapshot = publish(destination, warehouse)
    return {
        "restored": str(destination),
        "silver_versions": metadata["silver_versions"],
        "snapshot": snapshot,
    }


def retain_snapshots(root: Path, *, keep=5, apply=False) -> dict:
    if type(keep) is not int or keep < 1:
        raise ValueError("keep must be a positive integer")
    with writer_lock(root):
        current = current_snapshot(root)
        parent = (root / "parquet/snapshots").resolve()
        candidates = [
            p
            for p in parent.iterdir()
            if p.is_dir() and not p.is_symlink() and re.fullmatch(r"[0-9a-f]{32}", p.name)
        ]
        candidates.sort(key=lambda p: (p.stat().st_mtime_ns, p.name), reverse=True)
        retained = {current}
        retained.update(p for p in [p for p in candidates if p != current][: keep - 1])
        remove = [p for p in candidates if p not in retained]
        if apply:
            for path in remove:
                if path.resolve() == current or not path.resolve().is_relative_to(parent):
                    raise ValueError("unsafe retention path")
                shutil.rmtree(path)
            log = root / "operations/retention"
            log.mkdir(parents=True, exist_ok=True)
            atomic_json(
                log / f"{uuid.uuid4().hex}.json",
                {
                    "removed": [p.name for p in remove],
                    "current": current.name,
                    "keep": keep,
                    "at": utc_timestamp(datetime.now(UTC)),
                },
            )
    return {"applied": apply, "current": str(current), "remove": [str(p) for p in remove]}
