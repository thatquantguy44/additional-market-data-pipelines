import json
import subprocess
import sys


def cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "market_data_pipeline", *map(str, args)],
        capture_output=True,
        text=True,
    )


def test_backfill_backup_restore_check_and_retention_cli(tmp_path):
    root = tmp_path / "history"
    result = cli(
        "backfill",
        "--input",
        "tests/fixtures/aaii/synthetic.xls",
        "--root",
        root,
        "--start",
        "1987-01-01",
        "--end",
        "2026-10-26",
        "--quarantine-invalid",
    )
    assert result.returncode == 2, result.stderr
    assert json.loads(result.stdout)["quarantined_rows"] == 2
    assert cli("check", "--root", root).returncode == 1
    package = tmp_path / "backup"
    result = cli("backup", "--root", root, "--destination", package)
    assert result.returncode == 0, result.stderr
    restored = tmp_path / "restored"
    result = cli("restore", "--root", restored, "--backup", package)
    assert result.returncode == 0, result.stderr
    result = cli("gold", "--root", restored)
    assert len(json.loads(result.stdout)) == 4
    result = cli("retain", "--root", restored, "--keep", "1")
    assert result.returncode == 0 and not json.loads(result.stdout)["applied"]
