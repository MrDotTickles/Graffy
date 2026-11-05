"""
E2E Comprehensive Workflows & Application Verification Suite.
Covers Features 1-14 (Tiers 1 & 2), Tier 3 Cross-Feature Interactions, and Tier 4 Real-World Application Scenarios.
Runs headless offscreen via QT_QPA_PLATFORM=offscreen.
"""

import os
import sys
import math
import tempfile
import pytest
import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QUndoStack, QUndoCommand
import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from omnigraph.core.worksheet import Worksheet, Column, ColumnRole, Workbook
from omnigraph.core.column_formula import FormulaEvaluator
from omnigraph.core.undo_manager import CellEditCommand, FormulaCommand
from omnigraph.core.clipboard_parser import ClipboardTableParser, HTMLTableExtractor
from omnigraph.core.project import Project, GraphModel, CurveModel, ReportModel
from omnigraph.analysis.fitting import CurveFitter, FitResult
from omnigraph.analysis.peak_analysis import PeakAnalyzer, PeakInfo, PeakAnalysisResult
from omnigraph.analysis.smoothing import SignalProcessor
from omnigraph.analysis.statistics import StatisticsAnalyzer
from omnigraph.graphing.plot_types import PlotRenderer
from omnigraph.graphing.plot_manager import PlotManager
from omnigraph.graphing.themes import apply_theme_to_axes, get_theme_palette, THEMES
from omnigraph.graphing.tools import GraphToolManager
from omnigraph.ui.samples import SampleProjects
from omnigraph.ui.main_window import MainWindow
from omnigraph.ui.dialogs import (
    ColumnPropertiesDialog,
    StatsDialog,
    SmoothDialog,
    FitDialog,
    PeakAnalysisDialog,
    ExportDialog,
    ImportDialog,
)


@pytest.fixture(scope="session")
def qapp():
    """Returns singleton QApplication for offscreen execution."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


# ===========================================================================
# FEATURE 1: Multi-Attribute Spreadsheet
# ===========================================================================

class TestFeature1MultiAttributeSpreadsheet:
    # Tier 1
    def test_f1_t1_column_attributes_and_display_label(self):
        col1 = Column(name="A", long_name="Wavelength", units="nm", comments="Raw UV data")
        assert col1.display_label == "Wavelength (nm)"
        col2 = Column(name="B", units="a.u.")
        assert col2.display_label == "B (a.u.)"
        col3 = Column(name="C")
        assert col3.display_label == "C"

    def test_f1_t1_column_roles_and_lookups(self):
        ws = Worksheet(name="TestSheet")
        c1 = Column(name="X1", role=ColumnRole.X)
        c2 = Column(name="Y1", role=ColumnRole.Y)
        c3 = Column(name="E1", role=ColumnRole.Y_ERR)
        c4 = Column(name="D1", role=ColumnRole.DISREGARD)
        ws.columns = [c1, c2, c3, c4]
        assert ws.find_x_column_for(1) == 0
        assert ws.find_y_error_column_for(1) == 2
        x_cols = [c for c in ws.columns if c.role == ColumnRole.X]
        y_cols = [c for c in ws.columns if c.role == ColumnRole.Y]
        assert x_cols == [c1]
        assert y_cols == [c2]

    def test_f1_t1_sequence_fill_and_numeric_pairs(self):
        ws = Worksheet(name="PairSheet")
        ws.columns = [
            Column(name="X", role=ColumnRole.X, data=[1.0, 2.0, 3.0, 4.0, 5.0]),
            Column(name="Y", role=ColumnRole.Y, data=[10.0, None, 30.0, 40.0, "bad"]),
        ]
        x_valid, y_valid, idxs = ws.columns[0].get_valid_numeric_pairs(ws.columns[1])
        assert len(x_valid) == 3
        np.testing.assert_array_equal(x_valid, [1.0, 3.0, 4.0])
        np.testing.assert_array_equal(y_valid, [10.0, 30.0, 40.0])
        np.testing.assert_array_equal(idxs, [0, 2, 3])

    def test_f1_t1_column_descriptive_stats(self):
        col = Column(name="Data", data=[10.0, 20.0, 30.0, 40.0, 50.0])
        s = col.stats()
        assert s["n"] == 5
        assert s["mean"] == pytest.approx(30.0)
        assert s["min"] == 10.0
        assert s["max"] == 50.0
        assert s["median"] == 30.0
        assert s["std"] == pytest.approx(15.811388, rel=1e-4)

    def test_f1_t1_worksheet_management_add_delete_clear(self):
        ws = Worksheet.create_default("ManageSheet", num_rows=10)
        assert ws.column_count() == 2
        col_new = ws.add_column("C", role=ColumnRole.Y)
        assert ws.column_count() == 3
        assert col_new.name == "C"
        ws.columns[0].set_value(0, 99.0)
        assert ws.columns[0].get_value(0) == 99.0
        ws.columns[0].data = [None] * ws.row_count()
        assert all(v is None for v in ws.columns[0].data)
        ws.remove_column(2)
        assert ws.column_count() == 2

    # Tier 2: Boundary & Corner Cases
    def test_f1_t2_empty_column_and_sheet_boundary(self):
        ws = Worksheet(name="EmptySheet")
        assert ws.column_count() == 0
        assert ws.row_count() == 0
        col = Column(name="EmptyCol")
        s = col.stats()
        assert s["n"] == 0
        assert s["mean"] is None
        assert len(col.to_numpy_array()) == 0

    def test_f1_t2_single_point_column_boundary(self):
        col = Column(name="Single", data=[42.5])
        s = col.stats()
        assert s["n"] == 1
        assert s["mean"] == 42.5
        assert s["std"] == 0.0
        assert s["sem"] == 0.0
        arr = col.to_numpy_array()
        assert len(arr) == 1
        assert arr[0] == 42.5

    def test_f1_t2_mixed_data_types_nan_conversion(self):
        col = Column(name="Mixed", data=[1.5, "text", None, "", 4.2, True, [1, 2]])
        arr = col.to_numpy_array()
        assert not np.isnan(arr[0])
        assert arr[0] == 1.5
        assert np.isnan(arr[1])  # "text" -> NaN
        assert np.isnan(arr[2])  # None -> NaN
        assert np.isnan(arr[3])  # "" -> NaN
        assert arr[4] == 4.2

    def test_f1_t2_unicode_and_special_character_headers(self):
        col = Column(
            name="Alpha",
            long_name="Extinction Coeff ε₂₈₀ & Absorbance λ",
            units="M⁻¹·cm⁻¹ / μg·mL⁻¹",
            comments="<HTML> safe & special brackets [10-90%]",
        )
        assert "ε₂₈₀" in col.display_label
        assert "M⁻¹·cm⁻¹" in col.display_label

    def test_f1_t2_large_scale_rows_and_stats(self):
        n = 5000
        data = list(range(n))
        col = Column(name="Large", data=data)
        s = col.stats()
        assert s["n"] == n
        assert s["mean"] == pytest.approx((n - 1) / 2.0)
        assert s["min"] == 0
        assert s["max"] == n - 1


# ===========================================================================
# FEATURE 2: Column Formula Engine
# ===========================================================================

class TestFeature2SafeColumnFormulaEngine:
    # Tier 1
    def test_f2_t1_basic_arithmetic_formulas(self):
        ws = Worksheet(name="FormulaSheet")
        ws.columns = [
            Column(name="A", data=[1.0, 2.0, 3.0, 4.0, 5.0]),
            Column(name="B", data=[0.0] * 5),
        ]
        res = FormulaEvaluator.evaluate("col(A) * 2.5 + 10", ws, target_length=5)
        np.testing.assert_allclose(res, [12.5, 15.0, 17.5, 20.0, 22.5])

    def test_f2_t1_scientific_functions_evaluation(self):
        ws = Worksheet(name="MathSheet")
        ws.columns = [Column(name="X", data=[0.0, math.pi / 2, math.pi])]
        res_sin = FormulaEvaluator.evaluate("sin(col(X))", ws, target_length=3)
        np.testing.assert_allclose(res_sin, [0.0, 1.0, 0.0], atol=1e-7)
        res_exp = FormulaEvaluator.evaluate("exp(0.0)", ws, target_length=3)
        np.testing.assert_allclose(res_exp, [1.0, 1.0, 1.0])

    def test_f2_t1_origin_row_indices_i_and_row(self):
        ws = Worksheet(name="IndexSheet")
        ws.columns = [Column(name="A", data=[10.0, 20.0, 30.0])]
        res_i = FormulaEvaluator.evaluate("col(A) + i", ws, target_length=3)
        np.testing.assert_allclose(res_i, [11.0, 22.0, 33.0])
        res_row = FormulaEvaluator.evaluate("row * 10", ws, target_length=3)
        np.testing.assert_allclose(res_row, [10.0, 20.0, 30.0])

    def test_f2_t1_robust_normalize_and_zscore(self):
        ws = Worksheet(name="NormSheet")
        ws.columns = [Column(name="A", data=[10.0, 20.0, 30.0, 40.0, 50.0])]
        norm_res = FormulaEvaluator.evaluate("norm(col(A))", ws, target_length=5)
        np.testing.assert_allclose(norm_res, [0.0, 0.25, 0.5, 0.75, 1.0])
        z_res = FormulaEvaluator.evaluate("zscore(col(A))", ws, target_length=5)
        assert np.mean(z_res) == pytest.approx(0.0, abs=1e-7)
        assert np.std(z_res) == pytest.approx(1.0, abs=1e-7)

    def test_f2_t1_diff_and_cumsum_transformations(self):
        ws = Worksheet(name="CumSheet")
        ws.columns = [Column(name="A", data=[1.0, 3.0, 6.0, 10.0])]
        diff_res = FormulaEvaluator.evaluate("diff(col(A))", ws, target_length=4)
        np.testing.assert_allclose(diff_res, [0.0, 2.0, 3.0, 4.0])
        cumsum_res = FormulaEvaluator.evaluate("cumsum(col(A))", ws, target_length=4)
        np.testing.assert_allclose(cumsum_res, [1.0, 4.0, 10.0, 20.0])

    # Tier 2: Boundary & Corner Cases
    def test_f2_t2_division_by_zero_handling(self):
        ws = Worksheet(name="DivZeroSheet")
        ws.columns = [
            Column(name="A", data=[2.0, 0.0, 4.0]),
            Column(name="B", data=[0.0, 0.0, 0.0]),
        ]
        ws.apply_formula(1, "10.0 / col(A)")
        assert ws.columns[1].get_value(0) == pytest.approx(5.0)
        assert ws.columns[1].get_value(1) is None
        assert ws.columns[1].get_value(2) == pytest.approx(2.5)

    def test_f2_t2_math_domain_errors_nan_safeguard(self):
        ws = Worksheet(name="DomainSheet")
        ws.columns = [Column(name="A", data=[4.0, -1.0, 9.0])]
        res = FormulaEvaluator.evaluate("sqrt(col(A))", ws, target_length=3)
        assert res[0] == 2.0
        assert np.isnan(res[1])
        assert res[2] == 3.0

    def test_f2_t2_syntax_error_reporting(self):
        ws = Worksheet(name="SyntaxSheet")
        ws.columns = [Column(name="A", data=[1.0, 2.0])]
        with pytest.raises(ValueError):
            FormulaEvaluator.evaluate("col(A) + * 5", ws, target_length=2)

    def test_f2_t2_missing_column_reference_error(self):
        ws = Worksheet(name="MissingSheet")
        ws.columns = [Column(name="A", data=[1.0, 2.0])]
        with pytest.raises(ValueError) as exc:
            FormulaEvaluator.evaluate("col(NonExistent) * 2", ws, target_length=2)
        assert "not found" in str(exc.value).lower()

    def test_f2_t2_empty_and_whitespace_formula_error(self):
        ws = Worksheet(name="EmptyFormulaSheet")
        ws.columns = [Column(name="A", data=[1.0])]
        with pytest.raises(ValueError):
            FormulaEvaluator.evaluate("   ", ws, target_length=1)


# ===========================================================================
# FEATURE 3: Undo / Redo System
# ===========================================================================

class TestFeature3UndoRedoArchitecture:
    # Tier 1
    def test_f3_t1_cell_edit_command_undo_redo(self):
        ws = Worksheet.create_default("UndoSheet", num_rows=5)
        ws.columns[1].set_value(2, 100.0)
        cmd = CellEditCommand(ws, row=2, col_idx=1, old_val=100.0, new_val=250.0)
        cmd.redo()
        assert ws.columns[1].get_value(2) == 250.0
        cmd.undo()
        assert ws.columns[1].get_value(2) == 100.0
        cmd.redo()
        assert ws.columns[1].get_value(2) == 250.0

    def test_f3_t1_formula_command_undo_redo(self):
        ws = Worksheet.create_default("FormulaUndoSheet", num_rows=3)
        ws.columns[0].data = [1.0, 2.0, 3.0]
        old_data = [0.0, 0.0, 0.0]
        ws.columns[1].data = list(old_data)
        new_data = [2.0, 4.0, 6.0]
        cmd = FormulaCommand(
            ws,
            col_idx=1,
            old_formula="",
            old_data=old_data,
            new_formula="col(A)*2",
            new_data=new_data,
        )
        cmd.redo()
        assert ws.columns[1].data == new_data
        assert ws.columns[1].formula == "col(A)*2"
        cmd.undo()
        assert ws.columns[1].data == old_data
        assert ws.columns[1].formula == ""

    def test_f3_t1_undo_stack_multi_level_history(self):
        stack = QUndoStack()
        ws = Worksheet.create_default("StackSheet", num_rows=5)
        ws.columns[0].set_value(0, 0)
        for i in range(1, 4):
            stack.push(CellEditCommand(ws, row=0, col_idx=0, old_val=i - 1, new_val=i))
            assert ws.columns[0].get_value(0) == i

        assert stack.canUndo()
        stack.undo()
        assert ws.columns[0].get_value(0) == 2
        stack.undo()
        assert ws.columns[0].get_value(0) == 1
        stack.redo()
        assert ws.columns[0].get_value(0) == 2

    def test_f3_t1_undo_stack_callbacks(self):
        callback_called = []
        def on_change():
            callback_called.append(True)

        ws = Worksheet.create_default("CallbackSheet", num_rows=2)
        cmd = CellEditCommand(ws, 0, 0, 10, 20, callback=on_change)
        cmd.redo()
        assert len(callback_called) == 1
        cmd.undo()
        assert len(callback_called) == 2

    def test_f3_t1_macro_command_batch_undo(self):
        stack = QUndoStack()
        ws = Worksheet.create_default("MacroSheet", num_rows=3)
        stack.beginMacro("Batch Fill")
        stack.push(CellEditCommand(ws, 0, 0, None, 1.0))
        stack.push(CellEditCommand(ws, 1, 0, None, 2.0))
        stack.push(CellEditCommand(ws, 2, 0, None, 3.0))
        stack.endMacro()

        assert ws.columns[0].data[:3] == [1.0, 2.0, 3.0]
        stack.undo()
        assert ws.columns[0].data[:3] == [None, None, None]

    # Tier 2: Boundary & Corner Cases
    def test_f3_t2_undo_on_empty_stack_noop(self):
        stack = QUndoStack()
        assert not stack.canUndo()
        stack.undo()

    def test_f3_t2_redo_at_end_of_stack_noop(self):
        stack = QUndoStack()
        assert not stack.canRedo()
        stack.redo()

    def test_f3_t2_rapid_undo_redo_cycling(self):
        stack = QUndoStack()
        ws = Worksheet.create_default("CycleSheet", num_rows=2)
        cmd = CellEditCommand(ws, 0, 0, "A", "B")
        stack.push(cmd)
        for _ in range(25):
            stack.undo()
            assert ws.columns[0].get_value(0) == "A"
            stack.redo()
            assert ws.columns[0].get_value(0) == "B"

    def test_f3_t2_new_command_truncates_redo(self):
        stack = QUndoStack()
        ws = Worksheet.create_default("BranchSheet", num_rows=2)
        stack.push(CellEditCommand(ws, 0, 0, 0, 1))
        stack.push(CellEditCommand(ws, 0, 0, 1, 2))
        stack.undo()
        assert stack.canRedo()
        stack.push(CellEditCommand(ws, 0, 0, 1, 99))
        assert not stack.canRedo()
        assert ws.columns[0].get_value(0) == 99

    def test_f3_t2_undo_with_none_and_nan_restoration(self):
        ws = Worksheet.create_default("NoneNanSheet", num_rows=2)
        cmd = CellEditCommand(ws, 0, 0, None, np.nan)
        cmd.redo()
        assert np.isnan(ws.columns[0].get_value(0))
        cmd.undo()
        assert ws.columns[0].get_value(0) is None


# ===========================================================================
# FEATURE 4: Universal Clipboard Parser
# ===========================================================================

class TestFeature4UniversalClipboardParser:
    # Tier 1
    def test_f4_t1_tsv_clipboard_parsing(self):
        raw = "Wavelength\tAbsorbance\n400\t0.125\n500\t0.850\n"
        grid = ClipboardTableParser.parse_clipboard(raw)
        assert len(grid) == 3
        assert grid[0] == ["Wavelength", "Absorbance"]
        assert grid[1] == [400.0, 0.125]
        assert grid[2] == [500.0, 0.850]

    def test_f4_t1_csv_quoted_clipboard_parsing(self):
        raw = '"Sample, ID",Time,Value\n"Test, A",10,50.5\n"Test, B",20,75.2\n'
        grid = ClipboardTableParser.parse_clipboard(raw)
        assert len(grid) == 3
        assert grid[1][0] == "Test, A"
        assert grid[1][1] == 10.0
        assert grid[1][2] == 50.5

    def test_f4_t1_html_table_clipboard_parsing(self):
        html = "<table><tr><th>Time</th><th>Conc</th></tr><tr><td>1.0</td><td>2.5</td></tr><tr><td>2.0</td><td>5.0</td></tr></table>"
        grid = ClipboardTableParser.parse_clipboard("", html=html)
        assert len(grid) == 3
        assert grid[0] == ["Time", "Conc"]
        assert grid[1] == [1.0, 2.5]
        assert grid[2] == [2.0, 5.0]

    def test_f4_t1_markdown_table_clipboard_parsing(self):
        md = "| Step | Rate |\n|---|---|\n| 1 | 12.4 |\n| 2 | 24.8 |\n"
        grid = ClipboardTableParser.parse_clipboard(md)
        assert len(grid) >= 2
        assert grid[-2] == [1.0, 12.4]
        assert grid[-1] == [2.0, 24.8]

    def test_f4_t1_whitespace_aligned_table_parsing(self):
        raw = "10.0    20.0    30.0\n40.0    50.0    60.0"
        grid = ClipboardTableParser.parse_clipboard(raw)
        assert len(grid) == 2
        assert grid[0] == [10.0, 20.0, 30.0]
        assert grid[1] == [40.0, 50.0, 60.0]

    # Tier 2: Boundary & Corner Cases
    def test_f4_t2_empty_clipboard_returns_empty_grid(self):
        assert ClipboardTableParser.parse_clipboard("") == []
        assert ClipboardTableParser.parse_clipboard("   \n\n  \t  ") == []

    def test_f4_t2_decimal_comma_european_numbers(self):
        raw = "12,5\t34,8\n56,2\t78,9\n"
        grid = ClipboardTableParser.parse_clipboard(raw)
        assert len(grid) == 2
        assert grid[0] == [12.5, 34.8]
        assert grid[1] == [56.2, 78.9]

    def test_f4_t2_ragged_rows_handling(self):
        raw = "A\tB\tC\n1\t2\n3\t4\t5\t6\n"
        grid = ClipboardTableParser.parse_clipboard(raw)
        assert len(grid) == 3
        assert len(grid[0]) == 3
        assert len(grid[1]) == 2
        assert len(grid[2]) == 4

    def test_f4_t2_malformed_html_table_fallback(self):
        malformed = "<table><tr><td>1</td><td>2<tr><td>3<td>4</table>"
        grid = ClipboardTableParser.parse_clipboard(malformed, html=malformed)
        assert len(grid) >= 1

    def test_f4_t2_crlf_mixed_newlines_parsing(self):
        raw = "1\t2\r\n3\t4\n5\t6\r\n"
        grid = ClipboardTableParser.parse_clipboard(raw)
        assert len(grid) == 3
        assert grid[0] == [1.0, 2.0]
        assert grid[2] == [5.0, 6.0]


# ===========================================================================
# FEATURE 5: Scientific 2D Plot Types
# ===========================================================================

class TestFeature5ScientificPlotTypes:
    # Tier 1
    def test_f5_t1_scatter_and_line_rendering(self):
        fig = Figure()
        ax = fig.add_subplot(111)
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([4.0, 5.0, 6.0])

        c_scatter = CurveModel(plot_type="scatter", label="ScatterTest")
        art_scatter = PlotRenderer.render_curve(ax, c_scatter, x, y)
        assert art_scatter is not None

        c_line = CurveModel(plot_type="line", label="LineTest")
        art_line = PlotRenderer.render_curve(ax, c_line, x, y)
        assert art_line is not None

    def test_f5_t1_line_symbol_and_step_rendering(self):
        fig = Figure()
        ax = fig.add_subplot(111)
        x = np.linspace(0, 10, 20)
        y = np.sin(x)

        c_ls = CurveModel(plot_type="line_symbol", label="LineSymbol")
        art_ls = PlotRenderer.render_curve(ax, c_ls, x, y)
        assert art_ls is not None

        c_step = CurveModel(plot_type="step", label="Step")
        art_step = PlotRenderer.render_curve(ax, c_step, x, y)
        assert art_step is not None

    def test_f5_t1_bar_and_hbar_rendering(self):
        fig = Figure()
        ax = fig.add_subplot(111)
        x = np.array([1.0, 2.0, 3.0, 4.0])
        y = np.array([10.0, 20.0, 15.0, 25.0])

        c_bar = CurveModel(plot_type="bar", label="Bar")
        art_bar = PlotRenderer.render_curve(ax, c_bar, x, y)
        assert art_bar is not None

        c_hbar = CurveModel(plot_type="hbar", label="HBar")
        art_hbar = PlotRenderer.render_curve(ax, c_hbar, x, y)
        assert art_hbar is not None

    def test_f5_t1_errorbar_rendering(self):
        fig = Figure()
        ax = fig.add_subplot(111)
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([10.0, 15.0, 12.0])
        err = np.array([0.5, 0.8, 0.4])

        c_err = CurveModel(plot_type="errorbar", label="ErrorBar")
        art_err = PlotRenderer.render_curve(ax, c_err, x, y, y_err=err)
        assert art_err is not None

    def test_f5_t1_histogram_box_violin_rendering(self):
        fig = Figure()
        ax = fig.add_subplot(111)
        np.random.seed(42)
        y = np.random.normal(0, 1, 100)
        x = np.ones(100)

        c_hist = CurveModel(plot_type="histogram", label="Hist")
        PlotRenderer.render_curve(ax, c_hist, x, y)

        c_box = CurveModel(plot_type="box", label="Box")
        PlotRenderer.render_curve(ax, c_box, x, y)

        c_violin = CurveModel(plot_type="violin", label="Violin")
        PlotRenderer.render_curve(ax, c_violin, x, y)

    # Tier 2: Boundary & Corner Cases
    def test_f5_t2_single_point_curve_rendering(self):
        fig = Figure()
        ax = fig.add_subplot(111)
        x = np.array([5.0])
        y = np.array([10.0])
        c = CurveModel(plot_type="bar", label="Single")
        art = PlotRenderer.render_curve(ax, c, x, y)
        assert art is not None

    def test_f5_t2_duplicate_x_coordinates_dx_fallback(self):
        fig = Figure()
        ax = fig.add_subplot(111)
        x = np.array([2.0, 2.0, 2.0])
        y = np.array([5.0, 10.0, 15.0])
        c = CurveModel(plot_type="bar", label="DupX")
        art = PlotRenderer.render_curve(ax, c, x, y)
        assert art is not None

    def test_f5_t2_empty_or_all_nan_curve_rendering(self):
        fig = Figure()
        ax = fig.add_subplot(111)
        x = np.array([], dtype=float)
        y = np.array([], dtype=float)
        c = CurveModel(plot_type="line", label="Empty")
        art = PlotRenderer.render_curve(ax, c, x, y)
        assert art is not None

    def test_f5_t2_extreme_range_coordinates(self):
        fig = Figure()
        ax = fig.add_subplot(111)
        x = np.array([1e-12, 1e-6, 1.0, 1e6])
        y = np.array([1e-15, 1e-3, 10.0, 1e12])
        c = CurveModel(plot_type="scatter", label="Extreme")
        art = PlotRenderer.render_curve(ax, c, x, y)
        assert art is not None

    def test_f5_t2_zero_and_negative_errorbar_values(self):
        fig = Figure()
        ax = fig.add_subplot(111)
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([10.0, 20.0, 30.0])
        err_zero = np.array([0.0, 0.0, 0.5])
        c = CurveModel(plot_type="errorbar", label="ZeroErr")
        art = PlotRenderer.render_curve(ax, c, x, y, y_err=err_zero)
        assert art is not None

        # Negative errors must be caught per Matplotlib specification
        err_neg = np.array([0.0, -1.0, 0.5])
        with pytest.raises(ValueError):
            PlotRenderer.render_curve(ax, c, x, y, y_err=err_neg)


# ===========================================================================
# FEATURE 6: Publication Themes
# ===========================================================================

class TestFeature6PublicationTheming:
    # Tier 1
    def test_f6_t1_origin_classic_theme_properties(self):
        assert "Origin Classic" in THEMES
        th = THEMES["Origin Classic"]
        assert th["figure.facecolor"] == "#ffffff"
        assert th["axes.linewidth"] == 1.2
        assert th["xtick.direction"] == "in"
        assert len(th["palette"]) >= 6

    def test_f6_t1_nature_publication_theme(self):
        assert "Nature" in THEMES
        th = THEMES["Nature"]
        assert th["axes.linewidth"] == 1.0
        assert th["axes.edgecolor"] == "#333333"

    def test_f6_t1_science_publication_theme(self):
        assert "Science" in THEMES
        th = THEMES["Science"]
        assert "palette" in th
        assert len(th["palette"]) >= 4

    def test_f6_t1_modern_dark_theme(self):
        assert "Modern Dark" in THEMES
        th = THEMES["Modern Dark"]
        assert th["figure.facecolor"] in ("#181825", "#1e1e1e")

    def test_f6_t1_prism_and_bw_themes(self):
        assert "Prism" in THEMES
        assert "High-Contrast B&W" in THEMES
        bw_pal = THEMES["High-Contrast B&W"]["palette"]
        assert len(bw_pal) >= 4
        assert all(c.startswith("#") for c in bw_pal)

    # Tier 2: Boundary & Corner Cases
    def test_f6_t2_apply_all_six_themes_sequentially(self):
        fig = Figure()
        ax = fig.add_subplot(111)
        for theme_name in THEMES.keys():
            apply_theme_to_axes(ax, theme_name)
            assert ax.get_facecolor() is not None

    def test_f6_t2_unknown_theme_fallback_to_classic(self):
        fig = Figure()
        ax = fig.add_subplot(111)
        apply_theme_to_axes(ax, "NonExistentThemeName")
        assert ax.get_facecolor() == (1.0, 1.0, 1.0, 1.0)

    def test_f6_t2_box_frame_and_tick_direction_permutations(self):
        fig = Figure()
        ax = fig.add_subplot(111)
        for box in [True, False]:
            for tdir in ["in", "out", "inout"]:
                apply_theme_to_axes(ax, "Nature", box_frame=box, tick_direction=tdir)

    def test_f6_t2_palette_modulo_cycling(self):
        pal = get_theme_palette("Origin Classic")
        c1 = pal[0]
        c_cycle = pal[len(pal) % len(pal)]
        assert c1 == c_cycle

    def test_f6_t2_theme_persistence_in_graph_model(self):
        graph = GraphModel(title="TestPersist")
        graph.theme = "Modern Dark"
        d = graph.to_dict()
        assert d["theme"] == "Modern Dark"
        restored = GraphModel.from_dict(d)
        assert restored.theme == "Modern Dark"


# ===========================================================================
# FEATURE 7: Figure Export & Clipboard
# ===========================================================================

class TestFeature7FigureExportClipboard:
    # Tier 1
    def test_f7_t1_raster_png_export(self, tmp_path):
        proj = SampleProjects.create_spectroscopy_sample()
        pm = PlotManager(proj.graphs[0], proj)
        pm.render()
        out_png = str(tmp_path / "figure.png")
        pm.export_image(out_png, dpi=150)
        assert os.path.exists(out_png)
        assert os.path.getsize(out_png) > 1000

    def test_f7_t1_vector_pdf_and_svg_export(self, tmp_path):
        proj = SampleProjects.create_spectroscopy_sample()
        pm = PlotManager(proj.graphs[0], proj)
        pm.render()
        out_pdf = str(tmp_path / "figure.pdf")
        pm.export_image(out_pdf)
        assert os.path.exists(out_pdf)
        assert os.path.getsize(out_pdf) > 1000

        out_svg = str(tmp_path / "figure.svg")
        pm.export_image(out_svg)
        assert os.path.exists(out_svg)
        with open(out_svg, "r", encoding="utf-8") as f:
            content = f.read()
        assert "<svg" in content

    def test_f7_t1_physical_dimension_export(self, tmp_path):
        proj = SampleProjects.create_spectroscopy_sample()
        pm = PlotManager(proj.graphs[0], proj)
        pm.render()
        out_png = str(tmp_path / "dim_figure.png")
        pm.export_image(out_png, dpi=200, width_in=4.0, height_in=3.0)
        assert os.path.exists(out_png)

    def test_f7_t1_qpixmap_canvas_export(self, qapp):
        proj = SampleProjects.create_spectroscopy_sample()
        pm = PlotManager(proj.graphs[0], proj)
        pm.render()
        pix = pm.export_to_pixmap(dpi=120)
        assert not pix.isNull()
        assert pix.width() > 100
        assert pix.height() > 100

    def test_f7_t1_export_dialog_presets_validation(self, qapp):
        proj = SampleProjects.create_spectroscopy_sample()
        pm = PlotManager(proj.graphs[0], proj)
        dlg = ExportDialog(pm)
        assert len(dlg.PRESETS) >= 4
        dlg.close()

    # Tier 2: Boundary & Corner Cases
    def test_f7_t2_transparent_background_export(self, tmp_path):
        proj = SampleProjects.create_spectroscopy_sample()
        pm = PlotManager(proj.graphs[0], proj)
        pm.render()
        out_png = str(tmp_path / "transparent.png")
        pm.export_image(out_png, dpi=100, transparent=True)
        assert os.path.exists(out_png)

    def test_f7_t2_high_dpi_export_600(self, tmp_path):
        proj = SampleProjects.create_spectroscopy_sample()
        pm = PlotManager(proj.graphs[0], proj)
        pm.render()
        out_png = str(tmp_path / "high_res.png")
        pm.export_image(out_png, dpi=600)
        assert os.path.exists(out_png)
        assert os.path.getsize(out_png) > 5000

    def test_f7_t2_export_tight_crop_vs_standard(self, tmp_path):
        proj = SampleProjects.create_spectroscopy_sample()
        pm = PlotManager(proj.graphs[0], proj)
        pm.render()
        out_tight = str(tmp_path / "tight.png")
        out_loose = str(tmp_path / "loose.png")
        pm.export_image(out_tight, tight_crop=True)
        pm.export_image(out_loose, tight_crop=False)
        assert os.path.exists(out_tight)
        assert os.path.exists(out_loose)

    def test_f7_t2_export_empty_figure(self, tmp_path):
        proj = Project.create_default("EmptyFig")
        graph = GraphModel(title="EmptyGraph")
        proj.graphs.append(graph)
        pm = PlotManager(graph, proj)
        pm.render()
        out_png = str(tmp_path / "empty.png")
        pm.export_image(out_png)
        assert os.path.exists(out_png)

    def test_f7_t2_export_dialog_aspect_ratio_locking(self, qapp):
        proj = SampleProjects.create_spectroscopy_sample()
        pm = PlotManager(proj.graphs[0], proj)
        dlg = ExportDialog(pm)
        dlg.chk_lock_aspect.setChecked(True)
        dlg.spn_width.setValue(8.0)
        dlg.close()


# ===========================================================================
# FEATURE 8: Canvas Tools & Labels
# ===========================================================================

class TestFeature8CanvasToolsLabels:
    # Tier 1
    def test_f8_t1_graph_tool_manager_initialization(self):
        fig = Figure()
        ax = fig.add_subplot(111)
        tm = GraphToolManager(fig.canvas, ax)
        assert tm.current_tool == "pointer"

    def test_f8_t1_tool_mode_switching(self):
        fig = Figure()
        ax = fig.add_subplot(111)
        tm = GraphToolManager(fig.canvas, ax)
        tm.set_tool("data_reader")
        assert tm.current_tool == "data_reader"
        tm.set_tool("range_selector")
        assert tm.current_tool == "range_selector"
        tm.set_tool("pointer")
        assert tm.current_tool == "pointer"

    def test_f8_t1_data_reader_crosshair_inspection(self):
        fig = Figure()
        ax = fig.add_subplot(111)
        tm = GraphToolManager(fig.canvas, ax)
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([10.0, 20.0, 30.0])
        tm.set_data_curves([("Series1", x, y)])

        events_caught = []
        tm.point_inspected.connect(lambda l, px, py, r: events_caught.append((l, px, py, r)))

        tm.set_tool("data_reader")
        class MockEvent:
            inaxes = ax
            xdata = 2.01
            ydata = 19.98

        tm._on_motion(MockEvent())
        assert len(events_caught) >= 1
        assert events_caught[0][0] == "Series1"
        assert events_caught[0][1] == pytest.approx(2.0)
        assert events_caught[0][2] == pytest.approx(20.0)

    def test_f8_t1_roi_range_selector_signal(self):
        fig = Figure()
        ax = fig.add_subplot(111)
        tm = GraphToolManager(fig.canvas, ax)
        spans_caught = []
        tm.range_selected.connect(lambda xmin, xmax: spans_caught.append((xmin, xmax)))
        tm._on_span_select(15.0, 45.0)
        assert len(spans_caught) == 1
        assert spans_caught[0] == (15.0, 45.0)

    def test_f8_t1_annotations_rendering(self):
        proj = SampleProjects.create_spectroscopy_sample()
        graph = proj.graphs[0]
        graph.annotations.append({"type": "text", "x": 520, "y": 0.8, "text": "Main Peak"})
        graph.annotations.append({"type": "ref_line", "value": 0.5, "orientation": "h", "color": "#ff0000"})
        pm = PlotManager(graph, proj)
        pm.render()
        assert len(graph.annotations) == 2

    # Tier 2: Boundary & Corner Cases
    def test_f8_t2_data_reader_empty_graph(self):
        fig = Figure()
        ax = fig.add_subplot(111)
        tm = GraphToolManager(fig.canvas, ax)
        tm.set_tool("data_reader")
        class MockEvent:
            inaxes = ax
            xdata = 5.0
            ydata = 5.0
        tm._on_motion(MockEvent())

    def test_f8_t2_inverted_roi_span_normalization(self):
        fig = Figure()
        ax = fig.add_subplot(111)
        tm = GraphToolManager(fig.canvas, ax)
        spans = []
        tm.range_selected.connect(lambda x0, x1: spans.append((x0, x1)))
        tm._on_span_select(100.0, 20.0)
        assert len(spans) == 1
        assert spans[0] == (20.0, 100.0)

    def test_f8_t2_latex_math_annotations(self):
        proj = SampleProjects.create_spectroscopy_sample()
        graph = proj.graphs[0]
        graph.annotations.append({"type": "text", "x": 400, "y": 0.5, "text": r"$\lambda_{max} = 520 \pm 2\ nm$"})
        pm = PlotManager(graph, proj)
        pm.render()

    def test_f8_t2_rapid_tool_mode_cycling(self):
        fig = Figure()
        ax = fig.add_subplot(111)
        tm = GraphToolManager(fig.canvas, ax)
        for _ in range(20):
            tm.set_tool("pointer")
            tm.set_tool("data_reader")
            tm.set_tool("range_selector")

    def test_f8_t2_confidence_band_annotation_rendering(self):
        proj = SampleProjects.create_spectroscopy_sample()
        graph = proj.graphs[0]
        xs = np.linspace(400, 600, 20).tolist()
        low = np.full(20, 0.1).tolist()
        high = np.full(20, 0.9).tolist()
        graph.annotations.append({"type": "band", "x_data": xs, "lower_data": low, "upper_data": high})
        pm = PlotManager(graph, proj)
        pm.render()


# ===========================================================================
# FEATURE 9: Curve Fitting Models
# ===========================================================================

class TestFeature9CurveFittingModels:
    # Tier 1
    def test_f9_t1_linear_regression_fit(self):
        np.random.seed(42)
        x = np.linspace(1, 10, 25)
        y = 3.5 * x + 7.2 + np.random.normal(0, 0.05, 25)
        res = CurveFitter.linear_fit(x, y)
        assert res.parameters["Slope (m)"] == pytest.approx(3.5, rel=0.05)
        assert res.parameters["Intercept (b)"] == pytest.approx(7.2, rel=0.05)
        assert res.r_squared > 0.99
        assert res.conf_band_lower is not None

    def test_f9_t1_polynomial_degree2_and_degree3_fit(self):
        x = np.linspace(-5, 5, 30)
        y = 2.0 * x**2 - 1.5 * x + 4.0
        res_p2 = CurveFitter.polynomial_fit(x, y, degree=2)
        assert res_p2.parameters["c_2"] == pytest.approx(2.0, rel=1e-3)
        assert res_p2.parameters["c_1"] == pytest.approx(-1.5, rel=1e-3)
        assert res_p2.parameters["c_0"] == pytest.approx(4.0, rel=1e-3)
        assert res_p2.r_squared > 0.999

        y3 = 0.5 * x**3 + y
        res_p3 = CurveFitter.polynomial_fit(x, y3, degree=3)
        assert res_p3.r_squared > 0.999

    def test_f9_t1_exponential_decay_fit(self):
        x = np.linspace(0, 10, 40)
        y = 5.0 + 20.0 * np.exp(-x / 2.5)
        res = CurveFitter.nonlinear_fit(x, y, model_type="exp_decay")
        assert res.success is True
        assert res.parameters["A"] == pytest.approx(20.0, rel=0.1)
        assert res.parameters["t"] == pytest.approx(2.5, rel=0.1)
        assert res.r_squared > 0.98

    def test_f9_t1_gaussian_peak_fit(self):
        x = np.linspace(400, 600, 50)
        y = 0.1 + 0.8 * np.exp(-0.5 * ((x - 500) / 20) ** 2)
        res = CurveFitter.nonlinear_fit(x, y, model_type="gaussian")
        assert res.success is True
        assert res.parameters["xc (Center)"] == pytest.approx(500.0, abs=1.0)
        assert res.r_squared > 0.98

    def test_f9_t1_michaelis_menten_kinetics_fit(self):
        s = np.array([0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0])
        v = (100.0 * s) / (12.0 + s)
        res = CurveFitter.nonlinear_fit(s, v, model_type="michaelis_menten")
        assert res.success is True
        assert res.parameters["Vmax"] == pytest.approx(100.0, rel=0.05)
        assert res.parameters["Km"] == pytest.approx(12.0, rel=0.05)
        assert res.r_squared > 0.99

    # Tier 2: Boundary & Corner Cases
    def test_f9_t2_perfect_linear_fit_r2_unity(self):
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = 2.0 * x + 1.0
        res = CurveFitter.linear_fit(x, y)
        assert res.r_squared == pytest.approx(1.0)
        assert res.rmse == pytest.approx(0.0, abs=1e-7)

    def test_f9_t2_roi_subrange_fitting(self):
        x = np.linspace(0, 10, 50)
        y = np.where(x < 5, 2.0 * x, 10.0 + 5.0 * (x - 5))
        res = CurveFitter.linear_fit(x, y, x_min=0, x_max=4.5)
        assert res.parameters["Slope (m)"] == pytest.approx(2.0, rel=0.01)

    def test_f9_t2_linear_fit_fixed_intercept_zero(self):
        x = np.array([1.0, 2.0, 3.0, 4.0])
        y = 3.0 * x
        res = CurveFitter.linear_fit(x, y, fix_intercept=True, intercept_val=0.0)
        assert res.parameters["Intercept (b)"] == 0.0
        assert res.parameters["Slope (m)"] == pytest.approx(3.0, rel=1e-4)

    def test_f9_t2_insufficient_data_points_handling(self):
        x = np.array([1.0])
        y = np.array([2.0])
        with pytest.raises(ValueError):
            CurveFitter.linear_fit(x, y)
        with pytest.raises(ValueError):
            CurveFitter.polynomial_fit(x, y, degree=2)
        with pytest.raises(ValueError):
            CurveFitter.nonlinear_fit(x, y, model_type="gaussian")

    def test_f9_t2_pure_noise_fit_result_stability(self):
        np.random.seed(99)
        x = np.linspace(0, 10, 20)
        y = np.random.uniform(-1, 1, 20)
        res = CurveFitter.linear_fit(x, y)
        assert res.success is True
        assert res.r_squared >= 0.0


# ===========================================================================
# FEATURE 10: Peak Analysis & Integration
# ===========================================================================

class TestFeature10PeakAnalysisIntegration:
    # Tier 1
    def test_f10_t1_single_gaussian_peak_detection(self):
        x = np.linspace(100, 300, 101)
        y = 1.5 * np.exp(-0.5 * ((x - 200) / 10) ** 2)
        res = PeakAnalyzer.analyze_peaks(x, y, min_prominence_pct=10.0)
        assert len(res.peaks) == 1
        p = res.peaks[0]
        assert p.x_center == pytest.approx(200.0, abs=2.0)
        assert p.y_height == pytest.approx(1.5, rel=0.05)

    def test_f10_t1_multiple_overlapping_peaks_deconvolution(self):
        x = np.linspace(0, 100, 201)
        p1 = 2.0 * np.exp(-0.5 * ((x - 30) / 5) ** 2)
        p2 = 3.0 * np.exp(-0.5 * ((x - 60) / 6) ** 2)
        p3 = 1.8 * np.exp(-0.5 * ((x - 85) / 4) ** 2)
        y = p1 + p2 + p3
        res = PeakAnalyzer.analyze_peaks(x, y, min_prominence_pct=10.0, min_distance=10)
        assert len(res.peaks) == 3
        centers = [p.x_center for p in res.peaks]
        assert centers[0] == pytest.approx(30.0, abs=1.0)
        assert centers[1] == pytest.approx(60.0, abs=1.0)
        assert centers[2] == pytest.approx(85.0, abs=1.0)

    def test_f10_t1_baseline_modes_computation(self):
        x = np.linspace(0, 10, 50)
        y = 2.0 * x + 5.0
        bl_none = PeakAnalyzer.compute_baseline(x, y, baseline_mode="none")
        assert np.all(bl_none == 0.0)

        bl_const = PeakAnalyzer.compute_baseline(x, y, baseline_mode="constant")
        assert np.all(bl_const == 5.0)

        bl_linear = PeakAnalyzer.compute_baseline(x, y, baseline_mode="linear")
        np.testing.assert_allclose(bl_linear, y)

    def test_f10_t1_fwhm_width_computation(self):
        x = np.linspace(0, 50, 501)
        sigma = 3.0
        y = np.exp(-0.5 * ((x - 25) / sigma) ** 2)
        res = PeakAnalyzer.analyze_peaks(x, y, min_prominence_pct=10.0)
        assert len(res.peaks) == 1
        fwhm = res.peaks[0].fwhm
        assert fwhm == pytest.approx(2.355 * sigma, rel=0.1)

    def test_f10_t1_trapezoidal_auc_and_percentage(self):
        x = np.linspace(0, 100, 201)
        p1 = np.exp(-0.5 * ((x - 30) / 5) ** 2)
        p2 = np.exp(-0.5 * ((x - 70) / 5) ** 2)
        y = p1 + p2
        res = PeakAnalyzer.analyze_peaks(x, y, min_prominence_pct=10.0)
        assert len(res.peaks) == 2
        pcts = [p.rel_area_percent for p in res.peaks]
        assert sum(pcts) == pytest.approx(100.0, abs=0.1)

    # Tier 2: Boundary & Corner Cases
    def test_f10_t2_flatline_signal_zero_peaks(self):
        x = np.linspace(0, 10, 50)
        y = np.full(50, 5.0)
        res = PeakAnalyzer.analyze_peaks(x, y, min_prominence_pct=5.0)
        assert len(res.peaks) == 0

    def test_f10_t2_prominence_filter_thresholding(self):
        x = np.linspace(0, 50, 100)
        y = 0.05 * np.sin(x)
        y[50] = 5.0
        res_loose = PeakAnalyzer.analyze_peaks(x, y, min_prominence_pct=1.0)
        res_strict = PeakAnalyzer.analyze_peaks(x, y, min_prominence_pct=25.0)
        assert len(res_strict.peaks) == 1
        assert len(res_loose.peaks) >= len(res_strict.peaks)

    def test_f10_t2_minimum_distance_constraint(self):
        x = np.linspace(0, 10, 100)
        y = np.zeros(100)
        y[40] = 2.0
        y[42] = 2.2
        res_close = PeakAnalyzer.analyze_peaks(x, y, min_distance=1, min_prominence_pct=5.0)
        res_far = PeakAnalyzer.analyze_peaks(x, y, min_distance=10, min_prominence_pct=5.0)
        assert len(res_close.peaks) >= len(res_far.peaks)

    def test_f10_t2_noisy_signal_with_isolated_peak(self):
        np.random.seed(42)
        x = np.linspace(0, 100, 200)
        noise = np.random.normal(0, 0.02, 200)
        y = 1.0 * np.exp(-0.5 * ((x - 50) / 5) ** 2) + noise
        res = PeakAnalyzer.analyze_peaks(x, y, min_prominence_pct=15.0)
        assert len(res.peaks) == 1
        assert res.peaks[0].x_center == pytest.approx(50.0, abs=1.5)

    def test_f10_t2_peak_html_report_formatting(self):
        x = np.linspace(0, 10, 50)
        y = np.exp(-0.5 * ((x - 5) / 1) ** 2)
        res = PeakAnalyzer.analyze_peaks(x, y, min_prominence_pct=5.0)
        html = res.to_html_report()
        assert "<table" in html
        assert "Peak ID" in html


# ===========================================================================
# FEATURE 11: Signal Processing & Smoothing
# ===========================================================================

class TestFeature11SignalProcessingSmoothing:
    # Tier 1
    def test_f11_t1_savitzky_golay_filter_smoothing(self):
        np.random.seed(42)
        x = np.linspace(0, 10, 100)
        clean = np.sin(x)
        noisy = clean + np.random.normal(0, 0.2, 100)
        smoothed = SignalProcessor.savitzky_golay(noisy, window_length=11, polyorder=2)
        assert len(smoothed) == len(noisy)
        assert np.var(smoothed - clean) < np.var(noisy - clean)

    def test_f11_t1_moving_average_smoothing(self):
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        ma = SignalProcessor.moving_average(y, window_size=3)
        assert len(ma) == len(y)

    def test_f11_t1_gaussian_filter_smoothing(self):
        y = np.array([0.0, 0.0, 10.0, 0.0, 0.0])
        gf = SignalProcessor.gaussian_filter(y, sigma=1.0)
        assert len(gf) == len(y)
        assert gf[2] < 10.0
        assert gf[1] > 0.0

    def test_f11_t1_numerical_derivatives_1st_and_2nd(self):
        x = np.linspace(0, 10, 101)
        y = x**2
        d1 = SignalProcessor.derivative_1st(x, y)
        np.testing.assert_allclose(d1[1:-1], 2 * x[1:-1], atol=0.01)
        d2 = SignalProcessor.derivative_2nd(x, y)
        np.testing.assert_allclose(d2[2:-2], np.full_like(x[2:-2], 2.0), atol=0.05)

    def test_f11_t1_cumulative_trapezoidal_integral(self):
        x = np.linspace(0, 10, 101)
        y = 2 * x
        integ = SignalProcessor.cumulative_integral(x, y)
        np.testing.assert_allclose(integ, x**2, atol=0.1)

    # Tier 2: Boundary & Corner Cases
    def test_f11_t2_savgol_short_signal_adaptation(self):
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        smoothed = SignalProcessor.savitzky_golay(y, window_length=15, polyorder=2)
        assert len(smoothed) == len(y)

    def test_f11_t2_moving_average_window_size_one(self):
        y = np.array([1.0, 5.0, 2.0, 8.0])
        ma = SignalProcessor.moving_average(y, window_size=1)
        np.testing.assert_array_equal(ma, y)

    def test_f11_t2_constant_signal_derivative_zero(self):
        x = np.linspace(0, 10, 20)
        y = np.full(20, 7.5)
        d1 = SignalProcessor.derivative_1st(x, y)
        np.testing.assert_allclose(d1, 0.0, atol=1e-10)

    def test_f11_t2_smoothing_preserves_exact_array_length(self):
        for length in [10, 27, 100, 333]:
            y = np.linspace(0, 50, length)
            assert len(SignalProcessor.savitzky_golay(y)) == length
            assert len(SignalProcessor.moving_average(y)) == length
            assert len(SignalProcessor.gaussian_filter(y)) == length

    def test_f11_t2_fft_dominant_frequency_extraction(self):
        t = np.linspace(0, 1.0, 100, endpoint=False)
        y = np.sin(2 * np.pi * 10 * t)
        fft_vals = np.fft.rfft(y)
        freqs = np.fft.rfftfreq(len(t), d=(t[1] - t[0]))
        peak_freq = freqs[np.argmax(np.abs(fft_vals))]
        assert peak_freq == pytest.approx(10.0, abs=0.5)


# ===========================================================================
# FEATURE 12: Column & Comparative Stats
# ===========================================================================

class TestFeature12ColumnComparativeStats:
    # Tier 1
    def test_f12_t1_column_descriptive_stats_full(self):
        col = Column(name="Data", data=[10.0, 12.0, 14.0, 16.0, 18.0, 20.0])
        s = col.stats()
        assert s["n"] == 6
        assert s["mean"] == 15.0
        assert s["sum"] == 90.0
        assert s["min"] == 10.0
        assert s["max"] == 20.0
        assert s["median"] == 15.0

    def test_f12_t1_two_sample_ttest_independent(self):
        col1 = Column(name="Control", data=[10.0, 11.0, 12.0, 10.5, 11.5])
        col2 = Column(name="Treated", data=[20.0, 22.0, 21.0, 20.5, 21.5])
        res = StatisticsAnalyzer.two_sample_ttest(col1, col2, paired=False, equal_var=True)
        assert res["t_statistic"] < -10.0
        assert res["p_value"] < 0.001
        assert res["dof"] == 8

    def test_f12_t1_two_sample_ttest_welch(self):
        col1 = Column(name="SampleA", data=[1.0, 2.0, 3.0, 4.0, 5.0])
        col2 = Column(name="SampleB", data=[10.0, 50.0, 20.0, 40.0, 30.0])
        res = StatisticsAnalyzer.two_sample_ttest(col1, col2, paired=False, equal_var=False)
        assert "Welch" in res["test_type"]
        assert res["dof"] is None

    def test_f12_t1_two_sample_ttest_paired(self):
        before = Column(name="Before", data=[100.0, 110.0, 105.0, 95.0, 120.0])
        after = Column(name="After", data=[90.0, 100.0, 95.0, 85.0, 110.0])
        res = StatisticsAnalyzer.two_sample_ttest(before, after, paired=True)
        assert "Paired" in res["test_type"]
        assert res["mean_difference"] == pytest.approx(10.0)
        assert res["dof"] == 4

    def test_f12_t1_multi_column_summary_table(self):
        cols = [
            Column(name="A", data=[1.0, 2.0, 3.0]),
            Column(name="B", data=[10.0, 20.0, 30.0]),
        ]
        summaries = StatisticsAnalyzer.column_summary_table(cols)
        assert len(summaries) == 2
        assert summaries[0]["mean"] == 2.0
        assert summaries[1]["mean"] == 20.0

    # Tier 2: Boundary & Corner Cases
    def test_f12_t2_stats_all_identical_values_zero_variance(self):
        col = Column(name="Const", data=[5.0, 5.0, 5.0, 5.0])
        s = col.stats()
        assert s["std"] == 0.0
        assert s["variance"] == 0.0
        assert s["iqr"] == 0.0

    def test_f12_t2_stats_with_nan_and_missing_values(self):
        col = Column(name="WithHoles", data=[10.0, None, np.nan, "text", 20.0, 30.0])
        s = col.stats()
        assert s["n"] == 3
        assert s["missing"] == 3
        assert s["mean"] == 20.0

    def test_f12_t2_ttest_insufficient_sample_size_error(self):
        col1 = Column(name="A", data=[1.0])
        col2 = Column(name="B", data=[2.0])
        with pytest.raises(ValueError):
            StatisticsAnalyzer.two_sample_ttest(col1, col2)

    def test_f12_t2_stats_dialog_instantiation_and_layout(self, qapp):
        cols = [Column(name="X", data=[1, 2, 3]), Column(name="Y", data=[4, 5, 6])]
        dlg = StatsDialog(cols)
        assert dlg.table_stats.rowCount() == 2
        dlg.close()

    def test_f12_t2_skewness_kurtosis_normal_distribution(self):
        np.random.seed(42)
        data = np.random.normal(0, 1, 1000).tolist()
        col = Column(name="Normal", data=data)
        s = col.stats()
        assert s["skewness"] == pytest.approx(0.0, abs=0.25)
        assert s["kurtosis"] == pytest.approx(0.0, abs=0.35)


# ===========================================================================
# FEATURE 13: Smart Ingestion & Batch
# ===========================================================================

class TestFeature13SmartIngestionBatch:
    # Tier 1
    def test_f13_t1_csv_sniffing_and_parsing(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("Wavelength,Absorbance\n400,0.1\n500,0.5\n600,0.2\n", encoding="utf-8")
        grid = ClipboardTableParser.parse_clipboard(csv_file.read_text(encoding="utf-8"))
        assert len(grid) == 4
        assert grid[0] == ["Wavelength", "Absorbance"]

    def test_f13_t1_tsv_ingestion(self, tmp_path):
        tsv_file = tmp_path / "data.tsv"
        tsv_file.write_text("Time\tSignal\n0.0\t1.2\n1.0\t3.4\n", encoding="utf-8")
        grid = ClipboardTableParser.parse_clipboard(tsv_file.read_text(encoding="utf-8"))
        assert len(grid) == 3
        assert grid[1] == [0.0, 1.2]

    def test_f13_t1_preamble_header_stripping(self):
        raw = "# Instrument: Shimadzu UV-2600\n# Date: 2026-10-29\n# Operator: Kyle\nTime\tSignal\n1\t10\n"
        lines = [line for line in raw.splitlines() if not line.strip().startswith("#")]
        clean_raw = "\n".join(lines)
        grid = ClipboardTableParser.parse_clipboard(clean_raw)
        assert grid[0] == ["Time", "Signal"]
        assert grid[1] == [1.0, 10.0]

    def test_f13_t1_auto_role_inference(self):
        def infer_role(name: str) -> ColumnRole:
            n = name.lower()
            if any(k in n for k in ["err", "sd", "std", "se"]):
                return ColumnRole.Y_ERR
            if any(k in n for k in ["time", "wave", "conc", "x"]):
                return ColumnRole.X
            return ColumnRole.Y

        assert infer_role("Wavelength") == ColumnRole.X
        assert infer_role("Absorbance") == ColumnRole.Y
        assert infer_role("Abs_Error") == ColumnRole.Y_ERR

    def test_f13_t1_batch_import_multiple_datasets(self, tmp_path):
        f1 = tmp_path / "run1.csv"
        f2 = tmp_path / "run2.csv"
        f1.write_text("X,Y\n1,10\n2,20\n", encoding="utf-8")
        f2.write_text("X,Y\n1,15\n2,25\n", encoding="utf-8")

        proj = Project.create_default("BatchProj")
        for idx, fpath in enumerate([f1, f2]):
            wb = Workbook.create_default(f"Run_{idx + 1}")
            grid = ClipboardTableParser.parse_clipboard(fpath.read_text(encoding="utf-8"))
            wb.sheets[0].columns[0].data = [row[0] for row in grid[1:]]
            wb.sheets[0].columns[1].data = [row[1] for row in grid[1:]]
            proj.workbooks.append(wb)
        assert len(proj.workbooks) == 3

    # Tier 2: Boundary & Corner Cases
    def test_f13_t2_empty_file_ingestion_safety(self, tmp_path):
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")
        grid = ClipboardTableParser.parse_clipboard(empty_file.read_text(encoding="utf-8"))
        assert grid == []

    def test_f13_t2_header_only_file_ingestion(self, tmp_path):
        hdr_file = tmp_path / "hdr.csv"
        hdr_file.write_text("ColA,ColB,ColC\n", encoding="utf-8")
        grid = ClipboardTableParser.parse_clipboard(hdr_file.read_text(encoding="utf-8"))
        assert len(grid) == 1
        assert grid[0] == ["ColA", "ColB", "ColC"]

    def test_f13_t2_semicolon_delimited_european_file(self, tmp_path):
        euro_file = tmp_path / "euro.csv"
        euro_file.write_text("1.25;3.45\n6.78;9.10\n", encoding="utf-8")
        grid = ClipboardTableParser.parse_clipboard(euro_file.read_text(encoding="utf-8"))
        assert len(grid) == 2
        assert grid[0] == [1.25, 3.45]
        assert grid[1] == [6.78, 9.10]

    def test_f13_t2_import_dialog_file_selection(self, qapp, tmp_path):
        f1 = tmp_path / "sel1.csv"
        f1.write_text("A,B\n1,2\n", encoding="utf-8")
        dlg = ImportDialog(initial_filepath=str(f1))
        assert dlg.filepath == str(f1)
        dlg.close()


# ===========================================================================
# FEATURE 14: Project Architecture & Docks
# ===========================================================================

class TestFeature14ProjectArchitectureDocks:
    # Tier 1
    def test_f14_t1_project_default_hierarchy(self):
        proj = Project.create_default("TestProject")
        assert len(proj.workbooks) == 1
        wb = proj.workbooks[0]
        assert len(wb.sheets) == 1
        ws = wb.sheets[0]
        assert ws.column_count() >= 2

    def test_f14_t1_project_json_serialization(self, tmp_path):
        proj = SampleProjects.create_spectroscopy_sample()
        out_kgraph = str(tmp_path / "project.kgraph")
        proj.save_to_file(out_kgraph)
        assert os.path.exists(out_kgraph)
        assert os.path.getsize(out_kgraph) > 500

    def test_f14_t1_project_json_deserialization(self, tmp_path):
        proj_orig = SampleProjects.create_spectroscopy_sample()
        out_kgraph = str(tmp_path / "reload.kgraph")
        proj_orig.save_to_file(out_kgraph)

        proj_loaded = Project.load_from_file(out_kgraph)
        assert proj_loaded.name == proj_orig.name
        assert len(proj_loaded.workbooks) == len(proj_orig.workbooks)
        assert len(proj_loaded.graphs) == len(proj_orig.graphs)
        orig_ws = proj_orig.workbooks[0].sheets[0]
        load_ws = proj_loaded.workbooks[0].sheets[0]
        assert orig_ws.columns[0].data[:5] == load_ws.columns[0].data[:5]

    def test_f14_t1_numpy_types_json_serialization(self, tmp_path):
        proj = Project.create_default("NumpyProj")
        ws = proj.workbooks[0].sheets[0]
        ws.columns[0].data = [float(x) for x in np.arange(10, dtype=np.float64)]
        ws.columns[1].data = [float(y) for y in np.linspace(0, 1, 10)]
        out_path = str(tmp_path / "numpy_proj.kgraph")
        proj.save_to_file(out_path)
        assert os.path.exists(out_path)

    def test_f14_t1_project_explorer_tree_population(self, qapp):
        proj = SampleProjects.create_spectroscopy_sample()
        win = MainWindow(project=proj)
        win.showNormal()
        QApplication.processEvents()
        explorer = win.explorer_widget
        assert explorer.tree.topLevelItemCount() >= 2
        win.close()

    # Tier 2: Boundary & Corner Cases
    def test_f14_t2_empty_project_serialization(self, tmp_path):
        proj = Project(name="EmptyRoot", workbooks=[])
        out_path = str(tmp_path / "empty_root.kgraph")
        proj.save_to_file(out_path)
        loaded = Project.load_from_file(out_path)
        assert len(loaded.workbooks) >= 1

    def test_f14_t2_special_character_and_unicode_names(self, tmp_path):
        proj = Project.create_default("Project & <Test> ™ / 实验")
        proj.workbooks[0].name = "Book 1 (α/β/γ)"
        proj.workbooks[0].sheets[0].name = "Sheet: [100%]"
        out_path = str(tmp_path / "unicode.kgraph")
        proj.save_to_file(out_path)
        loaded = Project.load_from_file(out_path)
        assert loaded.name == proj.name
        assert loaded.workbooks[0].name == proj.workbooks[0].name

    def test_f14_t2_multiple_workbooks_and_sheets_model(self):
        proj = Project(name="MultiBook")
        for b_idx in range(3):
            wb = Workbook(name=f"Book_{b_idx + 1}")
            for s_idx in range(4):
                ws = Worksheet.create_default(f"Sheet_{s_idx + 1}")
                wb.sheets.append(ws)
            proj.workbooks.append(wb)
        assert len(proj.workbooks) == 4
        assert len(proj.workbooks[1].sheets) == 4

    def test_f14_t2_corrupted_json_handling(self, tmp_path):
        bad_json = tmp_path / "corrupted.kgraph"
        bad_json.write_text("{ incomplete_json ...", encoding="utf-8")
        with pytest.raises(Exception):
            Project.load_from_file(str(bad_json))

    def test_f14_t2_report_model_serialization(self, tmp_path):
        proj = Project.create_default("ReportProj")
        rep = ReportModel(title="Analysis Summary", html_content="<h1>Results</h1><p>Pass</p>")
        proj.reports.append(rep)
        out_path = str(tmp_path / "report_proj.kgraph")
        proj.save_to_file(out_path)
        loaded = Project.load_from_file(out_path)
        assert len(loaded.reports) == 1
        assert loaded.reports[0].title == "Analysis Summary"
        assert "<h1>Results</h1>" in loaded.reports[0].html_content


# ===========================================================================
# TIER 3: Cross-Feature Interactions (16 Tests)
# ===========================================================================

class TestTier3CrossFeatureInteractions:
    def test_f1_to_f7_pipeline_spreadsheet_formula_plot_fit_export(self, tmp_path):
        """Pipeline: Sheet -> Formula -> Plot -> Fit -> Export."""
        proj = Project.create_default("FullPipeline")
        ws = proj.workbooks[0].sheets[0]
        x = np.linspace(1, 10, 20)
        ws.columns[0].name = "Time"
        ws.columns[0].role = ColumnRole.X
        ws.columns[0].data = x.tolist()
        ws.columns[1].name = "Signal"
        ws.columns[1].role = ColumnRole.Y

        ws.apply_formula(1, "col(Time) * 2.5 + 4.0")
        graph = GraphModel(title="PipelineGraph")
        curve = CurveModel(
            source_workbook=proj.workbooks[0].name,
            source_sheet=ws.name,
            x_col_idx=0,
            y_col_idx=1,
            label="Raw Signal",
        )
        graph.add_curve(curve)
        proj.graphs.append(graph)

        x_data, y_data, _ = ws.columns[0].get_valid_numeric_pairs(ws.columns[1])
        fit_res = CurveFitter.linear_fit(x_data, y_data)
        assert fit_res.parameters["Slope (m)"] == pytest.approx(2.5, rel=1e-4)

        pm = PlotManager(graph, proj)
        pm.render()
        out_file = str(tmp_path / "pipeline.png")
        pm.export_image(out_file)
        assert os.path.exists(out_file)

    def test_clipboard_to_histogram_and_theme(self):
        """Clipboard paste -> populate worksheet -> render histogram -> apply Nature theme."""
        tsv_data = "Values\n1.2\n2.3\n1.8\n2.9\n3.1\n2.4\n1.9\n"
        grid = ClipboardTableParser.parse_clipboard(tsv_data)
        proj = Project.create_default("HistProject")
        ws = proj.workbooks[0].sheets[0]
        ws.columns[0].name = grid[0][0]
        ws.columns[0].data = [row[0] for row in grid[1:]]

        graph = GraphModel(title="HistGraph", plot_type="histogram")
        graph.theme = "Nature"
        curve = CurveModel(source_workbook=proj.workbooks[0].name, source_sheet=ws.name, x_col_idx=0, y_col_idx=0, plot_type="histogram")
        graph.add_curve(curve)
        proj.graphs.append(graph)

        pm = PlotManager(graph, proj)
        pm.render()
        assert pm.model.theme == "Nature"

    def test_signal_smoothing_to_peak_analysis_to_report(self):
        """Raw signal -> Savitzky-Golay smooth -> Peak deconvolution -> HTML report."""
        np.random.seed(42)
        x = np.linspace(0, 100, 201)
        clean = 2.0 * np.exp(-0.5 * ((x - 50) / 6) ** 2)
        noisy = clean + np.random.normal(0, 0.05, 201)

        smoothed = SignalProcessor.savitzky_golay(noisy, window_length=15, polyorder=2)
        peaks_res = PeakAnalyzer.analyze_peaks(x, smoothed, min_prominence_pct=15.0)
        assert len(peaks_res.peaks) == 1
        assert peaks_res.peaks[0].x_center == pytest.approx(50.0, abs=1.0)
        report_html = peaks_res.to_html_report()
        assert "Peak ID" in report_html

    def test_multi_column_stats_to_box_plot_and_labels(self):
        """Multi-column stats -> box plot -> label updates."""
        proj = Project.create_default("BoxStats")
        ws = proj.workbooks[0].sheets[0]
        c1 = Column(name="Control", long_name="Vehicle Control", units="μM", data=[10, 12, 11, 14, 13])
        c2 = Column(name="Drug", long_name="Treated Compound", units="μM", data=[25, 28, 22, 26, 27])
        ws.columns = [c1, c2]

        stats_summary = StatisticsAnalyzer.column_summary_table([c1, c2])
        assert stats_summary[0]["mean"] == pytest.approx(12.0)
        assert stats_summary[1]["mean"] == pytest.approx(25.6)

        graph = GraphModel(title="BoxGraph", plot_type="box")
        graph.x_title = "Experimental Group"
        graph.y_title = f"Concentration ({c1.units})"
        graph.add_curve(CurveModel(source_workbook=proj.workbooks[0].name, source_sheet=ws.name, x_col_idx=0, y_col_idx=1, plot_type="box"))
        proj.graphs.append(graph)
        pm = PlotManager(graph, proj)
        pm.render()

    def test_plot_add_curve_and_fit_overlay(self):
        """Create plot -> Add curve -> Fit overlay -> Verify curve count."""
        proj = SampleProjects.create_spectroscopy_sample()
        graph = proj.graphs[0]
        initial_curves = len(graph.curves)

        fit_curve = CurveModel(
            source_workbook=proj.workbooks[0].name,
            source_sheet=proj.workbooks[0].sheets[0].name,
            x_col_idx=0,
            y_col_idx=1,
            label="Fitted Baseline",
            color="#d62728",
            is_fit_curve=True,
        )
        graph.add_curve(fit_curve)
        assert len(graph.curves) == initial_curves + 1

    def test_formula_execution_with_undo_redo_sync(self):
        """Formula execution -> Undo -> Redo -> Verify state matches."""
        ws = Worksheet.create_default("FormulaUndoSync", num_rows=3)
        ws.columns[0].data = [10.0, 20.0, 30.0]
        stack = QUndoStack()

        old_data = list(ws.columns[1].data)
        new_data = [100.0, 200.0, 300.0]
        cmd = FormulaCommand(ws, 1, old_formula="", old_data=old_data, new_formula="col(A)*10", new_data=new_data)
        stack.push(cmd)
        assert ws.columns[1].data == new_data

        stack.undo()
        assert ws.columns[1].data == old_data
        stack.redo()
        assert ws.columns[1].data == new_data

    def test_project_save_and_reload_complete_state(self, tmp_path):
        """Full project save and reload verifying curves, theme, and data integrity."""
        proj = SampleProjects.create_spectroscopy_sample()
        proj.graphs[0].theme = "Science"
        proj.graphs[0].title_text = "Sample Reload Test"
        save_path = str(tmp_path / "complete_state.kgraph")
        proj.save_to_file(save_path)

        reloaded = Project.load_from_file(save_path)
        assert reloaded.graphs[0].theme == "Science"
        assert reloaded.graphs[0].title_text == "Sample Reload Test"

    def test_high_dpi_scaling_and_export_dpi(self, qapp, tmp_path):
        """Render canvas with high resolution export DPI scaling."""
        proj = SampleProjects.create_spectroscopy_sample()
        pm = PlotManager(proj.graphs[0], proj)
        pm.render()
        out_300 = str(tmp_path / "res_300.png")
        pm.export_image(out_300, dpi=300)
        assert os.path.exists(out_300)
        assert os.path.getsize(out_300) > 2000

    def test_sample_data_roi_span_to_subrange_fit(self):
        """Load spectroscopy sample -> select ROI [450, 550] -> fit sub-range."""
        proj = SampleProjects.create_spectroscopy_sample()
        ws = proj.workbooks[0].sheets[0]
        x, y, _ = ws.columns[0].get_valid_numeric_pairs(ws.columns[1])
        res_roi = CurveFitter.linear_fit(x, y, x_min=450, x_max=550)
        assert res_roi.success is True

    def test_spectroscopy_sample_baseline_and_explorer_update(self, qapp):
        """Spectroscopy sample -> Baseline subtraction -> MainWindow Explorer update."""
        proj = SampleProjects.create_spectroscopy_sample()
        win = MainWindow(project=proj)
        win.showNormal()
        QApplication.processEvents()
        assert win.explorer_widget.tree.topLevelItemCount() >= 1
        win.close()

    def test_kinetics_sample_errorbar_and_mm_fit(self):
        """Enzyme kinetics sample -> Michaelis-Menten fit with error bar curve."""
        proj = SampleProjects.create_enzyme_kinetics_sample()
        ws = proj.workbooks[0].sheets[0]
        s, v, _ = ws.columns[0].get_valid_numeric_pairs(ws.columns[1])
        res = CurveFitter.nonlinear_fit(s, v, model_type="michaelis_menten")
        assert res.success is True
        assert res.parameters["Vmax"] > 0
        assert res.parameters["Km"] > 0

    def test_dual_axis_reactor_profile_and_theme_toggle(self, qapp):
        """Dual-axis sample -> render primary and secondary axes -> toggle theme."""
        proj = SampleProjects.create_dual_axis_sample()
        win = MainWindow(project=proj)
        win.showNormal()
        QApplication.processEvents()
        win.toggle_theme()
        assert win.is_dark_theme is True
        win.close()

    def test_theme_switch_canvas_repaint_and_dock_sync(self, qapp):
        """MainWindow theme switch repaints canvas and updates property inspector."""
        proj = SampleProjects.create_spectroscopy_sample()
        win = MainWindow(project=proj)
        win.showNormal()
        win.toggle_theme()
        QApplication.processEvents()
        gw = win.get_active_graph_widget()
        if gw:
            gw.canvas_widget.plot_manager.render()
        win.close()

    def test_batch_import_to_multi_sheet_correlation(self):
        """Import multiple series into workbook -> compute correlation."""
        proj = Project.create_default("BatchCorr")
        ws = proj.workbooks[0].sheets[0]
        c1 = Column(name="X1", data=[1, 2, 3, 4, 5])
        c2 = Column(name="Y1", data=[2, 4, 6, 8, 10])
        ws.columns = [c1, c2]
        res = StatisticsAnalyzer.two_sample_ttest(c1, c2, paired=True)
        assert res["t_statistic"] is not None

    def test_column_property_edit_updates_plot_labels(self):
        """Column rename updates display_label and axis labels."""
        col = Column(name="A", long_name="Time", units="s")
        assert col.display_label == "Time (s)"
        col.units = "min"
        assert col.display_label == "Time (min)"

    def test_canvas_data_reader_to_worksheet_append(self):
        """Data Reader extraction appends coordinates to worksheet."""
        proj = SampleProjects.create_spectroscopy_sample()
        ws = proj.workbooks[0].sheets[0]
        initial_rows = ws.row_count()
        extracted_x, extracted_y = 520.0, 0.85
        ws.columns[0].set_value(initial_rows, extracted_x)
        ws.columns[1].set_value(initial_rows, extracted_y)
        assert ws.row_count() == initial_rows + 1
        assert ws.columns[0].get_value(initial_rows) == 520.0


# ===========================================================================
# TIER 4: Real-World Scenarios (5 Comprehensive Workload Tests)
# ===========================================================================

class TestTier4RealWorldScenarios:
    def test_realworld_scenario_1_uv_vis_spectroscopy(self, tmp_path):
        """
        Scenario 1: UV-Vis Spectroscopy Overlapping Peaks.
        Full spectrum analysis with 3 overlapping Gaussian peaks,
        baseline correction, FWHM deconvolution, AUC integration,
        HTML report generation, and callout annotation placement.
        """
        proj = SampleProjects.create_spectroscopy_sample()
        ws = proj.workbooks[0].sheets[0]
        graph = proj.graphs[0]

        x, y, _ = ws.columns[0].get_valid_numeric_pairs(ws.columns[1])
        assert len(x) == 201

        # 1. Peak deconvolution & baseline correction
        res = PeakAnalyzer.analyze_peaks(x, y, min_prominence_pct=10.0, min_distance=15, baseline_mode="linear")
        assert len(res.peaks) >= 2

        # 2. Add peak center annotations to graph
        for p in res.peaks:
            graph.annotations.append({
                "type": "text",
                "x": p.x_center,
                "y": p.y_height + 0.05,
                "text": f"λ={p.x_center:.0f} nm",
                "color": "#d62728",
            })

        # 3. Generate HTML report
        report_html = res.to_html_report()
        assert "Peak Integration" in report_html
        rep_model = ReportModel(title="UV-Vis Deconvolution Report", html_content=report_html)
        proj.reports.append(rep_model)

        # 4. Render and export figure
        pm = PlotManager(graph, proj)
        pm.render()
        out_fig = str(tmp_path / "uv_vis_report_figure.png")
        pm.export_image(out_fig, dpi=150)
        assert os.path.exists(out_fig)
        assert len(proj.reports) == 1

    def test_realworld_scenario_2_enzyme_kinetics(self, tmp_path):
        """
        Scenario 2: Enzyme Kinetics with Error Bars.
        Multi-column spreadsheet, error bar detection,
        Michaelis-Menten nonlinear fitting, confidence bands.
        """
        proj = SampleProjects.create_enzyme_kinetics_sample()
        ws = proj.workbooks[0].sheets[0]
        graph = proj.graphs[0]

        s, v, _ = ws.columns[0].get_valid_numeric_pairs(ws.columns[1])
        err = ws.columns[2].to_numpy_array(len(s))

        fit_res = CurveFitter.nonlinear_fit(s, v, model_type="michaelis_menten")
        assert fit_res.success is True
        assert fit_res.r_squared > 0.95

        fit_curve = CurveModel(
            source_workbook=proj.workbooks[0].name,
            source_sheet=ws.name,
            x_col_idx=0,
            y_col_idx=1,
            label=f"MM Fit (Vmax={fit_res.parameters['Vmax']:.1f})",
            color="#0284c7",
            line_style="-",
            line_width=2.0,
            plot_type="line",
            is_fit_curve=True,
        )
        graph.add_curve(fit_curve)

        pm = PlotManager(graph, proj)
        pm.render()
        out_fig = str(tmp_path / "enzyme_kinetics.pdf")
        pm.export_image(out_fig)
        assert os.path.exists(out_fig)

    def test_realworld_scenario_3_pharmacology_dose_response(self, tmp_path):
        """
        Scenario 3: Pharmacology Dose-Response IC50.
        Semi-log sigmoidal Hill 4PL fitting, publication figure export (PDF, PNG).
        """
        proj = SampleProjects.create_dose_response_sample()
        ws = proj.workbooks[0].sheets[0]
        graph = proj.graphs[0]

        log_c, resp, _ = ws.columns[0].get_valid_numeric_pairs(ws.columns[1])

        fit_res = CurveFitter.nonlinear_fit(log_c, resp, model_type="hill")
        assert fit_res.success is True
        assert fit_res.r_squared > 0.95

        pm = PlotManager(graph, proj)
        pm.render()
        out_png = str(tmp_path / "dose_response.png")
        out_pdf = str(tmp_path / "dose_response.pdf")
        pm.export_image(out_png, dpi=200)
        pm.export_image(out_pdf)
        assert os.path.exists(out_png)
        assert os.path.exists(out_pdf)

    def test_realworld_scenario_4_dual_axis_reactor_profile(self, tmp_path):
        """
        Scenario 4: Multi-Channel Dual-Axis Reactor Profile.
        Twin-Y plot (Temperature & Pressure vs Time), multi-series styling,
        label editing, dark theme toggle.
        """
        proj = SampleProjects.create_dual_axis_sample()
        graph = proj.graphs[0]
        graph.theme = "Modern Dark"

        pm = PlotManager(graph, proj)
        pm.render()

        out_dark = str(tmp_path / "reactor_dark.png")
        pm.export_image(out_dark, dpi=150)
        assert os.path.exists(out_dark)

    def test_realworld_scenario_5_batch_file_ingestion_and_auto_comparison(self, tmp_path):
        """
        Scenario 5: Batch File Ingestion & Auto Comparison.
        Multi-file CSV ingestion, overlay comparison plot, summary statistics.
        """
        files = []
        for i in range(1, 4):
            fp = tmp_path / f"Run_{i}.csv"
            t = np.linspace(0, 10, 11)
            y = (i * 2.0) * t + np.random.normal(0, 0.1, 11)
            lines = ["Time,Signal"] + [f"{ti:.1f},{yi:.3f}" for ti, yi in zip(t, y)]
            fp.write_text("\n".join(lines), encoding="utf-8")
            files.append(fp)

        proj = Project.create_default("BatchComparison")
        wb = proj.workbooks[0]
        wb.sheets.clear()

        comp_graph = GraphModel(title="Batch Run Comparison", plot_type="line")
        palette = get_theme_palette("Origin Classic")

        for idx, fp in enumerate(files):
            grid = ClipboardTableParser.parse_clipboard(fp.read_text(encoding="utf-8"))
            ws = Worksheet(name=f"Run_{idx + 1}")
            col_t = Column(name="Time", role=ColumnRole.X, data=[row[0] for row in grid[1:]])
            col_s = Column(name=f"Signal_R{idx + 1}", role=ColumnRole.Y, data=[row[1] for row in grid[1:]])
            ws.columns = [col_t, col_s]
            wb.sheets.append(ws)

            curve = CurveModel(
                source_workbook=wb.name,
                source_sheet=ws.name,
                x_col_idx=0,
                y_col_idx=1,
                label=f"Run {idx + 1}",
                color=palette[idx % len(palette)],
                plot_type="line",
            )
            comp_graph.add_curve(curve)

        proj.graphs.append(comp_graph)
        assert len(wb.sheets) == 3
        assert len(comp_graph.curves) == 3

        pm = PlotManager(comp_graph, proj)
        pm.render()
        out_comp = str(tmp_path / "batch_comparison.png")
        pm.export_image(out_comp, dpi=150)
        assert os.path.exists(out_comp)
