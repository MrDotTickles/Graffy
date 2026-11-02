"""
Undo / Redo management system for Graffy worksheets.
Provides QUndoCommand implementations for cell edits, formula evaluation,
column fills, clearing, pasting, sorting, and structural worksheet alterations.
"""

import copy
from typing import Optional, Callable, Dict, Any, List
from PyQt6.QtGui import QUndoCommand, QUndoStack


class CellEditCommand(QUndoCommand):
    """Undo/redo for single spreadsheet cell modifications."""

    def __init__(self, worksheet, row: int, col_idx: int, old_val: Any, new_val: Any, callback: Optional[Callable] = None):
        col = worksheet.get_column(col_idx)
        col_name = col.name if col else f"Col {col_idx+1}"
        super().__init__(f"Edit Cell ({row+1}, {col_name})")
        self.worksheet = worksheet
        self.row = row
        self.col_idx = col_idx
        self.old_val = old_val
        self.new_val = new_val
        self.callback = callback

    def redo(self):
        col = self.worksheet.get_column(self.col_idx)
        if col:
            col.set_value(self.row, self.new_val)
        if self.callback:
            self.callback()

    def undo(self):
        col = self.worksheet.get_column(self.col_idx)
        if col:
            col.set_value(self.row, self.old_val)
        if self.callback:
            self.callback()


class FormulaCommand(QUndoCommand):
    """Undo/redo for applying column formulas."""

    def __init__(
        self,
        worksheet,
        col_idx: int,
        old_formula: Optional[str],
        old_data: List[Any],
        new_formula: str,
        new_data: List[Any],
        callback: Optional[Callable] = None,
    ):
        col = worksheet.get_column(col_idx)
        col_name = col.name if col else f"Col {col_idx+1}"
        super().__init__(f"Apply Formula on Col({col_name})")
        self.worksheet = worksheet
        self.col_idx = col_idx
        self.old_formula = old_formula
        self.old_data = list(old_data)
        self.new_formula = new_formula
        self.new_data = list(new_data)
        self.callback = callback

    def redo(self):
        col = self.worksheet.get_column(self.col_idx)
        if col:
            col.formula = self.new_formula
            col.data = list(self.new_data)
        if self.callback:
            self.callback()

    def undo(self):
        col = self.worksheet.get_column(self.col_idx)
        if col:
            col.formula = self.old_formula
            col.data = list(self.old_data)
        if self.callback:
            self.callback()


class FillColumnCommand(QUndoCommand):
    """Undo/redo for quick fill operations."""

    def __init__(
        self,
        worksheet,
        col_idx: int,
        old_data: List[Any],
        new_data: List[Any],
        fill_type: str,
        callback: Optional[Callable] = None,
    ):
        col = worksheet.get_column(col_idx)
        col_name = col.name if col else f"Col {col_idx+1}"
        super().__init__(f"Quick Fill '{fill_type}' on Col({col_name})")
        self.worksheet = worksheet
        self.col_idx = col_idx
        self.old_data = list(old_data)
        self.new_data = list(new_data)
        self.callback = callback

    def redo(self):
        col = self.worksheet.get_column(self.col_idx)
        if col:
            col.data = list(self.new_data)
        if self.callback:
            self.callback()

    def undo(self):
        col = self.worksheet.get_column(self.col_idx)
        if col:
            col.data = list(self.old_data)
        if self.callback:
            self.callback()


class ClearColumnCommand(QUndoCommand):
    """Undo/redo for clearing a column."""

    def __init__(self, worksheet, col_idx: int, old_data: List[Any], callback: Optional[Callable] = None):
        col = worksheet.get_column(col_idx)
        col_name = col.name if col else f"Col {col_idx+1}"
        super().__init__(f"Clear Col({col_name})")
        self.worksheet = worksheet
        self.col_idx = col_idx
        self.old_data = list(old_data)
        self.callback = callback

    def redo(self):
        col = self.worksheet.get_column(self.col_idx)
        if col:
            col.data.clear()
        if self.callback:
            self.callback()

    def undo(self):
        col = self.worksheet.get_column(self.col_idx)
        if col:
            col.data = list(self.old_data)
        if self.callback:
            self.callback()


class WorksheetSnapshotCommand(QUndoCommand):
    """
    Undo/redo for structural or multi-cell operations:
    Sorting, inserting/deleting columns, paste block, clearing selection, role changes.
    """

    def __init__(
        self,
        worksheet,
        before_dict: Dict[str, Any],
        after_dict: Dict[str, Any],
        action_title: str,
        callback: Optional[Callable] = None,
    ):
        super().__init__(action_title)
        self.worksheet = worksheet
        self.before_dict = copy.deepcopy(before_dict)
        self.after_dict = copy.deepcopy(after_dict)
        self.callback = callback

    def redo(self):
        self.worksheet.restore_from_dict(self.after_dict)
        if self.callback:
            self.callback()

    def undo(self):
        self.worksheet.restore_from_dict(self.before_dict)
        if self.callback:
            self.callback()
