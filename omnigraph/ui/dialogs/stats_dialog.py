"""
Descriptive statistics and hypothesis testing dialog.
"""

from typing import List
import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QComboBox, QCheckBox, QPushButton, QLabel,
    QTextBrowser, QDialogButtonBox, QApplication, QMessageBox, QWidget,
    QHeaderView
)
from PyQt6.QtCore import Qt
from omnigraph.core.worksheet import Column
from omnigraph.core.project import ReportModel
from omnigraph.analysis.reporting import report_document, report_table, result_number
from omnigraph.analysis.statistics import StatisticsAnalyzer


class StatsDialog(QDialog):
    """Dialog showing descriptive statistics and two-sample t-tests."""

    def __init__(self, columns: List[Column], parent=None, *, source=""):
        super().__init__(parent)
        self.columns = columns
        self.source = source
        self.saved_report = None
        self.setWindowTitle("Explore statistics")
        self.resize(720, 480)
        self.setMinimumSize(560, 380)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)

        # Tab 1: Descriptive Stats
        tab1 = QWidget()
        l1 = QVBoxLayout(tab1)

        self.table_stats = QTableWidget()
        metrics = ["N", "Mean", "Std Dev", "SEM", "Median", "Min", "Max", "Sum", "Skewness"]
        self.table_stats.setColumnCount(len(metrics))
        self.table_stats.setHorizontalHeaderLabels(metrics)
        self.table_stats.setRowCount(len(self.columns))
        self.table_stats.setAlternatingRowColors(True)
        self.table_stats.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_stats.setVerticalHeaderLabels([c.display_label for c in self.columns])
        self.table_stats.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_stats.horizontalHeader().setStretchLastSection(True)

        for row_i, col in enumerate(self.columns):
            s = col.stats()
            vals = [
                str(s["n"]),
                f"{s['mean']:.5g}" if s["mean"] is not None else "-",
                f"{s['std']:.5g}" if s["std"] is not None else "-",
                f"{s['sem']:.5g}" if s["sem"] is not None else "-",
                f"{s['median']:.5g}" if s["median"] is not None else "-",
                f"{s['min']:.5g}" if s["min"] is not None else "-",
                f"{s['max']:.5g}" if s["max"] is not None else "-",
                f"{s['sum']:.5g}" if s["sum"] is not None else "-",
                f"{s['skewness']:.3f}" if s["skewness"] is not None else "-",
            ]
            for col_i, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table_stats.setItem(row_i, col_i, item)

        l1.addWidget(self.table_stats)

        btn_copy_tsv = QPushButton("Copy results")
        btn_copy_tsv.clicked.connect(self._copy_stats_tsv)
        l1.addWidget(btn_copy_tsv)
        self.copy_status = QLabel("")
        self.copy_status.setWordWrap(True)
        l1.addWidget(self.copy_status)

        self.tabs.addTab(tab1, "Summary")

        # Tab 2: Two-Sample t-Test
        tab2 = QWidget()
        l2 = QVBoxLayout(tab2)

        sel_layout = QHBoxLayout()
        sel_layout.addWidget(QLabel("Group 1:"))
        self.combo_g1 = QComboBox()
        self.combo_g1.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_g1.setMinimumContentsLength(8)
        for c in self.columns:
            self.combo_g1.addItem(c.display_label, c)
        sel_layout.addWidget(self.combo_g1)

        sel_layout.addWidget(QLabel("Group 2:"))
        self.combo_g2 = QComboBox()
        self.combo_g2.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_g2.setMinimumContentsLength(8)
        for c in self.columns:
            self.combo_g2.addItem(c.display_label, c)
        if len(self.columns) > 1:
            self.combo_g2.setCurrentIndex(1)
        sel_layout.addWidget(self.combo_g2)

        l2.addLayout(sel_layout)

        opt_layout = QHBoxLayout()
        self.chk_paired = QCheckBox("Paired Samples (Repeated measures)")
        opt_layout.addWidget(self.chk_paired)
        self.chk_welch = QCheckBox("Welch's t-test (Unequal variances)")
        opt_layout.addWidget(self.chk_welch)
        opt_layout.addStretch()
        l2.addLayout(opt_layout)

        btn_run_ttest = QPushButton("Compare groups")
        btn_run_ttest.clicked.connect(self._run_ttest)
        l2.addWidget(btn_run_ttest)

        self.btn_add_bracket = QPushButton("Add significance bracket to graph")
        self.btn_add_bracket.setEnabled(False)
        self.btn_add_bracket.clicked.connect(self._add_bracket_to_graph)
        l2.addWidget(self.btn_add_bracket)

        self.last_ttest_result = None

        self.txt_ttest_res = QTextBrowser()
        self.txt_ttest_res.setObjectName("AnalysisReport")
        self.txt_ttest_res.setHtml("<i>Choose two columns, then Compare groups to evaluate significance.</i>")
        l2.addWidget(self.txt_ttest_res)

        self.tabs.addTab(tab2, "Compare two groups")

        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        self.btn_save_report = buttons.addButton("Save report", QDialogButtonBox.ButtonRole.ActionRole)
        self.btn_save_report.clicked.connect(self._save_report)
        self.tabs.currentChanged.connect(self._update_report_button)
        self.combo_g1.currentIndexChanged.connect(self._clear_comparison)
        self.combo_g2.currentIndexChanged.connect(self._clear_comparison)
        self.chk_paired.toggled.connect(self._clear_comparison)
        self.chk_welch.toggled.connect(self._clear_comparison)
        self._update_report_button()
        layout.addWidget(buttons)
        self.chk_paired.setToolTip("Use paired data only when each row represents the same subject or a matched pair in both columns.")
        self.chk_welch.setToolTip("Welch's test allows the two groups to have different variances. This changes the statistical test; choose based on your study.")
        from omnigraph.ui.dialogs.dialog_layout import finish_dialog
        finish_dialog(self)

    def _copy_stats_tsv(self):
        lines = []
        # Header
        headers = ["Column"] + [self.table_stats.horizontalHeaderItem(i).text() for i in range(self.table_stats.columnCount())]
        lines.append("\t".join(headers))
        for r in range(self.table_stats.rowCount()):
            row_label = self.table_stats.verticalHeaderItem(r).text()
            row_cells = [self.table_stats.item(r, c).text() if self.table_stats.item(r, c) else "" for c in range(self.table_stats.columnCount())]
            lines.append("\t".join([row_label] + row_cells))

        QApplication.clipboard().setText("\n".join(lines))
        self.copy_status.setText("Results copied. Paste them into your spreadsheet or report.")

    def _run_ttest(self):
        col1 = self.combo_g1.currentData()
        col2 = self.combo_g2.currentData()
        if not col1 or not col2 or col1 == col2:
            QMessageBox.warning(self, "Selection Error", "Please select two distinct columns.")
            return

        paired = self.chk_paired.isChecked()
        equal_var = not self.chk_welch.isChecked()

        try:
            res = StatisticsAnalyzer.two_sample_ttest(col1, col2, paired=paired, equal_var=equal_var)
            self.txt_ttest_res.setHtml(self._comparison_report(res))
            self.last_ttest_result = res
            self.btn_add_bracket.setEnabled(True)
            self._update_report_button()

        except Exception as e:
            QMessageBox.critical(self, "t-Test Failed", str(e))

    def _comparison_report(self, result):
        p_value = result["p_value"]
        interpretation = ("p < 0.05" if result["significant_005"] else "p ≥ 0.05") if np.isfinite(p_value) else "Unavailable"
        summary = [
            ("Group 1", result["col1_name"]),
            ("Group 2", result["col2_name"]),
            ("p-value", result_number(p_value)),
            ("Threshold result", interpretation),
            ("Mean difference (group 1 − group 2)", result_number(result["mean_difference"])),
            ("t statistic", result_number(result["t_statistic"])),
            ("Degrees of freedom", result_number(result["dof"])),
            ("Sample sizes", f"{result['n1']} and {result['n2']}"),
        ]
        return report_document(f"Group comparison · {result['test_type']}", source=self.source, summary=summary)

    def _update_report_button(self):
        has_results = self.last_ttest_result is not None if self.tabs.currentIndex() == 1 else bool(self.columns)
        self.btn_save_report.setEnabled(has_results)

    def _clear_comparison(self):
        self.last_ttest_result = None
        self.txt_ttest_res.setPlainText("Choose two columns, then Compare groups.")
        self.btn_add_bracket.setEnabled(False)
        self._update_report_button()

    def _save_report(self):
        if self.tabs.currentIndex() == 1:
            if self.last_ttest_result is None:
                return
            title = "Group comparison"
            content = self._comparison_report(self.last_ttest_result)
        else:
            title = "Worksheet statistics"
            sections = []
            for row, column in enumerate(self.columns):
                metrics = [(self.table_stats.horizontalHeaderItem(index).text(),
                            self.table_stats.item(row, index).text())
                           for index in range(self.table_stats.columnCount())]
                sections.append((column.display_label, report_table(("Measure", "Value"), metrics, numeric=(1,))))
            content = report_document(title, source=self.source, sections=sections)
        self.saved_report = ReportModel(title=title, report_type="statistics", html_content=content)
        self.accept()

    def _add_bracket_to_graph(self):
        """Adds significance bracket for the computed t-test to the active graph."""
        if not self.last_ttest_result:
            return

        # Find active graph from parent window
        parent = self.parent()
        active_graph = None
        if hasattr(parent, "get_active_graph"):
            active_graph = parent.get_active_graph()
        elif hasattr(parent, "project") and getattr(parent.project, "graphs", []):
            active_graph = parent.project.graphs[0]

        if not active_graph:
            QMessageBox.information(self, "No Graph Found", "Please open or create a graph window first.")
            return

        p_val = self.last_ttest_result.get("p_value", 0.05)
        stars = StatisticsAnalyzer.p_to_stars(p_val)

        # Match col1 and col2 with curves on active graph to determine accurate group positions
        col1 = self.combo_g1.currentData()
        col2 = self.combo_g2.currentData()
        x1 = 1.0
        x2 = 2.0
        c1_idx = None
        c2_idx = None
        for i, c in enumerate(active_graph.curves):
            wb = parent.project.get_workbook(c.source_workbook) if hasattr(parent, "project") else None
            if wb:
                s = next((sh for sh in wb.sheets if sh.name == c.source_sheet), None)
                if s:
                    col = s.get_column(c.y_col_idx)
                    if col == col1 and c1_idx is None:
                        c1_idx = i + 1
                    elif col == col2 and c2_idx is None:
                        c2_idx = i + 1
        if c1_idx is not None and c2_idx is not None:
            x1 = float(c1_idx)
            x2 = float(c2_idx)
        # Determine highest Y value on graph to place bracket safely above data
        max_y = 10.0
        for c in active_graph.curves:
            wb = parent.project.get_workbook(c.source_workbook) if hasattr(parent, "project") else None
            if wb:
                s = next((sh for sh in wb.sheets if sh.name == c.source_sheet), None)
                if s:
                    col = s.get_column(c.y_col_idx)
                    if col:
                        arr = col.to_numpy_array()
                        valid = arr[~np.isnan(arr)]
                        if len(valid) > 0:
                            max_y = max(max_y, float(np.max(valid)))

        bracket_y = max_y * 1.12 if max_y > 0 else max_y + 1.0
        bracket = StatisticsAnalyzer.create_significance_bracket(
            x1=x1, x2=x2, y=bracket_y, p_value=p_val, custom_text=stars,
            h=abs(bracket_y) * 0.04 if bracket_y != 0 else 0.5
        )
        active_graph.annotations.append(bracket)

        if hasattr(parent, "refresh_active_graph"):
            parent.refresh_active_graph()
        elif hasattr(parent, "_on_graph_labels_changed"):
            parent._on_graph_labels_changed()

        QMessageBox.information(
            self,
            "Bracket Added",
            f"Significance bracket '{stars}' (p = {p_val:.4g}) added to {active_graph.title}!",
        )
