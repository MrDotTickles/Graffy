"""
Project model, Graph model, and serialization system.
Manages entire workspace state: Workbooks, Sheets, Graphs, Annotations, and Fit Reports.
"""

import json
import os
import uuid
from typing import List, Dict, Any, Optional
import numpy as np
from omnigraph.core.worksheet import Workbook, Worksheet, Column, ColumnRole


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder that converts numpy scalars and arrays to native Python types."""

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


class CurveModel:
    """Represents a single plotted data series or fitted line."""

    def __init__(
        self,
        id: Optional[str] = None,
        source_workbook: str = "Book1",
        source_sheet: str = "Sheet1",
        x_col_idx: int = 0,
        y_col_idx: int = 1,
        y_err_col_idx: Optional[int] = None,
        label: str = "Data",
        color: str = "#1f77b4",
        line_style: str = "-",
        line_width: float = 1.8,
        marker: str = "o",
        marker_size: float = 6.0,
        marker_face_color: str = "auto",
        marker_edge_color: str = "auto",
        marker_edge_width: float = 1.0,
        alpha: float = 1.0,
        axis: str = "primary",  # "primary" or "secondary"
        plot_type: str = "scatter",  # scatter, line, line_symbol, bar, step, area
        is_fit_curve: bool = False,
        fit_formula_str: str = "",
        fit_model_name: Optional[str] = None,
        fit_source_curve_id: Optional[str] = None,
        fit_degree: Optional[int] = None,
        visible: bool = True,
        layer_index: int = 0,
        y_offset: float = 0.0,
        x_offset: float = 0.0,
    ):
        self.id = id if id else str(uuid.uuid4())[:8]
        self.source_workbook = source_workbook
        self.source_sheet = source_sheet
        self.x_col_idx = x_col_idx
        self.y_col_idx = y_col_idx
        self.y_err_col_idx = y_err_col_idx
        self.label = label
        self.color = color
        self.line_style = line_style
        self.line_width = line_width
        self.marker = marker
        self.marker_size = marker_size
        self.marker_face_color = marker_face_color
        self.marker_edge_color = marker_edge_color
        self.marker_edge_width = marker_edge_width
        self.alpha = alpha
        self.axis = axis
        self.plot_type = plot_type
        self.is_fit_curve = is_fit_curve
        self.fit_formula_str = fit_formula_str
        self.fit_model_name = fit_model_name
        self.fit_source_curve_id = fit_source_curve_id
        self.fit_degree = fit_degree
        self.visible = visible
        self.layer_index = layer_index
        self.y_offset = float(y_offset)
        self.x_offset = float(x_offset)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_workbook": self.source_workbook,
            "source_sheet": self.source_sheet,
            "x_col_idx": self.x_col_idx,
            "y_col_idx": self.y_col_idx,
            "y_err_col_idx": self.y_err_col_idx,
            "label": self.label,
            "color": self.color,
            "line_style": self.line_style,
            "line_width": self.line_width,
            "marker": self.marker,
            "marker_size": self.marker_size,
            "marker_face_color": self.marker_face_color,
            "marker_edge_color": self.marker_edge_color,
            "marker_edge_width": self.marker_edge_width,
            "alpha": self.alpha,
            "axis": self.axis,
            "plot_type": self.plot_type,
            "is_fit_curve": self.is_fit_curve,
            "fit_formula_str": self.fit_formula_str,
            "fit_model_name": self.fit_model_name,
            "fit_source_curve_id": self.fit_source_curve_id,
            "fit_degree": self.fit_degree,
            "visible": self.visible,
            "layer_index": self.layer_index,
            "y_offset": self.y_offset,
            "x_offset": self.x_offset,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CurveModel":
        return cls(
            id=d.get("id"),
            source_workbook=d.get("source_workbook", "Book1"),
            source_sheet=d.get("source_sheet", "Sheet1"),
            x_col_idx=d.get("x_col_idx", 0),
            y_col_idx=d.get("y_col_idx", 1),
            y_err_col_idx=d.get("y_err_col_idx"),
            label=d.get("label", "Data"),
            color=d.get("color", "#1f77b4"),
            line_style=d.get("line_style", "-"),
            line_width=d.get("line_width", 1.8),
            marker=d.get("marker", "o"),
            marker_size=d.get("marker_size", 6.0),
            marker_face_color=d.get("marker_face_color", "auto"),
            marker_edge_color=d.get("marker_edge_color", "auto"),
            marker_edge_width=d.get("marker_edge_width", 1.0),
            alpha=d.get("alpha", 1.0),
            axis=d.get("axis", "primary"),
            plot_type=d.get("plot_type", "scatter"),
            is_fit_curve=d.get("is_fit_curve", False),
            fit_formula_str=d.get("fit_formula_str", ""),
            fit_model_name=d.get("fit_model_name"),
            fit_source_curve_id=d.get("fit_source_curve_id"),
            fit_degree=d.get("fit_degree"),
            visible=d.get("visible", True),
            layer_index=d.get("layer_index", 0),
            y_offset=d.get("y_offset", 0.0),
            x_offset=d.get("x_offset", 0.0),
        )


class GraphModel:
    """Represents a Graph window with axes, curves, theme, and styling."""

    def __init__(
        self,
        title: str = "Graph1",
        id: Optional[str] = None,
        plot_type: str = "scatter",
        layout_mode: str = "single",
        title_text: str = "",
        x_title: str = "X Axis",
        y_title: str = "Y Axis",
        y2_title: str = "",
        waterfall_enabled: bool = False,
        waterfall_y_step: float = 0.0,
        waterfall_x_step: float = 0.0,
        waterfall_baseline: bool = False,
        sync_axes: bool = True,
    ):
        self.id = id if id else str(uuid.uuid4())[:8]
        self.title = title
        self.plot_type = plot_type  # scatter, line, line_symbol, bar, errorbar, histogram, box, etc.
        self.layout_mode = layout_mode  # "single", "twin_x", "stacked_2x1"
        self.curves: List[CurveModel] = []

        # Axes properties
        self.x_title: str = x_title
        self.y_title: str = y_title
        self.y2_title: str = y2_title
        self.y_bottom_title: str = "Bottom Y"
        self.title_text: str = title_text
        self.panel_label: str = ""  # Quick publication panel autograph e.g. '(A)', '(B)', 'Figure 1'

        self.x_scale: str = "linear"  # linear, log10, ln
        self.y_scale: str = "linear"
        self.y2_scale: str = "linear"

        self.x_auto_limits: bool = True
        self.x_min: Optional[float] = None
        self.x_max: Optional[float] = None

        self.y_auto_limits: bool = True
        self.y_min: Optional[float] = None
        self.y_max: Optional[float] = None

        self.y2_auto_limits: bool = True
        self.y2_min: Optional[float] = None
        self.y2_max: Optional[float] = None

        # Frame & Styling (Origin Classic has box frame with inward ticks)
        self.box_frame: bool = True
        self.tick_direction: str = "in"  # "in", "out", "inout", "none"
        self.show_grid_major: bool = False
        self.show_grid_minor: bool = False
        self.grid_color: str = "#e0e0e0"
        self.grid_alpha: float = 0.7
        self.grid_style: str = "--"

        # Legend properties
        self.legend_show: bool = True
        self.legend_location: str = "best"
        self.legend_frame: bool = True
        self.legend_font_size: int = 10

        # Theme
        self.theme: str = "Origin Classic"  # Origin Classic, Nature, Science, Modern Dark, Prism, High-Contrast

        # Waterfall / Offset Spectra properties
        self.waterfall_enabled: bool = waterfall_enabled
        self.waterfall_offset_mode: str = "uniform"  # "uniform", "percentage", "absolute"
        self.waterfall_y_step: float = waterfall_y_step
        self.waterfall_x_step: float = waterfall_x_step
        self.waterfall_baseline: bool = waterfall_baseline

        # Multi-panel & Axis synchronization
        self.sync_axes: bool = sync_axes

        # Annotations (text callouts, reference lines, significance brackets)
        self.annotations: List[Dict[str, Any]] = []

    def add_curve(self, curve: CurveModel):
        self.curves.append(curve)

    def remove_curve(self, curve_id: str) -> bool:
        for i, c in enumerate(self.curves):
            if c.id == curve_id:
                self.curves.pop(i)
                return True
        return False

    def remove_curve_at(self, index: int) -> bool:
        if 0 <= index < len(self.curves):
            self.curves.pop(index)
            return True
        return False

    def move_curve_up(self, index: int) -> bool:
        """Moves curve earlier in drawing order (lower z-layer)."""
        if 1 <= index < len(self.curves):
            self.curves[index], self.curves[index - 1] = self.curves[index - 1], self.curves[index]
            return True
        return False

    def move_curve_down(self, index: int) -> bool:
        """Moves curve later in drawing order (top z-layer)."""
        if 0 <= index < len(self.curves) - 1:
            self.curves[index], self.curves[index + 1] = self.curves[index + 1], self.curves[index]
            return True
        return False

    def toggle_curve_visibility(self, index: int) -> bool:
        if 0 <= index < len(self.curves):
            self.curves[index].visible = not self.curves[index].visible
            return True
        return False

    def set_title(self, text: str):
        self.title_text = text.strip()

    def set_x_title(self, text: str):
        self.x_title = text.strip()

    def set_y_title(self, text: str):
        self.y_title = text.strip()

    def set_y2_title(self, text: str):
        self.y2_title = text.strip()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "plot_type": self.plot_type,
            "layout_mode": self.layout_mode,
            "curves": [c.to_dict() for c in self.curves],
            "x_title": self.x_title,
            "y_title": self.y_title,
            "y2_title": self.y2_title,
            "y_bottom_title": self.y_bottom_title,
            "title_text": self.title_text,
            "panel_label": getattr(self, "panel_label", ""),
            "x_scale": self.x_scale,
            "y_scale": self.y_scale,
            "y2_scale": self.y2_scale,
            "x_auto_limits": self.x_auto_limits,
            "x_min": self.x_min,
            "x_max": self.x_max,
            "y_auto_limits": self.y_auto_limits,
            "y_min": self.y_min,
            "y_max": self.y_max,
            "y2_auto_limits": self.y2_auto_limits,
            "y2_min": self.y2_min,
            "y2_max": self.y2_max,
            "box_frame": self.box_frame,
            "tick_direction": self.tick_direction,
            "show_grid_major": self.show_grid_major,
            "show_grid_minor": self.show_grid_minor,
            "grid_color": self.grid_color,
            "grid_alpha": self.grid_alpha,
            "grid_style": self.grid_style,
            "legend_show": self.legend_show,
            "legend_location": self.legend_location,
            "legend_frame": self.legend_frame,
            "legend_font_size": self.legend_font_size,
            "theme": self.theme,
            "waterfall_enabled": self.waterfall_enabled,
            "waterfall_offset_mode": self.waterfall_offset_mode,
            "waterfall_y_step": self.waterfall_y_step,
            "waterfall_x_step": self.waterfall_x_step,
            "waterfall_baseline": self.waterfall_baseline,
            "sync_axes": self.sync_axes,
            "annotations": self.annotations,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GraphModel":
        g = cls(
            title=d.get("title", "Graph1"),
            id=d.get("id"),
            plot_type=d.get("plot_type", "scatter"),
            layout_mode=d.get("layout_mode", "single"),
        )
        g.curves = [CurveModel.from_dict(c) for c in d.get("curves", [])]
        g.x_title = d.get("x_title", "X Axis")
        g.y_title = d.get("y_title", "Y Axis")
        g.y2_title = d.get("y2_title", "")
        g.y_bottom_title = d.get("y_bottom_title", "Bottom Y")
        g.title_text = d.get("title_text", "")
        g.panel_label = d.get("panel_label", "")
        g.x_scale = d.get("x_scale", "linear")
        g.y_scale = d.get("y_scale", "linear")
        g.y2_scale = d.get("y2_scale", "linear")
        g.x_auto_limits = d.get("x_auto_limits", True)
        g.x_min = d.get("x_min")
        g.x_max = d.get("x_max")
        g.y_auto_limits = d.get("y_auto_limits", True)
        g.y_min = d.get("y_min")
        g.y_max = d.get("y_max")
        g.y2_auto_limits = d.get("y2_auto_limits", True)
        g.y2_min = d.get("y2_min")
        g.y2_max = d.get("y2_max")
        g.box_frame = d.get("box_frame", True)
        g.tick_direction = d.get("tick_direction", "in")
        g.show_grid_major = d.get("show_grid_major", False)
        g.show_grid_minor = d.get("show_grid_minor", False)
        g.grid_color = d.get("grid_color", "#e0e0e0")
        g.grid_alpha = d.get("grid_alpha", 0.7)
        g.grid_style = d.get("grid_style", "--")
        g.legend_show = d.get("legend_show", True)
        g.legend_location = d.get("legend_location", "best")
        g.legend_frame = d.get("legend_frame", True)
        g.legend_font_size = d.get("legend_font_size", 10)
        g.theme = d.get("theme", "Origin Classic")
        g.waterfall_enabled = d.get("waterfall_enabled", False)
        g.waterfall_offset_mode = d.get("waterfall_offset_mode", "uniform")
        g.waterfall_y_step = d.get("waterfall_y_step", 0.0)
        g.waterfall_x_step = d.get("waterfall_x_step", 0.0)
        g.waterfall_baseline = d.get("waterfall_baseline", False)
        g.sync_axes = d.get("sync_axes", True)
        g.annotations = d.get("annotations", [])
        return g


class ReportModel:
    """Represents a scientific fit or analysis report sheet."""

    def __init__(
        self,
        title: str = "Fit Report 1",
        id: Optional[str] = None,
        report_type: str = "fit",
        html_content: str = "",
        parameters: Optional[Dict[str, Any]] = None,
    ):
        self.id = id if id else str(uuid.uuid4())[:8]
        self.title = title
        self.report_type = report_type
        self.html_content = html_content
        self.parameters = parameters if parameters is not None else {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "report_type": self.report_type,
            "html_content": self.html_content,
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ReportModel":
        return cls(
            title=d.get("title", "Report1"),
            id=d.get("id"),
            report_type=d.get("report_type", "fit"),
            html_content=d.get("html_content", ""),
            parameters=d.get("parameters", {}),
        )


class Project:
    """Root project managing all workbooks, graphs, and analysis reports."""

    def __init__(self, name: str = "Untitled Project", workbooks: Optional[List[Workbook]] = None):
        self.name = name
        self.filepath: Optional[str] = None
        self.workbooks: List[Workbook] = workbooks if workbooks is not None else [Workbook.create_default("Book1")]
        self.graphs: List[GraphModel] = []
        self.reports: List[ReportModel] = []

    @classmethod
    def create_default(cls, name: str = "Untitled Project") -> "Project":
        return cls(name=name)

    def add_workbook(self, name: Optional[str] = None) -> Workbook:
        if not name:
            name = f"Book{len(self.workbooks) + 1}"
        wb = Workbook(name=name)
        self.workbooks.append(wb)
        return wb

    def get_workbook(self, name: str) -> Optional[Workbook]:
        for wb in self.workbooks:
            if wb.name == name:
                return wb
        return None

    def get_graph(self, title_or_id: str) -> Optional[GraphModel]:
        for g in self.graphs:
            if g.title == title_or_id or g.id == title_or_id:
                return g
        return None

    def save_to_file(self, filepath: str):
        """Save project as JSON .kgraph file."""
        data = {
            "version": "1.0",
            "name": self.name,
            "workbooks": [wb.to_dict() for wb in self.workbooks],
            "graphs": [g.to_dict() for g in self.graphs],
            "reports": [r.to_dict() for r in self.reports],
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, cls=NumpyEncoder)
        self.filepath = filepath

    save_project = save_to_file

    @classmethod
    def load_from_file(cls, filepath: str) -> "Project":
        """Load project from JSON .kgraph file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        proj = cls(name=data.get("name", "Loaded Project"))
        proj.filepath = filepath
        proj.workbooks = [Workbook.from_dict(wb) for wb in data.get("workbooks", [])]
        proj.graphs = [GraphModel.from_dict(g) for g in data.get("graphs", [])]
        proj.reports = [ReportModel.from_dict(r) for r in data.get("reports", [])]
        if not proj.workbooks:
            proj.workbooks.append(Workbook.create_default("Book1"))
        return proj
