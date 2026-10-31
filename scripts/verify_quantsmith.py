"""Resolve and verify the configured local QuantSmith guidance without modifying it."""

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path, PurePosixPath


def git(root: Path, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError("cannot inspect the local QuantSmith Git checkout") from exc


def verify(reference: Path, path: Path | None = None) -> dict:
    config = json.loads(reference.read_text())
    required = {
        "schema_version",
        "name",
        "mode",
        "default_path",
        "path_env",
        "revision",
        "git_tree",
        "guidance_sha256",
    }
    if (
        not isinstance(config, dict)
        or set(config) != required
        or type(config["schema_version"]) is not int
        or config["schema_version"] != 1
        or config["name"] != "QuantSmith"
        or config["mode"] != "local_reference"
    ):
        raise ValueError("unsupported QuantSmith reference schema")
    for key in ("revision", "git_tree"):
        if not isinstance(config[key], str) or not re.fullmatch(r"[0-9a-f]{40}", config[key]):
            raise ValueError(f"invalid QuantSmith {key}")
    if not isinstance(config["path_env"], str) or not re.fullmatch(
        r"[A-Z][A-Z0-9_]+", config["path_env"]
    ):
        raise ValueError("invalid QuantSmith path environment-variable name")
    if not isinstance(config["default_path"], str) or not config["default_path"].strip():
        raise ValueError("QuantSmith default_path must be nonempty")
    location = (
        str(path)
        if path is not None
        else os.environ.get(config["path_env"], config["default_path"])
    )
    if not location.strip():
        raise ValueError("QuantSmith path override must be nonempty")
    root = Path(location).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"QuantSmith is unavailable; set {config['path_env']} or use --path")
    if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise ValueError("QuantSmith path must be the Git checkout root")
    revision = git(root, "rev-parse", "HEAD")
    if (
        revision != config["revision"]
        or git(root, "rev-parse", "HEAD^{tree}") != config["git_tree"]
    ):
        raise ValueError("QuantSmith revision/tree differs from pin; review before repinning")
    guidance = config["guidance_sha256"]
    if not isinstance(guidance, dict) or not guidance:
        raise ValueError("QuantSmith guidance inventory must not be empty")
    for relative, digest in guidance.items():
        name = PurePosixPath(relative)
        if (
            name.is_absolute()
            or ".." in name.parts
            or not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            raise ValueError("invalid QuantSmith guidance inventory entry")
        file = root / name
        if not file.resolve().is_relative_to(root) or not file.is_file():
            raise ValueError(f"QuantSmith guidance file unavailable: {relative}")
        if hashlib.sha256(file.read_bytes()).hexdigest() != digest:
            raise ValueError(f"QuantSmith guidance differs from pin: {relative}")
    if git(root, "rev-parse", "HEAD") != revision:
        raise ValueError("QuantSmith revision changed during verification; retry")
    return {
        "library": config["name"],
        "mode": config["mode"],
        "path": str(root),
        "revision": revision,
        "git_tree": config["git_tree"],
        "guidance_files": len(guidance),
        "other_worktree_changes": bool(git(root, "status", "--porcelain=v1")),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, help="override environment and configured path")
    parser.add_argument(
        "--reference",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "agents/quantsmith.reference.json",
    )
    args = parser.parse_args(argv)
    try:
        print(json.dumps(verify(args.reference, args.path), indent=2))
        return 0
    except (ValueError, OSError) as exc:
        print(f"QuantSmith reference not verified: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
