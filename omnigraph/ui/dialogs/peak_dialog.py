"""
Interactive Peak Analysis & Integration Wizard dialog.
Detects peaks, subtracts baselines, calculates FWHM and Area Under Curve (AUC),
and generates peak annotations and summary reports.
"""

from typing import Optional, List
import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QLabel, QDoubleSpinBox, QSpinBox, QCheckBox, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QDialogButtonBox, QMessageBox,
    QScrollArea, QFrame, QWidget, QSizePolicy, QApplication, QHeaderView
)
from omnigraph.core.project import Project, GraphModel, CurveModel, ReportModel
from omnigraph.core.worksheet import Worksheet, Column, ColumnRole
from omnigraph.analysis.peak_analysis import PeakAnalyzer, PeakAnalysisResult


class PeakAnalysisDialog(QDialog):
    """Wizard for scientific peak detection, baseline correction, and integration."""

    def __init__(
        self,
        project: Project,
        active_graph: Optional[GraphModel] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.project = project
        self.active_graph = active_graph
        self.last_result: Optional[PeakAnalysisResult] = None

        self.setWindowTitle("Peak Integration & Baseline Analysis")
        self.resize(720, 560)
        self.setMinimumSize(540, 440)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Scroll area ensures controls and boxes adapt gracefully to screen resolution and zoom scaling
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(2, 2, 2, 2)

        # Left Column: Data Source, Parameters, and Output Configuration
        left_widget = QWidget()
        left_widget.setMinimumWidth(280)
        left_widget.setMaximumWidth(320)
        if self.screen().availableGeometry().width()<760:
            content_layout.setDirection(QHBoxLayout.Direction.TopToBottom)
            left_widget.setMinimumWidth(0)
            left_widget.setMaximumWidth(16777215)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(8)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 1. Source Data
        grp_src = QGroupBox("Data Source")
        fl_src = QFormLayout(grp_src)
        fl_src.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        fl_src.setContentsMargins(8, 12, 8, 8)
        fl_src.setSpacing(6)

        self.combo_sheet = QComboBox()
        self.combo_sheet.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_sheet.setMinimumContentsLength(10)
        self.combo_sheet.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for wb in self.project.workbooks:
            for s in wb.sheets:
                self.combo_sheet.addItem(f"{wb.name} - {s.name}", (wb.name, s.name))
        self.combo_sheet.currentIndexChanged.connect(self._populate_columns)
        fl_src.addRow("Worksheet:", self.combo_sheet)

        self.combo_x_col = QComboBox()
        self.combo_x_col.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_x_col.setMinimumContentsLength(8)
        self.combo_x_col.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        fl_src.addRow("X Column:", self.combo_x_col)

        self.combo_y_col = QComboBox()
        self.combo_y_col.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_y_col.setMinimumContentsLength(8)
        self.combo_y_col.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        fl_src.addRow("Y Column (Spectrum):", self.combo_y_col)

        left_layout.addWidget(grp_src)

        # 2. Parameters
        grp_params = QGroupBox("Peak Search & Baseline Settings")
        fl_params = QFormLayout(grp_params)
        fl_params.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        fl_params.setContentsMargins(8, 12, 8, 8)
        fl_params.setSpacing(6)

        self.combo_baseline = QComboBox()
        self.combo_baseline.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_baseline.setMinimumContentsLength(8)
        self.combo_baseline.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_baseline.addItem("Linear Baseline", "linear")
        self.combo_baseline.addItem("Constant (Min Y)", "constant")
        self.combo_baseline.addItem("Polynomial (Order 2)", "poly")
        self.combo_baseline.addItem("None (Raw Y)", "none")
        fl_params.addRow("Baseline Correction:", self.combo_baseline)

        self.spn_prominence = QDoubleSpinBox()
        self.spn_prominence.setRange(0.5, 90.0)
        self.spn_prominence.setValue(5.0)
        self.spn_prominence.setSuffix(" %")
        self.spn_prominence.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        fl_params.addRow("Min Prominence (%):", self.spn_prominence)

        self.spn_distance = QSpinBox()
        self.spn_distance.setRange(1, 200)
        self.spn_distance.setValue(5)
        self.spn_distance.setSuffix(" pts")
        self.spn_distance.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        fl_params.addRow("Min Distance:", self.spn_distance)

        left_layout.addWidget(grp_params)

        # 3. Actions / Outputs
        grp_actions = QGroupBox("Outputs")
        al = QVBoxLayout(grp_actions)
        al.setContentsMargins(8, 12, 8, 8)
        al.setSpacing(6)
        self.chk_add_markers = QCheckBox("Add peak callout annotations to active graph")
        self.chk_add_markers.setChecked(True)
        al.addWidget(self.chk_add_markers)

        self.chk_create_report = QCheckBox("Generate Peak Integration Report tab")
        self.chk_create_report.setChecked(True)
        al.addWidget(self.chk_create_report)
        left_layout.addWidget(grp_actions)

        # Detect button (prominent in control column)
        btn_search = QPushButton("Find peaks and integrate")
        btn_search.setProperty("role","primary")
        btn_search.clicked.connect(self._run_peak_search)
        left_layout.addWidget(btn_search)
        left_layout.addStretch()

        content_layout.addWidget(left_widget, stretch=0)

        # Right Column: Detected Peaks & Area Under Curve (AUC) Table
        grp_table = QGroupBox("Detected Peaks & Area Under Curve (AUC)")
        tl = QVBoxLayout(grp_table)
        tl.setContentsMargins(8, 12, 8, 8)
        tl.setSpacing(6)

        self.table_peaks = QTableWidget()
        self.table_peaks.setColumnCount(5)
        self.table_peaks.setHorizontalHeaderLabels(["Peak ID", "Center (X)", "Net Height", "FWHM", "% Area"])
        self.table_peaks.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_peaks.setAlternatingRowColors(True)
        self.table_peaks.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_peaks.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_peaks.setMinimumHeight(180)
        self.table_peaks.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        tl.addWidget(self.table_peaks)

        content_layout.addWidget(grp_table, stretch=1)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll, 1)

        # Buttons (pinned at bottom outside scroll area)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Add peak results")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setProperty("role","primary")
        from omnigraph.ui.dialogs.dialog_layout import finish_dialog
        finish_dialog(self,scroll_body=False)

        self.combo_x_col.currentIndexChanged.connect(self._clear_cached_result)
        self.combo_y_col.currentIndexChanged.connect(self._clear_cached_result)
        self.combo_baseline.currentIndexChanged.connect(self._clear_cached_result)
        self.spn_prominence.valueChanged.connect(self._clear_cached_result)
        self.spn_distance.valueChanged.connect(self._clear_cached_result)

        self._populate_columns()
        self._run_peak_search(quiet=True)

    def _clear_cached_result(self, *args):
        self.last_result = None

    def _populate_columns(self):
        self._clear_cached_result()
        self.table_peaks.setRowCount(0)
        self.combo_x_col.blockSignals(True)
        self.combo_y_col.blockSignals(True)
        self.combo_x_col.clear()
        self.combo_y_col.clear()

        data = self.combo_sheet.currentData()
        if not data:
            self.combo_x_col.blockSignals(False)
            self.combo_y_col.blockSignals(False)
            return
        wb_name, sheet_name = data
        wb = self.project.get_workbook(wb_name)
        if not wb:
            self.combo_x_col.blockSignals(False)
            self.combo_y_col.blockSignals(False)
            return
        sheet = next((s for s in wb.sheets if s.name == sheet_name), None)
        if not sheet:
            self.combo_x_col.blockSignals(False)
            self.combo_y_col.blockSignals(False)
            return

        x_candidate = 0
        y_candidate = 1 if sheet.column_count() > 1 else 0

        for i, col in enumerate(sheet.columns):
            self.combo_x_col.addItem(f"Col {col.name}: {col.display_label}", i)
            self.combo_y_col.addItem(f"Col {col.name}: {col.display_label}", i)
            if col.role == ColumnRole.X:
                x_candidate = i
            elif col.role == ColumnRole.Y and i > x_candidate:
                y_candidate = i

        self.combo_x_col.setCurrentIndex(x_candidate)
        self.combo_y_col.setCurrentIndex(y_candidate)
        self.combo_x_col.blockSignals(False)
        self.combo_y_col.blockSignals(False)

    def _run_peak_search(self, quiet: bool = False) -> Optional[PeakAnalysisResult]:
        data = self.combo_sheet.currentData()
        if not data:
            return None
        wb_name, sheet_name = data
        wb = self.project.get_workbook(wb_name)
        if not wb:
            return None
        sheet = next((s for s in wb.sheets if s.name == sheet_name), None)
        if not sheet:
            return None

        x_col_idx = self.combo_x_col.currentData()
        y_col_idx = self.combo_y_col.currentData()
        if x_col_idx is None or y_col_idx is None:
            return None

        x_col = sheet.get_column(x_col_idx)
        y_col = sheet.get_column(y_col_idx)
        if not x_col or not y_col:
            return None

        x_arr, y_arr, _ = x_col.get_valid_numeric_pairs(y_col)
        if len(x_arr) < 5:
            if not quiet:
                QMessageBox.warning(self, "Data Error", "At least 5 valid data points required.")
            return None

        baseline_mode = self.combo_baseline.currentData()
        prom = self.spn_prominence.value()
        dist = self.spn_distance.value()

        try:
            res = PeakAnalyzer.analyze_peaks(x_arr, y_arr, baseline_mode=baseline_mode, min_prominence_pct=prom, min_distance=dist)
            self.last_result = res

            # Populate table
            self.table_peaks.setRowCount(len(res.peaks))
            for i, p in enumerate(res.peaks):
                self.table_peaks.setItem(i, 0, QTableWidgetItem(f"Peak #{p.peak_id}"))
                self.table_peaks.setItem(i, 1, QTableWidgetItem(f"{p.x_center:.4f}"))
                self.table_peaks.setItem(i, 2, QTableWidgetItem(f"{p.net_height:.4f}"))
                self.table_peaks.setItem(i, 3, QTableWidgetItem(f"{p.fwhm:.4f}"))
                self.table_peaks.setItem(i, 4, QTableWidgetItem(f"{p.rel_area_percent:.2f}%"))

            return res

        except Exception as e:
            if not quiet:
                QMessageBox.critical(self, "Peak Detection Failed", str(e))
            return None

    def _on_accept(self):
        res = self.last_result or self._run_peak_search()
        if not res:
            return

        # 1. Add annotations to active graph
        if self.chk_add_markers.isChecked() and self.active_graph:
            for p in res.peaks:
                self.active_graph.annotations.append({
                    "type": "text",
                    "x": p.x_center,
                    "y": p.y_height + 0.05 * p.net_height,
                    "text": f"▼ P{p.peak_id} ({p.x_center:.3g})\n{p.rel_area_percent:.1f}%",
                    "color": "#0f766e",
                    "font_size": 9,
                })

        # 2. Add Report tab
        if self.chk_create_report.isChecked():
            rep = ReportModel(
                title=f"Peak Report ({len(res.peaks)} Peaks)",
                report_type="peak_analysis",
                html_content=res.to_html_report(),
                parameters={"peaks_count": len(res.peaks), "total_area": res.total_area},
            )
            self.project.reports.append(rep)

        self.accept()
