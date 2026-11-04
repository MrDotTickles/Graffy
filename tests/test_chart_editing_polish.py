"""Regression checks for real editing behavior and saved visual settings."""
import os
os.environ["QT_QPA_PLATFORM"]="offscreen"
import pytest
from matplotlib.colors import to_rgba
from PyQt6.QtWidgets import QApplication,QColorDialog,QMessageBox,QCheckBox,QStyle,QStyleOptionButton
from PyQt6.QtGui import QColor,QFont,QFontDatabase
from PyQt6.QtCore import Qt
from omnigraph.core.project import GraphModel,Project,CurveModel
from omnigraph.ui.samples import SampleProjects
from omnigraph.ui.dialogs.legend_dialog import LegendEditorDialog
from omnigraph.ui.color_field import ColorField
from omnigraph.ui.graph_view import GraphViewWidget
from omnigraph.graphing.plot_manager import PlotManager
from omnigraph.graphing.themes import get_theme_palette,THEMES
from omnigraph.ui.styles.qss import LIGHT_THEME_QSS,DARK_THEME_QSS

@pytest.fixture(scope="module")
def app():
    instance=QApplication.instance() or QApplication([])
    instance.setStyle("Fusion")
    if os.name=="nt":
        for name in ("segoeui.ttf","segoeuib.ttf","seguisym.ttf","seguiemj.ttf"):
            QFontDatabase.addApplicationFont("C:/Windows/Fonts/"+name)
    instance.setFont(QFont("Segoe UI",10))
    instance.setStyleSheet(LIGHT_THEME_QSS)
    return instance


def test_legend_color_changes_render_and_round_trip(app,tmp_path):
    project=SampleProjects.create_spectroscopy_sample()
    graph=project.graphs[0]
    manager=PlotManager(graph,project)
    dialog=LegendEditorDialog(graph,project=project,on_apply_callback=manager.render)
    dialog.color_buttons[0].set_color("#a21caf")
    dialog.table_series.item(0,3).setText("My signal")
    dialog.text_color.set_color("#173b27")
    dialog.background_color.set_color("#ffe6b3")
    dialog.border_color.set_color("#ad2634")
    dialog.opacity.setValue(100)
    assert dialog._apply_changes()
    legend=manager.ax.get_legend()
    assert legend.get_texts()[0].get_text()=="My signal"
    assert to_rgba(legend.get_texts()[0].get_color())==to_rgba("#173b27")
    assert legend.get_frame().get_facecolor()==to_rgba("#ffe6b3")
    assert legend.get_frame().get_edgecolor()==to_rgba("#ad2634")
    assert to_rgba(manager.ax.lines[0].get_color())==to_rgba("#a21caf")
    path=tmp_path/"styled.kgraph"
    project.save_to_file(str(path))
    restored=Project.load_from_file(str(path)).graphs[0]
    assert restored.legend_text_color=="#173b27"
    assert restored.legend_face_color=="#ffe6b3"
    assert restored.legend_edge_color=="#ad2634"
    assert restored.legend_frame_alpha==1
    assert restored.curves[0].color=="#a21caf"
    dialog.close()


def test_old_projects_keep_automatic_legend_colors(app):
    graph=GraphModel.from_dict({"title":"Legacy","curves":[]})
    assert graph.legend_text_color==graph.legend_face_color==graph.legend_edge_color=="auto"
    assert graph.legend_frame_alpha==0.9


@pytest.mark.parametrize("theme",["Origin Classic","Modern Dark"])
def test_automatic_legend_text_uses_figure_theme(app,theme):
    project=SampleProjects.create_spectroscopy_sample()
    graph=project.graphs[0];graph.theme=theme
    manager=PlotManager(graph,project);manager.render()
    assert to_rgba(manager.ax.get_legend().get_texts()[0].get_color())==to_rgba(THEMES[theme]["axes.labelcolor"])


def test_cancel_does_not_apply_legend_draft(app,monkeypatch):
    graph=SampleProjects.create_spectroscopy_sample().graphs[0]
    before=graph.to_dict()
    dialog=LegendEditorDialog(graph)
    monkeypatch.setattr(QColorDialog,"getColor",lambda *a,**kw:QColor("#f97316"))
    dialog.color_buttons[0].click()
    dialog.text_color.set_color("#342c77")
    dialog.chk_frame.setChecked(False)
    dialog.reject()
    assert graph.to_dict()==before


def test_failed_apply_does_not_close_or_partially_change_graph(app,monkeypatch):
    graph=SampleProjects.create_spectroscopy_sample().graphs[0]
    before=graph.to_dict()
    def failure():
        raise RuntimeError("Could not render")
    dialog=LegendEditorDialog(graph,on_apply_callback=failure)
    dialog.color_buttons[0].set_color("#ef4444")
    monkeypatch.setattr(QMessageBox,"warning",lambda *a,**kw:None)
    dialog._on_ok()
    assert dialog.result()!=dialog.DialogCode.Accepted
    assert graph.to_dict()==before
    dialog.close()


def test_source_name_reset_uses_real_column_name(app):
    project=SampleProjects.create_spectroscopy_sample()
    graph=project.graphs[0]
    curve=graph.curves[0]
    sheet=project.get_workbook(curve.source_workbook).sheets[0]
    sheet.columns[curve.y_col_idx].long_name="Measured absorption"
    graph.curves[0].label="Old temporary label"
    dialog=LegendEditorDialog(graph,project=project)
    dialog._preset_reset_to_columns()
    assert dialog.table_series.item(0,3).text()==sheet.columns[curve.y_col_idx].display_label
    dialog.close()


def test_series_controls_update_render_and_keep_automatic_colors(app,monkeypatch):
    project=SampleProjects.create_spectroscopy_sample()
    graph=project.graphs[0]
    graph.curves[0].plot_type="line_symbol"
    widget=GraphViewWidget(graph,project)
    editor=widget.series_editor
    monkeypatch.setattr(QColorDialog,"getColor",lambda *a,**kw:QColor("#b91c1c"))
    editor.color.button.click()
    editor.line_width.setValue(3.2)
    editor.marker_fill.make_transparent()
    assert graph.curves[0].color=="#b91c1c"
    assert graph.curves[0].marker_face_color=="none"
    assert graph.curves[0].line_width==3.2
    line=widget.canvas_widget.plot_manager.ax.lines[0]
    assert line.get_markerfacecolor()=="none"
    editor.color.reset_color()
    assert graph.curves[0].color=="auto"
    graph.theme="Nature"
    widget.refresh_plot()
    assert graph.curves[0].color=="auto"
    assert to_rgba(widget.canvas_widget.plot_manager.ax.lines[0].get_color())==to_rgba(get_theme_palette("Nature")[0])
    widget.close()


def test_none_symbol_and_step_line_style_match_selection(app):
    project=SampleProjects.create_spectroscopy_sample()
    graph=project.graphs[0];curve=graph.curves[0]
    curve.plot_type="line_symbol";curve.marker="none"
    manager=PlotManager(graph,project);manager.render()
    assert manager.ax.lines[0].get_marker() in ("", "None", "none")
    curve.plot_type="step";curve.line_style="--"
    manager.render()
    assert manager.ax.lines[0].get_linestyle()=="--"


def test_secondary_and_bottom_axis_labels_apply(app):
    project=SampleProjects.create_spectroscopy_sample()
    graph=project.graphs[0]
    graph.curves[0].axis="secondary";graph.layout_mode="twin_x";graph.y2_title=""
    widget=GraphViewWidget(graph,project)
    assert not widget.txt_quick_y2.isHidden()
    widget.txt_quick_y2.setText("Secondary signal")
    widget._on_quick_label_edited()
    assert graph.y2_title=="Secondary signal"
    assert widget.canvas_widget.plot_manager.ax2.get_ylabel()=="Secondary signal"
    graph.layout_mode="stacked_2x1"
    widget._sync_quick_labels()
    widget.txt_quick_y_bottom.setText("Bottom signal")
    widget._on_quick_label_edited()
    assert graph.y_bottom_title=="Bottom signal"
    assert widget.canvas_widget.plot_manager.ax_bottom.get_ylabel()=="Bottom signal"
    widget.close()


@pytest.mark.parametrize("stylesheet",[LIGHT_THEME_QSS,DARK_THEME_QSS])
def test_checkbox_checkmark_is_rendered_in_both_themes(app,stylesheet):
    app.setStyleSheet(stylesheet)
    checkbox=QCheckBox("Show legend")
    checkbox.resize(200,44);checkbox.show();app.processEvents()
    option=QStyleOptionButton();option.initFrom(checkbox)
    rect=checkbox.style().subElementRect(QStyle.SubElement.SE_CheckBoxIndicator,option,checkbox)
    unchecked=checkbox.grab().toImage().copy(rect)
    checkbox.setChecked(True);app.processEvents()
    checked=checkbox.grab().toImage().copy(rect)
    assert checked!=unchecked
    assert rect.width()>=18 and rect.height()>=18
    checkbox.close()
    app.setStyleSheet(LIGHT_THEME_QSS)


@pytest.mark.parametrize("kind",["scatter","line","line_symbol","step","spline","errorbar","bar","hbar","area","histogram","box","box_jitter","violin","violin_jitter","jitter"])
def test_existing_chart_switches_type_without_replotting_or_losing_data(app,kind,tmp_path):
    from copy import deepcopy
    import numpy as np
    project=SampleProjects.create_enzyme_kinetics_sample()
    graph=project.graphs[0]
    before=deepcopy(project.workbooks[0].to_dict())
    curve=graph.curves[0]
    source=(curve.id,curve.source_workbook,curve.source_sheet,curve.x_col_idx,curve.y_col_idx,curve.y_err_col_idx)
    graph.x_auto_limits=False;graph.x_min=0;graph.x_max=1
    graph.y_auto_limits=False;graph.y_min=0;graph.y_max=1
    widget=GraphViewWidget(graph,project)
    widget.change_plot_actions[kind].trigger()
    assert len(project.graphs)==1 and project.graphs[0] is graph
    assert graph.curves[0] is curve and curve.plot_type==kind
    assert source==(curve.id,curve.source_workbook,curve.source_sheet,curve.x_col_idx,curve.y_col_idx,curve.y_err_col_idx)
    assert project.workbooks[0].to_dict()==before
    assert graph.x_auto_limits and graph.y_auto_limits
    manager=widget.canvas_widget.plot_manager
    assert manager.ax.has_data()
    if kind=="histogram":
        assert sum(p.get_height() for p in manager.ax.patches)==8
        assert graph.y_title=="Count"
    elif kind=="hbar":
        _,values,_=manager._get_curve_data(curve)
        assert np.allclose([p.get_width() for p in manager.ax.patches],values)
    elif kind in ("box","box_jitter","violin","violin_jitter","jitter"):
        from matplotlib.container import ErrorbarContainer
        assert not any(isinstance(c,ErrorbarContainer) for c in manager.ax.containers)
    path=tmp_path/"converted.kgraph"
    project.save_to_file(str(path))
    restored=Project.load_from_file(str(path))
    assert restored.graphs[0].curves[0].plot_type==kind
    widget.change_plot_type("errorbar")
    assert graph.y_title=="Initial Velocity V0 (μmol/min)"
    assert graph.x_title=="Substrate Concentration [S] (mM)"
    assert curve.y_err_col_idx==2
    assert project.workbooks[0].to_dict()==before
    widget.close()


def test_conversion_preserves_fitted_lines_and_individual_series_choice(app):
    from copy import deepcopy
    project=SampleProjects.create_spectroscopy_sample();graph=project.graphs[0]
    fit=CurveModel.from_dict(graph.curves[0].to_dict());fit.id="fit-test";fit.is_fit_curve=True
    graph.curves.append(fit)
    graph.annotations.append({"type":"text","x":400,"y":0.3,"text":"Keep me"})
    fit_before=deepcopy(fit.to_dict())
    widget=GraphViewWidget(graph,project)
    widget.change_plot_type("scatter")
    assert graph.curves[0].marker=="o"
    assert fit.to_dict()==fit_before
    assert graph.annotations[0]["text"]=="Keep me"
    editor=widget.series_editor
    editor.plot_type.setCurrentIndex(editor.plot_type.findData("bar"))
    assert graph.curves[0].plot_type=="bar"
    assert fit.to_dict()==fit_before
    assert len(project.graphs)==1
    widget.close()


def test_plot_axis_labels_and_scales_survive_switch_and_reopen(app,tmp_path):
    from omnigraph.core.plot_editing import change_graph_plot_type
    project=SampleProjects.create_enzyme_kinetics_sample();graph=project.graphs[0]
    graph.x_scale="log10"
    change_graph_plot_type(graph,"histogram")
    assert graph.x_scale==graph.y_scale=="linear"
    graph.x_title="Rate distribution";graph.y_title="Observations"
    path=tmp_path/"axis-types.kgraph";project.save_to_file(str(path))
    graph=Project.load_from_file(str(path)).graphs[0]
    change_graph_plot_type(graph,"line")
    assert graph.x_scale=="log10"
    assert graph.x_title=="Substrate Concentration [S] (mM)"
    change_graph_plot_type(graph,"box")
    assert graph.x_scale=="linear" and graph.x_title=="Series"
    change_graph_plot_type(graph,"histogram")
    assert graph.x_title=="Rate distribution" and graph.y_title=="Observations"


def test_legend_series_color_updates_matching_symbol_outline(app,monkeypatch):
    project=SampleProjects.create_enzyme_kinetics_sample();graph=project.graphs[0]
    manager=PlotManager(graph,project)
    dialog=LegendEditorDialog(graph,project=project,on_apply_callback=manager.render)
    monkeypatch.setattr(QColorDialog,"getColor",lambda *args,**kwargs:QColor("#6d28d9"))
    dialog.color_buttons[0].click()
    assert dialog._apply_changes()
    curve=graph.curves[0]
    assert curve.color=="#6d28d9" and curve.marker_edge_color=="auto"
    assert curve.marker_face_color=="#ffffff"
    line=manager.ax.containers[0].lines[0]
    assert to_rgba(line.get_markeredgecolor())==to_rgba("#6d28d9")
    assert to_rgba(line.get_markerfacecolor())==to_rgba("#ffffff")
    dialog.close()
