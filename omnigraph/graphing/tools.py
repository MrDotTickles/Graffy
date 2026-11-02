"""
Interactive canvas tools:
- Origin-style Data Reader Tool (Crosshair inspection)
- Range Selector (ROI SpanSelector for fitting/integration)
- Annotation placement tools
"""

from typing import Optional, Callable, Dict, Any, List, Tuple
import numpy as np
from matplotlib.widgets import SpanSelector
from PyQt6.QtCore import QObject, pyqtSignal


class GraphToolManager(QObject):
    """Manages interactive tools on a Matplotlib figure/canvas."""

    point_inspected = pyqtSignal(str, float, float, int)  # curve_label, x, y, row_idx
    range_selected = pyqtSignal(float, float)  # xmin, xmax
    annotation_added = pyqtSignal(dict)  # annotation dict

    def __init__(self, canvas, ax, ax2=None):
        super().__init__()
        self.canvas = canvas
        self.ax = ax
        self.ax2 = ax2
        self.current_tool = "pointer"  # pointer, data_reader, range_selector, text_annotation, ref_line

        # Internal state
        self._span_selector: Optional[SpanSelector] = None
        self._crosshair_v = None
        self._crosshair_h = None
        self._cursor_text = None
        self._data_curves = []  # list of tuples: (label, x_data, y_data)
        self._cid_motion = None
        self._cid_click = None

        self._init_events()

    def set_data_curves(self, curves: List[Tuple[str, np.ndarray, np.ndarray]]):
        self._data_curves = curves

    def _init_events(self):
        self._cid_motion = self.canvas.mpl_connect("motion_notify_event", self._on_motion)
        self._cid_click = self.canvas.mpl_connect("button_press_event", self._on_click)

    def set_tool(self, tool_name: str):
        """Switch active tool: 'pointer', 'data_reader', 'range_selector', 'annotation'."""
        self.current_tool = tool_name
        self._cleanup_crosshair()

        if self._span_selector is not None:
            self._span_selector.set_active(tool_name == "range_selector")

        if tool_name == "range_selector":
            if self._span_selector is None:
                self._span_selector = SpanSelector(
                    self.ax,
                    self._on_span_select,
                    direction="horizontal",
                    useblit=True,
                    props=dict(alpha=0.25, facecolor="#0284c7"),
                    interactive=True,
                    drag_from_anywhere=True,
                )
            self._span_selector.set_active(True)
        elif tool_name == "data_reader":
            # Set crosshair lines
            self._crosshair_v = self.ax.axvline(x=np.nan, color="#ef4444", linestyle="--", linewidth=1.0, zorder=10)
            self._crosshair_h = self.ax.axhline(y=np.nan, color="#ef4444", linestyle="--", linewidth=1.0, zorder=10)
            self._cursor_text = self.ax.text(
                0.02,
                0.95,
                "",
                transform=self.ax.transAxes,
                bbox=dict(boxstyle="round,pad=0.4", fc="#ffffff", ec="#0284c7", lw=1.2, alpha=0.9),
                fontsize=9,
                fontweight="bold",
                color="#0f172a",
                zorder=11,
            )

        self.canvas.draw_idle()

    def _cleanup_crosshair(self):
        if self._crosshair_v is not None:
            try:
                self._crosshair_v.remove()
            except ValueError:
                pass
            self._crosshair_v = None
        if self._crosshair_h is not None:
            try:
                self._crosshair_h.remove()
            except ValueError:
                pass
            self._crosshair_h = None
        if self._cursor_text is not None:
            try:
                self._cursor_text.remove()
            except ValueError:
                pass
            self._cursor_text = None

    def _on_span_select(self, xmin: float, xmax: float):
        if xmin > xmax:
            xmin, xmax = xmax, xmin
        self.range_selected.emit(float(xmin), float(xmax))

    def _on_motion(self, event):
        if not event.inaxes or self.current_tool != "data_reader":
            return

        x_mouse = event.xdata
        y_mouse = event.ydata
        if x_mouse is None or y_mouse is None:
            return

        # Find nearest point among all registered curves
        best_dist = float("inf")
        best_pt = None

        for item in self._data_curves:
            if hasattr(item, "row_indices"):
                label, xs, ys = item[0], item[1], item[2]
                row_indices = getattr(item, "row_indices", None)
                is_masked = getattr(item, "is_masked", False)
            elif len(item) >= 5:
                label, xs, ys, row_indices, is_masked = item[:5]
            elif len(item) == 4:
                label, xs, ys, row_indices = item
                is_masked = False
            else:
                label, xs, ys = item[:3]
                row_indices, is_masked = None, False

            if len(xs) == 0:
                continue
            dx = xs - x_mouse
            dy = ys - y_mouse
            dist_sq = dx**2 + dy**2
            min_idx = np.argmin(dist_sq)
            d = dist_sq[min_idx]
            if d < best_dist:
                best_dist = d
                actual_row = int(row_indices[min_idx]) if (row_indices is not None and len(row_indices) > min_idx) else int(min_idx)
                best_pt = (label, float(xs[min_idx]), float(ys[min_idx]), actual_row, bool(is_masked))

        if best_pt and self._crosshair_v and self._crosshair_h:
            label, px, py, row_idx, is_m = best_pt
            self._crosshair_v.set_xdata([px, px])
            self._crosshair_h.set_ydata([py, py])
            if self._cursor_text:
                m_tag = " [MASKED]" if is_m else ""
                self._cursor_text.set_text(f"{label}\nX = {px:.5g}\nY = {py:.5g}\nRow: {row_idx + 1}{m_tag}")
            self.canvas.draw_idle()
            self.point_inspected.emit(label, px, py, row_idx)

    def find_nearest_point(self, x_mouse: float, y_mouse: float) -> Optional[Tuple[str, float, float, int, bool]]:
        """Finds nearest (curve_label, x, y, row_idx, is_masked) to given data coordinates."""
        if not self._data_curves or x_mouse is None or y_mouse is None:
            return None

        best_dist = float("inf")
        best_pt = None

        for item in self._data_curves:
            if hasattr(item, "row_indices"):
                label, xs, ys = item[0], item[1], item[2]
                row_indices = getattr(item, "row_indices", None)
                is_masked = getattr(item, "is_masked", False)
            elif len(item) >= 5:
                label, xs, ys, row_indices, is_masked = item[:5]
            elif len(item) == 4:
                label, xs, ys, row_indices = item
                is_masked = False
            else:
                label, xs, ys = item[:3]
                row_indices, is_masked = None, False

            if len(xs) == 0:
                continue
            dx = xs - x_mouse
            dy = ys - y_mouse
            dist_sq = dx**2 + dy**2
            min_idx = np.argmin(dist_sq)
            d = dist_sq[min_idx]
            if d < best_dist:
                best_dist = d
                actual_row = int(row_indices[min_idx]) if (row_indices is not None and len(row_indices) > min_idx) else int(min_idx)
                best_pt = (label, float(xs[min_idx]), float(ys[min_idx]), actual_row, bool(is_masked))

        return best_pt

    def _on_click(self, event):
        if not event.inaxes:
            return
        if self.current_tool == "data_reader":
            self._on_motion(event)
