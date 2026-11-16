"""Build XY series and comparison figures from dropped worksheet data."""

from copy import deepcopy
from uuid import uuid4

from omnigraph.core.column_matching import numeric_pairs
from omnigraph.core.plot_editing import axis_family, change_series_plot_type
from omnigraph.core.project import CurveModel, GraphModel
from omnigraph.core.worksheet import ColumnRole
from omnigraph.graphing.themes import get_theme_palette


def worksheet_curves(sheet, workbook, graph, plot_type, pairs=None):
    """Return usable, unplotted series. Keep the worksheet as their live source."""
    existing = {(curve.source_workbook, curve.source_sheet, curve.x_col_idx, curve.y_col_idx)
                for curve in graph.curves if not curve.is_fit_curve}
    labels = {curve.label for curve in graph.curves}
    palette = get_theme_palette(graph.theme)
    curves = []
    duplicate = False
    if pairs is None:
        pairs = [(x, y) for x, y in sheet.plot_column_pairs() if sheet.columns[y].role == ColumnRole.Y]
    for x, y in pairs:
        if (workbook, sheet.name, x, y) in existing:
            duplicate = True
            continue
        xs, _ = numeric_pairs(sheet, x, y)
        if not len(xs):
            continue
        y_column = sheet.columns[y]
        base = label = f"{sheet.name} · {y_column.display_label}"
        suffix = 2
        while label in labels:
            label = f"{base} ({suffix})"
            suffix += 1
        labels.add(label)
        error = sheet.find_y_error_column_for(y)
        kind = "errorbar" if error is not None and plot_type in {"line", "scatter", "line_symbol"} else plot_type
        curves.append(CurveModel(
            source_workbook=workbook, source_sheet=sheet.name, x_col_idx=x, y_col_idx=y,
            y_err_col_idx=error, label=label, color=palette[(len(graph.curves) + len(curves)) % len(palette)],
            plot_type=kind,
        ))
    return curves, duplicate


def _curve_key(curve):
    return curve.source_workbook, curve.source_sheet, curve.x_col_idx, curve.y_col_idx


def _columns(project, curve):
    sheet = project.get_worksheet(curve.source_workbook, curve.source_sheet)
    if sheet is None:
        return (None, None)
    return sheet.get_column(curve.x_col_idx), sheet.get_column(curve.y_col_idx)


def _axis_title(columns, axis):
    labels = {column.display_label for column in columns if column}
    if len(labels) == 1:
        return next(iter(labels))
    units = {column.units for column in columns if column}
    if len(units) == 1 and "" not in units:
        return f"{axis} ({next(iter(units))})"
    return axis


def create_drop_figure(project, target, incoming, mode):
    incoming = [
        curve for curve in incoming
        if (sheet := project.get_worksheet(curve.source_workbook, curve.source_sheet)) is not None
        and len(numeric_pairs(sheet, curve.x_col_idx, curve.y_col_idx)[0])
    ]
    if not incoming:
        raise ValueError("The dropped data needs numeric values in separate X and Y columns.")
    current = []
    if mode != "new":
        for curve in target.curves:
            if curve.is_fit_curve or not curve.visible:
                continue
            sheet = project.get_worksheet(curve.source_workbook, curve.source_sheet)
            if sheet is not None and len(numeric_pairs(sheet, curve.x_col_idx, curve.y_col_idx)[0]):
                current.append(curve)
    chart_type = {"new": "New chart", "side_by_side": "Side-by-side", "waterfall": "Waterfall"}[mode]
    subject = incoming[0].source_sheet if mode == "new" else target.title
    root = f"{chart_type} · {subject}"
    title = root
    number = 2
    while project.get_graph(title):
        title = f"{root} ({number})"
        number += 1
    graph = GraphModel(title=title, plot_type="line_symbol", sync_axes=False)
    graph.theme = target.theme

    if mode == "side_by_side":
        if not current:
            first_source = _curve_key(incoming[0])[:2]
            if any(_curve_key(curve)[:2] != first_source for curve in incoming[1:]):
                current = [curve for curve in incoming if _curve_key(curve)[:2] == first_source]
                incoming = [curve for curve in incoming if _curve_key(curve)[:2] != first_source]
            else:
                current, incoming = incoming[:1], incoming[1:]
        if not incoming:
            raise ValueError("A side-by-side comparison needs two series. Drop another worksheet or add a second Y column.")
        graph.layout_mode = "grid_1x2"
    elif mode == "waterfall":
        traces = {_curve_key(curve): curve for curve in [*current, *incoming]}
        current, incoming = [], list(traces.values())
        if len(incoming) < 2:
            raise ValueError("A waterfall needs at least two different traces. Add another worksheet or Y column.")
        x_columns, y_columns = zip(*(_columns(project, curve) for curve in incoming))
        if any(len({column.units for column in columns if column and column.units}) > 1
               for columns in (x_columns, y_columns)):
            raise ValueError("Waterfall traces must use matching X and Y units. Use side-by-side for separate axes.")
        graph.waterfall_enabled = True
        graph.waterfall_offset_mode = "auto"
        graph.waterfall_show_y_axis = False
        graph.plot_type = "line"

    palette = get_theme_palette(graph.theme)
    for index, original in enumerate([*current, *incoming]):
        curve = deepcopy(original)
        curve.id = uuid4().hex[:8]
        curve.axis = "primary"
        curve.layer_index = int(mode == "side_by_side" and index >= len(current))
        curve.x_offset = curve.y_offset = 0
        curve.color = palette[index % len(palette)]
        if mode == "waterfall":
            change_series_plot_type(curve, "line")
        elif axis_family(curve.plot_type) != "xy":
            change_series_plot_type(curve, "line_symbol")
        graph.add_curve(curve)
    if mode == "side_by_side":
        for prefix, curves in (("", graph.curves[:len(current)]), ("right_panel_", graph.curves[len(current):])):
            xs, ys = zip(*(_columns(project, curve) for curve in curves))
            setattr(graph, f"{prefix}x_title", _axis_title(xs, "X"))
            setattr(graph, f"{prefix}y_title", _axis_title(ys, "Y"))
        graph.comparison_panels = True
    else:
        if mode == "new":
            kinds = {curve.plot_type for curve in graph.curves}
            if len(kinds) == 1:
                graph.plot_type = graph.curves[0].plot_type
        xs, ys = zip(*(_columns(project, curve) for curve in graph.curves))
        graph.x_title = _axis_title(xs, "X")
        graph.y_title = _axis_title(ys, "Y")
    return graph
