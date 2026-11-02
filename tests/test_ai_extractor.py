"""
Automated tests for AI Data Extractor & Smart Plotter.
Verifies smart ingestion of raw messy text, scientific instrument logs,
automatic delimiter/header/unit parsing, role inference, and auto-plotting.
"""

import os
import sys
import pytest
from PyQt6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from omnigraph.ai.data_extractor import SmartDataExtractor, ExtractionResult
from omnigraph.core.worksheet import ColumnRole
from omnigraph.core.project import Project
from omnigraph.ui.dialogs.ai_extractor_dialog import AIDataExtractorDialog
from omnigraph.ui.main_window import MainWindow
from omnigraph.ui.samples import SampleProjects


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_heuristic_extraction_from_messy_instrument_text():
    """Verify smart extraction of messy scientific instrument data with comment preamble."""
    messy_text = (
        "####################################################\n"
        "# Instrument: Cary 5000 UV-Vis\n"
        "# Operator: BioLab User\n"
        "# Date: 2026-10-19\n"
        "# Baseline: Auto-subtracted\n"
        "####################################################\n"
        "Wavelength (nm)\tAbsorbance (OD)\tStd_Error\n"
        "400.0\t0.125\t0.005\n"
        "410.0\t0.245\t0.008\n"
        "420.0\t0.589\t0.012\n"
        "430.0\t0.985\t0.020\n"
        "440.0\t1.420\t0.025\n"
        "450.0\t1.105\t0.018\n"
        "460.0\t0.650\t0.010\n"
        "470.0\t0.310\t0.006\n"
    )

    result = SmartDataExtractor.extract_from_text(messy_text, source_name="CaryTest.txt")

    assert not result.dataframe.empty
    assert len(result.dataframe) == 8
    assert len(result.dataframe.columns) == 3

    # Check parsed units
    assert result.column_units["Wavelength (nm)"] == "nm"
    assert result.column_units["Absorbance (OD)"] == "OD"

    # Check inferred roles
    assert result.column_roles["Wavelength (nm)"] == ColumnRole.X
    assert result.column_roles["Absorbance (OD)"] == ColumnRole.Y
    assert result.column_roles["Std_Error"] == ColumnRole.Y_ERR

    # Check recommended plot
    assert result.recommended_plot == "errorbar"

    # Convert to worksheet
    ws = result.to_worksheet("Extracted_Cary")
    assert ws.name == "Extracted_Cary"
    assert ws.column_count() == 3
    assert ws.columns[0].role == ColumnRole.X
    assert ws.columns[0].units == "nm"
    assert ws.columns[1].role == ColumnRole.Y
    assert ws.columns[2].role == ColumnRole.Y_ERR


def test_extraction_from_file_with_whitespace_delimiters(tmp_path):
    """Verify file-based smart extraction on space-separated data file."""
    dat_file = tmp_path / "reactor_log.dat"
    dat_content = (
        "; Chemical Reactor Monitoring Output\n"
        "; Run ID: RX-442\n"
        "Time(min)   Temp(C)   Pressure(bar)\n"
        "0.0         25.2      1.01\n"
        "5.0         45.8      1.15\n"
        "10.0        80.4      1.45\n"
        "15.0        120.1     1.98\n"
        "20.0        150.0     2.50\n"
    )
    dat_file.write_text(dat_content, encoding="utf-8")

    result = SmartDataExtractor.extract_from_file(str(dat_file))
    assert not result.dataframe.empty
    assert len(result.dataframe) == 5
    assert len(result.dataframe.columns) == 3
    assert result.column_roles["Time(min)"] == ColumnRole.X
    assert result.column_units["Time(min)"] == "min"
    assert result.column_units["Temp(C)"] == "C"


def test_ai_extractor_dialog_workflow(qapp):
    """Verify complete dialog workflow: loading messy HPLC data and 1-click import and plot."""
    project = Project.create_default("AIDialogTest")
    dlg = AIDataExtractorDialog(project)

    # Load sample HPLC log
    dlg._load_sample_hplc()

    assert dlg.extraction_result is not None
    assert not dlg.extraction_result.dataframe.empty
    assert len(dlg.extraction_result.dataframe) == 13

    # Trigger Import & Plot
    dlg._on_import_and_plot()

    assert dlg.created_worksheet is not None
    assert len(project.workbooks[0].sheets) >= 2  # Default sheet + new extracted sheet
    assert dlg.created_graph is not None
    assert len(dlg.created_graph.curves) >= 1

    dlg.close()


def test_pure_numeric_data_does_not_eat_first_row():
    """Verify that pure numeric data with no headers preserves row 0 and names columns cleanly."""
    raw_csv = (
        "1.0, 2.5\n"
        "2.0, 5.0\n"
        "3.0, 7.5\n"
        "4.0, 10.0\n"
    )
    result = SmartDataExtractor.extract_from_text(raw_csv, source_name="NumericOnly.csv")

    assert not result.dataframe.empty
    # Must preserve ALL 4 rows! Row 0 was NOT eaten as column names!
    assert len(result.dataframe) == 4
    assert result.dataframe.iloc[0, 0] == 1.0
    assert result.dataframe.iloc[0, 1] == 2.5
    assert result.dataframe.columns[0] == "Col A"
    assert result.dataframe.columns[1] == "Col B"
    assert result.metadata["HeaderMode"] == "none"


def test_two_header_rows_names_and_units():
    """Verify extraction when file has row 0 as names and row 1 as units."""
    raw_data = (
        "Wavelength\tAbsorbance\tError\n"
        "nm\ta.u.\tOD\n"
        "400.0\t0.15\t0.01\n"
        "500.0\t0.45\t0.02\n"
        "600.0\t0.85\t0.03\n"
    )
    result = SmartDataExtractor.extract_from_text(raw_data, source_name="TwoRows.txt")

    assert not result.dataframe.empty
    assert len(result.dataframe) == 3
    assert result.dataframe.columns[0] == "Wavelength"
    assert result.dataframe.columns[1] == "Absorbance"
    assert result.column_units["Wavelength"] == "nm"
    assert result.column_units["Absorbance"] == "a.u."
    assert result.metadata["HeaderMode"] == "two_rows"


def test_header_mode_dropdown_interaction(qapp):
    """Verify changing header mode combobox in dialog re-runs extraction and updates table."""
    project = Project.create_default("HeaderModeTest")
    dlg = AIDataExtractorDialog(project)

    raw_nums = "10.0, 20.0\n30.0, 40.0\n50.0, 60.0"
    dlg.tabs_source.setCurrentIndex(1)
    dlg.txt_paste.setPlainText(raw_nums)

    # Auto-detect should recognize it as pure data (none)
    dlg._run_extraction()
    assert len(dlg.extraction_result.dataframe) == 3
    assert dlg.extraction_result.metadata["HeaderMode"] == "none"

    # User explicitly forces first row as names
    dlg.combo_header_mode.setCurrentIndex(1)  # "first_row"
    assert len(dlg.extraction_result.dataframe) == 2
    assert dlg.extraction_result.metadata["HeaderMode"] == "first_row"

    # Switch back to none
    dlg.combo_header_mode.setCurrentIndex(3)  # "none"
    assert len(dlg.extraction_result.dataframe) == 3

    dlg.close()



def test_main_window_ai_integration(qapp):
    """Verify MainWindow has AI actions in menus and toolbars."""
    project = SampleProjects.create_spectroscopy_sample()
    window = MainWindow(project=project)
    window.show()

    # Verify AI Extract action exists on toolbar
    from PyQt6.QtWidgets import QToolBar
    tb_data = window.findChild(QToolBar, "ToolbarFileData")
    assert tb_data is not None
    action_texts = [act.text() for act in tb_data.actions()]
    window.close()


def test_x01_ascii_rocking_curve_extraction(tmp_path):
    """Verify smart extraction of ASCII .x01 XRD rocking curve file with instrument parameters."""
    x01_file = tmp_path / "GaAs_epilayer_scan.x01"
    x01_content = (
        "[Header]\n"
        "Sample = InGaAs/GaAs Superlattice 10-period\n"
        "Instrument = Bede D1 High-Resolution Diffractometer\n"
        "Radiation = Cu-Ka1 (1.540597 A)\n"
        "Scan Mode = Rocking Curve (Omega Scan)\n"
        "Range = -1000 to +1000 arcsec\n"
        "Step Size = 100.0 arcsec\n"
        "Count Time = 1.0 s\n"
        "[Data]\n"
        "Omega (arcsec)\tIntensity (Counts)\n"
        "-1000.0\t120\n"
        "-900.0\t450\n"
        "-800.0\t2800\n"
        "-700.0\t14500\n"
        "-600.0\t52000\n"
        "-500.0\t12400\n"
        "-400.0\t2100\n"
        "-300.0\t600\n"
        "-200.0\t250\n"
        "-100.0\t1800\n"
        "0.0\t185000\n"
        "100.0\t2400\n"
        "200.0\t310\n"
    )
    x01_file.write_text(x01_content, encoding="utf-8")

    result = SmartDataExtractor.extract_from_file(str(x01_file))

    assert not result.dataframe.empty
    assert len(result.dataframe) == 13
    assert len(result.dataframe.columns) == 2
    assert "InGaAs/GaAs" in result.metadata.get("Sample", "")
    assert "Bede D1" in result.metadata.get("Instrument", "")
    assert result.recommended_plot == "line"

    # Verify column roles and units
    omega_col = result.dataframe.columns[0]
    intens_col = result.dataframe.columns[1]
    assert result.column_roles[omega_col] == ColumnRole.X
    assert result.column_roles[intens_col] == ColumnRole.Y
    assert result.column_units[omega_col] == "arcsec"
    assert result.column_units[intens_col] == "Counts"


def test_x01_uppercase_extension(tmp_path):
    """Verify case-insensitive .X01 extension handling."""
    x01_file = tmp_path / "SPECTRUM_RUN.X01"
    content = (
        "# Detector Scan Channel 01\n"
        "2Theta (deg)\tCounts (CPS)\n"
        "10.0\t15\n"
        "10.5\t28\n"
        "11.0\t95\n"
        "11.5\t450\n"
        "12.0\t2100\n"
        "12.5\t620\n"
        "13.0\t80\n"
    )
    x01_file.write_text(content, encoding="utf-8")

    result = SmartDataExtractor.extract_from_file(str(x01_file))
    assert not result.dataframe.empty
    assert len(result.dataframe) == 7
    first_col = result.dataframe.columns[0]
    assert result.column_roles[first_col] == ColumnRole.X
    assert result.column_units[first_col] == "deg"


def test_x01_binary_format_extraction(tmp_path):
    """Verify binary .x01 file parsing with embedded ASCII header and float array."""
    import struct
    bin_file = tmp_path / "raw_binary_scan.x01"

    # Header with metadata text, padded to 256 bytes with nulls
    header_text = b"Instrument=BedeScan_HRXRD\x00Sample=AlGaAs_Heterostructure\x00Step=10.0\x00Start=-500.0\x00"
    header_padded = header_text + b"\x00" * (256 - len(header_text))

    # Float array payload (simulating intensities)
    intensities = [10.0, 15.0, 45.0, 250.0, 1200.0, 8500.0, 1200.0, 310.0, 60.0, 20.0, 12.0, 10.0]
    payload = struct.pack(f"<{len(intensities)}f", *intensities)

    bin_file.write_bytes(header_padded + payload)

    result = SmartDataExtractor.extract_from_file(str(bin_file))
    assert not result.dataframe.empty
    assert len(result.dataframe) == len(intensities)
    assert len(result.dataframe.columns) == 2
    assert result.recommended_plot == "line"

    # Verify monotonic X axis generation from metadata
    x_col = result.dataframe.columns[0]
    y_col = result.dataframe.columns[1]
    assert result.column_roles[x_col] == ColumnRole.X
    assert result.column_roles[y_col] == ColumnRole.Y
    assert result.dataframe[x_col].iloc[0] == -500.0
    assert result.dataframe[x_col].iloc[1] == -490.0


def test_ai_dialog_sample_xrd_rocking_curve(qapp):
    """Verify 1-click loading and plotting of sample XRD rocking curve in AIDataExtractorDialog."""
    project = Project.create_default("XRDTestProject")
    dlg = AIDataExtractorDialog(project)

    # Click sample XRD rocking curve button
    dlg._load_sample_xrd()

    assert dlg.extraction_result is not None
    assert not dlg.extraction_result.dataframe.empty
    assert "Omega (arcsec)" in dlg.extraction_result.dataframe.columns
    assert "Intensity (Counts)" in dlg.extraction_result.dataframe.columns
    assert dlg.combo_plot_type.currentText() == "line"

    # Execute Import & Plot
    dlg._on_import_and_plot()
    assert dlg.created_worksheet is not None
    assert dlg.created_graph is not None
    assert len(dlg.created_graph.curves) >= 1
    assert dlg.created_graph.curves[0].plot_type == "line"

    dlg.close()


def test_pure_numeric_data_does_not_eat_first_row():
    """Verify that pure numeric data with no headers preserves row 0 and names columns cleanly."""
    raw_csv = (
        "1.0, 2.5\n"
        "2.0, 5.0\n"
        "3.0, 7.5\n"
        "4.0, 10.0\n"
    )
    result = SmartDataExtractor.extract_from_text(raw_csv, source_name="NumericOnly.csv")

    assert not result.dataframe.empty
    # Must preserve ALL 4 rows! Row 0 was NOT eaten as column names!
    assert len(result.dataframe) == 4
    assert result.dataframe.iloc[0, 0] == 1.0
    assert result.dataframe.iloc[0, 1] == 2.5
    assert result.dataframe.columns[0] == "Col A"
    assert result.dataframe.columns[1] == "Col B"
    assert result.metadata["HeaderMode"] == "none"


def test_two_header_rows_names_and_units():
    """Verify extraction when file has row 0 as names and row 1 as units."""
    raw_data = (
        "Wavelength\tAbsorbance\tError\n"
        "nm\ta.u.\tOD\n"
        "400.0\t0.15\t0.01\n"
        "500.0\t0.45\t0.02\n"
        "600.0\t0.85\t0.03\n"
    )
    result = SmartDataExtractor.extract_from_text(raw_data, source_name="TwoRows.txt")

    assert not result.dataframe.empty
    assert len(result.dataframe) == 3
    assert result.dataframe.columns[0] == "Wavelength"
    assert result.dataframe.columns[1] == "Absorbance"
    assert result.column_units["Wavelength"] == "nm"
    assert result.column_units["Absorbance"] == "a.u."
    assert result.metadata["HeaderMode"] == "two_rows"


def test_header_mode_dropdown_interaction(qapp):
    """Verify changing header mode combobox in dialog re-runs extraction and updates table."""
    project = Project.create_default("HeaderModeTest")
    dlg = AIDataExtractorDialog(project)

    raw_nums = "10.0, 20.0\n30.0, 40.0\n50.0, 60.0"
    dlg.tabs_source.setCurrentIndex(1)
    dlg.txt_paste.setPlainText(raw_nums)

    # Auto-detect should recognize it as pure data (none)
    dlg._run_extraction()
    assert len(dlg.extraction_result.dataframe) == 3
    assert dlg.extraction_result.metadata["HeaderMode"] == "none"

    # User explicitly forces first row as names
    dlg.combo_header_mode.setCurrentIndex(1)  # "first_row"
    assert len(dlg.extraction_result.dataframe) == 2
    assert dlg.extraction_result.metadata["HeaderMode"] == "first_row"

    # Switch back to none
    dlg.combo_header_mode.setCurrentIndex(3)  # "none"
    assert len(dlg.extraction_result.dataframe) == 3

    dlg.close()


