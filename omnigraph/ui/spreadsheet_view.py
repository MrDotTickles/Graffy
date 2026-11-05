"""
High-performance Origin-style spreadsheet view widget.
Features multi-attribute columns (Short Name, Long Name, Units, Role),
clipboard Copy/Paste, sorting, quick fills, formulas, context menus,
and native full-fidelity Undo/Redo (QUndoStack).
"""

import os
import inspect
import copy
import re
from itertools import groupby
from typing import Optional, List, Any
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView,
    QMenu, QMessageBox, QInputDialog, QLabel, QLineEdit,
    QToolButton, QAbstractItemView, QApplication, QStyledItemDelegate,
    QAbstractItemDelegate, QToolBar
)
from PyQt6.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, pyqtSignal, QEvent, QSize, QItemSelectionModel
)
from PyQt6.QtGui import QKeySequence, QColor, QBrush, QFont, QUndoStack

from omnigraph.ui.styles.design import icon
from omnigraph.core.worksheet import Worksheet, ColumnRole
from omnigraph.core.undo_manager import (
    CellEditCommand, FillColumnCommand,
    ClearColumnCommand, WorksheetSnapshotCommand
)
from omnigraph.core.clipboard_parser import ClipboardTableParser


class WorksheetTableModel(QAbstractTableModel):
    """Data model exposing Worksheet columns and rows to QTableView with Undo tracking."""

    def __init__(self, worksheet: Worksheet, undo_stack: Optional[QUndoStack] = None):
        super().__init__()
        self.worksheet = worksheet
        self.undo_stack = undo_stack

    def rowCount(self, parent=QModelIndex()) -> int:
        # An empty sheet has one editable entry row.
        return max(self.worksheet.row_count(), 1)

    def columnCount(self, parent=QModelIndex()) -> int:
        return self.worksheet.column_count()

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        col_idx = index.column()
        row_idx = index.row()
        col = self.worksheet.get_column(col_idx)
        if not col:
            return None

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            val = col.get_value(row_idx)
            if val is None or val == "":
                return ""
            if isinstance(val, float):
                # Clean representation
                return f"{val:.6g}" if role == Qt.ItemDataRole.DisplayRole else str(val)
            return str(val)

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            # Right align numbers, left align text
            val = col.get_value(row_idx)
            if isinstance(val, (int, float)):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        elif role == Qt.ItemDataRole.BackgroundRole:
            if col.is_row_masked(row_idx):
                return QBrush(QColor(254, 226, 226))  # Light red mask tint
            # Highlight alternating rows or role-based tint
            if col.role == ColumnRole.X:
                return QBrush(QColor(240, 249, 255, 40))
            elif col.role == ColumnRole.Y_ERR:
                return QBrush(QColor(254, 242, 242, 40))

        elif role == Qt.ItemDataRole.ForegroundRole:
            if col.is_row_masked(row_idx):
                return QBrush(QColor(220, 38, 38))  # Red text for masked points

        elif role == Qt.ItemDataRole.FontRole:
            if col.is_row_masked(row_idx):
                font = QFont()
                font.setStrikeOut(True)
                return font

        return None

    def setData(self, index: QModelIndex, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False

        col_idx = index.column()
        row_idx = index.row()
        col = self.worksheet.get_column(col_idx)
        if not col:
            return False

        old_val = col.get_value(row_idx)
        str_val = str(value).strip() if value is not None else ""
        if str_val == "":
            parsed_val = None
        else:
            try:
                # Try parsing as float
                parsed_val = float(str_val)
            except ValueError:
                parsed_val = str_val

        # If value didn't change, skip
        if parsed_val == old_val:
            return False

        def notify_edit():
            cell = self.index(row_idx, col_idx)
            if row_idx == 0:
                self.headerDataChanged.emit(Qt.Orientation.Vertical, 0, 0)
            self.dataChanged.emit(cell, cell, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])

        if self.undo_stack is not None:
            cmd = CellEditCommand(
                self.worksheet,
                row_idx,
                col_idx,
                old_val,
                parsed_val,
                callback=notify_edit,
            )
            self.undo_stack.push(cmd)
        else:
            col.set_value(row_idx, parsed_val)
            notify_edit()

        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal:
            col = self.worksheet.get_column(section)
            if not col:
                return None

            if role == Qt.ItemDataRole.DisplayRole:
                # Origin multi-line column header:
                # Line 1: Col Name (Role)
                # Line 2: Long Name
                # Line 3: [Units]
                parts = [f"{col.name} ({col.role.value})"]
                if col.long_name:
                    parts.append(col.long_name)
                if col.units:
                    parts.append(f"[{col.units}]")
                return "\n".join(parts)

            elif role == Qt.ItemDataRole.ToolTipRole:
                comments_info = f"\nComments: {col.comments}" if col.comments else ""
                formula_info = f"\nFormula: {col.formula}" if col.formula else ""
                return f"Column: {col.name}\nRole: {col.role.value}\nColumn Name: {col.display_label}\nUnits: {col.units}{comments_info}{formula_info}"

        elif orientation == Qt.Orientation.Vertical:
            if role == Qt.ItemDataRole.DisplayRole:
                return str(section + 1) if self.worksheet.row_count() else "+"
            if role == Qt.ItemDataRole.ToolTipRole and not self.worksheet.row_count():
                return "Type or paste into this row to start entering data."

        return None


class SpreadsheetItemDelegate(QStyledItemDelegate):
    """Delegate that intercepts pasting multi-cell table data while editing a cell."""

    def __init__(self, parent_widget: "SpreadsheetWidget"):
        super().__init__(parent_widget)
        self.parent_widget = parent_widget

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            editor.installEventFilter(self)
        return editor

    def eventFilter(self, editor, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.matches(QKeySequence.StandardKey.Paste) or (
                event.key() == Qt.Key.Key_V and event.modifiers() == Qt.KeyboardModifier.ControlModifier
            ):
                clipboard = QApplication.clipboard()
                mime = clipboard.mimeData()
                text = clipboard.text() or ""
                # If clipboard has table or multi-cell data, intercept and paste across cells!
                is_multi_cell = False
                if mime and mime.hasHtml() and ("<table" in mime.html().lower() or "<tr" in mime.html().lower()):
                    is_multi_cell = True
                elif "\n" in text or "\t" in text or ";" in text or "|" in text:
                    is_multi_cell = True
                elif "," in text and len(text.split(",")) > 1:
                    is_multi_cell = True
                elif len(re.split(r"\s{2,}|\s+", text.strip())) > 1:
                    is_multi_cell = True

                if is_multi_cell:
                    self.parent_widget.table_view.closeEditor(editor, QAbstractItemDelegate.EndEditHint.RevertModelCache)
                    self.parent_widget.paste_selection()
                    return True
        return super().eventFilter(editor, event)


class SpreadsheetTableView(QTableView):
    """TableView subclass with native keyboard shortcuts for Copy, Paste, Undo, Redo, and Clear."""

    def __init__(self, parent_widget: "SpreadsheetWidget"):
        super().__init__(parent_widget)
        self.parent_widget = parent_widget

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Paste) or (
            event.key() == Qt.Key.Key_V and event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            self.parent_widget.paste_selection()
            event.accept()
            return
        elif event.matches(QKeySequence.StandardKey.Copy) or (
            event.key() == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            self.parent_widget.copy_selection()
            event.accept()
            return
        elif event.matches(QKeySequence.StandardKey.Undo) or (
            event.key() == Qt.Key.Key_Z and event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            self.parent_widget.undo()
            event.accept()
            return
        elif event.matches(QKeySequence.StandardKey.Redo) or (
            event.key() == Qt.Key.Key_Y and event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            self.parent_widget.redo()
            event.accept()
            return
        elif event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.parent_widget.delete_selected_columns()
            event.accept()
            return
        elif event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.parent_widget.clear_selection()
            event.accept()
            return
        super().keyPressEvent(event)


class SpreadsheetWidget(QWidget):
    """Full-featured spreadsheet view with undo/redo, formulas, and column operations."""

    request_plot = pyqtSignal(str)  # plot_type
    column_role_changed = pyqtSignal(int, str)  # col_idx, role_value
    data_modified = pyqtSignal()
    selection_changed = pyqtSignal(list)  # list of selected column indexes
    request_add_to_active_graph = pyqtSignal(str)  # plot_type
    request_jump_to_graph = pyqtSignal(str)  # graph_title

    def __init__(self, worksheet: Worksheet, parent=None):
        super().__init__(parent)
        self.worksheet = worksheet
        self.undo_stack = QUndoStack(self)
        self.model = WorksheetTableModel(worksheet, undo_stack=self.undo_stack)
        self.model.dataChanged.connect(lambda: self.data_modified.emit())

        self._init_ui()

    def minimumSizeHint(self) -> QSize:
        base = super().minimumSizeHint()
        return QSize(min(base.width(), 150), base.height())

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Quick action bar at top using responsive QToolBar (handles overflow gracefully)
        self.toolbar = QToolBar("Worksheet Actions", self)
        self.toolbar.setObjectName("SpreadsheetActionToolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.setStyleSheet("QToolBar { border: none; padding: 2px 4px; background: transparent; }")

        self.rows_menu = QMenu(self)
        self.rows_menu.setTitle("Rows")
        self._add_row_actions(self.rows_menu)
        self.btn_rows = QToolButton(self)
        self.btn_rows.setText("Rows")
        self.btn_rows.setMenu(self.rows_menu)
        self.btn_rows.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.rows_toolbar_action = self.toolbar.addWidget(self.btn_rows)

        # Column editing tools placed directly above the sheet data columns
        self.act_sheet_add_col = self.toolbar.addAction("+ Col", self.add_column)
        self.act_sheet_add_col.setToolTip("Add new column to active worksheet")
        self.act_sheet_del_col = self.toolbar.addAction("- Col", self.delete_selected_columns)
        self.act_sheet_del_col.setToolTip("Delete currently selected column(s)")

        # Column Role dropdown properly added to worksheet local action toolbar adjacent to column tools
        self.btn_role = QToolButton()
        self.btn_role.setText("Set Role ▾")
        self.btn_role.setToolTip("Set role for selected column (X, Y, YErr, Label)")
        self.btn_role.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        role_menu = QMenu(self.btn_role)
        role_menu.addAction("Set as X (Independent)", lambda: self.set_selected_column_role(ColumnRole.X))
        role_menu.addAction("Set as Y (Dependent)", lambda: self.set_selected_column_role(ColumnRole.Y))
        role_menu.addAction("Set as Y Error (Uncertainty)", lambda: self.set_selected_column_role(ColumnRole.Y_ERR))
        role_menu.addAction("Set as Label (Text)", lambda: self.set_selected_column_role(ColumnRole.LABEL))
        role_menu.addAction("Disregard (Ignore)", lambda: self.set_selected_column_role(ColumnRole.DISREGARD))
        self.btn_role.setMenu(role_menu)
        self.toolbar.addWidget(self.btn_role)

        # Point / Cell Masking
        self.btn_mask = QToolButton()
        self.btn_mask.setText("Masking")
        self.btn_mask.setToolTip("Exclude cells from analysis or include them again")
        self.btn_mask.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        m_menu = QMenu(self.btn_mask)
        self._add_mask_actions(m_menu)
        self.btn_mask.setMenu(m_menu)
        self.toolbar.addWidget(self.btn_mask)

        self.toolbar.addSeparator()

        # Undo / Redo toolbar buttons
        self.btn_undo = QToolButton()
        self.btn_undo.setText("↶ Undo")
        self.btn_undo.setToolTip("Undo last change (Ctrl+Z)")
        self.btn_undo.setEnabled(False)
        self.btn_undo.clicked.connect(self.undo)
        self.toolbar.addWidget(self.btn_undo)

        self.btn_redo = QToolButton()
        self.btn_redo.setText("↷ Redo")
        self.btn_redo.setToolTip("Redo last undone change (Ctrl+Y)")
        self.btn_redo.setEnabled(False)
        self.btn_redo.clicked.connect(self.redo)
        self.toolbar.addWidget(self.btn_redo)

        self.undo_stack.canUndoChanged.connect(self._on_can_undo_changed)
        self.undo_stack.canRedoChanged.connect(self._on_can_redo_changed)

        self.toolbar.addSeparator()

        self.lbl_col_info = QLabel("Selected: None")
        self.lbl_col_info.setObjectName("SpreadsheetColInfo")
        self.lbl_col_info.setMinimumWidth(0)
        self.toolbar.addWidget(self.lbl_col_info)

        self.toolbar.addSeparator()
        lbl_plot_tag = QLabel("📈 Plotted in:")
        lbl_plot_tag.setObjectName("SpreadsheetPlotTag")
        self.toolbar.addWidget(lbl_plot_tag)

        self.btn_plotted_graph = QToolButton()
        self.btn_plotted_graph.setText("None")
        self.btn_plotted_graph.setToolTip("Graphs currently plotting columns from this worksheet")
        self.toolbar.addWidget(self.btn_plotted_graph)

        layout.addWidget(self.toolbar)

        # Table View
        self.table_view = SpreadsheetTableView(self)
        self.item_delegate = SpreadsheetItemDelegate(self)
        self.table_view.setItemDelegate(self.item_delegate)
        self.table_view.setModel(self.model)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table_view.horizontalHeader().setDefaultSectionSize(145)
        row_header = self.table_view.verticalHeader()
        row_header.setDefaultSectionSize(29)
        row_header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        row_header.customContextMenuRequested.connect(self._on_row_context_menu)
        row_header.setToolTip("Right-click a row number to insert or delete rows")
        self.table_view.horizontalHeader().setMinimumSectionSize(60)
        self.table_view.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.horizontalHeader().customContextMenuRequested.connect(self._on_header_context_menu)
        self.table_view.horizontalHeader().sectionDoubleClicked.connect(self.edit_column_properties)
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._on_cell_context_menu)
        self.table_view.selectionModel().selectionChanged.connect(self._on_selection_changed)

        # Wire hotkey 'M'
        from PyQt6.QtGui import QShortcut
        self.shortcut_mask = QShortcut(QKeySequence(Qt.Key.Key_M), self)
        self.shortcut_mask.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_mask.activated.connect(self.mask_selection)

        layout.addWidget(self.table_view)

    def enable_guided_sheet(self):
        """Keep the data table readable and expose editing tools on demand."""
        if hasattr(self, "starter_panel"):
            return
        from PyQt6.QtWidgets import QFrame, QPushButton
        self.toolbar.hide()
        header = QWidget()
        header.setObjectName("SheetHeader")
        row = QHBoxLayout(header)
        row.setContentsMargins(12,10,12,10)
        heading = QLabel(self.worksheet.name)
        heading.setProperty("role","heading")
        row.addWidget(heading)
        self.sheet_summary = QLabel()
        self.sheet_summary.setProperty("role","muted")
        row.addWidget(self.sheet_summary)
        row.addStretch()
        rows_button = QPushButton("Rows", header)
        rows_button.setMenu(self.rows_menu)
        row.addWidget(rows_button)
        self.rows_toolbar_action.setVisible(False)
        self.sheet_tools_toggle = QPushButton("Column tools")
        self.sheet_tools_toggle.setIcon(icon("edit"))
        self.sheet_tools_toggle.setCheckable(True)
        self.sheet_tools_toggle.toggled.connect(self.toolbar.setVisible)
        row.addWidget(self.sheet_tools_toggle)
        self.layout().insertWidget(0,header)
        self.starter_panel = QFrame()
        self.starter_panel.setObjectName("WorksheetStarterPanel")
        content = QVBoxLayout(self.starter_panel)
        content.setContentsMargins(24,22,24,22)
        content.setSpacing(12)
        heading = QLabel("Bring your data into focus")
        heading.setProperty("role","heading")
        content.addWidget(heading)
        hint = QLabel("Import a file or paste cells from Excel. You can also type directly into the table below.")
        hint.setProperty("role","muted")
        hint.setWordWrap(True)
        content.addWidget(hint)
        buttons = QHBoxLayout()
        import_button = QPushButton("Import data…")
        import_button.setIcon(icon("import","#ffffff"))
        import_button.setProperty("role","primary")
        import_button.clicked.connect(lambda: self.window().import_data() if hasattr(self.window(),"import_data") else None)
        paste_button = QPushButton("Paste cells")
        paste_button.clicked.connect(self.paste_selection)
        buttons.addWidget(import_button)
        buttons.addWidget(paste_button)
        buttons.addStretch()
        content.addLayout(buttons)
        self.layout().insertWidget(1,self.starter_panel)
        self.data_modified.connect(self._refresh_starter_panel)
        self._refresh_starter_panel()

    def _refresh_starter_panel(self):
        if hasattr(self,"starter_panel"):
            has_data = any(any(v is not None and str(v).strip() for v in c.data) for c in self.worksheet.columns)
            self.starter_panel.setVisible(not has_data)
            rows = self.worksheet.row_count()
            columns = self.worksheet.column_count()
            row_label = "row" if rows == 1 else "rows"
            column_label = "column" if columns == 1 else "columns"
            self.sheet_summary.setText(f"{rows:,} {row_label} · {columns} {column_label}")

    def _on_can_undo_changed(self, can_undo: bool):
        self.btn_undo.setEnabled(can_undo)
        if can_undo:
            self.btn_undo.setToolTip(f"Undo: {self.undo_stack.undoText()} (Ctrl+Z)")
        else:
            self.btn_undo.setToolTip("Undo (Ctrl+Z)")

    def _on_can_redo_changed(self, can_redo: bool):
        self.btn_redo.setEnabled(can_redo)
        if can_redo:
            self.btn_redo.setToolTip(f"Redo: {self.undo_stack.redoText()} (Ctrl+Y)")
        else:
            self.btn_redo.setToolTip("Redo (Ctrl+Y)")

    def update_linked_graphs(self, graphs: list):
        """Updates the toolbar indicator showing which graphs plot this worksheet."""
        if not hasattr(self, "btn_plotted_graph"):
            return
        linked = [g for g in graphs if any(c.source_sheet == self.worksheet.name for c in g.curves)]
        if not linked:
            self.btn_plotted_graph.setText("None")
            self.btn_plotted_graph.setToolTip("No graphs currently plot data from this worksheet.")
            self.btn_plotted_graph.setEnabled(False)
            self.btn_plotted_graph.setMenu(None)
        elif len(linked) == 1:
            g = linked[0]
            self.btn_plotted_graph.setText(f"📈 {g.title} ↗")
            self.btn_plotted_graph.setToolTip(f"Jump to graph '{g.title}' plotting this data")
            self.btn_plotted_graph.setEnabled(True)
            self.btn_plotted_graph.setMenu(None)
            try:
                self.btn_plotted_graph.clicked.disconnect()
            except Exception:
                pass
            self.btn_plotted_graph.clicked.connect(lambda checked=False, t=g.title: self.request_jump_to_graph.emit(t))
        else:
            self.btn_plotted_graph.setText(f"📈 {len(linked)} Graphs ▾")
            self.btn_plotted_graph.setToolTip(f"{len(linked)} graphs plot this worksheet: {', '.join(g.title for g in linked)}")
            self.btn_plotted_graph.setEnabled(True)
            self.btn_plotted_graph.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            menu = QMenu(self.btn_plotted_graph)
            for g in linked:
                menu.addAction(f"📈 {g.title}", lambda t=g.title: self.request_jump_to_graph.emit(t))
            self.btn_plotted_graph.setMenu(menu)

    def undo(self):
        """Undoes last worksheet operation."""
        if self.undo_stack.canUndo():
            desc = self.undo_stack.undoText()
            self.undo_stack.undo()
            self.refresh_view()
            self._notify_data_modified(f"Undid: {desc}")

    def redo(self):
        """Redoes last undone worksheet operation."""
        if self.undo_stack.canRedo():
            desc = self.undo_stack.redoText()
            self.undo_stack.redo()
            self.refresh_view()
            self._notify_data_modified(f"Redid: {desc}")

    def _notify_data_modified(self, status_msg: Optional[str] = None):
        self.data_modified.emit()
        win = self.window()
        if hasattr(win, "_on_sheet_data_modified"):
            win._on_sheet_data_modified()
        if status_msg and hasattr(win, "statusBar") and win.statusBar():
            win.statusBar().showMessage(status_msg, 3000)

    def refresh_view(self):
        """Notifies the table view of changes in data or columns."""
        self.model.beginResetModel()
        self.model.endResetModel()
        self.data_modified.emit()

    def get_selected_column_index(self) -> int:
        indexes = self.table_view.selectionModel().selectedIndexes()
        if indexes:
            return indexes[0].column()
        return 0

    def get_selected_column_indexes(self) -> List[int]:
        indexes = self.table_view.selectionModel().selectedIndexes()
        cols = sorted(list(set(idx.column() for idx in indexes)))
        return cols

    def _on_selection_changed(self):
        indexes = self.table_view.selectionModel().selectedIndexes()
        if not indexes:
            self.lbl_col_info.setText("Selected: None")
            if hasattr(self, "act_sheet_del_col"):
                self.act_sheet_del_col.setToolTip("Delete currently selected column(s)")
            self.selection_changed.emit([])
            return

        cols = sorted(list(set(idx.column() for idx in indexes)))
        if len(cols) == 1:
            col = self.worksheet.get_column(cols[0])
            if col:
                col_name_label = f"'{col.name}: {col.display_label}'" if col.display_label and col.display_label != col.name else f"'{col.name}'"
                self.lbl_col_info.setText(f"Col {col.name} ({col.role.value}): {col.display_label}")
                if hasattr(self, "act_sheet_del_col"):
                    self.act_sheet_del_col.setToolTip(f"Delete column {col_name_label} (Shift+Del)")
        else:
            col_names = [self.worksheet.get_column(c).name for c in cols if self.worksheet.get_column(c)]
            self.lbl_col_info.setText(f"Selected {len(cols)} Columns: {', '.join(col_names)}")
            if hasattr(self, "act_sheet_del_col"):
                self.act_sheet_del_col.setToolTip(f"Delete {len(cols)} selected columns ({', '.join(col_names)}) (Shift+Del)")

        self.selection_changed.emit(cols)

    def _add_row_actions(self, menu: QMenu):
        set_count = menu.addAction("Set Row Count…", self.set_row_count)
        append = menu.addAction("Add Rows at End…", self.add_rows)
        menu.addSeparator()
        insert = menu.addAction("Insert Row Above", self.insert_row_above)
        delete = menu.addAction("Delete Selected Rows", self.delete_selected_rows)

        def update_actions():
            has_columns = self.worksheet.column_count() > 0
            has_rows_selected = self.worksheet.row_count() > 0 and self.table_view.selectionModel().hasSelection()
            set_count.setEnabled(has_columns)
            append.setEnabled(has_columns)
            insert.setEnabled(has_rows_selected)
            delete.setEnabled(has_rows_selected)

        menu.aboutToShow.connect(update_actions)

    def _selected_rows(self) -> List[int]:
        selection = self.table_view.selectionModel().selection()
        row_count = self.worksheet.row_count()
        return sorted({
            row
            for span in selection
            for row in range(span.top(), min(span.bottom() + 1, row_count))
        })

    def _on_row_context_menu(self, pos):
        header = self.table_view.verticalHeader()
        row = header.logicalIndexAt(pos)
        if row < 0:
            return
        if not any(span.top() <= row <= span.bottom() for span in self.table_view.selectionModel().selection()):
            self.table_view.selectRow(row)
        self.rows_menu.exec(header.mapToGlobal(pos))

    def set_row_count(self):
        if not self.worksheet.column_count():
            return
        current = self.worksheet.row_count()
        count, accepted = QInputDialog.getInt(
            self, "Set Row Count", "Total rows in this worksheet:", current, 0, max(current, 1_000_000)
        )
        if not accepted or count == current:
            return
        if count > current:
            self._insert_rows(current, count - current, "Set Row Count")
        else:
            self._delete_row_ranges([(count, current - count)], "Set Row Count")

    def add_rows(self):
        if not self.worksheet.column_count():
            return
        count, accepted = QInputDialog.getInt(
            self, "Add Rows", "Blank rows to add at the end:", 1, 1, 100_000
        )
        if accepted:
            self._insert_rows(self.worksheet.row_count(), count, "Add Rows")

    def insert_row_above(self):
        rows = self._selected_rows()
        if rows:
            self._insert_rows(rows[0], 1, "Insert Row")

    def delete_selected_rows(self):
        ranges = []
        for _, group in groupby(enumerate(self._selected_rows()), key=lambda pair: pair[1] - pair[0]):
            rows = [row for _, row in group]
            ranges.append((rows[0], len(rows)))
        if ranges:
            self._delete_row_ranges(ranges, "Delete Rows")

    def _insert_rows(self, first: int, count: int, action: str):
        before = copy.deepcopy(self.worksheet.to_dict())
        self.worksheet.insert_rows(first, count)
        self._record_row_change(before, action)
        self.table_view.setCurrentIndex(self.model.index(first, 0))

    def _delete_row_ranges(self, ranges: list[tuple[int, int]], action: str):
        has_data = any(
            value is not None and value != ""
            for col in self.worksheet.columns
            for first, count in ranges
            for value in col.data[first:first + count]
        )
        if has_data:
            total = sum(count for _, count in ranges)
            answer = QMessageBox.question(
                self, "Delete Worksheet Rows",
                f"Delete {total:,} {'row' if total == 1 else 'rows'}, including the data? "
                "You can undo this change.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        before = copy.deepcopy(self.worksheet.to_dict())
        for first, count in reversed(ranges):
            self.worksheet.delete_rows(first, count)
        self._record_row_change(before, action)
        row = min(ranges[0][0], self.model.rowCount() - 1)
        self.table_view.setCurrentIndex(self.model.index(row, 0))

    def _record_row_change(self, before, action: str):
        self.undo_stack.push(WorksheetSnapshotCommand(
            self.worksheet, before, self.worksheet.to_dict(), action, callback=self.refresh_view
        ))

    def add_column(self):
        before = copy.deepcopy(self.worksheet.to_dict())
        self.worksheet.add_column()
        after = copy.deepcopy(self.worksheet.to_dict())
        cmd = WorksheetSnapshotCommand(self.worksheet, before, after, "Add Column", callback=self.refresh_view)
        self.undo_stack.push(cmd)
        self._notify_data_modified("Added new column")

    def set_selected_column_role(self, role: ColumnRole):
        col_idx = self.get_selected_column_index()
        col = self.worksheet.get_column(col_idx)
        if col and col.role != role:
            before = copy.deepcopy(self.worksheet.to_dict())
            col.role = role
            after = copy.deepcopy(self.worksheet.to_dict())
            cmd = WorksheetSnapshotCommand(
                self.worksheet, before, after, f"Set Col({col.name}) as {role.value}", callback=self.refresh_view
            )
            self.undo_stack.push(cmd)
            self.column_role_changed.emit(col_idx, role.value)
            self._notify_data_modified(f"Set Col({col.name}) role to {role.value}")

    def _on_header_context_menu(self, pos):
        col_idx = self.table_view.horizontalHeader().logicalIndexAt(pos)
        if col_idx < 0:
            return

        menu = QMenu(self)
        col = self.worksheet.get_column(col_idx)
        title = f"Column {col.name}" if col else f"Column {col_idx+1}"
        menu.addSection(title)

        # Roles submenu
        role_menu = menu.addMenu("Set Column Role")
        role_menu.addAction("X (Independent Variable)", lambda: self._set_role(col_idx, ColumnRole.X))
        role_menu.addAction("Y (Dependent Variable)", lambda: self._set_role(col_idx, ColumnRole.Y))
        role_menu.addAction("Y Error (Uncertainty)", lambda: self._set_role(col_idx, ColumnRole.Y_ERR))
        role_menu.addAction("Label (Text Annotations)", lambda: self._set_role(col_idx, ColumnRole.LABEL))
        role_menu.addAction("Disregard (Ignore)", lambda: self._set_role(col_idx, ColumnRole.DISREGARD))

        menu.addSeparator()
        menu.addAction("Set Column Values (Formula)...", lambda: self.open_formula_dialog(col_idx))
        menu.addAction("Column Properties...", lambda: self.edit_column_properties(col_idx))
        menu.addAction("Column Statistics...", lambda: self.show_column_stats(col_idx))

        menu.addSeparator()
        fill_menu = menu.addMenu("Quick Fill")
        fill_menu.addAction("Row Numbers (1..N)", lambda: self._fill_col(col_idx, "seq"))
        fill_menu.addAction("Uniform Random [0, 1]", lambda: self._fill_col(col_idx, "uniform"))
        fill_menu.addAction("Normal Random (μ=0, σ=1)", lambda: self._fill_col(col_idx, "normal"))

        menu.addSeparator()
        sort_menu = menu.addMenu("Sort Worksheet")
        sort_menu.addAction("Ascending (A → Z, 1 → 9)", lambda: self._sort_sheet(col_idx, True))
        sort_menu.addAction("Descending (Z → A, 9 → 1)", lambda: self._sort_sheet(col_idx, False))

        menu.addSeparator()
        menu.addAction("📋 Paste Table Starting Here", lambda: self._paste_at_col(col_idx))
        menu.addAction("Insert Column Before", lambda: self._insert_col(col_idx))
        selected_cols = self.get_selected_column_indexes()
        if len(selected_cols) > 1 and col_idx in selected_cols:
            col_names = [self.worksheet.get_column(c).name for c in selected_cols if self.worksheet.get_column(c)]
            menu.addAction(f"Delete Selected Columns ({', '.join(col_names)})", self.delete_selected_columns)
        else:
            col = self.worksheet.get_column(col_idx)
            col_desc = f"'{col.name}: {col.display_label}'" if col and col.display_label and col.display_label != col.name else f"'{col.name}'" if col else f"Column {col_idx+1}"
            menu.addAction(f"Delete Column {col_desc}", lambda: self.delete_selected_columns([col_idx]))
        menu.addAction("Clear Column Data", lambda: self._clear_col(col_idx))

        menu.exec(self.table_view.horizontalHeader().mapToGlobal(pos))

    def _paste_at_col(self, col_idx: int):
        """Pastes table from clipboard starting at row 0 of specified column."""
        idx = self.model.index(0, col_idx)
        self.table_view.setCurrentIndex(idx)
        self.paste_selection()

    def _on_cell_context_menu(self, pos):
        index = self.table_view.indexAt(pos)
        menu = QMenu(self)

        menu.addAction("↶ Undo", self.undo)
        menu.actions()[-1].setEnabled(self.undo_stack.canUndo())
        menu.addAction("↷ Redo", self.redo)
        menu.actions()[-1].setEnabled(self.undo_stack.canRedo())
        menu.addSeparator()

        menu.addAction("Copy Selection (Ctrl+C)", self.copy_selection)

        paste_menu = menu.addMenu("📋 Paste Table / Data")
        paste_menu.addAction("Smart Paste (Detect Headers & Split Columns) [Ctrl+V]", self.paste_selection)
        paste_menu.addAction("Paste with First Row as Headers", lambda: self.paste_selection(force_headers=True))
        paste_menu.addAction("Paste Directly into Cells (Raw)", lambda: self.paste_selection(force_raw=True))

        menu.addAction("Clear Cells (Del)", self.clear_selection)
        if index.isValid():
            selection = self.table_view.selectionModel()
            if not selection.isSelected(index):
                self.table_view.setCurrentIndex(index)
            menu.addMenu(self.rows_menu)
        selected_cols = self.get_selected_column_indexes()
        if len(selected_cols) > 1:
            col_names = [self.worksheet.get_column(c).name for c in selected_cols if self.worksheet.get_column(c)]
            menu.addAction(f"Delete Selected Columns ({', '.join(col_names)})", self.delete_selected_columns)
        elif len(selected_cols) == 1:
            c = self.worksheet.get_column(selected_cols[0])
            c_desc = f"'{c.name}: {c.display_label}'" if c and c.display_label and c.display_label != c.name else f"'{c.name}'" if c else ""
            menu.addAction(f"Delete Column {c_desc}", self.delete_selected_columns)
        else:
            menu.addAction("Delete Selected Column(s)", self.delete_selected_columns)
        menu.addSeparator()

        if index.isValid():
            col_idx = index.column()
            menu.addAction("Set Column Values (Formula)...", lambda: self.open_formula_dialog(col_idx))
            menu.addAction("Column Statistics...", lambda: self.show_column_stats(col_idx))

        menu.addSeparator()
        self._add_mask_actions(menu)

        menu.exec(self.table_view.viewport().mapToGlobal(pos))

    def _set_role(self, col_idx: int, role: ColumnRole):
        col = self.worksheet.get_column(col_idx)
        if col and col.role != role:
            before = copy.deepcopy(self.worksheet.to_dict())
            col.role = role
            after = copy.deepcopy(self.worksheet.to_dict())
            cmd = WorksheetSnapshotCommand(
                self.worksheet, before, after, f"Set Col({col.name}) as {role.value}", callback=self.refresh_view
            )
            self.undo_stack.push(cmd)
            self.column_role_changed.emit(col_idx, role.value)
            self._notify_data_modified()

    def _fill_col(self, col_idx: int, fill_type: str):
        col = self.worksheet.get_column(col_idx)
        if not col:
            return
        old_data = list(col.data)
        n = self.worksheet.row_count() or 50
        if fill_type == "seq":
            new_data = [float(i + 1) for i in range(n)]
        elif fill_type == "uniform":
            new_data = [float(v) for v in np.random.uniform(0.0, 1.0, size=n)]
        elif fill_type == "normal":
            new_data = [float(v) for v in np.random.normal(0.0, 1.0, size=n)]
        else:
            return

        cmd = FillColumnCommand(
            self.worksheet, col_idx, old_data, new_data, fill_type, callback=self.refresh_view
        )
        self.undo_stack.push(cmd)
        self._notify_data_modified(f"Filled Col({col.name}) with {fill_type}")

    def _sort_sheet(self, col_idx: int, ascending: bool):
        before = copy.deepcopy(self.worksheet.to_dict())
        self.worksheet.sort_by_column(col_idx, ascending=ascending)
        after = copy.deepcopy(self.worksheet.to_dict())
        col = self.worksheet.get_column(col_idx)
        col_name = col.name if col else f"Col {col_idx+1}"
        dir_str = "Asc" if ascending else "Desc"
        cmd = WorksheetSnapshotCommand(
            self.worksheet, before, after, f"Sort by {col_name} ({dir_str})", callback=self.refresh_view
        )
        self.undo_stack.push(cmd)
        self._notify_data_modified()

    def _insert_col(self, col_idx: int):
        before = copy.deepcopy(self.worksheet.to_dict())
        self.worksheet.insert_column(col_idx)
        after = copy.deepcopy(self.worksheet.to_dict())
        cmd = WorksheetSnapshotCommand(self.worksheet, before, after, "Insert Column", callback=self.refresh_view)
        self.undo_stack.push(cmd)
        self._notify_data_modified()

    def delete_selected_columns(self, col_indices: Optional[Any] = None, confirm: Optional[bool] = None):
        """Deletes selected columns with visual selection highlight, confirmation prompt, and undo/redo snapshot tracking."""
        if col_indices is None or isinstance(col_indices, bool):
            col_indices = self.get_selected_column_indexes()
            if not col_indices:
                col_indices = [self.get_selected_column_index()]
        elif isinstance(col_indices, int):
            col_indices = [col_indices]

        valid_indices = sorted(list(set(i for i in col_indices if i is not None and 0 <= i < self.worksheet.column_count())), reverse=True)
        if not valid_indices:
            return

        if len(valid_indices) >= self.worksheet.column_count():
            QMessageBox.warning(self, "Warning", "Worksheet must retain at least one column.")
            return

        # Ensure visual selection clearly highlights the entire column(s) being deleted
        self.table_view.clearSelection()
        for idx in valid_indices:
            self.table_view.selectionModel().select(
                self.model.index(0, idx),
                QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Columns
            )
        self._on_selection_changed()
        QApplication.processEvents()

        cols = [self.worksheet.get_column(i) for i in reversed(valid_indices) if self.worksheet.get_column(i)]
        if len(cols) == 1:
            c = cols[0]
            col_desc = f"'{c.name}: {c.display_label}'" if c.display_label and c.display_label != c.name else f"'{c.name}'"
            prompt_text = f"Delete column {col_desc}?\n\nThis action can be undone with Ctrl+Z."
        else:
            descs = [f"'{c.name}: {c.display_label}'" if c.display_label and c.display_label != c.name else f"'{c.name}'" for c in cols]
            prompt_text = f"Delete {len(cols)} columns ({', '.join(descs)})?\n\nThis action can be undone with Ctrl+Z."

        # Confirmation prompt handling
        should_prompt = confirm
        if should_prompt is None:
            is_offscreen_unmocked = (
                os.environ.get("QT_QPA_PLATFORM") == "offscreen"
                and inspect.isbuiltin(QMessageBox.question)
            )
            should_prompt = not is_offscreen_unmocked

        if should_prompt:
            reply = QMessageBox.question(
                self,
                "Confirm Delete Column",
                prompt_text,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                win = self.window()
                if hasattr(win, "statusBar") and win.statusBar():
                    win.statusBar().showMessage("Column deletion cancelled", 3000)
                return

        names = [c.name for c in cols]
        names_str = ", ".join(names)

        before = copy.deepcopy(self.worksheet.to_dict())
        for idx in valid_indices:
            self.worksheet.remove_column(idx)
        after = copy.deepcopy(self.worksheet.to_dict())

        title = f"Delete Column(s) ({names_str})" if len(names) > 1 else f"Delete Col({names_str})"
        cmd = WorksheetSnapshotCommand(self.worksheet, before, after, title, callback=self.refresh_view)
        self.undo_stack.push(cmd)
        self.refresh_view()

        if len(cols) == 1:
            c = cols[0]
            col_desc = f"'{c.name}: {c.display_label}'" if c.display_label and c.display_label != c.name else f"'{c.name}'"
            self._notify_data_modified(f"Deleted column {col_desc}")
        else:
            self._notify_data_modified(f"Deleted {len(cols)} columns ({names_str})")

    def _delete_col(self, col_idx: int):
        self.delete_selected_columns([col_idx])

    def set_zoom(self, zoom: float):
        """Scales default section size, row height, and table view layout with zoom level."""
        section_size = max(50, int(110 * zoom))
        row_size = max(20, int(26 * zoom))
        self.table_view.horizontalHeader().setDefaultSectionSize(section_size)
        self.table_view.verticalHeader().setDefaultSectionSize(row_size)
        self.refresh_view()

    def _clear_col(self, col_idx: int):
        col = self.worksheet.get_column(col_idx)
        if col:
            old_data = list(col.data)
            cmd = ClearColumnCommand(self.worksheet, col_idx, old_data, callback=self.refresh_view)
            self.undo_stack.push(cmd)
            self._notify_data_modified(f"Cleared Col({col.name})")

    def edit_column_properties(self, col_idx: Optional[int] = None):
        if col_idx is None:
            col_idx = self.get_selected_column_index()
        col = self.worksheet.get_column(col_idx)
        if not col:
            return

        from omnigraph.ui.dialogs.column_prop_dialog import ColumnPropertiesDialog
        before = copy.deepcopy(self.worksheet.to_dict())
        dlg = ColumnPropertiesDialog(col, self)
        if dlg.exec():
            after = copy.deepcopy(self.worksheet.to_dict())
            cmd = WorksheetSnapshotCommand(
                self.worksheet, before, after, f"Edit Properties of Col({col.name})", callback=self.refresh_view
            )
            self.undo_stack.push(cmd)
            self.refresh_view()
            self._notify_data_modified()

    def open_formula_dialog(self, col_idx: Optional[int] = None):
        if col_idx is None:
            col_idx = self.get_selected_column_index()
        from omnigraph.ui.dialogs.formula_dialog import FormulaDialog
        dlg = FormulaDialog(self.worksheet, col_idx, undo_stack=self.undo_stack, parent=self)
        if dlg.exec():
            self.refresh_view()
            self._notify_data_modified("Formula applied")

    def show_column_stats(self, col_idx: Optional[int] = None):
        if col_idx is None:
            col_idx = self.get_selected_column_index()
        col = self.worksheet.get_column(col_idx)
        if not col:
            return
        from omnigraph.ui.dialogs.stats_dialog import StatsDialog
        dlg = StatsDialog([col], self)
        dlg.exec()

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Undo):
            self.undo()
            event.accept()
        elif event.matches(QKeySequence.StandardKey.Redo):
            self.redo()
            event.accept()
        elif event.matches(QKeySequence.StandardKey.Copy):
            self.copy_selection()
            event.accept()
        elif event.matches(QKeySequence.StandardKey.Paste):
            self.paste_selection()
            event.accept()
        elif event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.delete_selected_columns()
            event.accept()
        elif event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.clear_selection()
            event.accept()
        else:
            super().keyPressEvent(event)

    def copy_selection(self):
        """Copies selected cells as TSV text to clipboard."""
        selection = self.table_view.selectionModel().selectedIndexes()
        if not selection:
            return

        rows = sorted(list(set(idx.row() for idx in selection)))
        cols = sorted(list(set(idx.column() for idx in selection)))

        lines = []
        for r in rows:
            row_vals = []
            for c in cols:
                val = self.worksheet.get_cell(r, c)
                row_vals.append("" if val is None else str(val))
            lines.append("\t".join(row_vals))

        tsv_data = "\n".join(lines)
        QApplication.clipboard().setText(tsv_data)

    def paste_selection(self, force_headers: bool = False, force_raw: bool = False):
        """
        Intelligently pastes tables from clipboard (HTML, TSV, CSV, space-delimited, Markdown).
        Ensures external tables are distributed into rows and columns, never dumping into a single cell.
        Smart header detection: if pasting at row 0 and row 0 contains text headers, applies them as column names/units.
        """
        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()
        text = clipboard.text() or ""
        html = mime.html() if (mime and mime.hasHtml()) else None

        if not text and not html:
            return

        table = ClipboardTableParser.parse_clipboard(text, html=html)
        if not table:
            return

        indexes = self.table_view.selectionModel().selectedIndexes()
        start_row = indexes[0].row() if indexes else 0
        start_col = indexes[0].column() if indexes else 0

        before = copy.deepcopy(self.worksheet.to_dict())

        # Determine whether to extract headers
        headers_applied = False
        headers_list = None
        data_rows = table

        if not force_raw:
            if force_headers:
                headers_list = [str(c) if c is not None else "" for c in table[0]]
                data_rows = table[1:] if len(table) > 1 else []
            elif start_row == 0:
                has_h, detected_headers, remaining_data = ClipboardTableParser.detect_headers(table)
                if has_h:
                    headers_list = detected_headers
                    data_rows = remaining_data

        if headers_list:
            headers_applied = True
            for c_offset, h_text in enumerate(headers_list):
                target_c = start_col + c_offset
                while target_c >= self.worksheet.column_count():
                    self.worksheet.add_column()
                col = self.worksheet.get_column(target_c)
                if col:
                    long_n, units = ClipboardTableParser.extract_name_and_units(h_text)
                    col.long_name = long_n
                    if units:
                        col.units = units
                    # Auto-assign roles based on column index or name keywords
                    if target_c == 0 and ("x" in long_n.lower() or "time" in long_n.lower() or "wave" in long_n.lower()):
                        col.role = ColumnRole.X
                    elif any(w in long_n.lower() for w in ("error", "err", "std", "sd", "se")):
                        col.role = ColumnRole.Y_ERR
                    elif col.role != ColumnRole.X:
                        col.role = ColumnRole.Y

        # Paste data rows into cells
        for r_offset, row in enumerate(data_rows):
            target_r = start_row + r_offset
            for c_offset, val in enumerate(row):
                target_c = start_col + c_offset
                while target_c >= self.worksheet.column_count():
                    self.worksheet.add_column()
                self.worksheet.set_cell(target_r, target_c, val)

        after = copy.deepcopy(self.worksheet.to_dict())
        cmd = WorksheetSnapshotCommand(self.worksheet, before, after, "Paste Table", callback=self.refresh_view)
        self.undo_stack.push(cmd)

        n_rows = len(data_rows)
        n_cols = max(len(r) for r in table) if table else 0
        msg = f"Pasted table: {n_rows} data row(s) × {n_cols} column(s)"
        if headers_applied:
            msg += " (Headers detected & applied to columns)"
        self._notify_data_modified(msg)

    def clear_selection(self):
        """Clears contents of selected cells with Undo support."""
        indexes = [
            idx for idx in self.table_view.selectionModel().selectedIndexes()
            if self.worksheet.get_cell(idx.row(), idx.column()) is not None
        ]
        if not indexes:
            return

        before = copy.deepcopy(self.worksheet.to_dict())
        for idx in indexes:
            self.worksheet.set_cell(idx.row(), idx.column(), None)
        after = copy.deepcopy(self.worksheet.to_dict())

        cmd = WorksheetSnapshotCommand(self.worksheet, before, after, "Clear Cells", callback=self.refresh_view)
        self.undo_stack.push(cmd)
        self._notify_data_modified("Cleared cells")

    def _add_mask_actions(self, menu: QMenu):
        menu.addAction("Mask Cells (Exclude) [M]", lambda: self.mask_selection())
        menu.addAction("Unselect Cells (Include Again)", self.unmask_selection)
        menu.addAction("Unselect All Masked Cells", self.clear_all_masks)

    def mask_selection(self, masked: bool = True):
        """Masks or unmasks selected cells to exclude/include them in curve fitting and stats."""
        row_count = self.worksheet.row_count()
        selection = [
            idx for idx in self.table_view.selectionModel().selectedIndexes()
            if idx.row() < row_count and self.worksheet.is_cell_masked(idx.row(), idx.column()) != masked
        ]
        if not selection:
            return
        before = copy.deepcopy(self.worksheet.to_dict())
        for idx in selection:
            self.worksheet.mask_cell(idx.row(), idx.column(), masked=masked)
        action_name = "Mask Cells" if masked else "Unselect Cells"
        self.undo_stack.push(WorksheetSnapshotCommand(
            self.worksheet, before, self.worksheet.to_dict(), action_name,
            callback=self.table_view.viewport().update,
        ))
        self._notify_data_modified(f"{action_name} ({len(selection)} cells)")

    def unmask_selection(self):
        """Unmasks selected cells."""
        self.mask_selection(masked=False)

    def clear_all_masks(self):
        """Clears all masked cells in this worksheet."""
        if not self.worksheet.has_masked_cells():
            return
        before = copy.deepcopy(self.worksheet.to_dict())
        self.worksheet.clear_all_masks()
        after = copy.deepcopy(self.worksheet.to_dict())
        cmd = WorksheetSnapshotCommand(
            self.worksheet, before, after, "Unselect All Masked Cells", callback=self.table_view.viewport().update
        )
        self.undo_stack.push(cmd)
        self._notify_data_modified("All masked cells included again")

