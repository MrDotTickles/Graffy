"""
Tests for:
1. Easy delete column button (- Col / Delete Column(s)) and multi-column deletion with undo/redo.
2. Simplified column naming (single Column Name field instead of confusing short/long names).
3. Window scaling and PeakAnalysisDialog default size + QScrollArea wrapper.
4. Global zoom in / zoom out / reset zoom via Ctrl +, Ctrl -, Ctrl 0.
5. Main toolbar Undo and Redo buttons with Ctrl+Z, Ctrl+Y, and Ctrl+Shift+Z.
"""

import os
import sys
import pytest
from PyQt6.QtWidgets import QApplication, QScrollArea, QTableWidget
from PyQt6.QtCore import Qt, QItemSelectionModel
from PyQt6.QtGui import QKeySequence

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from omnigraph.ui.main_window import MainWindow
from omnigraph.core.project import Project
from omnigraph.core.worksheet import Worksheet, Column, ColumnRole
from omnigraph.ui.dialogs.column_prop_dialog import ColumnPropertiesDialog
from omnigraph.ui.dialogs.peak_dialog import PeakAnalysisDialog
from omnigraph.ui.dialogs.fit_dialog import FitDialog
from omnigraph.ui.dialogs.smooth_dialog import SmoothDialog
from omnigraph.ui.dialogs.add_curve_dialog import AddCurveDialog
from omnigraph.ui.graph_view import GraphViewWidget
from omnigraph.ui.report_view import ReportViewWidget
from omnigraph.ui.samples import SampleProjects
from omnigraph.core.column_formula import FormulaEvaluator


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture(autouse=True)
def mock_msgbox(monkeypatch):
    from PyQt6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **kw: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **kw: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **kw: QMessageBox.StandardButton.Ok)


def test_easy_delete_column_buttons_and_multi_column_undo(qapp):
    """Test - Col buttons on main toolbar & spreadsheet, multi-column deletion, and undo/redo."""
    proj = SampleProjects.create_spectroscopy_sample()
    win = MainWindow(project=proj)
    sw = win.get_active_spreadsheet_widget()
    assert sw is not None
    ws = sw.worksheet

    # Verify prominent - Col actions exist
    assert hasattr(win, "act_del_col")
    assert "- Col" in win.act_del_col.text()
    assert hasattr(sw, "btn_del_col")
    assert "- Col" in sw.btn_del_col.text()
    assert hasattr(sw, "btn_add_col")
    assert "+ Col" in sw.btn_add_col.text()

    # Initial column count is 4 (Wavelength, Peak1, Peak2, Total_Spectrum)
    initial_cols = ws.column_count()
    assert initial_cols >= 2

    # Add a column using + Col
    win.add_column_to_active_sheet()
    assert ws.column_count() == initial_cols + 1
    new_col_name = ws.columns[-1].name

    # Select the newly added column and delete it using delete_selected_columns_from_active_sheet
    sw.table_view.selectColumn(ws.column_count() - 1)
    win.delete_selected_columns_from_active_sheet()
    assert ws.column_count() == initial_cols
    assert ws.get_column_by_name(new_col_name) is None

    # Undo deletion via win.undo_action
    assert sw.undo_stack.canUndo() is True
    win.undo_action()
    assert ws.column_count() == initial_cols + 1
    assert ws.columns[-1].name == new_col_name

    # Redo deletion via win.redo_action
    assert sw.undo_stack.canRedo() is True
    win.redo_action()
    assert ws.column_count() == initial_cols

    # Test multi-column deletion:
    # Add two columns
    win.add_column_to_active_sheet()
    win.add_column_to_active_sheet()
    cols_before = ws.column_count()

    # Select both new columns
    idx1 = cols_before - 2
    idx2 = cols_before - 1
    sw.delete_selected_columns([idx1, idx2])
    assert ws.column_count() == cols_before - 2

    # Single undo restores both columns
    sw.undo()
    assert ws.column_count() == cols_before

    # Single redo deletes both columns again
    sw.redo()
    assert ws.column_count() == cols_before - 2

    # Safety check: Cannot delete all columns
    all_indices = list(range(ws.column_count()))
    sw.delete_selected_columns(all_indices)
    assert ws.column_count() > 0  # Still has columns

    win.close()


def test_simplified_column_naming_dialog_and_property_dock(qapp):
    """Test unified Column Name field in ColumnPropertiesDialog and PropertyInspectorWidget."""
    col = Column(name="B", long_name="", units="mM", comments="Test comment", role=ColumnRole.Y)
    col.data = [1.0, 2.0, 3.0]
    ws = Worksheet("TestSheet")
    ws.columns = [Column(name="A", role=ColumnRole.X, data=[10, 20, 30]), col]

    # 1. ColumnPropertiesDialog
    dlg = ColumnPropertiesDialog(col)
    assert hasattr(dlg, "txt_name")
    assert hasattr(dlg, "txt_long_name")
    assert dlg.txt_name is dlg.txt_long_name  # Unified into a single line edit

    # Set new intuitive Column Name
    dlg.txt_name.setText("Concentration")
    dlg._on_accept()

    assert col.long_name == "Concentration"
    assert col.display_label == "Concentration (mM)"
    dlg.close()

    # 2. FormulaEvaluator works with both unified name and reference letter
    res1 = FormulaEvaluator.evaluate("col(Concentration) * 2", ws)
    res2 = FormulaEvaluator.evaluate("col(B) * 2", ws)
    assert (res1 == [2.0, 4.0, 6.0]).all()
    assert (res2 == [2.0, 4.0, 6.0]).all()

    # 3. PropertyInspectorWidget
    proj = Project("NamingProj")
    proj.workbooks[0].sheets[0] = ws
    win = MainWindow(project=proj)
    prop = win.property_widget

    assert hasattr(prop, "txt_col_name")
    assert hasattr(prop, "txt_col_long_name")
    assert prop.txt_col_name is prop.txt_col_long_name

    # Switch selection to col B
    prop.set_active_worksheet(ws)
    prop.combo_cols.setCurrentIndex(1)
    assert prop.txt_col_name.text() == "Concentration"

    # Edit via property dock
    prop.txt_col_name.setText("Absorbance_Max")
    assert col.long_name == "Absorbance_Max"
    assert col.display_label == "Absorbance_Max (mM)"

    win.close()


def test_peak_analysis_dialog_geometry_and_scroll_scaling(qapp):
    """Verify PeakAnalysisDialog default geometry is enlarged and wrapped in QScrollArea."""
    proj = SampleProjects.create_spectroscopy_sample()
    dlg = PeakAnalysisDialog(project=proj)

    # 1. Size checks: generously sized by default
    assert dlg.size().width() >= 650
    assert dlg.size().height() >= 550
    available=dlg.screen().availableGeometry()
    assert 280 <= dlg.minimumSize().width() <= available.width()
    assert 240 <= dlg.minimumSize().height() <= available.height()

    # 2. Verify QScrollArea is present
    scrolls = dlg.findChildren(QScrollArea)
    assert len(scrolls) >= 1
    scroll = scrolls[0]
    assert scroll.widgetResizable() is True
    assert scroll.widget() is not None

    # 3. Verify Table peaks has non-zero minimum height
    tables = dlg.findChildren(QTableWidget)
    assert len(tables) >= 1
    assert tables[0].minimumHeight() >= 100

    # 4. Shrink dialog to test layout resilience
    dlg.resize(540, 460)
    dlg.show()
    QApplication.processEvents()
    # Scroll area ensures all child groupboxes remain in layout without destruction
    assert scroll.widget().isVisible() is True
    dlg.close()


def test_fit_dialog_geometry_and_scroll_scaling(qapp):
    """Verify FitDialog has generous sizing and scroll area."""
    proj = SampleProjects.create_enzyme_kinetics_sample()
    dlg = FitDialog(project=proj)
    assert dlg.size().width() >= 600
    assert dlg.size().height() >= 520
    scrolls = dlg.findChildren(QScrollArea)
    assert len(scrolls) >= 1
    dlg.close()


def test_zoom_scaling_shortcuts_and_level_bounds(qapp):
    """Verify global zoom in, zoom out, reset zoom, and bounds clamping."""
    proj = SampleProjects.create_spectroscopy_sample()
    win = MainWindow(project=proj)

    initial_zoom = win.zoom_level
    assert initial_zoom == 1.0
    initial_font_size = win._base_font_size

    # Zoom in
    win.zoom_in()
    assert win.zoom_level == 1.1
    assert qapp.font().pointSize() >= initial_font_size

    # Zoom in again
    win.zoom_in()
    assert win.zoom_level == 1.2

    # Zoom out
    win.zoom_out()
    assert win.zoom_level == 1.1

    # Reset zoom
    win.reset_zoom()
    assert win.zoom_level == 1.0
    assert qapp.font().pointSize() == initial_font_size

    # Clamping test: zoom in beyond maximum (2.0)
    for _ in range(15):
        win.zoom_in()
    assert win.zoom_level == 2.0

    # Clamping test: zoom out beyond minimum (0.7)
    for _ in range(20):
        win.zoom_out()
    assert win.zoom_level == 0.7

    win.reset_zoom()
    assert win.zoom_level == 1.0

    # Test spreadsheet table zoom adjustment
    sw = win.get_active_spreadsheet_widget()
    if sw:
        col_width_1 = sw.table_view.horizontalHeader().defaultSectionSize()
        win.set_zoom_level(1.5)
        col_width_15 = sw.table_view.horizontalHeader().defaultSectionSize()
        assert col_width_15 > col_width_1
        win.reset_zoom()

    win.close()


def test_main_window_undo_redo_buttons_and_shortcuts(qapp):
    """Verify main toolbar ↶ Undo and ↷ Redo buttons with dynamic enable/tooltip sync."""
    proj = SampleProjects.create_spectroscopy_sample()
    win = MainWindow(project=proj)
    sw = win.get_active_spreadsheet_widget()

    # Verify buttons exist on main toolbar
    assert hasattr(win, "btn_undo")
    assert hasattr(win, "btn_redo")
    assert "Undo" in win.btn_undo.text()
    assert "Redo" in win.btn_redo.text()

    # Initially clean sheet has nothing to undo
    assert win.btn_undo.isEnabled() is False
    assert win.btn_redo.isEnabled() is False

    # Modify cell data via model
    model = sw.model
    idx = model.index(0, 0)
    old_val = model.data(idx, Qt.ItemDataRole.EditRole)
    model.setData(idx, "999.5", Qt.ItemDataRole.EditRole)

    # Undo should now be enabled on main window toolbar
    assert win.btn_undo.isEnabled() is True
    assert "Undo: Edit Cell" in win.btn_undo.toolTip()
    assert win.btn_redo.isEnabled() is False

    # Trigger undo
    win.undo_action()
    assert model.data(idx, Qt.ItemDataRole.EditRole) == str(old_val)
    assert win.btn_undo.isEnabled() is False
    assert win.btn_redo.isEnabled() is True
    assert "Redo: Edit Cell" in win.btn_redo.toolTip()

    # Trigger redo
    win.redo_action()
    assert model.data(idx, Qt.ItemDataRole.EditRole) == "999.5"
    assert win.btn_undo.isEnabled() is True
    assert win.btn_redo.isEnabled() is False

    # Test alternate shortcut Ctrl+Shift+Z for redo
    win.undo_action()
    assert win.btn_redo.isEnabled() is True
    assert hasattr(win, "shortcut_redo_alt")
    win.shortcut_redo_alt.activated.emit()
    assert model.data(idx, Qt.ItemDataRole.EditRole) == "999.5"

    win.close()


def test_delete_columns_qaction_signal_compatibility(qapp):
    """Verify delete_selected_columns handles bool argument passed by Qt signals without crashing."""
    ws = Worksheet.create_default()
    ws.add_column()
    initial_count = ws.column_count()
    from omnigraph.ui.spreadsheet_view import SpreadsheetWidget
    sw = SpreadsheetWidget(ws)

    # Calling with checked=False (as QAction.triggered and QAbstractButton.clicked emit)
    sw.delete_selected_columns(False)
    assert ws.column_count() == initial_count - 1

    # Calling with integer index
    ws.add_column()
    sw.delete_selected_columns(1)
    assert ws.column_count() == initial_count - 1

    # Undo restores column
    sw.undo()
    assert ws.column_count() == initial_count


def test_property_dock_clear_and_type_column_name(qapp):
    """Verify user can clear and edit column name in PropertyInspectorWidget without it reverting to 'A'."""
    from omnigraph.ui.property_dock import PropertyInspectorWidget
    ws = Worksheet.create_default()
    prop = PropertyInspectorWidget()
    prop.set_active_worksheet(ws)

    # Initial text should be 'A'
    assert prop.txt_col_name.text() == "A"

    # User clears the field to type a new name: must not snap back to 'A'
    prop.txt_col_name.setText("")
    assert prop.txt_col_name.text() == ""
    assert ws.columns[0].long_name == ""

    # User types new name
    prop.txt_col_name.setText("Temperature")
    assert prop.txt_col_name.text() == "Temperature"
    assert ws.columns[0].long_name == "Temperature"
    assert ws.columns[0].display_label == "Temperature"
    assert "Temperature" in prop.combo_cols.itemText(0)


def test_direct_simplified_column_name_in_formula(qapp):
    """Verify FormulaEvaluator supports direct column variable names defined via simplified Column Name."""
    ws = Worksheet("KineticsSheet")
    ws.columns = [
        Column(name="A", long_name="Time", role=ColumnRole.X, data=[0.0, 1.0, 2.0]),
        Column(name="B", long_name="Velocity", role=ColumnRole.Y, data=[10.0, 20.0, 30.0]),
    ]
    # Direct variable reference Velocity * 2
    res1 = FormulaEvaluator.evaluate("Velocity * 2", ws)
    assert (res1 == [20.0, 40.0, 60.0]).all()

    # Mixed with col() function
    res2 = FormulaEvaluator.evaluate("col(Velocity) + Time", ws)
    assert (res2 == [10.0, 21.0, 32.0]).all()


def test_zoom_scales_row_height_and_graph_dpi(qapp):
    """Verify zoom scaling adjusts table row height and graph canvas DPI."""
    proj = SampleProjects.create_spectroscopy_sample()
    win = MainWindow(project=proj)
    sw = win.get_active_spreadsheet_widget()
    assert sw is not None

    base_row_h = sw.table_view.verticalHeader().defaultSectionSize()
    win.set_zoom_level(1.5)
    zoomed_row_h = sw.table_view.verticalHeader().defaultSectionSize()
    assert zoomed_row_h > base_row_h

    # Check graph tab DPI scaling
    win.center_tabs.setCurrentIndex(1)  # Switch to graph tab
    gw = win.get_active_graph_widget()
    if gw:
        assert hasattr(gw, "set_zoom")
        fig = gw.canvas_widget.plot_manager.fig
        win.set_zoom_level(1.4)
        assert fig.dpi == 140

    win.reset_zoom()
    win.close()


def test_smooth_and_add_curve_dialogs_have_scroll_areas(qapp):
    """Verify SmoothDialog and AddCurveDialog have QScrollArea for responsive scaling."""
    ws = Worksheet.create_default()
    smooth_dlg = SmoothDialog(ws)
    assert len(smooth_dlg.findChildren(QScrollArea)) >= 1
    smooth_dlg.close()

    proj = SampleProjects.create_spectroscopy_sample()
    graph = proj.graphs[0]
    add_curve_dlg = AddCurveDialog(proj, graph)
    assert len(add_curve_dlg.findChildren(QScrollArea)) >= 1
    add_curve_dlg.close()


def test_undo_redo_while_graph_tab_active(qapp):
    """Verify Undo/Redo works across the project even when user is viewing a Graph tab."""
    proj = SampleProjects.create_spectroscopy_sample()
    win = MainWindow(project=proj)

    # Make edit in sheet
    sw = win.get_active_spreadsheet_widget()
    model = sw.model
    idx = model.index(0, 0)
    old_val = model.data(idx, Qt.ItemDataRole.EditRole)
    model.setData(idx, "888.0", Qt.ItemDataRole.EditRole)
    assert win.btn_undo.isEnabled() is True

    # Switch to Graph tab
    win.center_tabs.setCurrentIndex(1)
    assert win.get_active_graph_widget() is not None

    # Undo should still be accessible and work
    assert win.btn_undo.isEnabled() is True
    win.undo_action()
    assert model.data(idx, Qt.ItemDataRole.EditRole) == str(old_val)

    # Redo should work
    assert win.btn_redo.isEnabled() is True
    win.redo_action()
    assert model.data(idx, Qt.ItemDataRole.EditRole) == "888.0"

    win.close()


def test_shift_delete_deletes_column(qapp):
    """Verify Shift+Delete on SpreadsheetTableView deletes selected column rather than clearing cell."""
    ws = Worksheet.create_default()
    ws.add_column()
    initial_count = ws.column_count()
    from omnigraph.ui.spreadsheet_view import SpreadsheetWidget
    from PyQt6.QtGui import QKeyEvent
    from PyQt6.QtCore import QEvent
    sw = SpreadsheetWidget(ws)
    sw.table_view.selectColumn(1)

    # Simulate Shift+Delete key event
    event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Delete,
        Qt.KeyboardModifier.ShiftModifier
    )
    sw.table_view.keyPressEvent(event)
    assert ws.column_count() == initial_count - 1

    # Plain Delete clears cell, does not delete column
    event_plain = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Delete,
        Qt.KeyboardModifier.NoModifier
    )
    sw.table_view.keyPressEvent(event_plain)
    assert ws.column_count() == initial_count - 1
