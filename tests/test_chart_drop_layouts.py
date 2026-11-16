from copy import deepcopy

import pytest
from PyQt6.QtCore import QPoint, QPointF, QMimeData, Qt, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent
from PyQt6.QtTest import QTest

from omnigraph.core.chart_drop import create_drop_figure, worksheet_curves
from omnigraph.core.project import CurveModel, GraphModel, Project
from omnigraph.graphing.plot_manager import PlotManager
from omnigraph.ui.dialogs.chart_drop_dialog import ChartDropDialog
from omnigraph.ui.dialogs.import_dialog import ImportDialog
from omnigraph.ui.main_window import MainWindow
from omnigraph.worksheet_drag import WorksheetDragData


def project_with_traces():
    project = Project.create_default()
    workbook = project.workbooks[0]
    sheet = workbook.sheets[0]
    sheet.columns[0].long_name = "Wavelength"
    sheet.columns[0].units = "nm"
    sheet.columns[0].data = [450, 500, 550, 600]
    sheet.columns[1].long_name = "Signal"
    sheet.columns[1].units = "V"
    sheet.columns[1].data = [1, 4, 6, 2]
    incoming = deepcopy(sheet)
    incoming.name = "Second run"
    incoming.columns[1].data = [2, 6, 7, 3]
    workbook.sheets.append(incoming)
    graph = GraphModel(title="First run")
    graph.add_curve(CurveModel(label="Reference", plot_type="line"))
    project.graphs.append(graph)
    return project, graph, incoming


def test_layout_tiles_return_the_selected_layout(qt_test_application):
    chooser = ChartDropDialog("Second run.csv", "First run")
    chooser.show()
    qt_test_application.processEvents()
    tiles = chooser.picker.tiles
    for key, button in tiles.items():
        assert not button.icon().isNull()
        button.click()
        assert chooser.result() == chooser.DialogCode.Accepted
        assert chooser.choice == key

    chooser = ChartDropDialog("Second run.csv", "First run")
    chooser.show()
    chooser.activateWindow()
    qt_test_application.processEvents()
    tiles = chooser.picker.tiles
    tiles["add"].setFocus()
    QTest.keyClick(tiles["add"], Qt.Key.Key_Right)
    assert tiles["side_by_side"].hasFocus()
    QTest.keyClick(tiles["side_by_side"], Qt.Key.Key_Return)
    assert chooser.choice == "side_by_side"


def test_side_by_side_creates_independent_linked_axes_and_saves_them(monkeypatch, tmp_path):
    project, original, incoming = project_with_traces()
    incoming.columns[1].units = "mV"
    state = original.to_dict()
    window = MainWindow(project)
    monkeypatch.setattr(window, "_choose_drop_layout", lambda *args: "side_by_side")
    window._add_worksheet_to_chart("Book1", incoming.name, original.id)
    comparison = window.get_active_graph()
    assert original.to_dict() == state
    assert comparison is not original
    assert [(c.source_sheet, c.layer_index) for c in comparison.curves] == [("Sheet1", 0), (incoming.name, 1)]
    assert comparison.curves[0].id != original.curves[0].id

    comparison.right_panel_x_auto_limits = False
    comparison.right_panel_x_min, comparison.right_panel_x_max = 420, 650
    path = tmp_path / "comparison.kgraph"
    project.save_to_file(path)
    restored = Project.load_from_file(path)
    manager = PlotManager(restored.graphs[-1], restored)
    manager.render()
    left, right = manager.axes
    assert left.get_ylabel() == "Signal (V)"
    assert right.get_ylabel() == "Signal (mV)"
    assert right.get_xlim() == pytest.approx((420, 650))
    assert left.get_xlim() != pytest.approx(right.get_xlim())
    assert len(left.lines) == len(right.lines) == 1
    assert len(left.get_legend().get_texts()) == 2


def test_waterfall_offsets_two_traces_and_hides_y_axis():
    project, original, incoming = project_with_traces()
    draft = GraphModel()
    series, _ = worksheet_curves(incoming, "Book1", draft, "line_symbol")
    graph = create_drop_figure(project, original, series, "waterfall")
    manager = PlotManager(graph, project)
    manager.render()
    assert graph.waterfall_enabled and not original.waterfall_enabled
    assert not manager.ax.yaxis.get_visible()
    assert manager.ax.lines[1].get_ydata()[0] > incoming.columns[1].data[0]

    incoming.columns[1].units = "mV"
    with pytest.raises(ValueError, match="matching X and Y units"):
        create_drop_figure(project, original, series, "waterfall")


def test_file_drop_can_make_new_chart_and_cancel_without_import(monkeypatch, tmp_path):
    project, original, _ = project_with_traces()
    window = MainWindow(project)
    path = tmp_path / "dropped.csv"
    path.write_text("Time,Signal A,Signal B\n1,2,3\n2,3,5\n3,5,4\n", encoding="utf-8")
    sheets = len(project.workbooks[0].sheets)
    monkeypatch.setattr(window, "_choose_drop_layout", lambda *args: None)
    window._drop_files_onto_chart([str(path)], original)
    assert len(project.graphs) == 1
    assert len(project.workbooks[0].sheets) == sheets

    def accept(dialog):
        assert dialog.series_combo.currentData() == "all"
        dialog._on_accept()
        return dialog.result()

    monkeypatch.setattr(ImportDialog, "exec", accept)
    monkeypatch.setattr(window, "_choose_drop_layout", lambda *args: "new")
    window._drop_files_onto_chart([str(path)], original)
    graph = window.get_active_graph()
    assert graph is not original
    assert len(original.curves) == 1
    assert [(c.source_sheet, c.y_col_idx) for c in graph.curves] == [("dropped", 1), ("dropped", 2)]



def test_side_by_side_from_a_blank_chart_keeps_each_file_together(monkeypatch, tmp_path):
    project = Project.create_default()
    target = GraphModel(title="Blank chart")
    project.graphs.append(target)
    window = MainWindow(project)
    paths = [tmp_path / "First.csv", tmp_path / "Second.csv"]
    for path in paths:
        path.write_text("Time,Signal A,Signal B\n1,2,3\n2,3,5\n3,5,4\n", encoding="utf-8")

    def accept(dialog):
        dialog._on_accept()
        return dialog.result()

    monkeypatch.setattr(ImportDialog, "exec", accept)
    monkeypatch.setattr(window, "_choose_drop_layout", lambda *args: "side_by_side")
    window._drop_files_onto_chart([str(path) for path in paths], target)
    graph = window.get_active_graph()
    assert graph is not target and not target.curves
    assert sorted((curve.source_sheet, curve.layer_index) for curve in graph.curves) == [
        ("First", 0), ("First", 0), ("Second", 1), ("Second", 1),
    ]



@pytest.mark.parametrize(("source", "mode"), [("worksheet", "waterfall"), ("file", "side_by_side")])
def test_drop_on_visual_tile_uses_layout_without_opening_picker(qt_test_application, monkeypatch, tmp_path, source, mode):
    project, original, incoming = project_with_traces()
    window = MainWindow(project)
    window.resize(1300, 800)
    window.show()
    window._on_explorer_item_activated("graph", original.title, original.id)
    qt_test_application.processEvents()
    canvas = window.get_active_graph_widget().canvas_widget
    receiver = canvas.canvas
    if source == "worksheet":
        mime = WorksheetDragData(project, "Book1", incoming.name)
    else:
        path = tmp_path / "Dropped.csv"
        path.write_text("Wavelength,Signal\n450,2\n500,6\n550,7\n600,3\n", encoding="utf-8")
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(path))])

        def accept(dialog):
            dialog._on_accept()
            return dialog.result()

        monkeypatch.setattr(ImportDialog, "exec", accept)
    def unexpected_picker(*args):
        pytest.fail("Dropping on a tile should use that layout immediately.")
    monkeypatch.setattr(window, "_choose_drop_layout", unexpected_picker)

    copy = Qt.DropAction.CopyAction
    mouse = Qt.MouseButton.LeftButton
    modifiers = Qt.KeyboardModifier.NoModifier
    start = receiver.rect().bottomRight() - QPoint(8, 8)
    try:
        enter = QDragEnterEvent(start, copy, mime, mouse, modifiers)
        qt_test_application.sendEvent(receiver, enter)
        assert enter.isAccepted()
        picker = canvas._drop_picker
        assert picker.isVisible()

        qt_test_application.sendEvent(receiver, QDragLeaveEvent())
        assert not picker.isVisible()
        qt_test_application.sendEvent(receiver, QDragEnterEvent(start, copy, mime, mouse, modifiers))

        tile = picker.tiles[mode]
        point = receiver.mapFromGlobal(tile.mapToGlobal(tile.rect().center()))
        move = QDragMoveEvent(point, copy, mime, mouse, modifiers)
        qt_test_application.sendEvent(receiver, move)
        assert picker.active_layout == mode
        drop = QDropEvent(QPointF(point), copy, mime, mouse, modifiers)
        qt_test_application.sendEvent(receiver, drop)
        assert drop.isAccepted()
        assert not picker.isVisible()
        qt_test_application.processEvents()
        graph = window.get_active_graph()
        assert graph is not original and len(original.curves) == 1
        assert graph.waterfall_enabled if mode == "waterfall" else graph.layout_mode == "grid_1x2"
    finally:
        window._remember_saved_state()
        window.close()
