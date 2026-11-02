"""
Report viewer widget displaying rich formatted HTML fitting and statistical results.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QPushButton,
    QToolButton, QFileDialog, QMessageBox, QApplication
)
from omnigraph.core.project import ReportModel


class ReportViewWidget(QWidget):
    """Displays publication-grade analysis and fitting reports."""

    def __init__(self, report_model: ReportModel, parent=None):
        super().__init__(parent)
        self.report_model = report_model
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Top bar
        bar_layout = QHBoxLayout()
        btn_copy_text = QToolButton()
        btn_copy_text.setText("📋 Copy Report")
        btn_copy_text.clicked.connect(self._copy_text)
        bar_layout.addWidget(btn_copy_text)

        btn_export_html = QToolButton()
        btn_export_html.setText("💾 Export HTML...")
        btn_export_html.clicked.connect(self._export_html)
        bar_layout.addWidget(btn_export_html)

        bar_layout.addStretch()
        layout.addLayout(bar_layout)

        # Text Browser
        self.browser = QTextBrowser(self)
        self.browser.setOpenExternalLinks(True)
        app = QApplication.instance()
        if app:
            self.browser.document().setDefaultFont(app.font())
        self.browser.setHtml(self.report_model.html_content)
        layout.addWidget(self.browser)

    def set_report(self, report_model: ReportModel):
        self.report_model = report_model
        self.browser.setHtml(report_model.html_content)

    def _copy_text(self):
        QApplication.clipboard().setText(self.browser.toPlainText())
        QMessageBox.information(self, "Copied", "Report text copied to clipboard!")

    def _export_html(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Report HTML", f"{self.report_model.title}.html", "HTML Files (*.html)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.report_model.html_content)
            QMessageBox.information(self, "Saved", f"Report saved to {path}")

    def set_zoom(self, zoom: float):
        """Scales browser document font and layout with zoom level."""
        app = QApplication.instance()
        if app:
            base_font = app.font()
            pt = max(6, int(round(base_font.pointSize())))
            font = self.browser.font()
            font.setPointSize(pt)
            self.browser.setFont(font)
            self.browser.document().setDefaultFont(font)
