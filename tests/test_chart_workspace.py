import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import pytest
from PyQt6.QtWidgets import QApplication
from omnigraph.ui.main_window import MainWindow
from omnigraph.ui.graph_view import GraphViewWidget
from omnigraph.ui.samples import SampleProjects

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])

@pytest.mark.parametrize("width",[640,800,1280])
def test_chart_editor_collapses_without_losing_label_edits(app,width):
    project=SampleProjects.create_spectroscopy_sample()
    widget=GraphViewWidget(project.graphs[0],project)
    widget.resize(width,650)
    widget.show()
    app.processEvents()
    assert not widget.chart_settings.isVisible()
    assert not widget.canvas_widget.toolbar.isVisible()
    collapsed=widget.canvas_widget.size()
    widget.edit_chart_button.setChecked(True)
    app.processEvents()
    assert widget.chart_settings.isVisible()
    if width >= 950:
        assert widget.canvas_widget.width()<collapsed.width()
    else:
        assert not widget.chart_settings.isWindow()
        assert widget.canvas_widget.height()>80
    widget.txt_quick_title.setText("A clear title")
    widget._on_quick_label_edited()
    widget.edit_chart_button.setChecked(False)
    app.processEvents()
    assert project.graphs[0].title_text=="A clear title"
    assert widget.canvas_widget.width()*widget.canvas_widget.height()>=(collapsed.width()-2)*(collapsed.height()-2)
    widget.close()

def test_workflow_actions_follow_active_data_or_chart(app):
    window=MainWindow(project=SampleProjects.create_spectroscopy_sample())
    window.enable_guided_workspace()
    assert window.chart_workflow_button.isEnabled()
    assert not window.export_workflow_action.isEnabled()
    window.center_tabs.setCurrentIndex(window.center_tabs.count()-1)
    assert not window.chart_workflow_button.isEnabled()
    assert window.analyze_workflow_button.isEnabled()
    assert window.export_workflow_action.isEnabled()
    window.close()

def test_blank_worksheet_has_actions_then_hides_starter(app):
    window=MainWindow()
    window.enable_guided_workspace()
    window.show()
    app.processEvents()
    sheet=window.get_active_spreadsheet_widget()
    assert sheet.starter_panel.isVisible()
    assert not window.chart_workflow_button.isEnabled()
    assert not window.export_workflow_action.isEnabled()
    sheet.worksheet.columns[0].data=[1,2,3]
    sheet.data_modified.emit()
    assert not sheet.starter_panel.isVisible()
    assert window.chart_workflow_button.isEnabled()
    window._remember_saved_state()
    window.close()


def test_all_zero_data_is_still_actionable(app):
    window=MainWindow()
    window.enable_guided_workspace()
    sheet=window.get_active_spreadsheet_widget()
    for column in sheet.worksheet.columns:
        column.data=[0,0,0]
    sheet.data_modified.emit()
    assert window.chart_workflow_button.isEnabled()
    assert window.analyze_workflow_button.isEnabled()
    assert sheet.starter_panel.isHidden()
    window._remember_saved_state()
    window.close()

def test_view_data_navigates_to_the_source_worksheet(app):
    window=MainWindow(project=SampleProjects.create_spectroscopy_sample())
    window.enable_guided_workspace()
    window.center_tabs.setCurrentIndex(window.center_tabs.count()-1)
    graph=window.get_active_graph_widget()
    source=graph.graph_model.curves[0].source_sheet
    graph.view_data_action.trigger()
    assert window.center_tabs.currentWidget().worksheet.name==source
    window.close()

def test_explore_menu_calls_navigation_tools(app,monkeypatch):
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
    from PyQt6.QtWidgets import QToolButton
    calls=[]
    for method in ["zoom","pan","home"]:
        monkeypatch.setattr(NavigationToolbar2QT,method,lambda self,*a,name=method:calls.append(name))
    project=SampleProjects.create_spectroscopy_sample()
    graph=GraphViewWidget(project.graphs[0],project)
    calls.clear()
    explore=next(button for button in graph.chart_toolbar.findChildren(QToolButton) if button.text()=="Explore")
    actions={action.text():action for action in explore.menu().actions()}
    for label in ["Zoom into an area","Pan the chart","Reset view"]:
        actions[label].trigger()
    assert calls==["zoom","pan","home"]
    graph.close()
