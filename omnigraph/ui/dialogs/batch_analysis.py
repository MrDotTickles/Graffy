"""Run a fit or peak search on worksheets with matching columns."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QProgressDialog

from omnigraph.analysis.reporting import report_document, report_table
from omnigraph.core.column_matching import column_signature, match_column, numeric_pairs
from omnigraph.core.project import ReportModel
from omnigraph.ui.dialogs.item_selection import choose_items


def run_batch(dialog, title, source_key, x_index, y_index, analyze, summarize, headers, settings, min_points):
    project = dialog.project
    source = project.get_worksheet(*source_key) if source_key else None
    x_col = source.get_column(x_index) if source else None
    y_col = source.get_column(y_index) if source else None
    if x_col is None or y_col is None or x_col is y_col:
        QMessageBox.warning(dialog, title, "Choose separate X and Y columns on the example worksheet.")
        return
    x_spec, y_spec = column_signature(x_col), column_signature(y_col)
    sheets = [(workbook.name, sheet) for workbook in project.workbooks
              for sheet in workbook.sheets if sheet.column_count() >= 2]
    labels = [f"{workbook} / {sheet.name}" for workbook, sheet in sheets]
    selected = choose_items(
        dialog, title,
        f"Select worksheets to analyze using {x_col.display_label} and {y_col.display_label}. "
        "Graffy matches column names, units, and roles and creates one comparison report.",
        "Run analysis", labels, [index for index, (_, sheet) in enumerate(sheets) if sheet is source],
    )
    if not selected:
        return
    progress = QProgressDialog("Analyzing worksheets…", "Cancel", 0, len(selected), dialog)
    progress.setWindowModality(Qt.WindowModality.WindowModal)
    progress.setMinimumDuration(0)
    rows = []
    skipped = []
    try:
        for step, index in enumerate(selected):
            workbook, sheet = sheets[index]
            progress.setLabelText(f"Analyzing {labels[index]}…")
            progress.setValue(step)
            if progress.wasCanceled():
                return
            x, y = (x_index, y_index) if sheet is source else (
                match_column(sheet, x_spec), match_column(sheet, y_spec),
            )
            if x is None or y is None:
                skipped.append((labels[index], "Missing or ambiguous column match"))
                continue
            xs, ys = numeric_pairs(sheet, x, y)
            if len(xs) < min_points:
                skipped.append((labels[index], f"Fewer than {min_points} included numeric pairs"))
                continue
            try:
                rows.append((labels[index], *summarize(analyze(xs, ys))))
            except Exception as error:
                skipped.append((labels[index], str(error) or type(error).__name__))
    finally:
        progress.close()
    details = [("Results by worksheet", report_table(("Worksheet", *headers), rows))]
    if skipped:
        details.append(("Worksheets skipped", report_table(("Worksheet", "Reason"), skipped)))
    summary = [*settings, ("Worksheets completed", f"{len(rows)} of {len(selected)}")]
    report = ReportModel(
        title=title,
        report_type="batch_analysis",
        html_content=report_document(title, source=f"{x_col.display_label} → {y_col.display_label}",
                                     summary=summary, sections=details),
    )
    project.reports.append(report)
    dialog.accept()
