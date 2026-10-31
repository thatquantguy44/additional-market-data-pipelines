import hashlib
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from market_data_pipeline.pipelines.aaii.data.csv import PARSER_VERSION
from market_data_pipeline.shared.files import atomic_json, utc_timestamp


def archive(
    root, payload, manifest, source_path, captured_at, *, transport=None, date_selection=None
) -> tuple[dict, Path]:
    envelope = {
        "run_id": uuid.uuid4().hex,
        "retrieved_at": utc_timestamp(captured_at),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "parser_version": "aaii-xls-v1" if manifest.format == "xls" else PARSER_VERSION,
        "manifest": manifest.to_dict(),
        "source_uri": source_path.resolve().as_uri() if source_path else None,
        "transport": "local-file",
        "http_status": None,
        "http_headers": {},
    }
    if transport:
        envelope.update(transport)
    if date_selection:
        envelope["selection"] = date_selection
        if date_selection.get("mode") == "backfill":
            envelope["parser_version"] = "aaii-xls-v2"
    directory = root / "bronze" / manifest.dataset / envelope["run_id"]
    directory.mkdir(parents=True)
    with (directory / f"payload.{manifest.format}").open("xb") as file:
        file.write(payload)
        file.flush()
        os.fsync(file.fileno())
    atomic_json(directory / "metadata.json", envelope)
    return envelope, directory


def load_archive(path: Path) -> tuple[dict, bytes]:
    envelope = json.loads((path / "metadata.json").read_text())
    suffix = envelope["manifest"]["format"]
    if suffix not in ("csv", "xls"):
        raise ValueError("unsupported archived format")
    payload = (path / f"payload.{suffix}").read_bytes()
    if hashlib.sha256(payload).hexdigest() != envelope["sha256"]:
        raise ValueError(f"Bronze digest mismatch: {path.name}")
    allowed = {"aaii-xls-v1", "aaii-xls-v2"} if suffix == "xls" else {PARSER_VERSION}
    if envelope["parser_version"] not in allowed:
        raise ValueError("unsupported archived parser version")
    if (
        envelope["parser_version"] == "aaii-xls-v2"
        and envelope.get("selection", {}).get("mode") != "backfill"
    ):
        raise ValueError("XLS v2 archives require explicit backfill selection")
    if not isinstance(envelope["run_id"], str) or not (
        len(envelope["run_id"]) == 32 and all(c in "0123456789abcdef" for c in envelope["run_id"])
    ):
        raise ValueError("invalid archived run ID")
    captured = datetime.fromisoformat(envelope["retrieved_at"].replace("Z", "+00:00"))
    if utc_timestamp(captured) != envelope["retrieved_at"]:
        raise ValueError("archived capture time must be canonical UTC")
    return envelope, payload
