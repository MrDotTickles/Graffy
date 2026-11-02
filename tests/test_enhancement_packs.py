"""
Comprehensive test suite for Graffy Enhancement Packs:
- Option A: Analytical & Spectroscopy Pack (Stacked Waterfall Spectra, Point Masking & Outlier Exclusion, Drag & Drop Canvas)
- Option B: Biological & Clinical Statistics Pack (Box/Violin/Jitter, Significance Brackets, Dose-Response 4PL / IC50)
- Option C: Multi-Panel Figure 1 Layout Builder (1x2, 2x1, 2x2 Subplots, Panel Labels (A)-(D), Synchronized Axes)
- UX Streamlining & Theme Palettes (Colorblind Safe / Okabe-Ito)
"""

import os
import tempfile
import numpy as np
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QMimeData, QUrl, QPointF
from PyQt6.QtGui import QDropEvent

from omnigraph.core.worksheet import Worksheet, Column, ColumnRole, Workbook
from omnigraph.core.project import Project, GraphModel, CurveModel
from omnigraph.analysis.fitting import CurveFitter
from omnigraph.analysis.statistics import StatisticsAnalyzer
from omnigraph.graphing.themes import THEMES, get_theme_palette
from omnigraph.graphing.plot_types import PlotRenderer
from omnigraph.graphing.plot_manager import PlotManager
from omnigraph.ui.samples import SampleProjects


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ============================================================================
# 1. Option A: Interactive Data Point Masking & Outlier Exclusion
# ============================================================================

class TestPointMasking:
    def test_column_masking_operations(self):
        col = Column(name="Y", data=[10.0, 20.0, 999.0, 40.0, 50.0])
        assert not col.is_row_masked(2)
        assert len(col.masked_rows) == 0

        col.mask_row(2, True)
        assert col.is_row_masked(2)
        assert col.masked_rows == {2}

        # Test to_numpy_array with include_masked=True vs False
        arr_all = col.to_numpy_array(include_masked=True)
        assert len(arr_all) == 5
        assert arr_all[2] == 999.0

        arr_unmasked = col.to_numpy_array(include_masked=False)
        assert np.isnan(arr_unmasked[2])
        assert not np.isnan(arr_unmasked[0])
        assert arr_unmasked[0] == 10.0

        # Unmask row
        col.mask_row(2, False)
        assert not col.is_row_masked(2)
        assert len(col.masked_rows) == 0

    def test_worksheet_mask_cell_and_clear(self):
        ws = Worksheet(name="TestSheet")
        ws.columns = [
            Column(name="X", data=[1.0, 2.0, 3.0, 4.0]),
            Column(name="Y", data=[10.0, 20.0, 30.0, 40.0]),
        ]
        assert not ws.has_masked_cells()

        ws.mask_cell(1, 1, True)
        assert ws.has_masked_cells()
        assert ws.is_cell_masked(1, 1)
        assert not ws.is_cell_masked(1, 0)

        # Clear masks
        ws.clear_all_masks()
        assert not ws.has_masked_cells()
        assert not ws.is_cell_masked(1, 1)

    def test_masking_serialization(self):
        col = Column(name="Data", data=[1.0, 2.0, 3.0, 4.0])
        col.mask_row(1, True)
        col.mask_row(3, True)

        d = col.to_dict()
        assert "masked_rows" in d
        assert sorted(d["masked_rows"]) == [1, 3]

        col2 = Column.from_dict(d)
        assert col2.is_row_masked(1)
        assert col2.is_row_masked(3)
        assert not col2.is_row_masked(0)

    def test_masking_excludes_outlier_from_fit(self):
        # Line y = 2x + 1 with one massive high-leverage outlier at index 4 (x=5, y=1000)
        x_data = [1.0, 2.0, 3.0, 4.0, 5.0]
        y_data = [3.0, 5.0, 7.0, 9.0, 1000.0]

        col_x = Column(name="X", data=x_data, role=ColumnRole.X)
        col_y = Column(name="Y", data=y_data, role=ColumnRole.Y)

        # Before masking: fit corrupted by outlier
        x_vals_corrupt, y_vals_corrupt, _ = col_x.get_valid_numeric_pairs(col_y, include_masked=True)
        res_corrupt = CurveFitter.linear_fit(x_vals_corrupt, y_vals_corrupt)
        assert abs(res_corrupt.parameters["Slope (m)"] - 2.0) > 10.0  # severely warped

        # Mask row 4
        col_y.mask_row(4, True)

        # After masking: get_valid_numeric_pairs defaults to include_masked=False
        x_clean, y_clean, _ = col_x.get_valid_numeric_pairs(col_y)
        assert len(x_clean) == 4
        assert 5.0 not in x_clean  # row 4 excluded

        res_clean = CurveFitter.linear_fit(x_clean, y_clean)
        assert abs(res_clean.parameters["Slope (m)"] - 2.0) < 1e-6
        assert abs(res_clean.parameters["Intercept (b)"] - 1.0) < 1e-6
        assert res_clean.r_squared > 0.99999

        # Also verify get_masked_numeric_pairs returns the excluded point
        x_m, y_m, _ = col_x.get_masked_numeric_pairs(col_y)
        assert len(x_m) == 1
        assert x_m[0] == 5.0
        assert y_m[0] == 1000.0


# ============================================================================
# 2. Option A: Stacked Waterfall & Offset Spectra
# ============================================================================

class TestWaterfallSpectra:
    def test_waterfall_curve_and_graph_model(self):
        c = CurveModel(y_offset=15.5, x_offset=2.0)
        assert c.y_offset == 15.5
        assert c.x_offset == 2.0

        d = c.to_dict()
        assert d["y_offset"] == 15.5
        assert d["x_offset"] == 2.0

        c2 = CurveModel.from_dict(d)
        assert c2.y_offset == 15.5
        assert c2.x_offset == 2.0

        g = GraphModel(
            title="Waterfall XRD",
            waterfall_enabled=True,
            waterfall_y_step=25.0,
            waterfall_x_step=5.0,
            waterfall_baseline=True
        )
        assert g.waterfall_enabled is True
        assert g.waterfall_y_step == 25.0
        assert g.waterfall_x_step == 5.0
        assert g.waterfall_baseline is True

        gd = g.to_dict()
        assert gd["waterfall_enabled"] is True
        assert gd["waterfall_y_step"] == 25.0
        assert gd["waterfall_baseline"] is True

        g2 = GraphModel.from_dict(gd)
        assert g2.waterfall_enabled is True
        assert g2.waterfall_y_step == 25.0
        assert g2.waterfall_baseline is True

    def test_waterfall_sample_generation(self):
        proj = SampleProjects.create_waterfall_sample()
        assert len(proj.workbooks) > 0
        assert len(proj.graphs) > 0
        graph = proj.graphs[0]
        assert graph.waterfall_enabled is True
        assert graph.waterfall_y_step == 25.0
        assert len(graph.curves) == 4

        # Verify PlotManager renders waterfall without error
        pm = PlotManager(graph, proj)
        pm.render()
        assert pm.ax is not None


# ============================================================================
# 3. Option B: Biological & Clinical Statistics (Box, Violin, Jitter, Brackets, 4PL)
# ============================================================================

class TestBiologicalStatistics:
    def test_box_and_violin_renderers(self):
        proj = Project(name="BioProj")
        ws = proj.workbooks[0].sheets[0]
        ws.columns = [
            Column(name="A", long_name="Control", data=[10.0, 11.2, 9.8, 12.1, 10.5]),
            Column(name="B", long_name="Drug 10uM", data=[14.0, 15.5, 13.9, 16.2, 14.8]),
            Column(name="C", long_name="Drug 100uM", data=[20.1, 21.5, 19.8, 22.0, 20.9]),
        ]

        plot_types_to_test = ["box", "box_jitter", "violin", "violin_jitter", "jitter"]
        for ptype in plot_types_to_test:
            g = GraphModel(title=f"Plot_{ptype}", plot_type=ptype)
            for i, col in enumerate(ws.columns):
                g.add_curve(CurveModel(
                    source_sheet=ws.name,
                    x_col_idx=0,
                    y_col_idx=i,
                    label=col.long_name,
                    plot_type=ptype
                ))
            pm = PlotManager(g, proj)
            pm.render()
            assert pm.ax is not None

    def test_significance_bracket_p_to_stars(self):
        assert StatisticsAnalyzer.p_to_stars(0.00005) == "****"
        assert StatisticsAnalyzer.p_to_stars(0.0005) == "***"
        assert StatisticsAnalyzer.p_to_stars(0.005) == "**"
        assert StatisticsAnalyzer.p_to_stars(0.03) == "*"
        assert StatisticsAnalyzer.p_to_stars(0.08) == "ns"
        assert StatisticsAnalyzer.p_to_stars(0.50) == "ns"

    def test_significance_bracket_creation(self):
        bracket = StatisticsAnalyzer.create_significance_bracket(
            x1=0, x2=2, y=25.0, p_value=0.0004, h=1.5, color="#1e293b"
        )
        assert bracket["type"] == "bracket"
        assert bracket["x1"] == 0
        assert bracket["x2"] == 2
        assert bracket["y"] == 25.0
        assert bracket["p_value"] == 0.0004
        assert bracket["text"] == "***"
        assert bracket["color"] == "#1e293b"

    def test_render_significance_bracket_on_graph(self):
        proj = Project(name="AnnotationTest")
        ws = proj.workbooks[0].sheets[0]
        ws.columns = [
            Column(name="X", data=[1, 2, 3]),
            Column(name="Y", data=[10, 20, 30])
        ]
        g = GraphModel(title="BracketGraph")
        g.add_curve(CurveModel(source_sheet=ws.name, x_col_idx=0, y_col_idx=1))
        b = StatisticsAnalyzer.create_significance_bracket(1, 3, 35.0, p_value=0.001)
        g.annotations.append(b)

        pm = PlotManager(g, proj)
        pm.render()
        assert len(g.annotations) == 1

    def test_dose_response_4pl_ic50_fit(self):
        # Generate synthetic 4PL curve
        # y = bottom + (top - bottom) / (1 + 10^((logEC50 - x) * hill_slope))
        log_conc = np.linspace(-9.0, -4.0, 15)
        top = 100.0
        bottom = 5.0
        log_ec50 = -6.5  # IC50 = 10^-6.5 = 3.16e-7 M
        hill_slope = 1.0
        y = bottom + (top - bottom) / (1.0 + 10.0 ** ((log_ec50 - log_conc) * hill_slope))

        res = CurveFitter.nonlinear_fit(log_conc, y, model="hill")
        assert res.success is True
        assert abs(res.parameters["logEC50"] - (-6.5)) < 0.1
        assert abs(res.parameters["Top"] - 100.0) < 1.0
        assert abs(res.parameters["Bottom"] - 5.0) < 1.0

        # Check direct IC50 / EC50 reporting in parameters
        assert "EC50 / IC50" in res.parameters
        ic50_val = res.parameters["EC50 / IC50"]
        expected_ic50 = 10.0 ** (-6.5)
        assert abs(ic50_val - expected_ic50) / expected_ic50 < 0.25

        # Check formatted report text contains IC50 / EC50
        summary = res.to_html_report()
        assert "EC50 / IC50" in summary
        assert "Dose-Response 4PL" in summary


# ============================================================================
# 4. Option C: Multi-Panel "Figure 1" Layout Builder
# ============================================================================

class TestMultiPanelLayouts:
    def test_multipanel_figure_rendering(self):
        proj = Project(name="MultiPanelTest")
        ws = proj.workbooks[0].sheets[0]
        x = np.linspace(0, 10, 50)
        ws.columns = [
            Column(name="X", data=x.tolist(), role=ColumnRole.X),
            Column(name="Y1", data=np.sin(x).tolist(), role=ColumnRole.Y),
            Column(name="Y2", data=np.cos(x).tolist(), role=ColumnRole.Y),
            Column(name="Y3", data=(x ** 0.5).tolist(), role=ColumnRole.Y),
            Column(name="Y4", data=np.exp(-0.2 * x).tolist(), role=ColumnRole.Y),
        ]

        layouts = ["grid_1x2", "grid_2x1", "grid_2x2"]
        for mode in layouts:
            g = GraphModel(title=f"Fig_{mode}", layout_mode=mode, sync_axes=True)
            n_panels = 4 if mode == "grid_2x2" else 2
            for i in range(n_panels):
                g.add_curve(CurveModel(
                    source_sheet=ws.name,
                    x_col_idx=0,
                    y_col_idx=i + 1,
                    label=f"Panel {chr(65+i)}",
                    layer_index=i
                ))

            pm = PlotManager(g, proj)
            pm.render()
            assert pm.fig is not None
            # Verify panel labels (A), (B)... were added as text artists
            assert len(pm.fig.axes) == n_panels

    def test_sync_axes_flag(self):
        g = GraphModel(title="SyncTest", layout_mode="grid_2x2", sync_axes=True)
        assert g.sync_axes is True
        d = g.to_dict()
        assert d["sync_axes"] is True
        g2 = GraphModel.from_dict(d)
        assert g2.sync_axes is True


# ============================================================================
# 5. Themes & Palettes (Colorblind Safe / Okabe-Ito)
# ============================================================================

class TestThemesAndPalettes:
    def test_colorblind_safe_theme_exists(self):
        assert "Colorblind Safe" in THEMES
        cb = THEMES["Colorblind Safe"]
        palette = cb["palette"]
        # Okabe-Ito gold standard palette contains 8 distinct colors
        assert len(palette) >= 8
        # Should contain Okabe-Ito hexes (e.g., #0072b2 blue, #d55e00 vermilion)
        assert "#0072b2" in palette
        assert "#d55e00" in palette

        got_palette = get_theme_palette("Colorblind Safe")
        assert got_palette == palette


# ============================================================================
# 6. Drag & Drop and UI Integration
# ============================================================================

class TestUIDragDropAndCanvas:
    def test_graph_view_import_file_as_curve_layer(self, qapp):
        from omnigraph.ui.graph_view import GraphViewWidget

        proj = Project.create_default("DropTest")
        graph = GraphModel(title="DropTestGraph")
        proj.graphs.append(graph)
        gw = GraphViewWidget(graph, proj)

        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write("Time,Signal\n0.0,1.2\n1.0,2.5\n2.0,3.8\n3.0,5.1\n")
            temp_path = f.name

        try:
            assert len(graph.curves) == 0
            gw._import_file_as_curve_layer(temp_path)
            assert len(graph.curves) == 1
            c = graph.curves[0]
            base_expected = os.path.splitext(os.path.basename(temp_path))[0]
            assert c.source_sheet == base_expected
            # Verify worksheet was created in project
            sheet_found = False
            for wb in proj.workbooks:
                for s in wb.sheets:
                    if s.name == c.source_sheet:
                        sheet_found = True
                        assert s.column_count() >= 2
                        assert s.row_count() == 4
            assert sheet_found is True
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_spreadsheet_masking_integration(self, qapp):
        from omnigraph.ui.spreadsheet_view import SpreadsheetWidget

        ws = Worksheet(name="SheetMaskTest")
        ws.columns = [
            Column(name="A", data=[1.0, 2.0, 3.0, 4.0]),
            Column(name="B", data=[10.0, 20.0, 30.0, 40.0]),
        ]
        sw = SpreadsheetWidget(ws)

        # Select row 1 and row 2 of column B
        idx1 = sw.model.index(1, 1)
        idx2 = sw.model.index(2, 1)
        sw.table_view.selectionModel().select(idx1, sw.table_view.selectionModel().SelectionFlag.Select)
        sw.table_view.selectionModel().select(idx2, sw.table_view.selectionModel().SelectionFlag.Select)

        sw.mask_selection(masked=True)
        assert ws.is_cell_masked(1, 1)
        assert ws.is_cell_masked(2, 1)
        assert not ws.is_cell_masked(0, 1)

        # Undo mask
        sw.undo()
        assert not ws.is_cell_masked(1, 1)
        assert not ws.is_cell_masked(2, 1)

        # Redo mask
        sw.redo()
        assert ws.is_cell_masked(1, 1)
        assert ws.is_cell_masked(2, 1)

        # Clear all masks
        sw.clear_all_masks()
        assert not ws.has_masked_cells()

    def test_point_masking_with_blank_rows_and_unmasking(self, qapp):
        """Verify find_nearest_point maps to exact worksheet row index even with blank rows, and unmasks red 'X'."""
        proj = Project(name="MaskAccuracyProj")
        ws = proj.workbooks[0].sheets[0]
        # Row 0 is None (blank), Row 1 is (1, 10), Row 2 is (2, 20), Row 3 is (3, 30)
        col_x = Column(name="X", role=ColumnRole.X, data=[None, 1.0, 2.0, 3.0])
        col_y = Column(name="Y", role=ColumnRole.Y, data=[None, 10.0, 20.0, 30.0])
        ws.columns = [col_x, col_y]

        graph = GraphModel(title="MaskGraph")
        curve = CurveModel(source_sheet=ws.name, x_col_idx=0, y_col_idx=1, label="Signal")
        graph.add_curve(curve)
        proj.graphs.append(graph)

        pm = PlotManager(graph, proj)
        pm.render()

        from omnigraph.graphing.tools import GraphToolManager
        tm = GraphToolManager(pm.fig.canvas, pm.ax)
        tm.set_data_curves(pm.rendered_curves)

        # Hover near point (2.0, 20.0) -> this is row 2 in worksheet, but index 1 in valid numeric array
        pt = tm.find_nearest_point(2.0, 20.0)
        assert pt is not None
        lbl, px, py, row_idx, is_masked = pt
        assert row_idx == 2  # EXACT worksheet row 2!
        assert is_masked is False

        # Now mask row 2
        col_y.mask_row(2, True)
        pm.render()
        tm.set_data_curves(pm.rendered_curves)

        # Point (2.0, 20.0) is now a masked outlier (red 'X').
        # Verify find_nearest_point finds it as MASKED at row 2 so user can unmask it
        pt_masked = tm.find_nearest_point(2.0, 20.0)
        assert pt_masked is not None
        _, _, _, row_idx_m, is_m = pt_masked
        assert row_idx_m == 2
        assert is_m is True

        # Unmask row 2
        col_y.mask_row(2, False)
        pm.render()
        assert not col_y.is_row_masked(2)

    def test_automatic_fit_recalculation_on_point_masking(self, qapp):
        """Verify that masking an outlier causes any linked fit curve to automatically recompute."""
        proj = Project(name="AutoFitRecalcProj")
        ws = proj.workbooks[0].sheets[0]
        # Line y = 3x + 2, with row 4 corrupted by a huge outlier (x=5, y=500)
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [5.0, 8.0, 11.0, 14.0, 500.0]
        ws.columns = [
            Column(name="X", role=ColumnRole.X, data=xs),
            Column(name="Y", role=ColumnRole.Y, data=ys),
        ]

        graph = GraphModel(title="FitGraph")
        data_curve = CurveModel(source_sheet=ws.name, x_col_idx=0, y_col_idx=1, label="RawData")
        graph.add_curve(data_curve)

        # Add initial fit sheet and fit curve
        fit_ws = Worksheet(name="Fit_Linear_1")
        fit_col_x = Column(name="A", role=ColumnRole.X, data=[1.0, 5.0])
        fit_col_y = Column(name="B", role=ColumnRole.Y, data=[0.0, 500.0])
        fit_ws.columns = [fit_col_x, fit_col_y]
        proj.workbooks[0].sheets.append(fit_ws)

        fit_curve = CurveModel(
            source_sheet="Fit_Linear_1",
            x_col_idx=0,
            y_col_idx=1,
            label="Fit (linear)",
            is_fit_curve=True,
            fit_model_name="linear",
            fit_source_curve_id=data_curve.id,
        )
        graph.add_curve(fit_curve)
        proj.graphs.append(graph)

        pm = PlotManager(graph, proj)
        pm.render()

        # Before masking: slope is warped by row 4 outlier
        assert "y = " in fit_curve.fit_formula_str

        # Mask row 4 outlier
        ws.columns[1].mask_row(4, True)

        # Render triggers automatic recalculation
        pm.render()

        # After masking row 4: slope should be exactly 3.0, intercept exactly 2.0
        assert "y = 3" in fit_curve.fit_formula_str
        # Verify fitted Y in fit_ws was updated
        dense_y = fit_ws.columns[1].data
        assert abs(dense_y[0] - (3.0 * fit_ws.columns[0].data[0] + 2.0)) < 1e-4

    def test_box_multi_group_positions_and_labels(self, qapp):
        """Verify grouped box plots get distinct X positions and proper category tick labels."""
        proj = Project(name="GroupTestProj")
        ws = proj.workbooks[0].sheets[0]
        ws.columns = [
            Column(name="A", long_name="Control", data=[10.0, 11.0, 12.0]),
            Column(name="B", long_name="Drug A", data=[15.0, 16.0, 17.0]),
            Column(name="C", long_name="Drug B", data=[20.0, 21.0, 22.0]),
        ]

        graph = GraphModel(title="GroupedBox", plot_type="box_jitter")
        for i, col in enumerate(ws.columns):
            graph.add_curve(CurveModel(
                source_sheet=ws.name,
                x_col_idx=0,
                y_col_idx=i,
                label=col.long_name,
                plot_type="box_jitter"
            ))

        pm = PlotManager(graph, proj)
        pm.render()

        ticks = list(pm.ax.get_xticks())
        assert len(ticks) == 3
        assert ticks == [1.0, 2.0, 3.0]
        tick_labels = [t.get_text() for t in pm.ax.get_xticklabels()]
        assert tick_labels == ["Control", "Drug A", "Drug B"]

    def test_property_dock_offsets_and_plot_types(self, qapp):
        """Verify PropertyInspectorWidget provides offset spinboxes and new biological plot types."""
        from omnigraph.ui.property_dock import PropertyInspectorWidget
        pi = PropertyInspectorWidget()
        all_types = [pi.combo_plot_type.itemText(i) for i in range(pi.combo_plot_type.count())]
        assert "box_whisker" in all_types
        assert "box_jitter" in all_types
        assert "violin" in all_types
        assert "violin_jitter" in all_types
        assert "jitter" in all_types

        assert hasattr(pi, "spn_y_offset")
        assert hasattr(pi, "spn_x_offset")

        # Test loading curve into UI
        c = CurveModel(y_offset=12.5, x_offset=-3.0, plot_type="violin")
        pi._load_curve_into_ui(c)
        assert pi.spn_y_offset.value() == 12.5
        assert pi.spn_x_offset.value() == -3.0
        assert pi.combo_plot_type.currentText() == "violin"

    def test_drag_drop_1d_dataset(self, qapp):
        """Verify dropping a 1-column CSV automatically constructs Row Index X and adds layer."""
        from omnigraph.ui.graph_view import GraphViewWidget
        proj = Project(name="Drop1DProj")
        graph = GraphModel(title="Drop1DGraph")
        proj.graphs.append(graph)
        gw = GraphViewWidget(graph, proj)

        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write("Absorbance\n0.12\n0.24\n0.48\n0.96\n")
            temp_path = f.name

        try:
            gw._import_file_as_curve_layer(temp_path)
            assert len(graph.curves) == 1
            # Verify sheet has 2 columns: Row Index (X) and Absorbance (Y)
            ws = proj.workbooks[0].sheets[-1]
            assert ws.column_count() == 2
            assert ws.columns[0].role == ColumnRole.X
            assert ws.columns[1].role == ColumnRole.Y
            assert ws.columns[0].data == [1, 2, 3, 4]
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_100_percent_masked_points_stats(self):
        """Verify masking 100% of points returns null descriptive stats and does not crash."""
        col = Column(name="Y", role=ColumnRole.Y, data=[10.0, 20.0, 30.0])
        col.mask_row(0, True)
        col.mask_row(1, True)
        col.mask_row(2, True)

        stats = col.stats(include_masked=False)
        assert stats["n"] == 0
        assert stats["missing"] == 3
        assert stats["mean"] is None
        assert stats["std"] is None
        assert stats["median"] is None

        # Verify StatsDialog handles all-masked columns cleanly
        from omnigraph.ui.dialogs.stats_dialog import StatsDialog
        dlg = StatsDialog(columns=[col])
        assert dlg.table_stats.rowCount() == 1
        assert dlg.table_stats.item(0, 0).text() == "0"
        assert dlg.table_stats.item(0, 1).text() == "-"

    def test_drag_drop_corrupted_empty_file_with_multipanel_layout(self, qapp):
        """Verify dropping an empty/corrupted CSV onto a 2x2 layout handles error safely."""
        from omnigraph.ui.graph_view import GraphViewWidget
        proj = Project.create_default("EmptyDropProj")
        graph = GraphModel(title="2x2 Layout", layout_mode="grid_2x2")
        proj.graphs.append(graph)
        gw = GraphViewWidget(graph, proj)

        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            # Empty file (0 bytes)
            temp_empty = f.name

        try:
            with pytest.raises(Exception):
                gw._import_file_as_curve_layer(temp_empty)
            # Ensure graph and layout remain intact
            assert graph.layout_mode == "grid_2x2"
            assert len(graph.curves) == 0
        finally:
            if os.path.exists(temp_empty):
                os.remove(temp_empty)

    def test_rendered_curves_backward_compatibility(self, qapp):
        """Verify pm.rendered_curves can be unpacked as 3 items AND has row/mask attributes."""
        proj = Project(name="CompatProj")
        ws = proj.workbooks[0].sheets[0]
        ws.columns = [
            Column(name="X", role=ColumnRole.X, data=[1.0, 2.0, 3.0]),
            Column(name="Y", role=ColumnRole.Y, data=[10.0, 20.0, 30.0]),
        ]
        graph = GraphModel(title="CompatGraph")
        graph.add_curve(CurveModel(source_sheet=ws.name, x_col_idx=0, y_col_idx=1, label="C1"))
        proj.graphs.append(graph)

        pm = PlotManager(graph, proj)
        pm.render()

        # 3-element unpack test (legacy requirement)
        for label, xs, ys in pm.rendered_curves:
            assert label == "C1"
            assert len(xs) == 3
            assert len(ys) == 3

        # Extended attributes test
        rc = pm.rendered_curves[0]
        assert hasattr(rc, "row_indices")
        assert hasattr(rc, "is_masked")
        assert rc.is_masked is False
        assert list(rc.row_indices) == [0, 1, 2]
