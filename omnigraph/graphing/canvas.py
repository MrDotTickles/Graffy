"""
High-performance Qt Figure Canvas for interactive scientific plotting.
Integrates Matplotlib with PyQt6, custom mouse navigation, and tool switching.
"""

import numpy as np

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy, QInputDialog, QLabel
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from omnigraph.worksheet_drag import WorksheetDragData
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.lines import Line2D
from matplotlib.transforms import IdentityTransform
from scipy.spatial import cKDTree

from omnigraph.graphing.plot_manager import PlotManager
from omnigraph.graphing.tools import GraphToolManager
from omnigraph.core.project import GraphModel, Project


class OmniCanvas(QWidget):
    """Interactive canvas widget displaying a GraphModel."""

    coordinates_changed = pyqtSignal(float, float)  # (x, y) coordinates under mouse cursor
    point_inspected = pyqtSignal(str, float, float, int)  # curve, x, y, row
    range_selected = pyqtSignal(float, float)  # xmin, xmax
    labels_changed = pyqtSignal()  # emitted when title or axis labels are edited
    worksheet_dropped = pyqtSignal(str, str, str)  # workbook, worksheet, optional layout
    files_dropped = pyqtSignal(list, str)  # file paths, optional layout
    point_mask_toggled = pyqtSignal(str, int)  # curve_label, row_idx
    request_significance_bracket = pyqtSignal(float, float, float)  # x1, x2, y
    request_text_note = pyqtSignal(object)
    request_annotation_edit = pyqtSignal(object)
    request_annotation_remove = pyqtSignal(object)
    annotation_moved = pyqtSignal(object, float, float)
    annotation_transformed = pyqtSignal(object, str, float)
    request_manage_overlays = pyqtSignal()
    note_placement_changed = pyqtSignal(bool)

    def __init__(self, graph_model: GraphModel, project: Project, parent=None):
        super().__init__(parent)
        self.graph_model = graph_model
        self.project = project
        self._last_mouse_data = None
        self._last_inspected = None
        self._drop_picker = None
        self._placing_note = False
        self._note_drag = None
        self._selected_note = None
        self._hover_index = {}
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAcceptDrops(True)

        self.plot_manager = PlotManager(graph_model, project)
        self.canvas = FigureCanvas(self.plot_manager.fig)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._hover_label = QLabel(self.canvas)
        self._hover_label.setTextFormat(Qt.TextFormat.PlainText)
        self._hover_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._hover_label.setStyleSheet(
            "background: #17233a; color: white; border-radius: 5px; padding: 5px 8px;"
        )
        self._hover_marker = QLabel(self.canvas)
        self._hover_marker.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._hover_marker.setFixedSize(11, 11)
        self._hover_marker.setStyleSheet("border: 2px solid #7c3aed; background: white; border-radius: 5px;")
        self._clear_hover()
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setIconSize(self.toolbar.iconSize())

        self.tool_manager = GraphToolManager(self.canvas, self.plot_manager.ax)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        # Wire events
        self.canvas.mpl_connect("motion_notify_event", self._on_motion)
        self.canvas.mpl_connect("figure_leave_event", self._clear_hover)
        self.canvas.mpl_connect("draw_event", self._draw_note_frame)
        self.canvas.mpl_connect("button_press_event", self._on_canvas_click)
        self.canvas.mpl_connect("button_release_event", self._finish_note_drag)
        self.tool_manager.point_inspected.connect(self._on_point_inspected)
        self.tool_manager.range_selected.connect(self.range_selected)

        # Wire hotkey 'M' for point masking
        from PyQt6.QtGui import QKeySequence, QShortcut
        self.shortcut_mask = QShortcut(QKeySequence(Qt.Key.Key_M), self)
        self.shortcut_mask.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_mask.activated.connect(self._toggle_mask_at_cursor)
        self.cancel_note_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self.canvas)
        self.cancel_note_shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
        self.cancel_note_shortcut.setEnabled(False)
        self.cancel_note_shortcut.activated.connect(self.cancel_note_placement)

        # Initial render
        self.refresh()

    def _show_drop_layouts(self):
        if self._drop_picker is None:
            from omnigraph.ui.chart_layout_picker import ChartLayoutPicker

            self._drop_picker = ChartLayoutPicker("Drop on a layout", self)
            self._drop_picker.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        picker = self._drop_picker
        area = self.canvas.geometry()
        size = picker.preferred_size()
        if size.width() + 16 > area.width() or size.height() + 16 > area.height():
            picker.hide()
            return
        picker.resize(size)
        picker.move(area.x() + (area.width() - size.width()) // 2, area.y() + 8)
        picker.raise_()
        picker.show()

    def _drop_layout_at(self, point):
        picker = self._drop_picker
        return picker.layout_at(picker.mapFrom(self, point)) if picker is not None else ""

    def _hide_drop_layouts(self):
        if self._drop_picker is not None:
            self._drop_picker.highlight("")
            self._drop_picker.hide()

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        worksheet = isinstance(mime, WorksheetDragData) and mime.project is self.project
        if worksheet or any(url.isLocalFile() for url in mime.urls()):
            event.acceptProposedAction()
            self._show_drop_layouts()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self._drop_picker is not None:
            self._drop_picker.highlight(self._drop_layout_at(event.position().toPoint()))
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._hide_drop_layouts()
        event.accept()

    def dropEvent(self, event):
        choice = self._drop_layout_at(event.position().toPoint())
        self._hide_drop_layouts()
        mime = event.mimeData()
        if isinstance(mime, WorksheetDragData) and mime.project is self.project:
            event.acceptProposedAction()
            self.worksheet_dropped.emit(mime.workbook, mime.sheet, choice)
            return
        paths = [url.toLocalFile() for url in mime.urls() if url.isLocalFile()]
        if paths:
            event.acceptProposedAction()
            self.files_dropped.emit(paths, choice)
            return
        super().dropEvent(event)

    def _on_point_inspected(self, label: str, x: float, y: float, row: int):
        self._last_inspected = (label, x, y, row)
        self.point_inspected.emit(label, x, y, row)

    def _toggle_mask_at_cursor(self):
        """Toggle mask on the point closest to mouse cursor."""
        pt = None
        if self._last_mouse_data:
            pt = self.tool_manager.find_nearest_point(self._last_mouse_data[0], self._last_mouse_data[1])
        if not pt and self._last_inspected:
            pt = self._last_inspected
        if pt:
            label = pt[0]
            row_idx = pt[3]
            self.point_mask_toggled.emit(label, row_idx)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            self.plot_manager.fig.tight_layout(pad=1.2)
            self.canvas.draw_idle()
        except Exception:
            pass

    def refresh(self):
        """Re-render graph from model."""
        self._note_drag = None
        self._clear_hover()
        self._hover_index.clear()
        self.plot_manager.render()
        if not any(note is self._selected_note for note, _ in self.plot_manager.annotation_artists):
            self._selected_note = None
        self.toolbar.update()
        self.tool_manager.ax = self.plot_manager.ax
        self.tool_manager.ax2 = self.plot_manager.ax2
        self.tool_manager.set_data_curves(self.plot_manager.rendered_curves)
        self.canvas.draw_idle()

    def set_tool(self, tool_name: str):
        """Switch canvas tool ('pointer', 'data_reader', 'range_selector')."""
        self.cancel_note_placement()
        self._clear_hover()
        self._select_note(None)
        self.tool_manager.set_tool(tool_name)

    def hideEvent(self, event):
        self.cancel_note_placement()
        super().hideEvent(event)

    def start_note_placement(self):
        if self.toolbar.mode.name == "PAN":
            self.toolbar.pan()
        elif self.toolbar.mode.name == "ZOOM":
            self.toolbar.zoom()
        self._clear_hover()
        self._select_note(None)
        self._placing_note = True
        self.cancel_note_shortcut.setEnabled(True)
        self.canvas.setCursor(Qt.CursorShape.CrossCursor)
        self.canvas.setFocus()
        self.note_placement_changed.emit(True)

    def cancel_note_placement(self):
        if self._placing_note:
            self._placing_note = False
            self.cancel_note_shortcut.setEnabled(False)
            self.canvas.unsetCursor()
            self.note_placement_changed.emit(False)

    def _note_location(self, event):
        axes = self.plot_manager.axes
        secondary = event.inaxes is self.plot_manager.ax2
        return {"type": "text", "x": float(event.xdata), "y": float(event.ydata),
                "panel": axes.index(event.inaxes) if not secondary else 0,
                "axis": "secondary" if secondary else "primary", "clip": True}

    def _note_at(self, event):
        if event.x is None or event.y is None:
            return None
        renderer = self.canvas.get_renderer()
        for annotation, artist in reversed(self.plot_manager.annotation_artists):
            if artist.get_clip_on() and not artist.axes.bbox.contains(event.x, event.y):
                continue
            if artist.get_window_extent(renderer).padded(4).contains(event.x, event.y):
                return annotation, artist
        return None

    def _select_note(self, note):
        if self._selected_note is not note:
            self._selected_note = note
            self.canvas.draw_idle()

    def _note_handles(self, renderer):
        for annotation, artist in self.plot_manager.annotation_artists:
            if annotation is self._selected_note:
                box = artist.get_window_extent(renderer).padded(5 * self.canvas.device_pixel_ratio)
                rotate = ((box.x0 + box.x1) / 2, box.y1 + 17 * self.canvas.device_pixel_ratio)
                resize = (box.x1, box.y0)
                return artist, box, rotate, resize
        return None

    def _draw_note_frame(self, event):
        if event.canvas.is_saving() or self._selected_note is None or self.toolbar.mode:
            return
        handles = self._note_handles(event.renderer)
        if handles is None:
            return
        _, box, rotate, resize = handles
        artists = (
            Line2D([box.x0, box.x1, box.x1, box.x0, box.x0],
                   [box.y0, box.y0, box.y1, box.y1, box.y0], linewidth=0.9),
            Line2D([rotate[0], rotate[0]], [box.y1, rotate[1]], linewidth=0.9),
            Line2D([rotate[0]], [rotate[1]], marker="o", markersize=6, markerfacecolor="white"),
            Line2D([resize[0]], [resize[1]], marker="s", markersize=6, markerfacecolor="white"),
        )
        for handle in artists:
            handle.set_color("#7c3aed")
            handle.set_markeredgecolor("#7c3aed")
            handle.set_transform(IdentityTransform())
            handle.set_figure(self.plot_manager.fig)
            handle.draw(event.renderer)

    def _handle_at(self, event):
        if self._selected_note is None:
            return None
        handles = self._note_handles(self.canvas.get_renderer())
        if handles is not None:
            artist, _, rotate, resize = handles
            point = np.array([event.x, event.y])
            for mode, center in (("rotation", rotate), ("font_size", resize)):
                if np.linalg.norm(point - center) <= 9 * self.canvas.device_pixel_ratio:
                    return artist, mode
        return None

    def _move_note_preview(self, event):
        if self._note_drag is None or event.x is None or event.y is None:
            return
        annotation, artist, start, mode = self._note_drag
        delta = np.array((event.x, event.y)) - start
        moved = np.dot(delta, delta) >= 16
        ax = artist.axes
        anchor = ax.transData.transform((annotation.get("x", 0.5), annotation.get("y", 0.5)))
        if mode == "rotation":
            angle = annotation.get("rotation", 0)
            if moved:
                x, y = start - anchor
                dx, dy = delta
                angle += np.degrees(np.arctan2(y + dy, x + dx) - np.arctan2(y, x))
            artist.set_rotation(angle)
        elif mode == "font_size":
            size = annotation.get("font_size", 10)
            if moved:
                distance = max(8, np.linalg.norm(start - anchor))
                size = float(np.clip(size * max(8, np.linalg.norm(start + delta - anchor)) / distance, 4, 200))
            artist.set_fontsize(size)
        elif moved:
            bounds = ax.bbox
            point = np.clip(anchor + delta, (bounds.x0, bounds.y0), (bounds.x1, bounds.y1))
            position = ax.transData.inverted().transform(point)
            if np.isfinite(position).all():
                artist.set_position(position)
        else:
            artist.set_position((annotation.get("x", 0.5), annotation.get("y", 0.5)))
        self.canvas.draw_idle()

    def _finish_note_drag(self, event):
        if self._note_drag is None or event.button != 1:
            return
        self._move_note_preview(event)
        annotation, artist, start, mode = self._note_drag
        self._note_drag = None
        if mode:
            if np.linalg.norm(np.array((event.x, event.y)) - start) >= 4:
                value = (artist.get_rotation() + 180) % 360 - 180 if mode == "rotation" else artist.get_fontsize()
                self.annotation_transformed.emit(annotation, mode, round(value, 1))
            return
        x, y = (float(value) for value in artist.get_position())
        if (x, y) != (annotation.get("x", 0.5), annotation.get("y", 0.5)):
            self.annotation_moved.emit(annotation, x, y)

    def _clear_hover(self, event=None):
        self._hover_label.hide()
        self._hover_marker.hide()

    def _hover_data(self, event):
        if event.inaxes is None or self._placing_note or self._note_drag is not None or self.toolbar.mode:
            self._clear_hover()
            return
        if self.tool_manager.current_tool != "pointer" or self._note_at(event) or self._handle_at(event):
            self._clear_hover()
            return

        best = None
        ratio = self.canvas.device_pixel_ratio
        radius = 11 * ratio
        for ax, label, xs, ys, rows in self.plot_manager.hover_curves:
            if not ax.bbox.contains(event.x, event.y) or not len(xs):
                continue
            key = (ax.bbox.bounds, ax.get_xlim(), ax.get_ylim(), ax.get_xscale(), ax.get_yscale())
            cache_key = (ax, id(xs), id(ys))
            cached = self._hover_index.get(cache_key)
            if cached is None or cached[0] != key:
                pixels = ax.transData.transform(np.column_stack((xs, ys)))
                visible = (np.isfinite(pixels).all(axis=1) & (pixels[:, 0] >= ax.bbox.x0)
                           & (pixels[:, 0] <= ax.bbox.x1) & (pixels[:, 1] >= ax.bbox.y0)
                           & (pixels[:, 1] <= ax.bbox.y1))
                indexes = np.flatnonzero(visible)
                cached = key, indexes, cKDTree(pixels[visible])
                self._hover_index[cache_key] = cached
            _, indexes, tree = cached
            distance, index = tree.query((event.x, event.y), distance_upper_bound=radius)
            if np.isfinite(distance):
                radius = distance + 1e-9
                data_index = indexes[index]
                row = rows[data_index] if rows is not None else None
                best = label, xs[data_index], ys[data_index], row, tree.data[index]
        if best is None:
            self._clear_hover()
            return

        label, x, y, row, pixel = best
        px, py = int(pixel[0] / ratio), self.canvas.height() - int(pixel[1] / ratio)
        short_label = label if len(label) <= 52 else label[:49] + "…"
        description = f"{short_label}\nX {x:.6g}  ·  Y {y:.6g}"
        if row is not None:
            description += f"  ·  Row {row + 1}"
        if self._hover_label.text() != description:
            self._hover_label.setText(description)
            self._hover_label.adjustSize()
        self._hover_marker.move(px - 5, py - 5)
        self._hover_marker.show()
        width, height = self._hover_label.width(), self._hover_label.height()
        left = px + 13 if px + 13 + width < self.canvas.width() else max(0, px - width - 13)
        top = py - height - 10 if py >= height + 10 else py + 10
        self._hover_label.move(left, top)
        self._hover_label.show()

    def _on_motion(self, event):
        self._move_note_preview(event)
        self._hover_data(event)
        if event.inaxes and event.xdata is not None and event.ydata is not None:
            self._last_mouse_data = (float(event.xdata), float(event.ydata))
            self.coordinates_changed.emit(float(event.xdata), float(event.ydata))

    def _on_canvas_click(self, event):
        """Direct in-place double-click label editing, right-click context menu, and legend detection."""
        inside = event.inaxes is not None and event.xdata is not None and event.ydata is not None
        if self._placing_note:
            if event.button == 1 and inside:
                self.cancel_note_placement()
                self.request_text_note.emit(self._note_location(event))
            elif event.button == 3:
                self.cancel_note_placement()
            return
        if event.button == 1 and not self.toolbar.mode and self.tool_manager.current_tool == "pointer":
            self._clear_hover()
            handle = self._handle_at(event)
            if handle is not None:
                artist, mode = handle
                self._note_drag = (self._selected_note, artist, np.array([event.x, event.y]), mode)
                return
            note = self._note_at(event)
            if note is not None:
                annotation, artist = note
                self._select_note(annotation)
                if event.dblclick:
                    self.request_annotation_edit.emit(annotation)
                else:
                    self._note_drag = (annotation, artist, np.array([event.x, event.y]), "")
                return
            self._select_note(None)
        # Handle Right-Click (Button 3) Context Menu
        if event.button == 3 and inside:
            self._show_canvas_context_menu(event)
            return

        if not event.dblclick or event.button != 1:
            return

        # Check if double click hit the legend (Key)
        ax = self.plot_manager.ax
        if ax is not None:
            legend = ax.get_legend()
            if legend is not None and legend.get_visible():
                contains, _ = legend.contains(event)
                if contains:
                    self.open_legend_editor()
                    return

        if event.x is None or event.y is None:
            return
        renderer = self.canvas.get_renderer()
        manager = self.plot_manager

        def hit(text):
            return (text.get_visible() and bool(text.get_text())
                    and text.get_window_extent(renderer).padded(4).contains(event.x, event.y))

        # Labels are outside the plotting area. Use their actual painted bounds.
        for panel in manager.fig.axes:
            y_key = self._y_axis_key(panel)
            if panel.yaxis.get_visible() and hit(panel.yaxis.label):
                {"y": self.edit_y_title, "y2": self.edit_y2_title,
                 "y_bottom": self.edit_bottom_y_title,
                 "right_panel_y": lambda: self._edit_right_panel_label("y")}[y_key]()
                return
            if panel.xaxis.get_visible() and hit(panel.xaxis.label):
                if self._is_right_comparison_panel(panel):
                    self._edit_right_panel_label("x")
                else:
                    self.edit_x_title()
                return
        for panel in manager.fig.axes:
            if hit(panel.title):
                self.edit_graph_title()
                return

        for panel in manager.fig.axes:
            if panel.xaxis.get_visible() and any(hit(label) for label in panel.get_xticklabels()):
                self.edit_axis_bounds("right_panel_x" if self._is_right_comparison_panel(panel) else "x")
                return
            if panel.yaxis.get_visible() and any(hit(label) for label in panel.get_yticklabels()):
                self.edit_axis_bounds(self._y_axis_key(panel))
                return
        if event.inaxes is not None:
            self._open_quick_labels()

    def _is_right_comparison_panel(self, panel):
        return (self.graph_model.comparison_panels and self.graph_model.layout_mode == "grid_1x2"
                and panel is self.plot_manager.axes[1])

    def _edit_right_panel_label(self, axis):
        field = f"right_panel_{axis}_title"
        title = f"Right panel {axis.upper()} label"
        text, accepted = QInputDialog.getText(self, title, title, text=getattr(self.graph_model, field))
        if accepted:
            setattr(self.graph_model, field, text.strip())
            self.refresh()
            self.labels_changed.emit()

    def _y_axis_key(self, panel):
        manager = self.plot_manager
        if self._is_right_comparison_panel(panel):
            return "right_panel_y"
        if panel is manager.ax2:
            return "y2"
        if panel is manager.ax_bottom and self.graph_model.layout_mode in {"stacked_2x1", "grid_2x1"}:
            return "y_bottom"
        return "y"

    def edit_axis_bounds(self, focus_axis=""):
        """Open the bounds editor for the axes drawn on this chart."""
        from omnigraph.ui.dialogs.axis_bounds_dialog import AxisBoundsDialog

        manager = self.plot_manager
        stacked = self.graph_model.layout_mode in {"stacked_2x1", "grid_2x1"}
        axes = [
            ("x", "Horizontal (X)", manager.ax, "x"),
            ("y", "Upper vertical (Y)" if stacked else "Vertical (Y)", manager.ax, "y"),
        ]
        if self.graph_model.comparison_panels and self.graph_model.layout_mode == "grid_1x2":
            axes = [
                ("x", "Left panel horizontal (X)", manager.ax, "x"),
                ("y", "Left panel vertical (Y)", manager.ax, "y"),
                ("right_panel_x", "Right panel horizontal (X)", manager.axes[1], "x"),
                ("right_panel_y", "Right panel vertical (Y)", manager.axes[1], "y"),
            ]
        if manager.ax2 is not None:
            axes.append(("y2", "Right vertical (Y)", manager.ax2, "y"))
        if stacked and manager.ax_bottom is not None:
            axes.append(("y_bottom", "Lower vertical (Y)", manager.ax_bottom, "y"))
        dialog = AxisBoundsDialog(self.graph_model, axes, focus_axis=focus_axis, parent=self)
        if dialog.exec():
            self.refresh()
            self.labels_changed.emit()

    def edit_bottom_y_title(self):
        text, ok = QInputDialog.getText(
            self, "Edit Lower Y-Axis Label", "Lower Y-Axis Label:", text=self.graph_model.y_bottom_title or "",
        )
        if ok:
            self.graph_model.y_bottom_title = text.strip()
            self.refresh()
            self.labels_changed.emit()

    def edit_graph_title(self):
        """Interactive prompt to edit graph title."""
        text, ok = QInputDialog.getText(
            self, "Edit Graph Title", "Graph Title:", text=self.graph_model.title_text or ""
        )
        if ok:
            self.graph_model.title_text = text.strip()
            self.refresh()
            self.labels_changed.emit()

    def edit_x_title(self):
        """Interactive prompt to edit X-axis title."""
        text, ok = QInputDialog.getText(
            self, "Edit X-Axis Label", "X-Axis Label (e.g. Wavelength (nm)):", text=self.graph_model.x_title or ""
        )
        if ok:
            self.graph_model.x_title = text.strip()
            self.refresh()
            self.labels_changed.emit()

    def edit_y_title(self):
        """Interactive prompt to edit Left Y-axis title."""
        text, ok = QInputDialog.getText(
            self, "Edit Y-Axis Label", "Left Y-Axis Label (e.g. Absorbance (a.u.)):", text=self.graph_model.y_title or ""
        )
        if ok:
            self.graph_model.y_title = text.strip()
            self.refresh()
            self.labels_changed.emit()

    def edit_y2_title(self):
        """Interactive prompt to edit Right Y-axis (Twin-Y) title."""
        text, ok = QInputDialog.getText(
            self, "Edit Right Y-Axis Label", "Right Y-Axis Label (Twin-Y):", text=self.graph_model.y2_title or ""
        )
        if ok:
            self.graph_model.y2_title = text.strip()
            self.refresh()
            self.labels_changed.emit()

    def open_legend_editor(self):
        """Opens Key & Legend Editor modal to quickly rename series labels and styling."""
        from omnigraph.ui.dialogs.legend_dialog import LegendEditorDialog
        try:
            def apply_legend():
                self.refresh()
                self.labels_changed.emit()
            dlg = LegendEditorDialog(self.graph_model, parent=self, on_apply_callback=apply_legend, project=self.project)
            if dlg.exec():
                self.refresh()
                self.labels_changed.emit()
        except Exception as e:
            print(f"Legend editor error: {e}")

    def _open_quick_labels(self):
        """Opens all-in-one QuickLabelsDialog."""
        from omnigraph.ui.dialogs.quick_labels_dialog import QuickLabelsDialog
        dlg = QuickLabelsDialog(self.graph_model, self)
        if dlg.exec():
            self.refresh()
            self.labels_changed.emit()

    def _toggle_legend(self):
        """Toggles legend visibility on/off."""
        self.graph_model.legend_show = not self.graph_model.legend_show
        self.refresh()
        self.labels_changed.emit()

    def _show_canvas_context_menu(self, event):
        """Interactive right-click menu with point masking, significance bracket, and styling."""
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QCursor
        menu = QMenu(self)

        note = self._note_at(event)
        if note is not None:
            annotation, _ = note
            menu.addAction("Edit text note…", lambda: self.request_annotation_edit.emit(annotation))
            menu.addAction("Remove text note", lambda: self.request_annotation_remove.emit(annotation))
        else:
            menu.addAction("Add text note here…", lambda: self.request_text_note.emit(self._note_location(event)))
        menu.addSeparator()

        pt = self.tool_manager.find_nearest_point(event.xdata, event.ydata)
        if pt:
            label, px, py, row_idx = pt[:4]
            is_m = pt[4] if len(pt) > 4 else False
            action = "Unselect Point (Include Again)" if is_m else "Select Point (Exclude)"
            act_text = f"{action} · Row {row_idx + 1} ({px:.4g}, {py:.4g}) [M]"
            menu.addAction(act_text, lambda: self.point_mask_toggled.emit(label, row_idx))
            menu.addSeparator()

        menu.addAction(
            "⭐ Add Significance Bracket (*, **, ns)...",
            lambda: self.request_significance_bracket.emit(
                float(event.xdata or 1.0),
                float(event.xdata or 1.0) + 1.0,
                float(event.ydata or 1.0),
            )
        )
        menu.addSeparator()

        if any(curve.is_fit_curve for curve in self.graph_model.curves) or any(
            ann.get("type") in {"band", "bracket", "significance"} for ann in self.graph_model.annotations
        ):
            menu.addAction("Analysis overlays…", self.request_manage_overlays.emit)

        # Quick direct label edits
        lbl_menu = menu.addMenu("✏️ Edit Labels & Titles")
        lbl_menu.addAction("🏷️ Edit Graph Title...", self.edit_graph_title)
        lbl_menu.addAction("↔️ Edit X-Axis Title...", self.edit_x_title)
        lbl_menu.addAction("↕️ Edit Left Y-Axis Title...", self.edit_y_title)
        if self.plot_manager.ax2 is not None or any(c.axis == "secondary" for c in self.graph_model.curves):
            lbl_menu.addAction("↕️ Edit Right Y-Axis Title...", self.edit_y2_title)
        lbl_menu.addSeparator()
        lbl_menu.addAction("✏️ Edit All Titles & Series Labels (Dialog)...", self._open_quick_labels)

        act_legend = menu.addAction("🔑 Edit Key / Legend Labels...")
        act_legend.triggered.connect(self.open_legend_editor)

        menu.addSeparator()

        is_shown = self.graph_model.legend_show
        toggle_text = "Hide Key / Legend" if is_shown else "Show Key / Legend"
        act_toggle = menu.addAction(f"👁️ {toggle_text}")
        act_toggle.triggered.connect(self._toggle_legend)

        menu.addSeparator()

        act_copy = menu.addAction("📋 Copy Graph Image (300 DPI)")
        act_copy.triggered.connect(lambda: self.copy_to_clipboard())

        menu.exec(QCursor.pos())

    def contextMenuEvent(self, event):
        """Interactive right-click context menu on graph canvas widget."""
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)

        # Quick direct label edits
        lbl_menu = menu.addMenu("✏️ Edit Labels & Titles")
        lbl_menu.addAction("🏷️ Edit Graph Title...", self.edit_graph_title)
        lbl_menu.addAction("↔️ Edit X-Axis Title...", self.edit_x_title)
        lbl_menu.addAction("↕️ Edit Left Y-Axis Title...", self.edit_y_title)
        if self.plot_manager.ax2 is not None or any(c.axis == "secondary" for c in self.graph_model.curves):
            lbl_menu.addAction("↕️ Edit Right Y-Axis Title...", self.edit_y2_title)
        lbl_menu.addSeparator()
        lbl_menu.addAction("✏️ Edit All Titles & Series Labels (Dialog)...", self._open_quick_labels)

        act_legend = menu.addAction("🔑 Edit Key / Legend Labels...")
        act_legend.triggered.connect(self.open_legend_editor)

        menu.addSeparator()

        is_shown = self.graph_model.legend_show
        toggle_text = "Hide Key / Legend" if is_shown else "Show Key / Legend"
        act_toggle = menu.addAction(f"👁️ {toggle_text}")
        act_toggle.triggered.connect(self._toggle_legend)

        menu.addSeparator()

        act_copy = menu.addAction("📋 Copy Graph Image (300 DPI)")
        act_copy.triggered.connect(lambda: self.copy_to_clipboard())

        menu.exec(event.globalPos())

    def copy_to_clipboard(self, width_in: float = 7.0, height_in: float = 5.0, dpi: int = 300) -> bool:
        """Copies graph image to the system clipboard at publication quality with full OS format compatibility."""
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QImage, QClipboard
        from PyQt6.QtCore import QMimeData, QByteArray

        png_bytes = self.plot_manager.export_png_bytes(
            dpi=dpi,
            transparent=False,
            width_in=width_in,
            height_in=height_in,
            pad_inches=0.15,
        )
        if not png_bytes:
            return False

        qimg = QImage()
        qimg.loadFromData(png_bytes)

        mime = QMimeData()
        # CF_DIB / CF_DIBV5 for Windows apps (Word, PowerPoint, Paint, Excel)
        mime.setImageData(qimg)
        # Standard PNG byte stream for web browsers, Google Docs, Slack, Discord
        mime.setData("image/png", QByteArray(png_bytes))

        clipboard = QApplication.clipboard()
        clipboard.setMimeData(mime, QClipboard.Mode.Clipboard)
        return True
