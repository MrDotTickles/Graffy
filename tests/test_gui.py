import os
import sys
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Ensure offscreen platform for headless test execution
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from omnigraph.ui.main_window import MainWindow
from omnigraph.core.project import Project
from omnigraph.ui.samples import SampleProjects


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_main_window_startup(qapp):
    proj = SampleProjects.create_spectroscopy_sample()
    window = MainWindow(project=proj)
    assert window is not None
    assert "Graffy" in window.windowTitle()
    assert window.center_tabs.count() >= 2  # Has sheet and graph tabs

    # Test theme toggle
    window.toggle_theme()
    assert window.is_dark_theme is True
    window.toggle_theme()
    assert window.is_dark_theme is False

    # Test adding a column
    initial_cols = proj.workbooks[0].sheets[0].column_count()
    window.add_column_to_active_sheet()
    assert proj.workbooks[0].sheets[0].column_count() == initial_cols + 1

    # Test loading another sample
    window.load_sample("kinetics")
    assert "Enzyme Kinetics" in window.project.name
    assert len(window.project.graphs) >= 1

    # Test export to pixmap
    gw = window.get_active_graph_widget()
    if gw:
        pix = gw.canvas_widget.plot_manager.export_to_pixmap(dpi=100)
        assert not pix.isNull()
        assert pix.width() > 100
        assert pix.height() > 100

    window.close()


def test_sidebar_sizing_and_window_fit(qapp):
    from PyQt6.QtWidgets import QScrollArea, QToolBar
    proj = SampleProjects.create_spectroscopy_sample()
    window = MainWindow(project=proj)
    window.show()

    # 1. Docks minimum width prevents cutoff
    assert window.dock_explorer.minimumWidth() >= 200
    assert window.dock_properties.minimumWidth() >= 280

    # 2. Property Inspector tabs all wrapped in QScrollArea to prevent vertical/horizontal clipping
    pi = window.property_widget
    assert isinstance(pi.tab_curves, QScrollArea)
    assert isinstance(pi.tab_axes, QScrollArea)
    assert isinstance(pi.tab_legend, QScrollArea)
    assert isinstance(pi.tab_column, QScrollArea)

    # 3. Toolbars are grouped into responsive functional toolbars
    tb_file = window.findChild(QToolBar, "ToolbarFileData")
    tb_plot = window.findChild(QToolBar, "ToolbarPlotAnalysis")
    assert tb_file is not None
    assert tb_plot is not None

    # 4. Project Explorer tree has dynamic scrollbars to prevent clipping long names
    tree = window.explorer_widget.tree
    assert tree.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded

    window.close()

