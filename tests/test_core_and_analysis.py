import numpy as np
import pytest
from omnigraph.core import Worksheet, Column, ColumnRole, Project, FormulaEvaluator
from omnigraph.analysis import CurveFitter, PeakAnalyzer, SignalProcessor, StatisticsAnalyzer


def test_worksheet_and_formula():
    ws = Worksheet.create_default()
    col_a = ws.get_column(0)
    col_b = ws.get_column(1)
    col_a.fill_sequence(0.0, 0.5, 20)
    assert len(col_a.data) == 20

    ws.apply_formula(1, '2.5 * col("A") + 1.2')
    arr_b = col_b.to_numpy_array()
    assert len(arr_b) == 20
    assert np.isclose(arr_b[0], 1.2)
    assert np.isclose(arr_b[1], 2.45)


def test_linear_regression():
    x = np.linspace(1, 10, 20)
    y = 3.5 * x - 2.1 + np.random.normal(0, 0.05, 20)
    res = CurveFitter.linear_fit(x, y)
    assert res.r_squared > 0.99
    assert np.isclose(res.parameters["Slope (m)"], 3.5, atol=0.2)
    assert np.isclose(res.parameters["Intercept (b)"], -2.1, atol=0.5)
    assert res.conf_band_lower is not None
    assert len(res.conf_band_lower) == len(res.x_dense)


def test_polynomial_fit():
    x = np.linspace(-3, 3, 30)
    y = 0.5 * x**2 - 1.2 * x + 4.0
    res = CurveFitter.polynomial_fit(x, y, degree=2)
    assert res.r_squared > 0.999
    assert np.isclose(res.parameters["c_2"], 0.5, atol=0.01)
    assert np.isclose(res.parameters["c_1"], -1.2, atol=0.01)


def test_nonlinear_gaussian():
    x = np.linspace(-10, 10, 100)
    y = 2.0 + 15.0 * np.exp(-0.5 * ((x - 1.5) / 1.8) ** 2)
    res = CurveFitter.nonlinear_fit(x, y, model_type="gaussian")
    assert res.r_squared > 0.99
    assert np.isclose(res.parameters["xc (Center)"], 1.5, atol=0.1)


def test_nonlinear_exponential_decay():
    x = np.linspace(0, 10, 50)
    y = 1.0 + 5.0 * np.exp(-x / 2.5)
    res = CurveFitter.nonlinear_fit(x, y, model_type="exp_decay")
    assert res.r_squared > 0.99
    assert np.isclose(res.parameters["t"], 2.5, atol=0.2)


def test_peak_analysis():
    x = np.linspace(0, 100, 200)
    # 2 peaks
    y = 10.0 * np.exp(-0.5 * ((x - 30) / 3) ** 2) + 20.0 * np.exp(-0.5 * ((x - 70) / 4) ** 2) + 1.0
    res = PeakAnalyzer.analyze_peaks(x, y, baseline_mode="constant")
    assert len(res.peaks) == 2
    assert np.isclose(res.peaks[0].x_center, 30, atol=1.0)
    assert np.isclose(res.peaks[1].x_center, 70, atol=1.0)
    assert res.peaks[1].area > res.peaks[0].area


def test_signal_processing():
    x = np.linspace(0, 10, 100)
    y = np.sin(x)
    smooth = SignalProcessor.moving_average(y, window_size=5)
    assert len(smooth) == 100

    d1 = SignalProcessor.derivative_1st(x, y)
    assert np.isclose(d1[0], np.cos(x[0]), atol=0.05)


def test_project_save_load(tmp_path):
    proj = Project.create_default("TestProject")
    wb = proj.workbooks[0]
    ws = wb.sheets[0]
    ws.columns[0].data = [1.0, 2.0, 3.0]
    ws.columns[1].data = [10.0, 20.0, 30.0]

    save_path = str(tmp_path / "test.kgraph")
    proj.save_to_file(save_path)

    loaded = Project.load_from_file(save_path)
    assert loaded.name == "TestProject"
    assert len(loaded.workbooks) == 1
    loaded_ws = loaded.workbooks[0].sheets[0]
    assert loaded_ws.columns[0].data == [1.0, 2.0, 3.0]
