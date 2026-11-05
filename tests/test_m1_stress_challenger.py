"""
Empirical stress-testing harness by teamwork_challenger_m1_2.
Focus areas:
1. Signal smoothing on columns with leading, trailing, and intermittent None values.
   Verify length preservation and row alignment against raw inputs.
2. Curve fitting and export round-trip after applying fixes.
3. Test dialog instantiation on edge-case project configurations (0 workbooks, 0 sheets, 0 columns, corrupted curves).
"""

import os
import sys
import pytest
import numpy as np

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from omnigraph.core.worksheet import Workbook, Worksheet, Column, ColumnRole
from omnigraph.core.project import Project, GraphModel, CurveModel
from omnigraph.analysis.smoothing import SignalProcessor
from omnigraph.analysis.fitting import CurveFitter
from omnigraph.graphing.plot_manager import PlotManager
from omnigraph.ui.dialogs.smooth_dialog import SmoothDialog
from omnigraph.ui.dialogs.fit_dialog import FitDialog
from omnigraph.ui.dialogs.add_curve_dialog import AddCurveDialog
from omnigraph.ui.dialogs.peak_dialog import PeakAnalysisDialog
from omnigraph.ui.dialogs.stats_dialog import StatsDialog
from omnigraph.ui.dialogs.legend_dialog import LegendEditorDialog
from omnigraph.ui.dialogs.quick_labels_dialog import QuickLabelsDialog
from omnigraph.ui.dialogs.formula_dialog import FormulaDialog
from omnigraph.ui.dialogs.column_prop_dialog import ColumnPropertiesDialog
from omnigraph.ui.dialogs.export_dialog import ExportDialog
from omnigraph.ui.dialogs.import_dialog import ImportDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture(autouse=True)
def mock_messagebox(monkeypatch):
    from PyQt6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)


# =========================================================================
# TEST SUITE 1: Signal Smoothing with Leading, Trailing, Intermittent Nones
# =========================================================================

@pytest.mark.parametrize("method_code", ["savgol", "moving_avg", "gaussian", "d1", "d2", "integral"])
def test_smoothing_none_patterns_new_column(qapp, method_code):
    """
    Stress-test signal transformations with:
    - 3 leading Nones
    - 2 intermittent Nones
    - 3 trailing Nones
    Verify exact length preservation and alignment in 'New Column' mode.
    """
    ws = Worksheet.create_default(num_rows=16)
    ws.columns[0].fill_sequence(0.0, 1.0, 16)
    # Y data: 16 rows total. Valid points at indices [3, 4, 5, 8, 9, 10, 11, 12] (8 points)
    raw_y = [
        None, None, None,          # 0, 1, 2: leading Nones
        10.0, 20.0, 30.0,          # 3, 4, 5: valid
        None, None,                # 6, 7: intermittent Nones
        40.0, 50.0, 60.0, 70.0, 80.0, # 8, 9, 10, 11, 12: valid
        None, None, None           # 13, 14, 15: trailing Nones
    ]
    ws.columns[1].data = list(raw_y)

    dlg = SmoothDialog(ws, selected_col_idx=1)
    idx = dlg.combo_method.findData(method_code)
    assert idx >= 0
    dlg.combo_method.setCurrentIndex(idx)
    dlg.spn_window.setValue(3)
    dlg.spn_poly.setValue(1)
    dlg.radio_new_col.setChecked(True)
    dlg._on_accept()

    # Verify new column was created
    assert ws.column_count() == 3
    new_col = ws.columns[2]

    # 1. Total length must be strictly preserved
    assert len(new_col.data) == 16, f"Expected length 16 for {method_code}, got {len(new_col.data)}"

    # 2. None positions must exactly match raw_y None positions
    none_indices = [0, 1, 2, 6, 7, 13, 14, 15]
    valid_indices = [3, 4, 5, 8, 9, 10, 11, 12]

    for ni in none_indices:
        assert new_col.data[ni] is None, f"Method {method_code}: index {ni} should be None, got {new_col.data[ni]}"

    for vi in valid_indices:
        val = new_col.data[vi]
        assert val is not None, f"Method {method_code}: index {vi} should have numeric value, got None"
        assert isinstance(val, float), f"Method {method_code}: index {vi} should be float, got {type(val)}"
        assert not np.isnan(val), f"Method {method_code}: index {vi} value is NaN"
        assert not np.isinf(val), f"Method {method_code}: index {vi} value is Inf"

    dlg.close()


@pytest.mark.parametrize("method_code", ["savgol", "moving_avg", "gaussian", "d1", "d2", "integral"])
def test_smoothing_none_patterns_replace_mode(qapp, method_code):
    """
    Stress-test signal transformations in 'Replace Existing Column Data' mode.
    Verify exact length preservation and alignment.
    """
    ws = Worksheet.create_default(num_rows=14)
    ws.columns[0].fill_sequence(1.0, 1.0, 14)
    raw_y = [
        None, None,                # 0, 1: leading
        5.0, 10.0, 15.0, 20.0,     # 2, 3, 4, 5: valid
        None,                      # 6: intermittent
        25.0, 30.0, 35.0, 40.0,    # 7, 8, 9, 10: valid
        None, None, None           # 11, 12, 13: trailing
    ]
    ws.columns[1].data = list(raw_y)

    dlg = SmoothDialog(ws, selected_col_idx=1)
    idx = dlg.combo_method.findData(method_code)
    dlg.combo_method.setCurrentIndex(idx)
    dlg.spn_window.setValue(3)
    dlg.spn_poly.setValue(1)
    dlg.radio_replace.setChecked(True)
    dlg._on_accept()

    assert ws.column_count() == 2
    col_y = ws.columns[1]

    assert len(col_y.data) == 14
    none_indices = [0, 1, 6, 11, 12, 13]
    valid_indices = [2, 3, 4, 5, 7, 8, 9, 10]

    for ni in none_indices:
        assert col_y.data[ni] is None, f"Replace {method_code}: index {ni} should be None"

    for vi in valid_indices:
        val = col_y.data[vi]
        assert val is not None, f"Replace {method_code}: index {vi} should not be None"
        assert isinstance(val, float)
        assert not np.isnan(val)

    dlg.close()


def test_smoothing_with_x_and_y_staggered_nones(qapp):
    """
    Stress-test where X and Y have MISSING values at DIFFERENT positions.
    X has Nones at [0, 4]
    Y has Nones at [2, 7]
    Valid numeric pair rows should be all rows except [0, 2, 4, 7].
    Row length and alignment must remain completely intact.
    """
    ws = Worksheet("Staggered")
    col_x = Column("A", role=ColumnRole.X, data=[None, 1.0, 2.0, 3.0, None, 5.0, 6.0, 7.0, 8.0])
    col_y = Column("B", role=ColumnRole.Y, data=[10.0, 20.0, None, 40.0, 50.0, 60.0, 70.0, None, 90.0])
    ws.columns = [col_x, col_y]

    dlg = SmoothDialog(ws, selected_col_idx=1)
    dlg.combo_method.setCurrentIndex(dlg.combo_method.findData("moving_avg"))
    dlg.spn_window.setValue(3)
    dlg.radio_new_col.setChecked(True)
    dlg._on_accept()

    assert ws.column_count() == 3
    new_col = ws.columns[2]
    assert len(new_col.data) == 9

    # Rows with missing in either X or Y: 0 (X is None), 2 (Y is None), 4 (X is None), 7 (Y is None)
    invalid_rows = [0, 2, 4, 7]
    valid_rows = [1, 3, 5, 6, 8]

    for r in invalid_rows:
        assert new_col.data[r] is None, f"Row {r} should be None in new smoothed column"

    for r in valid_rows:
        assert isinstance(new_col.data[r], float), f"Row {r} should have smoothed float value"

    dlg.close()


def test_smoothing_fft_transformation(qapp):
    """Test FFT spectrum generation adds Frequency (X) and FFT Power (Y) columns."""
    ws = Worksheet.create_default(num_rows=20)
    t = np.linspace(0, 0.2, 20)
    sig = np.sin(2 * np.pi * 10 * t)
    ws.columns[0].data = t.tolist()
    ws.columns[1].data = sig.tolist()

    dlg = SmoothDialog(ws, selected_col_idx=1)
    dlg.combo_method.setCurrentIndex(dlg.combo_method.findData("fft"))
    dlg._on_accept()

    # FFT adds col_f (X) and col_p (Y)
    assert ws.column_count() == 4
    col_f = ws.columns[2]
    col_p = ws.columns[3]

    assert col_f.role == ColumnRole.X
    assert col_p.role == ColumnRole.Y
    assert len(col_f.data) == 11
    assert len(col_p.data) == 11
    assert all(isinstance(v, float) for v in col_f.data)
    assert all(isinstance(v, float) for v in col_p.data)
    dlg.close()


# =========================================================================
# TEST SUITE 2: Curve Fitting & Export Round-Trip
# =========================================================================

def test_curve_fitting_all_models_and_report_generation():
    """Verify all fitting models converge and produce valid FitResult and HTML reports."""
    x = np.linspace(1.0, 10.0, 25)

    # 1. Linear
    y_lin = 2.5 * x + 4.0 + np.random.normal(0, 0.05, len(x))
    res_lin = CurveFitter.linear_fit(x, y_lin)
    assert res_lin.success
    assert res_lin.r_squared > 0.95
    assert len(res_lin.parameters) >= 2
    assert len(res_lin.to_html_report()) > 100

    # 2. Polynomial 2
    y_p2 = 0.5 * x**2 - 2 * x + 3 + np.random.normal(0, 0.05, len(x))
    res_p2 = CurveFitter.polynomial_fit(x, y_p2, degree=2)
    assert res_p2.success
    assert res_p2.r_squared > 0.95

    # 3. Polynomial 3
    y_p3 = 0.1 * x**3 - 0.5 * x**2 + x + np.random.normal(0, 0.05, len(x))
    res_p3 = CurveFitter.polynomial_fit(x, y_p3, degree=3)
    assert res_p3.success
    assert res_p3.r_squared > 0.95

    # 4. Exponential Decay
    y_exp = 5.0 * np.exp(-0.4 * x) + 1.0 + np.random.normal(0, 0.02, len(x))
    res_exp = CurveFitter.nonlinear_fit(x, y_exp, model_type="exp_decay")
    assert res_exp.success
    assert res_exp.r_squared > 0.90

    # 5. Gaussian Peak
    y_gauss = 10.0 * np.exp(-((x - 5.0) ** 2) / (2 * 1.2**2)) + 0.5
    res_gauss = CurveFitter.nonlinear_fit(x, y_gauss, model_type="gaussian")
    assert res_gauss.success
    assert res_gauss.r_squared > 0.95


def test_fit_dialog_export_and_project_roundtrip(qapp, tmp_path):
    """
    Stress-test full workflow:
    1. Create Project with data
    2. Open FitDialog, run Linear fit, accept with export sheet & graph overlay
    3. Verify new fit worksheet and fit curve on graph
    4. Save project to JSON .kgraph
    5. Load project from file
    6. Verify fit sheet and graph curves exist in loaded project
    7. Export graph to PNG, PDF, SVG, TIFF and verify files are generated without error
    """
    proj = Project.create_default("FitRoundTripProject")
    ws = proj.workbooks[0].sheets[0]
    x_data = [float(i) for i in range(1, 15)]
    y_data = [2.0 * x + 1.0 for x in x_data]
    ws.columns[0].data = x_data
    ws.columns[1].data = y_data

    graph = GraphModel(title="LinearFitGraph")
    data_curve = CurveModel(
        source_workbook="Book1",
        source_sheet="Sheet1",
        x_col_idx=0,
        y_col_idx=1,
        label="Raw Data",
        plot_type="scatter",
    )
    graph.add_curve(data_curve)
    proj.graphs.append(graph)

    # Instantiate FitDialog and run fit
    dlg = FitDialog(proj, active_graph=graph)
    dlg.combo_model.setCurrentIndex(dlg.combo_model.findData("linear"))
    dlg.chk_export_sheet.setChecked(True)
    dlg.chk_overlay_graph.setChecked(True)
    dlg._run_fit_calculation()
    dlg._on_accept()
    dlg.close()

    # Verify fit sheet was created
    wb = proj.workbooks[0]
    assert len(wb.sheets) == 2
    fit_sheet = wb.sheets[1]
    assert fit_sheet.name.startswith("Fit_")
    assert fit_sheet.column_count() == 4  # Fitted X, Fitted Y, Orig X, Residuals

    # Verify fit curve was overlaid on graph
    assert len(graph.curves) >= 2
    fit_curve = graph.curves[1]
    assert fit_curve.is_fit_curve is True
    assert "Fit" in fit_curve.label

    # Save project to file (tests JSON serialization with NumPy types)
    kgraph_path = str(tmp_path / "fitted_project.kgraph")
    proj.save_project(kgraph_path)
    assert os.path.exists(kgraph_path)
    assert os.path.getsize(kgraph_path) > 500

    # Load project back
    loaded_proj = Project.load_from_file(kgraph_path)
    assert len(loaded_proj.workbooks) == 1
    assert len(loaded_proj.workbooks[0].sheets) == 2
    assert len(loaded_proj.graphs) == 1

    loaded_graph = loaded_proj.graphs[0]
    assert len(loaded_graph.curves) >= 2
    assert loaded_graph.curves[1].is_fit_curve is True

    # Render loaded graph via PlotManager
    pm = PlotManager(loaded_graph, loaded_proj)
    pm.render()
    assert len(pm.rendered_curves) >= 2

    # Export to all supported formats
    png_path = str(tmp_path / "export.png")
    pdf_path = str(tmp_path / "export.pdf")
    svg_path = str(tmp_path / "export.svg")
    tiff_path = str(tmp_path / "export.tiff")

    pm.export_image(png_path, dpi=150)
    pm.export_image(pdf_path)
    pm.export_image(svg_path)
    pm.export_image(tiff_path, dpi=150)

    assert os.path.exists(png_path) and os.path.getsize(png_path) > 1000
    assert os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000
    assert os.path.exists(svg_path) and os.path.getsize(svg_path) > 1000
    assert os.path.exists(tiff_path) and os.path.getsize(tiff_path) > 1000

    # Also test pixmap and png bytes export
    pixmap = pm.export_to_pixmap(dpi=100)
    assert not pixmap.isNull()
    assert pixmap.width() > 100 and pixmap.height() > 100

    png_bytes = pm.export_png_bytes(dpi=100)
    assert len(png_bytes) > 500


# =========================================================================
# TEST SUITE 3: Dialog Instantiation on Edge-Case Project Configurations
# =========================================================================

def test_dialogs_with_zero_workbooks(qapp):
    """Instantiate and exercise dialogs when Project has 0 workbooks."""
    p_zero_wb = Project(name="ZeroWB", workbooks=[])
    graph = GraphModel(title="EmptyGraph")

    # AddCurveDialog
    dlg1 = AddCurveDialog(p_zero_wb, graph)
    assert dlg1.combo_sheet.count() == 0
    dlg1._on_accept()
    dlg1.close()

    # FitDialog
    dlg2 = FitDialog(p_zero_wb, active_graph=graph)
    assert dlg2.combo_sheet.count() == 0
    assert dlg2._run_fit_calculation() is None
    dlg2._on_accept()
    dlg2.close()

    # PeakAnalysisDialog
    dlg3 = PeakAnalysisDialog(p_zero_wb, active_graph=graph)
    assert dlg3.combo_sheet.count() == 0
    assert dlg3._run_peak_search() is None
    dlg3._on_accept()
    dlg3.close()


def test_dialogs_with_zero_sheets(qapp):
    """Instantiate and exercise dialogs when Project has a workbook with 0 sheets."""
    empty_wb = Workbook(name="EmptyBook")
    empty_wb.sheets = []
    p_zero_sheets = Project(name="ZeroSheets", workbooks=[empty_wb])
    graph = GraphModel(title="EmptyGraph")

    dlg1 = AddCurveDialog(p_zero_sheets, graph)
    assert dlg1.combo_sheet.count() == 0
    dlg1._on_accept()
    dlg1.close()

    dlg2 = FitDialog(p_zero_sheets, active_graph=graph)
    assert dlg2.combo_sheet.count() == 0
    assert dlg2._run_fit_calculation() is None
    dlg2._on_accept()
    dlg2.close()

    dlg3 = PeakAnalysisDialog(p_zero_sheets, active_graph=graph)
    assert dlg3.combo_sheet.count() == 0
    assert dlg3._run_peak_search() is None
    dlg3._on_accept()
    dlg3.close()


def test_dialogs_with_zero_columns(qapp):
    """Instantiate and exercise dialogs when Worksheet has 0 columns."""
    empty_ws = Worksheet(name="ZeroColSheet")
    empty_ws.columns = []
    wb = Workbook(name="Book1")
    wb.sheets = [empty_ws]
    p_zero_cols = Project(name="ZeroCols", workbooks=[wb])
    graph = GraphModel(title="EmptyGraph")

    # AddCurveDialog
    dlg1 = AddCurveDialog(p_zero_cols, graph)
    assert dlg1.combo_x_col.count() == 0
    dlg1._on_accept()
    dlg1.close()

    # FitDialog
    dlg2 = FitDialog(p_zero_cols, active_graph=graph)
    assert dlg2.combo_x_col.count() == 0
    assert dlg2._run_fit_calculation() is None
    dlg2._on_accept()
    dlg2.close()

    # PeakAnalysisDialog
    dlg3 = PeakAnalysisDialog(p_zero_cols, active_graph=graph)
    assert dlg3.combo_x_col.count() == 0
    assert dlg3._run_peak_search() is None
    dlg3._on_accept()
    dlg3.close()

    # StatsDialog
    dlg5 = StatsDialog([])
    assert dlg5.table_stats.rowCount() == 0
    dlg5._run_ttest()
    dlg5.close()

    # FormulaDialog
    dlg6 = FormulaDialog(empty_ws)
    assert dlg6.combo_target.count() == 0
    dlg6._on_accept()
    dlg6.close()


def test_smooth_dialog_crashes_on_zero_columns_reproduction(qapp):
    """
    Verified remediation:
    SmoothDialog._on_accept() handles col_idx=None when worksheet has 0 columns,
    returning cleanly without raising TypeError.
    """
    empty_ws = Worksheet(name="ZeroColSheet")
    empty_ws.columns = []
    dlg = SmoothDialog(empty_ws)
    assert dlg.combo_col.count() == 0
    dlg._on_accept()
    dlg.close()


def test_dialogs_and_plot_manager_with_corrupted_curves(qapp):
    """
    Stress-test with malformed / corrupted curves:
    - Non-existent workbook
    - Non-existent sheet
    - Out of bounds column index
    - Empty labels, missing colors
    """
    proj = Project.create_default("CorruptedCurvesTest")
    graph = GraphModel(title="CorruptGraph")

    bad_curve1 = CurveModel(
        source_workbook="GhostBook",
        source_sheet="GhostSheet",
        x_col_idx=999,
        y_col_idx=1000,
        label="",
        color="",
    )
    bad_curve2 = CurveModel(
        source_workbook="",
        source_sheet="",
        x_col_idx=-5,
        y_col_idx=-1,
        label=None,
        color="invalid_color_string",
    )
    graph.curves = [bad_curve1, bad_curve2]
    proj.graphs.append(graph)

    # 1. LegendEditorDialog
    dlg_legend = LegendEditorDialog(graph)
    dlg_legend._preset_number_series()
    dlg_legend._preset_reset_to_columns()
    dlg_legend._apply_changes()
    dlg_legend.close()

    # 2. QuickLabelsDialog
    dlg_labels = QuickLabelsDialog(graph)
    dlg_labels._on_accept()
    dlg_labels.close()

    # 3. PlotManager render & export
    pm = PlotManager(graph, proj)
    # Must render without unhandled exception
    pm.render()
    assert len(pm.rendered_curves) == 0  # No valid data rendered

    # Export Dialog
    dlg_export = ExportDialog(pm)
    dlg_export._update_preview()
    dlg_export.close()
