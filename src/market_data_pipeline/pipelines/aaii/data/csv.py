import csv
import hashlib
import io
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from market_data_pipeline.pipelines.aaii.manifest import Manifest

PARSER_VERSION = "aaii-csv-v1"


@dataclass(frozen=True)
class Sentiment:
    survey_date: str
    bullish: float
    neutral: float
    bearish: float
    provider_published_at: str | None = None

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


def _share(value: str, units: str) -> Decimal:
    value = value.strip()
    if value.endswith("%"):
        if units != "percent":
            raise ValueError("percent suffix conflicts with fraction units")
        value = value[:-1]
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("missing or invalid share") from exc
    if not number.is_finite():
        raise ValueError("non-finite share")
    if units == "percent":
        number /= 100
    if not 0 <= number <= 1:
        raise ValueError("share outside [0,1]")
    return number


def normalize(payload: bytes, manifest: Manifest, captured_date: date) -> list[Sentiment]:
    """Normalize a complete local CSV; reject the whole capture on blocking DQ."""
    try:
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")), strict=True)
        if reader.fieldnames is None or set(reader.fieldnames) != set(manifest.columns.values()):
            raise ValueError("CSV header does not match manifest columns")
        if len(reader.fieldnames) != 4:
            raise ValueError("duplicate CSV header")
        result = []
        seen = set()
        for line, row in enumerate(reader, start=2):
            try:
                if None in row or any(v is None for v in row.values()):
                    raise ValueError("CSV row width does not match header")
                raw_date = row[manifest.columns["survey_date"]].strip()
                survey_date = datetime.strptime(raw_date, manifest.date_format).date()
                if survey_date > captured_date:
                    raise ValueError("survey date is after capture date")
                if survey_date in seen:
                    raise ValueError("duplicate survey date")
                seen.add(survey_date)
                shares = [
                    _share(row[manifest.columns[key]], manifest.units)
                    for key in ("bullish", "neutral", "bearish")
                ]
                if abs(sum(shares) - 1) > Decimal(str(manifest.sum_tolerance)):
                    raise ValueError("shares do not sum to one within rounding tolerance")
                result.append(Sentiment(survey_date.isoformat(), *(float(v) for v in shares)))
            except (ValueError, TypeError) as exc:
                raise ValueError(f"AAII row {line}: {exc}") from exc
        if not result:
            raise ValueError("empty AAII extract")
        return sorted(result, key=lambda row: row.survey_date)
    except (UnicodeError, csv.Error) as exc:
        raise ValueError("invalid UTF-8 CSV") from exc
