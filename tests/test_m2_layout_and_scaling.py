"""
Unit tests for Milestone 2: High-DPI Foundation & Main Window Layouts.

Verifies:
1. High-DPI PassThrough scale factor rounding policy contract in main.py.
2. MainWindow initialization: no premature show/maximize, toolbar break between toolbars.
3. Dock width flexibility: Project Explorer and Property Inspector docks have no rigid maximum width caps.
4. MainWindow minimumSizeHint() <= 900x650 px across standard and High-DPI environments.
5. SpreadsheetWidget responsive QToolBar layout and minimumSizeHint reduction with overflow support.
6. GraphViewWidget combo_theme non-clipping width (>= 140px) and size adjust policy.
7. GraphViewWidget label_bar 2-row QGridLayout refactoring and compact screen responsiveness.
8. PropertyInspectorWidget: removal of inline stylesheet and non-truncating 2-row Curves tab button layout (< 285px).
9. ReportViewWidget: removal of inline stylesheet and theme adaptability.
10. Stylesheet font-size pixel removal: preserving point-size scaling for typography.
11. Scrollbar accessibility: 12-14px thickness in both Light and Dark themes.
"""

import os
import sys
import inspect
import pytest
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QApplication, QToolBar, QToolButton, QLabel, QWidget,
    QGridLayout, QLineEdit, QComboBox, QPushButton, QCheckBox,
    QScrollBar, QTextBrowser
)

import main as main_mod
from omnigraph.core.worksheet import Worksheet, ColumnRole
from omnigraph.core.project import Project, GraphModel, CurveModel, ReportModel
from omnigraph.graphing.themes import THEMES
from omnigraph.ui.samples import SampleProjects
from omnigraph.ui.main_window import MainWindow
from omnigraph.ui.spreadsheet_view import SpreadsheetWidget
from omnigraph.ui.graph_view import GraphViewWidget
from omnigraph.ui.property_dock import PropertyInspectorWidget
from omnigraph.ui.report_view import ReportViewWidget
from omnigraph.ui.styles.qss import DARK_THEME_QSS, LIGHT_THEME_QSS


@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


# ---------------------------------------------------------------------------
# 1. High-DPI & Main.py Contracts
# ---------------------------------------------------------------------------

def test_high_dpi_passthrough_policy_contract():
    """Verify QApplication High-DPI PassThrough policy contract in main.py."""
    assert hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"), "Qt must provide HighDpiScaleFactorRoundingPolicy"
    assert hasattr(Qt.HighDpiScaleFactorRoundingPolicy, "PassThrough"), "PassThrough policy must be available"

    src = inspect.getsource(main_mod.main)
    assert "setHighDpiScaleFactorRoundingPolicy" in src, "main.py must configure setHighDpiScaleFactorRoundingPolicy"
    assert "PassThrough" in src, "main.py must set PassThrough rounding policy"
    assert "AA_EnableHighDpiScaling" not in src, "Deprecated AA_EnableHighDpiScaling must be removed"
    assert "AA_UseHighDpiPixmaps" not in src, "Deprecated AA_UseHighDpiPixmaps must be removed"


# ---------------------------------------------------------------------------
# 2. MainWindow Initialization & Geometry
# ---------------------------------------------------------------------------

def test_mainwindow_init_not_prematurely_shown_or_maximized(qapp):
    """Verify MainWindow.__init__ does not prematurely call showMaximized()."""
    proj = SampleProjects.create_spectroscopy_sample()
    win = MainWindow(project=proj)
    try:
        assert not win.isVisible(), "MainWindow should not be visible immediately after __init__"
        assert not win.isMaximized(), "MainWindow should not be maximized immediately after __init__"
        win.showNormal()
        assert win.isVisible(), "MainWindow should be visible after showNormal()"
    finally:
        win.close()


def test_mainwindow_dock_maximum_width_unconstrained(qapp):
    """Verify MainWindow docks have no rigid maximum width caps (e.g. 450/460px)."""
    proj = SampleProjects.create_spectroscopy_sample()
    win = MainWindow(project=proj)
    try:
        assert win.dock_explorer.maximumWidth() > 10000, (
            f"dock_explorer maximumWidth capped: {win.dock_explorer.maximumWidth()}"
        )
        assert win.dock_properties.maximumWidth() > 10000, (
            f"dock_properties maximumWidth capped: {win.dock_properties.maximumWidth()}"
        )
        assert win.dock_explorer.minimumWidth() >= 200, "dock_explorer minimumWidth should preserve sidebar minimum"
        assert win.dock_properties.minimumWidth() >= 280, "dock_properties minimumWidth should preserve sidebar minimum"
    finally:
        win.close()


def test_mainwindow_toolbars_layout_break(qapp):
    """Verify MainWindow has toolbar break between File & Data and Plot & Analysis toolbars."""
    proj = SampleProjects.create_spectroscopy_sample()
    win = MainWindow(project=proj)
    try:
        tb_file = win.findChild(QToolBar, "ToolbarFileData")
        tb_plot = win.findChild(QToolBar, "ToolbarPlotAnalysis")
        assert tb_file is not None, "ToolbarFileData missing"
        assert tb_plot is not None, "ToolbarPlotAnalysis missing"
        assert win.toolBarBreak(tb_plot) is True, "ToolbarPlotAnalysis should have a toolbar break"
        assert win.toolBarBreak(tb_file) is False, "ToolbarFileData should be on the first toolbar row"
    finally:
        win.close()


def test_mainwindow_minimum_size_hint(qapp):
    """Verify MainWindow.minimumSizeHint() <= 900x650 px and window resizes cleanly to 900x650."""
    proj = SampleProjects.create_spectroscopy_sample()
    win = MainWindow(project=proj)
    try:
        hint = win.minimumSizeHint()
        assert hint.width() <= 900, f"MainWindow minimum width {hint.width()} exceeds 900px"
        assert hint.height() <= 650, f"MainWindow minimum height {hint.height()} exceeds 650px"

        win.resize(900, 650)
        assert win.size().width() <= 900, f"Window width {win.size().width()} failed to resize <= 900"
        assert win.size().height() <= 650, f"Window height {win.size().height()} failed to resize <= 650"
    finally:
        win.close()


# ---------------------------------------------------------------------------
# 3. SpreadsheetView Responsive Toolbar
# ---------------------------------------------------------------------------

def test_spreadsheet_widget_responsive_toolbar(qapp):
    """Verify SpreadsheetWidget uses a QToolBar with minimumSizeHint width <= 150px."""
    ws = Worksheet(name="TestSheet")
    col_x = ws.add_column("X", role=ColumnRole.X)
    col_x.data = [1.0, 2.0, 3.0]
    col_y = ws.add_column("Y", role=ColumnRole.Y)
    col_y.data = [4.0, 5.0, 6.0]

    sw = SpreadsheetWidget(ws)

    # 1. Must have responsive QToolBar
    assert hasattr(sw, "toolbar"), "SpreadsheetWidget must have 'toolbar' attribute"
    assert isinstance(sw.toolbar, QToolBar), "SpreadsheetWidget.toolbar must be a QToolBar"
    assert sw.toolbar.objectName() == "SpreadsheetActionToolbar"

    # 2. Undo / Redo buttons and label must exist with expected types
    assert hasattr(sw, "btn_undo") and isinstance(sw.btn_undo, QToolButton)
    assert hasattr(sw, "btn_redo") and isinstance(sw.btn_redo, QToolButton)
    assert hasattr(sw, "lbl_col_info") and isinstance(sw.lbl_col_info, QLabel)

    # 3. Minimum width must be compact (<= 150px)
    min_hint = sw.minimumSizeHint()
    assert min_hint.width() <= 150, f"SpreadsheetWidget minimum width {min_hint.width()} exceeds 150px"

    # 4. Long column info labels must not inflate minimum width
    sw.lbl_col_info.setText("Col A (Y): Very Long Column Title For Biological Enzyme Kinetics Assay")
    assert sw.minimumSizeHint().width() <= 150, "Long column label must not inflate minimumSizeHint width"


# ---------------------------------------------------------------------------
# 4. GraphView Theme Combobox & Label Bar
# ---------------------------------------------------------------------------

def test_graph_view_theme_combobox_sizing(qapp):
    """Verify combo_theme does not clip long theme names and has no 115px artificial max width."""
    proj = SampleProjects.create_spectroscopy_sample()
    gm = proj.graphs[0]
    gv = GraphViewWidget(gm, proj)

    # 1. Maximum width must not be capped at 115px
    assert gv.combo_theme.maximumWidth() > 115, "combo_theme maximumWidth must not be capped at 115px"

    # 2. Size adjust policy must adjust to minimum contents length with icon
    assert gv.combo_theme.sizeAdjustPolicy() in (
        QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon,
        QComboBox.SizeAdjustPolicy.AdjustToContents
    )

    # 3. Minimum contents length must be at least 14
    assert gv.combo_theme.minimumContentsLength() >= 14, "minimumContentsLength must be >= 14"

    # 4. Combobox sizeHint must fit longest theme 'High-Contrast B&W' (at least 140px)
    hint_w = gv.combo_theme.sizeHint().width()
    assert hint_w >= 140, f"combo_theme sizeHint width {hint_w} is too small to fit 'High-Contrast B&W'"

    # 5. Selecting themes works cleanly
    for theme_name in THEMES.keys():
        gv.combo_theme.setCurrentText(theme_name)
        assert gv.graph_model.theme == theme_name


def test_graph_view_label_bar_compact_grid(qapp):
    """Verify label_bar uses a 2-row QGridLayout with public attributes and label sync."""
    proj = SampleProjects.create_spectroscopy_sample()
    gm = proj.graphs[0]
    gv = GraphViewWidget(gm, proj)

    # 1. Layout must be QGridLayout
    layout = gv.label_bar.layout()
    assert isinstance(layout, QGridLayout), f"label_bar layout must be QGridLayout, got {type(layout)}"
    assert layout.rowCount() == 2, f"label_bar grid must have 2 rows, got {layout.rowCount()}"

    # 2. Text fields and labels must exist as public attributes
    assert hasattr(gv, "txt_quick_title") and isinstance(gv.txt_quick_title, QLineEdit)
    assert hasattr(gv, "txt_quick_x") and isinstance(gv.txt_quick_x, QLineEdit)
    assert hasattr(gv, "txt_quick_y") and isinstance(gv.txt_quick_y, QLineEdit)
    assert hasattr(gv, "lbl_quick_y2") and isinstance(gv.lbl_quick_y2, QLabel)
    assert hasattr(gv, "txt_quick_y2") and isinstance(gv.txt_quick_y2, QLineEdit)

    # 3. Editing title and axis labels works and syncs to graph model
    gv.txt_quick_title.setText("Absorbance Spectrum")
    gv.txt_quick_x.setText("Wavelength (nm)")
    gv.txt_quick_y.setText("Absorbance (A.U.)")
    gv._on_quick_label_edited()
    assert gm.title_text == "Absorbance Spectrum"
    assert gm.x_title == "Wavelength (nm)"
    assert gm.y_title == "Absorbance (A.U.)"

    # 4. Right Y visibility toggle syncs properly
    gv._sync_quick_labels()
    # Default spectroscopy sample does not have secondary axis, so Y2 is hidden
    assert gv.lbl_quick_y2.isHidden() is True
    assert gv.txt_quick_y2.isHidden() is True

    # When y2_title is present, Y2 is shown
    gm.y2_title = "Right Y Axis"
    gv._sync_quick_labels()
    assert gv.lbl_quick_y2.isHidden() is False
    assert gv.txt_quick_y2.isHidden() is False


# ---------------------------------------------------------------------------
# 5. Property Inspector & Report View Theme Consistency
# ---------------------------------------------------------------------------

def test_property_dock_no_inline_stylesheet(qapp):
    """Verify PropertyInspectorWidget has no hardcoded inline stylesheet overriding application themes."""
    dock = PropertyInspectorWidget()
    assert dock.styleSheet() == "", "PropertyInspectorWidget must not have local hardcoded stylesheet"

    # Theme polish verification
    qapp.setStyleSheet(DARK_THEME_QSS)
    dock.ensurePolished()
    qapp.setStyleSheet(LIGHT_THEME_QSS)
    dock.ensurePolished()


def test_property_dock_curves_tab_button_row_non_truncation(qapp):
    """Verify Curves tab layer controls fit in 285px dock without label clipping."""
    dock = PropertyInspectorWidget()
    graph = GraphModel(title="Enzyme Kinetics")
    c1 = CurveModel(source_sheet="Sheet1", x_col_idx=0, y_col_idx=1, label="Substrate 10mM")
    c2 = CurveModel(source_sheet="Sheet1", x_col_idx=0, y_col_idx=2, label="Substrate 20mM")
    graph.curves.extend([c1, c2])
    dock.set_active_graph(graph)

    # Controls must exist as accessible attributes
    assert hasattr(dock, "chk_curve_visible") and isinstance(dock.chk_curve_visible, QCheckBox)
    assert hasattr(dock, "btn_remove_curve") and isinstance(dock.btn_remove_curve, QPushButton)
    assert hasattr(dock, "btn_move_up") and isinstance(dock.btn_move_up, QPushButton)
    assert hasattr(dock, "btn_move_down") and isinstance(dock.btn_move_down, QPushButton)

    # Descriptive button text
    assert dock.chk_curve_visible.text() == "Visible"
    assert "Remove" in dock.btn_remove_curve.text()
    assert "Up" in dock.btn_move_up.text()
    assert "Down" in dock.btn_move_down.text()

    # Verify controls are arranged across 2 rows, each row fitting within dock min width (285px)
    w_row1 = dock.chk_curve_visible.sizeHint().width() + dock.btn_remove_curve.sizeHint().width() + 20
    w_row2 = dock.btn_move_up.sizeHint().width() + dock.btn_move_down.sizeHint().width() + 20
    dock_min_w = dock.minimumWidth()

    assert w_row1 <= dock_min_w, f"Row 1 width ({w_row1}px) must fit within dock min width ({dock_min_w}px)"
    assert w_row2 <= dock_min_w, f"Row 2 width ({w_row2}px) must fit within dock min width ({dock_min_w}px)"

    # Functionality verification: visibility toggle
    dock.chk_curve_visible.setChecked(False)
    assert graph.curves[0].visible is False
    dock.chk_curve_visible.setChecked(True)
    assert graph.curves[0].visible is True

    # Functionality verification: z-order reordering
    assert graph.curves[0].label == "Substrate 10mM"
    dock.btn_move_down.click()
    assert graph.curves[0].label == "Substrate 20mM"
    dock.btn_move_up.click()
    assert graph.curves[0].label == "Substrate 10mM"

    # Functionality verification: curve removal
    dock.btn_remove_curve.click()
    assert len(graph.curves) == 1


def test_report_view_no_inline_stylesheet(qapp):
    """Verify ReportViewWidget.browser has no hardcoded stylesheet and adapts to application themes."""
    rep = ReportModel(title="Nonlinear Regression Report", html_content="<h1>Fit Report</h1>")
    rw = ReportViewWidget(rep)
    assert rw.browser.styleSheet() == "", "QTextBrowser must not have local inline stylesheet"

    qapp.setStyleSheet(DARK_THEME_QSS)
    rw.browser.ensurePolished()
    qapp.setStyleSheet(LIGHT_THEME_QSS)
    rw.browser.ensurePolished()


# ---------------------------------------------------------------------------
# 6. High-DPI QSS Typography & Scrollbar Accessibility
# ---------------------------------------------------------------------------

def test_qss_font_scaling_preserves_point_size(qapp):
    """Verify global QWidget, QLabel, and QCheckBox rules do not hardcode fixed font-size: 12px;."""
    # Ensure QWidget root block does not force fixed font-size: 12px
    dark_qwidget = DARK_THEME_QSS.split("QWidget {")[1].split("}")[0]
    light_qwidget = LIGHT_THEME_QSS.split("QWidget {")[1].split("}")[0]
    assert "font-size: 12px;" not in dark_qwidget, "DARK_THEME_QSS QWidget must not specify fixed font-size"
    assert "font-size: 12px;" not in light_qwidget, "LIGHT_THEME_QSS QWidget must not specify fixed font-size"

    # Ensure point size is preserved
    app_font = qapp.font()
    app_font.setPointSize(14)
    qapp.setFont(app_font)

    qapp.setStyleSheet(DARK_THEME_QSS)
    lbl = QLabel("High-DPI Point Size Typography")
    lbl.ensurePolished()

    assert lbl.font().pointSize() == 14, "Label font point size must be preserved"
    assert lbl.font().pixelSize() == -1, "Label font pixel size must not be forced"


def test_qss_scrollbar_thickness(qapp):
    """Verify scrollbars are between 12px and 14px thick for High-DPI accessibility."""
    # Verify no legacy 8px scrollbars remain
    assert "width: 8px;" not in DARK_THEME_QSS, "Legacy 8px scrollbar found in DARK_THEME_QSS"
    assert "height: 8px;" not in DARK_THEME_QSS, "Legacy 8px scrollbar found in DARK_THEME_QSS"
    assert "width: 8px;" not in LIGHT_THEME_QSS, "Legacy 8px scrollbar found in LIGHT_THEME_QSS"
    assert "height: 8px;" not in LIGHT_THEME_QSS, "Legacy 8px scrollbar found in LIGHT_THEME_QSS"

    # Dark theme scrollbars
    qapp.setStyleSheet(DARK_THEME_QSS)
    sb_v_dark = QScrollBar(Qt.Orientation.Vertical)
    sb_h_dark = QScrollBar(Qt.Orientation.Horizontal)
    sb_v_dark.ensurePolished()
    sb_h_dark.ensurePolished()
    assert 12 <= sb_v_dark.sizeHint().width() <= 14, (
        f"Dark vertical scrollbar width ({sb_v_dark.sizeHint().width()}px) must be 12-14px"
    )
    assert 12 <= sb_h_dark.sizeHint().height() <= 14, (
        f"Dark horizontal scrollbar height ({sb_h_dark.sizeHint().height()}px) must be 12-14px"
    )

    # Light theme scrollbars
    qapp.setStyleSheet(LIGHT_THEME_QSS)
    sb_v_light = QScrollBar(Qt.Orientation.Vertical)
    sb_h_light = QScrollBar(Qt.Orientation.Horizontal)
    sb_v_light.ensurePolished()
    sb_h_light.ensurePolished()
    assert 12 <= sb_v_light.sizeHint().width() <= 14, (
        f"Light vertical scrollbar width ({sb_v_light.sizeHint().width()}px) must be 12-14px"
    )
    assert 12 <= sb_h_light.sizeHint().height() <= 14, (
        f"Light horizontal scrollbar height ({sb_h_light.sizeHint().height()}px) must be 12-14px"
    )
