"""Generate invented XLS fixtures; optional one-off tool: xlwt==1.3.0.

Run with the isolated fixture-tool Python. xlwt is not a runtime dependency.
"""

from datetime import datetime
from pathlib import Path

import xlwt

root = Path(__file__).resolve().parents[1] / "tests/fixtures/aaii"
for name, change in [("synthetic.xls", False), ("synthetic-correction.xls", True)]:
    book = xlwt.Workbook()
    sheet = book.add_sheet("SENTIMENT")
    sheet.write(2, 0, "Reported")
    for column, value in enumerate(["Date", "Bullish", "Neutral", "Bearish"]):
        sheet.write(3, column, value)
    values = [
        ("1987-06-26", None, None, None),
        ("2010-01-07", 0.3, 0.2, 0.5),
        ("2010-01-14", None, 0.2, 0.8),
        ("2026-10-01", 0.35, 0.2, 0.45),
        ("2026-10-08", 0.45 if change else 0.4, 0.2, 0.35 if change else 0.4),
        ("2026-10-22", 0.37, 0.17, 0.46),
    ]
    style = xlwt.easyxf(num_format_str="M/D/YYYY")
    for row, (label, *shares) in enumerate(values, start=5):
        sheet.write(row, 0, datetime.fromisoformat(label), style)
        for column, share in enumerate(shares, start=1):
            if share is not None:
                sheet.write(row, column, share)
    sheet.write(12, 0, "Observations over life of survey")
    sheet.write(13, 0, "Avg")
    book.save(str(root / name))
