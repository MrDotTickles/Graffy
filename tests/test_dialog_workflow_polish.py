from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QInputDialog, QMessageBox

from omnigraph.core.project import CurveModel, GraphModel, Project
from omnigraph.core.worksheet import ColumnRole
from omnigraph.ui.dialogs.action_search import ActionSearchDialog
from omnigraph.ui.dialogs.add_curve_dialog import AddCurveDialog
from omnigraph.ui.dialogs.fit_dialog import FitDialog
from omnigraph.ui.dialogs.legend_dialog import LegendEditorDialog
from omnigraph.ui.dialogs.saved_presets_dialog import SavedPresetsDialog
from omnigraph.ui.dialogs.smooth_dialog import SmoothDialog
from omnigraph.ui.main_window import MainWindow
from omnigraph.ui.saved_settings import load_settings, store_settings


def data_project():
    project = Project.create_default()
    sheet = project.workbooks[0].sheets[0]
    sheet.columns[0].data = list(range(24))
    sheet.columns[1].data = [i * i for i in sheet.columns[0].data]
    return project, sheet


def test_action_search_filters_synonyms_and_opens_the_selected_action(qt_test_application):
    import_data = lambda: None
    edit_axes = lambda: None
    export_graph = lambda: None
    dialog = ActionSearchDialog([
        ("Import data", "excel csv", import_data),
        ("Set axis bounds", "minimum maximum", edit_axes),
        ("Export chart", "pdf svg", export_graph),
    ])
    dialog.show()
    QTest.keyClicks(dialog.search, "maximum")
    assert dialog.results.count() == 1
    QTest.keyPress(dialog.search, Qt.Key.Key_Return)
    assert dialog.selected_action is edit_axes

    dialog = ActionSearchDialog([("Import data", "", import_data), ("Export chart", "", export_graph)])
    dialog.show()
    QTest.keyPress(dialog.search, Qt.Key.Key_Down)
    QTest.keyPress(dialog.search, Qt.Key.Key_Return)
    assert dialog.selected_action is export_graph


def test_add_series_suggests_unused_column_and_clears_old_errors():
    project, sheet = data_project()
    sheet.add_column(long_name="Uncertainty", role=ColumnRole.Y_ERR).data = [1] * 24
    sheet.add_column(long_name="Second trace").data = [3] * 24
    graph = GraphModel()
    graph.curves.append(CurveModel())
    dialog = AddCurveDialog(project, graph)
    assert dialog.combo_y_col.currentData() == 3
    assert dialog.combo_yerr_col.currentData() is None
    dialog.combo_y_col.setCurrentIndex(dialog.combo_y_col.findData(1))
    assert dialog.combo_yerr_col.currentData() == 2
    dialog.combo_y_col.setCurrentIndex(dialog.combo_y_col.findData(0))
    assert dialog.combo_yerr_col.currentData() is None
    assert not dialog.add_button.isEnabled()
    dialog._on_accept()
    assert len(graph.curves) == 1
    dialog.combo_y_col.setCurrentIndex(dialog.combo_y_col.findData(1))
    dialog.combo_plot_type.setCurrentIndex(dialog.combo_plot_type.findData("bar"))
    dialog._on_accept()
    assert graph.curves[-1].plot_type == "bar"
    assert graph.curves[-1].y_err_col_idx is None


def test_cancel_restores_legend_after_preview():
    graph = GraphModel()
    graph.curves.append(CurveModel(color="#13579b"))
    renders = []
    dialog = LegendEditorDialog(graph, on_apply_callback=lambda: renders.append(graph.curves[0].color))
    dialog.color_buttons[0].set_color("#b97531")
    dialog.btn_apply.click()
    assert graph.curves[0].color == "#b97531"
    dialog.reject()
    assert graph.curves[0].color == "#13579b"
    assert renders == ["#b97531", "#13579b"]


def test_fit_dependent_controls_follow_model_range_and_output():
    project, _ = data_project()
    graph = GraphModel()
    graph.curves.append(CurveModel())
    dialog = FitDialog(project, active_graph=graph)
    assert dialog.spn_roi_min.isHidden()
    dialog.chk_use_roi.setChecked(True)
    assert not dialog.spn_roi_min.isHidden()
    dialog.combo_model.setCurrentIndex(dialog.combo_model.findData("gaussian"))
    assert dialog.chk_fix_intercept.isHidden()
    dialog.chk_export_sheet.setChecked(False)
    assert not dialog.chk_overlay_graph.isChecked()
    assert not dialog.chk_conf_band.isEnabled()
    dialog.chk_overlay_graph.setChecked(True)
    assert dialog.chk_export_sheet.isChecked()


def test_signal_processing_can_be_undone_from_worksheet(monkeypatch):
    project, sheet = data_project()
    window = MainWindow(project)
    original = list(sheet.columns[1].data)

    def run(dialog):
        dialog.combo_col.setCurrentIndex(1)
        dialog.combo_method.setCurrentIndex(dialog.combo_method.findData("moving_avg"))
        dialog.radio_replace.setChecked(True)
        dialog._on_accept()
        return dialog.result()

    monkeypatch.setattr(SmoothDialog, "exec", run)
    window.open_smoothing_dialog()
    assert sheet.columns[1].data != original
    window.undo_action()
    assert sheet.columns[1].data == original
    window._remember_saved_state()
    window.close()


def test_manage_saved_presets_renames_and_removes_the_selected_category(monkeypatch):
    chart_key, reading_key = "charts/setups", "import/reading_profiles"
    before_chart, before_reading = load_settings(chart_key), load_settings(reading_key)
    try:
        store_settings(chart_key, {"Original chart": {"style": {}}})
        store_settings(reading_key, {"Instrument CSV": ["first_row", ","]})
        dialog = SavedPresetsDialog()
        monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: ("Renamed chart", True))
        dialog.rename.click()
        assert load_settings(chart_key) == {"Renamed chart": {"style": {}}}
        dialog.kind.setCurrentIndex(1)
        monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.No)
        dialog.remove.click()
        assert "Instrument CSV" in load_settings(reading_key)
        monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
        dialog.remove.click()
        assert load_settings(reading_key) == {}
        assert not dialog.remove.isEnabled()
        assert "Renamed chart" in load_settings(chart_key)
    finally:
        store_settings(chart_key, before_chart)
        store_settings(reading_key, before_reading)



def test_dialog_footer_stacks_and_returns_to_one_row(qt_test_application, monkeypatch):
    from PyQt6.QtCore import QRect
    from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QWidget
    from omnigraph.ui.dialogs.dialog_layout import finish_dialog

    class SmallScreen:
        def availableGeometry(self):
            return QRect(0, 0, 400, 400)

    monkeypatch.setattr(QWidget, "screen", lambda self: SmallScreen())
    dialog = QDialog()
    dialog.resize(500, 320)
    footer = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
    for button in footer.buttons():
        button.setMinimumWidth(195)
    layout = QVBoxLayout(dialog)
    layout.addWidget(footer)
    finish_dialog(dialog, scroll_body=False)
    dialog.show()
    qt_test_application.processEvents()
    assert footer.orientation() == Qt.Orientation.Vertical
    for button in footer.buttons():
        assert dialog.rect().contains(button.mapTo(dialog, button.rect().bottomRight()))
    dialog.resize(520, 320)
    qt_test_application.processEvents()
    assert footer.orientation() == Qt.Orientation.Horizontal
    dialog.close()



def test_action_search_shortcut_uses_the_current_tab(qt_test_application, monkeypatch):
    project, _ = data_project()
    graph = GraphModel()
    graph.curves.append(CurveModel())
    project.graphs.append(graph)
    window = MainWindow(project)
    window.show()
    window.activateWindow()
    qt_test_application.processEvents()
    opened = []

    def record(dialog):
        opened.append([label for label, _, _ in dialog.actions])
        return dialog.DialogCode.Rejected

    monkeypatch.setattr(ActionSearchDialog, "exec", record)
    shortcut = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
    try:
        QTest.keyClick(window, Qt.Key.Key_P, shortcut)
        assert "Apply a column formula…" in opened[-1]
        assert "Set axis bounds…" not in opened[-1]
        window._on_explorer_item_activated("graph", graph.title, graph.id)
        qt_test_application.processEvents()
        QTest.keyClick(window, Qt.Key.Key_P, shortcut)
        assert "Set axis bounds…" in opened[-1]
        assert "Apply a column formula…" not in opened[-1]
    finally:
        window.close()
