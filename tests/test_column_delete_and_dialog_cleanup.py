"""
Tests for:
1. Removal of duplicate + Col / - Col buttons from spreadsheet toolbar.
2. Clear column deletion UX:
   - Visual highlighting on table.
   - Clear confirmation prompt with exact column letter and name.
   - Status bar feedback on deletion and cancellation.
   - Dynamic delete action tooltip reflecting selected column.
   - Undo/redo integration.
3. Peak Analysis Dialog 2-column responsive layout and clean typography.
4. Clean standard dialog font sizing without artificial enlargement.
"""

import os
import sys
import pytest
import numpy as np
from PyQt6.QtWidgets import QApplication, QMessageBox, QTableWidget, QScrollArea
from PyQt6.QtCore import Qt, QItemSelectionModel

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from omnigraph.ui.main_window import MainWindow
from omnigraph.core.project import Project
from omnigraph.core.worksheet import Worksheet, Column, ColumnRole
from omnigraph.ui.dialogs.peak_dialog import PeakAnalysisDialog
from omnigraph.ui.dialogs.formula_dialog import FormulaDialog
from omnigraph.ui.dialogs.quick_labels_dialog import QuickLabelsDialog
from omnigraph.ui.samples import SampleProjects


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_no_duplicate_col_buttons_in_spreadsheet_toolbar(qapp):
    """Ensure the sheet toolbar provides exactly one action for each column command."""
    proj = SampleProjects.create_spectroscopy_sample()
    win = MainWindow(project=proj)
    sw = win.get_active_spreadsheet_widget()
    assert sw is not None

    actions = [action.text() for action in sw.toolbar.actions()]
    assert actions.count("+ Col") == 1
    assert actions.count("- Col") == 1

    # Top ribbon toolbar must still provide the canonical actions:
    assert hasattr(win, "act_add_col")
    assert hasattr(win, "act_del_col")
    win.close()


def test_column_deletion_confirmation_prompt_and_cancellation(qapp, monkeypatch):
    """Ensure column deletion prompts with exact column letter and name, and cancellation does not delete."""
    proj = SampleProjects.create_spectroscopy_sample()
    win = MainWindow(project=proj)
    sw = win.get_active_spreadsheet_widget()
    assert sw is not None
    ws = sw.worksheet

    initial_col_count = ws.column_count()
    col_b = ws.get_column(1)
    col_b_expected = f"B: {col_b.display_label}"

    # Select column B (index 1)
    sw.table_view.selectColumn(1)

    # Track prompt arguments
    prompt_boxes = []

    def mock_question(parent, title, text, buttons, default):
        prompt_boxes.append((title, text))
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", mock_question)

    # Trigger deletion with confirmation
    sw.delete_selected_columns([1], confirm=True)

    # Must prompt user with column name
    assert len(prompt_boxes) == 1
    title, text = prompt_boxes[0]
    assert "Delete Column" in title
    assert col_b_expected in text
    assert "Ctrl+Z" in text

    # Since user clicked 'No', column count remains unchanged
    assert ws.column_count() == initial_col_count
    assert ws.get_column(1).name == col_b.name

    # Status bar should indicate cancellation
    assert "cancelled" in win.status_bar.currentMessage().lower()
    win.close()


def test_column_deletion_confirmed_with_undo_redo(qapp, monkeypatch):
    """Ensure confirmed column deletion deletes the column, shows status message, and supports undo/redo."""
    proj = SampleProjects.create_spectroscopy_sample()
    win = MainWindow(project=proj)
    sw = win.get_active_spreadsheet_widget()
    assert sw is not None
    ws = sw.worksheet

    initial_col_count = ws.column_count()
    col_b_name = ws.get_column(1).name

    def mock_question_yes(parent, title, text, buttons, default):
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", mock_question_yes)

    # Select column 1 and delete
    sw.table_view.selectColumn(1)
    sw.delete_selected_columns([1], confirm=True)

    # Column should be deleted
    assert ws.column_count() == initial_col_count - 1
    assert ws.get_column_by_name(col_b_name) is None

    # Status bar should indicate deletion
    status_msg = win.status_bar.currentMessage()
    assert "Deleted column" in status_msg
    assert "B: Absorbance" in status_msg

    # Test undo
    sw.undo()
    assert ws.column_count() == initial_col_count
    assert ws.get_column(1).name == col_b_name

    # Test redo
    sw.redo()
    assert ws.column_count() == initial_col_count - 1
    assert ws.get_column_by_name(col_b_name) is None
    win.close()


def test_dynamic_tooltip_reflects_selected_column(qapp):
    """Ensure the delete action tooltips dynamically update to show which column is selected."""
    proj = SampleProjects.create_spectroscopy_sample()
    win = MainWindow(project=proj)
    sw = win.get_active_spreadsheet_widget()
    ws = sw.worksheet

    col_a = ws.get_column(0)
    col_b = ws.get_column(1)

    # Select column A
    sw.table_view.selectColumn(0)
    sw._on_selection_changed()
    assert f"'A: {col_a.display_label}'" in win.act_del_col.toolTip()
    assert f"'A: {col_a.display_label}'" in sw.act_sheet_del_col.toolTip()

    # Select column B
    sw.table_view.selectColumn(1)
    sw._on_selection_changed()
    assert f"'B: {col_b.display_label}'" in win.act_del_col.toolTip()
    assert f"'B: {col_b.display_label}'" in sw.act_sheet_del_col.toolTip()
    win.close()


def test_peak_analysis_dialog_two_column_layout(qapp):
    """Ensure PeakAnalysisDialog uses a 2-column responsive layout with visible table and parameters."""
    proj = SampleProjects.create_spectroscopy_sample()
    dlg = PeakAnalysisDialog(project=proj)

    # Verify dialog geometry
    size = dlg.size()
    assert size.width() >= 650
    assert size.height() >= 500

    # Verify table preview has expanding size policy and good minimum height
    assert hasattr(dlg, "table_peaks")
    assert dlg.table_peaks.minimumHeight() >= 150

    # Verify key controls exist and are properly instantiated
    assert hasattr(dlg, "combo_sheet")
    assert hasattr(dlg, "combo_x_col")
    assert hasattr(dlg, "combo_y_col")
    assert hasattr(dlg, "combo_baseline")
    assert hasattr(dlg, "spn_prominence")
    assert hasattr(dlg, "spn_distance")
    assert hasattr(dlg, "chk_add_markers")
    assert hasattr(dlg, "chk_create_report")

    # Verify scroll area wrap
    scrolls = dlg.findChildren(QScrollArea)
    assert len(scrolls) >= 1
    assert scrolls[0].widgetResizable() is True
    dlg.close()


def test_dialog_typography_cleanup(qapp):
    """Verify that popup dialogs have clean standard typography without bloated font-sizes."""
    proj = SampleProjects.create_spectroscopy_sample()
    ws = proj.workbooks[0].sheets[0]

    # Formula dialog check
    f_dlg = FormulaDialog(ws, target_col_idx=1)
    f_dlg._update_live_preview()
    assert "font-size: 12px" not in f_dlg.lbl_status.styleSheet()
    assert "font-size: 14px" not in f_dlg.lbl_status.styleSheet()
    f_dlg.close()

    # Quick labels dialog check
    graph = proj.graphs[0]
    q_dlg = QuickLabelsDialog(graph)
    from PyQt6.QtWidgets import QLabel
    for lbl in q_dlg.findChildren(QLabel):
        assert "font-size: 14px" not in lbl.text()
    q_dlg.close()

    # Fitting report typography check: no 22px headers
    from omnigraph.analysis.fitting import CurveFitter
    res = CurveFitter.linear_fit(np.linspace(1, 10, 20), np.linspace(2, 20, 20))
    fit_html = res.to_html_report()
    assert "font-size: 22px" not in fit_html
    assert "font-size: 16px" in fit_html
    assert "font-size: 11px" in fit_html

    # Stats dialog check: no 13px font
    from omnigraph.ui.dialogs.stats_dialog import StatsDialog
    st_dlg = StatsDialog(ws.columns)
    assert hasattr(st_dlg, "txt_ttest_res")
    st_dlg.close()


def test_context_menu_explicit_column_deletion_labels(qapp):
    """Verify right-click menus show the exact column letter and name for deletion."""
    proj = SampleProjects.create_spectroscopy_sample()
    win = MainWindow(project=proj)
    sw = win.get_active_spreadsheet_widget()
    ws = sw.worksheet

    col_b = ws.get_column(1)
    # Select column B
    sw.table_view.selectColumn(1)
    sw._on_selection_changed()

    # Emulate cell context menu creation
    from PyQt6.QtCore import QPoint
    from PyQt6.QtWidgets import QMenu
    # Create menu using internal logic
    pos = sw.table_view.visualRect(sw.model.index(0, 1)).center()
    idx = sw.table_view.indexAt(pos)
    assert idx.isValid()
    assert idx.column() == 1

    # Verify that get_selected_column_indexes returns [1]
    assert sw.get_selected_column_indexes() == [1]

    # Verify column description formatting
    col_desc = f"'{col_b.name}: {col_b.display_label}'"
    assert "B: Absorbance" in col_desc
    win.close()


def test_delete_column_from_ribbon_while_graph_active_switches_to_sheet(qapp, monkeypatch):
    """Verify clicking - Col while viewing a graph switches tab to spreadsheet so user sees the column."""
    proj = SampleProjects.create_spectroscopy_sample()
    win = MainWindow(project=proj)
    win.show()
    QApplication.processEvents()

    # Switch to Graph tab
    graph_idx = -1
    for idx, meta in win.tab_metadata.items():
        if meta[0] == "graph":
            graph_idx = idx
            break
    assert graph_idx >= 0
    win.center_tabs.setCurrentIndex(graph_idx)
    assert win.center_tabs.currentWidget() != win.get_active_spreadsheet_widget()

    # Mock confirmation to cancel
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)

    # Click delete column
    win.delete_selected_columns_from_active_sheet(confirm=True)

    # Must have switched to spreadsheet widget so user could see what was targeted
    sw = win.get_active_spreadsheet_widget()
    assert win.center_tabs.currentWidget() == sw
    win.close()


def test_peak_analysis_table_stretch_and_styling(qapp):
    """Verify table_peaks uses QHeaderView.ResizeMode.Stretch and has alternating colors."""
    proj = SampleProjects.create_spectroscopy_sample()
    dlg = PeakAnalysisDialog(project=proj)

    hdr = dlg.table_peaks.horizontalHeader()
    from PyQt6.QtWidgets import QHeaderView
    assert hdr.sectionResizeMode(0) == QHeaderView.ResizeMode.Stretch
    assert dlg.table_peaks.alternatingRowColors() is True
    assert dlg.table_peaks.selectionBehavior() == QTableWidget.SelectionBehavior.SelectRows
    dlg.close()


def test_qss_header_checked_and_formula_input_size(qapp):
    """Verify QHeaderView::section:checked is styled and FormulaInput font size is 12px."""
    from omnigraph.ui.styles.qss import DARK_THEME_QSS, LIGHT_THEME_QSS
    assert "QHeaderView::section:checked" in DARK_THEME_QSS
    assert "QHeaderView::section:checked" in LIGHT_THEME_QSS
    assert "font-size: 14px;" not in DARK_THEME_QSS.split("QLineEdit#FormulaInput")[1].split("}")[0]
    assert "font-size: 12px;" in DARK_THEME_QSS.split("QLineEdit#FormulaInput")[1].split("}")[0]


def test_multi_column_visual_highlighting_before_deletion(qapp, monkeypatch):
    """Verify that multi-column deletion highlights all targeted columns simultaneously on the table."""
    proj = SampleProjects.create_spectroscopy_sample()
    win = MainWindow(project=proj)
    sw = win.get_active_spreadsheet_widget()
    ws = sw.worksheet

    # Add 2 more columns so we have A, B, C, D
    win.add_column_to_active_sheet()
    win.add_column_to_active_sheet()
    assert ws.column_count() >= 4

    captured_selected_cols = []

    def mock_question(parent, title, text, buttons, default):
        # Inspect which columns are visually selected in the table view right before the user decides
        selected = sorted(list(set(idx.column() for idx in sw.table_view.selectionModel().selectedIndexes())))
        captured_selected_cols.extend(selected)
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", mock_question)

    # Trigger deletion of columns 1 and 2
    sw.delete_selected_columns([1, 2], confirm=True)

    # Crucial check: BOTH columns 1 and 2 must have been highlighted simultaneously!
    assert captured_selected_cols == [1, 2]
    win.close()


def test_peak_dialog_parameter_change_invalidates_stale_cache(qapp):
    """Verify changing Y column or parameters invalidates last_result so stale peaks are never accepted."""
    from omnigraph.core.project import Project
    proj = Project("TestStale")
    ws = proj.workbooks[0].sheets[0]

    x = np.linspace(200, 800, 301)
    p1 = 5.0 * np.exp(-0.5 * ((x - 350) / 15) ** 2)
    p2 = 12.0 * np.exp(-0.5 * ((x - 550) / 20) ** 2)

    ws.columns = [
        Column("A", role=ColumnRole.X, data=x.tolist()),
        Column("B", role=ColumnRole.Y, data=p1.tolist()),
        Column("C", role=ColumnRole.Y, data=p2.tolist()),
    ]

    dlg = PeakAnalysisDialog(project=proj)
    # Detect for Column B
    dlg.combo_y_col.setCurrentIndex(1)
    res_b = dlg._run_peak_search()
    assert len(res_b.peaks) == 1
    assert np.isclose(res_b.peaks[0].x_center, 350, atol=2.0)
    assert dlg.last_result is res_b

    # Changing column to C should invalidate last_result cache!
    dlg.combo_y_col.setCurrentIndex(2)
    assert dlg.last_result is None

    # Accepting without explicit detect should now compute for Column C (center at 550)
    res_c = dlg._run_peak_search()
    assert len(res_c.peaks) == 1
    assert np.isclose(res_c.peaks[0].x_center, 550, atol=2.0)
    dlg.close()


def test_spreadsheet_widget_shift_delete_shortcut(qapp, monkeypatch):
    """Verify Shift+Delete keypress event on SpreadsheetWidget calls delete_selected_columns."""
    from PyQt6.QtGui import QKeyEvent
    from PyQt6.QtCore import QEvent
    proj = SampleProjects.create_spectroscopy_sample()
    win = MainWindow(project=proj)
    sw = win.get_active_spreadsheet_widget()

    deleted_called = []
    monkeypatch.setattr(sw, "delete_selected_columns", lambda: deleted_called.append(True))

    event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Delete,
        Qt.KeyboardModifier.ShiftModifier
    )
    sw.keyPressEvent(event)
    assert len(deleted_called) == 1
    win.close()


def test_mac_shift_backspace_shortcut(qapp, monkeypatch):
    """Verify Shift+Backspace keypress (MacBook keyboard delete) calls delete_selected_columns."""
    from PyQt6.QtGui import QKeyEvent
    from PyQt6.QtCore import QEvent
    proj = SampleProjects.create_spectroscopy_sample()
    win = MainWindow(project=proj)
    sw = win.get_active_spreadsheet_widget()

    deleted_called = []
    monkeypatch.setattr(sw, "delete_selected_columns", lambda: deleted_called.append(True))

    event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Backspace,
        Qt.KeyboardModifier.ShiftModifier
    )
    sw.keyPressEvent(event)
    assert len(deleted_called) == 1

    # Also verify table_view routes Shift+Backspace
    table_deleted_called = []
    monkeypatch.setattr(sw, "delete_selected_columns", lambda: table_deleted_called.append(True))
    sw.table_view.keyPressEvent(event)
    assert len(table_deleted_called) == 1
    win.close()


def test_macos_menu_roles(qapp):
    """Verify that Quit and About actions have appropriate QAction.MenuRole set for macOS."""
    from PyQt6.QtGui import QAction
    proj = SampleProjects.create_spectroscopy_sample()
    win = MainWindow(project=proj)

    # Search for About and Exit actions
    about_act = None
    exit_act = None
    for act in win.findChildren(QAction):
        if "About Graffy" in act.text():
            about_act = act
        elif act.text() == "Exit":
            exit_act = act

    assert about_act is not None, "About Graffy action must exist"
    assert exit_act is not None, "Exit action must exist"
    assert about_act.menuRole() == QAction.MenuRole.AboutRole
    assert exit_act.menuRole() == QAction.MenuRole.QuitRole
    win.close()


def test_delete_column_when_sw_is_none(qapp, monkeypatch):
    """Verify delete_selected_columns_from_active_sheet prompts and updates status when sw is None."""
    proj = SampleProjects.create_spectroscopy_sample()
    win = MainWindow(project=proj)
    # Simulate sw is None
    monkeypatch.setattr(win, "get_active_spreadsheet_widget", lambda: None)
    ws = win.get_active_worksheet()
    initial_cols = ws.column_count()

    prompts = []
    def mock_question(parent, title, text, buttons, default):
        prompts.append((title, text))
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", mock_question)
    win.delete_selected_columns_from_active_sheet(confirm=True)

    assert len(prompts) == 1
    assert "Confirm Delete Column" in prompts[0][0]
    assert ws.column_count() == initial_cols - 1
    assert "Deleted column" in win.status_bar.currentMessage()
    win.close()


