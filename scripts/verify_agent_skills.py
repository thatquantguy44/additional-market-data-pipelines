"""Verify the vendored workflow snapshot without Git or network access."""

import hashlib
import json
from pathlib import Path


def snapshot_digest(root: Path) -> tuple[str, int]:
    entries = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError(f"snapshot symlink escapes the library: {relative}")
            entries.append([relative, "symlink", path.readlink().as_posix()])
        elif path.is_file():
            if path.name == ".git":
                raise ValueError("snapshot must not contain Git metadata")
            entries.append(
                [
                    relative,
                    "executable" if path.stat().st_mode & 0o111 else "file",
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                ]
            )
    digest = hashlib.sha256(json.dumps(entries, separators=(",", ":")).encode()).hexdigest()
    return digest, len(entries)


def main() -> int:
    repository = Path(__file__).resolve().parent.parent
    pin = json.loads((repository / "agents/agent-skills.lock.json").read_text())
    root = repository / "agents/agent-skills"
    digest, count = snapshot_digest(root)
    if digest != pin["snapshot_sha256"] or count != pin["file_count"]:
        print(f"agent-skills snapshot differs from pinned revision {pin['revision']}")
        return 1
    print(f"agent-skills verified: {pin['revision']} ({count} files/symlinks; no network required)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
