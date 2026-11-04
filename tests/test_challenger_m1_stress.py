"""
Empirical Stress and Adversarial Challenge Suite for Milestone 1.
Challenger: teamwork_challenger_m1_1
Tests edge cases, boundary conditions, and stress loads across all 7 M1 focus areas.
"""

import os
import sys
import tempfile
import pytest
import numpy as np
import matplotlib.pyplot as plt

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from omnigraph.core.worksheet import Workbook, Worksheet, Column, ColumnRole
from omnigraph.core.project import Project, GraphModel, CurveModel, NumpyEncoder
from omnigraph.graphing.plot_types import PlotRenderer
from omnigraph.ui.spreadsheet_view import SpreadsheetWidget
from omnigraph.ui.dialogs.formula_dialog import FormulaDialog
from omnigraph.ui.dialogs.legend_dialog import LegendEditorDialog
from omnigraph.ui.dialogs.add_curve_dialog import AddCurveDialog
from omnigraph.ui.dialogs.fit_dialog import FitDialog
from omnigraph.ui.dialogs.peak_dialog import PeakAnalysisDialog
from omnigraph.ui.dialogs.smooth_dialog import SmoothDialog
from omnigraph.ui.dialogs.stats_dialog import StatsDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


# =========================================================================
# 1. Quick Fill Stress & Boundary Tests
# =========================================================================

def test_quick_fill_boundary_n(qapp):
    """Test Quick Fill with n=0, 1, 10000 on both uniform and normal distributions."""
    # Test Column level methods with n=0, 1, 10000
    col = Column(name="TestCol", role=ColumnRole.Y)
    
    # n = 0
    col.fill_random_uniform(low=0.0, high=1.0, count=0)
    assert len(col.data) == 0
    col.fill_random_normal(mean=0.0, std=1.0, count=0)
    assert len(col.data) == 0

    # n = 1
    col.fill_random_uniform(low=-5.0, high=5.0, count=1)
    assert len(col.data) == 1
    assert -5.0 <= col.data[0] <= 5.0
    col.fill_random_normal(mean=10.0, std=2.0, count=1)
    assert len(col.data) == 1
    assert isinstance(col.data[0], float)

    # n = 10000
    col.fill_random_uniform(low=0.0, high=100.0, count=10000)
    assert len(col.data) == 10000
    assert all(0.0 <= v <= 100.0 for v in col.data)

    col.fill_random_normal(mean=0.0, std=1.0, count=10000)
    assert len(col.data) == 10000
    # Statistical checks on large sample
    assert abs(np.mean(col.data)) < 0.1
    assert abs(np.std(col.data) - 1.0) < 0.1


def test_quick_fill_spreadsheet_widget_boundary(qapp):
    """Test SpreadsheetWidget fill actions with various sheet sizes."""
    # Empty worksheet
    ws_empty = Worksheet("Empty")
    ws_empty.add_column(role=ColumnRole.Y)
    sw_empty = SpreadsheetWidget(ws_empty)
    # Filling empty sheet defaults to min 50 rows
    sw_empty._fill_col(0, "uniform")
    assert len(ws_empty.columns[0].data) == 50
    sw_empty._fill_col(0, "normal")
    assert len(ws_empty.columns[0].data) == 50

    # Large worksheet (10000 rows)
    ws_large = Worksheet.create_default(num_rows=10000)
    sw_large = SpreadsheetWidget(ws_large)
    sw_large._fill_col(0, "uniform")
    assert len(ws_large.columns[0].data) == 10000
    sw_large._fill_col(0, "normal")
    assert len(ws_large.columns[0].data) == 10000


# =========================================================================
# 2. Sorting Adversarial & Boundary Tests
# =========================================================================

def test_sorting_adversarial_mixed_values():
    """Test sorting columns with mixed ints, negative floats, strings, None, empty strings, unicode, and NaN."""
    ws = Worksheet("SortTest")
    col0 = ws.add_column(name="A", role=ColumnRole.X)
    col1 = ws.add_column(name="B", role=ColumnRole.Y)

    adversarial_data = [
        np.nan,
        -999.5,
        "100",           # string looking like a number
        None,
        0,
        "Alpha",
        "",
        -0.0,
        float("nan"),
        "日本語",        # unicode string
        1000000,
        False,           # bool
        "café",          # unicode accent
        -1e-8,
        None,
        True,            # bool
        "   ",           # whitespace string
    ]
    col0.data = list(adversarial_data)
    col1.data = list(range(len(adversarial_data)))

    # Ascending sort
    ws.sort_by_column(0, ascending=True)
    assert len(col0.data) == len(adversarial_data)
    assert len(col1.data) == len(adversarial_data)

    # Let's inspect group ordering:
    # Group 0: numbers (including numeric strings converted to float, bools are group 1)
    # Group 1: strings and bools
    # Group 2: None, "", NaN
    
    # Verify numbers are sorted ascending
    numbers = []
    strings_and_bools = []
    missing_group = []

    for v in col0.data:
        if v is None or v == "" or (isinstance(v, float) and np.isnan(v)):
            missing_group.append(v)
        elif isinstance(v, bool):
            strings_and_bools.append(v)
        else:
            try:
                numbers.append(float(v))
            except (ValueError, TypeError):
                strings_and_bools.append(v)

    # In ascending sort: numbers must come before strings/bools, which come before missing
    # Let's verify non-decreasing numbers
    for i in range(len(numbers) - 1):
        assert numbers[i] <= numbers[i + 1]

    # Verify descending sort does not crash and reverses appropriately
    ws.sort_by_column(0, ascending=False)
    assert len(col0.data) == len(adversarial_data)
    assert len(col1.data) == len(adversarial_data)

    # Verify sorting single row, zero rows, and column index out of bounds
    ws_single = Worksheet.create_default(num_rows=1)
    ws_single.sort_by_column(0, ascending=True)  # should not crash
    ws_single.sort_by_column(-1, ascending=True)  # out of bounds: should no-op
    ws_single.sort_by_column(99, ascending=True)  # out of bounds: should no-op


# =========================================================================
# 3. Formula Infinity & Boundary Math Handling
# =========================================================================

def test_formula_infinity_stress(qapp):
    """Test formulas: dividing by zero, log(0), log(-1), sqrt(-1), 1/(A-B) where A==B."""
    ws = Worksheet.create_default(num_rows=6)
    ws.columns[0].data = [0.0, 5.0, -10.0, 0.0, 1.0, 2.0]
    ws.columns[1].data = [0.0, 5.0, -10.0, 4.0, 1.0, 2.0]
    col_res = ws.add_column(name="C", role=ColumnRole.Y)

    # 1. 1.0 / A (with A=0.0) -> inf
    ws.apply_formula(2, "1.0 / col(A)")
    assert col_res.data[0] is None
    assert col_res.data[3] is None
    assert col_res.data[1] == pytest.approx(0.2)
    assert col_res.data[2] == pytest.approx(-0.1)
    # Ensure NO inf or nan values persist
    for val in col_res.data:
        assert val is None or (isinstance(val, float) and np.isfinite(val))

    # 2. log(A) (with A=0.0 -> -inf, A=-10.0 -> nan)
    ws.apply_formula(2, "log(col(A))")
    assert col_res.data[0] is None  # log(0) -> -inf -> None
    assert col_res.data[2] is None  # log(-10) -> nan -> None
    assert col_res.data[3] is None  # log(0) -> -inf -> None
    for val in col_res.data:
        assert val is None or (isinstance(val, float) and np.isfinite(val))

    # 3. sqrt(col(A)) (with A=-10.0 -> nan)
    ws.apply_formula(2, "sqrt(col(A))")
    assert col_res.data[2] is None
    for val in col_res.data:
        assert val is None or (isinstance(val, float) and np.isfinite(val))

    # 4. 1.0 / (col(A) - col(B)) where A == B for rows 0, 1, 2, 4, 5
    ws.apply_formula(2, "1.0 / (col(A) - col(B))")
    assert col_res.data[0] is None
    assert col_res.data[1] is None
    assert col_res.data[2] is None
    assert col_res.data[4] is None
    assert col_res.data[5] is None
    # row 3: A=0, B=4 -> 1 / (0 - 4) = -0.25
    assert col_res.data[3] == pytest.approx(-0.25)
    for val in col_res.data:
        assert val is None or (isinstance(val, float) and np.isfinite(val))

    # 5. Direct ZeroDivisionError in scalar expression, e.g. "1 / 0"
    ws.apply_formula(2, "1 / 0")
    assert all(val is None for val in col_res.data)


# =========================================================================
# 4. JSON Serialization Stress Tests
# =========================================================================

def test_json_serialization_numpy_stress(tmp_path):
    """Test saving project with diverse numpy types: arrays, float32, int32, bool_, nan, None."""
    proj = Project.create_default("StressSerialization")
    ws = proj.workbooks[0].sheets[0]

    # Populate with extensive variety of numpy types and edge values
    ws.columns[0].data = [
        np.float32(1.2345),
        np.float64(-9.8765),
        np.int8(-128),
        np.int16(32767),
        np.int32(-2147483648),
        np.int64(9223372036854775807),
        np.uint8(255),
        np.uint16(65535),
        np.uint32(4294967295),
        np.bool_(True),
        np.bool_(False),
        np.nan,
        float("nan"),
        float("inf"),
        float("-inf"),
        None,
        np.float32(np.nan),
        np.float64(np.inf),
    ]

    # Second column with numpy array as elements or list
    ws.columns[1].data = [
        np.array([1, 2, 3]),
        "regular string",
        {"nested": np.int32(99)},
        None,
    ]

    filepath = str(tmp_path / "numpy_stress.kgraph")
    proj.save_project(filepath)
    assert os.path.exists(filepath)

    # Reload and verify
    loaded = Project.load_from_file(filepath)
    data0 = loaded.workbooks[0].sheets[0].columns[0].data

    assert isinstance(data0[0], float)
    assert pytest.approx(data0[0], 1e-4) == 1.2345
    assert isinstance(data0[2], int)
    assert data0[2] == -128
    assert data0[5] == 9223372036854775807
    assert data0[9] is True
    assert data0[10] is False
    # Check round-trip preservation
    assert isinstance(data0[0], float)
    assert pytest.approx(data0[0], 1e-4) == 1.2345
    assert isinstance(data0[2], int)
    assert data0[2] == -128
    assert data0[3] == 32767
    assert data0[4] == -2147483648
    assert data0[5] == 9223372036854775807
    assert data0[9] is True
    assert data0[10] is False
    assert data0[15] is None
    # np.nan / float nan round-trip
    assert np.isnan(data0[11])
    assert np.isnan(data0[12])

    # Verify column 1 loaded
    data1 = loaded.workbooks[0].sheets[0].columns[1].data
    assert data1[0] == [1, 2, 3]
    assert data1[1] == "regular string"
    assert data1[2] == {"nested": 99}
    assert data1[3] is None


# =========================================================================
# 5. Bar & Horizontal Bar Charts Stress Tests
# =========================================================================

def test_bar_chart_edge_coordinates():
    """Test plotting bar and hbar with duplicate x, single points, and identical coordinates."""
    fig, ax = plt.subplots()

    # 1. Bar with all identical coordinates
    cm_bar = CurveModel(plot_type="bar")
    x_all_same = np.array([7.0, 7.0, 7.0, 7.0])
    y_vals = np.array([1.0, 2.0, 3.0, 4.0])
    art_bar = PlotRenderer.render_curve(ax, cm_bar, x_all_same, y_vals)
    assert len(art_bar.patches) == 4
    for p in art_bar.patches:
        assert p.get_width() > 0.0
        assert p.get_width() == pytest.approx(0.75)

    # 2. Bar with single point
    ax.cla()
    x_single = np.array([42.0])
    y_single = np.array([100.0])
    art_single = PlotRenderer.render_curve(ax, cm_bar, x_single, y_single)
    assert len(art_single.patches) == 1
    assert art_single.patches[0].get_width() > 0.0
    assert art_single.patches[0].get_width() == pytest.approx(0.75)

    # 3. Bar with cluster duplicates: e.g. [1.0, 1.0, 1.0, 10.0, 10.0]
    ax.cla()
    x_cluster = np.array([1.0, 1.0, 1.0, 10.0, 10.0])
    y_cluster = np.array([5.0, 6.0, 7.0, 8.0, 9.0])
    art_cluster = PlotRenderer.render_curve(ax, cm_bar, x_cluster, y_cluster)
    assert len(art_cluster.patches) == 5
    # The positive diff is 9.0, width = 9.0 * 0.75 = 6.75
    for p in art_cluster.patches:
        assert p.get_width() == pytest.approx(6.75)

    # 4. HBar with all identical y
    ax.cla()
    cm_hbar = CurveModel(plot_type="hbar")
    y_all_same = np.array([-3.5, -3.5, -3.5])
    x_vals = np.array([10.0, 20.0, 30.0])
    art_hbar = PlotRenderer.render_curve(ax, cm_hbar, y_all_same, x_vals)
    assert len(art_hbar.patches) == 3
    for p in art_hbar.patches:
        assert p.get_height() > 0.0
        assert p.get_height() == pytest.approx(0.75)

    # 5. HBar single point
    ax.cla()
    art_hsingle = PlotRenderer.render_curve(ax, cm_hbar, np.array([5.0]), np.array([2.0]))
    assert len(art_hsingle.patches) == 1
    assert art_hsingle.patches[0].get_height() == pytest.approx(0.75)

    plt.close(fig)


# =========================================================================
# 6. Legend Editor Stress Tests
# =========================================================================

def test_legend_editor_stress(qapp):
    """Test Legend Editor reset with multiple curves, nameless curves, fit curves, and special characters."""
    graph = GraphModel(title="ComplexGraph")
    graph.curves = [
        CurveModel(source_sheet="S1", label="Signal Alpha"),
        CurveModel(source_sheet="S1", label=""),  # nameless curve
        CurveModel(source_sheet="S1", label=None),  # None label
        CurveModel(source_sheet="S1", label="Linear Fit [y = 3.2x + 1.1, R²=0.998]"),  # fit curve
        CurveModel(source_sheet="S1", label="Unicode: Δλ / θ (µm) ± 5%"),  # symbols
    ]

    dlg = LegendEditorDialog(graph)
    assert dlg.table_series.rowCount() == 5

    # Test reset to columns
    dlg._preset_reset_to_columns()
    assert dlg.table_series.item(0, 3).text() == "Signal Alpha"
    assert dlg.table_series.item(1, 3).text() == "Curve_2"
    assert dlg.table_series.item(2, 3).text() == "Curve_3"
    assert dlg.table_series.item(3, 3).text() == "Linear Fit [y = 3.2x + 1.1, R²=0.998]"
    assert dlg.table_series.item(4, 3).text() == "Unicode: Δλ / θ (µm) ± 5%"

    # Apply changes
    dlg._apply_changes()
    assert graph.curves[1].label == "Curve_2"
    assert graph.curves[2].label == "Curve_3"
    dlg.close()


# =========================================================================
# 7. Smoothing & Dialogs Stress Tests
# =========================================================================

def test_smoothing_sparse_and_missing_rows(qapp):
    """Test smoothing with sparse/missing rows across various algorithms."""
    ws = Worksheet("SparseSheet")
    col_x = ws.add_column(name="X", role=ColumnRole.X)
    col_y = ws.add_column(name="Y", role=ColumnRole.Y)

    # 30 rows with 50% None
    col_x.data = [float(i) for i in range(30)]
    y_raw = []
    for i in range(30):
        if i % 2 == 0:
            y_raw.append(float(i**2))
        else:
            y_raw.append(None)
    col_y.data = y_raw

    # Test savgol
    dlg_sg = SmoothDialog(ws, selected_col_idx=1)
    dlg_sg.spn_window.setValue(5)
    dlg_sg.spn_poly.setValue(2)
    dlg_sg._on_accept()

    assert ws.column_count() == 3
    sg_col = ws.columns[2]
    assert len(sg_col.data) == 30
    for i in range(30):
        if i % 2 == 0:
            assert isinstance(sg_col.data[i], float)
        else:
            assert sg_col.data[i] is None
    dlg_sg.close()

    # Test moving average
    dlg_ma = SmoothDialog(ws, selected_col_idx=1)
    dlg_ma.combo_method.setCurrentIndex(1)  # moving_avg
    dlg_ma.spn_window.setValue(3)
    dlg_ma._on_accept()

    assert ws.column_count() == 4
    ma_col = ws.columns[3]
    assert len(ma_col.data) == 30
    for i in range(30):
        if i % 2 == 0:
            assert isinstance(ma_col.data[i], float)
        else:
            assert ma_col.data[i] is None
    dlg_ma.close()


def test_empty_project_dialog_launches(qapp):
    """Test dialog launches when project or workbook has 0 items."""
    empty_proj = Project("TotallyEmpty", workbooks=[])
    graph = GraphModel("G")

    # AddCurveDialog
    d_curve = AddCurveDialog(empty_proj, graph)
    d_curve._populate_columns()
    d_curve._on_accept()
    d_curve.close()

    # FitDialog
    d_fit = FitDialog(empty_proj, graph)
    d_fit._populate_columns()
    assert d_fit._run_fit_calculation() is None
    d_fit.close()

    # PeakAnalysisDialog
    d_peak = PeakAnalysisDialog(empty_proj, graph)
    d_peak._populate_columns()
    assert d_peak._run_peak_search() is None
    d_peak.close()

    # SmoothDialog with empty worksheet
    ws_empty = Worksheet("EmptyWS")
    d_smooth = SmoothDialog(ws_empty, selected_col_idx=-1)
    d_smooth.close()

    # StatsDialog with empty columns list
    d_stats = StatsDialog(ws_empty.columns)
    d_stats.close()


# =========================================================================
# Additional Adversarial Stress Tests
# =========================================================================

def test_sorting_stress_unequal_lengths_and_infinities():
    """Test sorting with unequal column lengths, +/- inf, and all None."""
    ws = Worksheet("UnequalSort")
    col_a = ws.add_column(name="A", role=ColumnRole.X)
    col_b = ws.add_column(name="B", role=ColumnRole.Y)
    col_c = ws.add_column(name="C", role=ColumnRole.Y)

    # Col A has 6 rows with +inf and -inf
    col_a.data = [float("inf"), -10.0, 0.0, float("-inf"), 5.0, None]
    # Col B has 4 rows
    col_b.data = ["b0", "b1", "b2", "b3"]
    # Col C has all None
    col_c.data = [None] * 6

    # Ascending sort by Col A
    ws.sort_by_column(0, ascending=True)
    # Expected numbers in ascending order: -inf, -10.0, 0.0, 5.0, inf, then None
    assert col_a.data[0] == float("-inf")
    assert col_a.data[1] == -10.0
    assert col_a.data[2] == 0.0
    assert col_a.data[3] == 5.0
    assert col_a.data[4] == float("inf")
    assert col_a.data[5] is None

    # Descending sort by Col A
    ws.sort_by_column(0, ascending=False)
    # In reverse: None group comes first, then inf, 5.0, 0.0, -10.0, -inf
    assert col_a.data[0] is None
    assert col_a.data[1] == float("inf")
    assert col_a.data[2] == 5.0
    assert col_a.data[3] == 0.0
    assert col_a.data[4] == -10.0
    assert col_a.data[5] == float("-inf")

    # Sort by Col C (all None) - must not crash
    ws.sort_by_column(2, ascending=True)
    assert len(col_c.data) == 6


def test_formula_chaining_and_complex_roots(qapp):
    """Test formula evaluation with sqrt of negative numbers and chaining with diff, cumsum, norm."""
    ws = Worksheet.create_default(num_rows=4)
    ws.columns[0].data = [1.0, 2.0, 3.0, 4.0]
    col_res = ws.add_column(name="C", role=ColumnRole.Y)

    # 1. sqrt(-4) evaluates np.sqrt(-4.0) -> nan -> converted to None
    ws.apply_formula(2, "sqrt(-4)")
    assert col_res.data[0] is None

    # 2. Formula chaining with diff, cumsum
    ws.columns[0].data = [1.0, 2.0, 3.0, 4.0]
    ws.apply_formula(2, "cumsum(col(A))")
    assert col_res.data == [1.0, 3.0, 6.0, 10.0]

    ws.apply_formula(2, "diff(col(A))")
    assert col_res.data == [0.0, 1.0, 1.0, 1.0]


def test_formula_scalar_complex_vulnerability(qapp):
    """Demonstrates that scalar complex powers like (-4)**0.5 fail with TypeError due to float(scalar)."""
    ws = Worksheet.create_default(num_rows=4)
    ws.add_column(name="C", role=ColumnRole.Y)

    # Evaluating a scalar complex expression calls float() on complex number
    with pytest.raises(TypeError, match="must be a string or a real number, not 'complex'"):
        ws.apply_formula(1, "(-4) ** 0.5")


def test_formula_overflow_vulnerability(qapp):
    """Demonstrates that overflow (e.g. exp(1000)) raises ValueError: '__import__' because np.errstate lacks over='ignore'."""
    ws = Worksheet.create_default(num_rows=4)
    ws.columns[0].data = [1.0, 10.0, 100.0, 1000.0]
    ws.add_column(name="C", role=ColumnRole.Y)

    # Currently raises ValueError: Formula evaluation error: '__import__'
    # because errstate only suppresses 'divide' and 'invalid', not 'over'
    with pytest.raises(ValueError, match="__import__"):
        ws.apply_formula(2, "exp(col(A))")



def test_bar_chart_negative_and_unordered():
    """Test bar and hbar charts with negative duplicate coordinates and unordered values."""
    fig, ax = plt.subplots()
    cm_bar = CurveModel(plot_type="bar")

    # Negative duplicate coordinates
    x_neg = np.array([-10.0, -10.0, -5.0])
    y_neg = np.array([1.0, 2.0, 3.0])
    art_neg = PlotRenderer.render_curve(ax, cm_bar, x_neg, y_neg)
    assert len(art_neg.patches) == 3
    for p in art_neg.patches:
        assert p.get_width() > 0.0

    # Unordered coordinates with duplicate: [3.0, 1.0, 4.0, 1.0, 5.0]
    ax.cla()
    x_unord = np.array([3.0, 1.0, 4.0, 1.0, 5.0])
    y_unord = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
    art_unord = PlotRenderer.render_curve(ax, cm_bar, x_unord, y_unord)
    assert len(art_unord.patches) == 5
    for p in art_unord.patches:
        assert p.get_width() > 0.0

    # Subnormal or near-zero diffs: [1.0, 1.0 + 1e-14, 2.0]
    ax.cla()
    x_sub = np.array([1.0, 1.0 + 1e-14, 2.0])
    y_sub = np.array([1.0, 2.0, 3.0])
    art_sub = PlotRenderer.render_curve(ax, cm_bar, x_sub, y_sub)
    assert len(art_sub.patches) == 3
    # 1e-14 is <= 1e-12, so the positive diff found is 1.0 - 1e-14 ≈ 1.0, width ≈ 0.75
    for p in art_sub.patches:
        assert p.get_width() > 0.0

    plt.close(fig)


def test_legend_editor_empty_and_large_series(qapp):
    """Test Legend Editor with 0 curves and 50 curves."""
    # 0 curves
    graph_empty = GraphModel(title="EmptyGraph")
    dlg_empty = LegendEditorDialog(graph_empty)
    assert dlg_empty.table_series.rowCount() == 0
    dlg_empty._preset_reset_to_columns()
    dlg_empty._apply_changes()
    dlg_empty.close()

    # 50 curves
    graph_large = GraphModel(title="LargeGraph")
    graph_large.curves = [
        CurveModel(source_sheet="S1", label=f"Series_{i}") for i in range(50)
    ]
    dlg_large = LegendEditorDialog(graph_large)
    assert dlg_large.table_series.rowCount() == 50
    dlg_large._preset_reset_to_columns()
    dlg_large._apply_changes()
    assert len(graph_large.curves) == 50
    dlg_large.close()


def test_smoothing_all_modes_and_boundary_points(qapp, monkeypatch):
    """Test all smoothing modes on boundary points (exactly 3 points and < 3 points)."""
    ws = Worksheet("SmoothBoundary")
    col_x = ws.add_column(name="X", role=ColumnRole.X)
    col_y = ws.add_column(name="Y", role=ColumnRole.Y)

    # Exactly 3 points
    col_x.data = [0.0, 1.0, 2.0]
    col_y.data = [10.0, 20.0, 15.0]

    # Test all methods on exactly 3 points
    methods = ["savgol", "moving_avg", "gaussian", "d1", "d2", "integral", "fft"]
    for idx, method in enumerate(methods):
        dlg = SmoothDialog(ws, selected_col_idx=1)
        dlg.combo_method.setCurrentIndex(idx)
        dlg.spn_window.setValue(3)
        dlg.spn_poly.setValue(1)
        dlg._on_accept()
        dlg.close()

    # < 3 points (only 2 points): should show warning and not crash
    from PyQt6.QtWidgets import QMessageBox
    warning_called = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warning_called.append(True))

    ws_two = Worksheet("TwoPoints")
    col_x2 = ws_two.add_column(name="X", role=ColumnRole.X)
    col_y2 = ws_two.add_column(name="Y", role=ColumnRole.Y)
    col_x2.data = [0.0, 1.0]
    col_y2.data = [10.0, 20.0]

    dlg_two = SmoothDialog(ws_two, selected_col_idx=1)
    dlg_two._on_accept()  # Triggers warning and returns safely
    assert len(warning_called) == 1
    assert ws_two.column_count() == 2  # No new column added
    dlg_two.close()
