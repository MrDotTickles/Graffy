"""Exercise the worksheet transpose, chart overlays, and pointer interactions."""

import io
from copy import deepcopy

from matplotlib.backend_bases import MouseEvent
from matplotlib.collections import PolyCollection
from PyQt6.QtCore import QItemSelection, QItemSelectionModel, QMimeData, Qt
from PyQt6.QtWidgets import QApplication, QMessageBox

from omnigraph.graphing.plot_manager import PlotManager
from omnigraph.ui.dialogs.annotation_dialog import AnnotationDialog, AnnotationListDialog
from omnigraph.ui.dialogs.fit_dialog import FitDialog
from omnigraph.ui.graph_view import GraphViewWidget
from omnigraph.ui.spreadsheet_view import SpreadsheetWidget

from test_chart_annotations import sample_chart


def test_transpose_selection_and_paste_undo(monkeypatch):
    project, _ = sample_chart()
    worksheet = project.workbooks[0].sheets[0]
    for column in worksheet.columns:
        column.data = [None] * 8
    worksheet.columns[0].data[0] = "Concentration"
    worksheet.columns[1].data[0] = 42
    worksheet.columns[1].mask_row(0)
    widget = SpreadsheetWidget(worksheet)
    selection = QItemSelection(widget.model.index(0, 0), widget.model.index(0, 1))
    widget.table_view.selectionModel().select(selection, QItemSelectionModel.SelectionFlag.ClearAndSelect)
    before = deepcopy(worksheet.to_dict())
    widget.transpose_selection()
    assert worksheet.columns[0].data[:2] == ["Concentration", 42]
    assert worksheet.columns[0].is_row_masked(1)
    assert worksheet.columns[1].get_value(0) is None
    widget.undo()
    assert worksheet.to_dict() == before
    widget.redo()
    assert worksheet.columns[0].get_value(1) == 42

    QApplication.clipboard().setText("10\t20\t30")
    widget.table_view.setCurrentIndex(widget.model.index(3, 1))
    widget.paste_selection(transpose=True)
    assert worksheet.columns[1].data[3:6] == [10, 20, 30]

    def unexpected_confirmation(*args):
        raise AssertionError("Undoable worksheet deletion should not require confirmation.")

    monkeypatch.setattr(QMessageBox, "question", unexpected_confirmation)
    widget._delete_row_ranges([(1, 1)], "Delete row")
    widget.undo()
    assert worksheet.columns[0].get_value(1) == 42
    widget.delete_selected_columns([1])
    widget.undo()
    assert worksheet.columns[1].data[3:6] == [10, 20, 30]


def test_fit_visibility_and_band_ownership(qt_test_application):
    project, graph = sample_chart()
    sheet = project.workbooks[0].sheets[0]
    other = sheet.add_column()
    other.data = [18, 28, 27, 36, 42, 53, 66]
    source = graph.curves[0]
    other_curve = type(source)(source_sheet=source.source_sheet, source_workbook=source.source_workbook, y_col_idx=2)
    graph.add_curve(other_curve)
    view = GraphViewWidget(graph, project)

    for column in (1, 2):
        fit = FitDialog(project, active_graph=graph)
        fit.combo_y_col.setCurrentIndex(fit.combo_y_col.findData(column))
        fit.chk_fit_line.setChecked(column == 2)
        fit.chk_conf_band.setChecked(column == 1)
        fit._on_accept()
        assert fit.result()
    view.record_added_fit_overlays({source.id, other_curve.id}, set())
    first, second = [a for a in graph.annotations if a["band_kind"] == "confidence"]
    assert first["fit_curve_id"] != second["fit_curve_id"]
    assert first["upper_data"] != second["upper_data"]
    def visible_bands():
        return sum(isinstance(a, PolyCollection) for a in view.canvas_widget.plot_manager.ax.collections)

    assert visible_bands() == 1
    manager = AnnotationListDialog(
        graph, view._edit_analysis_overlay, view._remove_analysis_overlay,
        toggle=view._toggle_analysis_overlay, analysis=True,
    )
    manager.items.item(0).setCheckState(Qt.CheckState.Checked)
    assert graph.curves[2].visible
    manager.items.item(2).setCheckState(Qt.CheckState.Unchecked)
    assert not first["visible"]
    assert visible_bands() == 0
    view.undo()
    assert first["visible"] and visible_bands() == 1


def test_pasted_scripts_are_saved_and_exported_as_paths():
    placement = {"type": "text", "x": 2, "y": 4}
    editor = AnnotationDialog(placement, adding=True)
    clipboard = QMimeData()
    clipboard.setHtml('<b>Rate</b> (µmol·s<sup>−1</sup>) and <span style="color:#773399">CO<sub>2</sub></span>')
    editor.text.insertFromMimeData(clipboard)
    editor._save()
    saved = editor.result_annotation
    assert any(run.get("script") == "super" for run in saved["runs"])
    assert any(run.get("script") == "sub" for run in saved["runs"])
    assert any(run.get("bold") and run["text"] == "Rate" for run in saved["runs"])
    reopened = AnnotationDialog(saved)
    reopened._save()
    assert reopened.result_annotation["runs"] == saved["runs"]

    project, graph = sample_chart()
    graph.annotations.append(saved)
    manager = PlotManager(graph, project)
    manager.render()
    target = io.BytesIO()
    manager.export_image(target, file_format="svg")
    assert "#773399" in target.getvalue().decode()
    assert manager.export_png_bytes(dpi=84).startswith(b"\x89PNG")


def test_pointer_hover_and_note_handles(qt_test_application):
    project, graph = sample_chart(split=True)
    view = GraphViewWidget(graph, project)
    view.resize(1100, 700)
    view.show()
    qt_test_application.processEvents()
    host = view.canvas_widget
    canvas = host.canvas
    manager = host.plot_manager
    canvas.draw()

    x, y = manager.axes[1].transData.transform((3, 6))
    host._on_motion(MouseEvent("motion_notify_event", canvas, x, y))
    assert not host._hover_label.isHidden() and "Row 3" in host._hover_label.text()
    host._on_motion(MouseEvent("motion_notify_event", canvas, 3, 3))
    assert host._hover_label.isHidden()

    note = {"type": "text", "text": "Peak", "x": 3, "y": 5, "panel": 1, "font_size": 12}
    view._change_annotation(note, None, note, "Add note")
    host._select_note(note)
    canvas.draw()
    _, _, rotate, resize = host._note_handles(canvas.get_renderer())
    for point, dx, dy, field in ((resize, 45, -22, "font_size"), (rotate, -45, 28, "rotation")):
        x, y = point
        host._on_canvas_click(MouseEvent("button_press_event", canvas, x, y, button=1))
        host._finish_note_drag(MouseEvent("button_release_event", canvas, x + dx, y + dy, button=1))
        assert note[field] != {"font_size": 12, "rotation": 0}[field]
        view.undo()
        canvas.draw()
    assert note["font_size"] == 12 and "rotation" not in note
