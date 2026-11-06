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


def test_ctrl_w_and_chart_import_open_only_the_requested_chart(qt_test_application, monkeypatch):
    from PyQt6.QtCore import Qt
    from PyQt6.QtTest import QTest

    project = Project.create_default()
    previous = GraphModel(title="Plot - Pasted_Data")
    project.graphs.append(previous)
    window = MainWindow(project)
    window.show()
    window.activateWindow()
    qt_test_application.processEvents()
    assert window.center_tabs.count() == 2
    for count in (1, 0):
        QTest.keyClick(window, Qt.Key.Key_W, Qt.KeyboardModifier.ControlModifier)
        qt_test_application.processEvents()
        assert window.center_tabs.count() == count
    assert not window.close_tab_action.isEnabled()
    assert window.get_active_graph() is None
    assert previous in project.graphs

    def accept_import(dialog):
        assert dialog.active_graph_title is None
        assert dialog.chk_auto_plot.isChecked()
        dialog.tabs_source.setCurrentIndex(1)
        dialog.txt_paste.setPlainText("Time,First,Second\n0,10,100\n1,20,200")
        assert dialog.series_combo.currentData() == "first"
        second = next(index for index in range(dialog.series_combo.count())
                      if dialog.series_combo.itemText(index) == "Second")
        dialog.series_combo.setCurrentIndex(second)
        dialog._on_accept()
        return dialog.result()

    monkeypatch.setattr(ImportDialog, "exec", accept_import)
    window.import_into_chart()
    current = window.get_active_graph()
    assert current is not previous
    assert current.title == "Plot - Pasted_Data (2)"
    assert len(previous.curves) == 0
    assert [(curve.label, curve.y_col_idx) for curve in current.curves] == [("Second", 2)]
    assert window.center_tabs.count() == 1
    source = current.curves[0]
    assert project.get_worksheet(source.source_workbook, source.source_sheet) is not None
    window._on_explorer_item_activated("graph", previous.title, previous.id)
    assert window.get_active_graph() is previous


def test_regular_import_opens_a_worksheet_and_tools_start_visible(qt_test_application):
    from PyQt6.QtCore import Qt

    project = Project.create_default()
    window = MainWindow(project)
    window.enable_guided_workspace()
    window.close_current_tab()
    dialog = ImportDialog(initial_text="Time,Signal\n1,4\n2,8", parent=window)
    assert not dialog.chk_auto_plot.isChecked()
    dialog._on_accept()
    window._process_imported_results(dialog)
    assert not project.graphs
    assert window.center_tabs.count() == 1
    sheet = window.get_active_spreadsheet_widget()
    assert not sheet.toolbar.isHidden()
    assert sheet.sheet_tools_toggle.text() == "Hide tools"
    sheet.sheet_tools_toggle.click()
    assert sheet.toolbar.isHidden()
    assert sheet.sheet_tools_toggle.text() == "Show tools"
    assert sheet.sheet_tools_toggle.arrowType() == Qt.ArrowType.DownArrow
    sheet.sheet_tools_toggle.click()
    assert not sheet.toolbar.isHidden()
    window._remember_saved_state()


def test_chart_with_missing_source_never_uses_unrelated_worksheet(qt_test_application):
    from omnigraph.graphing.plot_manager import PlotManager

    project = Project.create_default()
    worksheet = project.workbooks[0].sheets[0]
    worksheet.columns[0].data = [1, 2]
    worksheet.columns[1].data = [3, 4]
    graph = GraphModel()
    graph.curves = [CurveModel(source_sheet="Deleted worksheet")]
    plot = PlotManager(graph, project)
    assert plot._get_curve_data(graph.curves[0])[0].size == 0


def test_saved_statistics_report_uses_current_data_and_comparison(qt_test_application, monkeypatch):
    from omnigraph.ui.dialogs.stats_dialog import StatsDialog
    from omnigraph.ui.report_view import ReportViewWidget

    project = Project.create_default()
    worksheet = project.workbooks[0].sheets[0]
    worksheet.columns[0].long_name = "Control"
    worksheet.columns[0].data = [1, 2, 3]
    worksheet.columns[1].long_name = "Treatment"
    worksheet.columns[1].data = [5, 7, 9]
    window = MainWindow(project)

    def save_comparison(dialog):
        dialog.tabs.setCurrentIndex(1)
        assert not dialog.btn_save_report.isEnabled()
        dialog._run_ttest()
        assert dialog.btn_save_report.isEnabled()
        dialog.btn_save_report.click()
        return dialog.result()

    monkeypatch.setattr(StatsDialog, "exec", save_comparison)
    window.open_statistics_dialog()
    report = window.center_tabs.currentWidget()
    assert isinstance(report, ReportViewWidget)
    content = report.browser.toPlainText()
    assert all(value in content for value in ("Book1 / Sheet1", "Control", "Treatment", "p-value"))
    assert len(project.reports) == 1
    assert window.center_tabs.count() == 2
