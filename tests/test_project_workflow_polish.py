"""Regression coverage for save recovery, plotted selection and reusable charts."""
import json

from PyQt6.QtCore import QItemSelectionModel, QStandardPaths
from PyQt6.QtWidgets import QMessageBox
import pytest

from omnigraph.core.plot_editing import rebind_chart_data
from omnigraph.core.project import CurveModel, GraphModel, Project
from omnigraph.ui.dialogs.import_dialog import ImportDialog
from omnigraph.ui.dialogs.replace_data_dialog import ReplaceDataDialog
from omnigraph.ui.main_window import MainWindow


def test_interrupted_overwrite_preserves_project(tmp_path, monkeypatch):
    project = Project.create_default("Original")
    path = tmp_path / "project.kgraph"
    project.save_to_file(path)
    original = path.read_bytes()

    def fail_mid_write(data, stream, **kwargs):
        stream.write("{")
        raise OSError("interrupted write")

    monkeypatch.setattr(json, "dump", fail_mid_write)
    with pytest.raises(OSError):
        project.save_to_file(path)
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]


def test_recovery_opens_unsaved_copy_without_overwriting_project(qt_test_application, tmp_path, monkeypatch):
    monkeypatch.setattr(QStandardPaths, "writableLocation", lambda *_: str(tmp_path))
    saved_file = tmp_path / "saved.kgraph"
    project = Project.create_default("Example")
    project.save_to_file(str(saved_file))
    first = MainWindow(project)
    first.enable_guided_workspace()
    first.start_project_recovery()
    project.workbooks[0].sheets[0].set_cell(0, 0, 12)
    first._write_recovery()
    assert project.filepath == str(saved_file)
    assert Project.load_from_file(saved_file).workbooks[0].sheets[0].get_cell(0, 0) is None
    first._recovery_timer.stop()
    first._recovery_lock.unlock()  # Simulate a process exit before normal cleanup.
    first._recovery_path = None

    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    second = MainWindow()
    second.enable_guided_workspace()
    assert second.start_project_recovery()
    assert second.project.filepath is None
    assert second.project.workbooks[0].sheets[0].get_cell(0, 0) == 12
    assert "Recovered" in second.windowTitle()
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Discard)
    assert second.close()
    assert not (tmp_path / "Recovery" / "Unsaved.kgraph").exists()


def test_selected_x_and_y_only_and_chart_keeps_sheet_undo(qt_test_application):
    project = Project.create_default()
    sheet = project.workbooks[0].sheets[0]
    sheet.columns[0].data = [1, 2]
    sheet.columns[0].long_name = "Time"
    sheet.columns[1].data = [3, 4]
    sheet.columns[1].long_name = "Run A"
    sheet.add_column(long_name="Run B").data = [6, 7]
    window = MainWindow(project)
    window.enable_guided_workspace()
    view = window.get_active_spreadsheet_widget()
    view.model.setData(view.model.index(0, 1), "5")
    selection = view.table_view.selectionModel()
    for index in (0, 1):
        selection.select(view.model.index(0, index),
                         QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Columns)
    assert window.chart_selection_note.text() == "Time → Run A"
    window.create_plot("line")
    assert [(c.x_col_idx, c.y_col_idx) for c in project.graphs[0].curves] == [(0, 1)]
    assert view.undo_stack.canUndo()
    assert sheet.plot_column_pairs() == [(0, 1), (0, 2)]


def test_duplicate_chart_reuses_style_and_does_not_reuse_old_fit(qt_test_application):
    project = Project.create_default()
    workbook = project.workbooks[0]
    sheet = workbook.sheets[0]
    sheet.columns[0].data = [1, 2]
    sheet.columns[1].data = [3, 4]
    sheet.columns[1].long_name = "New signal"
    graph = GraphModel(title="Template", x_title="Time", layout_mode="grid_1x2")
    original = CurveModel(color="#9944dd", line_style="--", source_sheet=sheet.name)
    graph.curves = [original, CurveModel(is_fit_curve=True)]
    graph.annotations = [{"type": "ref_line", "value": 2}, {"type": "band"}]

    dialog = ReplaceDataDialog(project, graph, duplicate=True)
    dialog._accept_mapping()
    duplicate = rebind_chart_data(graph, dialog.mappings, copy_title="Template (copy)")
    assert duplicate.id != graph.id and duplicate.curves[0].id != original.id
    assert duplicate.x_title == "Time" and duplicate.layout_mode == "grid_1x2"
    assert len(duplicate.curves) == 1
    assert duplicate.curves[0].color == "#9944dd" and duplicate.curves[0].line_style == "--"
    assert duplicate.curves[0].label == "New signal"
    assert duplicate.annotations == [{"type": "ref_line", "value": 2}]
    assert len(graph.curves) == 2 and len(graph.annotations) == 2


def test_import_preview_reports_nonnumeric_values_and_preserves_chart_target(qt_test_application):
    dialog = ImportDialog(initial_text="Time,Signal,Label\n1,4,a\n2,bad,b\n3,8,c",
                          active_graph_title="Reference")
    dialog.combo_header.setCurrentIndex(dialog.combo_header.findData("first_row"))
    assert "Column names from row 1" in dialog.preview_details.text()
    assert "4 nonnumeric or nonfinite values" in dialog.preview_details.text()
    assert "Label" in dialog.preview_details.text()
    assert "bad" in dialog.preview_details.toolTip()
    assert dialog.table_prev.columnCount() == 2
    dialog._on_accept()
    assert dialog.add_to_active_graph
