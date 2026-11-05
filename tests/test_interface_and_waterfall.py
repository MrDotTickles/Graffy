import pytest
from PyQt6.QtCore import Qt,QSettings
from PyQt6.QtWidgets import QApplication,QLabel
from omnigraph.ui.samples import SampleProjects
from omnigraph.ui.main_window import MainWindow
from omnigraph.ui.graph_view import GraphViewWidget
from omnigraph.core.project import Project
from omnigraph.graphing.plot_manager import PlotManager


def test_waterfall_axis_is_optional_persisted_and_does_not_change_data(qt_test_application,tmp_path):
    project=SampleProjects.create_waterfall_sample()
    graph=project.graphs[0]
    original=project.workbooks[0].to_dict()
    view=GraphViewWidget(graph,project)
    manager=view.canvas_widget.plot_manager
    assert not manager.ax.yaxis.get_visible()
    assert not manager.ax.spines['left'].get_visible()
    view.waterfall_axis_checkbox.setChecked(True)
    assert manager.ax.yaxis.get_visible()
    view.waterfall_spacing.setValue(3.5)
    assert graph.waterfall_y_step==3.5
    path=tmp_path/'waterfall.kgraph';project.save_to_file(str(path))
    restored=Project.load_from_file(str(path))
    assert restored.graphs[0].waterfall_show_y_axis
    assert restored.graphs[0].waterfall_y_step==3.5
    assert restored.workbooks[0].to_dict()==original
    view.waterfall_checkbox.setChecked(False)
    assert manager.ax.yaxis.get_visible()
    view.close()


def test_resizing_never_opens_editor_window(qt_test_application):
    project=SampleProjects.create_spectroscopy_sample()
    view=GraphViewWidget(project.graphs[0],project);view.show()
    for opened in (False,True):
        view.edit_chart_button.setChecked(opened)
        view.txt_quick_title.setText('Keep this draft')
        for width in (1200,640,1050,400,1200):
            view.resize(width,700);qt_test_application.processEvents()
            assert not view.chart_settings.isWindow()
            assert view.chart_settings.parentWidget() is view.chart_splitter
            assert view.chart_settings.isVisible()==opened
            assert view.txt_quick_title.text()=='Keep this draft'
    view.close()


def test_interface_scale_changes_controls_and_dialogs_not_figure(qt_test_application):
    window=MainWindow(project=SampleProjects.create_spectroscopy_sample())
    window.show();qt_test_application.processEvents()
    graph=next(window.center_tabs.widget(i) for i in range(window.center_tabs.count()) if isinstance(window.center_tabs.widget(i),GraphViewWidget))
    figure=graph.canvas_widget.plot_manager.fig
    original_dpi=figure.dpi
    window.set_interface_scale(1,persist=False)
    base_font=qt_test_application.font().pointSizeF()
    base_height=window.interface_scale_combo.sizeHint().height()
    window.set_interface_scale(1.5,persist=False)
    qt_test_application.processEvents()
    assert qt_test_application.font().pointSizeF()>base_font
    assert window.interface_scale_combo.sizeHint().height()>base_height
    assert figure.dpi==original_dpi
    window.toggle_theme()
    assert window.interface_scale==1.5
    assert '27px' in qt_test_application.styleSheet()
    window.set_zoom_level(1.4)
    assert figure.dpi==140
    assert qt_test_application.font().pointSizeF()>base_font
    window.set_interface_scale(1,persist=False);window.reset_zoom()
    window._remember_saved_state();window.close()


def test_interface_size_is_restored_on_restart(qt_test_application,tmp_path,monkeypatch):
    import omnigraph.ui.main_window as module
    settings=QSettings(str(tmp_path/'ui.ini'),QSettings.Format.IniFormat)
    monkeypatch.setattr(module,'QSettings',lambda *args:settings)
    first=MainWindow()
    first.set_interface_scale(1.25)
    first.close()
    second=MainWindow()
    assert second.interface_scale==1.25
    assert second.interface_scale_combo.currentData()==1.25
    second.set_interface_scale(1,persist=False)
    second.close()
