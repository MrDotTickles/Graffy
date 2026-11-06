"""Read, copy, and export saved analysis results."""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTextBrowser, QToolBar, QLabel,
    QFileDialog, QMessageBox, QApplication,
)

from omnigraph.core.project import ReportModel
from omnigraph.ui.styles.design import icon


class ReportViewWidget(QWidget):
    """Analysis results stay selectable and retain their saved source and settings."""

    def __init__(self, report_model: ReportModel, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        toolbar = QToolBar("Report actions", self)
        toolbar.setObjectName("ReportActions")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toolbar.addAction(icon("copy"), "Copy report", self._copy_text)
        toolbar.addAction(icon("export"), "Save HTML…", self._export_html)
        layout.addWidget(toolbar)

        self.browser = QTextBrowser(self)
        self.browser.setObjectName("AnalysisReport")
        self.browser.setOpenLinks(False)
        self.browser.document().setDocumentMargin(14)
        layout.addWidget(self.browser, 1)
        self.feedback = QLabel()
        self.feedback.setProperty("role", "muted")
        self.feedback.setWordWrap(True)
        self.feedback.hide()
        layout.addWidget(self.feedback)

        self.set_report(report_model)

    def set_report(self, report_model: ReportModel):
        self.report_model = report_model
        self.browser.setHtml(report_model.html_content)
        self.feedback.hide()

    def _copy_text(self):
        QApplication.clipboard().setText(self.browser.toPlainText())
        self.feedback.setText("Report text copied.")
        self.feedback.show()

    def _export_html(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save analysis report", f"{self.report_model.title}.html", "HTML Files (*.html)",
        )
        if not path:
            return
        try:
            Path(path).write_text(self.report_model.html_content, encoding="utf-8")
        except OSError as error:
            QMessageBox.critical(self, "Could not save report", str(error))
            return
        self.feedback.setText(f"Report saved as {Path(path).name}.")
        self.feedback.show()

    def set_zoom(self, zoom: float):
        app = QApplication.instance()
        if app:
            base = getattr(app, "_graffy_base_ui_font", app.font())
            font = QFont(base)
            font.setPointSizeF(max(6, base.pointSizeF() * zoom))
            self.browser.setFont(font)
            self.browser.document().setDefaultFont(font)
