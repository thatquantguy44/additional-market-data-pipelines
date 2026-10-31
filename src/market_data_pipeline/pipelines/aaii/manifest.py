from dataclasses import MISSING, asdict, dataclass, fields
from pathlib import Path
from typing import Any

import yaml

from market_data_pipeline.shared.yaml import UniqueLoader


@dataclass(frozen=True)
class Manifest:
    source: str
    dataset: str
    format: str
    columns: dict[str, str]
    date_format: str
    units: str
    sum_tolerance: float
    access: dict[str, str]
    date_basis: str = "survey_date"
    sheet: str | None = None
    header_row: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def manifest_from_dict(value: dict) -> Manifest:
    allowed = {field.name for field in fields(Manifest)}
    required = {field.name for field in fields(Manifest) if field.default is MISSING}
    if not isinstance(value, dict) or set(value) - allowed or required - set(value):
        raise ValueError(
            f"manifest fields must include {sorted(required)}; unknown fields rejected"
        )
    if (value["source"], value["dataset"]) != (
        "aaii",
        "aaii-investor-sentiment",
    ) or value["format"] not in ("csv", "xls"):
        raise ValueError("only the AAII CSV and official XLS contracts are implemented")
    columns = value["columns"]
    if not isinstance(columns, dict) or set(columns) != {
        "survey_date",
        "bullish",
        "neutral",
        "bearish",
    }:
        raise ValueError("columns must map survey_date, bullish, neutral, bearish")
    if any(not isinstance(v, str) or not v.strip() for v in columns.values()):
        raise ValueError("column names must be nonempty strings")
    if len(set(columns.values())) != 4:
        raise ValueError("column mappings must be unique")
    if not isinstance(value["date_format"], str) or value["date_format"] not in {
        "%m/%d/%Y",
        "%Y-%m-%d",
    }:
        raise ValueError("date_format must include a four-digit year")
    if not isinstance(value["units"], str) or value["units"] not in {"percent", "fraction"}:
        raise ValueError("units must be percent or fraction")
    tolerance = value["sum_tolerance"]
    if type(tolerance) not in (int, float) or not 0 <= tolerance <= 0.002:
        raise ValueError("sum_tolerance must be between 0 and 0.002")
    access = value["access"]
    if (
        not isinstance(access, dict)
        or set(access) != {"method", "source_url", "terms_url", "automation"}
        or any(not isinstance(v, str) or not v for v in access.values())
    ):
        raise ValueError("access requires method, source_url, terms_url, automation")
    basis = value.get("date_basis", "survey_date")
    if basis not in ("survey_date", "reported_date"):
        raise ValueError("date_basis must be survey_date or reported_date")
    if value["format"] == "xls":
        if (value.get("sheet"), value.get("header_row"), value["units"], basis) != (
            "SENTIMENT",
            4,
            "fraction",
            "reported_date",
        ):
            raise ValueError("XLS requires SENTIMENT, header_row 4, fractions and reported_date")
        if access != {
            "method": "official-xls-download",
            "source_url": "https://www.aaii.com/files/surveys/sentiment.xls",
            "terms_url": "https://www.aaii.com/privacy/tos",
            "automation": "explicit-bounded-run",
        }:
            raise ValueError("XLS access must use the verified official bounded download contract")
    elif (
        access["method"] != "authorized-local-export"
        or access["automation"] != "unverified-disabled"
    ):
        raise ValueError("CSV requires authorized-local-export access")
    return Manifest(**value)


def load_manifest(path: Path) -> Manifest:
    try:
        return manifest_from_dict(yaml.load(path.read_text(), Loader=UniqueLoader))
    except yaml.YAMLError as exc:
        raise ValueError("invalid YAML manifest") from exc
