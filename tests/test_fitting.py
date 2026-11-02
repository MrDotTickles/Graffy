import pytest
import numpy as np
from omnigraph.analysis.fitting import CurveFitter


def test_linear_regression_fixed_intercept():
    x = np.linspace(1, 10, 15)
    y = 4.2 * x + np.random.normal(0, 0.02, 15)
    res = CurveFitter.linear_fit(x, y, fix_intercept=True, intercept_val=0.0)
    assert np.isclose(res.parameters["Slope (m)"], 4.2, atol=0.1)
    assert res.parameters["Intercept (b)"] == 0.0
    assert res.r_squared > 0.99


def test_dose_response_hill_fit():
    log_c = np.linspace(-9, -4, 11)
    # Bottom 0, Top 100, logEC50 -6.5, HillSlope 1.0
    y_true = 0.0 + 100.0 / (1.0 + 10.0 ** (-6.5 - log_c))
    res = CurveFitter.nonlinear_fit(log_c, y_true, model_type="hill")
    assert res.r_squared > 0.999
    assert np.isclose(res.parameters["logEC50"], -6.5, atol=0.1)
    assert np.isclose(res.parameters["Top"], 100.0, atol=1.0)


def test_michaelis_menten_fit():
    s = np.array([0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0])
    v_true = (60.0 * s) / (12.0 + s)
    res = CurveFitter.nonlinear_fit(s, v_true, model_type="michaelis_menten")
    assert res.r_squared > 0.999
    assert np.isclose(res.parameters["Vmax"], 60.0, atol=1.0)
    assert np.isclose(res.parameters["Km"], 12.0, atol=1.0)
