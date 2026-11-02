"""
Scientific Peak Analysis & Deconvolution Engine.
Finds peaks, computes baselines, FWHM, and peak integration (Area Under Curve).
"""

from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from scipy import signal, integrate


class PeakInfo:
    """Information for a single identified peak."""

    def __init__(
        self,
        index: int,
        peak_id: int,
        x_center: float,
        y_height: float,
        baseline_y: float,
        fwhm: float,
        area: float,
        rel_area_percent: float,
        left_base_x: float,
        right_base_x: float,
    ):
        self.index = index
        self.peak_id = peak_id
        self.x_center = x_center
        self.y_height = y_height
        self.baseline_y = baseline_y
        self.net_height = y_height - baseline_y
        self.fwhm = fwhm
        self.area = area
        self.rel_area_percent = rel_area_percent
        self.left_base_x = left_base_x
        self.right_base_x = right_base_x

    def to_dict(self) -> Dict[str, Any]:
        return {
            "peak_id": self.peak_id,
            "x_center": self.x_center,
            "y_height": self.y_height,
            "net_height": self.net_height,
            "baseline_y": self.baseline_y,
            "fwhm": self.fwhm,
            "area": self.area,
            "rel_area_percent": self.rel_area_percent,
            "left_base_x": self.left_base_x,
            "right_base_x": self.right_base_x,
        }


class PeakAnalysisResult:
    """Complete results from peak detection and integration."""

    def __init__(
        self,
        peaks: List[PeakInfo],
        x: np.ndarray,
        y_raw: np.ndarray,
        baseline: np.ndarray,
        y_corrected: np.ndarray,
        total_area: float,
    ):
        self.peaks = peaks
        self.x = x
        self.y_raw = y_raw
        self.baseline = baseline
        self.y_corrected = y_corrected
        self.total_area = total_area

    def to_html_report(self) -> str:
        """Generates rich HTML peak summary report with guaranteed high contrast."""
        rows = ""
        for i, p in enumerate(self.peaks):
            bg = "#ffffff" if i % 2 == 0 else "#f8fafc"
            rows += f"""
            <tr style="background-color: {bg};">
                <td style="padding: 6px 10px; font-weight: bold; color: #0f172a; border-bottom: 1px solid #e2e8f0;">Peak #{p.peak_id}</td>
                <td style="padding: 6px 10px; font-family: monospace; color: #0f172a; border-bottom: 1px solid #e2e8f0;">{p.x_center:.4f}</td>
                <td style="padding: 6px 10px; font-family: monospace; color: #0f172a; border-bottom: 1px solid #e2e8f0;">{p.net_height:.4f}</td>
                <td style="padding: 6px 10px; font-family: monospace; color: #0f172a; border-bottom: 1px solid #e2e8f0;">{p.fwhm:.4f}</td>
                <td style="padding: 6px 10px; font-family: monospace; color: #0f172a; border-bottom: 1px solid #e2e8f0;">{p.area:.4f}</td>
                <td style="padding: 6px 10px; font-family: monospace; font-weight: bold; color: #0284c7; border-bottom: 1px solid #e2e8f0;">{p.rel_area_percent:.2f}%</td>
            </tr>
            """

        html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #ffffff; color: #0f172a; max-width: 800px; padding: 16px;">
            <div style="background-color: #0f766e; color: #ffffff; padding: 12px 16px; border-radius: 6px 6px 0 0;">
                <h2 style="margin: 0; font-size: 16px; color: #ffffff; font-weight: 700;">Peak Integration Report</h2>
                <div style="font-size: 11px; color: #ccfbf1; margin-top: 4px; font-weight: 500;">
                    Detected {len(self.peaks)} peaks &nbsp;|&nbsp; Total Net Area: <strong>{self.total_area:.4f}</strong>
                </div>
            </div>
            <div style="background-color: #ffffff; border: 1.5px solid #cbd5e1; border-top: none; padding: 12px; border-radius: 0 0 6px 6px;">
                <table style="width: 100%; border-collapse: collapse; font-size: 11px; text-align: left; background-color: #ffffff;">
                    <thead>
                        <tr style="background-color: #f1f5f9; color: #0f172a;">
                            <th style="padding: 8px 10px; color: #0f172a; font-weight: 700; border-bottom: 2px solid #cbd5e1;">Peak ID</th>
                            <th style="padding: 8px 10px; color: #0f172a; font-weight: 700; border-bottom: 2px solid #cbd5e1;">Center (X)</th>
                            <th style="padding: 8px 10px; color: #0f172a; font-weight: 700; border-bottom: 2px solid #cbd5e1;">Height (&Delta;Y)</th>
                            <th style="padding: 8px 10px; color: #0f172a; font-weight: 700; border-bottom: 2px solid #cbd5e1;">FWHM (Width)</th>
                            <th style="padding: 8px 10px; color: #0f172a; font-weight: 700; border-bottom: 2px solid #cbd5e1;">Area</th>
                            <th style="padding: 8px 10px; color: #0f172a; font-weight: 700; border-bottom: 2px solid #cbd5e1;">% Area</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            </div>
        </div>
        """
        return html


class PeakAnalyzer:
    """Algorithms for baseline determination, peak search, and integration."""

    @staticmethod
    def compute_baseline(
        x: np.ndarray,
        y: np.ndarray,
        baseline_mode: str = "linear",  # "none", "constant", "linear", "poly"
        poly_order: int = 2,
    ) -> np.ndarray:
        """Calculates baseline array of same length as y."""
        if baseline_mode == "none":
            return np.zeros_like(y)
        elif baseline_mode == "constant":
            return np.full_like(y, np.min(y))
        elif baseline_mode == "linear":
            # Line connecting ends: (x0, y0) to (x_end, y_end)
            x0, x1 = x[0], x[-1]
            y0, y1 = y[0], y[-1]
            if x1 == x0:
                return np.full_like(y, y0)
            slope = (y1 - y0) / (x1 - x0)
            return y0 + slope * (x - x0)
        elif baseline_mode == "poly":
            coeffs = np.polyfit(x, y, deg=min(poly_order, len(x) - 1))
            return np.polyval(coeffs, x)
        return np.zeros_like(y)

    @staticmethod
    def analyze_peaks(
        x: np.ndarray,
        y: np.ndarray,
        baseline_mode: str = "linear",
        min_prominence_pct: float = 5.0,  # percentage of y peak-to-peak
        min_distance: int = 5,
        poly_order: int = 2,
    ) -> PeakAnalysisResult:
        """
        Detects peaks and calculates peak areas, heights, and FWHM.
        """
        # Sort by x if not already sorted
        sort_idx = np.argsort(x)
        x_sorted = x[sort_idx]
        y_sorted = y[sort_idx]

        # Calculate baseline
        baseline = PeakAnalyzer.compute_baseline(x_sorted, y_sorted, baseline_mode, poly_order)
        y_corr = np.maximum(y_sorted - baseline, 0.0)

        # Determine prominence threshold
        y_range = float(np.ptp(y_corr)) or 1.0
        prominence = (min_prominence_pct / 100.0) * y_range

        # Find peaks on corrected data
        peak_indices, properties = signal.find_peaks(
            y_corr,
            prominence=prominence,
            distance=min_distance,
            width=1,
        )

        widths, width_heights, left_ips, right_ips = signal.peak_widths(y_corr, peak_indices, rel_height=0.5)

        # Compute dx average for width conversion
        dx = np.mean(np.diff(x_sorted)) if len(x_sorted) > 1 else 1.0

        raw_peaks = []
        total_net_area = 0.0

        for i, idx in enumerate(peak_indices):
            xc = float(x_sorted[idx])
            yh = float(y_sorted[idx])
            base_y = float(baseline[idx])
            fwhm = float(widths[i] * dx)

            # Left and right bounds for integration (take width at base or half way to neighbors)
            left_bound = 0 if i == 0 else int((peak_indices[i - 1] + idx) / 2)
            right_bound = len(x_sorted) if i == len(peak_indices) - 1 else int((peak_indices[i + 1] + idx) / 2)

            sub_x = x_sorted[left_bound:right_bound]
            sub_y = y_corr[left_bound:right_bound]
            if len(sub_x) >= 2:
                peak_area = float(integrate.trapezoid(sub_y, sub_x))
            else:
                peak_area = float(sub_y[0] * dx) if len(sub_y) > 0 else 0.0

            total_net_area += peak_area

            raw_peaks.append({
                "index": int(idx),
                "peak_id": i + 1,
                "x_center": xc,
                "y_height": yh,
                "baseline_y": base_y,
                "fwhm": fwhm,
                "area": peak_area,
                "left_base_x": float(x_sorted[left_bound]),
                "right_base_x": float(x_sorted[min(right_bound, len(x_sorted) - 1)]),
            })

        # Calculate relative area %
        peaks = []
        for rp in raw_peaks:
            rel_pct = (rp["area"] / total_net_area * 100.0) if total_net_area > 0 else 0.0
            peaks.append(
                PeakInfo(
                    index=rp["index"],
                    peak_id=rp["peak_id"],
                    x_center=rp["x_center"],
                    y_height=rp["y_height"],
                    baseline_y=rp["baseline_y"],
                    fwhm=rp["fwhm"],
                    area=rp["area"],
                    rel_area_percent=rel_pct,
                    left_base_x=rp["left_base_x"],
                    right_base_x=rp["right_base_x"],
                )
            )

        return PeakAnalysisResult(
            peaks=peaks,
            x=x_sorted,
            y_raw=y_sorted,
            baseline=baseline,
            y_corrected=y_corr,
            total_area=total_net_area,
        )
