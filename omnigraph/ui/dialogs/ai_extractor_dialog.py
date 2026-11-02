"""
AI Data Extractor & Smart Plotter Dialog.
Allows users to drag & drop or select ANY file (or paste messy text),
automatically extracts numeric tables and column metadata, and plots it in 1 click.
"""

import os
import re
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QTabWidget, QTextEdit, QTableView, QComboBox, QCheckBox,
    QGroupBox, QDialogButtonBox, QMessageBox, QSplitter, QHeaderView, QWidget,
    QApplication
)
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QEvent
from PyQt6.QtGui import QColor, QFont

from omnigraph.ai.data_extractor import SmartDataExtractor, ExtractionResult
from omnigraph.core.project import Project, GraphModel, CurveModel
from omnigraph.core.worksheet import Workbook, Worksheet, ColumnRole


class ExtractedPreviewModel(QAbstractTableModel):
    """Table model displaying extracted DataFrame with metadata in headers."""

    def __init__(self, result: Optional[ExtractionResult] = None):
        super().__init__()
        self.result = result

    def set_result(self, result: ExtractionResult):
        self.beginResetModel()
        self.result = result
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        if self.result is None or self.result.dataframe.empty:
            return 0
        return min(len(self.result.dataframe), 200)

    def columnCount(self, parent=QModelIndex()) -> int:
        if self.result is None or self.result.dataframe.empty:
            return 0
        return len(self.result.dataframe.columns)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or self.result is None:
            return None

        val = self.result.dataframe.iloc[index.row(), index.column()]
        if role == Qt.ItemDataRole.DisplayRole:
            if val is None or (isinstance(val, float) and (val != val)):
                return ""
            if isinstance(val, float):
                return f"{val:.5g}"
            return str(val)

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):
        if self.result is None or self.result.dataframe.empty:
            return None

        if orientation == Qt.Orientation.Horizontal:
            col_name = self.result.dataframe.columns[section]
            role_enum = self.result.column_roles.get(col_name, ColumnRole.Y)
            unit = self.result.column_units.get(col_name, "")
            unit_str = f"\n[{unit}]" if unit else ""

            if role == Qt.ItemDataRole.DisplayRole:
                return f"{col_name} ({role_enum.value}){unit_str}"
            elif role == Qt.ItemDataRole.ForegroundRole:
                app = QApplication.instance()
                is_dark = getattr(app, "is_dark_theme", False) or "background-color: #181825" in (app.styleSheet() if app else "")
                if role_enum == ColumnRole.X:
                    return QColor("#38bdf8" if is_dark else "#0369a1")
                elif role_enum == ColumnRole.Y_ERR:
                    return QColor("#f59e0b" if is_dark else "#b45309")
                return QColor("#cdd6f4" if is_dark else "#0f172a")

        elif orientation == Qt.Orientation.Vertical:
            if role == Qt.ItemDataRole.DisplayRole:
                return str(section + 1)

        return None


class AIDataExtractorDialog(QDialog):
    """Interactive AI modal to extract data from any file and plot it."""

    def __init__(self, project: Project, active_graph: Optional[GraphModel] = None, parent=None):
        super().__init__(parent)
        self.project = project
        self.active_graph = active_graph
        self.extraction_result: Optional[ExtractionResult] = None
        self.created_worksheet: Optional[Worksheet] = None
        self.created_graph: Optional[GraphModel] = None

        self.setWindowTitle("🤖 AI Data Extractor & Smart Plotter")
        self.resize(780, 580)
        self.setMinimumSize(660, 480)
        self.setAcceptDrops(True)
        self.setObjectName("AIDataExtractorDialog")
        self._apply_theme_style()
        self._init_ui()

    def _apply_theme_style(self):
        app = QApplication.instance()
        is_dark = getattr(app, "is_dark_theme", False) or "background-color: #181825" in (app.styleSheet() if app else "")
        if is_dark:
            self.setStyleSheet("""
                QDialog {
                    background-color: #181825;
                }
                QLabel {
                    color: #cdd6f4;
                    font-weight: 600;
                }
                QGroupBox {
                    border: 1.5px solid #313244;
                    border-radius: 6px;
                    margin-top: 14px;
                    padding: 12px 8px 8px 8px;
                    background-color: #1e1e2e;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 1px 8px;
                    color: #89b4fa;
                    font-weight: 700;
                    background-color: #1e1e2e;
                    border: 1px solid #313244;
                    border-radius: 3px;
                }
                QGroupBox QLabel, QGroupBox QCheckBox {
                    color: #cdd6f4;
                    font-weight: 600;
                }
                QLineEdit, QComboBox {
                    background-color: #181825;
                    color: #cdd6f4;
                    border: 1.5px solid #45475a;
                    border-radius: 4px;
                    padding: 5px 8px;
                    font-weight: 500;
                }
                QTabWidget::pane {
                    border: 1.5px solid #313244;
                    background-color: #1e1e2e;
                    border-radius: 4px;
                }
                QTabBar::tab {
                    background-color: #181825;
                    color: #cdd6f4;
                    font-weight: 700;
                    font-size: 11px;
                    padding: 6px 14px;
                    margin-right: 2px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                    border: 1px solid #313244;
                }
                QTabBar::tab:selected {
                    background-color: #1e1e2e;
                    color: #89b4fa;
                    border-bottom: 2px solid #89b4fa;
                }
                QTableView {
                    background-color: #181825;
                    alternate-background-color: #1e1e2e;
                    gridline-color: #313244;
                    color: #cdd6f4;
                    border: 1.5px solid #313244;
                    border-radius: 4px;
                    selection-background-color: #45475a;
                    selection-color: #89b4fa;
                }
                QHeaderView::section {
                    background-color: #1e1e2e;
                    color: #cdd6f4;
                    font-weight: 700;
                    padding: 4px 6px;
                    border: 1px solid #313244;
                }
            """)
        else:
            self.setStyleSheet("""
                QDialog {
                    background-color: #f8fafc;
                }
                QLabel {
                    color: #0f172a;
                    font-weight: 600;
                }
                QGroupBox {
                    border: 1.5px solid #cbd5e1;
                    border-radius: 6px;
                    margin-top: 14px;
                    padding: 12px 8px 8px 8px;
                    background-color: #ffffff;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 1px 8px;
                    color: #0369a1;
                    font-weight: 700;
                    background-color: #ffffff;
                    border: 1px solid #cbd5e1;
                    border-radius: 3px;
                }
                QGroupBox QLabel, QGroupBox QCheckBox {
                    color: #0f172a;
                    font-weight: 600;
                }
                QLineEdit, QComboBox {
                    background-color: #ffffff;
                    color: #0f172a;
                    border: 1.5px solid #94a3b8;
                    border-radius: 4px;
                    padding: 5px 8px;
                    font-weight: 500;
                }
                QTabWidget::pane {
                    border: 1.5px solid #cbd5e1;
                    background-color: #ffffff;
                    border-radius: 4px;
                }
                QTabBar::tab {
                    background-color: #e2e8f0;
                    color: #0f172a;
                    font-weight: 700;
                    font-size: 11px;
                    padding: 6px 14px;
                    margin-right: 2px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                    border: 1px solid #cbd5e1;
                }
                QTabBar::tab:selected {
                    background-color: #ffffff;
                    color: #0369a1;
                    border-bottom: 2px solid #0284c7;
                }
                QTableView {
                    background-color: #ffffff;
                    alternate-background-color: #f8fafc;
                    gridline-color: #cbd5e1;
                    color: #0f172a;
                    border: 1.5px solid #cbd5e1;
                    border-radius: 4px;
                    selection-background-color: #0284c7;
                    selection-color: #ffffff;
                }
                QHeaderView::section {
                    background-color: #f1f5f9;
                    color: #0f172a;
                    font-weight: 700;
                    padding: 4px 6px;
                    border: 1px solid #cbd5e1;
                }
            """)
        if hasattr(self, "preview_model") and self.preview_model is not None:
            self.preview_model.layoutChanged.emit()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = urls[0].toLocalFile()
                if path and os.path.exists(path):
                    self.tabs_source.setCurrentIndex(0)
                    self.txt_filepath.setText(path)
                    self._load_file_preview(path)
                    self._run_extraction()
                    event.acceptProposedAction()
                    return
        super().dropEvent(event)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)

        app = QApplication.instance()
        is_dark = getattr(app, "is_dark_theme", False) or "background-color: #181825" in (app.styleSheet() if app else "")

        # Header Banner
        lbl_banner = QLabel("<b>AI Smart File Ingestion & Auto-Plot</b>")
        lbl_banner.setStyleSheet(f"font-weight: 700; color: {'#38bdf8' if is_dark else '#0369a1'};")
        main_layout.addWidget(lbl_banner)

        lbl_desc = QLabel(
            "Select ANY raw file (TXT, CSV, DAT, LOG, XRD .X01, Excel, JSON) or paste messy text. "
            "AI automatically removes metadata preambles, extracts tables, assigns X/Y roles, and generates your graph!"
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"color: {'#cdd6f4' if is_dark else '#0f172a'}; font-weight: 500;")
        main_layout.addWidget(lbl_desc)

        # Source Selection Tabs
        self.tabs_source = QTabWidget(self)
        self.tabs_source.setFixedHeight(120)

        # Tab 1: File Selection
        w_file = QWidget()
        l_file = QVBoxLayout(w_file)
        f_row = QHBoxLayout()
        self.txt_filepath = QLineEdit()
        self.txt_filepath.setPlaceholderText("Select any file or drag & drop here (e.g. scan.x01, raw_instrument_output.dat)...")
        f_row.addWidget(self.txt_filepath)

        btn_browse = QPushButton("📁 Browse File...")
        btn_style_browse = (
            "font-weight: 600; color: #cdd6f4; background-color: #313244; border: 1.5px solid #45475a; padding: 5px 12px; border-radius: 4px;"
            if is_dark else
            "font-weight: 600; color: #0f172a; background-color: #f1f5f9; border: 1.5px solid #94a3b8; padding: 5px 12px; border-radius: 4px;"
        )
        btn_browse.setStyleSheet(btn_style_browse)
        btn_browse.clicked.connect(self._browse_file)
        f_row.addWidget(btn_browse)
        l_file.addLayout(f_row)

        # Quick sample buttons
        samples_row = QHBoxLayout()
        samples_row.setSpacing(6)
        lbl_sample_prompt = QLabel("Or load sample raw data:")
        lbl_sample_prompt.setStyleSheet(f"font-weight: 600; color: {'#cdd6f4' if is_dark else '#0f172a'};")
        samples_row.addWidget(lbl_sample_prompt)

        sample_btn_style = (
            "font-weight: 600; color: #cdd6f4; background-color: #313244; border: 1.5px solid #45475a; padding: 4px 8px; border-radius: 4px;"
            if is_dark else
            "font-weight: 600; color: #0f172a; background-color: #f1f5f9; border: 1.5px solid #94a3b8; padding: 4px 8px; border-radius: 4px;"
        )

        btn_sample_xrd = QPushButton("XRD Rocking (.x01)")
        btn_sample_xrd.setStyleSheet(sample_btn_style)
        btn_sample_xrd.clicked.connect(self._load_sample_xrd)
        samples_row.addWidget(btn_sample_xrd)

        btn_sample_hplc = QPushButton("HPLC Log (.log)")
        btn_sample_hplc.setStyleSheet(sample_btn_style)
        btn_sample_hplc.clicked.connect(self._load_sample_hplc)
        samples_row.addWidget(btn_sample_hplc)

        btn_sample_spec = QPushButton("Spectrometer (.txt)")
        btn_sample_spec.setStyleSheet(sample_btn_style)
        btn_sample_spec.clicked.connect(self._load_sample_spec)
        samples_row.addWidget(btn_sample_spec)
        samples_row.addStretch()
        l_file.addLayout(samples_row)
        self.tabs_source.addTab(w_file, "📁 From File")

        # Tab 2: Paste Raw Text
        w_text = QWidget()
        l_text = QVBoxLayout(w_text)
        l_text.setContentsMargins(4, 4, 4, 4)
        self.txt_paste = QTextEdit()
        self.txt_paste.setPlaceholderText("Paste unstructured numbers, instrument logs, or clipboard data here...")
        self.txt_paste.setStyleSheet(
            "color: #cdd6f4; background-color: #181825; border: 1.5px solid #45475a; font-family: 'Consolas', 'Courier New', monospace; font-size: 11px;"
            if is_dark else
            "color: #0f172a; background-color: #ffffff; border: 1.5px solid #94a3b8; font-family: 'Consolas', 'Courier New', monospace; font-size: 11px;"
        )
        l_text.addWidget(self.txt_paste)
        self.tabs_source.addTab(w_text, "📋 Paste Raw Text")

        main_layout.addWidget(self.tabs_source)

        # Extraction Settings Bar (Header Mode & Delimiter Options)
        grp_settings = QGroupBox("Extraction Settings")
        l_settings = QGridLayout(grp_settings)
        l_settings.setContentsMargins(8, 6, 8, 6)
        l_settings.setSpacing(6)

        l_settings.addWidget(QLabel("Header Mode:"), 0, 0)
        self.combo_header_mode = QComboBox()
        self.combo_header_mode.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_header_mode.setMinimumContentsLength(10)
        self.combo_header_mode.addItem("Auto-Detect (Smart Detection)", "auto")
        self.combo_header_mode.addItem("First Row is Column Names", "first_row")
        self.combo_header_mode.addItem("First 2 Rows are Names & Units", "two_rows")
        self.combo_header_mode.addItem("No Header (Pure Numeric Data)", "none")
        self.combo_header_mode.currentIndexChanged.connect(self._on_header_or_delim_changed)
        l_settings.addWidget(self.combo_header_mode, 0, 1)

        l_settings.addWidget(QLabel("Delimiter:"), 0, 2)
        self.combo_delim = QComboBox()
        self.combo_delim.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_delim.setMinimumContentsLength(8)
        self.combo_delim.addItem("Auto-Detect Delimiter", "auto")
        self.combo_delim.addItem("Comma (,)", ",")
        self.combo_delim.addItem("Tab (\\t)", "\t")
        self.combo_delim.addItem("Semicolon (;)", ";")
        self.combo_delim.addItem("Whitespace", "whitespace")
        self.combo_delim.currentIndexChanged.connect(self._on_header_or_delim_changed)
        l_settings.addWidget(self.combo_delim, 0, 3)

        # Action button to trigger extraction (spans row 1)
        btn_extract = QPushButton("⚡ Auto-Extract Data with AI")
        btn_extract.setStyleSheet("font-weight: 700; background-color: #0284c7; color: #ffffff; padding: 6px 14px; border-radius: 4px;")
        btn_extract.clicked.connect(self._run_extraction)
        l_settings.addWidget(btn_extract, 1, 0, 1, 4)

        main_layout.addWidget(grp_settings)

        # Splitter: Raw Preview vs Extracted Table Preview
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Raw Source Preview
        grp_raw = QGroupBox("Raw Source Preview")
        l_raw = QVBoxLayout(grp_raw)
        self.txt_raw_preview = QTextEdit()
        self.txt_raw_preview.setReadOnly(True)
        self.txt_raw_preview.setStyleSheet(
            "color: #cdd6f4; background-color: #181825; border: 1.5px solid #313244; font-family: 'Consolas', 'Courier New', monospace; font-size: 11px;"
            if is_dark else
            "color: #0f172a; background-color: #ffffff; border: 1.5px solid #cbd5e1; font-family: 'Consolas', 'Courier New', monospace; font-size: 11px;"
        )
        l_raw.addWidget(self.txt_raw_preview)
        splitter.addWidget(grp_raw)

        # Right: Extracted Table Preview
        grp_extracted = QGroupBox("AI Extracted Table Preview")
        l_ext = QVBoxLayout(grp_extracted)
        self.table_preview = QTableView()
        self.preview_model = ExtractedPreviewModel()
        self.table_preview.setModel(self.preview_model)
        self.table_preview.horizontalHeader().setDefaultSectionSize(110)
        l_ext.addWidget(self.table_preview)

        self.lbl_extract_summary = QLabel("No data extracted yet.")
        self.lbl_extract_summary.setStyleSheet(
            f"font-weight: 700; color: {'#4ade80' if is_dark else '#15803d'}; padding: 4px;"
        )
        l_ext.addWidget(self.lbl_extract_summary)
        splitter.addWidget(grp_extracted)

        splitter.setSizes([320, 480])
        main_layout.addWidget(splitter)

        # Plot Options & Creation Controls
        grp_plot_opts = QGroupBox("Auto-Plot Options")
        l_opts = QGridLayout(grp_plot_opts)
        l_opts.setSpacing(6)

        l_opts.addWidget(QLabel("Plot Type:"), 0, 0)
        self.combo_plot_type = QComboBox()
        self.combo_plot_type.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_plot_type.addItems(["line_symbol", "scatter", "line", "spline", "bar", "area", "errorbar", "step"])
        l_opts.addWidget(self.combo_plot_type, 0, 1)

        self.chk_create_graph = QCheckBox("Generate Graph Window")
        self.chk_create_graph.setChecked(True)
        l_opts.addWidget(self.chk_create_graph, 0, 2)

        self.combo_target_graph = QComboBox()
        self.combo_target_graph.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_target_graph.setMinimumContentsLength(10)
        self.combo_target_graph.addItem("Create New Graph")
        if self.active_graph:
            self.combo_target_graph.addItem(f"Layer onto Active Graph ({self.active_graph.title})")
        l_opts.addWidget(self.combo_target_graph, 0, 3)

        main_layout.addWidget(grp_plot_opts)

        # Dialog Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet(
            "font-weight: 600; color: #cdd6f4; background-color: #313244; border: 1.5px solid #45475a; padding: 6px 14px; border-radius: 4px;"
            if is_dark else
            "font-weight: 600; color: #0f172a; background-color: #f1f5f9; border: 1.5px solid #94a3b8; padding: 6px 14px; border-radius: 4px;"
        )
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        self.btn_import_plot = QPushButton("📈 Import && Plot Now!")
        self.btn_import_plot.setEnabled(False)
        self.btn_import_plot.setStyleSheet("font-weight: 700; background-color: #15803d; color: #ffffff; padding: 7px 18px; border-radius: 4px;")
        self.btn_import_plot.clicked.connect(self._on_import_and_plot)
        btn_layout.addWidget(self.btn_import_plot)

        main_layout.addLayout(btn_layout)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Any Data File",
            "",
            "XRD Rocking Curves & Scans (*.x01 *.X01 *.x02 *.X02 *.x03 *.X03 *.dat *.txt);;"
            "All Supported Files (*.txt *.csv *.dat *.log *.tsv *.prn *.xlsx *.xls *.json *.x01 *.X01 *.x02 *.X02 *.x03 *.X03);;"
            "All Files (*.*)"
        )
        if path:
            self.txt_filepath.setText(path)
            self._load_file_preview(path)
            self._run_extraction()

    def _load_file_preview(self, path: str):
        try:
            with open(path, "rb") as bf:
                head_bytes = bf.read(4096)
            if b"\x00" in head_bytes[:1024]:
                ascii_strs = re.findall(b"[ -~]{4,}", head_bytes[:512])
                decoded_meta = [s.decode("latin-1", errors="ignore") for s in ascii_strs]
                preview_txt = f"Binary scientific scan: {os.path.basename(path)} ({os.path.getsize(path)} bytes)\n"
                if decoded_meta:
                    preview_txt += "Detected Metadata in Header:\n  " + "\n  ".join(decoded_meta) + "\n\n"
                preview_txt += f"Hex preview (first 64 bytes):\n{head_bytes[:64].hex(' ')}"
                self.txt_raw_preview.setPlainText(preview_txt)
            else:
                try:
                    text = head_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    text = head_bytes.decode("latin-1", errors="replace")
                self.txt_raw_preview.setPlainText(text)
        except Exception:
            self.txt_raw_preview.setPlainText(f"Binary or encoded file: {os.path.basename(path)}")

    def _load_sample_xrd(self):
        sample_xrd = (
            "[Header]\n"
            "Sample = InGaAs/GaAs Epilayer\n"
            "Instrument = Bede D1 HRXRD Diffractometer\n"
            "Radiation = Cu-Ka1 (1.540597 A)\n"
            "Scan Mode = Rocking Curve (Omega Scan)\n"
            "Range = -1500 to +1500 arcsec\n"
            "Step Size = 25.0 arcsec\n"
            "Count Time = 1.0 s\n"
            "[Data]\n"
            "Omega (arcsec)\tIntensity (Counts)\n"
            "-1500.0\t18\n"
            "-1400.0\t22\n"
            "-1300.0\t35\n"
            "-1200.0\t84\n"
            "-1100.0\t310\n"
            "-1000.0\t1420\n"
            "-950.0\t4250\n"
            "-900.0\t12800\n"
            "-850.0\t28900\n"
            "-800.0\t51200\n"
            "-750.0\t31400\n"
            "-700.0\t13600\n"
            "-600.0\t3100\n"
            "-500.0\t890\n"
            "-400.0\t320\n"
            "-300.0\t195\n"
            "-200.0\t410\n"
            "-100.0\t2850\n"
            "-50.0\t18200\n"
            "0.0\t185400\n"
            "50.0\t24100\n"
            "100.0\t3600\n"
            "200.0\t520\n"
            "300.0\t210\n"
            "400.0\t145\n"
            "500.0\t110\n"
            "600.0\t85\n"
            "800.0\t54\n"
            "1000.0\t38\n"
            "1200.0\t25\n"
            "1500.0\t19\n"
        )
        self.tabs_source.setCurrentIndex(1)
        self.txt_paste.setPlainText(sample_xrd)
        self.txt_raw_preview.setPlainText(sample_xrd)
        self._run_extraction()

    def _load_sample_hplc(self):
        sample_log = (
            "# Instrument: Agilent 1260 Infinity HPLC\n"
            "# Date: 2026-10-19 10:14:22\n"
            "# Flow Rate: 1.0 mL/min\n"
            "# Solvent A: 0.1% TFA in H2O, Solvent B: Acetonitrile\n"
            "# Sample ID: Peptide-Analogue-07\n"
            "Retention_Time (min)\tAbsorbance_214nm (mAU)\tAbsorbance_280nm (mAU)\tBackpressure (bar)\n"
            "0.0\t1.2\t0.3\t142.1\n"
            "0.5\t1.4\t0.4\t142.5\n"
            "1.0\t1.5\t0.3\t143.0\n"
            "1.5\t2.1\t0.5\t143.2\n"
            "2.0\t8.6\t1.8\t144.0\n"
            "2.5\t45.8\t12.4\t145.2\n"
            "3.0\t120.4\t31.2\t146.5\n"
            "3.2\t185.9\t48.7\t147.0\n"
            "3.5\t75.3\t19.8\t146.8\n"
            "4.0\t15.2\t3.9\t145.5\n"
            "4.5\t3.8\t0.9\t144.8\n"
            "5.0\t2.0\t0.4\t144.2\n"
            "6.0\t1.8\t0.3\t143.8\n"
        )
        self.tabs_source.setCurrentIndex(1)
        self.txt_paste.setPlainText(sample_log)
        self.txt_raw_preview.setPlainText(sample_log)
        self._run_extraction()

    def _load_sample_spec(self):
        sample_spec = (
            "---------------------------------------------------\n"
            "Varian Cary 5000 UV-Vis-NIR Spectrophotometer\n"
            "Scan Speed: 600 nm/min, SBW: 2.0 nm\n"
            "Operator: Kyle, Lab: Bio-Spectroscopy\n"
            "---------------------------------------------------\n"
            "Wavelength (nm) , Absorbance (OD) , Std_Error\n"
            "300.0 , 0.052 , 0.003\n"
            "320.0 , 0.089 , 0.004\n"
            "340.0 , 0.174 , 0.005\n"
            "360.0 , 0.352 , 0.008\n"
            "380.0 , 0.680 , 0.012\n"
            "400.0 , 1.150 , 0.018\n"
            "420.0 , 1.480 , 0.022\n"
            "440.0 , 1.210 , 0.019\n"
            "460.0 , 0.720 , 0.011\n"
            "480.0 , 0.380 , 0.007\n"
            "500.0 , 0.190 , 0.004\n"
            "550.0 , 0.075 , 0.002\n"
            "600.0 , 0.041 , 0.001\n"
        )
        self.tabs_source.setCurrentIndex(1)
        self.txt_paste.setPlainText(sample_spec)
        self.txt_raw_preview.setPlainText(sample_spec)
        self._run_extraction()

    def _on_header_or_delim_changed(self):
        curr_tab = self.tabs_source.currentIndex()
        if curr_tab == 0:
            path = self.txt_filepath.text().strip()
            if path and os.path.exists(path):
                self._run_extraction()
        else:
            if self.txt_paste.toPlainText().strip():
                self._run_extraction()

    def _run_extraction(self):
        """Runs the SmartDataExtractor engine with selected header mode and delimiter."""
        try:
            curr_tab = self.tabs_source.currentIndex()
            header_mode = self.combo_header_mode.currentData()
            delim_val = self.combo_delim.currentData()
            delim_override = None if delim_val == "auto" else (r"\s+" if delim_val == "whitespace" else delim_val)

            if curr_tab == 0:
                filepath = self.txt_filepath.text().strip()
                if not filepath or not os.path.exists(filepath):
                    QMessageBox.warning(self, "No File", "Please select a valid file to extract.")
                    return
                self.extraction_result = SmartDataExtractor.extract_from_file(
                    filepath,
                    header_mode=header_mode,
                    delimiter_override=delim_override,
                )
            else:
                raw_text = self.txt_paste.toPlainText().strip()
                if not raw_text:
                    QMessageBox.warning(self, "Empty Text", "Please paste data text into the box.")
                    return
                self.txt_raw_preview.setPlainText(raw_text[:2000])
                self.extraction_result = SmartDataExtractor.extract_from_text(
                    raw_text,
                    header_mode=header_mode,
                    delimiter_override=delim_override,
                )

            res = self.extraction_result
            if res.dataframe.empty:
                QMessageBox.warning(self, "Extraction Notice", "No numeric data could be extracted.")
                return

            # Update preview
            self.preview_model.set_result(res)
            self.combo_plot_type.setCurrentText(res.recommended_plot)

            hdr_mode = res.metadata.get("HeaderMode", "Detected")
            hdr_desc = {
                "none": "Pure Data (Row 1 is Data)",
                "first_row": "Row 1 as Names",
                "two_rows": "Rows 1 & 2 as Names + Units",
            }.get(hdr_mode, hdr_mode)

            summary = (
                f"✅ Extracted {len(res.dataframe)} rows × {len(res.dataframe.columns)} columns "
                f"({hdr_desc}) | Recommended: {res.recommended_plot.upper()}"
            )
            self.lbl_extract_summary.setText(summary)
            self.btn_import_plot.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(self, "Extraction Error", f"Failed to extract data:\n{e}")

    def _on_import_and_plot(self):
        """Applies extracted table to project workbooks and auto-generates graph."""
        if self.extraction_result is None or self.extraction_result.dataframe.empty:
            return

        res = self.extraction_result
        if not self.project.workbooks:
            self.project.workbooks.append(Workbook("Book1"))
        wb = self.project.workbooks[0]

        # Determine worksheet name
        base_name = "AI_Extracted"
        counter = 1
        sheet_name = base_name
        existing_names = [s.name for s in wb.sheets]
        while sheet_name in existing_names:
            counter += 1
            sheet_name = f"{base_name}_{counter}"

        ws = res.to_worksheet(sheet_name=sheet_name)
        wb.sheets.append(ws)
        self.created_worksheet = ws

        # Create or Layer onto Graph
        if self.chk_create_graph.isChecked():
            plot_type = self.combo_plot_type.currentText()
            target_mode = self.combo_target_graph.currentText()

            # Find X column
            x_col_idx = 0
            for idx, col in enumerate(ws.columns):
                if col.role == ColumnRole.X:
                    x_col_idx = idx
                    break

            # Find Y columns
            y_col_indices = [idx for idx, col in enumerate(ws.columns) if col.role == ColumnRole.Y]
            if not y_col_indices and len(ws.columns) > 1:
                y_col_indices = [1]

            # Find Error columns if present
            err_col_indices = [idx for idx, col in enumerate(ws.columns) if col.role == ColumnRole.Y_ERR]

            palette = [
                "#0284c7", "#e11d48", "#16a34a", "#d97706", "#7c3aed",
                "#0891b2", "#dc2626", "#475569", "#ea580c", "#2563eb"
            ]
            markers = ["o", "s", "^", "D", "v", "<", ">", "p", "*", "h"]

            if "Layer onto Active" in target_mode and self.active_graph:
                graph = self.active_graph
            else:
                graph_title = f"AI_Plot_{len(self.project.graphs) + 1}"
                graph = GraphModel(title=graph_title, plot_type=plot_type)
                xcol = ws.get_column(x_col_idx)
                if xcol:
                    graph.x_title = xcol.display_label
                if y_col_indices and ws.get_column(y_col_indices[0]):
                    ycol = ws.get_column(y_col_indices[0])
                    graph.y_title = ycol.display_label
                graph.title_text = f"AI Extracted: {sheet_name}"
                self.project.graphs.append(graph)

            # Add curve for each Y column
            for i, y_idx in enumerate(y_col_indices):
                y_col = ws.get_column(y_idx)
                err_idx = err_col_indices[i] if i < len(err_col_indices) else None

                curve_idx = len(graph.curves)
                color = palette[curve_idx % len(palette)]
                marker = markers[curve_idx % len(markers)]

                c = CurveModel(
                    source_workbook=wb.name,
                    source_sheet=ws.name,
                    x_col_idx=x_col_idx if x_col_idx is not None else 0,
                    y_col_idx=y_idx,
                    y_err_col_idx=err_idx,
                    label=y_col.display_label if y_col else f"Y{i+1}",
                    color=color,
                    line_style="-",
                    line_width=1.8,
                    marker=marker if "symbol" in plot_type or plot_type == "scatter" else "none",
                    marker_size=6.0,
                    plot_type="errorbar" if (err_idx is not None or plot_type == "errorbar") else plot_type,
                )
                graph.add_curve(c)

            self.created_graph = graph

        self.accept()
