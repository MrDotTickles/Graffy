import pytest
from PyQt6.QtCore import QPoint, QPointF, Qt
from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QToolButton

from omnigraph.core.project import CurveModel, GraphModel, Project
from omnigraph.core.worksheet import ColumnRole, Workbook, Worksheet
from omnigraph.ui.dialogs.axis_bounds_dialog import AxisBoundsDialog
from omnigraph.ui.graph_view import GraphViewWidget
from omnigraph.ui.main_window import MainWindow
from omnigraph.worksheet_drag import WorksheetDragData


def sample_project():
    project = Project.create_default()
    sheet = project.workbooks[0].sheets[0]
    sheet.columns[0].data = [1, 2, 3]
    sheet.columns[1].data = [10, 11, 12]
    graph = GraphModel(title_text="Measured signal", x_title="Time", y_title="Intensity")
    graph.curves = [CurveModel()]
    project.graphs.append(graph)
    return project, graph


def test_axis_bounds_validate_apply_and_restore_auto(qt_test_application, monkeypatch, tmp_path):
    project, graph = sample_project()
    graph.x_scale = "log10"
    view = GraphViewWidget(graph, project)

    def enter_bounds(dialog):
        _, automatic, minimum, maximum, _, _ = dialog.controls["x"]
        automatic.setChecked(False)
        minimum.setText("0")
        maximum.setText("20")
        dialog._apply()
        assert "logarithmic" in dialog.error.text()
        assert graph.x_auto_limits
        minimum.setText("2e-1")
        dialog._apply()
        return dialog.result()

    monkeypatch.setattr(AxisBoundsDialog, "exec", enter_bounds)
    next(action for action in view.chart_toolbar.actions() if action.text() == "Axis bounds").trigger()
    canvas = view.canvas_widget
    axis = canvas.plot_manager.ax
    assert axis.get_xlim() == pytest.approx((0.2, 20))
    canvas.toolbar.push_current()
    axis.set_xlim(1, 4)
    canvas.toolbar.push_current()
    canvas.toolbar.home()
    assert axis.get_xlim() == pytest.approx((0.2, 20))
    path = tmp_path / "bounds.kgraph"
    project.save_to_file(path)
    saved = Project.load_from_file(path).graphs[0]
    assert (saved.x_auto_limits, saved.x_min, saved.x_max) == (False, 0.2, 20)

    def reset_bounds(dialog):
        dialog.controls["x"][1].setChecked(True)
        dialog._apply()
        return dialog.result()

    monkeypatch.setattr(AxisBoundsDialog, "exec", reset_bounds)
    view.canvas_widget.edit_axis_bounds()
    assert graph.x_auto_limits
    assert view.canvas_widget.plot_manager.ax.get_xlim() != (0.2, 20)


def test_figure_uses_numeric_bounds_for_visible_panels(qt_test_application):
    from omnigraph.graphing.plot_manager import PlotManager

    project, graph = sample_project()
    graph.layout_mode = "stacked_2x1"
    graph.x_auto_limits = graph.y_auto_limits = graph.y_bottom_auto_limits = False
    graph.x_min, graph.x_max = 0, 4
    graph.y_min, graph.y_max = 7, 15
    graph.y_bottom_min, graph.y_bottom_max = -3, 3
    manager = PlotManager(graph, project)
    manager.render()
    for panel in manager.axes:
        assert panel.get_xlim() == pytest.approx((0, 4))
    assert manager.ax.get_ylim() == pytest.approx((7, 15))
    assert manager.ax_bottom.get_ylim() == pytest.approx((-3, 3))

    graph.layout_mode = "single"
    graph.curves.append(CurveModel(axis="secondary"))
    graph.y2_auto_limits = False
    graph.y2_min, graph.y2_max = 20, 50
    manager.render()
    assert manager.ax2.get_ylim() == pytest.approx((20, 50))


def test_double_click_routes_title_y_label_and_tick_to_different_actions(qt_test_application, monkeypatch):
    project, graph = sample_project()
    view = GraphViewWidget(graph, project)
    view.resize(1000, 680)
    view.show()
    qt_test_application.processEvents()
    widget = view.canvas_widget
    canvas = widget.canvas
    canvas.draw()
    observed = []
    monkeypatch.setattr(widget, "edit_graph_title", lambda: observed.append("title"))
    monkeypatch.setattr(widget, "edit_y_title", lambda: observed.append("y label"))
    monkeypatch.setattr(widget, "edit_axis_bounds", lambda axis: observed.append(axis))
    axes = widget.plot_manager.ax
    tick = next(label for label in axes.get_yticklabels()
                if axes.bbox.y0 < label.get_window_extent(canvas.get_renderer()).y0 < axes.bbox.y1)
    for artist in (axes.title, axes.yaxis.label, tick):
        extent = artist.get_window_extent(canvas.get_renderer())
        ratio = canvas.device_pixel_ratio
        x = (extent.x0 + extent.x1) / (2 * ratio)
        y = canvas.height() - (extent.y0 + extent.y1) / (2 * ratio)
        QTest.mouseDClick(canvas, Qt.MouseButton.LeftButton, pos=QPoint(round(x), round(y)))
    assert observed == ["title", "y label", "y"]


def test_worksheet_drop_on_canvas_and_chart_list_keeps_sources_distinct(qt_test_application, monkeypatch):
    project, graph = sample_project()
    workbook = Workbook("Runs")
    sheet = Worksheet.create_default("Sheet1")
    sheet.columns[0].data = [1, 2, 3]
    sheet.columns[1].data = [20, 21, 22]
    sheet.add_column(long_name="Uncertainty", role=ColumnRole.Y_ERR).data = [1, 1, 1]
    sheet.add_column(long_name="High signal").data = [30, 31, 32]
    workbook.sheets.append(sheet)
    project.workbooks.append(workbook)
    second_graph = GraphModel(title="Other chart")
    project.graphs.append(second_graph)
    window = MainWindow(project)
    monkeypatch.setattr(window, "_choose_drop_layout", lambda *args: "add")
    window.resize(1250, 750)
    window.show()
    window._on_explorer_item_activated("graph", graph.title, graph.id)
    qt_test_application.processEvents()
    view = window.get_active_graph_widget()
    mime = WorksheetDragData(project, workbook.name, sheet.name)
    copy = Qt.DropAction.CopyAction
    mouse = Qt.MouseButton.LeftButton
    modifiers = Qt.KeyboardModifier.NoModifier

    def drop(receiver, point):
        enter = QDragEnterEvent(point, copy, mime, mouse, modifiers)
        qt_test_application.sendEvent(receiver, enter)
        assert enter.isAccepted()
        move = QDragMoveEvent(point, copy, mime, mouse, modifiers)
        qt_test_application.sendEvent(receiver, move)
        event = QDropEvent(QPointF(point), copy, mime, mouse, modifiers)
        qt_test_application.sendEvent(receiver, event)
        assert event.isAccepted()
        qt_test_application.processEvents()

    tab_count = window.center_tabs.count()
    receiver = view.canvas_widget.canvas
    drop(receiver, receiver.rect().center())
    assert window.center_tabs.count() == tab_count
    assert [(c.source_workbook, c.y_col_idx) for c in graph.curves] == [("Book1", 1), ("Runs", 1), ("Runs", 3)]
    assert graph.curves[1].y_err_col_idx == 2
    drop(receiver, receiver.rect().center())
    assert len(graph.curves) == 3

    tree = window.explorer_widget.tree
    item = tree.findItems(second_graph.title, Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchRecursive)[0]
    tree.scrollToItem(item)
    drop(tree.viewport(), tree.visualItemRect(item).center())
    assert window.get_active_graph() is second_graph
    assert all(c.source_workbook == workbook.name for c in second_graph.curves)
    assert len(second_graph.curves) == 2

    view = window.get_active_graph_widget()
    data_menu = next(button.menu() for button in view.chart_toolbar.findChildren(QToolButton)
                     if button.text() == "Data")
    data_menu.aboutToShow.emit()
    add_worksheet = next(action.menu() for action in data_menu.actions() if action.text() == "Add worksheet")
    add_worksheet.actions()[0].trigger()
    assert len(second_graph.curves) == 3
    assert second_graph.curves[-1].source_workbook == "Book1"
