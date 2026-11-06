"""Readable HTML shared by saved analysis results and previews."""

from html import escape
from math import isfinite


def result_number(value, digits=6):
    return format(value, f".{digits}g") if value is not None and isfinite(value) else "—"


def report_table(headers, rows, *, numeric=()):
    """Keep numeric columns aligned and preserve text safely in exported HTML."""
    head = "".join(f'<th bgcolor="#e8eef7" align="left">{escape(str(label))}</th>' for label in headers)
    body = []
    for index, row in enumerate(rows):
        color = "#ffffff" if index % 2 == 0 else "#f2f5fa"
        cells = []
        for column, value in enumerate(row):
            align = "right" if column in numeric else "left"
            cells.append(f'<td bgcolor="{color}" align="{align}">{escape(str(value))}</td>')
        body.append("<tr>" + "".join(cells) + "</tr>")
    return '<table width="99%" cellspacing="0" cellpadding="6"><tr>' + head + "</tr>" + "".join(body) + "</table>"


def report_document(title, *, source="", summary=(), sections=()):
    context = f"<p><strong>Source</strong> · {escape(source)}</p>" if source else ""
    overview = report_table(("Result", "Value"), summary, numeric=(1,)) if summary else ""
    details = "".join(f"<h3>{escape(heading)}</h3>{body}" for heading, body in sections)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f"<title>{escape(title)}</title></head>"
        '<body style="background-color:#ffffff;color:#17243b;font-family:Segoe UI,Arial,sans-serif;">'
        f"<h2>{escape(title)}</h2>{context}{overview}{details}</body></html>"
    )
