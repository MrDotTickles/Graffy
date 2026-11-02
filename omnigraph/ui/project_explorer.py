"""
Project & Data Explorer dock widget.
Provides a clean, intuitive, 1-level grouped tree of:
- DATA TABLES (worksheets with column/row count badges)
- GRAPHS (plots with curve counts and plot type badges)
- REPORTS & RESULTS (fit and analysis results)
Features live search filtering, single-click instant navigation,
bidirectional active tab tracking, and rich context menus.
"""

from typing import Optional, List, Dict, Any
import os
import uuid
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QToolButton, QMenu, QInputDialog, QMessageBox, QHeaderView, QLineEdit,
    QApplication, QFileDialog, QLabel, QPushButton
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QFont, QColor, QBrush, QAction
from omnigraph.core.project import Project, GraphModel, ReportModel, CurveModel
from omnigraph.core.worksheet import Workbook, Worksheet, ColumnRole


class ProjectExplorerWidget(QWidget):
    """Modern, intuitive navigation tree for all project items."""

    # Navigation & item creation signals
    item_activated = pyqtSignal(str, str, str)  # (item_type: 'sheet'|'graph'|'report', item_id, parent_id)
    request_new_graph = pyqtSignal()
    request_new_sheet = pyqtSignal()
    request_ai_extract = pyqtSignal()
    request_new_project = pyqtSignal()
    request_open_project = pyqtSignal()
    request_save_project = pyqtSignal()
    request_rename_project = pyqtSignal()

    # Context action signals
    request_quick_plot = pyqtSignal(str, str, str)  # (sheet_name, parent_id, plot_type)
    request_duplicate_sheet = pyqtSignal(str, str)  # (sheet_name, parent_id)
    request_duplicate_graph = pyqtSignal(str)       # (graph_title)
    request_export_sheet = pyqtSignal(str, str)     # (sheet_name, parent_id)
    request_export_graph = pyqtSignal(str)          # (graph_title)
    request_export_report = pyqtSignal(str)         # (report_title)
    request_delete_sheet = pyqtSignal(str, str)     # (sheet_name, parent_id)
    request_delete_graph = pyqtSignal(str)          # (graph_title)
    request_delete_report = pyqtSignal(str)         # (report_title)
    request_rename_sheet = pyqtSignal(str, str)     # (sheet_name, parent_id)
    request_rename_graph = pyqtSignal(str)          # (graph_title)

    def __init__(self, project: Project, parent=None):
        super().__init__(parent)
        self.project = project
        self._init_ui()

    def sizeHint(self) -> QSize:
        return QSize(250, 600)

    def minimumSizeHint(self) -> QSize:
        return QSize(200, 380)

    def _is_dark_theme(self) -> bool:
        p = self.parent()
        while p:
            if hasattr(p, "is_dark_theme"):
                return bool(p.is_dark_theme)
            p = p.parent()
        return False

    def _refresh_status_label(self):
        if not hasattr(self, "lbl_project_status"):
            return
        if self.project.filepath:
            fname = os.path.basename(self.project.filepath)
            self.lbl_project_status.setText(f"💾 {fname}")
            self.lbl_project_status.setStyleSheet("font-size: 10px; color: #16a34a; font-weight: 500;")
        else:
            self.lbl_project_status.setText("● Unsaved Project")
            self.lbl_project_status.setStyleSheet("font-size: 10px; color: #ea580c; font-weight: 500;")

    def update_header(self):
        """Updates project title and save file status label."""
        if hasattr(self, "lbl_project_name"):
            self.lbl_project_name.setText(self.project.name)
        self._refresh_status_label()

    def set_project(self, project: Project):
        """Switches active project reference and rebuilds explorer view."""
        self.project = project
        self.update_header()
        self.populate_tree()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # 1. Project Title & File Card
        self.header_card = QWidget()
        self.header_card.setObjectName("ProjectHeaderCard")
        card_layout = QHBoxLayout(self.header_card)
        card_layout.setContentsMargins(8, 6, 6, 6)
        card_layout.setSpacing(6)

        lbl_icon = QLabel("📁")
        lbl_icon.setStyleSheet("font-size: 16px;")
        card_layout.addWidget(lbl_icon)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        self.lbl_project_name = QLabel(self.project.name)
        self.lbl_project_name.setStyleSheet("font-weight: bold; font-size: 12px;")
        self.lbl_project_status = QLabel()
        self._refresh_status_label()
        text_layout.addWidget(self.lbl_project_name)
        text_layout.addWidget(self.lbl_project_status)
        card_layout.addLayout(text_layout, 1)

        btn_proj_menu = QToolButton()
        btn_proj_menu.setText("⋮")
        btn_proj_menu.setToolTip("Project Actions (Rename, Save, Open)")
        btn_proj_menu.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        p_menu = QMenu(btn_proj_menu)
        p_menu.addAction("✏️ Rename Project...", self.request_rename_project.emit)
        p_menu.addAction("💾 Save Project", self.request_save_project.emit)
        p_menu.addSeparator()
        p_menu.addAction("📂 Open Project...", self.request_open_project.emit)
        p_menu.addAction("➕ New Project", self.request_new_project.emit)
        btn_proj_menu.setMenu(p_menu)
        card_layout.addWidget(btn_proj_menu)

        layout.addWidget(self.header_card)

        # 2. Quick Action Toolbar (1 Clean Row)
        tools_layout = QHBoxLayout()
        tools_layout.setSpacing(4)

        btn_add_sheet = QPushButton("➕ Sheet")
        btn_add_sheet.setToolTip("Add new worksheet to project")
        btn_add_sheet.clicked.connect(self.request_new_sheet.emit)
        tools_layout.addWidget(btn_add_sheet, 1)

        btn_add_graph = QPushButton("➕ Graph")
        btn_add_graph.setToolTip("Create new graph")
        btn_add_graph.clicked.connect(self.request_new_graph.emit)
        tools_layout.addWidget(btn_add_graph, 1)

        btn_refresh = QToolButton()
        btn_refresh.setText("🔄")
        btn_refresh.setToolTip("Refresh project explorer")
        btn_refresh.setStyleSheet("padding: 4px 8px; font-size: 13px;")
        btn_refresh.clicked.connect(self.populate_tree)
        tools_layout.addWidget(btn_refresh)

        layout.addLayout(tools_layout)

        # 2. Live Search & Filter Bar
        self.txt_search = QLineEdit(self)
        self.txt_search.setPlaceholderText("🔍 Filter items (e.g. Sheet, XRD, Fit)...")
        self.txt_search.setClearButtonEnabled(True)
        self.txt_search.textChanged.connect(self._filter_tree)
        layout.addWidget(self.txt_search)

        # 3. Flat Category Navigation Tree
        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tree.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)

        # Single click AND double click activate the item
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.tree)

        self.populate_tree()

    def _create_category_header(self, text: str, count: int) -> QTreeWidgetItem:
        header = QTreeWidgetItem(self.tree)
        header.setText(0, f"{text} ({count})")
        header.setFlags(Qt.ItemFlag.ItemIsEnabled)  # Clickable to expand/collapse, not selectable as a leaf
        font = header.font(0)
        font.setBold(True)
        font.setPointSize(9)
        header.setFont(0, font)

        dark = self._is_dark_theme()
        header_color = QColor("#89b4fa" if dark else "#0284c7")
        header.setForeground(0, QBrush(header_color))
        header.setExpanded(True)
        return header

    def populate_tree(self):
        """Rebuilds the flat, 1-level category tree from current Project state."""
        # Record currently selected item if any
        selected_data = None
        current = self.tree.currentItem()
        if current:
            selected_data = current.data(0, Qt.ItemDataRole.UserRole)

        self.tree.clear()

        # 1. DATA TABLES (Worksheets)
        sheets_count = sum(len(wb.sheets) for wb in self.project.workbooks)
        cat_data = self._create_category_header("📊  DATA TABLES", sheets_count)

        if sheets_count == 0:
            empty_item = QTreeWidgetItem(cat_data)
            empty_item.setText(0, "  (No worksheets yet)")
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
        else:
            multiple_wbs = len(self.project.workbooks) > 1
            for wb in self.project.workbooks:
                for ws in wb.sheets:
                    ws_item = QTreeWidgetItem(cat_data)
                    c_count = ws.column_count()
                    r_count = ws.row_count()

                    plotted_graphs = [g.title for g in self.project.graphs if any(c.source_sheet == ws.name for c in g.curves)]
                    plot_badge = f" ⇨ 📈 {', '.join(plotted_graphs)}" if plotted_graphs else ""

                    ws_item.setText(0, f"📄 {ws.name} ({c_count} cols){plot_badge}")
                    ws_item.setData(0, Qt.ItemDataRole.UserRole, ("sheet", ws.name, wb.name))

                    col_names = [c.display_label for c in ws.columns[:8]]
                    cols_str = ", ".join(col_names) + ("..." if len(ws.columns) > 8 else "")
                    plotted_str = f"\nPlotted in Graph(s): {', '.join(plotted_graphs)}" if plotted_graphs else "\nPlotted in: None"
                    ws_item.setToolTip(
                        0,
                        f"Worksheet: {ws.name}\n"
                        f"Workbook: {wb.name}\n"
                        f"Columns ({c_count}): {cols_str}\n"
                        f"Rows: {r_count}"
                        f"{plotted_str}\n\n"
                        "💡 Click to open • Right-click for Quick Plot & Options"
                    )

        # 2. GRAPHS (Plots)
        graphs_count = len(self.project.graphs)
        cat_graphs = self._create_category_header("📈  GRAPHS", graphs_count)

        if graphs_count == 0:
            empty_item = QTreeWidgetItem(cat_graphs)
            empty_item.setText(0, "  (No graphs yet - click + Graph)")
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
        else:
            for g in self.project.graphs:
                g_item = QTreeWidgetItem(cat_graphs)
                c_count = len(g.curves)
                curves_str = f"{c_count} curve{'s' if c_count != 1 else ''}"
                type_str = g.plot_type.replace("_", " ").capitalize()

                source_sheets = list(dict.fromkeys(c.source_sheet for c in g.curves if c.source_sheet))
                sheet_badge = f" ⇦ 📄 {', '.join(source_sheets)}" if source_sheets else ""

                g_item.setText(0, f"📈 {g.title} ({curves_str}{sheet_badge})")
                g_item.setData(0, Qt.ItemDataRole.UserRole, ("graph", g.title, g.id))

                curve_labels = [c.label for c in g.curves[:6]]
                curves_detail = ", ".join(curve_labels) + ("..." if c_count > 6 else "")
                src_str = f"\nLinked Source Sheet(s): {', '.join(source_sheets)}" if source_sheets else ""
                g_item.setToolTip(
                    0,
                    f"Graph: {g.title}\n"
                    f"Plot Type: {type_str}\n"
                    f"Curves ({c_count}): {curves_detail}"
                    f"{src_str}\n\n"
                    "💡 Click to open • Right-click to Add Layer, Duplicate & Export"
                )

        # 3. REPORTS & RESULTS (Analysis & Fit Reports)
        reports_count = len(self.project.reports)
        cat_reports = self._create_category_header("📋  REPORTS & RESULTS", reports_count)

        if reports_count == 0:
            empty_item = QTreeWidgetItem(cat_reports)
            empty_item.setText(0, "  (No reports yet - run Analysis)")
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
        else:
            for r in self.project.reports:
                r_item = QTreeWidgetItem(cat_reports)
                rep_type = r.report_type.capitalize() if r.report_type else "Fit"
                r_item.setText(0, f"📋 {r.title}")
                r_item.setData(0, Qt.ItemDataRole.UserRole, ("report", r.title, r.id))
                r_item.setToolTip(
                    0,
                    f"Report: {r.title}\n"
                    f"Type: {rep_type}\n\n"
                    "💡 Click to open • Right-click to Export"
                )

        # Re-apply any active search filter
        if hasattr(self, "txt_search") and self.txt_search.text():
            self._filter_tree(self.txt_search.text())

        # Restore previous selection
        if selected_data:
            self.highlight_item(selected_data[0], selected_data[1])

    def _filter_tree(self, query: str):
        """Live search filter across sheet names, graph titles, reports, and column metadata."""
        query = query.strip().lower()
        if not query:
            for i in range(self.tree.topLevelItemCount()):
                cat_item = self.tree.topLevelItem(i)
                cat_item.setHidden(False)
                for j in range(cat_item.childCount()):
                    cat_item.child(j).setHidden(False)
            return

        for i in range(self.tree.topLevelItemCount()):
            cat_item = self.tree.topLevelItem(i)
            visible_children = 0
            for j in range(cat_item.childCount()):
                child = cat_item.child(j)
                text = child.text(0).lower()
                tooltip = child.toolTip(0).lower()
                matches = (query in text) or (query in tooltip)
                child.setHidden(not matches)
                if matches:
                    visible_children += 1

            cat_item.setHidden(visible_children == 0)
            if visible_children > 0:
                cat_item.setExpanded(True)

    def highlight_item(self, item_type: str, item_id: str):
        """Highlights matching tree item without triggering recursive activations."""
        self.tree.blockSignals(True)
        try:
            for i in range(self.tree.topLevelItemCount()):
                cat_item = self.tree.topLevelItem(i)
                for j in range(cat_item.childCount()):
                    child = cat_item.child(j)
                    data = child.data(0, Qt.ItemDataRole.UserRole)
                    if data and data[0] == item_type and (data[1] == item_id or data[2] == item_id):
                        cat_item.setExpanded(True)
                        child.setHidden(False)
                        self.tree.setCurrentItem(child)
                        self.tree.scrollToItem(child)
                        return
        finally:
            self.tree.blockSignals(False)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        self._activate_item(item)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        self._activate_item(item)

    def _activate_item(self, item: QTreeWidgetItem):
        if not item:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            item_type, item_id, parent_id = data
            self.item_activated.emit(item_type, item_id, parent_id or "")

    def _on_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        menu = QMenu(self)

        if not item:
            # Blank space context menu
            menu.addAction("➕ Add Worksheet", self.request_new_sheet.emit)
            menu.addAction("➕ Create New Graph", self.request_new_graph.emit)
            menu.addAction("🤖 AI Smart Data Import & Plot...", self.request_ai_extract.emit)
            menu.addSeparator()
            menu.addAction("🔄 Refresh Explorer", self.populate_tree)
            menu.exec(self.tree.mapToGlobal(pos))
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            # Category header context menu
            header_text = item.text(0)
            if "DATA TABLES" in header_text:
                menu.addAction("➕ Add Worksheet", self.request_new_sheet.emit)
                menu.addAction("🤖 AI Smart Data Import & Plot...", self.request_ai_extract.emit)
            elif "GRAPHS" in header_text:
                menu.addAction("➕ Create New Graph", self.request_new_graph.emit)
            elif "REPORTS" in header_text:
                menu.addAction("🔄 Refresh Reports", self.populate_tree)
            menu.exec(self.tree.mapToGlobal(pos))
            return

        item_type, item_id, parent_id = data

        if item_type == "sheet":
            menu.addAction("📂 Open Worksheet", lambda: self.item_activated.emit("sheet", item_id, parent_id))

            plot_menu = menu.addMenu("📊 Quick Plot")
            plot_menu.addAction("Scatter Plot", lambda: self.request_quick_plot.emit(item_id, parent_id, "scatter"))
            plot_menu.addAction("Line Plot", lambda: self.request_quick_plot.emit(item_id, parent_id, "line"))
            plot_menu.addAction("Line + Symbol", lambda: self.request_quick_plot.emit(item_id, parent_id, "line_symbol"))
            plot_menu.addAction("Bar Chart", lambda: self.request_quick_plot.emit(item_id, parent_id, "bar"))
            plot_menu.addAction("Double Y-Axis (Twin Y)", lambda: self.request_quick_plot.emit(item_id, parent_id, "twin_x"))

            menu.addSeparator()
            menu.addAction("📋 Duplicate Sheet", lambda: self.request_duplicate_sheet.emit(item_id, parent_id))
            menu.addAction("✏️ Rename Sheet...", lambda: self.request_rename_sheet.emit(item_id, parent_id))
            menu.addAction("💾 Export as CSV...", lambda: self.request_export_sheet.emit(item_id, parent_id))
            menu.addSeparator()
            menu.addAction("🗑️ Delete Sheet", lambda: self.request_delete_sheet.emit(item_id, parent_id))

        elif item_type == "graph":
            menu.addAction("📂 Open Graph", lambda: self.item_activated.emit("graph", item_id, parent_id))
            menu.addAction("➕ Add Layer to Graph...", lambda: self._on_graph_action("add_layer", item_id))
            menu.addAction("✏️ Quick Labels Editor...", lambda: self._on_graph_action("edit_labels", item_id))
            menu.addSeparator()
            menu.addAction("📋 Duplicate Graph", lambda: self.request_duplicate_graph.emit(item_id))
            menu.addAction("✏️ Rename Graph...", lambda: self.request_rename_graph.emit(item_id))
            menu.addAction("🖼️ Export Graph (PNG, PDF, SVG)...", lambda: self.request_export_graph.emit(item_id))
            menu.addAction("📋 Copy to Clipboard", lambda: self._on_graph_action("copy", item_id))
            menu.addSeparator()
            menu.addAction("🗑️ Delete Graph", lambda: self.request_delete_graph.emit(item_id))

        elif item_type == "report":
            menu.addAction("📂 Open Report", lambda: self.item_activated.emit("report", item_id, parent_id))
            menu.addAction("💾 Export Report...", lambda: self.request_export_report.emit(item_id))
            menu.addSeparator()
            menu.addAction("🗑️ Delete Report", lambda: self.request_delete_report.emit(item_id))

        menu.exec(self.tree.mapToGlobal(pos))

    def _on_graph_action(self, action: str, graph_title: str):
        self.item_activated.emit("graph", graph_title, "")
        p = self.parent()
        while p:
            if hasattr(p, "open_add_layer_dialog") and action == "add_layer":
                p.open_add_layer_dialog()
                return
            elif hasattr(p, "open_quick_labels_dialog") and action == "edit_labels":
                p.open_quick_labels_dialog()
                return
            elif hasattr(p, "copy_active_graph") and action == "copy":
                p.copy_active_graph()
                return
            p = p.parent()

    # Fallback direct actions for standalone usage or tests
    def _rename_sheet(self, sheet_name: str, wb_name: str):
        self.request_rename_sheet.emit(sheet_name, wb_name)

    def _delete_sheet(self, sheet_name: str, wb_name: str):
        self.request_delete_sheet.emit(sheet_name, wb_name)

    def _rename_graph(self, title: str):
        self.request_rename_graph.emit(title)

    def _delete_graph(self, title: str):
        self.request_delete_graph.emit(title)

    def _delete_report(self, title: str):
        self.request_delete_report.emit(title)
