"""
Universal Data Import Dialog for single or multiple files or raw text paste.
Supports CSV, TSV, TXT, DAT, Excel (.xlsx, .xls), XRD scans (.x01, .x02), LOG, and JSON.
Allows multi-file batch ingestion into separate sheets, separate workbooks, or merged tables,
with auto-delimiter, smart header/unit detection, raw text pasting, and auto-comparison graphing.
"""

import os
import re
from typing import Optional, List, Dict, Any
import pandas as pd
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout, QComboBox,
    QCheckBox, QLineEdit, QTextEdit, QTabWidget, QPushButton, QTableWidget,
    QTableWidgetItem, QFileDialog, QDialogButtonBox, QMessageBox, QLabel,
    QListWidget, QListWidgetItem, QGroupBox, QSplitter, QWidget, QHeaderView,
    QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

from omnigraph.core.worksheet import Worksheet, Column, ColumnRole
from omnigraph.ai.data_extractor import SmartDataExtractor


class ImportDialog(QDialog):
    """
    Dialog for importing structured data into worksheets from files or raw text.
    Supports single or batch file selection, raw text/clipboard pasting, format sniffers,
    destination routing, and instant live table previews.
    """

    def __init__(
        self,
        initial_filepath: Optional[str] = None,
        initial_filepaths: Optional[List[str]] = None,
        initial_text: Optional[str] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.filepaths: List[str] = []
        if initial_filepaths:
            self.filepaths = [p for p in initial_filepaths if p and os.path.exists(p)]
        elif initial_filepath and os.path.exists(initial_filepath):
            self.filepaths = [initial_filepath]

        self.filepath = self.filepaths[0] if self.filepaths else ""
        self.imported_dataframe: Optional[pd.DataFrame] = None
        self.imported_results: List[Dict[str, Any]] = []
        self.destination_mode: str = "sheets"
        self.auto_plot: bool = False
        self.plot_type: str = "line_symbol"

        self.setWindowTitle("📥 Smart Data Import & Auto-Plot (Files or Raw Text)")
        self.resize(840, 600)
        self.setMinimumSize(680, 500)
        self.setAcceptDrops(True)
        self._init_ui()

        if initial_text:
            self.txt_paste.setPlainText(initial_text)
            self.tabs_source.setCurrentIndex(1)
            self._load_text_preview()
        elif self.filepaths:
            self._refresh_file_list()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            new_paths = [u.toLocalFile() for u in urls if u.toLocalFile() and os.path.exists(u.toLocalFile())]
            if new_paths:
                self.tabs_source.setCurrentIndex(0)
                for p in new_paths:
                    if p not in self.filepaths:
                        self.filepaths.append(p)
                self._refresh_file_list()
                event.acceptProposedAction()
                return
        super().dropEvent(event)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)

        # Tabbed Input Source: Files or Raw Pasted Text
        self.tabs_source = QTabWidget()
        self.tabs_source.setObjectName("ImportTabsSource")

        # Tab 0: File Selection & Batch Controls
        tab_files = QWidget()
        l_files = QVBoxLayout(tab_files)
        l_files.setContentsMargins(6, 6, 6, 6)
        l_files.setSpacing(6)

        # Top path/buttons bar
        top_bar = QHBoxLayout()
        self.txt_path_display = QLineEdit()
        self.txt_path_display.setPlaceholderText("Select single or multiple files (CSV, TXT, DAT, Excel, XRD .x01)...")
        self.txt_path_display.setReadOnly(True)
        top_bar.addWidget(self.txt_path_display)

        btn_browse = QPushButton("📁 Browse Files...")
        btn_browse.setStyleSheet("font-weight: 600; padding: 5px 12px;")
        btn_browse.clicked.connect(self._browse_files)
        top_bar.addWidget(btn_browse)

        btn_add = QPushButton("➕ Add More...")
        btn_add.setToolTip("Add more files to the current batch list")
        btn_add.clicked.connect(self._add_files)
        top_bar.addWidget(btn_add)

        btn_remove = QPushButton("🗑️ Remove")
        btn_remove.setToolTip("Remove selected file from the list")
        btn_remove.clicked.connect(self._remove_selected_file)
        top_bar.addWidget(btn_remove)

        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self._clear_files)
        top_bar.addWidget(btn_clear)

        l_files.addLayout(top_bar)

        # List widget showing selected files
        self.list_files = QListWidget()
        self.list_files.setFixedHeight(75)
        self.list_files.currentRowChanged.connect(self._on_file_selection_changed)
        l_files.addWidget(self.list_files)

        self.tabs_source.addTab(tab_files, "📁 From File(s)")

        # Tab 1: Raw Text / Clipboard
        tab_paste = QWidget()
        l_paste = QVBoxLayout(tab_paste)
        l_paste.setContentsMargins(6, 6, 6, 6)
        l_paste.setSpacing(6)

        paste_btn_bar = QHBoxLayout()
        btn_paste_clip = QPushButton("📋 Paste Clipboard")
        btn_paste_clip.setStyleSheet("font-weight: 600; padding: 4px 10px;")
        btn_paste_clip.clicked.connect(self._paste_clipboard)
        paste_btn_bar.addWidget(btn_paste_clip)

        lbl_samples = QLabel("Sample Data:")
        lbl_samples.setStyleSheet("font-weight: 600; padding-left: 6px;")
        paste_btn_bar.addWidget(lbl_samples)

        btn_sample_xrd = QPushButton("XRD Rocking (.x01)")
        btn_sample_xrd.clicked.connect(self._load_sample_xrd)
        paste_btn_bar.addWidget(btn_sample_xrd)

        btn_sample_hplc = QPushButton("HPLC Log (.log)")
        btn_sample_hplc.clicked.connect(self._load_sample_hplc)
        paste_btn_bar.addWidget(btn_sample_hplc)

        btn_sample_spec = QPushButton("Spectrometer (.txt)")
        btn_sample_spec.clicked.connect(self._load_sample_spec)
        paste_btn_bar.addWidget(btn_sample_spec)

        paste_btn_bar.addStretch()
        l_paste.addLayout(paste_btn_bar)

        self.txt_paste = QTextEdit()
        self.txt_paste.setPlaceholderText("Paste messy table text, copied spreadsheet rows, or instrument logs here...")
        self.txt_paste.setFixedHeight(85)
        self.txt_paste.textChanged.connect(self._load_text_preview)
        l_paste.addWidget(self.txt_paste)

        self.tabs_source.addTab(tab_paste, "📋 Paste Raw Text / Clipboard")
        self.tabs_source.currentChanged.connect(self._on_source_tab_changed)

        main_layout.addWidget(self.tabs_source)

        # Ingestion & Parsing Settings
        grp_settings = QGroupBox("Parsing & Ingestion Settings")
        gl = QHBoxLayout(grp_settings)
        gl.setSpacing(10)

        # Delimiter
        gl.addWidget(QLabel("Delimiter:"))
        self.combo_delim = QComboBox()
        self.combo_delim.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_delim.setMinimumContentsLength(8)
        self.combo_delim.addItem("Auto-Detect Delimiter", "auto")
        self.combo_delim.addItem("Comma (,)", ",")
        self.combo_delim.addItem("Tab (\\t)", "\t")
        self.combo_delim.addItem("Semicolon (;)", ";")
        self.combo_delim.addItem("Whitespace", "whitespace")
        self.combo_delim.currentIndexChanged.connect(self._refresh_current_preview)
        gl.addWidget(self.combo_delim)

        gl.addSpacing(10)

        # Header Mode
        gl.addWidget(QLabel("Header Mode:"))
        self.combo_header = QComboBox()
        self.combo_header.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_header.setMinimumContentsLength(10)
        self.combo_header.addItem("Auto-Detect Headers", "auto")
        self.combo_header.addItem("First Row is Column Names", "first_row")
        self.combo_header.addItem("First 2 Rows are Names & Units", "two_rows")
        self.combo_header.addItem("No Header (Pure Data)", "none")
        self.combo_header.currentIndexChanged.connect(self._refresh_current_preview)
        gl.addWidget(self.combo_header)

        gl.addStretch()
        main_layout.addWidget(grp_settings)

        # Multi-File Destination & Auto-Plot Group (responsive 2-row layout)
        grp_batch = QGroupBox("Destination & Auto-Graphing")
        bl = QGridLayout(grp_batch)
        bl.setSpacing(8)

        bl.addWidget(QLabel("Destination:"), 0, 0)
        self.combo_dest = QComboBox()
        self.combo_dest.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_dest.setMinimumContentsLength(10)
        self.combo_dest.addItem("Separate Sheet for each file in active workbook", "sheets")
        self.combo_dest.addItem("Separate Workbook for each file", "workbooks")
        self.combo_dest.addItem("Merge into single Sheet (Side-by-side columns)", "merge")
        bl.addWidget(self.combo_dest, 0, 1, 1, 3)

        self.chk_auto_plot = QCheckBox("📈 Auto-generate Comparison Graph")
        self.chk_auto_plot.setChecked(True)
        bl.addWidget(self.chk_auto_plot, 1, 0, 1, 2)

        lbl_plot = QLabel("Plot Type:")
        lbl_plot.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        bl.addWidget(lbl_plot, 1, 2)
        self.combo_plot_type = QComboBox()
        self.combo_plot_type.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_plot_type.addItems(["line_symbol", "scatter", "line", "spline", "bar", "area", "errorbar"])
        self.combo_plot_type.setCurrentText("line_symbol")
        bl.addWidget(self.combo_plot_type, 1, 3)

        main_layout.addWidget(grp_batch)

        # Data Preview Table
        preview_header_row = QHBoxLayout()
        self.lbl_preview_title = QLabel("<b>Data Preview (First 15 Rows):</b>")
        preview_header_row.addWidget(self.lbl_preview_title)
        preview_header_row.addStretch()
        self.lbl_file_count_badge = QLabel("0 files selected")
        app = QApplication.instance()
        is_dark = getattr(app, "is_dark_theme", False) or "background-color: #181825" in (app.styleSheet() if app else "")
        badge_color = "#38bdf8" if is_dark else "#0369a1"
        self.lbl_file_count_badge.setStyleSheet(f"color: {badge_color}; font-weight: bold;")
        preview_header_row.addWidget(self.lbl_file_count_badge)
        main_layout.addLayout(preview_header_row)

        self.table_prev = QTableWidget()
        self.table_prev.setAlternatingRowColors(True)
        self.table_prev.horizontalHeader().setStretchLastSection(True)
        main_layout.addWidget(self.table_prev)

        # Dialog Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)

        self.btn_ok = QPushButton("Import Data")
        self.btn_ok.setDefault(True)
        self.btn_ok.setStyleSheet("font-weight: 700; background-color: #15803d; color: #ffffff; padding: 6px 18px; border-radius: 4px;")
        self.btn_ok.clicked.connect(self._on_accept)
        buttons_layout.addWidget(self.btn_ok)

        main_layout.addLayout(buttons_layout)

    def _browse_files(self):
        """Allows selecting one or multiple files in file dialog."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Data File(s)",
            "",
            "All Supported Files (*.csv *.txt *.tsv *.dat *.xlsx *.xls *.x01 *.X01 *.x02 *.X02 *.x03 *.log *.json);;"
            "CSV Files (*.csv);;"
            "XRD Rocking Curves & Scans (*.x01 *.X01 *.x02 *.X02 *.dat *.txt);;"
            "Excel Workbooks (*.xlsx *.xls);;"
            "All Files (*.*)"
        )
        if files:
            self.filepaths = files
            self._refresh_file_list()

    def _add_files(self):
        """Appends additional files to current batch list."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Add Data File(s) to Batch",
            "",
            "All Supported Files (*.csv *.txt *.tsv *.dat *.xlsx *.xls *.x01 *.X01 *.x02 *.X02 *.log *.json);;"
            "All Files (*.*)"
        )
        if files:
            for f in files:
                if f not in self.filepaths:
                    self.filepaths.append(f)
            self._refresh_file_list()

    def _remove_selected_file(self):
        curr_row = self.list_files.currentRow()
        if 0 <= curr_row < len(self.filepaths):
            del self.filepaths[curr_row]
            self._refresh_file_list()

    def _clear_files(self):
        self.filepaths.clear()
        self._refresh_file_list()

    def _refresh_file_list(self):
        self.list_files.clear()
        for p in self.filepaths:
            size_kb = os.path.getsize(p) / 1024.0 if os.path.exists(p) else 0.0
            ext = os.path.splitext(p)[1].upper()
            item = QListWidgetItem(f"📄 {os.path.basename(p)}  ({size_kb:.1f} KB) - {ext}")
            item.setToolTip(p)
            self.list_files.addItem(item)

        count = len(self.filepaths)
        self.lbl_file_count_badge.setText(f"{count} file(s) selected")
        if count == 0:
            self.txt_path_display.setText("")
            self.table_prev.setRowCount(0)
            self.table_prev.setColumnCount(0)
            self.btn_ok.setText("Import Data")
            self.btn_ok.setEnabled(False)
        elif count == 1:
            self.txt_path_display.setText(self.filepaths[0])
            self.list_files.setCurrentRow(0)
            self.btn_ok.setText("Import 1 File")
            self.btn_ok.setEnabled(True)
        else:
            names = ", ".join(os.path.basename(p) for p in self.filepaths[:3])
            if count > 3:
                names += f" and {count - 3} more"
            self.txt_path_display.setText(f"{count} files: {names}")
            self.list_files.setCurrentRow(0)
            self.btn_ok.setText(f"Batch Import {count} Files")
            self.btn_ok.setEnabled(True)

    def _on_file_selection_changed(self, row: int):
        if 0 <= row < len(self.filepaths):
            self.filepath = self.filepaths[row]
            self._load_file_preview()

    def _on_source_tab_changed(self, index: int):
        self._refresh_current_preview()

    def _refresh_current_preview(self):
        if self.tabs_source.currentIndex() == 1:
            self._load_text_preview()
        else:
            self._load_file_preview()

    def _paste_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.txt_paste.setPlainText(text)
            self._load_text_preview()

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
        self.txt_paste.setPlainText(sample_xrd)
        self._load_text_preview()

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
        self.txt_paste.setPlainText(sample_log)
        self._load_text_preview()

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
        self.txt_paste.setPlainText(sample_spec)
        self._load_text_preview()

    def _load_text_preview(self):
        """Extracts and previews data from pasted text."""
        raw_text = self.txt_paste.toPlainText().strip()
        if not raw_text:
            self.table_prev.setRowCount(0)
            self.table_prev.setColumnCount(0)
            self.lbl_file_count_badge.setText("Pasted Text (Empty)")
            self.btn_ok.setText("Import Data")
            self.btn_ok.setEnabled(False)
            return

        header_mode = self.combo_header.currentData()
        delim_val = self.combo_delim.currentData()
        delim_override = None if delim_val == "auto" else (r"\s+" if delim_val == "whitespace" else delim_val)

        try:
            res = SmartDataExtractor.extract_from_text(
                raw_text,
                source_name="Pasted_Data",
                header_mode=header_mode,
                delimiter_override=delim_override,
            )
            df = res.dataframe.head(15)
            self.imported_dataframe = res.dataframe

            self.table_prev.setColumnCount(len(df.columns))
            self.table_prev.setHorizontalHeaderLabels([str(c) for c in df.columns])
            self.table_prev.setRowCount(len(df))

            for r_i in range(len(df)):
                for c_i in range(len(df.columns)):
                    val = df.iloc[r_i, c_i]
                    val_str = "" if pd.isna(val) else (f"{val:.5g}" if isinstance(val, float) else str(val))
                    self.table_prev.setItem(r_i, c_i, QTableWidgetItem(val_str))

            self.lbl_file_count_badge.setText("Pasted Text Active")
            self.lbl_preview_title.setText(
                f"<b>Data Preview for: Pasted Raw Text</b> "
                f"<span style='color: #64748b;'>({len(res.dataframe)} rows × {len(res.dataframe.columns)} cols)</span>"
            )
            self.btn_ok.setText("Import Pasted Data")
            self.btn_ok.setEnabled(True)

            if res.recommended_plot:
                idx = self.combo_plot_type.findText(res.recommended_plot)
                if idx >= 0:
                    self.combo_plot_type.setCurrentIndex(idx)

        except Exception as e:
            self.table_prev.setRowCount(0)
            self.table_prev.setColumnCount(0)
            self.lbl_preview_title.setText(f"<b>Preview Error:</b> {e}")
            self.btn_ok.setEnabled(False)

    def _load_file_preview(self):
        """Loads first 15 rows of the currently selected file."""
        if not self.filepath or not os.path.exists(self.filepath):
            return

        header_mode = self.combo_header.currentData()
        delim_val = self.combo_delim.currentData()
        delim_override = None if delim_val == "auto" else (r"\s+" if delim_val == "whitespace" else delim_val)

        try:
            res = SmartDataExtractor.extract_from_file(
                self.filepath,
                header_mode=header_mode,
                delimiter_override=delim_override,
            )
            df = res.dataframe.head(15)
            self.imported_dataframe = res.dataframe

            # Populate preview table
            self.table_prev.setColumnCount(len(df.columns))
            self.table_prev.setHorizontalHeaderLabels([str(c) for c in df.columns])
            self.table_prev.setRowCount(len(df))

            for r_i in range(len(df)):
                for c_i in range(len(df.columns)):
                    val = df.iloc[r_i, c_i]
                    val_str = "" if pd.isna(val) else (f"{val:.5g}" if isinstance(val, float) else str(val))
                    self.table_prev.setItem(r_i, c_i, QTableWidgetItem(val_str))

            self.lbl_preview_title.setText(
                f"<b>Data Preview for: {os.path.basename(self.filepath)}</b> "
                f"<span style='color: #64748b;'>({len(res.dataframe)} rows × {len(res.dataframe.columns)} cols)</span>"
            )

            if res.recommended_plot:
                idx = self.combo_plot_type.findText(res.recommended_plot)
                if idx >= 0:
                    self.combo_plot_type.setCurrentIndex(idx)

        except Exception as e:
            self.table_prev.setRowCount(0)
            self.table_prev.setColumnCount(0)
            self.lbl_preview_title.setText(f"<b>Preview Error:</b> {e}")

    def _on_accept(self):
        """Processes either pasted raw text or selected files for import."""
        header_mode = self.combo_header.currentData()
        delim_val = self.combo_delim.currentData()
        delim_override = None if delim_val == "auto" else (r"\s+" if delim_val == "whitespace" else delim_val)

        self.imported_results.clear()

        # Check if user is importing from Pasted Text tab
        if self.tabs_source.currentIndex() == 1:
            raw_text = self.txt_paste.toPlainText().strip()
            if not raw_text:
                QMessageBox.warning(self, "No Text", "Please paste data text or choose sample data.")
                return
            try:
                res = SmartDataExtractor.extract_from_text(
                    raw_text,
                    source_name="Pasted_Data",
                    header_mode=header_mode,
                    delimiter_override=delim_override,
                )
                if res.dataframe.empty:
                    QMessageBox.warning(self, "No Data", "No numeric columns could be extracted from the text.")
                    return
                ws = res.to_worksheet(sheet_name="Pasted_Data")
                self.imported_results.append({
                    "filepath": "Pasted_Data.txt",
                    "name": "Pasted_Data",
                    "dataframe": res.dataframe,
                    "worksheet": ws,
                    "recommended_plot": res.recommended_plot,
                })
                self.imported_dataframe = res.dataframe
                self.filepath = "Pasted_Data.txt"
            except Exception as e:
                QMessageBox.critical(self, "Extraction Error", f"Failed to extract data from text:\n{e}")
                return

        else:
            # Files tab
            if not self.filepaths:
                QMessageBox.warning(self, "No Files", "Please select at least one data file.")
                return

            errors = []
            for p in self.filepaths:
                if not os.path.exists(p):
                    errors.append(f"File not found: {p}")
                    continue
                try:
                    res = SmartDataExtractor.extract_from_file(
                        p,
                        header_mode=header_mode,
                        delimiter_override=delim_override,
                    )
                    if res.dataframe.empty:
                        errors.append(f"No numeric data extracted from {os.path.basename(p)}")
                        continue

                    base_name = os.path.splitext(os.path.basename(p))[0]
                    ws = res.to_worksheet(sheet_name=base_name)
                    self.imported_results.append({
                        "filepath": p,
                        "name": base_name,
                        "dataframe": res.dataframe,
                        "worksheet": ws,
                        "recommended_plot": res.recommended_plot,
                    })
                except Exception as e:
                    errors.append(f"{os.path.basename(p)}: {e}")

            if not self.imported_results:
                err_msg = "\n".join(errors[:5])
                QMessageBox.critical(self, "Import Failed", f"Could not import selected files:\n{err_msg}")
                return

            if errors:
                QMessageBox.warning(
                    self,
                    "Partial Import Notice",
                    f"Imported {len(self.imported_results)} files with {len(errors)} error(s):\n" + "\n".join(errors[:3])
                )

            self.imported_dataframe = self.imported_results[0]["dataframe"]
            self.filepath = self.imported_results[0]["filepath"]

        self.destination_mode = self.combo_dest.currentData()
        self.auto_plot = self.chk_auto_plot.isChecked()
        self.plot_type = self.combo_plot_type.currentText()

        self.accept()
