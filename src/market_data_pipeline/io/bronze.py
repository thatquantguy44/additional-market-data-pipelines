import hashlib
import json
import os
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from market_data_pipeline.data.aaii import PARSER_VERSION


def utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("capture timestamp requires a timezone")
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def atomic_json(path: Path, value):
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x") as file:
            json.dump(value, file, indent=2, sort_keys=True)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def writer_lock(root: Path):
    """POSIX filesystem lock; all publishers must use the same persistent root."""
    import fcntl

    root.mkdir(parents=True, exist_ok=True)
    with (root / ".writer.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


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
    if envelope["parser_version"] != ("aaii-xls-v1" if suffix == "xls" else PARSER_VERSION):
        raise ValueError("unsupported archived parser version")
    if not isinstance(envelope["run_id"], str) or not (
        len(envelope["run_id"]) == 32 and all(c in "0123456789abcdef" for c in envelope["run_id"])
    ):
        raise ValueError("invalid archived run ID")
    captured = datetime.fromisoformat(envelope["retrieved_at"].replace("Z", "+00:00"))
    if utc_timestamp(captured) != envelope["retrieved_at"]:
        raise ValueError("archived capture time must be canonical UTC")
    return envelope, payload
