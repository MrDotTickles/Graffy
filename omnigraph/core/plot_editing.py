"""Data-preserving changes shared by chart appearance controls."""
from copy import deepcopy
import uuid

from matplotlib.colors import to_rgba

PLOT_GROUPS = (
    ("XY plots", (("Scatter", "scatter"), ("Line", "line"),
     ("Line and symbols", "line_symbol"), ("Step", "step"),
     ("Smooth spline", "spline"), ("Error bars", "errorbar"),
     ("Vertical bars", "bar"), ("Horizontal bars", "hbar"), ("Area", "area"))),
    ("Distributions", (("Histogram", "histogram"), ("Box plot", "box"),
     ("Box plot and points", "box_jitter"), ("Violin", "violin"),
     ("Violin and points", "violin_jitter"), ("Individual points", "jitter"))),
)
PLOT_CHOICES = tuple(choice for _, choices in PLOT_GROUPS for choice in choices)
DISTRIBUTION_TYPES = {"histogram", "box", "box_whisker", "box_jitter", "violin", "violin_jitter", "jitter", "strip"}


def change_series_plot_type(curve, plot_type):
    """Keep data links, errors, styles and identity; ensure a visible default."""
    if plot_type not in dict((value, label) for label, value in PLOT_CHOICES):
        raise ValueError(f"Unsupported plot type: {plot_type}")
    curve.plot_type = plot_type
    if plot_type in {"scatter", "line_symbol", "errorbar"} and curve.marker in (None, "none", ""):
        curve.marker = "o"
    if plot_type in {"line", "line_symbol", "step", "spline"} and str(curve.line_style).lower() in ("none", "", " "):
        curve.line_style = "-"


def set_series_color(curve, color, effective_old_color=None):
    """Matching symbol overrides follow the base color; custom fills stay intact."""
    if color == curve.color:
        return
    old = effective_old_color or curve.color
    for field in ("marker_face_color", "marker_edge_color"):
        value = getattr(curve, field)
        try:
            matching = value not in ("auto", "none") and to_rgba(value) == to_rgba(old)
        except (ValueError, TypeError):
            matching = False
        if matching:
            setattr(curve, field, "auto")
    curve.color = color


def axis_family(plot_type):
    if plot_type == "histogram":
        return "histogram"
    if plot_type in DISTRIBUTION_TYPES:
        return "grouped"
    return "horizontal" if plot_type == "hbar" else "xy"


def change_graph_plot_type(graph, plot_type):
    """Convert measured series in place and retain representation-specific labels."""
    if plot_type not in {value for _, value in PLOT_CHOICES}:
        raise ValueError(f"Unsupported plot type: {plot_type}")
    curves = [curve for curve in graph.curves if not curve.is_fit_curve]
    if not curves:
        return False
    kinds = {curve.plot_type for curve in curves}
    current_family = axis_family(next(iter(kinds))) if len(kinds) == 1 else "xy"
    target_family = axis_family(plot_type)
    labels = graph.plot_axis_settings
    labels[current_family] = {"x": graph.x_title, "y": graph.y_title, "x_scale": graph.x_scale, "y_scale": graph.y_scale}
    if "xy" not in labels:
        labels["xy"] = ({"x": graph.y_title, "y": graph.x_title}
                        if current_family == "horizontal" else {"x": "X", "y": graph.y_title})
    xy = labels["xy"]
    xy.setdefault("x_scale", "linear")
    xy.setdefault("y_scale", graph.y_scale)
    defaults = {"xy": xy, "horizontal": {"x": xy["y"], "y": xy["x"], "x_scale": xy["y_scale"], "y_scale": xy["x_scale"]},
                "histogram": {"x": xy["y"], "y": "Count", "x_scale": xy["y_scale"], "y_scale": "linear"},
                "grouped": {"x": "Series", "y": xy["y"], "x_scale": "linear", "y_scale": xy["y_scale"]}}
    titles = labels.get(target_family, defaults[target_family])
    graph.x_title, graph.y_title = titles["x"], titles["y"]
    graph.x_scale, graph.y_scale = titles.get("x_scale", "linear"), titles.get("y_scale", "linear")
    for curve in curves:
        change_series_plot_type(curve, plot_type)
    graph.plot_type = plot_type
    graph.x_auto_limits = graph.y_auto_limits = graph.y2_auto_limits = True
    return True


def rebind_chart_data(graph, mappings, *, copy_title=None):
    """Reuse chart styling with new data. Old analysis results stay on the original chart."""
    if copy_title is not None:
        graph = deepcopy(graph)
        graph.id = uuid.uuid4().hex[:8]
        graph.title = copy_title

    measured = [curve for curve in graph.curves if not curve.is_fit_curve]
    if len(measured) != len(mappings):
        raise ValueError("Choose data for every series before replacing chart data.")
    for curve, (workbook, sheet, x, y, error, label) in zip(measured, mappings):
        if copy_title is not None:
            curve.id = uuid.uuid4().hex[:8]
        curve.source_workbook = workbook
        curve.source_sheet = sheet
        curve.x_col_idx = x
        curve.y_col_idx = y
        curve.y_err_col_idx = error
        curve.label = label
    graph.curves = measured
    graph.annotations = [ann for ann in graph.annotations if ann.get("type") not in {"band", "bracket", "significance"}]
    return graph
