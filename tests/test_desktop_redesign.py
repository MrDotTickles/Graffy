"""Behavioral checks for the redesigned workspace and adaptive chart editor."""
import os
os.environ["QT_QPA_PLATFORM"]="offscreen"
import pytest
from PyQt6.QtWidgets import QApplication,QToolButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont,QFontDatabase
from omnigraph.ui.main_window import MainWindow
from omnigraph.ui.samples import SampleProjects

@pytest.fixture(scope="module")
def app():
    instance=QApplication.instance() or QApplication([])
    instance.setStyle("Fusion")
    if os.name=="nt":
        for name in ("segoeui.ttf","segoeuib.ttf","seguisym.ttf","seguiemj.ttf"):
            QFontDatabase.addApplicationFont("C:/Windows/Fonts/"+name)
    instance.setFont(QFont("Segoe UI",10))
    return instance

def make_window(app,width=1280):
    window=MainWindow(SampleProjects.create_spectroscopy_sample())
    window.enable_guided_workspace()
    window.setMinimumSize(320,240)
    window.resize(width,800)
    window.show()
    app.processEvents()
    return window

def test_dragged_tabs_keep_graph_and_data_identity(app):
    window=make_window(app)
    sheet=window.center_tabs.widget(0)
    graph=window.center_tabs.widget(1)
    window.center_tabs.tabBar().moveTab(1,0)
    window.center_tabs.setCurrentIndex(0)
    assert window.get_active_graph_widget() is graph
    assert window.export_workflow_action.isEnabled()
    graph.view_data_action.trigger()
    assert window.center_tabs.currentWidget() is sheet
    assert window.chart_workflow_button.isEnabled()
    window.close()

def test_compact_editor_keeps_figure_readable_and_closes_cleanly(app):
    window=make_window(app,800)
    window.center_tabs.setCurrentIndex(1)
    graph=window.get_active_graph_widget()
    app.processEvents()
    height=graph.canvas_widget.height()
    graph.edit_chart_button.setChecked(True)
    app.processEvents()
    assert graph.editor_dialog.isVisible()
    assert graph.canvas_widget.height()>=height-2
    graph.txt_quick_title.setText("A finished figure")
    graph._on_quick_label_edited()
    graph.editor_dialog.reject()
    assert not graph.edit_chart_button.isChecked()
    assert graph.chart_settings.isHidden()
    assert graph.graph_model.title_text=="A finished figure"
    window._remember_saved_state()
    window.close()

def test_editor_moves_between_small_window_and_side_panel_without_losing_edits(app):
    window=make_window(app,800)
    window.center_tabs.setCurrentIndex(1)
    graph=window.get_active_graph_widget()
    graph.edit_chart_button.setChecked(True)
    graph.txt_quick_x.setText("Elapsed time (s)")
    graph._on_quick_label_edited()
    window.resize(1600,900)
    app.processEvents()
    assert not graph.editor_dialog.isVisible()
    assert graph.chart_settings.parentWidget() is graph.chart_splitter
    assert graph.chart_settings.isVisible()
    assert graph.txt_quick_x.text()=="Elapsed time (s)"
    window.resize(800,600)
    app.processEvents()
    assert graph.editor_dialog.isVisible()
    assert graph.txt_quick_x.text()=="Elapsed time (s)"
    graph.editor_dialog.accept()
    window._remember_saved_state()
    window.close()

def test_project_panel_can_be_opened_on_small_displays(app):
    window=make_window(app,800)
    assert not window.dock_explorer.isVisible()
    window.navigator_action.trigger()
    app.processEvents()
    assert window.dock_explorer.isVisible()
    window.resize(850,650)
    app.processEvents()
    assert window.dock_explorer.isVisible()
    window.close()

def test_theme_switch_preserves_editor_and_refreshes_icons(app):
    window=make_window(app,1440)
    window.center_tabs.setCurrentIndex(1)
    graph=window.get_active_graph_widget()
    graph.edit_chart_button.setChecked(True)
    before=graph.edit_chart_button.icon().cacheKey()
    window.toggle_theme()
    assert graph.edit_chart_button.icon().cacheKey()!=before
    assert graph.chart_settings.isVisible()
    window.toggle_theme()
    window.close()

@pytest.mark.parametrize("width",[400,640,800])
def test_compact_primary_actions_fit_in_toolbar(app,width):
    window=make_window(app,width)
    window.center_tabs.setCurrentIndex(1)
    app.processEvents()
    toolbar=window.quick_start_toolbar
    for button in (window.data_workflow_button,toolbar.widgetForAction(window.export_workflow_action)):
        assert button.isVisible()
        assert button.geometry().right()<toolbar.width()
    window.close()


def test_open_recent_preserves_unsaved_work_when_cancelled(app,monkeypatch,tmp_path):
    from PyQt6.QtWidgets import QMessageBox
    saved=tmp_path/"saved.kgraph"
    SampleProjects.create_spectroscopy_sample().save_to_file(str(saved))
    window=make_window(app)
    original=window.project
    original.name="My unsaved experiment"
    monkeypatch.setattr(QMessageBox,"question",lambda *a,**kw:QMessageBox.StandardButton.Cancel)
    window.open_recent_project(str(saved))
    assert window.project is original
    window._remember_saved_state()
    window.close()


def test_closing_tabs_preserves_project_items_and_reopens_only_requested_view(app):
    window=make_window(app)
    graph=window.project.graphs[0]
    sheet=window.project.workbooks[0].sheets[0]
    before=window._project_snapshot()
    window._on_tab_close_requested(1)
    window._on_tab_close_requested(0)
    assert window.center_tabs.count()==0
    assert window.workspace_stack.currentIndex()==1
    assert window._project_snapshot()==before
    window._on_explorer_item_activated("graph",graph.title,graph.id)
    assert window.center_tabs.count()==1
    assert window.get_active_graph_widget().graph_model is graph
    window.get_active_graph_widget().view_data_action.trigger()
    assert window.center_tabs.count()==2
    assert window.center_tabs.currentWidget().worksheet is sheet
    window.close()
