"""
Built-in scientific sample datasets and project templates.
Enables immediate experimentation with real-world scientific data.
"""

import numpy as np
from omnigraph.core.worksheet import Worksheet, Column, ColumnRole, Workbook
from omnigraph.core.project import Project, GraphModel, CurveModel


class SampleProjects:
    """Generates scientific example projects."""

    @staticmethod
    def create_spectroscopy_sample() -> Project:
        """UV-Vis / Raman spectrum with multiple overlapping peaks."""
        proj = Project(name="UV-Vis Spectroscopy Sample")
        wb = proj.workbooks[0]
        wb.name = "SpectraBook"
        ws = wb.sheets[0]
        ws.name = "Absorbance"

        # Generate data
        x = np.linspace(350, 750, 201)
        # Baseline + 3 peaks
        baseline = 0.05 + 0.0001 * (x - 350)
        p1 = 0.45 * np.exp(-0.5 * ((x - 440) / 18) ** 2)
        p2 = 0.85 * np.exp(-0.5 * ((x - 520) / 25) ** 2)
        p3 = 0.60 * np.exp(-0.5 * ((x - 610) / 20) ** 2)
        noise = np.random.normal(0, 0.008, len(x))
        y = baseline + p1 + p2 + p3 + noise

        col_x = Column(name="A", long_name="Wavelength", units="nm", role=ColumnRole.X, data=x.tolist())
        col_y = Column(name="B", long_name="Absorbance", units="a.u.", role=ColumnRole.Y, data=y.tolist())
        ws.columns = [col_x, col_y]

        # Create Graph
        graph = GraphModel(title="Spectra Graph", plot_type="line")
        graph.x_title = "Wavelength (nm)"
        graph.y_title = "Absorbance (a.u.)"
        graph.title_text = "UV-Vis Absorption Spectrum"
        curve = CurveModel(
            source_workbook=wb.name,
            source_sheet=ws.name,
            x_col_idx=0,
            y_col_idx=1,
            label="Sample Protein Complex",
            color="#0284c7",
            line_style="-",
            line_width=2.0,
            marker="none",
            plot_type="line",
        )
        graph.add_curve(curve)
        proj.graphs.append(graph)
        return proj

    @staticmethod
    def create_enzyme_kinetics_sample() -> Project:
        """Enzyme Michaelis-Menten Kinetics with Error bars."""
        proj = Project(name="Enzyme Kinetics Sample")
        wb = proj.workbooks[0]
        ws = wb.sheets[0]
        ws.name = "KineticsData"

        s_conc = np.array([0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 40.0, 80.0])
        # V = (Vmax * [S]) / (Km + [S]) with Vmax=50, Km=8
        v_true = (50.0 * s_conc) / (8.0 + s_conc)
        y_err = 0.05 * v_true + 0.4
        y_obs = v_true + np.random.normal(0, y_err, len(s_conc))

        col_s = Column(name="A", long_name="Substrate [S]", units="mM", role=ColumnRole.X, data=s_conc.tolist())
        col_v = Column(name="B", long_name="Initial Rate V0", units="μmol/min", role=ColumnRole.Y, data=y_obs.tolist())
        col_err = Column(name="C", long_name="Rate Error", units="μmol/min", role=ColumnRole.Y_ERR, data=y_err.tolist())
        ws.columns = [col_s, col_v, col_err]

        graph = GraphModel(title="Kinetics Curve", plot_type="errorbar")
        graph.x_title = "Substrate Concentration [S] (mM)"
        graph.y_title = "Initial Velocity V0 (μmol/min)"
        graph.title_text = "Enzyme Saturation Kinetics"
        curve = CurveModel(
            source_workbook=wb.name,
            source_sheet=ws.name,
            x_col_idx=0,
            y_col_idx=1,
            y_err_col_idx=2,
            label="Wild-Type Enzyme",
            color="#d62728",
            marker="o",
            marker_size=6.5,
            marker_face_color="#ffffff",
            marker_edge_color="#d62728",
            marker_edge_width=1.5,
            plot_type="errorbar",
        )
        graph.add_curve(curve)
        proj.graphs.append(graph)
        return proj

    @staticmethod
    def create_dose_response_sample() -> Project:
        """Pharmacology Sigmoidal Dose-Response / IC50 Curve."""
        proj = Project(name="Dose-Response Assay")
        wb = proj.workbooks[0]
        ws = wb.sheets[0]
        ws.name = "Inhibition"

        log_conc = np.linspace(-9, -4, 11)  # 1 nM to 100 μM
        # Hill equation: bottom=5, top=100, logEC50=-6.5, slope=1.0
        response = 5.0 + (100.0 - 5.0) / (1.0 + 10.0 ** (-6.5 - log_conc))
        noise = np.random.normal(0, 2.5, len(log_conc))
        y_obs = np.clip(response + noise, 0, 105)

        col_x = Column(name="A", long_name="Log[Inhibitor]", units="M", role=ColumnRole.X, data=log_conc.tolist())
        col_y = Column(name="B", long_name="Cell Viability", units="%", role=ColumnRole.Y, data=y_obs.tolist())
        ws.columns = [col_x, col_y]

        graph = GraphModel(title="Dose Response Plot", plot_type="scatter")
        graph.x_title = "Log [Inhibitor] (M)"
        graph.y_title = "Normalized Viability (%)"
        graph.title_text = "In Vitro Cytotoxicity Assay (IC50)"
        curve = CurveModel(
            source_workbook=wb.name,
            source_sheet=ws.name,
            x_col_idx=0,
            y_col_idx=1,
            label="Compound A",
            color="#059669",
            marker="s",
            marker_size=7.0,
            marker_face_color="#059669",
            plot_type="scatter",
        )
        graph.add_curve(curve)
        proj.graphs.append(graph)
        return proj

    @staticmethod
    def create_dual_axis_sample() -> Project:
        """Dual Y-Axis (Temperature & Pressure vs Time)."""
        proj = Project(name="Dual-Axis Reactor Profile")
        wb = proj.workbooks[0]
        ws = wb.sheets[0]
        ws.name = "ReactorData"

        time_min = np.linspace(0, 60, 31)
        temp_c = 25.0 + 150.0 * (1.0 - np.exp(-time_min / 12.0)) + np.random.normal(0, 1.0, len(time_min))
        press_bar = 1.0 + 8.5 * (1.0 - np.exp(-time_min / 18.0)) + np.random.normal(0, 0.15, len(time_min))

        col_t = Column(name="A", long_name="Reaction Time", units="min", role=ColumnRole.X, data=time_min.tolist())
        col_temp = Column(name="B", long_name="Temperature", units="°C", role=ColumnRole.Y, data=temp_c.tolist())
        col_press = Column(name="C", long_name="Pressure", units="bar", role=ColumnRole.Y, data=press_bar.tolist())
        ws.columns = [col_t, col_temp, col_press]

        graph = GraphModel(title="Reactor Profile", plot_type="line_symbol")
        graph.x_title = "Time (min)"
        graph.y_title = "Temperature (°C)"
        graph.y2_title = "Pressure (bar)"
        graph.title_text = "Chemical Reactor Operating Parameters"

        c1 = CurveModel(
            source_workbook=wb.name,
            source_sheet=ws.name,
            x_col_idx=0,
            y_col_idx=1,
            label="Reactor Temp (°C)",
            color="#d62728",
            axis="primary",
            marker="o",
            marker_size=5.0,
            line_style="-",
            plot_type="line_symbol",
        )
        c2 = CurveModel(
            source_workbook=wb.name,
            source_sheet=ws.name,
            x_col_idx=0,
            y_col_idx=2,
            label="Chamber Pressure (bar)",
            color="#1f77b4",
            axis="secondary",
            marker="s",
            marker_size=5.0,
            line_style="--",
            plot_type="line_symbol",
        )
        graph.add_curve(c1)
        graph.add_curve(c2)
        proj.graphs.append(graph)
        return proj

    @staticmethod
    def create_waterfall_sample() -> Project:
        """Stacked Waterfall / Offset XRD/FTIR/Raman Spectra."""
        proj = Project(name="Stacked Spectroscopy Sample")
        wb = proj.workbooks[0]
        wb.name = "SpectraBook"
        ws = wb.sheets[0]
        ws.name = "StackedSeries"

        x = np.linspace(400, 1800, 250)
        col_x = Column(name="A", long_name="Raman Shift", units="cm⁻¹", role=ColumnRole.X, data=x.tolist())
        cols = [col_x]

        labels = ["T = 0 min", "T = 30 min", "T = 60 min", "T = 120 min"]
        peak_growths = [0.2, 0.5, 0.9, 1.4]
        for idx, (label, factor) in enumerate(zip(labels, peak_growths)):
            col_letter = chr(66 + idx)
            baseline = 5.0 + 0.002 * (x - 400)
            p1 = factor * 20.0 * np.exp(-0.5 * ((x - 850) / 30) ** 2)
            p2 = (1.5 - factor * 0.4) * 15.0 * np.exp(-0.5 * ((x - 1340) / 45) ** 2)
            p3 = factor * 35.0 * np.exp(-0.5 * ((x - 1600) / 25) ** 2)
            noise = np.random.normal(0, 0.3, len(x))
            y = baseline + p1 + p2 + p3 + noise
            cols.append(Column(name=col_letter, long_name=label, units="Counts", role=ColumnRole.Y, data=y.tolist()))

        ws.columns = cols

        graph = GraphModel(
            title="Waterfall Spectra",
            plot_type="line",
            waterfall_enabled=True,
            waterfall_y_step=25.0,
            waterfall_x_step=0.0,
            waterfall_baseline=True,
        )
        graph.x_title = "Raman Shift (cm⁻¹)"
        graph.y_title = "Intensity (Offset Counts)"
        graph.title_text = "Time-Resolved In Situ Raman Monitoring"

        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
        for idx, label in enumerate(labels):
            curve = CurveModel(
                source_workbook=wb.name,
                source_sheet=ws.name,
                x_col_idx=0,
                y_col_idx=idx + 1,
                label=label,
                color=colors[idx % len(colors)],
                line_width=1.8,
                plot_type="line",
            )
            graph.add_curve(curve)

        proj.graphs.append(graph)
        return proj

    @staticmethod
    def create_bio_stats_sample() -> Project:
        """Biological Replicate Comparison (Box, Violin, Jitter & Brackets)."""
        proj = Project(name="Bio Statistics Sample")
        wb = proj.workbooks[0]
        ws = wb.sheets[0]
        ws.name = "AssayReplicates"

        np.random.seed(42)
        n = 30
        ctrl = np.random.normal(10.0, 1.5, n)
        treat_a = np.random.normal(14.5, 2.0, n)
        treat_b = np.random.normal(21.0, 2.8, n)

        col_a = Column(name="A", long_name="Vehicle Control", units="pg/mL", role=ColumnRole.Y, data=ctrl.tolist())
        col_b = Column(name="B", long_name="Compound 10 nM", units="pg/mL", role=ColumnRole.Y, data=treat_a.tolist())
        col_c = Column(name="C", long_name="Compound 100 nM", units="pg/mL", role=ColumnRole.Y, data=treat_b.tolist())
        ws.columns = [col_a, col_b, col_c]

        graph = GraphModel(title="Biomarker Response", plot_type="box_jitter")
        graph.x_title = "Experimental Group"
        graph.y_title = "Cytokine Secretion (pg/mL)"
        graph.title_text = "Treatment Group Comparison with Jitter"

        colors = ["#475569", "#0284c7", "#e11d48"]
        for idx, c in enumerate(ws.columns):
            curve = CurveModel(
                source_workbook=wb.name,
                source_sheet=ws.name,
                x_col_idx=0,
                y_col_idx=idx,
                label=c.long_name,
                color=colors[idx % len(colors)],
                plot_type="box_jitter",
            )
            graph.add_curve(curve)

        # Add a significance bracket between group 1 and 3 (Vehicle Control vs Compound 100 nM)
        from omnigraph.analysis.statistics import StatisticsAnalyzer
        bracket = StatisticsAnalyzer.create_significance_bracket(1.0, 3.0, 26.0, 0.0001, h=1.0)
        graph.annotations.append(bracket)

        proj.graphs.append(graph)
        return proj

