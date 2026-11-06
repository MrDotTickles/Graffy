"""
Interactive Fit a curve dialog.
Linear, Polynomial, and Non-linear fitting with parameter constraints,
ROI range selection, live preview, graph overlay, and report generation.
"""

from typing import Optional, List, Dict, Any
import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QLabel, QLineEdit, QCheckBox, QDoubleSpinBox, QPushButton,
    QGroupBox, QTextBrowser, QDialogButtonBox, QMessageBox,
    QScrollArea, QWidget, QFrame, QSizePolicy, QApplication
)
from omnigraph.core.project import Project, GraphModel, CurveModel, ReportModel
from omnigraph.core.worksheet import Worksheet, Column, ColumnRole, Workbook
from omnigraph.analysis.fitting import CurveFitter, FitResult


class FitDialog(QDialog):
    """Wizard for fitting data curves and generating publication reports."""

    def __init__(
        self,
        project: Project,
        active_graph: Optional[GraphModel] = None,
        active_worksheet: Optional[Worksheet] = None,
        initial_fit_type: str = "linear",
        roi_range: Optional[tuple] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.project = project
        self.active_graph = active_graph
        self.active_worksheet = active_worksheet
        self.roi_range = roi_range
        self.last_fit_result: Optional[FitResult] = None

        self.setWindowTitle("Fit a curve")
        self.resize(650, 580)
        self.setMinimumSize(540, 480)
        self._init_ui(initial_fit_type)

    def _init_ui(self, initial_fit_type: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # Scrollable configuration area ensures controls adapt to any DPI scaling or screen size
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(8)
        content_layout.setContentsMargins(0, 0, 4, 0)

        # 1. Data Source Selection
        grp_src = QGroupBox("Data Source")
        fl_src = QFormLayout(grp_src)

        self.combo_sheet = QComboBox()
        self.combo_sheet.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_sheet.setMinimumContentsLength(10)
        for wb in self.project.workbooks:
            for s in wb.sheets:
                self.combo_sheet.addItem(f"{wb.name} - {s.name}", (wb.name, s.name))
        fl_src.addRow("Worksheet:", self.combo_sheet)

        self.combo_x_col = QComboBox()
        self.combo_x_col.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_x_col.setMinimumContentsLength(10)
        fl_src.addRow("X Column:", self.combo_x_col)

        self.combo_y_col = QComboBox()
        self.combo_y_col.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_y_col.setMinimumContentsLength(10)
        fl_src.addRow("Y Column (Data):", self.combo_y_col)

        content_layout.addWidget(grp_src)

        # 2. Model Selection
        grp_model = QGroupBox("Fitting Function / Model")
        fl_model = QFormLayout(grp_model)

        self.combo_model = QComboBox()
        self.combo_model.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_model.setMinimumContentsLength(10)
        self.combo_model.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_model.addItem("Linear Regression (y = m*x + b)", "linear")
        self.combo_model.addItem("Polynomial (Degree 2): y = c2*x² + c1*x + c0", "poly2")
        self.combo_model.addItem("Polynomial (Degree 3): y = c3*x³ + c2*x² + c1*x + c0", "poly3")
        self.combo_model.addItem("Gaussian Peak: y = y0 + A/(w*√(π/2)) * exp(-2*((x-xc)/w)²)", "gaussian")
        self.combo_model.addItem("Exponential Decay: y = y0 + A * exp(-x / t)", "exp_decay")
        self.combo_model.addItem("Exponential Growth: y = y0 + A * exp(k * x)", "exp_growth")
        self.combo_model.addItem("Dose-Response / Pharmacological 4PL (Hill / IC50)", "hill")
        self.combo_model.addItem("Michaelis-Menten Kinetics: v = Vmax*x / (Km + x)", "michaelis_menten")
        self.combo_model.addItem("Power Law: y = a * x^b", "power")

        # Set initial
        for i in range(self.combo_model.count()):
            if self.combo_model.itemData(i) == initial_fit_type:
                self.combo_model.setCurrentIndex(i)
                break

        fl_model.addRow("Model Function:", self.combo_model)

        # Fix intercept option for linear
        self.chk_fix_intercept = QCheckBox("Fix Intercept at Zero (b = 0)")
        fl_model.addRow("", self.chk_fix_intercept)

        # ROI Range: multi-line layout to prevent horizontal overflow
        self.chk_use_roi = QCheckBox("Fit Selected ROI Range Only")
        fl_model.addRow("", self.chk_use_roi)

        self.spn_roi_min = QDoubleSpinBox()
        self.spn_roi_min.setRange(-1e9, 1e9)
        self.spn_roi_max = QDoubleSpinBox()
        self.spn_roi_max.setRange(-1e9, 1e9)

        if self.roi_range:
            self.chk_use_roi.setChecked(True)
            self.spn_roi_min.setValue(self.roi_range[0])
            self.spn_roi_max.setValue(self.roi_range[1])

        roi_layout = QHBoxLayout()
        roi_layout.addWidget(QLabel("Min X:"))
        roi_layout.addWidget(self.spn_roi_min)
        roi_layout.addWidget(QLabel("Max X:"))
        roi_layout.addWidget(self.spn_roi_max)
        fl_model.addRow("Range Bounds:", roi_layout)

        content_layout.addWidget(grp_model)

        # 3. Output Options
        grp_out = QGroupBox("Fit Output Actions")
        fl_out = QVBoxLayout(grp_out)
        self.chk_overlay_graph = QCheckBox("Overlay fitted curve onto active graph")
        self.chk_overlay_graph.setChecked(True)
        fl_out.addWidget(self.chk_overlay_graph)

        self.chk_conf_band = QCheckBox("Draw 95% Confidence Band shading")
        self.chk_conf_band.setChecked(True)
        fl_out.addWidget(self.chk_conf_band)

        self.chk_create_report = QCheckBox("Generate scientific Fit Report tab")
        self.chk_create_report.setChecked(True)
        fl_out.addWidget(self.chk_create_report)

        self.chk_export_sheet = QCheckBox("Export fitted data & residuals to new Worksheet tab")
        self.chk_export_sheet.setChecked(True)
        fl_out.addWidget(self.chk_export_sheet)

        content_layout.addWidget(grp_out)

        # 4. Preview / Results Display
        self.txt_preview = QTextBrowser()
        self.txt_preview.setObjectName("AnalysisReport")
        self.txt_preview.setMinimumHeight(125)
        self.txt_preview.setMaximumHeight(190)
        self.txt_preview.setHtml("<i>Click 'Preview fit' to evaluate and preview results.</i>")
        content_layout.addWidget(self.txt_preview)

        scroll.setWidget(content_widget)
        layout.addWidget(scroll, stretch=1)

        # Buttons (pinned at bottom outside scroll area)
        btn_layout = QHBoxLayout()
        btn_calc = QPushButton("Preview fit")
        btn_calc.clicked.connect(self._run_fit_calculation)
        btn_layout.addWidget(btn_calc)

        btn_layout.addStretch()

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self._on_accept)
        self.buttons.rejected.connect(self.reject)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Add fit")
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setDefault(True)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setProperty("role","primary")
        btn_layout.addWidget(self.buttons)

        layout.addLayout(btn_layout, stretch=0)

        self._populate_columns()
        self.combo_sheet.currentIndexChanged.connect(self._on_sheet_changed)
        curve = next((c for c in self.active_graph.curves if not c.is_fit_curve), None) if self.active_graph else None
        if curve:
            index = self.combo_sheet.findData((curve.source_workbook, curve.source_sheet))
            if index >= 0:
                self.combo_sheet.setCurrentIndex(index)
                self.combo_x_col.setCurrentIndex(max(0, self.combo_x_col.findData(curve.x_col_idx)))
                self.combo_y_col.setCurrentIndex(max(0, self.combo_y_col.findData(curve.y_col_idx)))
        elif self.active_worksheet:
            for index in range(self.combo_sheet.count()):
                if self.project.get_worksheet(*self.combo_sheet.itemData(index)) is self.active_worksheet:
                    self.combo_sheet.setCurrentIndex(index)
                    break
        self.combo_x_col.currentIndexChanged.connect(self._clear_fit_preview)
        self.combo_y_col.currentIndexChanged.connect(self._clear_fit_preview)
        self.combo_model.currentIndexChanged.connect(self._clear_fit_preview)
        self.chk_fix_intercept.toggled.connect(self._clear_fit_preview)
        self.chk_use_roi.toggled.connect(self._clear_fit_preview)
        self.spn_roi_min.valueChanged.connect(self._clear_fit_preview)
        self.spn_roi_max.valueChanged.connect(self._clear_fit_preview)
        from omnigraph.ui.dialogs.dialog_layout import fold_section, finish_dialog
        self.output_toggle, self.output_options = fold_section(grp_out, "Change fit outputs")
        summary = QLabel("Preview the fit, then add it to your project. The default adds the fitted curve, a report, and a results worksheet.")
        summary.setWordWrap(True)
        layout.insertWidget(0, summary)
        finish_dialog(self, scroll_body=False)

    def _clear_fit_preview(self):
        self.last_fit_result = None
        self.txt_preview.setPlainText("Settings changed. Preview the fit to see updated results.")

    def _on_sheet_changed(self):
        self._clear_fit_preview()
        self._populate_columns()

    def _populate_columns(self):
        self.combo_x_col.clear()
        self.combo_y_col.clear()

        data = self.combo_sheet.currentData()
        if not data:
            return
        wb_name, sheet_name = data
        wb = self.project.get_workbook(wb_name)
        if not wb:
            return
        sheet = next((s for s in wb.sheets if s.name == sheet_name), None)
        if not sheet:
            return

        x_candidate = 0
        y_candidate = 1 if sheet.column_count() > 1 else 0

        for i, col in enumerate(sheet.columns):
            self.combo_x_col.addItem(f"Col {col.name} ({col.role.value}): {col.display_label}", i)
            self.combo_y_col.addItem(f"Col {col.name} ({col.role.value}): {col.display_label}", i)
            if col.role == ColumnRole.X:
                x_candidate = i
            elif col.role == ColumnRole.Y and i > x_candidate:
                y_candidate = i

        self.combo_x_col.setCurrentIndex(x_candidate)
        self.combo_y_col.setCurrentIndex(y_candidate)

    def _run_fit_calculation(self) -> Optional[FitResult]:
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
        if len(x_arr) < 2:
            QMessageBox.warning(self, "Data Error", "Selected columns do not have enough valid numeric data points.")
            return None

        # ROI filter
        if self.chk_use_roi.isChecked():
            xmin = min(self.spn_roi_min.value(), self.spn_roi_max.value())
            xmax = max(self.spn_roi_min.value(), self.spn_roi_max.value())
            mask = (x_arr >= xmin) & (x_arr <= xmax)
            x_arr = x_arr[mask]
            y_arr = y_arr[mask]
            if len(x_arr) < 2:
                QMessageBox.warning(self, "ROI Error", "No data points found in the selected ROI range.")
                return None

        model_code = self.combo_model.currentData()

        try:
            if model_code == "linear":
                res = CurveFitter.linear_fit(x_arr, y_arr, fix_intercept=self.chk_fix_intercept.isChecked())
            elif model_code == "poly2":
                res = CurveFitter.polynomial_fit(x_arr, y_arr, degree=2)
            elif model_code == "poly3":
                res = CurveFitter.polynomial_fit(x_arr, y_arr, degree=3)
            else:
                res = CurveFitter.nonlinear_fit(x_arr, y_arr, model_type=model_code)

            self.last_fit_result = res

            self.txt_preview.setHtml(res.to_html_report(details=False))
            return res

        except Exception as e:
            QMessageBox.critical(self, "Fit Calculation Failed", f"Curve fitting failed to converge:\n{e}")
            return None

    def _on_accept(self):
        res = self.last_fit_result or self._run_fit_calculation()
        if not res:
            return

        data = self.combo_sheet.currentData()
        if not data:
            return
        wb_name, sheet_name = data
        wb = self.project.get_workbook(wb_name)
        sheet = next((s for s in wb.sheets if s.name == sheet_name), None) if wb else None
        x_col_idx = self.combo_x_col.currentData()
        y_col_idx = self.combo_y_col.currentData()

        # 1. Export fitted curve and residuals to a new Worksheet tab (like Origin's FitLinear1)
        if self.chk_export_sheet.isChecked() and wb:
            fit_sheet_name = f"Fit_{res.model_name[:8]}_{len(wb.sheets)}"
            fit_ws = Worksheet(name=fit_sheet_name)
            col_xf = Column(name="A", long_name="Fitted X", role=ColumnRole.X, data=res.x_dense.tolist())
            col_yf = Column(name="B", long_name="Fitted Y", role=ColumnRole.Y, data=res.y_dense.tolist())
            col_xo = Column(name="C", long_name="Orig X", role=ColumnRole.X, data=res.x_orig.tolist())
            col_res = Column(name="D", long_name="Residuals", role=ColumnRole.Y, data=res.residuals.tolist())
            fit_ws.columns = [col_xf, col_yf, col_xo, col_res]
            wb.sheets.append(fit_ws)

            # 2. Overlay fitted curve on graph
            if self.chk_overlay_graph.isChecked() and self.active_graph:
                src_curve = next(
                    (c for c in self.active_graph.curves
                     if not c.is_fit_curve and c.source_workbook == wb.name and c.source_sheet == sheet_name
                     and c.x_col_idx == x_col_idx and c.y_col_idx == y_col_idx),
                    None
                )
                src_id = src_curve.id if src_curve else None
                model_code = self.combo_model.currentData()
                live_fit = src_id and not self.chk_use_roi.isChecked() and not (
                    model_code == "linear" and self.chk_fix_intercept.isChecked()
                )
                deg = 2 if model_code == "poly2" else (3 if model_code == "poly3" else None)

                fit_curve = CurveModel(
                    source_workbook=wb.name,
                    source_sheet=fit_sheet_name,
                    x_col_idx=0,
                    y_col_idx=1,
                    label=f"Fit ({res.model_name})",
                    color="#d62728",
                    line_style="-",
                    line_width=2.0,
                    marker="none",
                    plot_type="line",
                    is_fit_curve=True,
                    fit_formula_str=res.formula_str,
                    fit_model_name=model_code if live_fit else None,
                    fit_source_curve_id=src_id,
                    fit_degree=deg,
                )
                self.active_graph.add_curve(fit_curve)

                # 95% Confidence Band overlay
                if self.chk_conf_band.isChecked() and res.conf_band_lower is not None:
                    self.active_graph.annotations.append({
                        "type": "band",
                        "x_data": res.x_dense.tolist(),
                        "lower_data": res.conf_band_lower.tolist(),
                        "upper_data": res.conf_band_upper.tolist(),
                        "color": "#0284c7",
                        "alpha": 0.18,
                        "label": "95% Conf. Band",
                    })

        # 3. Generate Scientific Report tab
        if self.chk_create_report.isChecked():
            x = sheet.get_column(x_col_idx) if sheet else None
            y = sheet.get_column(y_col_idx) if sheet else None
            source = f"{wb_name} / {sheet_name}"
            if x and y:
                source += f" · {x.display_label} → {y.display_label}"
            if len(res.x_orig):
                source += f" · X range {np.min(res.x_orig):.6g} to {np.max(res.x_orig):.6g}"
            rep = ReportModel(
                title=f"{res.model_name} Report",
                report_type="fit",
                html_content=res.to_html_report(source=source),
                parameters=res.parameters,
            )
            self.project.reports.append(rep)

        self.accept()
