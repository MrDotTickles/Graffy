import pytest
import numpy as np
from omnigraph.analysis.peak_analysis import PeakAnalyzer


def test_three_peak_deconvolution():
    x = np.linspace(200, 800, 301)
    # 3 peaks with linear baseline
    base = 0.1 + 0.0005 * x
    p1 = 5.0 * np.exp(-0.5 * ((x - 350) / 15) ** 2)
    p2 = 12.0 * np.exp(-0.5 * ((x - 500) / 20) ** 2)
    p3 = 8.0 * np.exp(-0.5 * ((x - 680) / 18) ** 2)
    y = base + p1 + p2 + p3

    res = PeakAnalyzer.analyze_peaks(x, y, baseline_mode="linear", min_prominence_pct=5.0)
    assert len(res.peaks) == 3
    assert np.isclose(res.peaks[0].x_center, 350, atol=2.0)
    assert np.isclose(res.peaks[1].x_center, 500, atol=2.0)
    assert np.isclose(res.peaks[2].x_center, 680, atol=2.0)

    # Area ordering: peak 2 should have largest area
    areas = [p.area for p in res.peaks]
    assert areas[1] > areas[2] > areas[0]
