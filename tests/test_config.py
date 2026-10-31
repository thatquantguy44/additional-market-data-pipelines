from pathlib import Path

import pytest
import yaml

from market_data_pipeline.aaii.config import load_config, resolve_runtime


def write_config(tmp_path, **updates):
    value = yaml.safe_load(Path("config/postgres.example.yml").read_text())
    value["postgres"].update(updates)
    path = tmp_path / "runtime.yml"
    path.write_text(yaml.safe_dump(value))
    return path


def test_config_resolves_relative_root_and_escapes_secret(tmp_path, monkeypatch):
    from psycopg.conninfo import conninfo_to_dict

    path = write_config(tmp_path, database="custom_db", port=55488, role="aaii_writer")
    monkeypatch.setenv("AAII_POSTGRES_PASSWORD", "quote' slash\\ space")
    monkeypatch.setenv("MARKET_DATA_POSTGRES_DSN", "postgresql://must-not-win.invalid/old")
    config = load_config(path)
    root, backend, dsn = resolve_runtime(config=config)
    assert root == (tmp_path / "../data/aaii-postgres").resolve()
    assert backend == "postgres"
    params = conninfo_to_dict(dsn)
    assert params["dbname"] == "custom_db"
    assert params["port"] == "55488"
    assert params["password"] == "quote' slash\\ space"
    assert "role=aaii_writer" in params["options"]
    assert "quote" not in repr(config)


@pytest.mark.parametrize(
    "updates",
    [
        {"port": 0},
        {"port": True},
        {"port": 65536},
        {"port": "5432"},
        {"role": "bad;DROP TABLE t"},
        {"schema": "public -c role=admin"},
        {"password": "must-not-be-in-config"},
        {"unknown": 1},
        {"sslmode": "whatever"},
        {"connect_timeout": -1},
        {"password_env": "invalid name"},
    ],
)
def test_bad_settings_fail_before_any_connection(tmp_path, updates):
    with pytest.raises(ValueError):
        load_config(write_config(tmp_path, **updates))


def test_cli_overrides_config_without_requiring_unused_secret(tmp_path):
    config = load_config(write_config(tmp_path))
    root, backend, dsn = resolve_runtime(
        config=config, root=tmp_path / "override", warehouse="sqlite"
    )
    assert (root, backend, dsn) == (tmp_path / "override", "sqlite", None)


def test_secret_missing_is_explicit_and_legacy_dsn_still_supported(tmp_path, monkeypatch):
    monkeypatch.delenv("AAII_POSTGRES_PASSWORD", raising=False)
    with pytest.raises(ValueError, match="AAII_POSTGRES_PASSWORD"):
        resolve_runtime(config=load_config(write_config(tmp_path)))
    monkeypatch.setenv("MARKET_DATA_POSTGRES_DSN", "postgresql://localhost/test")
    assert resolve_runtime(warehouse="postgres")[2] == "postgresql://localhost/test"
