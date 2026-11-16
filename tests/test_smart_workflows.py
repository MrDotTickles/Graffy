from copy import deepcopy

import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QInputDialog, QMessageBox

from omnigraph.ai.data_extractor import SmartDataExtractor
from omnigraph.core.project import CurveModel, GraphModel, Project
from omnigraph.graphing.plot_manager import PlotManager
from omnigraph.ui.dialogs import batch_analysis
from omnigraph.ui.dialogs.export_dialog import ExportDialog
from omnigraph.ui.dialogs.fit_dialog import FitDialog
from omnigraph.ui.dialogs.import_dialog import ImportDialog
from omnigraph.ui.dialogs.peak_dialog import PeakAnalysisDialog
from omnigraph.ui.dialogs.replace_data_dialog import ReplaceDataDialog
from omnigraph.ui.main_window import MainWindow


def project_with_runs():
    project = Project.create_default()
    workbook = project.workbooks[0]
    source = workbook.sheets[0]
    for column, label, units, values in zip(
        source.columns,
        ("Time", "Intensity"),
        ("s", "V"),
        (list(range(1, 9)), [2, 4, 7, 13, 9, 4, 2, 1]),
    ):
        column.long_name, column.units, column.data = label, units, values
    second = deepcopy(source)
    second.name = "Run 2"
    second.columns.reverse()
    mismatch = deepcopy(source)
    mismatch.name = "Run 3"
    mismatch.columns[1].units = "mV"
    workbook.sheets.extend([second, mismatch])
    graph = GraphModel(title="Signal", x_title="Time (s)", y_title="Intensity (V)")
    graph.x_auto_limits, graph.x_min, graph.x_max = False, 0, 9
    graph.curves.append(CurveModel(color="#e45320"))
    project.graphs.append(graph)
    return project, workbook, source, second, mismatch, graph


def test_saved_chart_setup_matches_reordered_columns_by_metadata(monkeypatch):
    project, workbook, _, second, _, graph = project_with_runs()
    window = MainWindow(project)
    settings = QSettings("Graffy", "Graffy")
    try:
        monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: ("Instrument trace", True))
        window.save_chart_setup(graph)
        serialized = settings.value("charts/setups")
        assert '"source_sheet": ""' in serialized
        monkeypatch.setattr(QInputDialog, "getItem", lambda *args, **kwargs: ("Instrument trace", True))
        window.create_chart_from_setup(workbook.name, second.name)
        result = window.get_active_graph()
        assert result is not graph
        curve = result.curves[0]
        assert (curve.source_sheet, curve.x_col_idx, curve.y_col_idx) == (second.name, 1, 0)
        assert curve.color == graph.curves[0].color
        assert (result.x_min, result.x_max) == (0, 9)
    finally:
        settings.remove("charts/setups")
        window._remember_saved_state()
        window.close()


def test_replace_data_leaves_incompatible_units_for_user_to_confirm():
    project, _, _, _, mismatch, graph = project_with_runs()
    dialog = ReplaceDataDialog(project, graph)
    dialog.source.setCurrentIndex(next(i for i, (_, sheet) in enumerate(dialog.sources) if sheet is mismatch))
    x, y, _ = dialog.column_controls[0]
    assert x.currentData() == 0
    assert y.currentIndex() == -1


def test_sheet_edits_only_refresh_a_linked_chart_once_on_activation(monkeypatch):
    project, workbook, source, second, _, graph = project_with_runs()
    other = GraphModel(title="Second chart")
    other.curves.append(CurveModel(source_sheet=second.name, x_col_idx=1, y_col_idx=0))
    project.graphs.append(other)
    window = MainWindow(project)
    calls = []
    for kind, _, _, view in window.tab_metadata.values():
        if kind == "graph":
            refresh = view.refresh_plot
            def track(view=view, refresh=refresh):
                calls.append(view.graph_model.title)
                refresh()
            monkeypatch.setattr(view, "refresh_plot", track)
    window._on_explorer_item_activated("sheet", source.name, workbook.name)
    sheet_view = window.get_active_spreadsheet_widget()
    sheet_view._notify_data_modified()
    sheet_view._notify_data_modified()
    assert calls == []
    window._on_explorer_item_activated("graph", other.title, other.id)
    assert calls == []
    window._on_explorer_item_activated("graph", graph.title, graph.id)
    assert calls == [graph.title]
    window.close()


@pytest.mark.parametrize("mode", ["fit", "peaks"])
def test_batch_analysis_reports_results_and_unmatched_sheets(monkeypatch, mode):
    project, _, source, second, mismatch, graph = project_with_runs()
    if mode == "fit":
        dialog = FitDialog(project, active_graph=graph)
        action = dialog._fit_across_worksheets
        expected = "Fitted parameters"
    else:
        dialog = PeakAnalysisDialog(project, active_worksheet=source)
        action = dialog._peaks_across_worksheets
        expected = "Peak centers"
    monkeypatch.setattr(batch_analysis, "choose_items", lambda *args: [0, 1, 2])
    action()
    assert dialog.result() == dialog.DialogCode.Accepted
    report = project.reports[-1]
    assert report.report_type == "batch_analysis"
    assert len(project.graphs) == 1
    assert "2 of 3" in report.html_content
    assert expected in report.html_content
    assert second.name in report.html_content
    assert mismatch.name in report.html_content
    assert "Missing or ambiguous column match" in report.html_content


def test_import_preset_reuses_preview_and_invalidates_on_file_edit(monkeypatch, tmp_path):
    path = tmp_path / "run.csv"
    path.write_text("Time,Signal\n1,2\n2,4\n", encoding="utf-8")
    extract = SmartDataExtractor.extract_from_file
    calls = []

    def track(path, **options):
        calls.append(path)
        return extract(path, **options)

    monkeypatch.setattr(SmartDataExtractor, "extract_from_file", staticmethod(track))
    settings = QSettings("Graffy", "Graffy")
    try:
        first = ImportDialog(initial_filepath=str(path))
        first.combo_header.setCurrentIndex(first.combo_header.findData("first_row"))
        monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: ("Instrument CSV", True))
        first._save_profile()
        calls.clear()
        first._on_accept()
        assert calls == []
        second = ImportDialog(initial_filepath=str(path))
        second.combo_profile.setCurrentIndex(second.combo_profile.findData("Instrument CSV"))
        second._apply_profile()
        assert second.combo_header.currentData() == "first_row"
        path.write_text("Time,Signal\n1,2\n2,4\n3,6\n", encoding="utf-8")
        calls.clear()
        second._on_accept()
        assert calls == [str(path)]
        assert len(second.imported_dataframe) == 3
    finally:
        settings.remove("import/reading_profiles")


def test_export_batch_keeps_existing_files_and_remembers_format(monkeypatch, tmp_path):
    project, _, _, _, _, graph = project_with_runs()
    other = deepcopy(graph)
    manager = PlotManager(graph, project)
    manager.render()
    existing = tmp_path / "Signal.svg"
    existing.write_bytes(b"original")
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: pytest.fail(args[-1]))
    settings = QSettings("Graffy", "Graffy")
    try:
        dialog = ExportDialog(manager, batch_graphs=[graph, other])
        dialog.combo_format.setCurrentIndex(dialog.combo_format.findData("svg"))
        dialog.combo_presets.setCurrentIndex(1)
        dialog._export_batch(tmp_path)
        assert existing.read_bytes() == b"original"
        for counter in (2, 3):
            assert b"<svg" in (tmp_path / f"Signal_{counter}.svg").read_bytes()
        restored = ExportDialog(manager)
        assert restored.combo_format.currentData() == "svg"
        assert restored.get_target_dimensions_in() == pytest.approx((3.5, 2.8))
    finally:
        settings.remove("export/options")
