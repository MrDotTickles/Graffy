"""
Unit tests for Milestone 1: Critical Bug & Defect Remediation.
Covers:
- Quick fill uniform & normal random parameter bug (size vs count)
- Mixed-type column sorting (numbers, strings, booleans, None/empty/NaN) and sort_rows_by_column alias
- Formula evaluation infinity handling (np.isinf converted to None)
- Project JSON serialization with NumPy scalars & arrays (NumpyEncoder & save_project alias)
- Bar & horizontal bar chart positive width/height fallback on duplicate coordinates
- Legend editor preset reset to columns safe label resolution
- MainWindow and AI Extractor empty workbooks handling
- Dialog empty project stability (AddCurveDialog, FitDialog, PeakAnalysisDialog NoneType unpacking)
- Signal smoothing data preservation, alignment, and missing value handling
"""

import os
import sys
import pytest
import numpy as np
import matplotlib.pyplot as plt

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from omnigraph.core.worksheet import Workbook, Worksheet, Column, ColumnRole
from omnigraph.core.project import Project, GraphModel, CurveModel
from omnigraph.graphing.plot_types import PlotRenderer
from omnigraph.ui.spreadsheet_view import SpreadsheetWidget
from omnigraph.ui.dialogs.formula_dialog import FormulaDialog
from omnigraph.ui.dialogs.legend_dialog import LegendEditorDialog
from omnigraph.ui.dialogs.add_curve_dialog import AddCurveDialog
from omnigraph.ui.dialogs.fit_dialog import FitDialog
from omnigraph.ui.dialogs.peak_dialog import PeakAnalysisDialog
from omnigraph.ui.dialogs.smooth_dialog import SmoothDialog
from omnigraph.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_quick_fill_uniform_and_normal(qapp):
    """Verifies that Quick Fill uniform and normal random generators execute without crash and record undo."""
    ws = Worksheet.create_default(num_rows=10)
    sw = SpreadsheetWidget(ws)

    # 1. Fill Uniform Random [0, 1]
    sw._fill_col(0, "uniform")
    col_a = ws.columns[0]
    assert len(col_a.data) >= 50
    assert all(isinstance(v, float) for v in col_a.data)
    assert all(0.0 <= v <= 1.0 for v in col_a.data)
    assert sw.undo_stack.canUndo() is True

    # Undo uniform fill
    sw.undo()
    assert len(ws.columns[0].data) == 10

    # 2. Fill Normal Random
    sw._fill_col(0, "normal")
    assert len(col_a.data) >= 50
    assert all(isinstance(v, float) for v in col_a.data)
    assert sw.undo_stack.canUndo() is True

    # Undo normal fill
    sw.undo()
    assert len(ws.columns[0].data) == 10


def test_sorting_mixed_types_and_alias():
    """Verifies that columns with mixed numbers, strings, bools, and None/empty sort without crashing."""
    ws = Worksheet.create_default(num_rows=8)
    ws.columns[0].data = [10.0, "Beta", None, 2.5, "Alpha", "", -1.0, True]
    ws.columns[1].data = ["id1", "id2", "id3", "id4", "id5", "id6", "id7", "id8"]

    # Ascending sort: Numbers first (sorted), strings/bools second (sorted), None/empty last
    ws.sort_by_column(0, ascending=True)
    # Numbers: -1.0, 2.5, 10.0
    assert ws.columns[0].data[:3] == [-1.0, 2.5, 10.0]
    # Strings and bool: "Alpha", "Beta", True (converted to str "True")
    assert ws.columns[0].data[3:6] == ["Alpha", "Beta", True]
    # None and empty at end
    assert ws.columns[0].data[6:] == [None, ""]

    # Check row synchronization with Column 1
    assert ws.columns[1].data[:3] == ["id7", "id4", "id1"]
    assert ws.columns[1].data[3:6] == ["id5", "id2", "id8"]
    assert ws.columns[1].data[6:] == ["id3", "id6"]

    # Descending sort: None/empty first, strings reversed, numbers reversed
    ws.sort_by_column(0, ascending=False)
    assert ws.columns[0].data[:2] == [None, ""]
    assert ws.columns[0].data[2:5] == [True, "Beta", "Alpha"]
    assert ws.columns[0].data[5:] == [10.0, 2.5, -1.0]

    # Verify sort_rows_by_column alias works identically
    ws.sort_rows_by_column(0, ascending=True)
    assert ws.columns[0].data[:3] == [-1.0, 2.5, 10.0]


def test_formula_inf_handling(qapp):
    """Verifies that formulas producing positive or negative infinity convert those values to None."""
    ws = Worksheet.create_default(num_rows=4)
    ws.columns[0].data = [2.0, 0.0, -1.0, 4.0]
    ws.columns[1].data = [0.0, 0.0, 0.0, 0.0]

    # Division by zero: 1.0 / 0.0 produces inf, should convert to None
    ws.apply_formula(1, "1.0 / col(A)")
    assert ws.columns[1].data == [0.5, None, -1.0, 0.25]

    # Negative infinity: -1.0 / 0.0 produces -inf, should convert to None
    ws.apply_formula(1, "-1.0 / col(A)")
    assert ws.columns[1].data == [-0.5, None, 1.0, -0.25]

    # Test via FormulaDialog preview and acceptance
    dlg = FormulaDialog(ws, target_col_idx=1)
    dlg.txt_formula.setText("1.0 / col(A)")
    dlg._trigger_preview()
    # Check that row 1 preview shows "Inf"
    item = dlg.table_preview.item(1, dlg.table_preview.columnCount() - 1)
    assert item is not None and item.text() == "Inf"
    dlg._on_accept()
    assert ws.columns[1].data == [0.5, None, -1.0, 0.25]
    dlg.close()


def test_project_numpy_serialization_and_alias(tmp_path):
    """Verifies that projects containing NumPy scalars and arrays serialize and deserialize without errors."""
    proj = Project.create_default("NumpyTestProject")
    ws = proj.workbooks[0].sheets[0]

    # Inject diverse NumPy types into column data
    ws.columns[0].data = [
        np.int64(42),
        np.int32(10),
        np.float64(3.14159),
        np.float32(2.5),
        np.bool_(True),
    ]

    filepath = str(tmp_path / "numpy_proj.kgraph")
    # Test save_to_file
    proj.save_to_file(filepath)
    assert os.path.exists(filepath)

    # Reload and verify integrity
    loaded = Project.load_from_file(filepath)
    loaded_data = loaded.workbooks[0].sheets[0].columns[0].data
    assert loaded_data == [42, 10, 3.14159, 2.5, True]
    assert isinstance(loaded_data[0], int)
    assert isinstance(loaded_data[2], float)
    assert isinstance(loaded_data[4], bool)

    # Test save_project alias
    alias_filepath = str(tmp_path / "numpy_proj_alias.kgraph")
    proj.save_project(alias_filepath)
    assert os.path.exists(alias_filepath)


def test_bar_and_hbar_duplicate_coordinates():
    """Verify that bar and hbar charts with duplicate coordinates maintain positive width and height."""
    fig, ax = plt.subplots()

    # Bar chart with duplicates
    cm_bar = CurveModel(plot_type="bar")
    x = np.array([1.0, 2.0, 2.0, 3.0])
    y = np.array([10.0, 20.0, 25.0, 30.0])
    artist_bar = PlotRenderer.render_curve(ax, cm_bar, x, y)
    assert len(artist_bar.patches) == 4
    for patch in artist_bar.patches:
        assert patch.get_width() > 0.0
    assert artist_bar.patches[0].get_width() == pytest.approx(0.75)

    # Bar chart all identical
    ax.cla()
    x_dup = np.array([5.0, 5.0, 5.0])
    y_dup = np.array([1.0, 2.0, 3.0])
    artist_bar2 = PlotRenderer.render_curve(ax, cm_bar, x_dup, y_dup)
    assert len(artist_bar2.patches) == 3
    for patch in artist_bar2.patches:
        assert patch.get_width() == pytest.approx(0.75)

    # HBar chart with duplicates
    ax.cla()
    cm_hbar = CurveModel(plot_type="hbar")
    y_h = np.array([1.0, 2.0, 2.0, 3.0])
    x_h = np.array([10.0, 20.0, 25.0, 30.0])
    artist_hbar = PlotRenderer.render_curve(ax, cm_hbar, y_h, x_h)
    assert len(artist_hbar.patches) == 4
    for patch in artist_hbar.patches:
        assert patch.get_height() > 0.0
    assert artist_hbar.patches[0].get_height() == pytest.approx(0.75)

    # HBar chart all identical
    ax.cla()
    y_h_dup = np.array([4.0, 4.0])
    x_h_dup = np.array([1.0, 2.0])
    artist_hbar2 = PlotRenderer.render_curve(ax, cm_hbar, y_h_dup, x_h_dup)
    assert len(artist_hbar2.patches) == 2
    for patch in artist_hbar2.patches:
        assert patch.get_height() == pytest.approx(0.75)

    plt.close(fig)


def test_legend_editor_reset_to_columns_preset(qapp):
    """Verify that 'Reset to Y Column' in LegendEditorDialog executes safely without AttributeError."""
    proj = Project.create_default("LegendResetTest")
    graph = GraphModel(title="Spectra")
    graph.curves = [
        CurveModel(source_sheet="S1", x_col_idx=0, y_col_idx=1, label="Signal 1"),
        CurveModel(source_sheet="S1", x_col_idx=0, y_col_idx=2, label=""),
    ]
    proj.graphs.append(graph)

    dlg = LegendEditorDialog(graph)

    # Number the series first
    dlg._preset_number_series()
    assert dlg.table_series.item(0, 3).text() == "Series 1"
    assert dlg.table_series.item(1, 3).text() == "Series 2"

    # Reset to columns - must not raise AttributeError
    dlg._preset_reset_to_columns()
    assert dlg.table_series.item(0, 3).text() == "Signal 1"
    assert dlg.table_series.item(1, 3).text() == "Curve_2"

    dlg._apply_changes()
    assert graph.curves[0].label == "Signal 1"
    assert graph.curves[1].label == "Curve_2"
    dlg.close()


def test_main_window_new_sheet_with_empty_workbooks(qapp):
    """Verify MainWindow.new_sheet safely creates Book1 if project.workbooks is empty."""
    win = MainWindow()
    win.project.workbooks.clear()
    assert len(win.project.workbooks) == 0

    win.new_sheet()
    assert len(win.project.workbooks) == 1
    assert win.project.workbooks[0].name == "Book1"
    assert len(win.project.workbooks[0].sheets) == 1
    win.close()


def test_dialogs_empty_project_stability(qapp):
    """Verifies that AddCurveDialog, FitDialog, and PeakAnalysisDialog do not crash on empty projects."""
    empty_proj = Project("Empty", workbooks=[])
    graph = GraphModel("TestGraph")

    # 1. AddCurveDialog
    dlg_curve = AddCurveDialog(empty_proj, graph)
    assert dlg_curve.combo_sheet.count() == 0
    dlg_curve._populate_columns()
    assert dlg_curve.combo_x_col.count() == 0
    # Simulate clicking accept on empty
    dlg_curve._on_accept()
    assert len(graph.curves) == 0
    dlg_curve.close()

    # 2. FitDialog
    dlg_fit = FitDialog(empty_proj, graph)
    assert dlg_fit.combo_sheet.count() == 0
    dlg_fit._populate_columns()
    assert dlg_fit.combo_x_col.count() == 0
    res_fit = dlg_fit._run_fit_calculation()
    assert res_fit is None
    dlg_fit.close()

    # 3. PeakAnalysisDialog
    dlg_peak = PeakAnalysisDialog(empty_proj, graph)
    assert dlg_peak.combo_sheet.count() == 0
    dlg_peak._populate_columns()
    assert dlg_peak.combo_x_col.count() == 0
    res_peak = dlg_peak._run_peak_search()
    assert res_peak is None
    dlg_peak.close()


def test_smooth_dialog_preserves_length_and_alignment_with_missing_values(qapp):
    """Verifies that smoothing does not truncate rows or misalign data when missing values are present."""
    ws = Worksheet.create_default(num_rows=10)
    ws.columns[0].fill_sequence(0, 1, 10)
    # Col B has missing values at index 2 and index 4
    ws.columns[1].data = [10.0, 20.0, None, 40.0, None, 60.0, 70.0, 80.0, 90.0, 100.0]

    # Test Add as New Column
    dlg = SmoothDialog(ws, selected_col_idx=1)
    dlg.spn_window.setValue(3)
    dlg._on_accept()

    assert ws.column_count() == 3
    new_col = ws.columns[2]
    # Length MUST be 10, not truncated to 8
    assert len(new_col.data) == 10
    # Missing rows must remain None
    assert new_col.data[2] is None
    assert new_col.data[4] is None
    # Valid rows must contain numeric values
    assert isinstance(new_col.data[0], float)
    assert isinstance(new_col.data[1], float)
    assert isinstance(new_col.data[3], float)
    assert isinstance(new_col.data[5], float)
    assert isinstance(new_col.data[9], float)
    dlg.close()

    # Test Replace mode
    dlg_rep = SmoothDialog(ws, selected_col_idx=1)
    dlg_rep.radio_replace.setChecked(True)
    dlg_rep.spn_window.setValue(3)
    dlg_rep._on_accept()

    assert len(ws.columns[1].data) == 10
    assert ws.columns[1].data[2] is None
    assert ws.columns[1].data[4] is None
    assert isinstance(ws.columns[1].data[0], float)
    dlg_rep.close()


def test_smooth_dialog_without_x_column_and_missing_values(qapp):
    """Verifies that smoothing works safely and preserves alignment when no X column exists."""
    ws = Worksheet("SingleCol")
    col_y = Column(name="A", role=ColumnRole.Y, data=[10.0, 20.0, None, 40.0, None, 60.0, 70.0])
    ws.columns = [col_y]

    dlg = SmoothDialog(ws, selected_col_idx=0)
    dlg.spn_window.setValue(3)
    dlg._on_accept()

    assert ws.column_count() == 2
    new_col = ws.columns[1]
    assert len(new_col.data) == 7
    assert new_col.data[2] is None
    assert new_col.data[4] is None
    assert isinstance(new_col.data[0], float)
    assert isinstance(new_col.data[5], float)
    dlg.close()


def test_smooth_dialog_and_worksheet_none_index_safety(qapp):
    """
    Verifies that SmoothDialog._on_accept(), Worksheet index accessors,
    and Column index accessors safely handle None indices and 0-column sheets without exception.
    """
    # 1. SmoothDialog on empty worksheet (0 columns)
    empty_ws = Worksheet(name="ZeroColSheet")
    empty_ws.columns = []
    dlg = SmoothDialog(empty_ws)
    assert dlg.combo_col.count() == 0
    # Must not raise TypeError or unhandled exception
    dlg._on_accept()
    dlg.close()

    # 2. Worksheet and Column defensive None handling
    ws = Worksheet.create_default(num_rows=5)
    assert ws.get_column(None) is None
    assert ws.get_column(-1) is None
    assert ws.get_column(999) is None
    assert ws.remove_column(None) is False
    assert ws.find_x_column_for(None) is None
    assert ws.find_y_error_column_for(None) is None

    assert ws.get_cell(None, None) is None
    assert ws.get_cell(0, None) is None
    assert ws.get_cell(None, 0) is None
    # set_cell with None indices must not crash
    ws.set_cell(None, None, 123)
    ws.set_cell(0, None, 123)
    ws.set_cell(None, 0, 123)

    # Column get_value and set_value with None row
    col = ws.columns[0]
    assert col.get_value(None) is None
    col.set_value(None, 456)

    # insert_rows and delete_rows with None row
    ws.insert_rows(None)
    ws.delete_rows(None)
    ws.sort_by_column(None)

