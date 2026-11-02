"""
Dynamic Property Inspector dock widget.
Context-sensitive: updates styling, axes, scales, and themes for Graphs;
and displays column metadata, quick stats, and roles for Worksheets.
"""

from typing import Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QCheckBox,
    QSlider, QPushButton, QColorDialog, QGroupBox, QScrollArea,
    QApplication
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor

from omnigraph.core.project import GraphModel, CurveModel
from omnigraph.core.worksheet import Worksheet, Column, ColumnRole
from omnigraph.graphing.themes import THEMES


class PropertyInspectorWidget(QWidget):
    """Dynamic right sidebar property editor."""

    graph_property_changed = pyqtSignal()
    worksheet_property_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_graph: Optional[GraphModel] = None
        self.active_worksheet: Optional[Worksheet] = None
        self.current_curve_idx: int = 0
        self.current_col_idx: int = 0

        self._init_ui()

    def sizeHint(self):
        from PyQt6.QtCore import QSize
        return QSize(320, 600)

    def minimumSizeHint(self):
        from PyQt6.QtCore import QSize
        return QSize(285, 380)

    def _init_ui(self):
        self.setObjectName("PropertyInspectorWidget")
        self.setMinimumWidth(285)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(2)

        self.tabs = QTabWidget(self)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.setElideMode(Qt.TextElideMode.ElideNone)
        main_layout.addWidget(self.tabs)

        # Tab 1: Curves / Series
        self.tab_curves = self._create_curves_tab()
        self.tabs.addTab(self.tab_curves, "Curves")

        # Tab 2: Axes & Scales
        self.tab_axes = self._create_axes_tab()
        self.tabs.addTab(self.tab_axes, "Axes")

        # Tab 3: Legend & Style
        self.tab_legend = self._create_legend_tab()
        self.tabs.addTab(self.tab_legend, "Legend")

        # Tab 4: Column Properties (for Worksheet)
        self.tab_column = self._create_column_tab()
        self.tabs.addTab(self.tab_column, "Column")

    def _create_curves_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Select Curve / Layer:"))
        self.combo_curve = QComboBox()
        self.combo_curve.currentIndexChanged.connect(self._on_curve_selection_changed)
        layout.addWidget(self.combo_curve)

        # Layer controls: split into 2 rows to prevent button label truncation at 125%/150% scaling
        # Row 1: Visibility checkbox and Remove button
        row_visibility = QHBoxLayout()
        self.chk_curve_visible = QCheckBox("Visible")
        self.chk_curve_visible.setChecked(True)
        self.chk_curve_visible.toggled.connect(self._toggle_curve_visibility)
        row_visibility.addWidget(self.chk_curve_visible)
        row_visibility.addStretch()

        self.btn_remove_curve = QPushButton("🗑️ Remove")
        self.btn_remove_curve.setToolTip("Remove this curve from graph")
        self.btn_remove_curve.clicked.connect(self._remove_curve)
        row_visibility.addWidget(self.btn_remove_curve)
        layout.addLayout(row_visibility)

        # Row 2: Z-order reordering buttons (Up / Down)
        row_reorder = QHBoxLayout()
        self.btn_move_up = QPushButton("▲ Up")
        self.btn_move_up.setToolTip("Move layer up (earlier z-order)")
        self.btn_move_up.clicked.connect(self._move_curve_up)
        row_reorder.addWidget(self.btn_move_up)

        self.btn_move_down = QPushButton("▼ Down")
        self.btn_move_down.setToolTip("Move layer down (later z-order)")
        self.btn_move_down.clicked.connect(self._move_curve_down)
        row_reorder.addWidget(self.btn_move_down)
        layout.addLayout(row_reorder)

        # Local aliases for backwards compatibility
        btn_move_up = self.btn_move_up
        btn_move_down = self.btn_move_down
        btn_remove_curve = self.btn_remove_curve

        # Curve properties
        grp = QGroupBox("Series Appearance")
        gl = QVBoxLayout(grp)

        gl.addWidget(QLabel("Legend Label:"))
        self.txt_curve_label = QLineEdit()
        self.txt_curve_label.textChanged.connect(self._apply_curve_changes)
        gl.addWidget(self.txt_curve_label)

        gl.addWidget(QLabel("Plot Type:"))
        self.combo_plot_type = QComboBox()
        self.combo_plot_type.addItems([
            "scatter", "line", "line_symbol", "step", "spline",
            "bar", "hbar", "area", "errorbar", "histogram",
            "box", "box_whisker", "box_jitter", "violin", "violin_jitter", "jitter"
        ])
        self.combo_plot_type.currentTextChanged.connect(self._apply_curve_changes)
        gl.addWidget(self.combo_plot_type)

        # Color
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Color:"))
        self.btn_curve_color = QPushButton("Pick Color")
        self.btn_curve_color.clicked.connect(self._pick_curve_color)
        color_layout.addWidget(self.btn_curve_color)
        gl.addLayout(color_layout)

        # Line style & width container (conditionally shown if plot type uses lines)
        self.container_line = QWidget()
        line_layout = QVBoxLayout(self.container_line)
        line_layout.setContentsMargins(0, 0, 0, 0)
        line_layout.setSpacing(4)

        line_layout.addWidget(QLabel("Line Style:"))
        self.combo_line_style = QComboBox()
        self.combo_line_style.addItems(["- (Solid)", "-- (Dashed)", "-. (Dash-Dot)", ": (Dotted)", "none"])
        self.combo_line_style.currentTextChanged.connect(self._apply_curve_changes)
        line_layout.addWidget(self.combo_line_style)

        lw_layout = QHBoxLayout()
        lw_layout.addWidget(QLabel("Line Width:"))
        self.spn_line_width = QDoubleSpinBox()
        self.spn_line_width.setRange(0.5, 12.0)
        self.spn_line_width.setSingleStep(0.5)
        self.spn_line_width.setValue(1.8)
        self.spn_line_width.valueChanged.connect(self._apply_curve_changes)
        lw_layout.addWidget(self.spn_line_width)
        line_layout.addLayout(lw_layout)

        gl.addWidget(self.container_line)

        # Marker symbol & size container (conditionally shown if plot type uses symbols)
        self.container_marker = QWidget()
        marker_layout = QVBoxLayout(self.container_marker)
        marker_layout.setContentsMargins(0, 0, 0, 0)
        marker_layout.setSpacing(4)

        marker_layout.addWidget(QLabel("Symbol Marker:"))
        self.combo_marker = QComboBox()
        self.combo_marker.addItems(["o (Circle)", "s (Square)", "^ (Triangle Up)", "v (Triangle Down)", "D (Diamond)", "* (Star)", "+ (Plus)", "x (Cross)", "none"])
        self.combo_marker.currentTextChanged.connect(self._apply_curve_changes)
        marker_layout.addWidget(self.combo_marker)

        ms_layout = QHBoxLayout()
        ms_layout.addWidget(QLabel("Symbol Size:"))
        self.spn_marker_size = QDoubleSpinBox()
        self.spn_marker_size.setRange(1.0, 25.0)
        self.spn_marker_size.setValue(6.0)
        self.spn_marker_size.valueChanged.connect(self._apply_curve_changes)
        ms_layout.addWidget(self.spn_marker_size)
        marker_layout.addLayout(ms_layout)

        gl.addWidget(self.container_marker)

        # Layer / Axis assignment
        gl.addWidget(QLabel("Layer / Axis Assignment:"))
        self.combo_axis_assign = QComboBox()
        self.combo_axis_assign.addItems(["primary (Left Y)", "secondary (Right Y)", "bottom_panel (Bottom Subplot)"])
        self.combo_axis_assign.currentTextChanged.connect(self._apply_curve_changes)
        gl.addWidget(self.combo_axis_assign)

        # Layer Offsets (Spectroscopy Waterfall & Custom Stagger)
        grp_offsets = QGroupBox("Layer Offsets (Waterfall / Stagger)")
        gl_off = QVBoxLayout(grp_offsets)

        row_yoff = QHBoxLayout()
        row_yoff.addWidget(QLabel("Y-Offset (ΔY):"))
        self.spn_y_offset = QDoubleSpinBox()
        self.spn_y_offset.setRange(-1e8, 1e8)
        self.spn_y_offset.setSingleStep(1.0)
        self.spn_y_offset.setValue(0.0)
        self.spn_y_offset.valueChanged.connect(self._apply_curve_changes)
        row_yoff.addWidget(self.spn_y_offset)
        gl_off.addLayout(row_yoff)

        row_xoff = QHBoxLayout()
        row_xoff.addWidget(QLabel("X-Offset (ΔX):"))
        self.spn_x_offset = QDoubleSpinBox()
        self.spn_x_offset.setRange(-1e8, 1e8)
        self.spn_x_offset.setSingleStep(1.0)
        self.spn_x_offset.setValue(0.0)
        self.spn_x_offset.valueChanged.connect(self._apply_curve_changes)
        row_xoff.addWidget(self.spn_x_offset)
        gl_off.addLayout(row_xoff)

        gl.addWidget(grp_offsets)

        layout.addWidget(grp)
        layout.addStretch()
        scroll.setWidget(w)
        return scroll

    def _create_axes_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(8)

        # Titles
        grp_titles = QGroupBox("Axis Titles")
        tl = QVBoxLayout(grp_titles)
        tl.addWidget(QLabel("Graph Title:"))
        self.txt_graph_title = QLineEdit()
        self.txt_graph_title.textChanged.connect(self._apply_axis_changes)
        tl.addWidget(self.txt_graph_title)

        tl.addWidget(QLabel("X Axis Title:"))
        self.txt_x_title = QLineEdit()
        self.txt_x_title.textChanged.connect(self._apply_axis_changes)
        tl.addWidget(self.txt_x_title)

        tl.addWidget(QLabel("Left Y Axis Title:"))
        self.txt_y_title = QLineEdit()
        self.txt_y_title.textChanged.connect(self._apply_axis_changes)
        tl.addWidget(self.txt_y_title)

        tl.addWidget(QLabel("Right Y Axis Title (Twin Y):"))
        self.txt_y2_title = QLineEdit()
        self.txt_y2_title.textChanged.connect(self._apply_axis_changes)
        tl.addWidget(self.txt_y2_title)
        layout.addWidget(grp_titles)

        # Scales & Grids
        grp_scales = QGroupBox("Scales & Ticks")
        sl = QVBoxLayout(grp_scales)

        sl.addWidget(QLabel("X Scale:"))
        self.combo_x_scale = QComboBox()
        self.combo_x_scale.addItems(["linear", "log10", "ln"])
        self.combo_x_scale.currentTextChanged.connect(self._apply_axis_changes)
        sl.addWidget(self.combo_x_scale)

        sl.addWidget(QLabel("Y Scale:"))
        self.combo_y_scale = QComboBox()
        self.combo_y_scale.addItems(["linear", "log10", "ln"])
        self.combo_y_scale.currentTextChanged.connect(self._apply_axis_changes)
        sl.addWidget(self.combo_y_scale)

        self.chk_box_frame = QCheckBox("Origin Boxed Frame (All 4 sides)")
        self.chk_box_frame.setChecked(True)
        self.chk_box_frame.toggled.connect(self._apply_axis_changes)
        sl.addWidget(self.chk_box_frame)

        sl.addWidget(QLabel("Tick Direction:"))
        self.combo_tick_dir = QComboBox()
        self.combo_tick_dir.addItems(["in", "out", "inout", "none"])
        self.combo_tick_dir.currentTextChanged.connect(self._apply_axis_changes)
        sl.addWidget(self.combo_tick_dir)

        self.chk_grid_major = QCheckBox("Show Major Gridlines")
        self.chk_grid_major.toggled.connect(self._apply_axis_changes)
        sl.addWidget(self.chk_grid_major)

        self.chk_grid_minor = QCheckBox("Show Minor Gridlines")
        self.chk_grid_minor.toggled.connect(self._apply_axis_changes)
        sl.addWidget(self.chk_grid_minor)

        layout.addWidget(grp_scales)
        layout.addStretch()
        scroll.setWidget(w)
        return scroll

    def _create_legend_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(8)

        self.chk_legend_show = QCheckBox("Display Legend")
        self.chk_legend_show.setChecked(True)
        self.chk_legend_show.toggled.connect(self._apply_legend_changes)
        layout.addWidget(self.chk_legend_show)

        layout.addWidget(QLabel("Position:"))
        self.combo_legend_loc = QComboBox()
        self.combo_legend_loc.addItems([
            "best", "upper right", "upper left", "lower right", "lower left", "center right", "center left", "outside right", "center"
        ])
        self.combo_legend_loc.currentTextChanged.connect(self._apply_legend_changes)
        layout.addWidget(self.combo_legend_loc)

        self.chk_legend_frame = QCheckBox("Draw Legend Box Frame")
        self.chk_legend_frame.setChecked(True)
        self.chk_legend_frame.toggled.connect(self._apply_legend_changes)
        layout.addWidget(self.chk_legend_frame)

        fs_layout = QHBoxLayout()
        fs_layout.addWidget(QLabel("Font Size:"))
        self.spn_legend_fs = QSpinBox()
        self.spn_legend_fs.setRange(6, 24)
        self.spn_legend_fs.setValue(10)
        self.spn_legend_fs.valueChanged.connect(self._apply_legend_changes)
        fs_layout.addWidget(self.spn_legend_fs)
        layout.addLayout(fs_layout)

        layout.addStretch()
        scroll.setWidget(w)
        return scroll

    def _create_column_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Select Column:"))
        self.combo_cols = QComboBox()
        self.combo_cols.currentIndexChanged.connect(self._on_col_selection_changed)
        layout.addWidget(self.combo_cols)

        grp = QGroupBox("Column Metadata")
        cl = QVBoxLayout(grp)

        cl.addWidget(QLabel("Column Name:"))
        self.txt_col_name = QLineEdit()
        self.txt_col_name.setPlaceholderText("e.g. Time, Absorbance...")
        self.txt_col_name.textChanged.connect(self._apply_col_changes)
        cl.addWidget(self.txt_col_name)
        self.txt_col_long_name = self.txt_col_name  # Backwards compatibility alias

        cl.addWidget(QLabel("Units:"))
        self.txt_col_units = QLineEdit()
        self.txt_col_units.textChanged.connect(self._apply_col_changes)
        cl.addWidget(self.txt_col_units)

        cl.addWidget(QLabel("Comments:"))
        self.txt_col_comments = QLineEdit()
        self.txt_col_comments.textChanged.connect(self._apply_col_changes)
        cl.addWidget(self.txt_col_comments)

        cl.addWidget(QLabel("Designation (Role):"))
        self.combo_col_role = QComboBox()
        for r in ColumnRole:
            self.combo_col_role.addItem(r.value)
        self.combo_col_role.currentTextChanged.connect(self._apply_col_changes)
        cl.addWidget(self.combo_col_role)

        layout.addWidget(grp)

        # Quick Stats Card
        grp_stats = QGroupBox("Quick Statistics")
        self.lbl_col_stats = QLabel("No column selected")
        self.lbl_col_stats.setTextFormat(Qt.TextFormat.RichText)
        ql = QVBoxLayout(grp_stats)
        ql.addWidget(self.lbl_col_stats)
        layout.addWidget(grp_stats)

        layout.addStretch()
        scroll.setWidget(w)
        return scroll

    def set_active_graph(self, graph: GraphModel):
        self.active_graph = graph
        self.tabs.setCurrentIndex(0)
        self._populate_graph_controls()

    def set_active_worksheet(self, ws: Worksheet):
        self.active_worksheet = ws
        self.tabs.setCurrentIndex(3)
        self._populate_worksheet_controls()

    def _populate_graph_controls(self):
        if not self.active_graph:
            return

        g = self.active_graph
        self.combo_curve.blockSignals(True)
        self.combo_curve.clear()
        for i, c in enumerate(g.curves):
            self.combo_curve.addItem(f"{i + 1}: {c.label}")
        self.combo_curve.blockSignals(False)

        if g.curves:
            self._load_curve_into_ui(g.curves[0])

        # Axes (block signals during population)
        self.txt_graph_title.blockSignals(True)
        self.txt_graph_title.setText(g.title_text)
        self.txt_graph_title.blockSignals(False)

        self.txt_x_title.blockSignals(True)
        self.txt_x_title.setText(g.x_title)
        self.txt_x_title.blockSignals(False)

        self.txt_y_title.blockSignals(True)
        self.txt_y_title.setText(g.y_title)
        self.txt_y_title.blockSignals(False)

        self.txt_y2_title.blockSignals(True)
        self.txt_y2_title.setText(g.y2_title)
        self.txt_y2_title.blockSignals(False)

        self.combo_x_scale.blockSignals(True)
        self.combo_x_scale.setCurrentText(g.x_scale)
        self.combo_x_scale.blockSignals(False)

        self.combo_y_scale.blockSignals(True)
        self.combo_y_scale.setCurrentText(g.y_scale)
        self.combo_y_scale.blockSignals(False)

        self.chk_box_frame.blockSignals(True)
        self.chk_box_frame.setChecked(g.box_frame)
        self.chk_box_frame.blockSignals(False)

        self.combo_tick_dir.blockSignals(True)
        self.combo_tick_dir.setCurrentText(g.tick_direction)
        self.combo_tick_dir.blockSignals(False)

        self.chk_grid_major.blockSignals(True)
        self.chk_grid_major.setChecked(g.show_grid_major)
        self.chk_grid_major.blockSignals(False)

        self.chk_grid_minor.blockSignals(True)
        self.chk_grid_minor.setChecked(g.show_grid_minor)
        self.chk_grid_minor.blockSignals(False)

        # Legend (block signals during population)
        self.chk_legend_show.blockSignals(True)
        self.chk_legend_show.setChecked(g.legend_show)
        self.chk_legend_show.blockSignals(False)

        self.combo_legend_loc.blockSignals(True)
        self.combo_legend_loc.setCurrentText(g.legend_location)
        self.combo_legend_loc.blockSignals(False)

        self.chk_legend_frame.blockSignals(True)
        self.chk_legend_frame.setChecked(g.legend_frame)
        self.chk_legend_frame.blockSignals(False)

        self.spn_legend_fs.blockSignals(True)
        self.spn_legend_fs.setValue(int(g.legend_font_size))
        self.spn_legend_fs.blockSignals(False)

    def _load_curve_into_ui(self, curve: CurveModel):
        self.txt_curve_label.blockSignals(True)
        self.txt_curve_label.setText(curve.label)
        self.txt_curve_label.blockSignals(False)

        self.combo_plot_type.blockSignals(True)
        self.combo_plot_type.setCurrentText(curve.plot_type)
        self.combo_plot_type.blockSignals(False)

        qcol = QColor(curve.color)
        lum = 0.299 * qcol.red() + 0.587 * qcol.green() + 0.114 * qcol.blue() if qcol.isValid() else 0
        txt_col = "#0f172a" if lum > 140 else "#ffffff"
        self.btn_curve_color.setStyleSheet(
            f"background-color: {curve.color}; color: {txt_col}; font-weight: bold; border: 2px solid #475569; border-radius: 4px; padding: 4px;"
        )

        self.spn_line_width.blockSignals(True)
        self.spn_line_width.setValue(curve.line_width)
        self.spn_line_width.blockSignals(False)

        self.spn_marker_size.blockSignals(True)
        self.spn_marker_size.setValue(curve.marker_size)
        self.spn_marker_size.blockSignals(False)

        self.chk_curve_visible.blockSignals(True)
        self.chk_curve_visible.setChecked(getattr(curve, "visible", True))
        self.chk_curve_visible.blockSignals(False)

        self.combo_axis_assign.blockSignals(True)
        if getattr(curve, "layer_index", 0) == 1:
            self.combo_axis_assign.setCurrentText("bottom_panel (Bottom Subplot)")
        elif curve.axis == "secondary":
            self.combo_axis_assign.setCurrentText("secondary (Right Y)")
        else:
            self.combo_axis_assign.setCurrentText("primary (Left Y)")
        self.combo_axis_assign.blockSignals(False)

        self.spn_y_offset.blockSignals(True)
        self.spn_y_offset.setValue(getattr(curve, "y_offset", 0.0))
        self.spn_y_offset.blockSignals(False)

        self.spn_x_offset.blockSignals(True)
        self.spn_x_offset.setValue(getattr(curve, "x_offset", 0.0))
        self.spn_x_offset.blockSignals(False)

        # Conditionally show features only if supported by the active plot type
        has_lines = curve.plot_type in ("line", "line_symbol", "step", "spline", "errorbar", "area")
        has_symbols = curve.plot_type in ("scatter", "line_symbol", "errorbar")
        self.container_line.setVisible(has_lines)
        self.container_marker.setVisible(has_symbols)

    def _toggle_curve_visibility(self, checked: bool):
        if self.active_graph and 0 <= self.current_curve_idx < len(self.active_graph.curves):
            self.active_graph.curves[self.current_curve_idx].visible = checked
            self.graph_property_changed.emit()

    def _move_curve_up(self):
        if self.active_graph and self.active_graph.move_curve_up(self.current_curve_idx):
            self.current_curve_idx = max(0, self.current_curve_idx - 1)
            self._populate_graph_controls()
            self.combo_curve.setCurrentIndex(self.current_curve_idx)
            self.graph_property_changed.emit()

    def _move_curve_down(self):
        if self.active_graph and self.active_graph.move_curve_down(self.current_curve_idx):
            self.current_curve_idx = min(len(self.active_graph.curves) - 1, self.current_curve_idx + 1)
            self._populate_graph_controls()
            self.combo_curve.setCurrentIndex(self.current_curve_idx)
            self.graph_property_changed.emit()

    def _remove_curve(self):
        if self.active_graph and 0 <= self.current_curve_idx < len(self.active_graph.curves):
            self.active_graph.remove_curve_at(self.current_curve_idx)
            self.current_curve_idx = max(0, self.current_curve_idx - 1)
            self._populate_graph_controls()
            self.graph_property_changed.emit()

    def _on_curve_selection_changed(self, idx: int):
        if self.active_graph and 0 <= idx < len(self.active_graph.curves):
            self.current_curve_idx = idx
            self._load_curve_into_ui(self.active_graph.curves[idx])

    def _pick_curve_color(self):
        if not self.active_graph or not self.active_graph.curves:
            return
        curve = self.active_graph.curves[self.current_curve_idx]
        color = QColorDialog.getColor(QColor(curve.color), self, "Select Curve Color")
        if color.isValid():
            curve.color = color.name()
            qcol = QColor(curve.color)
            lum = 0.299 * qcol.red() + 0.587 * qcol.green() + 0.114 * qcol.blue()
            txt_col = "#0f172a" if lum > 140 else "#ffffff"
            self.btn_curve_color.setStyleSheet(
                f"background-color: {curve.color}; color: {txt_col}; font-weight: bold; border: 2px solid #475569; border-radius: 4px;"
            )
            self.graph_property_changed.emit()

    def _apply_curve_changes(self):
        if not self.active_graph or not self.active_graph.curves:
            return
        if self.current_curve_idx >= len(self.active_graph.curves):
            return

        curve = self.active_graph.curves[self.current_curve_idx]
        curve.label = self.txt_curve_label.text()
        curve.plot_type = self.combo_plot_type.currentText()
        has_lines = curve.plot_type in ("line", "line_symbol", "step", "spline", "errorbar", "area")
        has_symbols = curve.plot_type in ("scatter", "line_symbol", "errorbar")
        self.container_line.setVisible(has_lines)
        self.container_marker.setVisible(has_symbols)

        curve.line_width = self.spn_line_width.value()
        curve.marker_size = self.spn_marker_size.value()

        # Marker style
        m_txt = self.combo_marker.currentText()
        curve.marker = m_txt.split()[0] if m_txt != "none" else "none"

        # Line style
        ls_txt = self.combo_line_style.currentText()
        curve.line_style = ls_txt.split()[0] if ls_txt != "none" else "none"

        axis_str = self.combo_axis_assign.currentText()
        if "bottom_panel" in axis_str:
            curve.layer_index = 1
            curve.axis = "primary"
            self.active_graph.layout_mode = "stacked_2x1"
        elif "secondary" in axis_str:
            curve.layer_index = 0
            curve.axis = "secondary"
        else:
            curve.layer_index = 0
            curve.axis = "primary"

        curve.y_offset = float(self.spn_y_offset.value())
        curve.x_offset = float(self.spn_x_offset.value())

        self.graph_property_changed.emit()

    def _apply_axis_changes(self):
        if not self.active_graph:
            return
        g = self.active_graph
        g.title_text = self.txt_graph_title.text()
        g.x_title = self.txt_x_title.text()
        g.y_title = self.txt_y_title.text()
        g.y2_title = self.txt_y2_title.text()
        g.x_scale = self.combo_x_scale.currentText()
        g.y_scale = self.combo_y_scale.currentText()
        g.box_frame = self.chk_box_frame.isChecked()
        g.tick_direction = self.combo_tick_dir.currentText()
        g.show_grid_major = self.chk_grid_major.isChecked()
        g.show_grid_minor = self.chk_grid_minor.isChecked()
        self.graph_property_changed.emit()

    def _apply_legend_changes(self):
        if not self.active_graph:
            return
        g = self.active_graph
        g.legend_show = self.chk_legend_show.isChecked()
        loc = self.combo_legend_loc.currentText().strip()
        if loc:
            g.legend_location = loc
        g.legend_frame = self.chk_legend_frame.isChecked()
        g.legend_font_size = float(self.spn_legend_fs.value())
        self.graph_property_changed.emit()

    def _populate_worksheet_controls(self):
        if not self.active_worksheet:
            return

        ws = self.active_worksheet
        self.combo_cols.blockSignals(True)
        self.combo_cols.clear()
        for i, col in enumerate(ws.columns):
            self.combo_cols.addItem(f"{col.name} ({col.role.value}): {col.display_label}")
        self.combo_cols.blockSignals(False)

        if ws.columns:
            self._load_col_into_ui(ws.columns[0])

    def _load_col_into_ui(self, col: Column):
        self.txt_col_name.blockSignals(True)
        self.txt_col_name.setText(col.long_name if col.long_name else col.name)
        self.txt_col_name.blockSignals(False)

        self.txt_col_units.blockSignals(True)
        self.txt_col_units.setText(col.units)
        self.txt_col_units.blockSignals(False)

        self.txt_col_comments.blockSignals(True)
        self.txt_col_comments.setText(col.comments)
        self.txt_col_comments.blockSignals(False)

        self.combo_col_role.blockSignals(True)
        self.combo_col_role.setCurrentText(col.role.value)
        self.combo_col_role.blockSignals(False)

        # Compute quick stats
        s = col.stats()
        app = QApplication.instance()
        is_dark = getattr(app, "is_dark_theme", False)
        text_color = "#cdd6f4" if is_dark else "#0f172a"
        muted_color = "#a6adc8" if is_dark else "#64748b"
        if s["n"] > 0:
            html = f"""
            <table style='width: 100%; color: {text_color}; font-size: 11px;'>
            <tr><td><b>N Points:</b></td><td align='right'><b>{s['n']}</b></td></tr>
            <tr><td><b>Mean:</b></td><td align='right'>{s['mean']:.4g}</td></tr>
            <tr><td><b>Std Dev:</b></td><td align='right'>{s['std']:.4g}</td></tr>
            <tr><td><b>Min:</b></td><td align='right'>{s['min']:.4g}</td></tr>
            <tr><td><b>Median:</b></td><td align='right'>{s['median']:.4g}</td></tr>
            <tr><td><b>Max:</b></td><td align='right'>{s['max']:.4g}</td></tr>
            <tr><td><b>Sum:</b></td><td align='right'>{s['sum']:.4g}</td></tr>
            </table>
            """
        else:
            html = f"<i style='color: {muted_color};'>No numeric data</i>"
        self.lbl_col_stats.setText(html)

    def _on_col_selection_changed(self, idx: int):
        if self.active_worksheet and 0 <= idx < len(self.active_worksheet.columns):
            self.current_col_idx = idx
            self._load_col_into_ui(self.active_worksheet.columns[idx])

    def _apply_col_changes(self):
        if not self.active_worksheet or not self.active_worksheet.columns:
            return
        if self.current_col_idx >= len(self.active_worksheet.columns):
            return

        col = self.active_worksheet.columns[self.current_col_idx]
        col.long_name = self.txt_col_name.text().strip()
        col.units = self.txt_col_units.text()
        col.comments = self.txt_col_comments.text()
        col.role = ColumnRole(self.combo_col_role.currentText())

        # Update column combo box item text to reflect new name/role
        self.combo_cols.blockSignals(True)
        self.combo_cols.setItemText(self.current_col_idx, f"{col.name} ({col.role.value}): {col.display_label}")
        self.combo_cols.blockSignals(False)

        self.worksheet_property_changed.emit()
