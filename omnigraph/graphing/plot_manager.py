"""
Graph rendering manager.
Coordinates between GraphModel, Project data sources, themes, and Matplotlib Figure/Axes.
Supports high-resolution exports (PNG, PDF, SVG, TIFF) and clipboard copying.
"""

import io
from typing import Optional, List, Tuple
import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np

from omnigraph.core.project import GraphModel, Project, CurveModel
from omnigraph.graphing.themes import apply_theme_to_axes, get_theme_palette, THEMES
from omnigraph.graphing.plot_types import PlotRenderer


class RenderedCurve(tuple):
    """
    3-tuple (label, xs, ys) for full backwards-compatibility with unpacking:
        label, xs, ys = item
        label, _, _ = item
    while also providing row_indices and is_masked as attributes and extended indexing (item[3], item[4]).
    """
    def __new__(cls, label: str, xs: np.ndarray, ys: np.ndarray, row_indices=None, is_masked: bool = False):
        instance = super().__new__(cls, (label, xs, ys))
        instance.row_indices = row_indices
        instance.is_masked = is_masked
        return instance

    def __getitem__(self, idx):
        if idx == 3:
            return self.row_indices
        if idx == 4:
            return self.is_masked
        return super().__getitem__(idx)


class PlotManager:
    """Renders GraphModel into a Matplotlib Figure."""

    def __init__(self, graph_model: GraphModel, project: Project):
        self.model = graph_model
        self.project = project
        self.fig = Figure(figsize=(6.5, 5.0), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax2: Optional[matplotlib.axes.Axes] = None
        self.rendered_curves: List[Tuple[str, np.ndarray, np.ndarray]] = []

    def recalculate_fits(self):
        """Automatically recalculates all fitted curves on the graph with current unmasked data."""
        from omnigraph.analysis.fitting import CurveFitter
        for curve in self.model.curves:
            if not getattr(curve, "is_fit_curve", False) or not getattr(curve, "fit_model_name", None):
                continue

            src_id = getattr(curve, "fit_source_curve_id", None)
            src_curve = next((c for c in self.model.curves if c.id == src_id), None)
            if not src_curve:
                src_curve = next((c for c in self.model.curves if not getattr(c, "is_fit_curve", False)), None)
            if not src_curve:
                continue

            x_d, y_d, _ = self._get_curve_data(src_curve)
            if len(x_d) < 2:
                continue

            model_code = curve.fit_model_name
            try:
                if model_code == "linear":
                    res = CurveFitter.linear_fit(x_d, y_d)
                elif model_code in ("poly", "poly2", "poly3"):
                    deg = getattr(curve, "fit_degree", 2) or 2
                    res = CurveFitter.polynomial_fit(x_d, y_d, degree=deg)
                elif model_code in ("hill", "dose_response"):
                    res = CurveFitter.nonlinear_fit(x_d, y_d, model="hill")
                elif model_code in ("gaussian", "exp_decay", "exp", "michaelis_menten"):
                    m = "exp_decay" if model_code == "exp" else model_code
                    res = CurveFitter.nonlinear_fit(x_d, y_d, model=m)
                else:
                    res = None

                if res and res.success:
                    curve.fit_formula_str = res.formula_str
                    wb = self.project.get_workbook(curve.source_workbook) or (self.project.workbooks[0] if self.project.workbooks else None)
                    if wb:
                        fit_ws = next((s for s in wb.sheets if s.name == curve.source_sheet), None)
                        if fit_ws and fit_ws.column_count() >= 2:
                            fit_ws.columns[0].data = res.x_dense.tolist()
                            fit_ws.columns[1].data = res.y_dense.tolist()
                            if fit_ws.column_count() >= 4:
                                fit_ws.columns[2].data = res.x_orig.tolist()
                                fit_ws.columns[3].data = res.residuals.tolist()

                    if res.conf_band_lower is not None:
                        for ann in self.model.annotations:
                            if ann.get("type") == "band":
                                ann["x_data"] = res.x_dense.tolist()
                                ann["lower_data"] = res.conf_band_lower.tolist()
                                ann["upper_data"] = res.conf_band_upper.tolist()
            except Exception:
                pass

    def render(self):
        """Draws complete graph according to model."""
        self.fig.clear()
        self.rendered_curves.clear()

        # Recalculate any fitted curves so outliers excluded via masking automatically update fits
        self.recalculate_fits()

        layout_mode = getattr(self.model, "layout_mode", "single")
        is_stacked = layout_mode in ("stacked_2x1", "grid_2x1")
        is_grid_1x2 = layout_mode == "grid_1x2"
        is_grid_2x2 = layout_mode in ("grid_2x2", "figure_1")
        has_secondary = (layout_mode in ("single","twin_x")) and any(c.axis == "secondary" for c in self.model.curves if getattr(c, "visible", True))

        theme = THEMES.get(self.model.theme, THEMES["Origin Classic"])
        lbl_color = theme.get("axes.labelcolor", "#000000")
        self.fig.patch.set_facecolor(theme.get("figure.facecolor", "#ffffff"))

        self.axes: List[matplotlib.axes.Axes] = []

        if is_grid_2x2:
            sync = getattr(self.model, "sync_axes", True)
            self.ax = self.fig.add_subplot(221)
            ax_b = self.fig.add_subplot(222, sharey=self.ax if sync else None)
            ax_c = self.fig.add_subplot(223, sharex=self.ax if sync else None)
            ax_d = self.fig.add_subplot(224, sharex=ax_b if sync else None, sharey=ax_c if sync else None)
            self.axes = [self.ax, ax_b, ax_c, ax_d]
            panel_tags = ["(A)", "(B)", "(C)", "(D)"]
            for i, p_ax in enumerate(self.axes):
                apply_theme_to_axes(
                    p_ax,
                    self.model.theme,
                    box_frame=self.model.box_frame,
                    tick_direction=self.model.tick_direction,
                )
                p_ax.text(
                    -0.08, 1.05,
                    panel_tags[i],
                    transform=p_ax.transAxes,
                    fontsize=12,
                    fontweight="bold",
                    color=lbl_color,
                    va="bottom",
                    zorder=100,
                )
            self.ax2 = None
            self.ax_bottom = ax_c

            # Bottom panels receive X labels
            ax_c.set_xlabel(self.model.x_title, color=lbl_color, fontweight="bold" if "Classic" in self.model.theme else "normal")
            ax_d.set_xlabel(self.model.x_title, color=lbl_color, fontweight="bold" if "Classic" in self.model.theme else "normal")
            # Left panels receive Y labels
            self.ax.set_ylabel(self.model.y_title, color=lbl_color, fontweight="bold" if "Classic" in self.model.theme else "normal")
            ax_c.set_ylabel(self.model.y_title, color=lbl_color, fontweight="bold" if "Classic" in self.model.theme else "normal")
            if not sync:
                self.ax.set_xlabel(self.model.x_title, color=lbl_color, fontweight="bold" if "Classic" in self.model.theme else "normal")
                ax_b.set_xlabel(self.model.x_title, color=lbl_color, fontweight="bold" if "Classic" in self.model.theme else "normal")
                ax_b.set_ylabel(self.model.y_title, color=lbl_color, fontweight="bold" if "Classic" in self.model.theme else "normal")
                ax_d.set_ylabel(self.model.y_title, color=lbl_color, fontweight="bold" if "Classic" in self.model.theme else "normal")

        elif is_grid_1x2:
            sync = getattr(self.model, "sync_axes", True)
            self.ax = self.fig.add_subplot(121)
            ax_right = self.fig.add_subplot(122, sharey=self.ax if sync else None)
            self.axes = [self.ax, ax_right]
            for i, p_ax in enumerate(self.axes):
                apply_theme_to_axes(
                    p_ax,
                    self.model.theme,
                    box_frame=self.model.box_frame,
                    tick_direction=self.model.tick_direction,
                )
                p_ax.text(
                    -0.08, 1.05,
                    ["(A)", "(B)"][i],
                    transform=p_ax.transAxes,
                    fontsize=12,
                    fontweight="bold",
                    color=lbl_color,
                    va="bottom",
                    zorder=100,
                )
            self.ax2 = None
            self.ax_bottom = None
            self.ax.set_xlabel(self.model.x_title, color=lbl_color, fontweight="bold" if "Classic" in self.model.theme else "normal")
            ax_right.set_xlabel(self.model.x_title, color=lbl_color, fontweight="bold" if "Classic" in self.model.theme else "normal")
            self.ax.set_ylabel(self.model.y_title, color=lbl_color, fontweight="bold" if "Classic" in self.model.theme else "normal")
            if not sync:
                ax_right.set_ylabel(self.model.y_title, color=lbl_color, fontweight="bold" if "Classic" in self.model.theme else "normal")

        elif is_stacked:
            self.ax = self.fig.add_subplot(211)
            self.ax_bottom = self.fig.add_subplot(212, sharex=self.ax)
            self.axes = [self.ax, self.ax_bottom]
            for i, p_ax in enumerate(self.axes):
                apply_theme_to_axes(
                    p_ax,
                    self.model.theme,
                    box_frame=self.model.box_frame,
                    tick_direction=self.model.tick_direction,
                )
                p_ax.text(
                    -0.08, 1.05,
                    ["(A)", "(B)"][i],
                    transform=p_ax.transAxes,
                    fontsize=12,
                    fontweight="bold",
                    color=lbl_color,
                    va="bottom",
                    zorder=100,
                )
            self.ax_bottom.set_xlabel(self.model.x_title, color=lbl_color, fontweight="bold" if "Classic" in self.model.theme else "normal")
            self.ax_bottom.set_ylabel(self.model.y_bottom_title or "Bottom Y", color=lbl_color, fontweight="bold" if "Classic" in self.model.theme else "normal")
            self.ax2 = None
        else:
            self.ax = self.fig.add_subplot(111)
            self.ax_bottom = None
            if has_secondary:
                self.ax2 = self.ax.twinx()
            else:
                self.ax2 = None

            apply_theme_to_axes(
                self.ax,
                self.model.theme,
                box_frame=self.model.box_frame,
                tick_direction=self.model.tick_direction,
            )
            if self.ax2:
                self.ax2.spines["right"].set_visible(True)
                self.ax2.tick_params(axis="y", direction=self.model.tick_direction, color=lbl_color, labelcolor=lbl_color)
                self.ax2.spines["right"].set_color(lbl_color)
            self.ax.set_xlabel(self.model.x_title, color=lbl_color, fontweight="bold" if "Classic" in self.model.theme else "normal")
            self.axes = [self.ax]

        # Check waterfall mode
        is_waterfall = getattr(self.model, "waterfall_enabled", False)
        wf_offset_mode = getattr(self.model, "waterfall_offset_mode", "auto")
        wf_y_step = getattr(self.model, "waterfall_y_step", 0.0)
        wf_x_step = getattr(self.model, "waterfall_x_step", 0.0)
        wf_baseline = getattr(self.model, "waterfall_baseline", False)

        # Auto waterfall step if not specified
        if is_waterfall:
            y_spans = []
            for c in self.model.curves:
                if getattr(c, "visible", True):
                    _, y_d, _ = self._get_curve_data(c)
                    if len(y_d) > 1:
                        y_spans.append(float(np.ptp(y_d)))
            base_span = float(np.mean(y_spans)) if y_spans else 1.0

            if wf_offset_mode == "percent":
                wf_y_step = max(base_span * (wf_y_step / 100.0 if wf_y_step > 0 else 0.20), 0.1)
            elif wf_y_step == 0.0 or wf_offset_mode == "auto":
                wf_y_step = max(base_span * 0.35, 0.1)

        # Collect grouped curves for multi-group positioning and X-tick labels
        grouped_curves = [
            c for c in self.model.curves
            if getattr(c, "visible", True)
            and c.plot_type in ("box", "box_whisker", "box_jitter", "violin", "violin_jitter", "jitter", "strip")
        ]
        group_positions = {}
        for g_idx, gc in enumerate(grouped_curves):
            x_raw, _, _ = self._get_curve_data(gc)
            finite_x = x_raw[np.isfinite(x_raw)] if len(x_raw) > 0 else np.array([])
            if len(finite_x) > 0 and len(np.unique(finite_x)) == 1:
                group_positions[gc.id] = float(finite_x[0])
            else:
                group_positions[gc.id] = float(g_idx + 1)

        # Plot curves
        palette = get_theme_palette(self.model.theme)
        visible_idx = 0
        for i, curve in enumerate(self.model.curves):
            # Check visibility
            if not getattr(curve, "visible", True):
                continue

            # Resolve automatic colors without changing the saved series settings.
            render_curve=curve
            if not curve.color or curve.color == "auto":
                from copy import copy
                render_curve=copy(curve)
                render_curve.color=palette[i % len(palette)]

            # Fetch unmasked data from project with original worksheet row indices
            x_data, y_data, y_err_data, valid_indices = self._get_curve_data_with_indices(curve)
            if len(x_data) == 0 or len(y_data) == 0:
                continue

            # Calculate waterfall / curve offsets
            x_off = float(getattr(curve, "x_offset", 0.0))
            y_off = float(getattr(curve, "y_offset", 0.0))
            if is_waterfall:
                y_off += visible_idx * wf_y_step
                x_off += visible_idx * wf_x_step

            x_plot = x_data + x_off if (x_off != 0.0) else x_data
            y_plot = y_data + y_off if (y_off != 0.0) else y_data

            # Determine target axes
            if len(self.axes) > 1:
                layer_target = getattr(curve, "layer_index", 0)
                target_ax = self.axes[layer_target % len(self.axes)]
            elif curve.axis == "secondary" and self.ax2:
                target_ax = self.ax2
            else:
                target_ax = self.ax

            # Baseline leveling indicator
            if is_waterfall and wf_baseline and len(x_plot) > 0:
                target_ax.hlines(
                    y_off,
                    np.min(x_plot),
                    np.max(x_plot),
                    colors="#94a3b8",
                    linestyles=":",
                    linewidths=0.9,
                    alpha=0.6,
                    zorder=2,
                )

            g_pos = group_positions.get(curve.id)
            PlotRenderer.render_curve(target_ax, render_curve, x_plot, y_plot, y_err_data, group_pos=g_pos)
            # Store RenderedCurve (3-tuple unpackable, with row_indices and is_masked)
            self.rendered_curves.append(RenderedCurve(curve.label, x_plot, y_plot, valid_indices, False))

            # Render masked outlier points if any and register them for unmasking
            x_m, y_m, m_indices = self._get_curve_masked_data_with_indices(curve)
            if len(x_m) > 0:
                target_ax.scatter(
                    x_m + x_off,
                    y_m + y_off,
                    marker="x",
                    s=max(curve.marker_size ** 2, 45),
                    color="#ef4444",
                    linewidths=1.8,
                    zorder=6,
                    label="_nolegend_",
                )
                self.rendered_curves.append(RenderedCurve(curve.label, x_m + x_off, y_m + y_off, m_indices, True))

            visible_idx += 1

        # Format grouped categorical X-axis ticks and labels
        if grouped_curves and len(self.axes) == 1:
            pos_list = [group_positions[c.id] for c in grouped_curves]
            lbl_list = [c.label for c in grouped_curves]
            self.ax.set_xticks(pos_list)
            self.ax.set_xticklabels(lbl_list, fontweight="bold" if "Classic" in self.model.theme else "normal")
            if not self.model.x_auto_limits or (self.model.x_min is None and self.model.x_max is None):
                self.ax.set_xlim(min(pos_list) - 0.6, max(pos_list) + 0.6)

        # Annotations (Confidence bands, reference lines, text)
        self._render_annotations()

        # Titles and labels
        self.ax.set_ylabel(self.model.y_title, color=lbl_color, fontweight="bold" if "Classic" in self.model.theme else "normal")
        if self.ax2 and self.model.y2_title:
            self.ax2.set_ylabel(self.model.y2_title, color=lbl_color, fontweight="bold" if "Classic" in self.model.theme else "normal")

        if self.model.title_text:
            self.ax.set_title(self.model.title_text, color=lbl_color, fontweight="bold", pad=10)

        # Quick Top-Left Publication Panel Autograph Label e.g. '(A)', '(B)', 'Fig 1'
        if getattr(self.model, "panel_label", ""):
            self.ax.text(
                -0.08, 1.04,
                self.model.panel_label,
                transform=self.ax.transAxes,
                fontsize=13,
                fontweight="bold",
                va="bottom",
                ha="left",
                color=lbl_color,
                zorder=100,
            )

        # Scales
        if self.model.x_scale == "log10":
            self.ax.set_xscale("log", base=10)
        elif self.model.x_scale == "ln":
            self.ax.set_xscale("log", base=np.e)

        if self.model.y_scale == "log10":
            self.ax.set_yscale("log", base=10)
        elif self.model.y_scale == "ln":
            self.ax.set_yscale("log", base=np.e)

        if self.ax2 and self.model.y2_scale == "log10":
            self.ax2.set_yscale("log", base=10)

        # Limits
        if not self.model.x_auto_limits and self.model.x_min is not None and self.model.x_max is not None:
            self.ax.set_xlim(self.model.x_min, self.model.x_max)

        if not self.model.y_auto_limits and self.model.y_min is not None and self.model.y_max is not None:
            self.ax.set_ylim(self.model.y_min, self.model.y_max)

        if self.ax2 and not self.model.y2_auto_limits and self.model.y2_min is not None and self.model.y2_max is not None:
            self.ax2.set_ylim(self.model.y2_min, self.model.y2_max)

        # Grid lines
        if self.model.show_grid_major:
            self.ax.grid(
                True,
                which="major",
                color=self.model.grid_color,
                linestyle=self.model.grid_style,
                alpha=self.model.grid_alpha,
            )
        else:
            self.ax.grid(False)

        if self.model.show_grid_minor:
            self.ax.grid(
                True,
                which="minor",
                color=self.model.grid_color,
                linestyle=":",
                alpha=self.model.grid_alpha * 0.6,
            )

        # Legend
        if self.model.legend_show and self.model.curves:
            # Gather handles from all axes if present
            handles, labels = self.ax.get_legend_handles_labels()
            if self.ax2:
                h2, l2 = self.ax2.get_legend_handles_labels()
                handles.extend(h2)
                labels.extend(l2)
            if is_stacked and self.ax_bottom:
                hb, lb = self.ax_bottom.get_legend_handles_labels()
                handles.extend(hb)
                labels.extend(lb)

            if handles:
                loc_raw = str(self.model.legend_location or "best").strip().lower()
                bbox_anchor = None
                if loc_raw in ("outside right", "outside_right"):
                    loc_arg = "center left"
                    bbox_anchor = (1.02, 0.5)
                elif loc_raw in ("outside top", "outside_top"):
                    loc_arg = "lower center"
                    bbox_anchor = (0.5, 1.02)
                elif loc_raw not in (
                    "best", "upper right", "upper left", "lower left", "lower right",
                    "right", "center left", "center right", "lower center", "upper center", "center"
                ):
                    loc_arg = "best"
                else:
                    loc_arg = loc_raw

                fs = max(6.0, float(self.model.legend_font_size or 10.0))
                try:
                    if bbox_anchor:
                        self.ax.legend(
                            handles,
                            labels,
                            loc=loc_arg,
                            bbox_to_anchor=bbox_anchor,
                            frameon=bool(self.model.legend_frame),
                            fontsize=fs,
                        )
                    else:
                        self.ax.legend(
                            handles,
                            labels,
                            loc=loc_arg,
                            frameon=bool(self.model.legend_frame),
                            fontsize=fs,
                        )
                except Exception:
                    # Bulletproof fallback in case of backend quirks
                    try:
                        self.ax.legend(handles, labels, loc="best", fontsize=10)
                    except Exception:
                        pass

        legend=self.ax.get_legend()
        if legend is not None:
            from matplotlib.colors import is_color_like
            theme=THEMES.get(self.model.theme,THEMES["Origin Classic"])
            def legend_color(attribute,default):
                value=getattr(self.model,attribute,"auto")
                return value if value not in (None,"auto","") and is_color_like(value) else default
            text_color=legend_color("legend_text_color",theme.get("axes.labelcolor","#202b40"))
            for text in legend.get_texts():
                text.set_color(text_color)
            frame=legend.get_frame()
            frame.set_facecolor(legend_color("legend_face_color",theme.get("legend.facecolor",theme["axes.facecolor"])))
            frame.set_edgecolor(legend_color("legend_edge_color",theme.get("legend.edgecolor",theme["axes.edgecolor"])))
            frame.set_alpha(max(0.0,min(1.0,float(getattr(self.model,"legend_frame_alpha",0.9)))))

        if is_waterfall and not self.model.waterfall_show_y_axis:
            for axis in self.fig.axes:
                axis.yaxis.set_visible(False)
                axis.spines["left"].set_visible(False)
                axis.spines["right"].set_visible(False)
        try:
            self.fig.tight_layout(pad=1.2)
        except Exception:
            pass

    def _get_curve_data_with_indices(self, curve: CurveModel) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray], np.ndarray]:
        """Extracts numeric arrays and valid worksheet row indices for a curve."""
        sheet = self.project.get_worksheet(curve.source_workbook, curve.source_sheet)
        if not sheet:
            return np.array([]), np.array([]), None, np.array([], dtype=int)

        x_col = sheet.get_column(curve.x_col_idx)
        y_col = sheet.get_column(curve.y_col_idx)
        if not x_col or not y_col:
            return np.array([]), np.array([]), None, np.array([], dtype=int)

        x_arr, y_arr, valid_indices = x_col.get_valid_numeric_pairs(y_col)

        # Y Error
        y_err_arr = None
        if curve.y_err_col_idx is not None:
            err_col = sheet.get_column(curve.y_err_col_idx)
            if err_col:
                raw_err = err_col.to_numpy_array(sheet.row_count())
                y_err_arr = raw_err[valid_indices]

        return x_arr, y_arr, y_err_arr, valid_indices

    def _get_curve_data(self, curve: CurveModel) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
        """Extracts numeric arrays for a curve from the Project workbooks."""
        x_arr, y_arr, y_err_arr, _ = self._get_curve_data_with_indices(curve)
        return x_arr, y_arr, y_err_arr

    def _get_curve_masked_data_with_indices(self, curve: CurveModel) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Extracts numeric arrays and row indices for masked points for a curve."""
        sheet = self.project.get_worksheet(curve.source_workbook, curve.source_sheet)
        if not sheet:
            return np.array([]), np.array([]), np.array([], dtype=int)

        x_col = sheet.get_column(curve.x_col_idx)
        y_col = sheet.get_column(curve.y_col_idx)
        if not x_col or not y_col:
            return np.array([]), np.array([]), np.array([], dtype=int)

        x_m, y_m, indices = x_col.get_masked_numeric_pairs(y_col)
        return x_m, y_m, indices

    def _get_curve_masked_data(self, curve: CurveModel) -> Tuple[np.ndarray, np.ndarray]:
        """Extracts numeric arrays for masked points for a curve."""
        x_m, y_m, _ = self._get_curve_masked_data_with_indices(curve)
        return x_m, y_m

    def _render_annotations(self):
        """Draws text annotations, reference lines, confidence bands, and significance brackets."""
        for ann in self.model.annotations:
            atype = ann.get("type")
            if atype == "text":
                x = ann.get("x", 0.5)
                y = ann.get("y", 0.5)
                text = ann.get("text", "")
                color = ann.get("color", "#000000")
                fsize = ann.get("font_size", 10)
                self.ax.text(x, y, text, color=color, fontsize=fsize, zorder=6)

            elif atype == "ref_line":
                val = ann.get("value", 0.0)
                orient = ann.get("orientation", "h")
                color = ann.get("color", "#d62728")
                style = ann.get("style", "--")
                label = ann.get("label", "")
                if orient == "h":
                    self.ax.axhline(val, color=color, linestyle=style, linewidth=1.2, label=label, zorder=2)
                else:
                    self.ax.axvline(val, color=color, linestyle=style, linewidth=1.2, label=label, zorder=2)

            elif atype == "band":
                xs = np.array(ann.get("x_data", []))
                low = np.array(ann.get("lower_data", []))
                high = np.array(ann.get("upper_data", []))
                color = ann.get("color", "#0284c7")
                alpha = ann.get("alpha", 0.2)
                label = ann.get("label", "")
                if len(xs) > 0 and len(low) == len(xs) and len(high) == len(xs):
                    self.ax.fill_between(xs, low, high, color=color, alpha=alpha, label=label, zorder=1)

            elif atype in ("bracket", "significance"):
                x1 = float(ann.get("x1", 1.0))
                x2 = float(ann.get("x2", 2.0))
                y = float(ann.get("y", 1.0))
                h = float(ann.get("h", 0.5))
                text = str(ann.get("text", "***"))
                color = ann.get("color", "#000000")
                lw = float(ann.get("line_width", 1.2))
                fsize = float(ann.get("font_size", 11))

                # Bracket shape: tick down at x1, horizontal bar to x2, tick down at x2
                bx = [x1, x1, x2, x2]
                by = [y - h, y, y, y - h]
                self.ax.plot(bx, by, color=color, linewidth=lw, zorder=10)
                self.ax.text(
                    (x1 + x2) / 2.0,
                    y + abs(h) * 0.15,
                    text,
                    ha="center",
                    va="bottom",
                    color=color,
                    fontsize=fsize,
                    fontweight="bold",
                    zorder=11,
                )

    def export_image(
        self,
        filepath: str,
        dpi: int = 300,
        transparent: bool = False,
        width_in: Optional[float] = None,
        height_in: Optional[float] = None,
        tight_crop: bool = True,
        pad_inches: float = 0.15,
    ):
        """Exports graph to high-res file (PNG, PDF, SVG, TIFF, EPS, JPG) with optional physical dimensions."""
        orig_size = self.fig.get_size_inches()
        orig_dpi = self.fig.dpi
        try:
            if width_in is not None and height_in is not None and width_in > 0 and height_in > 0:
                self.fig.set_size_inches(width_in, height_in, forward=False)
                try:
                    self.fig.tight_layout(pad=1.2)
                except Exception:
                    pass

            kwargs = {
                "dpi": dpi,
                "transparent": transparent,
            }
            if tight_crop:
                kwargs["bbox_inches"] = "tight"
                kwargs["pad_inches"] = pad_inches

            self.fig.savefig(filepath, **kwargs)
        finally:
            self.fig.set_size_inches(*orig_size, forward=False)
            self.fig.set_dpi(orig_dpi)
            try:
                self.fig.tight_layout(pad=1.2)
            except Exception:
                pass

    def export_png_bytes(
        self,
        dpi: int = 300,
        transparent: bool = False,
        width_in: Optional[float] = None,
        height_in: Optional[float] = None,
        tight_crop: bool = True,
        pad_inches: float = 0.15,
    ) -> bytes:
        """Renders figure to raw PNG bytes in memory at specified physical size."""
        buf = io.BytesIO()
        orig_size = self.fig.get_size_inches()
        orig_dpi = self.fig.dpi
        try:
            if width_in is not None and height_in is not None and width_in > 0 and height_in > 0:
                self.fig.set_size_inches(width_in, height_in, forward=False)
                try:
                    self.fig.tight_layout(pad=1.2)
                except Exception:
                    pass

            kwargs = {
                "format": "png",
                "dpi": dpi,
                "transparent": transparent,
            }
            if tight_crop:
                kwargs["bbox_inches"] = "tight"
                kwargs["pad_inches"] = pad_inches

            self.fig.savefig(buf, **kwargs)
            buf.seek(0)
            return buf.getvalue()
        finally:
            self.fig.set_size_inches(*orig_size, forward=False)
            self.fig.set_dpi(orig_dpi)
            try:
                self.fig.tight_layout(pad=1.2)
            except Exception:
                pass

    def export_to_pixmap(
        self,
        dpi: int = 200,
        width_in: Optional[float] = None,
        height_in: Optional[float] = None,
        tight_crop: bool = True,
    ):
        """Returns QPixmap of current figure for preview or clipboard."""
        from PyQt6.QtGui import QImage, QPixmap
        raw = self.export_png_bytes(
            dpi=dpi,
            transparent=False,
            width_in=width_in,
            height_in=height_in,
            tight_crop=tight_crop,
            pad_inches=0.15,
        )
        qimg = QImage()
        qimg.loadFromData(raw)
        return QPixmap.fromImage(qimg)
