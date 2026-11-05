"""
Graph view widget containing OmniCanvas, quick styling controls, tool toggles, and export buttons.
"""

import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QToolBar, QToolButton,
    QComboBox, QLabel, QMenu, QInputDialog, QMessageBox, QToolTip,
    QLineEdit, QScrollArea, QSizePolicy, QSplitter, QFormLayout, QTabWidget, QCheckBox, QDoubleSpinBox
)
from PyQt6.QtCore import pyqtSignal, Qt, QPoint, QRect
from PyQt6.QtGui import QAction, QKeySequence, QShortcut

from omnigraph.core.project import GraphModel, Project
from omnigraph.graphing.canvas import OmniCanvas
from omnigraph.graphing.themes import THEMES
from omnigraph.core.plot_editing import PLOT_GROUPS, change_graph_plot_type
from omnigraph.ui.styles.design import icon
from omnigraph.analysis.statistics import StatisticsAnalyzer


class GraphViewWidget(QWidget):
    """Hosts an interactive graph with quick tools and export controls."""

    coordinates_changed = pyqtSignal(float, float)
    request_curve_fit = pyqtSignal(str)  # fit_type: 'linear', 'poly', 'gaussian', 'exp_decay', 'hill'
    range_selected = pyqtSignal(float, float)  # xmin, xmax
    labels_changed = pyqtSignal()
    curves_changed = pyqtSignal()
    request_jump_to_sheet = pyqtSignal(str, str)  # (sheet_name, workbook_name)
    request_replace_data = pyqtSignal(bool)  # duplicate first

    def __init__(self, graph_model: GraphModel, project: Project, parent=None):
        super().__init__(parent)
        self.graph_model = graph_model
        self.project = project
        self._interface_scale = 1.0

        self._init_ui()

    def minimumSizeHint(self):
        from PyQt6.QtCore import QSize
        return QSize(250, 180)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Quick Graph Action Bar using QToolBar (handles overflows gracefully without text clipping)
        bar = QToolBar()
        bar.setMovable(False)
        bar.setFloatable(False)
        bar.setStyleSheet("QToolBar { border: none; padding: 2px 4px; background: transparent; }")

        # Theme Selector
        lbl_th = QLabel("Theme:")
        lbl_th.setStyleSheet("font-weight: 600; padding-right: 2px;")
        bar.addWidget(lbl_th)

        self.combo_theme = QComboBox()
        self.combo_theme.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_theme.setMinimumContentsLength(14)
        self.combo_theme.addItems(list(THEMES.keys()))
        self.combo_theme.setCurrentText(self.graph_model.theme)
        self.combo_theme.currentTextChanged.connect(self._on_theme_changed)

        bar.addSeparator()

        # Interactive Tools
        lbl_tl = QLabel("Tool:")
        lbl_tl.setStyleSheet("font-weight: 600; padding-right: 2px;")
        bar.addWidget(lbl_tl)

        self.btn_pointer = QToolButton()
        self.btn_pointer.setText("Pointer")
        self.btn_pointer.setCheckable(True)
        self.btn_pointer.setChecked(True)
        self.btn_pointer.clicked.connect(lambda: self._select_tool("pointer"))
        bar.addWidget(self.btn_pointer)

        self.btn_crosshair = QToolButton()
        self.btn_crosshair.setText("Reader")
        self.btn_crosshair.setToolTip("Data Reader Crosshair: Inspect data curve values in real time")
        self.btn_crosshair.setCheckable(True)
        self.btn_crosshair.clicked.connect(lambda: self._select_tool("data_reader"))
        bar.addWidget(self.btn_crosshair)

        self.btn_range = QToolButton()
        self.btn_range.setText("ROI")
        self.btn_range.setToolTip("ROI Range: Select Region of Interest on X axis for fitting/integration")
        self.btn_range.setCheckable(True)
        self.btn_range.clicked.connect(lambda: self._select_tool("range_selector"))
        bar.addWidget(self.btn_range)

        bar.addSeparator()

        # Key / Legend Button with quick menu
        btn_key = QToolButton()
        self.legend_menu_button = btn_key
        btn_key.setText("Legend")
        btn_key.setToolTip("Edit Key / Legend series labels, placement, and appearance")
        btn_key.setText("Series and legend…")
        btn_key.setToolTip("Edit series names, colors, and legend appearance")
        btn_key.clicked.connect(self._open_legend_editor)

        # Add Annotation Dropdown
        btn_ann = QToolButton()
        self.annotation_menu_button = btn_ann
        btn_ann.setText("Add annotation")
        btn_ann.setToolTip("Add text note, reference lines, or significance brackets")
        btn_ann.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        ann_menu = QMenu(btn_ann)
        ann_menu.addAction("⭐ Add Significance Bracket (*, **, ns)...", self._prompt_significance_bracket)
        ann_menu.addSeparator()
        ann_menu.addAction("Add Text Note...", self._add_text_annotation)
        ann_menu.addAction("Add Horizontal Reference Line (y = c)...", self._add_ref_line_h)
        ann_menu.addAction("Add Vertical Reference Line (x = c)...", self._add_ref_line_v)
        btn_ann.setMenu(ann_menu)

        from PyQt6.QtWidgets import QSizePolicy
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        bar.addWidget(spacer)

        # Keep attributes for backward compatibility
        from PyQt6.QtGui import QAction
        self.btn_copy = QToolButton()
        self.btn_copy.hide()
        self.btn_copy.clicked.connect(self._copy_to_clipboard)
        self.act_toggle_wf = QAction(self)
        self.act_toggle_wf.setCheckable(True)
        self.act_toggle_wf.setChecked(getattr(self.graph_model, "waterfall_enabled", False))
        self.act_toggle_wf.triggered.connect(self._toggle_waterfall)

        layout.addWidget(bar)

        # Linked Data Sources Bar (shows which table is plotted with 1-click jump button)
        self.source_bar = QWidget(self)
        self.source_bar.setObjectName("LinkedSourceBar")
        self.source_bar_layout = QHBoxLayout(self.source_bar)
        self.source_bar_layout.setContentsMargins(6, 2, 6, 2)
        self.source_bar_layout.setSpacing(6)
        layout.addWidget(self.source_bar)

        # Quick In-Line Labels Bar (Compact 2-row QGridLayout)
        self.label_bar = QWidget(self)
        self.label_bar.setObjectName("QuickLabelBar")
        lbl_layout = QGridLayout(self.label_bar)
        lbl_layout.setContentsMargins(6, 2, 6, 2)
        lbl_layout.setSpacing(6)

        # Row 0: Title, Panel Autograph, Right-Y, Apply button
        lbl_title = QLabel("Title:")
        lbl_layout.addWidget(lbl_title, 0, 0)
        self.txt_quick_title = QLineEdit(self.graph_model.title_text or "")
        self.txt_quick_title.setPlaceholderText("Graph Title")
        self.txt_quick_title.setToolTip("Edit Graph Title - press Enter to apply")
        self.txt_quick_title.editingFinished.connect(self._on_quick_label_edited)
        lbl_layout.addWidget(self.txt_quick_title, 0, 1)

        lbl_panel = QLabel("🏷️ Panel:")
        lbl_panel.setToolTip("Quick autograph panel label (top-left corner of publication figures)")
        lbl_layout.addWidget(lbl_panel, 0, 2)

        self.combo_quick_panel = QComboBox()
        self.combo_quick_panel.setEditable(True)
        self.combo_quick_panel.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_quick_panel.setMinimumContentsLength(6)
        self.combo_quick_panel.addItems(["None", "(A)", "(B)", "(C)", "(D)", "(E)", "(F)", "A", "B", "C", "D", "Figure 1", "Fig. 1"])
        cur_panel = getattr(self.graph_model, "panel_label", "")
        self.combo_quick_panel.setCurrentText(cur_panel if cur_panel else "None")
        self.combo_quick_panel.currentTextChanged.connect(self._on_quick_panel_changed)
        lbl_layout.addWidget(self.combo_quick_panel, 0, 3)

        self.lbl_quick_y2 = QLabel("Right Y:")
        lbl_layout.addWidget(self.lbl_quick_y2, 0, 4)
        self.txt_quick_y2 = QLineEdit(self.graph_model.y2_title or "")
        self.txt_quick_y2.setPlaceholderText("Right Y Title")
        self.txt_quick_y2.editingFinished.connect(self._on_quick_label_edited)
        lbl_layout.addWidget(self.txt_quick_y2, 0, 5)

        has_y2 = any(c.axis == "secondary" for c in self.graph_model.curves)
        self.lbl_quick_y2.setVisible(has_y2)
        self.txt_quick_y2.setVisible(has_y2)

        btn_apply = QToolButton()
        btn_apply.setText("✓ Apply")
        btn_apply.setToolTip("Apply label edits immediately")
        btn_apply.clicked.connect(self._on_quick_label_edited)
        lbl_layout.addWidget(btn_apply, 0, 6)

        # Row 1: X Axis, Left Y Axis, More button
        lbl_x = QLabel("↔️ X:")
        lbl_layout.addWidget(lbl_x, 1, 0)
        self.txt_quick_x = QLineEdit(self.graph_model.x_title or "")
        self.txt_quick_x.setPlaceholderText("X Axis Title")
        self.txt_quick_x.setToolTip("Edit X-Axis Label - press Enter to apply")
        self.txt_quick_x.editingFinished.connect(self._on_quick_label_edited)
        lbl_layout.addWidget(self.txt_quick_x, 1, 1)

        lbl_y = QLabel("↕️ Y:")
        lbl_layout.addWidget(lbl_y, 1, 2)
        self.txt_quick_y = QLineEdit(self.graph_model.y_title or "")
        self.txt_quick_y.setPlaceholderText("Left Y Axis Title")
        self.txt_quick_y.setToolTip("Edit Left Y-Axis Label - press Enter to apply")
        self.txt_quick_y.editingFinished.connect(self._on_quick_label_edited)
        lbl_layout.addWidget(self.txt_quick_y, 1, 3)

        btn_more = QToolButton()
        btn_more.setText("✏️ All...")
        btn_more.setToolTip("Edit all titles, units, and curve labels (F2)")
        btn_more.clicked.connect(self._open_edit_labels_dialog)
        lbl_layout.addWidget(btn_more, 1, 6)

        layout.addWidget(self.label_bar)

        # Embedded Canvas
        self.canvas_widget = OmniCanvas(self.graph_model, self.project, self)
        self.canvas_widget.coordinates_changed.connect(self.coordinates_changed)
        self.canvas_widget.range_selected.connect(self.range_selected)
        self.canvas_widget.labels_changed.connect(self.labels_changed)
        self.canvas_widget.labels_changed.connect(self._sync_quick_labels)
        self.canvas_widget.files_dropped.connect(self._on_files_dropped)
        self.canvas_widget.point_mask_toggled.connect(self._on_point_mask_toggled)
        self.canvas_widget.request_significance_bracket.connect(self._prompt_significance_bracket)
        layout.addWidget(self.canvas_widget)

        # Wire Ctrl+C shortcut to copy graph when focused on graph tab
        self.shortcut_copy = QShortcut(QKeySequence.StandardKey.Copy, self)
        self.shortcut_copy.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_copy.activated.connect(self._copy_to_clipboard)

        # Wire F2 shortcut to open QuickLabelsDialog
        self.shortcut_labels = QShortcut(QKeySequence(Qt.Key.Key_F2), self)
        self.shortcut_labels.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_labels.activated.connect(self._open_edit_labels_dialog)

        self._sync_quick_labels()
        self._update_source_bar()
        self._build_chart_workspace(layout, bar)

    def _build_chart_workspace(self, layout, legacy_bar):
        """A figure stage with an optional, responsive editor beside it."""
        for widget in (legacy_bar, self.source_bar, self.label_bar, self.canvas_widget):
            layout.removeWidget(widget)
        legacy_bar.hide()
        self.label_bar.hide()
        self.canvas_widget.toolbar.hide()
        self.chart_toolbar = QToolBar("Chart")
        self.chart_toolbar.setObjectName("ChartWorkspaceToolbar")
        self.chart_toolbar.setMovable(False)
        self.chart_toolbar.setFloatable(False)
        self.edit_chart_button = QToolButton()
        self.edit_chart_button.setText("Edit chart")
        self.edit_chart_button.setIcon(icon("edit"))
        self.edit_chart_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.edit_chart_button.setCheckable(True)
        self.edit_chart_button.setToolTip("Edit labels, style, legend, and annotations")
        self.edit_chart_button.toggled.connect(self._set_chart_settings_open)
        self.chart_toolbar.addWidget(self.edit_chart_button)
        self.change_plot_button=QToolButton()
        self.change_plot_button.setText("Change plot")
        self.change_plot_button.setIcon(icon("chart"))
        self.change_plot_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.change_plot_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.change_plot_button.setToolTip("Change the plot type on this chart using the same data. Fitted lines are kept.")
        plot_menu=QMenu(self.change_plot_button)
        note=plot_menu.addAction("All data series on this chart")
        note.setEnabled(False)
        self.change_plot_actions={}
        for group,choices in PLOT_GROUPS:
            submenu=plot_menu.addMenu(group)
            for label,value in choices:
                action=submenu.addAction(label)
                action.setCheckable(True)
                action.triggered.connect(lambda checked=False,kind=value:self.change_plot_type(kind))
                self.change_plot_actions[value]=action
        plot_menu.addSeparator()
        plot_menu.addAction("Change just one series…",self._edit_one_series)
        plot_menu.aboutToShow.connect(self._sync_plot_type_actions)
        self.change_plot_button.setMenu(plot_menu)
        self.chart_toolbar.addWidget(self.change_plot_button)
        self.legend_action = self.chart_toolbar.addAction(icon("legend"), "Legend…", self._open_legend_editor)
        self.legend_action.setToolTip("Change series colors, names and legend appearance")
        data_button = QToolButton()
        data_button.setText("Data")
        data_button.setIcon(icon("sheet"))
        data_button.setToolTip("View, add, or replace chart data")
        data_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        data_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        data_menu = QMenu(data_button)
        self.view_data_action = data_menu.addAction("View source worksheet", self._view_chart_data)
        all_sources = data_menu.addMenu("Source worksheets")
        data_menu.addAction("Add series…", self._open_add_layer_dialog)
        data_menu.addSeparator()
        replace_action = data_menu.addAction("Replace data…", lambda: self.request_replace_data.emit(False))
        duplicate_action = data_menu.addAction("Duplicate with new data…", lambda: self.request_replace_data.emit(True))

        def update_data_menu():
            measured = any(not curve.is_fit_curve for curve in self.graph_model.curves)
            sources = list(dict.fromkeys(
                (c.source_sheet, c.source_workbook) for c in self.graph_model.curves if c.source_sheet
            ))
            self.view_data_action.setEnabled(bool(sources))
            self.view_data_action.setVisible(len(sources) <= 1)
            all_sources.menuAction().setVisible(len(sources) > 1)
            all_sources.clear()
            if len(sources) > 1:
                for sheet, workbook in sources:
                    all_sources.addAction(
                        f"{workbook} / {sheet}",
                        lambda checked=False, s=sheet, w=workbook: self.request_jump_to_sheet.emit(s, w),
                    )
            replace_action.setEnabled(measured)
            duplicate_action.setEnabled(measured)

        update_data_menu()
        data_menu.aboutToShow.connect(update_data_menu)
        data_button.setMenu(data_menu)
        self.chart_toolbar.addWidget(data_button)
        navigation = QToolButton()
        navigation.setText("Explore")
        navigation.setIcon(icon("zoom"))
        navigation.setToolTip("Explore the chart")
        navigation.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        navigation.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(navigation)
        menu.addAction("Reset view", self.canvas_widget.toolbar.home)
        menu.addAction("Zoom into an area", self.canvas_widget.toolbar.zoom)
        menu.addAction("Pan the chart", self.canvas_widget.toolbar.pan)
        menu.addSeparator()
        menu.addAction("Read data values", lambda: self._select_tool("data_reader"))
        menu.addAction("Select fitting range", lambda: self._select_tool("range_selector"))
        menu.addAction("Return to pointer", lambda: self._select_tool("pointer"))
        navigation.setMenu(menu)
        self.chart_toolbar.addWidget(navigation)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred)
        self.chart_toolbar.addWidget(spacer)
        copy_action = self.chart_toolbar.addAction(icon("copy"), "Copy graph", self._copy_to_clipboard)
        self._chart_toolbar_buttons = (
            self.edit_chart_button, self.change_plot_button, data_button, navigation,
            self.chart_toolbar.widgetForAction(self.legend_action), self.chart_toolbar.widgetForAction(copy_action),
        )
        self.chart_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        layout.addWidget(self.chart_toolbar)

        self.chart_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.chart_splitter.setChildrenCollapsible(False)
        self.canvas_widget.setMinimumHeight(160)
        self.chart_splitter.addWidget(self.canvas_widget)
        content = QWidget()
        content.setObjectName("ChartEditorBody")
        settings = QVBoxLayout(content)
        settings.setContentsMargins(16,16,16,16)
        settings.setSpacing(12)
        self.editor_tabs = QTabWidget()
        self.editor_tabs.setObjectName("ChartEditorTabs")
        self.editor_tabs.setDocumentMode(True)
        self.editor_tabs.tabBar().setDrawBase(False)
        settings.addWidget(self.editor_tabs)
        labels = QWidget()
        form = QFormLayout(labels)
        form.setContentsMargins(0,14,0,8)
        form.setSpacing(8)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        for caption, field in (("Figure title",self.txt_quick_title),
                               ("Horizontal axis (X)",self.txt_quick_x),
                               ("Vertical axis (Y)",self.txt_quick_y)):
            field.setMinimumWidth(0)
            form.addRow(caption,field)
        self.lbl_quick_y2.setText("Right vertical axis")
        form.addRow(self.lbl_quick_y2,self.txt_quick_y2)
        form.addRow("Panel label (optional)",self.combo_quick_panel)
        self.lbl_quick_y_bottom=QLabel("Bottom panel vertical axis")
        self.txt_quick_y_bottom=QLineEdit(self.graph_model.y_bottom_title)
        self.txt_quick_y_bottom.editingFinished.connect(self._on_quick_label_edited)
        form.addRow(self.lbl_quick_y_bottom,self.txt_quick_y_bottom)
        self.editor_tabs.addTab(labels,"Labels")
        style = QWidget()
        style_layout = QVBoxLayout(style)
        style_layout.setContentsMargins(0,14,0,8)
        style_layout.setSpacing(10)
        style_layout.addWidget(QLabel("Figure style"))
        style_layout.addWidget(self.combo_theme)
        self.show_grid_checkbox=QCheckBox("Show grid lines")
        self.show_grid_checkbox.setChecked(self.graph_model.show_grid_major)
        self.show_grid_checkbox.toggled.connect(self._on_grid_toggled)
        style_layout.addWidget(self.show_grid_checkbox)
        self.waterfall_checkbox=QCheckBox("Stack spectra (waterfall)")
        self.waterfall_checkbox.toggled.connect(self._set_waterfall_enabled)
        style_layout.addWidget(self.waterfall_checkbox)
        self.waterfall_controls=QWidget()
        wf=QFormLayout(self.waterfall_controls)
        wf.setContentsMargins(0,0,0,0)
        wf.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        self.waterfall_axis_checkbox=QCheckBox("Show intensity axis")
        self.waterfall_axis_checkbox.toggled.connect(self._set_waterfall_axis)
        self.waterfall_axis_checkbox.setToolTip("Values include the vertical offset added to each spectrum")
        wf.addRow(self.waterfall_axis_checkbox)
        self.waterfall_spacing=QDoubleSpinBox()
        self.waterfall_spacing.setRange(0,1e9)
        self.waterfall_spacing.setDecimals(4)
        self.waterfall_spacing.setSpecialValueText("Automatic")
        self.waterfall_spacing.valueChanged.connect(self._set_waterfall_step)
        wf.addRow("Vertical spacing",self.waterfall_spacing)
        note=QLabel("Spectra are shifted vertically for clarity. Offset values are not absolute intensity measurements.")
        note.setWordWrap(True)
        note.setProperty("role","muted")
        wf.addRow(note)
        style_layout.addWidget(self.waterfall_controls)
        style_layout.addWidget(self.legend_menu_button)
        style_layout.addWidget(self.annotation_menu_button)
        style_layout.addStretch()
        self.editor_tabs.addTab(style,"Style")
        from omnigraph.ui.series_editor import SeriesEditor
        self.series_editor=SeriesEditor(self.graph_model)
        self.series_editor.changed.connect(self._on_series_style_changed)
        self.editor_tabs.addTab(self.series_editor,"Series")
        self.source_bar.hide()
        settings.addStretch()
        self.chart_settings = QScrollArea()
        self.chart_settings.setObjectName("ChartSettingsPanel")
        self.chart_settings.setWidgetResizable(True)
        self.chart_settings.setWidget(content)
        self.chart_settings.setMinimumSize(0, 0)
        self.chart_splitter.addWidget(self.chart_settings)
        self.chart_splitter.setStretchFactor(0,1)
        self.chart_splitter.setStretchFactor(1,0)
        self.chart_settings.hide()
        layout.addWidget(self.chart_splitter,1)
        self._sync_quick_labels()

    def _set_chart_settings_open(self, opened):
        self.edit_chart_button.setText("Done editing" if opened else "Edit chart")
        self._arrange_chart_editor()

    def _arrange_chart_editor(self):
        if not hasattr(self, "chart_settings"):
            return
        if not self.edit_chart_button.isChecked():
            self.chart_settings.hide()
            self.canvas_widget.setMinimumHeight(160)
            return
        orientation = Qt.Orientation.Horizontal if self.width() / self._interface_scale >= 950 else Qt.Orientation.Vertical
        if orientation == Qt.Orientation.Vertical:
            available = max(0, self.height() - self.chart_toolbar.sizeHint().height())
            self.canvas_widget.setMinimumHeight(min(160, int(available * 0.45)))
        else:
            self.canvas_widget.setMinimumHeight(160)
        changed=self.chart_splitter.orientation()!=orientation or not self.chart_settings.isVisible()
        self.chart_splitter.setOrientation(orientation)
        self.chart_settings.setMaximumWidth(380 if orientation==Qt.Orientation.Horizontal else 16777215)
        self.chart_settings.setMaximumHeight(16777215)
        self.chart_settings.show()
        if changed:
            extent=self.width() if orientation==Qt.Orientation.Horizontal else self.height()
            editor_size=min(350,max(120,int(extent*.43)))
            self.chart_splitter.setSizes([max(100,extent-editor_size),editor_size])

    def set_interface_scale(self, scale):
        self._interface_scale = scale
        self._adapt_chart_toolbar()
        self._arrange_chart_editor()

    def _adapt_chart_toolbar(self):
        if not hasattr(self, "_chart_toolbar_buttons"):
            return
        style = (Qt.ToolButtonStyle.ToolButtonIconOnly if self.width() / self._interface_scale < 700
                 else Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        for button in self._chart_toolbar_buttons:
            button.setToolButtonStyle(style)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self._adapt_chart_toolbar()
        self._arrange_chart_editor()

    def _view_chart_data(self):
        curve = next((c for c in self.graph_model.curves if c.source_sheet), None)
        if curve:
            self.request_jump_to_sheet.emit(curve.source_sheet, curve.source_workbook)

    def _update_source_bar(self):
        """Refreshes the linked worksheet indicators with 1-click jump buttons."""
        if not hasattr(self, "source_bar_layout"):
            return

        while self.source_bar_layout.count():
            item = self.source_bar_layout.takeAt(0)
            if item.widget():
                w = item.widget()
                w.setParent(None)
                w.deleteLater()

        lbl_icon = QLabel("Worksheet")
        lbl_icon.setObjectName("LinkedSourceIcon")
        self.source_bar_layout.addWidget(lbl_icon)

        # Collect unique sheets
        sheet_map = {}
        for c in self.graph_model.curves:
            if c.source_sheet:
                key = (c.source_sheet, c.source_workbook)
                if key not in sheet_map:
                    sheet_map[key] = []
                sheet_map[key].append(c.label)

        if not sheet_map:
            lbl_none = QLabel("None (Computed or manual curve)")
            lbl_none.setObjectName("LinkedSourceNone")
            self.source_bar_layout.addWidget(lbl_none)
        else:
            for (s_name, wb_name), curve_labels in sheet_map.items():
                btn_sheet = QToolButton()
                btn_sheet.setText(f"{s_name} ↗")
                btn_sheet.setToolTip(f"Jump directly to worksheet '{s_name}' ({wb_name})\nPlotted series: {', '.join(curve_labels[:4])}")
                btn_sheet.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_sheet.clicked.connect(lambda checked=False, s=s_name, w=wb_name: self.request_jump_to_sheet.emit(s, w))
                self.source_bar_layout.addWidget(btn_sheet)

        self.source_bar_layout.addStretch()

    def _set_quick_panel_label(self, val: str):
        if val == "None":
            self.graph_model.panel_label = ""
        elif val == "Custom...":
            text, ok = QInputDialog.getText(
                self, "Custom Panel Autograph", "Enter publication panel label:\n(e.g., (A), Panel 1, Fig. 2a)",
                text=getattr(self.graph_model, "panel_label", "(A)")
            )
            if ok:
                self.graph_model.panel_label = text.strip()
            else:
                return
        else:
            self.graph_model.panel_label = val

        p_text = getattr(self.graph_model, "panel_label", "")
        if hasattr(self, "btn_quick_panel"):
            self.btn_quick_panel.setText(p_text if p_text else "None ▾")
        if hasattr(self, "combo_quick_panel"):
            self.combo_quick_panel.blockSignals(True)
            self.combo_quick_panel.setCurrentText(p_text if p_text else "None")
            self.combo_quick_panel.blockSignals(False)
        self.refresh_plot()
        self.labels_changed.emit()

    def _on_quick_panel_changed(self, text: str):
        val = text.strip()
        self.graph_model.panel_label = "" if val == "None" else val
        if hasattr(self, "btn_quick_panel"):
            p_text = getattr(self.graph_model, "panel_label", "")
            self.btn_quick_panel.setText(p_text if p_text else "None ▾")
        self.refresh_plot()
        self.labels_changed.emit()

    def _open_add_layer_dialog(self):
        from omnigraph.ui.dialogs.add_curve_dialog import AddCurveDialog
        dlg = AddCurveDialog(self.project, self.graph_model, self)
        if dlg.exec():
            self.refresh_plot()
            self.curves_changed.emit()

    def _open_edit_labels_dialog(self):
        self.editor_tabs.setCurrentIndex(0)
        self.edit_chart_button.setChecked(True)
        self.txt_quick_title.setFocus()

    def _sync_plot_type_actions(self):
        curves=[c for c in self.graph_model.curves if not c.is_fit_curve]
        kinds={c.plot_type for c in curves}
        self.change_plot_button.setEnabled(bool(curves))
        for kind,action in self.change_plot_actions.items():
            action.setChecked(kinds=={kind})

    def _edit_one_series(self):
        self.editor_tabs.setCurrentWidget(self.series_editor)
        self.edit_chart_button.setChecked(True)
        self.series_editor.plot_type.setFocus()

    def change_plot_type(self,plot_type):
        if not change_graph_plot_type(self.graph_model,plot_type):
            return
        self.refresh_plot()
        self.curves_changed.emit()
        self.labels_changed.emit()

    def _on_series_style_changed(self):
        self.refresh_plot()
        self.labels_changed.emit()

    def _on_grid_toggled(self,enabled):
        self.graph_model.show_grid_major=enabled
        self.refresh_plot()
        self.labels_changed.emit()

    def _sync_quick_labels(self):
        """Synchronizes quick-label text fields with current graph model state."""
        if not hasattr(self, "txt_quick_title"):
            return
        self.txt_quick_title.blockSignals(True)
        self.txt_quick_x.blockSignals(True)
        self.txt_quick_y.blockSignals(True)

        self.txt_quick_title.setText(self.graph_model.title_text or "")
        self.txt_quick_x.setText(self.graph_model.x_title or "")
        self.txt_quick_y.setText(self.graph_model.y_title or "")

        if hasattr(self, "combo_quick_panel"):
            self.combo_quick_panel.blockSignals(True)
            p_text = getattr(self.graph_model, "panel_label", "")
            self.combo_quick_panel.setCurrentText(p_text if p_text else "None")
            self.combo_quick_panel.blockSignals(False)

        if hasattr(self, "btn_quick_panel"):
            p_text = getattr(self.graph_model, "panel_label", "")
            self.btn_quick_panel.setText(p_text if p_text else "None ▾")

        has_y2 = self.graph_model.layout_mode=="twin_x" or bool(self.graph_model.y2_title) or any(getattr(c, "axis", "primary") == "secondary" for c in self.graph_model.curves)
        if hasattr(self, "lbl_quick_y2") and hasattr(self, "txt_quick_y2"):
            self.txt_quick_y2.blockSignals(True)
            self.lbl_quick_y2.setHidden(not has_y2)
            self.txt_quick_y2.setHidden(not has_y2)
            if has_y2:
                self.txt_quick_y2.setText(self.graph_model.y2_title or "")
            self.txt_quick_y2.blockSignals(False)

        if hasattr(self,"txt_quick_y_bottom"):
            stacked=self.graph_model.layout_mode=="stacked_2x1"
            self.lbl_quick_y_bottom.setVisible(stacked)
            self.txt_quick_y_bottom.setVisible(stacked)
            self.txt_quick_y_bottom.setText(self.graph_model.y_bottom_title or "")
        if hasattr(self,"series_editor"):
            self.series_editor.sync()
        if hasattr(self,"waterfall_checkbox"):
            for control,value in ((self.waterfall_checkbox,self.graph_model.waterfall_enabled),(self.waterfall_axis_checkbox,self.graph_model.waterfall_show_y_axis)):
                control.blockSignals(True)
                control.setChecked(value)
                control.blockSignals(False)
            self.waterfall_spacing.blockSignals(True)
            self.waterfall_spacing.setValue(self.graph_model.waterfall_y_step)
            self.waterfall_spacing.blockSignals(False)
            self.waterfall_controls.setVisible(self.graph_model.waterfall_enabled)
        if hasattr(self,"show_grid_checkbox"):
            self.show_grid_checkbox.blockSignals(True)
            self.show_grid_checkbox.setChecked(self.graph_model.show_grid_major)
            self.show_grid_checkbox.blockSignals(False)
        self.txt_quick_title.blockSignals(False)
        self.txt_quick_x.blockSignals(False)
        self.txt_quick_y.blockSignals(False)

    def _on_quick_label_edited(self):
        """Applies inline label edits directly to graph and re-renders."""
        self.graph_model.title_text = self.txt_quick_title.text().strip()
        self.graph_model.x_title = self.txt_quick_x.text().strip()
        self.graph_model.y_title = self.txt_quick_y.text().strip()
        if not self.txt_quick_y2.isHidden():
            self.graph_model.y2_title=self.txt_quick_y2.text().strip()
        if hasattr(self,"txt_quick_y_bottom") and self.graph_model.layout_mode=="stacked_2x1":
            self.graph_model.y_bottom_title=self.txt_quick_y_bottom.text().strip()

        self.refresh_plot()
        self.labels_changed.emit()
        win = self.window()
        if hasattr(win, "statusBar") and win.statusBar():
            win.statusBar().showMessage("✓ Graph labels updated", 2500)

    def _toggle_quick_label_bar(self):
        self.edit_chart_button.setChecked(not self.edit_chart_button.isChecked())

    def _edit_title_prompt(self):
        self.canvas_widget.edit_graph_title()
        self._sync_quick_labels()

    def _edit_x_title_prompt(self):
        self.canvas_widget.edit_x_title()
        self._sync_quick_labels()

    def _edit_y_title_prompt(self):
        self.canvas_widget.edit_y_title()
        self._sync_quick_labels()

    def _open_legend_editor(self):
        self.canvas_widget.open_legend_editor()

    def _toggle_legend(self):
        self.canvas_widget._toggle_legend()

    def _set_legend_position(self, pos: str):
        self.graph_model.legend_location = pos
        self.graph_model.legend_show = True
        self.refresh_plot()
        self.labels_changed.emit()

    def refresh_plot(self):
        """Forces re-render of canvas."""
        self.canvas_widget.refresh()
        self._sync_plot_type_actions()
        self._update_source_bar()
        self._sync_quick_labels()

    def _on_theme_changed(self, theme_name: str):
        self.graph_model.theme = theme_name
        self.refresh_plot()
        self.labels_changed.emit()

    def _select_tool(self, tool_name: str):
        self.btn_pointer.setChecked(tool_name == "pointer")
        self.btn_crosshair.setChecked(tool_name == "data_reader")
        self.btn_range.setChecked(tool_name == "range_selector")
        self.canvas_widget.set_tool(tool_name)

    def _add_text_annotation(self):
        text, ok = QInputDialog.getText(self, "Add Text Annotation", "Enter annotation text:")
        if ok and text:
            # Place in center of current axes
            xlim = self.canvas_widget.plot_manager.ax.get_xlim()
            ylim = self.canvas_widget.plot_manager.ax.get_ylim()
            cx = (xlim[0] + xlim[1]) / 2.0
            cy = (ylim[0] + ylim[1]) / 2.0
            self.graph_model.annotations.append({
                "type": "text",
                "x": cx,
                "y": cy,
                "text": text,
                "color": "#000000" if self.graph_model.theme != "Modern Dark" else "#ffffff",
                "font_size": 10,
            })
            self.refresh_plot()

    def _add_ref_line_h(self):
        val, ok = QInputDialog.getDouble(self, "Horizontal Reference Line", "Enter Y value:", 0.0, -1e9, 1e9, 4)
        if ok:
            self.graph_model.annotations.append({
                "type": "ref_line",
                "orientation": "h",
                "value": val,
                "color": "#d62728",
                "style": "--",
                "label": f"y = {val:.4g}",
            })
            self.refresh_plot()

    def _add_ref_line_v(self):
        val, ok = QInputDialog.getDouble(self, "Vertical Reference Line", "Enter X value:", 0.0, -1e9, 1e9, 4)
        if ok:
            self.graph_model.annotations.append({
                "type": "ref_line",
                "orientation": "v",
                "value": val,
                "color": "#1f77b4",
                "style": "--",
                "label": f"x = {val:.4g}",
            })
            self.refresh_plot()

    def _copy_to_clipboard(self):
        success = self.canvas_widget.copy_to_clipboard(width_in=7.0, height_in=5.0, dpi=300)
        if success:
            win = self.window()
            if hasattr(win, "statusBar") and win.statusBar():
                win.statusBar().showMessage("📋 Graph copied to clipboard at publication quality (300 DPI, 7.0 × 5.0 in)", 4000)
            if hasattr(self, "btn_copy") and self.btn_copy.isVisible():
                QToolTip.showText(
                    self.btn_copy.mapToGlobal(QPoint(0, self.btn_copy.height() + 4)),
                    "✓ Copied to clipboard (300 DPI, 7.0 × 5.0 in)!",
                    self.btn_copy,
                    QRect(),
                    2500,
                )
        else:
            QMessageBox.warning(self, "Copy Failed", "Failed to copy graph to clipboard.")

    def _export_graph(self):
        from omnigraph.ui.dialogs.export_dialog import ExportDialog
        dlg = ExportDialog(self.canvas_widget.plot_manager, self)
        dlg.exec()

    def _set_waterfall_enabled(self,enabled):
        self.graph_model.waterfall_enabled=enabled
        self.refresh_plot()
        self.labels_changed.emit()

    def _set_waterfall_axis(self,enabled):
        self.graph_model.waterfall_show_y_axis=enabled
        self.refresh_plot()
        self.labels_changed.emit()

    def _toggle_waterfall(self):
        self.graph_model.waterfall_enabled = not getattr(self.graph_model, "waterfall_enabled", False)
        if hasattr(self, "act_toggle_wf"):
            self.act_toggle_wf.setChecked(self.graph_model.waterfall_enabled)
        self.refresh_plot()
        self.curves_changed.emit()

    def _set_waterfall_step(self, step: float):
        self.graph_model.waterfall_enabled = True
        self.graph_model.waterfall_y_step = float(step)
        if hasattr(self, "act_toggle_wf"):
            self.act_toggle_wf.setChecked(True)
        self.refresh_plot()
        self.curves_changed.emit()

    def _adjust_waterfall_step(self, factor: float):
        self.graph_model.waterfall_enabled = True
        cur = getattr(self.graph_model, "waterfall_y_step", 0.0)
        if cur == 0.0:
            y_spans = []
            for c in self.graph_model.curves:
                if getattr(c, "visible", True):
                    _, y_d, _ = self.canvas_widget.plot_manager._get_curve_data(c)
                    if len(y_d) > 1:
                        y_spans.append(float(np.ptp(y_d)))
            base_span = float(np.mean(y_spans)) if y_spans else 1.0
            cur = max(base_span * 0.35, 0.1)
        self.graph_model.waterfall_y_step = max(cur * factor, 1e-4)
        if hasattr(self, "act_toggle_wf"):
            self.act_toggle_wf.setChecked(True)
        self.refresh_plot()
        self.curves_changed.emit()

    def _custom_waterfall_step(self):
        cur = getattr(self.graph_model, "waterfall_y_step", 1.0)
        val, ok = QInputDialog.getDouble(self, "Custom Waterfall Step", "Enter vertical offset (ΔY) per curve layer:", cur, 0.0, 1e9, 4)
        if ok:
            self._set_waterfall_step(val)

    def _toggle_waterfall_x_stagger(self):
        cur = getattr(self.graph_model, "waterfall_x_step", 0.0)
        if cur == 0.0:
            xlim = self.canvas_widget.plot_manager.ax.get_xlim()
            span = abs(xlim[1] - xlim[0]) if len(xlim) == 2 else 10.0
            self.graph_model.waterfall_x_step = span * 0.05
        else:
            self.graph_model.waterfall_x_step = 0.0
        if hasattr(self, "act_wf_stagger"):
            self.act_wf_stagger.setChecked(self.graph_model.waterfall_x_step != 0.0)
        self.refresh_plot()
        self.curves_changed.emit()

    def _toggle_waterfall_baseline(self):
        cur = getattr(self.graph_model, "waterfall_baseline", False)
        self.graph_model.waterfall_baseline = not cur
        if hasattr(self, "act_wf_base"):
            self.act_wf_base.setChecked(self.graph_model.waterfall_baseline)
        self.refresh_plot()
        self.curves_changed.emit()

    def _prompt_significance_bracket(self, x1=1.0, x2=2.0, y=None):
        """Prompt user to add a publication significance bracket."""
        if y is None or np.isnan(y):
            ylim = self.canvas_widget.plot_manager.ax.get_ylim()
            y = ylim[1] - 0.1 * (ylim[1] - ylim[0])

        stars, ok = QInputDialog.getItem(
            self,
            "Add Significance Bracket",
            "Significance Annotation Label:",
            ["*** (p < 0.001)", "** (p < 0.01)", "* (p < 0.05)", "**** (p < 0.0001)", "ns (p ≥ 0.05)", "Custom..."],
            0,
            False,
        )
        if not ok:
            return

        label_clean = stars.split()[0]
        if "Custom" in stars:
            cust, ok_c = QInputDialog.getText(self, "Custom p-value", "Enter label text (e.g. p = 0.032):", text="p = ")
            if ok_c and cust:
                label_clean = cust

        ylim = self.canvas_widget.plot_manager.ax.get_ylim()
        tick_h = 0.04 * abs(ylim[1] - ylim[0]) if len(ylim) == 2 else 0.5
        bracket = StatisticsAnalyzer.create_significance_bracket(
            x1=x1, x2=x2, y=y, custom_text=label_clean, h=tick_h,
            color="#000000" if self.graph_model.theme != "Modern Dark" else "#ffffff"
        )
        self.graph_model.annotations.append(bracket)
        self.refresh_plot()
        self.labels_changed.emit()

    def _on_files_dropped(self, paths: list):
        """Open the standard import preview for files dropped onto a chart."""
        window = self.window()
        if hasattr(window, "_show_import_dialog"):
            window._show_import_dialog(initial_filepaths=paths, target_graph=self.graph_model)

    def _on_point_mask_toggled(self, curve_label: str, row_idx: int):
        """Toggle mask/exclusion for a point in the dataset."""
        target_curve = next((c for c in self.graph_model.curves if c.label == curve_label), None)
        if not target_curve and self.graph_model.curves:
            target_curve = self.graph_model.curves[0]
        if target_curve:
            wb = self.project.get_workbook(target_curve.source_workbook) or (self.project.workbooks[0] if self.project.workbooks else None)
            if wb:
                ws = next((s for s in wb.sheets if s.name == target_curve.source_sheet), None) or wb.get_active_sheet()
                if ws:
                    col_y = ws.get_column(target_curve.y_col_idx)
                    col_x = ws.get_column(target_curve.x_col_idx) if target_curve.x_col_idx is not None else None
                    if col_y:
                        is_m = col_y.is_row_masked(row_idx) or (col_x.is_row_masked(row_idx) if col_x else False)
                        col_y.mask_row(row_idx, not is_m)
                        if col_x and is_m:
                            col_x.mask_row(row_idx, False)
                        self.refresh_plot()
                        self.curves_changed.emit()
                        win = self.window()
                        if hasattr(win, "refresh_active_spreadsheet"):
                            win.refresh_active_spreadsheet()
                        if hasattr(win, "statusBar") and win.statusBar():
                            status_msg = f"Point {row_idx + 1} ({curve_label}) {'excluded from fits' if not is_m else 'restored'}"
                            win.statusBar().showMessage(f"🎯 {status_msg}", 3000)

    def set_zoom(self, zoom: float):
        """Scales graph figure DPI and layout to zoom in or out of the plot scale."""
        if hasattr(self, "canvas_widget") and hasattr(self.canvas_widget, "plot_manager"):
            fig = self.canvas_widget.plot_manager.fig
            base_dpi = 100
            new_dpi = max(60, min(int(round(base_dpi * zoom)), 250))
            if fig.dpi != new_dpi:
                fig.set_dpi(new_dpi)
                self.canvas_widget.canvas.draw_idle()
