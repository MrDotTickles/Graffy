"""
Renderers for all scientific plot types:
Scatter, Line, Line+Symbol, Step, Spline, Bar, H-Bar, Area, Errorbar, Histogram, Box, Violin.
"""

from typing import List, Optional, Tuple, Any
import numpy as np
from scipy import interpolate


class PlotRenderer:
    """Renders scientific curves on Matplotlib Axes."""

    @staticmethod
    def render_curve(
        ax,
        curve_model,
        x: np.ndarray,
        y: np.ndarray,
        y_err: Optional[np.ndarray] = None,
        group_pos: Optional[float] = None,
    ) -> Any:
        """Renders a single curve according to its plot_type and styling options."""
        pt = curve_model.plot_type
        color = curve_model.color
        lw = curve_model.line_width
        ls = curve_model.line_style
        alpha = curve_model.alpha
        label = curve_model.label

        # Marker styling
        marker = curve_model.marker if curve_model.marker != "none" else ""
        ms = curve_model.marker_size
        mfc = color if curve_model.marker_face_color == "auto" else curve_model.marker_face_color
        mec = color if curve_model.marker_edge_color == "auto" else curve_model.marker_edge_color
        mew = curve_model.marker_edge_width

        if pt == "scatter":
            m = marker if marker else "o"
            fc = mfc if mfc != "none" else "none"
            ec = mec if mec != "none" else color
            artist = ax.scatter(
                x,
                y,
                s=(ms ** 2),
                marker=m,
                facecolors=fc,
                edgecolors=ec,
                linewidths=mew,
                alpha=alpha,
                label=label,
                zorder=4,
            )
            return artist

        elif pt == "line":
            style = ls if ls != "none" else "-"
            artist = ax.plot(
                x,
                y,
                linestyle=style,
                linewidth=lw,
                color=color,
                alpha=alpha,
                label=label,
                zorder=3,
            )
            return artist[0]

        elif pt == "line_symbol":
            style = ls if ls != "none" else "-"
            m = marker if marker else "o"
            fc = mfc if mfc != "none" else "none"
            ec = mec if mec != "none" else color
            artist = ax.plot(
                x,
                y,
                linestyle=style,
                linewidth=lw,
                color=color,
                marker=m,
                markersize=ms,
                markerfacecolor=fc,
                markeredgecolor=ec,
                markeredgewidth=mew,
                alpha=alpha,
                label=label,
                zorder=3,
            )
            return artist[0]

        elif pt == "step":
            artist = ax.step(
                x,
                y,
                where="mid",
                linewidth=lw,
                color=color,
                alpha=alpha,
                label=label,
                zorder=3,
            )
            return artist[0]

        elif pt == "spline":
            if len(x) >= 4:
                # Sort points by x for interpolation
                sort_idx = np.argsort(x)
                xs, ys = x[sort_idx], y[sort_idx]
                # Unique x values to prevent spline crash
                xs_uniq, uniq_idx = np.unique(xs, return_index=True)
                ys_uniq = ys[uniq_idx]
                if len(xs_uniq) >= 4:
                    spl = interpolate.CubicSpline(xs_uniq, ys_uniq)
                    x_dense = np.linspace(xs_uniq[0], xs_uniq[-1], 300)
                    y_dense = spl(x_dense)
                    artist = ax.plot(
                        x_dense,
                        y_dense,
                        linestyle=ls if ls != "none" else "-",
                        linewidth=lw,
                        color=color,
                        alpha=alpha,
                        label=label,
                        zorder=3,
                    )
                    # Also plot symbols at actual data points if requested
                    if marker and marker != "none":
                        ax.scatter(x, y, s=(ms**2), marker=marker, facecolors=mfc, edgecolors=mec, alpha=alpha, zorder=4)
                    return artist[0]
            # Fallback to line
            artist = ax.plot(x, y, linestyle="-", linewidth=lw, color=color, alpha=alpha, label=label)
            return artist[0]

        elif pt == "bar":
            # Bar width estimation based on positive x spacing
            x_arr = np.asarray(x, dtype=float)
            x_valid = x_arr[np.isfinite(x_arr)] if len(x_arr) > 0 else x_arr
            diffs = np.diff(np.sort(x_valid)) if len(x_valid) > 1 else np.array([])
            pos_diffs = diffs[diffs > 1e-12]
            dx = float(np.min(pos_diffs)) if len(pos_diffs) > 0 else 1.0
            width = dx * 0.75 if dx > 0 else 0.75
            artist = ax.bar(
                x,
                y,
                width=width,
                color=color,
                edgecolor=mec if mec != "none" else "#000000",
                linewidth=mew,
                alpha=alpha,
                label=label,
                zorder=2,
            )
            return artist

        elif pt == "hbar":
            y_arr = np.asarray(y, dtype=float)
            y_valid = y_arr[np.isfinite(y_arr)] if len(y_arr) > 0 else y_arr
            diffs = np.diff(np.sort(y_valid)) if len(y_valid) > 1 else np.array([])
            pos_diffs = diffs[diffs > 1e-12]
            dy = float(np.min(pos_diffs)) if len(pos_diffs) > 0 else 1.0
            height = dy * 0.75 if dy > 0 else 0.75
            artist = ax.barh(
                y,
                x,
                height=height,
                color=color,
                edgecolor=mec if mec != "none" else "#000000",
                linewidth=mew,
                alpha=alpha,
                label=label,
                zorder=2,
            )
            return artist

        elif pt == "area":
            artist = ax.fill_between(
                x,
                y,
                0,
                color=color,
                alpha=alpha * 0.5,
                label=label,
                zorder=2,
            )
            ax.plot(x, y, color=color, linewidth=lw, alpha=alpha, zorder=3)
            return artist

        elif pt == "errorbar" or (y_err is not None and len(y_err) == len(y)):
            err = y_err if y_err is not None else np.zeros_like(y)
            artist = ax.errorbar(
                x,
                y,
                yerr=err,
                fmt=marker if marker else "o",
                color=color,
                ecolor=color,
                elinewidth=lw,
                capsize=3.5,
                capthick=1.0,
                markersize=ms,
                markerfacecolor=mfc if mfc != "none" else "none",
                markeredgecolor=mec,
                markeredgewidth=mew,
                alpha=alpha,
                label=label,
                zorder=4,
            )
            return artist

        elif pt == "histogram":
            bins = min(max(int(np.sqrt(len(y))), 5), 50)
            n_vals, bins_out, patches = ax.hist(
                y,
                bins=bins,
                color=color,
                edgecolor="#000000",
                linewidth=0.8,
                alpha=alpha * 0.75,
                label=label,
                density=False,
                zorder=2,
            )
            return patches

        elif pt in ("box", "box_whisker", "box_jitter", "jitter", "strip"):
            y_arr = np.asarray(y, dtype=float)
            y_clean = y_arr[np.isfinite(y_arr)]
            if len(y_clean) == 0:
                return None

            # Determine position
            if group_pos is not None:
                pos = float(group_pos)
            else:
                x_arr = np.asarray(x, dtype=float)
                x_valid = x_arr[np.isfinite(x_arr)]
                if len(x_valid) > 0 and len(np.unique(x_valid)) == 1:
                    pos = float(x_valid[0])
                else:
                    l_idx = getattr(curve_model, "layer_index", 0)
                    pos = float(l_idx + 1) if l_idx is not None else 1.0

            artists = []
            if pt in ("box", "box_whisker", "box_jitter"):
                bp = ax.boxplot(
                    [y_clean],
                    positions=[pos],
                    widths=0.45,
                    patch_artist=True,
                    boxprops=dict(facecolor=color, color="#000000", alpha=alpha * 0.7),
                    medianprops=dict(color="#d62728", linewidth=1.8),
                    whiskerprops=dict(color="#000000", linewidth=1.2),
                    capprops=dict(color="#000000", linewidth=1.2),
                    flierprops=dict(marker="o", color=color, markersize=4, alpha=0.6),
                )
                artists.append(bp)

            if pt in ("box_jitter", "jitter", "strip"):
                rng = np.random.RandomState(int(abs(pos * 100) + len(y_clean)) % 10000)
                jitter = rng.uniform(-0.14, 0.14, size=len(y_clean))
                sp = ax.scatter(
                    pos + jitter,
                    y_clean,
                    s=max(ms ** 2, 28),
                    facecolors=mfc if mfc != "none" else color,
                    edgecolors=mec if mec != "none" else "#1e293b",
                    linewidths=mew,
                    alpha=min(alpha, 0.75),
                    zorder=5,
                )
                artists.append(sp)

            # Add invisible line with label so legend displays properly
            leg_artist = ax.plot([], [], color=color, label=label, marker="s" if "box" in pt else "o", linestyle="none")[0]
            return leg_artist

        elif pt in ("violin", "violin_jitter"):
            y_arr = np.asarray(y, dtype=float)
            y_clean = y_arr[np.isfinite(y_arr)]
            if len(y_clean) == 0:
                return None

            if group_pos is not None:
                pos = float(group_pos)
            else:
                x_arr = np.asarray(x, dtype=float)
                x_valid = x_arr[np.isfinite(x_arr)]
                if len(x_valid) > 0 and len(np.unique(x_valid)) == 1:
                    pos = float(x_valid[0])
                else:
                    l_idx = getattr(curve_model, "layer_index", 0)
                    pos = float(l_idx + 1) if l_idx is not None else 1.0

            parts = ax.violinplot(
                [y_clean],
                positions=[pos],
                widths=0.6,
                showmeans=True,
                showmedians=True,
            )
            for pc in parts["bodies"]:
                pc.set_facecolor(color)
                pc.set_edgecolor("#000000")
                pc.set_alpha(alpha * 0.6)

            if pt == "violin_jitter":
                rng = np.random.RandomState(int(abs(pos * 100) + len(y_clean)) % 10000)
                jitter = rng.uniform(-0.12, 0.12, size=len(y_clean))
                ax.scatter(
                    pos + jitter,
                    y_clean,
                    s=max(ms ** 2, 25),
                    facecolors=mfc if mfc != "none" else color,
                    edgecolors=mec if mec != "none" else "#1e293b",
                    linewidths=mew,
                    alpha=min(alpha, 0.7),
                    zorder=5,
                )

            leg_artist = ax.plot([], [], color=color, label=label, marker="o", linestyle="none")[0]
            return leg_artist

        # Default fallback
        artist = ax.plot(x, y, color=color, linewidth=lw, alpha=alpha, label=label)
        return artist[0]
