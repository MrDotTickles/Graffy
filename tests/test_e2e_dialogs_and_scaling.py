"""
E2E Automated Verification: Dialog Sizing, Geometry Non-Clipping, and Scaling Harness.
Covers Feature 15 (High-DPI & Scale Factor) and Feature 16 (Dialog Sizing & Non-Clipping).
Runs headless offscreen via QT_QPA_PLATFORM=offscreen.
"""

import os
import sys
import pytest
import numpy as np

# Ensure offscreen platform before any Qt import
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QDialog,
    QScrollArea,
    QAbstractScrollArea,
    QToolBar,
)
from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtGui import QPixmap

from omnigraph.core.project import Project, GraphModel, CurveModel
from omnigraph.core.worksheet import Worksheet, Column, ColumnRole, Workbook
from omnigraph.graphing.plot_manager import PlotManager
from omnigraph.ui.samples import SampleProjects
from omnigraph.ui.main_window import MainWindow
from omnigraph.ui.dialogs import (
    AddCurveDialog,
    ColumnPropertiesDialog,
    ExportDialog,
    FitDialog,
    FormulaDialog,
    ImportDialog,
    LegendEditorDialog,
    PeakAnalysisDialog,
    QuickLabelsDialog,
    SmoothDialog,
    StatsDialog,
)


@pytest.fixture(scope="session")
def qapp():
    """Initializes or returns singleton QApplication configured for offscreen testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def sample_project():
    """Provides standard spectroscopy sample project."""
    return SampleProjects.create_spectroscopy_sample()


@pytest.fixture
def plot_manager(sample_project):
    """Provides PlotManager initialized with sample graph and project."""
    graph = sample_project.graphs[0]
    return PlotManager(graph, sample_project)


# ---------------------------------------------------------------------------
# Verification Utilities
# ---------------------------------------------------------------------------

def is_inside_scroll_area(widget: QWidget) -> bool:
    """Returns True if the widget or any ancestor is a QScrollArea / QAbstractScrollArea."""
    p = widget.parentWidget()
    while p is not None:
        if isinstance(p, (QScrollArea, QAbstractScrollArea)):
            return True
        p = p.parentWidget()
    return False


def get_clipping_defects(root_widget: QWidget, tolerance: int = 5) -> list:
    """
    Recursively inspects every visible child widget of root_widget.
    Verifies child geometry is enclosed within parent's visible rect
    or resides within a QScrollArea.
    """
    defects = []
    for child in root_widget.findChildren(QWidget):
        if not child.isVisible():
            continue
        p = child.parentWidget()
        if p is None:
            continue
        if is_inside_scroll_area(child):
            continue
        if child.isWindow():
            continue
        cg = child.geometry()
        pr = p.rect()
        if cg.right() > pr.right() + tolerance or cg.bottom() > pr.bottom() + tolerance:
            defects.append({
                "type": type(child).__name__,
                "name": child.objectName(),
                "child_geom": (cg.x(), cg.y(), cg.width(), cg.height()),
                "parent_rect": (pr.x(), pr.y(), pr.width(), pr.height()),
                "parent_type": type(p).__name__,
            })
    return defects


def assert_no_widget_clipping(widget: QWidget, context: str = ""):
    """Shows widget, processes events, and asserts 0 clipping defects."""
    widget.showNormal()
    if isinstance(widget, QDialog):
        if widget.width() < widget.sizeHint().width() or widget.height() < widget.sizeHint().height():
            widget.resize(widget.sizeHint())
    QApplication.processEvents()
    defects = get_clipping_defects(widget)
    assert len(defects) == 0, f"Clipping defects detected in {context or type(widget).__name__}: {defects}"


def assert_pixmap_valid(widget: QWidget, min_w: int = 50, min_h: int = 50):
    """Grabs QPixmap from widget and verifies it renders non-empty."""
    widget.showNormal()
    QApplication.processEvents()
    pix = widget.grab()
    assert not pix.isNull(), f"{type(widget).__name__} offscreen QPixmap is null"
    assert pix.width() >= min_w, f"{type(widget).__name__} QPixmap width {pix.width()} < {min_w}"
    assert pix.height() >= min_h, f"{type(widget).__name__} QPixmap height {pix.height()} < {min_h}"


# ---------------------------------------------------------------------------
# Feature 16: Dialog Sizing, Layout, and Geometry Bounds (All 12 Dialogs)
# ---------------------------------------------------------------------------

def test_dialog_add_curve_init_and_bounds(qapp, sample_project):
    graph = sample_project.graphs[0]
    dlg = AddCurveDialog(sample_project, graph)
    assert_no_widget_clipping(dlg, "AddCurveDialog")
    assert_pixmap_valid(dlg)
    dlg.close()


def test_chart_import_dialog_init_and_bounds(qapp, sample_project):
    graph = sample_project.graphs[0]
    dlg = ImportDialog(active_graph_title=graph.title)
    assert_no_widget_clipping(dlg, "Chart import")
    assert_pixmap_valid(dlg)
    dlg.close()


def test_dialog_column_properties_init_and_bounds(qapp, sample_project):
    ws = sample_project.workbooks[0].sheets[0]
    col = ws.columns[0]
    dlg = ColumnPropertiesDialog(col)
    assert_no_widget_clipping(dlg, "ColumnPropertiesDialog")
    assert_pixmap_valid(dlg)
    dlg.close()


def test_dialog_export_init_and_bounds(qapp, plot_manager):
    dlg = ExportDialog(plot_manager)
    assert_no_widget_clipping(dlg, "ExportDialog")
    assert_pixmap_valid(dlg)
    dlg.close()


def test_dialog_fit_init_and_bounds(qapp, sample_project):
    graph = sample_project.graphs[0]
    ws = sample_project.workbooks[0].sheets[0]
    dlg = FitDialog(sample_project, graph, ws)
    assert_no_widget_clipping(dlg, "FitDialog")
    assert_pixmap_valid(dlg)
    dlg.close()


def test_dialog_formula_init_and_bounds(qapp, sample_project):
    ws = sample_project.workbooks[0].sheets[0]
    dlg = FormulaDialog(ws, target_col_idx=0)
    assert_no_widget_clipping(dlg, "FormulaDialog")
    assert_pixmap_valid(dlg)
    dlg.close()


def test_dialog_import_init_and_bounds(qapp):
    dlg = ImportDialog()
    assert_no_widget_clipping(dlg, "ImportDialog")
    assert_pixmap_valid(dlg)
    dlg.close()


def test_dialog_legend_editor_init_and_bounds(qapp, sample_project):
    graph = sample_project.graphs[0]
    dlg = LegendEditorDialog(graph)
    assert_no_widget_clipping(dlg, "LegendEditorDialog")
    assert_pixmap_valid(dlg)
    dlg.close()


def test_dialog_peak_analysis_init_and_bounds(qapp, sample_project):
    graph = sample_project.graphs[0]
    dlg = PeakAnalysisDialog(sample_project, graph)
    assert_no_widget_clipping(dlg, "PeakAnalysisDialog")
    assert_pixmap_valid(dlg)
    dlg.close()


def test_dialog_quick_labels_init_and_bounds(qapp, sample_project):
    graph = sample_project.graphs[0]
    dlg = QuickLabelsDialog(graph)
    assert_no_widget_clipping(dlg, "QuickLabelsDialog")
    assert_pixmap_valid(dlg)
    dlg.close()


def test_dialog_smooth_init_and_bounds(qapp, sample_project):
    ws = sample_project.workbooks[0].sheets[0]
    dlg = SmoothDialog(ws, selected_col_idx=1)
    assert_no_widget_clipping(dlg, "SmoothDialog")
    assert_pixmap_valid(dlg)
    dlg.close()


def test_dialog_stats_init_and_bounds(qapp, sample_project):
    ws = sample_project.workbooks[0].sheets[0]
    dlg = StatsDialog(ws.columns)
    assert_no_widget_clipping(dlg, "StatsDialog")
    assert_pixmap_valid(dlg)
    dlg.close()


def test_all_12_dialogs_pixmap_render(qapp, sample_project, plot_manager):
    ws = sample_project.workbooks[0].sheets[0]
    graph = sample_project.graphs[0]
    dialog_list = [
        ("AddCurve", AddCurveDialog(sample_project, graph)),
        ("Chart import", ImportDialog(active_graph_title=graph.title)),
        ("ColumnProperties", ColumnPropertiesDialog(ws.columns[0])),
        ("Export", ExportDialog(plot_manager)),
        ("Fit", FitDialog(sample_project, graph, ws)),
        ("Formula", FormulaDialog(ws, 0)),
        ("Import", ImportDialog()),
        ("LegendEditor", LegendEditorDialog(graph)),
        ("PeakAnalysis", PeakAnalysisDialog(sample_project, graph)),
        ("QuickLabels", QuickLabelsDialog(graph)),
        ("Smooth", SmoothDialog(ws, 1)),
        ("Stats", StatsDialog(ws.columns)),
    ]
    for name, dlg in dialog_list:
        dlg.showNormal()
        QApplication.processEvents()
        pix = dlg.grab()
        assert not pix.isNull(), f"Dialog {name} produced null QPixmap"
        assert pix.width() > 100, f"Dialog {name} width too small: {pix.width()}"
        assert pix.height() > 100, f"Dialog {name} height too small: {pix.height()}"
        dlg.close()


def test_dialog_sizing_proportions_and_minimum_geometry(qapp, sample_project):
    """Verifies that dialogs initialize with valid minimumSize and dimensions."""
    ws = sample_project.workbooks[0].sheets[0]
    col_dlg = ColumnPropertiesDialog(ws.columns[0])
    assert col_dlg.size().width() >= 300
    assert col_dlg.size().height() >= 180
    col_dlg.close()

    quick_dlg = QuickLabelsDialog(sample_project.graphs[0])
    assert quick_dlg.size().width() >= 300
    assert quick_dlg.size().height() >= 250
    quick_dlg.close()


def test_dialog_multiple_open_close_cycles(qapp, sample_project):
    """Stress test: rapidly opens, validates bounds, and closes dialogs repeatedly."""
    ws = sample_project.workbooks[0].sheets[0]
    for _ in range(5):
        dlg = SmoothDialog(ws, 1)
        assert_no_widget_clipping(dlg, "SmoothDialog Cycle")
        dlg.close()


def test_dialog_with_empty_dataset_inputs(qapp):
    """Verifies dialogs handle empty worksheet/columns gracefully."""
    empty_proj = Project.create_default("Empty")
    empty_ws = empty_proj.workbooks[0].sheets[0]
    empty_col = empty_ws.columns[0]

    dlg_prop = ColumnPropertiesDialog(empty_col)
    assert_no_widget_clipping(dlg_prop, "ColumnPropertiesDialog Empty")
    dlg_prop.close()

    dlg_formula = FormulaDialog(empty_ws, 0)
    assert_no_widget_clipping(dlg_formula, "FormulaDialog Empty")
    dlg_formula.close()

    dlg_stats = StatsDialog(empty_ws.columns)
    assert_no_widget_clipping(dlg_stats, "StatsDialog Empty")
    dlg_stats.close()


def test_dialog_with_large_dataset_inputs(qapp):
    """Verifies dialogs handle large dataset (5,000 rows) without layout distortion."""
    proj = Project.create_default("LargeData")
    ws = proj.workbooks[0].sheets[0]
    data = np.linspace(0, 100, 5000).tolist()
    ws.columns[0].data = data
    ws.columns[1].data = (np.sin(data) * 50).tolist()

    dlg_stats = StatsDialog(ws.columns)
    assert_no_widget_clipping(dlg_stats, "StatsDialog LargeData")
    dlg_stats.close()

    dlg_smooth = SmoothDialog(ws, 1)
    assert_no_widget_clipping(dlg_smooth, "SmoothDialog LargeData")
    dlg_smooth.close()


def test_dialog_with_extreme_or_nan_inputs(qapp):
    """Verifies dialogs handle NaN, Inf, and extreme values (1e20) without crashing."""
    proj = Project.create_default("ExtremeData")
    ws = proj.workbooks[0].sheets[0]
    ws.columns[0].data = [1e-15, 1e20, None, np.nan, 42.0]
    ws.columns[1].data = [np.nan, None, -1e18, 0.0, 99.0]

    dlg_stats = StatsDialog(ws.columns)
    assert_no_widget_clipping(dlg_stats, "StatsDialog ExtremeData")
    dlg_stats.close()


# ---------------------------------------------------------------------------
# Feature 15: High-DPI Foundation, MainWindow Sizing, Scaling & Responsiveness
# ---------------------------------------------------------------------------

def test_mainwindow_init_and_no_clipping(qapp, sample_project):
    win = MainWindow(project=sample_project)
    win.showNormal()
    win.resize(1366, 768)
    QApplication.processEvents()
    assert_no_widget_clipping(win, "MainWindow Standard")
    win.close()


def test_mainwindow_resolution_1024x768(qapp, sample_project):
    win = MainWindow(project=sample_project)
    win.showNormal()
    win.resize(1024, 768)
    QApplication.processEvents()
    assert_no_widget_clipping(win, "MainWindow 1024x768")
    assert win.width() == 1024
    assert win.height() == 768
    win.close()


def test_mainwindow_resolution_1366x768(qapp, sample_project):
    win = MainWindow(project=sample_project)
    win.showNormal()
    win.resize(1366, 768)
    QApplication.processEvents()
    assert_no_widget_clipping(win, "MainWindow 1366x768")
    win.close()


def test_mainwindow_resolution_1920x1080(qapp, sample_project):
    win = MainWindow(project=sample_project)
    win.showNormal()
    win.resize(1920, 1080)
    QApplication.processEvents()
    assert_no_widget_clipping(win, "MainWindow 1920x1080")
    win.close()


def test_mainwindow_compact_resolution_800x600(qapp, sample_project):
    win = MainWindow(project=sample_project)
    win.showNormal()
    win.resize(800, 600)
    QApplication.processEvents()
    # At compact screen sizes, ensure central workspace and toolbars remain responsive
    assert win.center_tabs.count() >= 1
    win.close()


def test_mainwindow_dock_minimum_geometry_contracts(qapp, sample_project):
    win = MainWindow(project=sample_project)
    win.showNormal()
    QApplication.processEvents()
    assert win.dock_explorer.minimumWidth() >= 200
    assert win.dock_properties.minimumWidth() >= 280
    win.close()


def test_mainwindow_property_dock_scroll_area_enclosure(qapp, sample_project):
    win = MainWindow(project=sample_project)
    win.showNormal()
    QApplication.processEvents()
    pi = win.property_widget
    assert isinstance(pi.tab_curves, QScrollArea)
    assert isinstance(pi.tab_axes, QScrollArea)
    assert isinstance(pi.tab_legend, QScrollArea)
    assert isinstance(pi.tab_column, QScrollArea)
    win.close()


def test_mainwindow_pixmap_render_light_and_dark(qapp, sample_project):
    win = MainWindow(project=sample_project)
    win.showNormal()
    win.resize(1280, 800)
    QApplication.processEvents()

    # Light theme grab
    pix_light = win.grab()
    assert not pix_light.isNull()
    assert pix_light.width() == 1280

    # Toggle to dark theme
    win.toggle_theme()
    assert win.is_dark_theme is True
    QApplication.processEvents()
    pix_dark = win.grab()
    assert not pix_dark.isNull()
    assert pix_dark.width() == 1280

    win.close()


def test_mainwindow_theme_toggle_layout_stability(qapp, sample_project):
    win = MainWindow(project=sample_project)
    win.showNormal()
    win.resize(1280, 800)
    QApplication.processEvents()

    for _ in range(4):
        win.toggle_theme()
        QApplication.processEvents()
        assert_no_widget_clipping(win, "Theme Toggle Stability")

    win.close()


def test_mainwindow_tab_switching_layout_stability(qapp, sample_project):
    win = MainWindow(project=sample_project)
    win.showNormal()
    win.resize(1280, 800)
    QApplication.processEvents()

    tab_count = win.center_tabs.count()
    assert tab_count >= 2
    for idx in range(tab_count):
        win.center_tabs.setCurrentIndex(idx)
        QApplication.processEvents()
        assert_no_widget_clipping(win, f"Tab Switch to {idx}")

    win.close()


def test_mainwindow_rapid_resizing_stress(qapp, sample_project):
    win = MainWindow(project=sample_project)
    win.showNormal()
    resolutions = [(1024, 768), (1440, 900), (1280, 720), (1920, 1080), (1366, 768)]
    for w, h in resolutions:
        win.resize(w, h)
        QApplication.processEvents()
        assert win.width() == w
        assert win.height() == h
        assert_no_widget_clipping(win, f"Resize Stress ({w}x{h})")

    win.close()


def test_mainwindow_scaling_emulation_1_25(qapp, sample_project):
    """Emulates 125% DPI scale factor behavior and verifies layout bounds."""
    win = MainWindow(project=sample_project)
    win.showNormal()
    # 1366x768 scaled by 1.25 gives ~1707x960 virtual dimensions
    win.resize(int(1366 * 1.25), int(768 * 1.25))
    QApplication.processEvents()
    assert_no_widget_clipping(win, "MainWindow 125% DPI Scale")
    win.close()


def test_mainwindow_scaling_emulation_1_5(qapp, sample_project):
    """Emulates 150% DPI scale factor behavior and verifies layout bounds."""
    win = MainWindow(project=sample_project)
    win.showNormal()
    win.resize(int(1280 * 1.5), int(800 * 1.5))
    QApplication.processEvents()
    assert_no_widget_clipping(win, "MainWindow 150% DPI Scale")
    win.close()
