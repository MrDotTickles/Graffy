"""Exercise annotation editing, dragging, history, export, and prior projects."""

from copy import deepcopy

import pytest
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtTest import QTest

from omnigraph.core.project import CurveModel, GraphModel, Project
from omnigraph.graphing.plot_manager import PlotManager
from omnigraph.ui.dialogs.annotation_dialog import AnnotationDialog, AnnotationListDialog
from omnigraph.ui.dialogs.peak_dialog import PeakAnalysisDialog
from omnigraph.ui.main_window import MainWindow


def sample_chart(*, split=False):
    project = Project.create_default()
    sheet = project.workbooks[0].sheets[0]
    sheet.columns[0].data = [1, 2, 3, 4, 5, 6, 7]
    sheet.columns[1].data = [2, 4, 6, 8, 6, 4, 2]
    graph = GraphModel(title="Measured trace", x_title="Time", y_title="Response")
    graph.add_curve(CurveModel(plot_type="line"))
    if split:
        graph.layout_mode = "grid_1x2"
        graph.comparison_panels = True
        graph.add_curve(CurveModel(plot_type="line", layer_index=1))
    project.graphs.append(graph)
    return project, graph


def canvas_point(canvas, axes, x, y):
    px, py = axes.transData.transform((x, y))
    ratio = canvas.device_pixel_ratio
    return QPoint(round(px / ratio), round(canvas.height() - py / ratio))


def test_place_edit_and_drag_note_on_right_panel(monkeypatch, qt_test_application, tmp_path):
    project, graph = sample_chart(split=True)
    window = MainWindow(project)
    window.resize(1350, 810)
    window.show()
    window.activateWindow()
    window._on_explorer_item_activated("graph", graph.title, graph.id)
    qt_test_application.processEvents()
    view = window.get_active_graph_widget()
    canvas = view.canvas_widget.canvas
    manager = view.canvas_widget.plot_manager
    dialogs = []

    def accept(dialog):
        dialogs.append(dialog.windowTitle())
        dialog.text.setPlainText("Peak\nresponse" if len(dialogs) == 1 else "Updated note")
        dialog.size.setValue(18)
        dialog.rotation.setValue(-30)
        dialog.color.set_color("#8139a5")
        dialog.background.set_color("#f4ddff")
        dialog.bold.setChecked(True)
        dialog._save()
        return dialog.result()

    monkeypatch.setattr(AnnotationDialog, "exec", accept)
    view.annotation_menu_button.menu().actions()[0].trigger()
    assert view.canvas_widget._placing_note
    QTest.keyClick(canvas, Qt.Key.Key_Escape)
    assert not view.canvas_widget._placing_note and not graph.annotations

    view.annotation_menu_button.menu().actions()[0].trigger()
    right = manager.axes[1]
    canvas.draw()
    QTest.mouseClick(canvas, Qt.MouseButton.LeftButton, pos=canvas_point(canvas, right, 3, 5))
    assert dialogs == ["Add text note"]
    note, artist = manager.annotation_artists[0]
    assert artist.axes is manager.axes[1] and note["panel"] == 1
    assert artist.get_fontsize() == 18 and artist.get_rotation() == 330
    assert artist.get_color() == "#8139a5" and artist.get_bbox_patch() is not None

    canvas.draw()
    extent = artist.get_window_extent(canvas.get_renderer())
    ratio = canvas.device_pixel_ratio
    point = QPoint(round((extent.x0 + extent.x1) / (2 * ratio)),
                   round(canvas.height() - (extent.y0 + extent.y1) / (2 * ratio)))
    QTest.mouseDClick(canvas, Qt.MouseButton.LeftButton, pos=point)
    assert dialogs[-1] == "Edit text note"
    assert note["text"] == "Updated note"

    _, artist = manager.annotation_artists[0]
    canvas.draw()
    extent = artist.get_window_extent(canvas.get_renderer())
    point = QPoint(round((extent.x0 + extent.x1) / (2 * ratio)),
                   round(canvas.height() - (extent.y0 + extent.y1) / (2 * ratio)))
    moved = point + QPoint(38, 18)
    before = (note["x"], note["y"])
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=point)
    QTest.mouseMove(canvas, moved)
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=moved)
    assert (note["x"], note["y"]) != before
    assert view.undo_stack.undoText() == "Move text note"
    window.undo_action()
    assert (note["x"], note["y"]) == before
    window.redo_action()

    project_file = tmp_path / "annotation.kgraph"
    project.save_to_file(project_file)
    restored = Project.load_from_file(project_file)
    exported = PlotManager(restored.graphs[0], restored)
    exported.render()
    saved, saved_artist = exported.annotation_artists[0]
    assert saved == note
    assert saved_artist.axes is exported.axes[1]
    assert exported.export_png_bytes(dpi=72).startswith(bytes.fromhex("89504e47"))
    window.close()


def test_annotation_undo_keeps_other_notes_and_worksheet_history(qt_test_application):
    project, graph = sample_chart()
    window = MainWindow(project)
    sheet_tab = window.get_active_spreadsheet_widget()
    sheet_tab.model.setData(sheet_tab.model.index(0, 1), 123)
    assert sheet_tab.undo_stack.canUndo()
    window._on_explorer_item_activated("graph", graph.title, graph.id)
    view = window.get_active_graph_widget()
    legacy = {"type": "text", "text": "Old project note", "x": 1, "y": 3}
    graph.annotations.append(legacy)
    view.canvas_widget.refresh()
    assert window.act_undo.isEnabled()  # Worksheet history remains available before the first chart edit.
    line = {"type": "ref_line", "orientation": "h", "value": 5}
    view._change_annotation(line, None, line, "Add reference line")
    newer = {"type": "band", "x_data": [1, 2], "lower_data": [2, 3], "upper_data": [3, 4]}
    graph.annotations.append(newer)
    assert window.act_undo.isEnabled()

    window.undo_action()
    assert graph.annotations == [legacy, newer]
    assert sheet_tab.worksheet.columns[1].data[0] == 123
    window.close_current_tab()
    qt_test_application.processEvents()
    window._on_explorer_item_activated("graph", graph.title, graph.id)
    assert window.act_redo.isEnabled()
    window.redo_action()
    assert graph.annotations == [legacy, line, newer]
    view = window.get_active_graph_widget()
    manager = AnnotationListDialog(graph, view._edit_annotation, view._remove_annotation)
    manager.items.setCurrentRow(0)
    manager.remove_button.click()
    assert graph.annotations == [line, newer]
    window.undo_action()
    assert graph.annotations == [legacy, line, newer]
    window._remember_saved_state()
    window.close()


def test_invalid_math_does_not_change_the_note():
    original = {"type": "text", "text": "Original", "x": 0, "y": 0}
    dialog = AnnotationDialog(original)
    dialog.text.setPlainText(r"$\unknowncommand$")
    dialog.math.setChecked(True)
    dialog._save()
    assert dialog.result_annotation is None and dialog.error.text()
    assert original["text"] == "Original"
    dialog.math.setChecked(False)
    dialog._save()
    assert dialog.result_annotation["parse_math"] is False


def test_peak_marks_undo_as_one_action_without_removing_report(monkeypatch):
    project, graph = sample_chart()
    window = MainWindow(project)
    window._on_explorer_item_activated("graph", graph.title, graph.id)
    def accept(dialog):
        dialog.spn_distance.setValue(1)
        dialog._on_accept()
        return dialog.result()
    monkeypatch.setattr(PeakAnalysisDialog, "exec", accept)
    window.open_peak_analysis_wizard()
    expected = deepcopy(graph.annotations)
    assert project.reports and expected
    window._on_explorer_item_activated("graph", graph.title, graph.id)
    window.undo_action()
    assert graph.annotations == [] and len(project.reports) == 1
    window.redo_action()
    assert graph.annotations == expected and len(project.reports) == 1
    window._remember_saved_state()
    window.close()
