import json
import shutil
from pathlib import Path

from market_data_pipeline.aaii.io.bronze import load_archive
from market_data_pipeline.aaii.io.warehouse import Warehouse
from market_data_pipeline.aaii.manifest import manifest_from_dict
from market_data_pipeline.aaii.pipeline import promote_capture
from market_data_pipeline.shared.files import writer_lock


def replay(source: Path, destination: Path, *, dsn: str | None = None) -> dict:
    """Rebuild from original captures, preserving run identities and availability."""
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or destination.is_relative_to(source):
        raise ValueError("replay requires a separate empty destination")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("replay requires an empty destination")
    captures = []
    for metadata in (source / "bronze/aaii-investor-sentiment").glob("*/metadata.json"):
        envelope, payload = load_archive(metadata.parent)
        manifest = manifest_from_dict(envelope["manifest"])
        receipt_path = metadata.parent / "promotion.json"
        if not receipt_path.exists():
            raise ValueError("unresolved Bronze promotion; reconcile with warehouse before replay")
        receipt = json.loads(receipt_path.read_text())
        if type(receipt.get("accepted")) is not bool:
            raise ValueError("invalid promotion receipt")
        captures.append((envelope, payload, manifest, metadata.parent, receipt))
    if not captures:
        raise ValueError("no Bronze captures found")
    captures.sort(key=lambda capture: (capture[0]["retrieved_at"], capture[0]["run_id"]))
    succeeded, rejected, partial = 0, [], []
    with writer_lock(destination):
        with Warehouse(destination, dsn) as warehouse:
            if warehouse.runs() or warehouse.versions():
                raise ValueError("replay requires an empty warehouse")
        for envelope, payload, manifest, path, receipt in captures:
            directory = destination / "bronze" / manifest.dataset / envelope["run_id"]
            shutil.copytree(path, directory)
            if not receipt["accepted"]:
                with Warehouse(destination, dsn) as warehouse:
                    warehouse.record_run(envelope, str(directory))
                    warehouse.status(envelope["run_id"], "failed", message=receipt["reason"])
                rejected.append(envelope["run_id"])
                continue
            try:
                outcome = promote_capture(destination, envelope, payload, manifest, directory, dsn)
                if outcome["status"] == "partial":
                    partial.append(envelope["run_id"])
                else:
                    succeeded += 1
            except ValueError:
                rejected.append(envelope["run_id"])
    return {"succeeded": succeeded, "rejected": rejected, "partial": partial}
