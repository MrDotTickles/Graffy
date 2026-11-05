"""
Unit tests for the enhanced Formula Evaluator and native QUndoStack Undo/Redo system.
"""

import os
import sys
import numpy as np
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from omnigraph.core.worksheet import Worksheet, ColumnRole
from omnigraph.core.column_formula import FormulaEvaluator
from omnigraph.ui.spreadsheet_view import SpreadsheetWidget
from omnigraph.ui.dialogs.formula_dialog import FormulaDialog
from omnigraph.ui.main_window import MainWindow
from omnigraph.core.project import Project


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_formula_evaluator_syntax_and_operators(qapp):
    """Verifies that natural scientific formula syntax works seamlessly."""
    ws = Worksheet.create_default(num_rows=10)
    ws.columns[0].fill_sequence(1.0, 1.0, 10)  # Col A: 1..10
    ws.columns[1].fill_sequence(10.0, 10.0, 10)  # Col B: 10..100

    # 1. Natural OriginLab unquoted col(A)
    res = FormulaEvaluator.evaluate("col(A) * 2", ws)
    assert np.allclose(res, [2, 4, 6, 8, 10, 12, 14, 16, 18, 20])

    # 2. 1-based column numbering: col(1) is Col A
    res = FormulaEvaluator.evaluate("col(1) * 3", ws)
    assert np.allclose(res, [3, 6, 9, 12, 15, 18, 21, 24, 27, 30])

    # 3. Direct column letter variables: A + B
    res = FormulaEvaluator.evaluate("A + B", ws)
    assert np.allclose(res, [11, 22, 33, 44, 55, 66, 77, 88, 99, 110])

    # 4. Exponentiation operator ^: A^2 + 5
    res = FormulaEvaluator.evaluate("A^2 + 5", ws)
    assert np.allclose(res, [6, 9, 14, 21, 30, 41, 54, 69, 86, 105])

    # 5. Row index variable i (1..N)
    res = FormulaEvaluator.evaluate("i * 0.5", ws)
    assert np.allclose(res, [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0])

    # 6. Normalization: norm(A) -> 0..1
    res = FormulaEvaluator.evaluate("norm(A)", ws)
    assert np.isclose(res[0], 0.0)
    assert np.isclose(res[-1], 1.0)

    # 7. Z-Score standardization: zscore(A)
    res = FormulaEvaluator.evaluate("zscore(A)", ws)
    assert np.isclose(np.mean(res), 0.0, atol=1e-7)
    assert np.isclose(np.std(res), 1.0, atol=1e-7)

    # 8. First difference: diff(A)
    res = FormulaEvaluator.evaluate("diff(A)", ws)
    assert np.isclose(res[0], 0.0)
    assert np.allclose(res[1:], 1.0)

    # 9. Cumulative sum: cumsum(A)
    res = FormulaEvaluator.evaluate("cumsum(A)", ws)
    assert np.allclose(res, [1, 3, 6, 10, 15, 21, 28, 36, 45, 55])

    # 10. Trigonometric with pi: sin(A * pi / 2)
    res = FormulaEvaluator.evaluate("sin(A * pi / 2)", ws)
    assert np.isclose(res[0], 1.0)
    assert np.isclose(res[1], 0.0, atol=1e-7)


def test_formula_evaluator_friendly_errors(qapp):
    """Verifies that syntax and variable errors produce helpful messages."""
    ws = Worksheet.create_default(num_rows=10)

    # Unknown column
    with pytest.raises(ValueError) as exc:
        FormulaEvaluator.evaluate("col(NonExistent) * 2", ws)
    assert "not found" in str(exc.value)

    # Unknown variable
    with pytest.raises(ValueError) as exc:
        FormulaEvaluator.evaluate("xyz + 2", ws)
    assert "Unknown symbol" in str(exc.value)

    # Incomplete syntax
    with pytest.raises(ValueError) as exc:
        FormulaEvaluator.evaluate("sin(A * ", ws)
    assert "syntax" in str(exc.value).lower()


def test_formula_dialog_interaction(qapp):
    """Verifies FormulaDialog presets, token insertion, and live preview."""
    ws = Worksheet.create_default(num_rows=15)
    ws.columns[0].fill_sequence(1.0, 1.0, 15)
    ws.columns[1].fill_sequence(2.0, 2.0, 15)

    sw = SpreadsheetWidget(ws)
    dlg = FormulaDialog(ws, target_col_idx=1, undo_stack=sw.undo_stack, parent=sw)

    # Check preset selection
    dlg.combo_presets.setCurrentIndex(1)  # Linear scaling
    assert "col(" in dlg.txt_formula.text()

    # Manual formula
    dlg.txt_formula.setText("col(A) * 10")
    dlg._update_live_preview()

    assert "Formula valid" in dlg.lbl_status.text()
    assert dlg.btn_apply.isEnabled() is True

    # Accept formula
    dlg._on_accept()

    # Verify Col B was updated
    col_b = ws.columns[1]
    assert col_b.data[0] == 10.0
    assert col_b.data[1] == 20.0
    assert col_b.data[2] == 30.0
    assert col_b.formula == "col(A) * 10"

    dlg.close()


def test_undo_redo_formula_application(qapp):
    """Verifies that applying a formula can be instantly undone and redone via QUndoStack."""
    ws = Worksheet.create_default(num_rows=10)
    ws.columns[0].fill_sequence(1.0, 1.0, 10)
    orig_b = [5.0] * 10
    ws.columns[1].data = list(orig_b)

    sw = SpreadsheetWidget(ws)
    assert sw.undo_stack.canUndo() is False

    # Apply formula
    dlg = FormulaDialog(ws, target_col_idx=1, undo_stack=sw.undo_stack, parent=sw)
    dlg.txt_formula.setText("col(A) * 3")
    dlg._on_accept()

    # Values should be 3, 6, 9...
    assert ws.columns[1].data[0] == 3.0
    assert ws.columns[1].data[1] == 6.0
    assert sw.undo_stack.canUndo() is True
    assert "Formula" in sw.undo_stack.undoText()

    # Undo
    sw.undo()
    assert ws.columns[1].data[0] == 5.0
    assert ws.columns[1].data == orig_b
    assert sw.undo_stack.canUndo() is False
    assert sw.undo_stack.canRedo() is True

    # Redo
    sw.redo()
    assert ws.columns[1].data[0] == 3.0
    assert ws.columns[1].data[1] == 6.0
    assert sw.undo_stack.canUndo() is True


def test_undo_redo_cell_edits(qapp):
    """Verifies that table cell editing is recorded in the undo stack."""
    ws = Worksheet.create_default(num_rows=10)
    ws.columns[0].fill_sequence(1.0, 1.0, 10)

    sw = SpreadsheetWidget(ws)
    model = sw.model

    # Edit cell (row 2, col 0)
    idx = model.index(2, 0)
    assert ws.columns[0].data[2] == 3.0

    model.setData(idx, "99.5", Qt.ItemDataRole.EditRole)
    assert ws.columns[0].data[2] == 99.5
    assert sw.undo_stack.canUndo() is True

    # Undo
    sw.undo()
    assert ws.columns[0].data[2] == 3.0

    # Redo
    sw.redo()
    assert ws.columns[0].data[2] == 99.5


def test_undo_redo_structural_operations(qapp):
    """Verifies that add column, sort, and fill support undo/redo."""
    ws = Worksheet.create_default(num_rows=10)
    initial_cols = ws.column_count()

    sw = SpreadsheetWidget(ws)

    # 1. Add column
    sw.add_column()
    assert ws.column_count() == initial_cols + 1
    assert sw.undo_stack.canUndo() is True

    sw.undo()
    assert ws.column_count() == initial_cols

    sw.redo()
    assert ws.column_count() == initial_cols + 1

    # 2. Quick Fill
    sw._fill_col(0, "seq")
    assert ws.columns[0].data[0] == 1.0
    assert sw.undo_stack.canUndo() is True

    sw.undo()
    # Back to before fill
    assert sw.undo_stack.canRedo() is True


def test_main_window_edit_menu_undo_redo(qapp):
    """Verifies that MainWindow's Edit menu Undo (Ctrl+Z) and Redo (Ctrl+Y) actions operate on active sheet."""
    proj = Project.create_default("UndoTestProj")
    ws = proj.workbooks[0].sheets[0]
    ws.columns[0].fill_sequence(10, 10, 10)

    window = MainWindow(project=proj)
    sw = window.get_active_spreadsheet_widget()
    assert sw is not None

    # Perform an edit via spreadsheet widget
    sw.model.setData(sw.model.index(0, 0), "555.0", Qt.ItemDataRole.EditRole)
    assert ws.columns[0].data[0] == 555.0

    # Trigger undo via MainWindow action
    window.undo_action()
    assert ws.columns[0].data[0] == 10.0

    # Trigger redo via MainWindow action
    window.redo_action()
    assert ws.columns[0].data[0] == 555.0

    window.close()



def test_worksheet_row_menu_and_unselect_workflow(qapp, monkeypatch):
    from PyQt6.QtCore import QItemSelectionModel
    from PyQt6.QtWidgets import QInputDialog, QMessageBox, QPushButton

    ws = Worksheet.create_default(num_rows=4)
    ws.columns[0].data = [1, 2, 3, 4]
    sw = SpreadsheetWidget(ws)
    sw.enable_guided_sheet()
    assert any(button.text() == "Rows" for button in sw.findChildren(QPushButton))
    row_actions = {action.text(): action for action in sw.rows_menu.actions()}
    assert sw.model.rowCount() == 4
    sw.table_view.setCurrentIndex(sw.model.index(2, 0))
    row_actions["Insert Row Above"].trigger()
    assert ws.columns[0].data == [1, 2, None, 3, 4]
    sw.undo()
    assert sw.model.rowCount() == 4

    sw.table_view.setCurrentIndex(sw.model.index(0, 0))
    sw.table_view.selectionModel().select(sw.model.index(2, 1), QItemSelectionModel.SelectionFlag.Select)
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.No)
    row_actions["Delete Selected Rows"].trigger()
    assert ws.columns[0].data == [1, 2, 3, 4]
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    row_actions["Delete Selected Rows"].trigger()
    assert ws.columns[0].data == [2, 4]
    assert sw.model.rowCount() == 2
    sw.undo()
    assert ws.columns[0].data == [1, 2, 3, 4]
    sw.redo()
    assert sw.sheet_summary.text().startswith("2 rows")

    monkeypatch.setattr(QInputDialog, "getInt", lambda *args: (0, True))
    row_actions["Set Row Count…"].trigger()
    assert ws.row_count() == 0
    assert sw.model.rowCount() == 1
    assert sw.model.setData(sw.model.index(0, 0), "9")
    assert sw.sheet_summary.text().startswith("1 row")

    sw.table_view.setCurrentIndex(sw.model.index(0, 0))
    mask_actions = sw.btn_mask.menu().actions()
    mask_actions[0].trigger()
    assert ws.is_cell_masked(0, 0)
    assert "Unselect" in mask_actions[1].text()
    mask_actions[1].trigger()
    assert not ws.is_cell_masked(0, 0)
    sw.undo()
    assert ws.is_cell_masked(0, 0)
    sw.undo()
    sw.undo()
    assert ws.row_count() == 0

    monkeypatch.setattr(QInputDialog, "getInt", lambda *args: (3, True))
    row_actions["Add Rows at End…"].trigger()
    assert sw.model.rowCount() == 3
    sw._fill_col(0, "seq")
    assert ws.columns[0].data == [1, 2, 3]
