"""
High-performance Qt Figure Canvas for interactive scientific plotting.
Integrates Matplotlib with PyQt6, custom mouse navigation, and tool switching.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy, QInputDialog
from PyQt6.QtCore import pyqtSignal
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

from omnigraph.graphing.plot_manager import PlotManager
from omnigraph.graphing.tools import GraphToolManager
from omnigraph.core.project import GraphModel, Project


class OmniCanvas(QWidget):
    """Interactive canvas widget displaying a GraphModel."""

    coordinates_changed = pyqtSignal(float, float)  # (x, y) coordinates under mouse cursor
    point_inspected = pyqtSignal(str, float, float, int)  # curve, x, y, row
    range_selected = pyqtSignal(float, float)  # xmin, xmax
    labels_changed = pyqtSignal()  # emitted when title or axis labels are edited
    files_dropped = pyqtSignal(list)  # list of file paths dropped onto canvas
    point_mask_toggled = pyqtSignal(str, int)  # curve_label, row_idx
    request_significance_bracket = pyqtSignal(float, float, float)  # x1, x2, y

    def __init__(self, graph_model: GraphModel, project: Project, parent=None):
        super().__init__(parent)
        self.graph_model = graph_model
        self.project = project
        self._last_mouse_data = None
        self._last_inspected = None

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAcceptDrops(True)

        self.plot_manager = PlotManager(graph_model, project)
        self.canvas = FigureCanvas(self.plot_manager.fig)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

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
        self.canvas.mpl_connect("button_press_event", self._on_canvas_click)
        self.tool_manager.point_inspected.connect(self._on_point_inspected)
        self.tool_manager.range_selected.connect(self.range_selected)

        # Wire hotkey 'M' for point masking
        from PyQt6.QtGui import QKeySequence, QShortcut
        from PyQt6.QtCore import Qt
        self.shortcut_mask = QShortcut(QKeySequence(Qt.Key.Key_M), self)
        self.shortcut_mask.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_mask.activated.connect(self._toggle_mask_at_cursor)

        # Initial render
        self.refresh()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            paths = [u.toLocalFile() for u in urls if u.toLocalFile()]
            if paths:
                event.acceptProposedAction()
                self.files_dropped.emit(paths)
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
        self.plot_manager.render()
        self.tool_manager.ax = self.plot_manager.ax
        self.tool_manager.ax2 = self.plot_manager.ax2
        self.tool_manager.set_data_curves(self.plot_manager.rendered_curves)
        self.canvas.draw_idle()

    def set_tool(self, tool_name: str):
        """Switch canvas tool ('pointer', 'data_reader', 'range_selector')."""
        self.tool_manager.set_tool(tool_name)

    def _on_motion(self, event):
        if event.inaxes and event.xdata is not None and event.ydata is not None:
            self._last_mouse_data = (float(event.xdata), float(event.ydata))
            self.coordinates_changed.emit(float(event.xdata), float(event.ydata))

    def _on_canvas_click(self, event):
        """Direct in-place double-click label editing, right-click context menu, and legend detection."""
        # Handle Right-Click (Button 3) Context Menu
        if event.button == 3 and event.inaxes and event.xdata is not None and event.ydata is not None:
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

        # Normalized coordinates in figure [0, 1]
        width, height = self.canvas.get_width_height()
        if width <= 0 or height <= 0:
            return

        x_norm = event.x / width
        y_norm = event.y / height

        # 1. Top region -> Edit Graph Title
        if y_norm >= 0.78:
            self.edit_graph_title()
            return

        # 2. Bottom region -> Edit X-Axis Label
        if y_norm <= 0.22:
            self.edit_x_title()
            return

        # 3. Left region -> Edit Left Y-Axis Label
        if x_norm <= 0.22:
            self.edit_y_title()
            return

        # 4. Right region (if twin-x) -> Edit Right Y-Axis Label
        if x_norm >= 0.78 and self.plot_manager.ax2 is not None:
            self.edit_y2_title()
            return

        # 5. Middle plot area -> Open all-in-one QuickLabelsDialog
        self._open_quick_labels()

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
