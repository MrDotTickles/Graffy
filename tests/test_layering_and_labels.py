"""
Automated test suite verifying multi-curve layering, secondary twin-axis & stacked layouts,
quick label editing, and window scaling responsiveness.
"""

import os
import sys
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QResizeEvent

# Ensure headless execution
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from omnigraph.core.project import Project, GraphModel, CurveModel
from omnigraph.core.worksheet import Workbook, Worksheet, Column, ColumnRole
from omnigraph.graphing.plot_manager import PlotManager
from omnigraph.graphing.canvas import OmniCanvas
from omnigraph.ui.dialogs.quick_labels_dialog import QuickLabelsDialog
from omnigraph.ui.dialogs.add_curve_dialog import AddCurveDialog
from omnigraph.ui.main_window import MainWindow
from omnigraph.ui.samples import SampleProjects


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_curve_layering_reordering_visibility():
    """Verify layering multiple curves, reordering up/down, and toggling visibility."""
    wb = Workbook(name="Book1")
    ws = Worksheet(name="DataSheet")

    col_x = Column(name="A", long_name="Time", units="s", role=ColumnRole.X, data=[0, 1, 2, 3, 4])
    col_y1 = Column(name="B", long_name="Signal 1", units="mV", role=ColumnRole.Y, data=[10, 20, 15, 30, 25])
    col_y2 = Column(name="C", long_name="Signal 2", units="mV", role=ColumnRole.Y, data=[5, 12, 18, 22, 28])
    col_y3 = Column(name="D", long_name="Signal 3", units="mV", role=ColumnRole.Y, data=[1, 3, 7, 12, 19])

    ws.columns = [col_x, col_y1, col_y2, col_y3]
    wb.sheets.append(ws)
    project = Project(name="LayeringTest", workbooks=[wb])

    graph = GraphModel(title="MultiLayerGraph", title_text="Layered Signals")
    c1 = CurveModel(source_workbook="Book1", source_sheet="DataSheet", x_col_idx=0, y_col_idx=1, label="Signal 1")
    c2 = CurveModel(source_workbook="Book1", source_sheet="DataSheet", x_col_idx=0, y_col_idx=2, label="Signal 2")
    c3 = CurveModel(source_workbook="Book1", source_sheet="DataSheet", x_col_idx=0, y_col_idx=3, label="Signal 3")

    graph.add_curve(c1)
    graph.add_curve(c2)
    graph.add_curve(c3)
    project.graphs.append(graph)

    assert len(graph.curves) == 3
    assert graph.curves[0].label == "Signal 1"
    assert graph.curves[1].label == "Signal 2"
    assert graph.curves[2].label == "Signal 3"

    # Test Move Down
    graph.move_curve_down(0)
    assert graph.curves[0].label == "Signal 2"
    assert graph.curves[1].label == "Signal 1"

    # Test Move Up
    graph.move_curve_up(1)
    assert graph.curves[0].label == "Signal 1"
    assert graph.curves[1].label == "Signal 2"

    # Test Toggle Visibility
    assert graph.curves[1].visible is True
    graph.toggle_curve_visibility(1)
    assert graph.curves[1].visible is False

    # Test Render with PlotManager - hidden curve must be excluded
    pm = PlotManager(graph, project)
    pm.render()
    rendered_labels = [label for label, _, _ in pm.rendered_curves]
    assert "Signal 1" in rendered_labels
    assert "Signal 2" not in rendered_labels
    assert "Signal 3" in rendered_labels
    assert len(pm.rendered_curves) == 2

    # Make visible again and re-render
    graph.toggle_curve_visibility(1)
    pm.render()
    assert len(pm.rendered_curves) == 3

    # Test Remove Curve
    graph.remove_curve_at(2)
    assert len(graph.curves) == 2
    pm.render()
    assert len(pm.rendered_curves) == 2


def test_twin_x_and_stacked_layering():
    """Verify secondary Y axis (twin_x) and stacked 2x1 panel layouts."""
    project = SampleProjects.create_dual_axis_sample()
    graph = project.graphs[0]

    # Verify dual axis setup
    assert any(c.axis == "secondary" for c in graph.curves)

    pm = PlotManager(graph, project)
    pm.render()
    assert pm.ax is not None
    assert pm.ax2 is not None

    # Test Stacked 2x1 panel layout
    graph.layout_mode = "stacked_2x1"
    graph.curves[0].layer_index = 0
    graph.curves[1].layer_index = 1
    graph.y_bottom_title = "Reactor Pressure (bar)"

    pm_stacked = PlotManager(graph, project)
    pm_stacked.render()
    assert pm_stacked.ax is not None
    assert pm_stacked.ax_bottom is not None
    assert pm_stacked.ax_bottom.get_ylabel() == "Reactor Pressure (bar)"


def test_graph_label_setters_and_quick_labels_dialog(qapp):
    """Verify graph label setters and QuickLabelsDialog modification."""
    project = SampleProjects.create_spectroscopy_sample()
    graph = project.graphs[0]

    # Model setters
    graph.set_title("Calibrated UV-Vis Absorption")
    graph.set_x_title("Wavelength λ (nm)")
    graph.set_y_title("Absorbance A (a.u.)")
    graph.set_y2_title("Fluorescence Intensity")

    assert graph.title_text == "Calibrated UV-Vis Absorption"
    assert graph.x_title == "Wavelength λ (nm)"
    assert graph.y_title == "Absorbance A (a.u.)"
    assert graph.y2_title == "Fluorescence Intensity"

    # Test QuickLabelsDialog
    dlg = QuickLabelsDialog(graph)
    assert dlg.txt_title.text() == "Calibrated UV-Vis Absorption"
    assert dlg.txt_x.text() == "Wavelength λ (nm)"
    assert dlg.txt_y.text() == "Absorbance A (a.u.)"

    # Modify via dialog
    dlg.txt_title.setText("Dialog Edited Title")
    dlg.txt_x.setText("Wavelength (angstroms)")
    dlg.txt_y.setText("Optical Density (OD)")
    if dlg.curve_edits:
        dlg.curve_edits[0].setText("Custom Compound Alpha")

    dlg._on_accept()

    assert graph.title_text == "Dialog Edited Title"
    assert graph.x_title == "Wavelength (angstroms)"
    assert graph.y_title == "Optical Density (OD)"
    if graph.curves:
        assert graph.curves[0].label == "Custom Compound Alpha"

    dlg.close()


def test_canvas_window_scaling_and_resize(qapp):
    """Verify OmniCanvas responsive resizing and scaling without letterboxing or error."""
    project = SampleProjects.create_spectroscopy_sample()
    graph = project.graphs[0]

    canvas = OmniCanvas(graph, project)
    # Check Expanding policy
    assert canvas.sizePolicy().horizontalPolicy().value != 0
    assert canvas.sizePolicy().verticalPolicy().value != 0

    # Simulate Fullscreen resize event (e.g. 1920x1080)
    event_large = QResizeEvent(QSize(1920, 1080), QSize(800, 600))
    canvas.resizeEvent(event_large)
    canvas.refresh()

    # Simulate scaled down resize event (e.g. 900x650)
    event_small = QResizeEvent(QSize(900, 650), QSize(1920, 1080))
    canvas.resizeEvent(event_small)
    canvas.refresh()

    # Pixmap generation
    pix = canvas.plot_manager.export_to_pixmap(dpi=150)
    assert not pix.isNull()
    assert pix.width() > 0
    assert pix.height() > 0

    canvas.close()


def test_main_window_layering_and_label_integration(qapp):
    """Verify full MainWindow workflow: layering columns from worksheet and label editing."""
    project = SampleProjects.create_spectroscopy_sample()
    window = MainWindow(project=project)
    window.show()

    # Verify window minimum sizing
    assert window.minimumWidth() >= 800
    assert window.minimumHeight() >= 600

    active_graph = window.get_active_graph()
    assert active_graph is not None
    initial_curve_count = len(active_graph.curves)

    # Layer a selected column onto the active graph
    sw = window.get_active_spreadsheet_widget()
    if sw:
        # Select column 1
        sw.table_view.selectColumn(1)

    window.add_selected_columns_to_active_graph(plot_type="line")
    assert len(active_graph.curves) == initial_curve_count + 1

    # Verify active graph widget renders the new curve
    gw = window.get_active_graph_widget()
    if gw:
        assert len(gw.canvas_widget.plot_manager.rendered_curves) >= initial_curve_count + 1

    window.close()
