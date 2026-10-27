import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from market_data_pipeline.catalogs.manifest import load_manifest
from market_data_pipeline.config import load_config, resolve_runtime
from market_data_pipeline.io.bronze import utc_timestamp
from market_data_pipeline.io.warehouse import Warehouse
from market_data_pipeline.pipeline import export, run
from market_data_pipeline.replay import replay


def warehouse_dsn(backend: str) -> str | None:
    return resolve_runtime(warehouse=backend)[2]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="AAII authorized-local-export medallion pipeline")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate the manifest without writes")
    validate.add_argument(
        "--manifest", type=Path, default=Path("manifests/aaii-investor-sentiment.yml")
    )
    for command in ("run", "export", "gold", "replay"):
        sub = commands.add_parser(command)
        sub.add_argument("--root", type=Path)
        sub.add_argument("--warehouse", choices=("sqlite", "postgres"))
        sub.add_argument("--config", type=Path, help="runtime YAML; CLI root/backend override it")
        if command == "run":
            inputs = sub.add_mutually_exclusive_group(required=True)
            inputs.add_argument("--input", type=Path)
            inputs.add_argument(
                "--live", action="store_true", help="one bounded official XLS fetch"
            )
            sub.add_argument("--start")
            sub.add_argument("--end")
            sub.add_argument(
                "--manifest", type=Path, default=Path("manifests/aaii-investor-sentiment.yml")
            )
        if command == "gold":
            sub.add_argument(
                "--as-of", help="timezone-aware timestamp; observed availability cutoff"
            )
        if command == "replay":
            sub.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        if args.command == "validate":
            result = load_manifest(args.manifest).to_dict()
        else:
            root, backend, dsn = resolve_runtime(
                config=load_config(args.config) if args.config else None,
                root=args.root,
                warehouse=args.warehouse,
            )
            if args.command == "run":
                if args.live:
                    from market_data_pipeline.sources.aaii import run_live

                    result = run_live(args.manifest, root, start=args.start, end=args.end, dsn=dsn)
                else:
                    result = run(
                        args.input, args.manifest, root, dsn=dsn, start=args.start, end=args.end
                    )
            elif args.command == "replay":
                result = replay(args.source_root, root, dsn=dsn)
            else:
                if not dsn and not (root / "warehouse.sqlite3").exists():
                    raise ValueError("warehouse does not exist; run an import first")
                if args.command == "export":
                    result = {"snapshot": export(root, dsn=dsn)}
                else:
                    cutoff = (
                        utc_timestamp(datetime.fromisoformat(args.as_of.replace("Z", "+00:00")))
                        if args.as_of
                        else None
                    )
                    with Warehouse(root, dsn) as warehouse:
                        result = warehouse.gold(cutoff)
        print(json.dumps(result, indent=2))
        if args.command == "replay" and result["rejected"]:
            return 1
        return 0
    except Exception as exc:
        # Driver errors may include connection details. Do not print their text.
        message = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        print(f"error: {message}", file=sys.stderr)
        return 1
