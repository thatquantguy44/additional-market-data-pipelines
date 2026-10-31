from datetime import date
from pathlib import Path

import pytest

from market_data_pipeline.aaii.data.csv import normalize
from market_data_pipeline.aaii.manifest import load_manifest, manifest_from_dict

MANIFEST = Path("manifests/aaii-investor-sentiment.yml")
FIXTURE = Path("tests/fixtures/aaii/sentiment.csv")


def test_normalizes_explicit_percent_units_without_inventing_publication_time():
    rows = normalize(FIXTURE.read_bytes(), load_manifest(MANIFEST), date(2026, 10, 26))
    assert rows[0].survey_date == "2026-10-07"
    assert rows[0].bullish == 0.4
    assert rows[0].provider_published_at is None
    assert (
        rows[0].content_hash
        == normalize(FIXTURE.read_bytes(), load_manifest(MANIFEST), date(2026, 10, 26))[
            0
        ].content_hash
    )


@pytest.mark.parametrize(
    "row",
    [
        "10/21/2026,NaN,18,46",
        "10/21/2026,,18,46",
        "10/21/2026,360,18,46",
        "10/21/2026,30,18,46",
        "10/21/2026,-1,55,46",
        "10/21/26,36,18,46",
        "10/28/2026,36,18,46",
        "10/21/2026,Infinity,18,46",
    ],
)
def test_invalid_values_fail_closed(row):
    payload = f"Date,Bullish,Neutral,Bearish\n{row}\n".encode()
    with pytest.raises(ValueError):
        normalize(payload, load_manifest(MANIFEST), date(2026, 10, 26))


def test_duplicate_dates_and_schema_drift_fail():
    payload = FIXTURE.read_bytes()
    for invalid in [
        payload + payload.splitlines()[1] + b"\n",
        b"Date,Bullish\n",
        b"<html>Login</html>",
    ]:
        with pytest.raises(ValueError):
            normalize(invalid, load_manifest(MANIFEST), date(2026, 10, 26))


def test_manifest_rejects_unknown_fields_before_any_pipeline_io(tmp_path):
    path = tmp_path / "invalid.yml"
    path.write_text(MANIFEST.read_text() + "unexpected: true\n")
    with pytest.raises(ValueError, match="fields"):
        load_manifest(path)


@pytest.mark.parametrize(
    "field,value",
    [
        ("units", []),
        ("date_format", {}),
        ("sum_tolerance", float("nan")),
        ("sum_tolerance", True),
        ("columns", {"bullish": []}),
    ],
)
def test_manifest_rejects_malformed_field_types(field, value):
    manifest = load_manifest(MANIFEST).to_dict()
    manifest[field] = value
    with pytest.raises(ValueError):
        manifest_from_dict(manifest)


def test_fraction_units_and_rounding_tolerance_are_explicit():
    raw = load_manifest(MANIFEST).to_dict()
    raw["units"] = "fraction"
    manifest = manifest_from_dict(raw)
    payload = b"Date,Bullish,Neutral,Bearish\n10/21/2026,0.403,0.208,0.390\n"
    assert normalize(payload, manifest, date(2026, 10, 26))[0].bullish == 0.403
    with pytest.raises(ValueError, match="suffix"):
        normalize(payload.replace(b"0.403", b"40.3%"), manifest, date(2026, 10, 26))
