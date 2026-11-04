"""
Add Curve / Layer dialog.
Allows layering any dataset from any worksheet onto an active graph.
Supports primary Left Y, secondary Right Y (twin-x), and stacked subplot layers.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QLineEdit, QDoubleSpinBox, QPushButton, QColorDialog,
    QDialogButtonBox, QMessageBox, QLabel, QGroupBox, QScrollArea,
    QWidget, QFrame, QSizePolicy, QApplication
)
from PyQt6.QtGui import QColor

from omnigraph.ui.dialogs.dialog_layout import fold_section, finish_dialog
from omnigraph.core.project import Project, GraphModel, CurveModel
from omnigraph.core.worksheet import ColumnRole


class AddCurveDialog(QDialog):
    """Dialog to layer a new data curve onto an existing graph."""

    def __init__(self, project: Project, active_graph: GraphModel, parent=None):
        super().__init__(parent)
        self.project = project
        self.active_graph = active_graph
        self.selected_color = "auto"

        self.setWindowTitle(f"Add data to {active_graph.title}")
        self.resize(520, 480)
        self.setMinimumSize(420, 360)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(8)

        # 1. Source Worksheet
        grp_src = QGroupBox("Data Source")
        fl_src = QFormLayout(grp_src)
        fl_src.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.combo_sheet = QComboBox()
        self.combo_sheet.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_sheet.setMinimumContentsLength(8)
        for wb in self.project.workbooks:
            for s in wb.sheets:
                self.combo_sheet.addItem(f"{wb.name} - {s.name}", (wb.name, s.name))
        self.combo_sheet.currentIndexChanged.connect(self._populate_columns)
        fl_src.addRow("Worksheet:", self.combo_sheet)

        self.combo_x_col = QComboBox()
        self.combo_x_col.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_x_col.setMinimumContentsLength(8)
        fl_src.addRow("X Column:", self.combo_x_col)

        self.combo_y_col = QComboBox()
        self.combo_y_col.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_y_col.setMinimumContentsLength(8)
        self.combo_y_col.currentIndexChanged.connect(self._on_y_col_changed)
        fl_src.addRow("Y Column:", self.combo_y_col)

        self.combo_yerr_col = QComboBox()
        self.combo_yerr_col.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_yerr_col.setMinimumContentsLength(8)
        fl_src.addRow("Y Error (Optional):", self.combo_yerr_col)

        layout.addWidget(grp_src)

        # 2. Layer & Style
        grp_style = QGroupBox("Data series")
        fl_style = QFormLayout(grp_style)

        self.txt_label = QLineEdit("Series")
        fl_style.addRow("Series name:", self.txt_label)

        self.combo_plot_type = QComboBox()
        self.combo_plot_type.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_plot_type.addItems([
            "scatter", "line", "line_symbol", "bar", "step", "spline", "area", "errorbar"
        ])
        self.combo_plot_type.setCurrentText("line_symbol")
        fl_style.addRow("Plot Type:", self.combo_plot_type)

        grp_advanced = QGroupBox("Appearance")
        fl_advanced = QFormLayout(grp_advanced)
        fl_advanced.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.combo_axis = QComboBox()
        self.combo_axis.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_axis.addItem("Left vertical axis", "primary")
        self.combo_axis.addItem("Right vertical axis", "secondary")
        self.combo_axis.addItem("Separate lower panel", "bottom_panel")
        fl_advanced.addRow("Axes:", self.combo_axis)

        # Color picker
        color_layout = QHBoxLayout()
        self.btn_color = QPushButton("Auto Palette Color")
        self.btn_color.clicked.connect(self._pick_color)
        color_layout.addWidget(self.btn_color)
        fl_advanced.addRow("Color:", color_layout)

        # Marker (conditionally shown if plot type has symbols)
        self.lbl_marker = QLabel("Marker:")
        self.combo_marker = QComboBox()
        self.combo_marker.addItems(["o (Circle)", "s (Square)", "^ (Triangle Up)", "v (Triangle Down)", "D (Diamond)", "* (Star)", "+ (Plus)", "x (Cross)", "none"])
        fl_advanced.addRow(self.lbl_marker, self.combo_marker)

        # Line style (conditionally shown if plot type has lines)
        self.lbl_line_style = QLabel("Line Style:")
        self.combo_line_style = QComboBox()
        self.combo_line_style.addItems(["- (Solid)", "-- (Dashed)", "-. (Dash-Dot)", ": (Dotted)", "none"])
        fl_advanced.addRow(self.lbl_line_style, self.combo_line_style)

        self.combo_plot_type.currentTextChanged.connect(self._update_symbol_visibility)
        self._update_symbol_visibility()

        layout.addWidget(grp_style)
        layout.addWidget(grp_advanced)
        self.appearance_toggle, _ = fold_section(grp_advanced, "Axis and appearance options")

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll, 1)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Add series")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setDefault(True)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setProperty("role","primary")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        self._populate_columns()
        finish_dialog(self, scroll_body=False)
        self.btn_color.setAutoDefault(False)
        self.btn_color.setDefault(False)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setDefault(True)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setProperty("role","primary")

    def _update_symbol_visibility(self):
        """Conditionally shows/hides features based on whether plot type uses lines or symbols."""
        plot_type = self.combo_plot_type.currentText()
        has_symbols = plot_type in ("scatter", "line_symbol", "errorbar")
        has_lines = plot_type in ("line", "line_symbol", "step", "spline", "errorbar", "area")
        self.lbl_marker.setVisible(has_symbols)
        self.combo_marker.setVisible(has_symbols)
        self.lbl_line_style.setVisible(has_lines)
        self.combo_line_style.setVisible(has_lines)

    def _populate_columns(self):
        self.combo_x_col.clear()
        self.combo_y_col.clear()
        self.combo_yerr_col.clear()

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

        self.combo_yerr_col.addItem("(None - No Error Bars)", None)

        x_candidate = 0
        y_candidate = 1 if sheet.column_count() > 1 else 0

        for i, col in enumerate(sheet.columns):
            label = f"Col {col.name}: {col.display_label}"
            self.combo_x_col.addItem(label, i)
            self.combo_y_col.addItem(label, i)
            self.combo_yerr_col.addItem(label, i)
            if col.role == ColumnRole.X:
                x_candidate = i
            elif col.role == ColumnRole.Y and i > x_candidate:
                y_candidate = i

        self.combo_x_col.setCurrentIndex(x_candidate)
        self.combo_y_col.setCurrentIndex(y_candidate)
        self._on_y_col_changed()

    def _on_y_col_changed(self):
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

        y_idx = self.combo_y_col.currentData()
        if y_idx is not None and 0 <= y_idx < len(sheet.columns):
            col = sheet.columns[y_idx]
            self.txt_label.setText(col.display_label)
            # Check adjacent Y error column
            err_idx = sheet.find_y_error_column_for(y_idx)
            if err_idx is not None:
                for ci in range(self.combo_yerr_col.count()):
                    if self.combo_yerr_col.itemData(ci) == err_idx:
                        self.combo_yerr_col.setCurrentIndex(ci)
                        break

    def _pick_color(self):
        c = QColorDialog.getColor(QColor("#0284c7"), self, "Select Curve Color")
        if c.isValid():
            self.selected_color = c.name()
            self.btn_color.setText(self.selected_color)
            lum = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
            txt_col = "#0f172a" if lum > 140 else "#ffffff"
            self.btn_color.setStyleSheet(
                f"background-color: {self.selected_color}; color: {txt_col}; font-weight: bold; border-radius: 4px;"
            )

    def _on_accept(self):
        data = self.combo_sheet.currentData()
        if not data:
            return
        wb_name, sheet_name = data
        x_idx = self.combo_x_col.currentData()
        y_idx = self.combo_y_col.currentData()
        if x_idx is None or y_idx is None:
            return
        yerr_idx = self.combo_yerr_col.currentData()
        label = self.txt_label.text().strip() or "Layer"
        pt = self.combo_plot_type.currentText()
        axis_mode = self.combo_axis.currentData()

        # Marker
        m_txt = self.combo_marker.currentText()
        marker = m_txt.split()[0] if m_txt != "none" else "none"

        # Line style
        ls_txt = self.combo_line_style.currentText()
        line_style = ls_txt.split()[0] if ls_txt != "none" else "none"

        layer_idx = 1 if axis_mode == "bottom_panel" else 0
        axis = "secondary" if axis_mode == "secondary" else "primary"

        if axis_mode == "bottom_panel":
            self.active_graph.layout_mode = "stacked_2x1"
        elif axis_mode == "secondary":
            if self.active_graph.layout_mode != "stacked_2x1":
                self.active_graph.layout_mode = "twin_x"
            if not self.active_graph.y2_title:
                self.active_graph.y2_title = label

        curve = CurveModel(
            source_workbook=wb_name,
            source_sheet=sheet_name,
            x_col_idx=x_idx,
            y_col_idx=y_idx,
            y_err_col_idx=yerr_idx,
            label=label,
            color=self.selected_color,
            line_style=line_style,
            marker=marker,
            plot_type="errorbar" if (yerr_idx is not None or pt == "errorbar") else pt,
            axis=axis,
            layer_index=layer_idx,
        )

        self.active_graph.add_curve(curve)
        self.accept()
