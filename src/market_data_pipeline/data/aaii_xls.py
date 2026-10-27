"""AAII's inspected SENTIMENT worksheet; pure cell normalization below the XLS reader.

https://xlrd.readthedocs.io/en/latest/api.html
"""

import io
from datetime import date
from decimal import Decimal

from market_data_pipeline.data.aaii import Sentiment, _share

PARSER_VERSION = "aaii-xls-v1"


def selection(start: str | None, end: str | None) -> tuple[date, date]:
    if start is None or end is None:
        raise ValueError("XLS imports require explicit --start and --end dates")
    try:
        bounds = (date.fromisoformat(start), date.fromisoformat(end))
    except (ValueError, TypeError) as exc:
        raise ValueError("selection dates must be ISO YYYY-MM-DD") from exc
    if not 0 <= (bounds[1] - bounds[0]).days <= 90:
        raise ValueError("selection must be ordered and span no more than 90 days")
    return bounds


def normalize_rows(header, rows, manifest, captured_date, bounds) -> list[Sentiment]:
    expected = [manifest.columns[k] for k in ("survey_date", "bullish", "neutral", "bearish")]
    if header != expected:
        raise ValueError("XLS header does not match the verified column contract")
    output = []
    seen = set()
    for number, row in enumerate(rows, start=manifest.header_row + 1):
        label, *values = row
        if label == "Observations over life of survey":
            break
        if label is None and all(v is None for v in values):
            continue
        if not isinstance(label, date):
            raise ValueError(f"XLS row {number}: expected an Excel date cell")
        if not bounds[0] <= label <= bounds[1]:
            continue
        if label > captured_date or label in seen:
            raise ValueError(f"XLS row {number}: future or duplicate reported date")
        if any(type(value) not in (int, float) for value in values):
            raise ValueError(f"XLS row {number}: missing or nonnumeric shares")
        shares = [_share(str(v), "fraction") for v in values]
        if abs(sum(shares) - 1) > Decimal(str(manifest.sum_tolerance)):
            raise ValueError(f"XLS row {number}: shares do not sum to one")
        seen.add(label)
        output.append(Sentiment(label.isoformat(), *(float(v) for v in shares)))
    if not output:
        raise ValueError("no AAII observations in the requested reported-date window")
    return sorted(output, key=lambda row: row.survey_date)


def normalize_xls(payload, manifest, captured_date, bounds) -> list[Sentiment]:
    import xlrd

    try:
        book = xlrd.open_workbook(file_contents=payload, on_demand=True, logfile=io.StringIO())
    except xlrd.XLRDError as exc:
        raise ValueError("invalid AAII XLS workbook") from exc
    try:
        if manifest.sheet not in book.sheet_names():
            raise ValueError("missing AAII SENTIMENT worksheet")
        sheet = book.sheet_by_name(manifest.sheet)
        if sheet.cell_value(manifest.header_row - 2, 0) != "Reported":
            raise ValueError("XLS date label no longer matches the verified Reported Date contract")
        header = sheet.row_values(manifest.header_row - 1, 0, 4)

        def rows():
            for index in range(manifest.header_row, sheet.nrows):
                values = []
                for cell in sheet.row(index)[:4]:
                    if cell.ctype == xlrd.XL_CELL_DATE:
                        value = xlrd.xldate_as_datetime(cell.value, book.datemode).date()
                    elif cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                        value = None
                    elif cell.ctype == xlrd.XL_CELL_NUMBER:
                        value = cell.value
                    elif cell.ctype == xlrd.XL_CELL_TEXT:
                        value = cell.value
                    else:
                        # Historical error cells outside the selected window are retained
                        # in Bronze; selected error cells fail numeric-share validation.
                        value = f"unsupported Excel cell type {cell.ctype}"
                    values.append(value)
                yield values

        return normalize_rows(header, rows(), manifest, captured_date, bounds)
    finally:
        book.release_resources()
