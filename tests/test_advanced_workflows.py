import os
import sys
import numpy as np
import pytest
from PyQt6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from omnigraph.ui.main_window import MainWindow
from omnigraph.core.project import Project, GraphModel, CurveModel
from omnigraph.core.worksheet import Worksheet, Column, ColumnRole
from omnigraph.ui.dialogs import FitDialog, PeakAnalysisDialog, SmoothDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_workflow_create_plot_from_selection(qapp):
    proj = Project.create_default("PlotWorkflowTest")
    wb = proj.workbooks[0]
    ws = wb.sheets[0]

    # Setup columns
    ws.columns[0].name = "A"
    ws.columns[0].role = ColumnRole.X
    ws.columns[0].fill_sequence(0, 1, 10)

    ws.columns[1].name = "B"
    ws.columns[1].role = ColumnRole.Y
    ws.columns[1].fill_sequence(10, 2, 10)

    window = MainWindow(project=proj)
    initial_graphs = len(proj.graphs)

    # Call create_plot
    window.create_plot("line_symbol")
    assert len(proj.graphs) == initial_graphs + 1
    new_graph = proj.graphs[-1]
    assert len(new_graph.curves) >= 1
    assert new_graph.curves[0].plot_type == "line_symbol"
    assert new_graph.curves[0].x_col_idx == 0
    assert new_graph.curves[0].y_col_idx == 1

    window.close()


def test_workflow_linear_fit_and_report_generation(qapp, tmp_path):
    proj = Project.create_default("FitWorkflowTest")
    wb = proj.workbooks[0]
    ws = wb.sheets[0]

    x = np.linspace(1, 10, 20)
    y = 2.5 * x + 4.0 + np.random.normal(0, 0.05, 20)
    ws.columns[0].data = x.tolist()
    ws.columns[1].data = y.tolist()

    # Create a graph for this data
    graph = GraphModel(title="LinearGraph")
    curve = CurveModel(source_workbook=wb.name, source_sheet=ws.name, x_col_idx=0, y_col_idx=1)
    graph.add_curve(curve)
    proj.graphs.append(graph)

    window = MainWindow(project=proj)
    initial_sheets = len(wb.sheets)
    initial_reports = len(proj.reports)
    initial_curves = len(graph.curves)

    # Run FitDialog
    dlg = FitDialog(project=proj, active_graph=graph, active_worksheet=ws, initial_fit_type="linear", parent=window)
    dlg._on_accept()

    # Verify fit curve overlaid on graph
    assert len(graph.curves) == initial_curves + 1
    assert graph.curves[-1].is_fit_curve is True
    assert "Linear Regression" in graph.curves[-1].label

    # Verify 95% confidence band added to annotations
    assert len(graph.annotations) >= 1
    assert graph.annotations[0]["type"] == "band"

    # Verify new fit data sheet created
    assert len(wb.sheets) == initial_sheets + 1
    fit_sheet = wb.sheets[-1]
    assert fit_sheet.column_count() == 4  # Fitted X, Fitted Y, Orig X, Residuals

    # Verify report created
    assert len(proj.reports) == initial_reports + 1
    report = proj.reports[-1]
    assert "Linear Regression" in report.title
    assert "R²" in report.html_content or "R-Square" in report.html_content

    # Verify export to image file
    export_path = str(tmp_path / "linear_fit_graph.png")
    gw = window.get_active_graph_widget()
    if gw:
        gw.canvas_widget.plot_manager.export_image(export_path, dpi=150)
        assert os.path.exists(export_path)
        assert os.path.getsize(export_path) > 1000

    window.close()


def test_workflow_peak_analysis(qapp):
    proj = Project.create_default("PeakWorkflowTest")
    wb = proj.workbooks[0]
    ws = wb.sheets[0]

    x = np.linspace(100, 500, 150)
    y = 5.0 * np.exp(-0.5 * ((x - 250) / 15) ** 2) + 0.1
    ws.columns[0].data = x.tolist()
    ws.columns[1].data = y.tolist()

    graph = GraphModel(title="PeakGraph")
    proj.graphs.append(graph)

    window = MainWindow(project=proj)
    dlg = PeakAnalysisDialog(project=proj, active_graph=graph, parent=window)
    dlg._on_accept()

    # Peak annotation added to graph
    assert len(graph.annotations) >= 1
    assert "P1" in graph.annotations[0]["text"]

    # Peak report generated
    assert len(proj.reports) >= 1
    assert "Peak Report" in proj.reports[-1].title

    window.close()


def test_workflow_smoothing(qapp):
    ws = Worksheet.create_default(num_rows=30)
    ws.columns[0].fill_sequence(0, 1, 30)
    ws.columns[1].fill_random_normal(0, 1, 30)
    initial_cols = ws.column_count()

    dlg = SmoothDialog(ws, selected_col_idx=1)
    dlg.spn_window.setValue(5)
    dlg._on_accept()

    # New column added with smoothed data
    assert ws.column_count() == initial_cols + 1
    smoothed_col = ws.columns[-1]
    assert "SG_Smooth" in smoothed_col.long_name
    assert len(smoothed_col.data) == 30


def test_workflow_export_dimensions_and_scaling(qapp, tmp_path):
    """Verifies that exporting a graph honors publication dimensions and does not distort aspect ratio."""
    from omnigraph.ui.samples import SampleProjects
    from omnigraph.graphing.plot_manager import PlotManager
    import PIL.Image

    proj = SampleProjects.create_spectroscopy_sample()
    graph = proj.graphs[0]
    pm = PlotManager(graph, proj)
    pm.render()

    # Simulate distorted screen canvas
    pm.fig.set_size_inches(14.0, 3.5)

    # 1. Export with Publication Standard (7.0 x 5.0 in @ 300 DPI)
    pub_file = str(tmp_path / "pub_standard.png")
    pm.export_image(pub_file, dpi=300, width_in=7.0, height_in=5.0, tight_crop=True)
    assert os.path.exists(pub_file)

    with PIL.Image.open(pub_file) as im:
        w, h = im.size
        aspect = w / h
        # Should be nicely proportioned near 1.40, NOT > 4.0
        assert 1.25 < aspect < 1.60
        assert w > 1800 and h > 1300

    # 2. Export with Journal Single Column (3.5 x 2.8 in @ 300 DPI)
    col_file = str(tmp_path / "single_col.png")
    pm.export_image(col_file, dpi=300, width_in=3.5, height_in=2.8, tight_crop=True)
    assert os.path.exists(col_file)

    with PIL.Image.open(col_file) as im:
        w, h = im.size
        aspect = w / h
        assert 1.10 < aspect < 1.45
        assert 900 < w < 1200


def test_workflow_clipboard_copy_compatibility(qapp):
    """Verifies that copying to clipboard registers both QImage (CF_DIB) and image/png."""
    from omnigraph.ui.samples import SampleProjects
    from omnigraph.graphing.canvas import OmniCanvas

    proj = SampleProjects.create_spectroscopy_sample()
    graph = proj.graphs[0]
    canvas = OmniCanvas(graph, proj)

    # Copy to clipboard
    success = canvas.copy_to_clipboard(width_in=7.0, height_in=5.0, dpi=300)
    assert success is True

    cb = QApplication.clipboard()
    mime = cb.mimeData()

    assert mime.hasImage() is True
    assert mime.hasFormat("image/png") is True

    # Image retrieved from clipboard should have publication resolution
    img = cb.image()
    assert not img.isNull()
    assert img.width() > 1800
    assert img.height() > 1300
    aspect = img.width() / img.height()
    assert 1.25 < aspect < 1.60


def test_workflow_export_dialog_presets_and_units(qapp, tmp_path):
    """Tests ExportDialog preset selection, unit conversion, and file generation."""
    from omnigraph.ui.samples import SampleProjects
    from omnigraph.graphing.plot_manager import PlotManager
    from omnigraph.ui.dialogs.export_dialog import ExportDialog

    proj = SampleProjects.create_spectroscopy_sample()
    pm = PlotManager(proj.graphs[0], proj)
    pm.render()

    dlg = ExportDialog(pm)
    assert dlg.combo_presets.currentIndex() == 0
    w_in, h_in = dlg.get_target_dimensions_in()
    assert w_in == 7.0 and h_in == 5.0

    # Switch to Single Column preset
    dlg.combo_presets.setCurrentIndex(1)
    w_in, h_in = dlg.get_target_dimensions_in()
    assert w_in == 3.5 and h_in == 2.8

    # Switch to Centimeters unit
    dlg.combo_units.setCurrentIndex(1)
    assert abs(dlg.spn_width.value() - (3.5 * 2.54)) < 0.05

    # Switch to Pixels unit
    dlg.combo_units.setCurrentIndex(2)
    expected_px = round(3.5 * dlg.get_dpi())
    assert abs(dlg.spn_width.value() - expected_px) < 2

    # Test clipboard copy directly from ExportDialog
    dlg._on_copy_to_clipboard()
    assert "Copied" in dlg.lbl_copy_status.text()
    cb = QApplication.clipboard()
    assert cb.mimeData().hasImage() is True

    # Test export through dialog action
    dest_file = str(tmp_path / "dialog_export.png")
    dlg.txt_path.setText(dest_file)
    dlg.plot_manager.export_image(dest_file, dpi=dlg.get_dpi(), width_in=dlg._width_in, height_in=dlg._height_in)
    assert os.path.exists(dest_file)
    assert os.path.getsize(dest_file) > 1000

    dlg.close()


def test_batch_multi_file_import_separate_sheets(qapp, tmp_path):
    """Verifies importing multiple data files simultaneously into separate sheets in active workbook."""
    from omnigraph.ui.dialogs.import_dialog import ImportDialog

    # Create 3 sample data files
    file1 = tmp_path / "sample_A.csv"
    file1.write_text("Wavelength,Intensity\n400,10.5\n500,20.2\n600,15.1\n", encoding="utf-8")

    file2 = tmp_path / "sample_B.csv"
    file2.write_text("Wavelength,Intensity\n400,12.0\n500,25.4\n600,18.9\n", encoding="utf-8")

    file3 = tmp_path / "sample_C.csv"
    file3.write_text("Wavelength,Intensity\n400,8.2\n500,16.8\n600,11.5\n", encoding="utf-8")

    proj = Project.create_default("BatchImportTest")
    window = MainWindow(project=proj)

    dlg = ImportDialog(initial_filepaths=[str(file1), str(file2), str(file3)], parent=window)
    assert len(dlg.filepaths) == 3
    assert dlg.list_files.count() == 3

    # Accept dialog with destination="sheets"
    dlg.combo_dest.setCurrentIndex(0)  # "sheets"
    dlg.chk_auto_plot.setChecked(True)
    dlg._on_accept()

    assert len(dlg.imported_results) == 3

    # Process through MainWindow
    window._process_imported_results(dlg)

    wb = proj.workbooks[0]
    sheet_names = [s.name for s in wb.sheets]
    assert "sample_A" in sheet_names
    assert "sample_B" in sheet_names
    assert "sample_C" in sheet_names

    # Verify comparison graph was generated
    assert len(proj.graphs) >= 1
    comp_graph = proj.graphs[-1]
    assert len(comp_graph.curves) == 3
    assert comp_graph.curves[0].label == "sample_A"
    assert comp_graph.curves[1].label == "sample_B"
    assert comp_graph.curves[2].label == "sample_C"

    window.close()


def test_batch_multi_file_import_merged_sheet(qapp, tmp_path):
    """Verifies batch importing multiple files combined into a single sheet."""
    from omnigraph.ui.dialogs.import_dialog import ImportDialog

    file1 = tmp_path / "run1.dat"
    file1.write_text("Time  Signal\n0.0   1.2\n1.0   2.4\n", encoding="utf-8")

    file2 = tmp_path / "run2.dat"
    file2.write_text("Time  Signal\n0.0   1.5\n1.0   3.0\n", encoding="utf-8")

    proj = Project.create_default("MergeBatchTest")
    window = MainWindow(project=proj)

    dlg = ImportDialog(initial_filepaths=[str(file1), str(file2)], parent=window)
    dlg.combo_dest.setCurrentIndex(2)  # "merge"
    dlg.chk_auto_plot.setChecked(False)
    dlg._on_accept()

    window._process_imported_results(dlg)

    wb = proj.workbooks[0]
    merged_sheet = next((s for s in wb.sheets if "Merged" in s.name), None)
    assert merged_sheet is not None
    assert merged_sheet.column_count() == 4  # 2 cols from run1 + 2 cols from run2

    window.close()


def test_conditional_symbol_options_visibility(qapp):
    """Verifies that symbol options are hidden when plot type has no symbols, and shown when it does."""
    from omnigraph.ui.property_dock import PropertyInspectorWidget
    from omnigraph.ui.dialogs.add_curve_dialog import AddCurveDialog

    proj = Project.create_default("SymbolVisTest")
    wb = proj.workbooks[0]
    ws = wb.sheets[0]
    ws.columns[0].data = [1, 2, 3]
    ws.columns[1].data = [10, 20, 30]

    graph = GraphModel(title="TestPlot")
    c1 = CurveModel(source_sheet=ws.name, x_col_idx=0, y_col_idx=1, plot_type="line")
    graph.curves.append(c1)
    proj.graphs.append(graph)

    dock = PropertyInspectorWidget()
    dock.set_active_graph(graph)

    # For 'line', line container visible, symbol container hidden!
    assert dock.container_line.isHidden() is False
    assert dock.container_marker.isHidden() is True

    # Switch plot type to 'scatter' -> line container hidden, symbol container visible!
    dock.combo_plot_type.setCurrentText("scatter")
    assert dock.container_line.isHidden() is True
    assert dock.container_marker.isHidden() is False

    # Switch to 'bar' -> both line and symbol containers must be hidden!
    dock.combo_plot_type.setCurrentText("bar")
    assert dock.container_line.isHidden() is True
    assert dock.container_marker.isHidden() is True

    # Switch to 'step' -> line visible, symbol hidden
    dock.combo_plot_type.setCurrentText("step")
    assert dock.container_line.isHidden() is False
    assert dock.container_marker.isHidden() is True

    # Switch to 'line_symbol' -> both line and symbol visible
    dock.combo_plot_type.setCurrentText("line_symbol")
    assert dock.container_line.isHidden() is False
    assert dock.container_marker.isHidden() is False

    # Now verify AddCurveDialog
    dlg_add = AddCurveDialog(proj, graph)
    # Default is 'line_symbol'
    assert dlg_add.combo_marker.isHidden() is False
    assert dlg_add.lbl_marker.isHidden() is False
    assert dlg_add.combo_line_style.isHidden() is False

    # Change to 'line'
    dlg_add.combo_plot_type.setCurrentText("line")
    assert dlg_add.combo_marker.isHidden() is True
    assert dlg_add.lbl_marker.isHidden() is True
    assert dlg_add.combo_line_style.isHidden() is False

    # Change to 'bar'
    dlg_add.combo_plot_type.setCurrentText("bar")
    assert dlg_add.combo_marker.isHidden() is True
    assert dlg_add.lbl_marker.isHidden() is True
    assert dlg_add.combo_line_style.isHidden() is True

    # Change to 'scatter'
    dlg_add.combo_plot_type.setCurrentText("scatter")
    assert dlg_add.combo_marker.isHidden() is False
    assert dlg_add.combo_line_style.isHidden() is True

    dlg_add.close()


def test_legend_key_editor_dialog_and_presets(qapp):
    """Verifies Key & Legend Editor Dialog renaming, batch presets, and styling."""
    from omnigraph.ui.dialogs.legend_dialog import LegendEditorDialog

    proj = Project.create_default("LegendDialogTest")
    graph = GraphModel(title="Spectra")
    graph.curves = [
        CurveModel(source_sheet="S1", x_col_idx=0, y_col_idx=1, label="OldName1"),
        CurveModel(source_sheet="S1", x_col_idx=0, y_col_idx=2, label="OldName2"),
    ]
    proj.graphs.append(graph)

    dlg = LegendEditorDialog(graph)
    assert dlg.table_series.rowCount() == 2

    # Test numbering preset
    dlg._preset_number_series()
    assert dlg.table_series.item(0, 3).text() == "Series 1"
    assert dlg.table_series.item(1, 3).text() == "Series 2"

    # Test changing legend location and frame
    dlg.combo_pos.setCurrentText("outside right")
    dlg.chk_frame.setChecked(True)
    dlg.spn_fs.setValue(12)

    dlg._apply_changes()
    assert graph.curves[0].label == "Series 1"
    assert graph.curves[1].label == "Series 2"
    assert graph.legend_location == "outside right"
    assert graph.legend_frame is True
    assert graph.legend_font_size == 12.0

    dlg.close()


def test_graphing_one_x_and_two_y_columns_simultaneously(qapp):
    """Verifies that 1 X and 2 Y columns (A=X, B=Y, C=Y) graph simultaneously with distinct colors and legend."""
    proj = Project.create_default("SimultaneousPlotTest")
    wb = proj.workbooks[0]
    ws = wb.sheets[0]

    # Configure 3 columns: A (X), B (Y), C (Y)
    ws.columns[0].role = ColumnRole.X
    ws.columns[0].long_name = "Time"
    ws.columns[0].units = "s"
    ws.columns[0].data = [1.0, 2.0, 3.0, 4.0, 5.0]

    ws.columns[1].role = ColumnRole.Y
    ws.columns[1].long_name = "Sensor 1"
    ws.columns[1].units = "mA"
    ws.columns[1].data = [10.0, 20.0, 30.0, 40.0, 50.0]

    col_c = Column(name="C", long_name="Sensor 2", units="mA", role=ColumnRole.Y, data=[15.0, 25.0, 35.0, 45.0, 55.0])
    ws.columns.append(col_c)

    window = MainWindow(project=proj)

    # 1. Plot with no explicit column selection (e.g. user just clicked 'Line + Symbol' plot button)
    # It must auto-discover all Y columns and plot BOTH simultaneously!
    window.create_plot("line_symbol")
    assert len(proj.graphs) == 1
    g1 = proj.graphs[0]
    assert len(g1.curves) == 2, "Both Y columns must be graphed simultaneously"
    assert g1.curves[0].x_col_idx == 0
    assert g1.curves[0].y_col_idx == 1
    assert "Sensor 1" in g1.curves[0].label

    assert g1.curves[1].x_col_idx == 0
    assert g1.curves[1].y_col_idx == 2
    assert "Sensor 2" in g1.curves[1].label

    # Colors must be distinct
    assert g1.curves[0].color != g1.curves[1].color
    # Legend must be enabled for multi-curve graph
    assert g1.legend_show is True

    # 2. Plot with selecting columns A, B, and C
    sw = window.get_active_spreadsheet_widget()
    if sw:
        # Select all columns
        sw.table_view.selectAll()
        window.create_plot("line")
        assert len(proj.graphs) == 2
        g2 = proj.graphs[1]
        assert len(g2.curves) == 2
        assert g2.curves[0].y_col_idx == 1
        assert g2.curves[1].y_col_idx == 2
        assert g2.curves[0].color != g2.curves[1].color

    window.close()


def test_legend_dialog_ok_no_crash(qapp):
    """Verifies that pressing OK in LegendEditorDialog with 'outside right' or custom settings does not crash."""
    from omnigraph.ui.dialogs.legend_dialog import LegendEditorDialog
    from omnigraph.graphing.plot_manager import PlotManager

    proj = Project.create_default("LegendOkTest")
    wb = proj.workbooks[0]
    ws = wb.sheets[0]
    ws.columns[0].data = [1.0, 2.0, 3.0]
    ws.columns[1].data = [4.0, 5.0, 6.0]

    graph = GraphModel(title="LegendTestGraph")
    c1 = CurveModel(source_sheet=ws.name, x_col_idx=0, y_col_idx=1, label="Initial Series")
    graph.curves.append(c1)
    graph.legend_location = "outside right"
    proj.graphs.append(graph)

    # Open dialog and simulate user pressing OK
    dlg = LegendEditorDialog(graph)
    dlg._on_ok()  # Must not crash!
    assert dlg.result() == 1 or not dlg.isVisible()

    # Re-render on PlotManager to ensure Matplotlib handles "outside right" flawlessly
    pm = PlotManager(graph, proj)
    pm.render()  # Must render without ValueError or crash


def test_clipboard_table_parser_and_delimiters():
    """Verifies that ClipboardTableParser extracts data across space, TSV, CSV, semicolon, HTML, and Markdown."""
    from omnigraph.core.clipboard_parser import ClipboardTableParser

    # 1. Space-separated table (never single cell!)
    space_txt = "10.5   20.2   30.8\n40.1   50.3   60.9"
    t_space = ClipboardTableParser.parse_clipboard(space_txt)
    assert len(t_space) == 2
    assert len(t_space[0]) == 3
    assert t_space[0] == [10.5, 20.2, 30.8]
    assert t_space[1] == [40.1, 50.3, 60.9]

    # 2. HTML table from Excel or web
    html_txt = "<table><tr><th>Wavelength (nm)</th><th>Absorbance</th></tr><tr><td>400</td><td>0.125</td></tr><tr><td>500</td><td>0.450</td></tr></table>"
    t_html = ClipboardTableParser.parse_clipboard("", html=html_txt)
    assert len(t_html) == 3
    assert t_html[0] == ["Wavelength (nm)", "Absorbance"]
    assert t_html[1] == [400.0, 0.125]

    has_h, h_names, data_rows = ClipboardTableParser.detect_headers(t_html)
    assert has_h is True
    assert h_names == ["Wavelength (nm)", "Absorbance"]
    assert len(data_rows) == 2

    # 3. Units extraction
    name, units = ClipboardTableParser.extract_name_and_units("Reaction Time (min)")
    assert name == "Reaction Time"
    assert units == "min"

    name, units = ClipboardTableParser.extract_name_and_units("Enzyme Yield [µmol/L]")
    assert name == "Enzyme Yield"
    assert units == "µmol/L"


def test_spreadsheet_paste_from_outside_and_smart_headers(qapp):
    """Verifies that pasting a table from the outside never collapses into a single cell, and auto-detects headers."""
    from omnigraph.ui.spreadsheet_view import SpreadsheetWidget
    from PyQt6.QtWidgets import QApplication

    ws = Worksheet.create_default("PasteTest", num_rows=10)
    sw = SpreadsheetWidget(ws)

    # Simulate user copying a multi-column space-delimited table from terminal or PDF:
    space_table = "1.5   10.2   100.5\n2.5   20.4   200.8\n3.5   30.6   300.2"
    QApplication.clipboard().setText(space_table)

    # Paste into worksheet at cell (0, 0)
    sw.table_view.setCurrentIndex(sw.model.index(0, 0))
    sw.paste_selection()

    assert ws.column_count() >= 3
    # Verify values are distributed across columns and rows, NOT all in cell (0, 0)!
    assert ws.get_cell(0, 0) == 1.5
    assert ws.get_cell(0, 1) == 10.2
    assert ws.get_cell(0, 2) == 100.5

    assert ws.get_cell(1, 0) == 2.5
    assert ws.get_cell(1, 1) == 20.4
    assert ws.get_cell(1, 2) == 200.8

    # Test Undo of paste
    assert sw.undo_stack.canUndo() is True
    sw.undo()
    assert ws.get_cell(0, 0) is None

    # Now simulate user copying a table with Headers from Excel
    excel_table = "Wavelength (nm)\tAbsorbance (OD)\n400\t0.15\n450\t0.35\n500\t0.75"
    QApplication.clipboard().setText(excel_table)
    sw.table_view.setCurrentIndex(sw.model.index(0, 0))
    sw.paste_selection()

    # Headers applied to column metadata
    assert ws.columns[0].long_name == "Wavelength"
    assert ws.columns[0].units == "nm"
    assert ws.columns[0].role == ColumnRole.X

    assert ws.columns[1].long_name == "Absorbance"
    assert ws.columns[1].units == "OD"
    assert ws.columns[1].role == ColumnRole.Y

    # Data starts at row 0 without the header text polluting cell data!
    assert ws.get_cell(0, 0) == 400.0
    assert ws.get_cell(0, 1) == 0.15
    assert ws.get_cell(2, 0) == 500.0
    assert ws.get_cell(2, 1) == 0.75


def test_graph_quick_labels_bar_and_shortcuts(qapp):
    """Verifies that the Quick Labels Bar in GraphViewWidget allows instant, intuitive labeling."""
    from omnigraph.ui.graph_view import GraphViewWidget

    proj = Project.create_default("LabelsTest")
    graph = GraphModel(title="InitialTitle", title_text="InitialTitle", x_title="X Initial", y_title="Y Initial")
    c1 = CurveModel(source_sheet="S1", x_col_idx=0, y_col_idx=1, label="Curve 1")
    graph.curves.append(c1)
    proj.graphs.append(graph)

    gw = GraphViewWidget(graph, proj)

    # 1. Quick labels bar is present and wired
    assert hasattr(gw, "label_bar")
    assert gw.txt_quick_title.text() == "InitialTitle"
    assert gw.txt_quick_x.text() == "X Initial"
    assert gw.txt_quick_y.text() == "Y Initial"

    # 2. Modify via Quick Labels bar and apply
    gw.txt_quick_title.setText("Reaction Kinetics Absorbance")
    gw.txt_quick_x.setText("Time (min)")
    gw.txt_quick_y.setText("Yield (µM)")
    gw._on_quick_label_edited()

    assert graph.title_text == "Reaction Kinetics Absorbance"
    assert graph.x_title == "Time (min)"
    assert graph.y_title == "Yield (µM)"

    # 3. Canvas direct editing methods
    gw.canvas_widget.graph_model.title_text = "Updated via Canvas"
    gw.canvas_widget.labels_changed.emit()

    # Quick labels bar synchronized
    assert gw.txt_quick_title.text() == "Updated via Canvas"




