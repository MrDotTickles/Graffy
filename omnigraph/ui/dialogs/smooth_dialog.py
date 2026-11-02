"""
Smoothing, filtering, and mathematical signal processing dialog.
Savitzky-Golay, Moving Average, Gaussian, Derivatives, Integrals, and FFT.
"""

from typing import Optional
import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QSpinBox,
    QDoubleSpinBox, QRadioButton, QButtonGroup, QDialogButtonBox,
    QMessageBox, QLabel, QScrollArea, QWidget, QFrame, QSizePolicy
)
from omnigraph.core.project import Project
from omnigraph.core.worksheet import Worksheet, Column, ColumnRole
from omnigraph.analysis.smoothing import SignalProcessor


class SmoothDialog(QDialog):
    """Dialog for applying smoothing filters and signal transformations."""

    def __init__(self, worksheet: Worksheet, selected_col_idx: int = 1, parent=None):
        super().__init__(parent)
        self.worksheet = worksheet
        self.selected_col_idx = selected_col_idx
        self.setWindowTitle("Signal Processing & Smoothing")
        self.resize(480, 420)
        self.setMinimumSize(380, 300)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content_widget = QWidget()
        form = QFormLayout(content_widget)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        # Columns
        self.combo_col = QComboBox()
        self.combo_col.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_col.setMinimumContentsLength(8)
        for i, c in enumerate(self.worksheet.columns):
            self.combo_col.addItem(f"Col {c.name}: {c.display_label}", i)
        self.combo_col.setCurrentIndex(max(0, min(self.selected_col_idx, self.worksheet.column_count() - 1)))
        form.addRow("Target Data Column:", self.combo_col)

        # Method
        self.combo_method = QComboBox()
        self.combo_method.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_method.setMinimumContentsLength(10)
        self.combo_method.addItem("Savitzky-Golay Filter", "savgol")
        self.combo_method.addItem("Moving Average", "moving_avg")
        self.combo_method.addItem("Gaussian Smoothing", "gaussian")
        self.combo_method.addItem("1st Derivative (dy/dx)", "d1")
        self.combo_method.addItem("2nd Derivative (d²y/dx²)", "d2")
        self.combo_method.addItem("Cumulative Integral (∫ y dx)", "integral")
        self.combo_method.addItem("FFT Power Spectrum", "fft")
        self.combo_method.currentIndexChanged.connect(self._on_method_changed)
        form.addRow("Transformation:", self.combo_method)

        # Parameters
        self.spn_window = QSpinBox()
        self.spn_window.setRange(3, 101)
        self.spn_window.setSingleStep(2)
        self.spn_window.setValue(11)
        form.addRow("Window Size (odd):", self.spn_window)

        self.spn_poly = QSpinBox()
        self.spn_poly.setRange(1, 5)
        self.spn_poly.setValue(2)
        form.addRow("Polynomial Order:", self.spn_poly)

        self.spn_sigma = QDoubleSpinBox()
        self.spn_sigma.setRange(0.1, 50.0)
        self.spn_sigma.setValue(2.0)
        form.addRow("Gaussian Sigma:", self.spn_sigma)

        # Destination
        self.radio_new_col = QRadioButton("Add as New Column")
        self.radio_new_col.setChecked(True)
        self.radio_replace = QRadioButton("Replace Existing Column Data")
        self.btn_grp = QButtonGroup(self)
        self.btn_grp.addButton(self.radio_new_col)
        self.btn_grp.addButton(self.radio_replace)

        form.addRow("Output Target:", self.radio_new_col)
        form.addRow("", self.radio_replace)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        self._on_method_changed()

    def _on_method_changed(self):
        method = self.combo_method.currentData()
        self.spn_window.setEnabled(method in ("savgol", "moving_avg"))
        self.spn_poly.setEnabled(method == "savgol")
        self.spn_sigma.setEnabled(method == "gaussian")

    def _on_accept(self):
        col_idx = self.combo_col.currentData()
        if col_idx is None:
            return
        col = self.worksheet.get_column(col_idx)
        if not col:
            return

        x_idx = self.worksheet.find_x_column_for(col_idx)
        x_col = self.worksheet.get_column(x_idx) if x_idx is not None else None

        if x_col and x_col != col:
            xs, ys, valid_idx = x_col.get_valid_numeric_pairs(col)
        else:
            arr_y = col.to_numpy_array()
            valid = ~np.isnan(arr_y)
            valid_idx = np.where(valid)[0]
            ys = arr_y[valid]
            xs = valid_idx.astype(float)

        if len(ys) < 3:
            QMessageBox.warning(self, "Data Error", "Not enough valid numeric data points.")
            return

        method = self.combo_method.currentData()
        try:
            if method == "savgol":
                res = SignalProcessor.savitzky_golay(ys, self.spn_window.value(), self.spn_poly.value())
                suffix = "SG_Smooth"
            elif method == "moving_avg":
                res = SignalProcessor.moving_average(ys, self.spn_window.value())
                suffix = "MovAvg"
            elif method == "gaussian":
                res = SignalProcessor.gaussian_filter(ys, self.spn_sigma.value())
                suffix = "Gauss_Smooth"
            elif method == "d1":
                res = SignalProcessor.derivative_1st(xs, ys)
                suffix = "d1"
            elif method == "d2":
                res = SignalProcessor.derivative_2nd(xs, ys)
                suffix = "d2"
            elif method == "integral":
                res = SignalProcessor.cumulative_integral(xs, ys)
                suffix = "Integral"
            elif method == "fft":
                f, p = SignalProcessor.fft_spectrum(xs, ys)
                # Create FFT sheet
                col_f = self.worksheet.add_column(long_name="Frequency", units="Hz", role=ColumnRole.X)
                col_p = self.worksheet.add_column(long_name="FFT Power", units="", role=ColumnRole.Y)
                col_f.data = f.tolist()
                col_p.data = p.tolist()
                self.accept()
                return

            total_rows = max(len(col.data), self.worksheet.row_count())
            if self.radio_replace.isChecked():
                out_data = list(col.data)
                if len(out_data) < total_rows:
                    out_data.extend([None] * (total_rows - len(out_data)))
                for idx, val in zip(valid_idx, res):
                    out_data[idx] = float(val)
                col.data = out_data
            else:
                new_col = self.worksheet.add_column(long_name=f"{col.name}_{suffix}", units=col.units, role=ColumnRole.Y)
                out_data = [None] * total_rows
                for idx, val in zip(valid_idx, res):
                    out_data[idx] = float(val)
                new_col.data = out_data

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Processing Error", str(e))
