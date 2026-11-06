"""
Universal Data Import Dialog for single or multiple files or raw text paste.
Supports CSV, TSV, TXT, DAT, Excel (.xlsx, .xls), XRD scans (.x01, .x02), LOG, and JSON.
Allows multi-file batch ingestion into separate sheets, separate workbooks, or merged tables,
with auto-delimiter, smart header/unit detection, raw text pasting, and auto-comparison graphing.
"""

import os
from typing import Optional, List, Dict, Any
import pandas as pd
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QComboBox,
    QCheckBox, QLineEdit, QTextEdit, QTabWidget, QPushButton, QTableWidget,
    QTableWidgetItem, QFileDialog, QMessageBox, QLabel,
    QListWidget, QListWidgetItem, QGroupBox, QWidget,
    QApplication, QToolButton, QMenu
)
from PyQt6.QtCore import Qt

from omnigraph.ai.data_extractor import SmartDataExtractor
from omnigraph.core.worksheet import ColumnRole


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
        *,
        active_graph_title: Optional[str] = None,
        plot_by_default: bool = False,
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
        self.active_graph_title = active_graph_title
        self.plot_by_default = plot_by_default or active_graph_title is not None
        self.add_to_active_graph = False
        self.series_choice = "first"

        self.setWindowTitle("Import data")
        self.resize(840, 600)
        self.setMinimumSize(680, 500)
        self.setAcceptDrops(True)
        self._init_ui()

        if initial_text:
            self.tabs_source.setCurrentIndex(1)
            self.txt_paste.setPlainText(initial_text)
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

        btn_browse = QPushButton("Choose files…")
        btn_browse.setStyleSheet("font-weight: 600; padding: 5px 12px;")
        btn_browse.clicked.connect(self._browse_files)
        top_bar.addWidget(btn_browse)

        file_actions = QToolButton()
        file_actions.setText("More")
        file_actions.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        file_menu = QMenu(file_actions)
        file_menu.addAction("Add more files", self._add_files)
        file_menu.addAction("Remove selected file", self._remove_selected_file)
        file_menu.addAction("Clear files", self._clear_files)
        file_actions.setMenu(file_menu)
        top_bar.addWidget(file_actions)
        l_files.addLayout(top_bar)

        # List widget showing selected files
        self.list_files = QListWidget()
        self.list_files.setFixedHeight(75)
        self.list_files.currentRowChanged.connect(self._on_file_selection_changed)
        l_files.addWidget(self.list_files)

        self.tabs_source.addTab(tab_files, "Files")

        # Tab 1: Raw Text / Clipboard
        tab_paste = QWidget()
        l_paste = QVBoxLayout(tab_paste)
        l_paste.setContentsMargins(6, 6, 6, 6)
        l_paste.setSpacing(6)

        paste_btn_bar = QHBoxLayout()
        btn_paste_clip = QPushButton("Paste from clipboard")
        btn_paste_clip.setStyleSheet("font-weight: 600; padding: 4px 10px;")
        btn_paste_clip.clicked.connect(self._paste_clipboard)
        paste_btn_bar.addWidget(btn_paste_clip)

        examples = QToolButton()
        examples.setText("Try an example")
        examples.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        examples_menu = QMenu(examples)
        examples_menu.addAction("XRD scan", self._load_sample_xrd)
        examples_menu.addAction("Instrument log", self._load_sample_hplc)
        examples_menu.addAction("Spectrum", self._load_sample_spec)
        examples.setMenu(examples_menu)
        paste_btn_bar.addWidget(examples)
        paste_btn_bar.addStretch()
        l_paste.addLayout(paste_btn_bar)

        self.txt_paste = QTextEdit()
        self.txt_paste.setPlaceholderText("Paste messy table text, copied spreadsheet rows, or instrument logs here...")
        self.txt_paste.setFixedHeight(85)
        self.txt_paste.textChanged.connect(self._load_text_preview)
        l_paste.addWidget(self.txt_paste)

        self.tabs_source.addTab(tab_paste, "Paste text")
        self.tabs_source.currentChanged.connect(self._on_source_tab_changed)

        main_layout.addWidget(self.tabs_source)

        # Ingestion & Parsing Settings
        grp_settings = QGroupBox("Reading options")
        gl = QHBoxLayout(grp_settings)
        gl.setSpacing(10)

        # Delimiter
        gl.addWidget(QLabel("Separate columns by:"))
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
        gl.addWidget(QLabel("Column names:"))
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
        self.chk_auto_plot.setChecked(self.plot_by_default)
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
        self.lbl_preview_title = QLabel("Data preview")
        self.lbl_preview_title.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_preview_title.setWordWrap(True)
        preview_header_row.addWidget(self.lbl_preview_title)
        preview_header_row.addStretch()
        self.lbl_file_count_badge = QLabel("0 files selected")
        app = QApplication.instance()
        is_dark = getattr(app, "is_dark_theme", False) or "background-color: #181825" in (app.styleSheet() if app else "")
        badge_color = "#38bdf8" if is_dark else "#0369a1"
        self.lbl_file_count_badge.setStyleSheet(f"color: {badge_color}; font-weight: bold;")
        preview_header_row.addWidget(self.lbl_file_count_badge)
        main_layout.addLayout(preview_header_row)
        self.preview_details = QLabel("Choose a file or paste text to see a preview.")
        self.preview_details.setTextFormat(Qt.TextFormat.PlainText)
        self.preview_details.setWordWrap(True)
        self.preview_details.setProperty("role", "muted")
        main_layout.addWidget(self.preview_details)

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
        self.btn_ok.setProperty("role","primary")
        self.btn_ok.setStyleSheet("")
        self.btn_ok.clicked.connect(self._on_accept)
        buttons_layout.addWidget(self.btn_ok)

        main_layout.addLayout(buttons_layout)
        from omnigraph.ui.dialogs.dialog_layout import fold_section, finish_dialog
        grp_batch.layout().removeWidget(self.chk_auto_plot)
        self.chk_auto_plot.setText("Plot the imported data")
        main_layout.insertWidget(1, self.chk_auto_plot)
        self.graph_destination = QComboBox()
        self.graph_destination.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.graph_destination.setMinimumContentsLength(14)
        self.graph_destination.addItem("Create a new chart", False)
        if self.active_graph_title:
            self.graph_destination.addItem(f"Add to {self.active_graph_title}", True)
            self.graph_destination.setCurrentIndex(1)
            main_layout.insertWidget(2, self.graph_destination)
            self.chk_auto_plot.toggled.connect(self.graph_destination.setEnabled)
        else:
            self.graph_destination.hide()
        series_row = QHBoxLayout()
        series_label = QLabel("Plot series")
        self.series_combo = QComboBox()
        self.series_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.series_combo.setMinimumContentsLength(12)
        self.series_combo.setAccessibleName("Plot series")
        series_label.setBuddy(self.series_combo)
        series_row.addWidget(series_label)
        series_row.addWidget(self.series_combo, 1)
        self.series_options = QWidget()
        self.series_options.setLayout(series_row)
        main_layout.insertWidget(3 if self.active_graph_title else 2, self.series_options)
        self.series_options.setVisible(self.chk_auto_plot.isChecked())
        self.chk_auto_plot.toggled.connect(self.series_options.setVisible)
        self._update_plot_series()
        self.parsing_toggle, self.parsing_options = fold_section(grp_settings, "Adjust how data is read")
        self.destination_toggle, self.destination_options = fold_section(grp_batch, "Multiple-file and graph options")
        hint = QLabel("Choose files or paste text. Check the preview, then import. Headers and numbers are detected automatically on your computer.")
        hint.setWordWrap(True)
        main_layout.insertWidget(0, hint)
        self.btn_ok.setEnabled(False)
        finish_dialog(self)

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
            item = QListWidgetItem(f"{os.path.basename(p)} · {size_kb:.1f} KB · {ext}")
            item.setToolTip(p)
            self.list_files.addItem(item)

        count = len(self.filepaths)
        self.lbl_file_count_badge.setText(f"{count} file(s) selected")
        if count == 0:
            self.txt_path_display.setText("")
            self.filepath = ""
            self._load_file_preview()
        elif count == 1:
            self.txt_path_display.setText(self.filepaths[0])
            self.list_files.setCurrentRow(0)
        else:
            names = ", ".join(os.path.basename(p) for p in self.filepaths[:3])
            if count > 3:
                names += f" and {count - 3} more"
            self.txt_path_display.setText(f"{count} files: {names}")
            self.list_files.setCurrentRow(0)

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
        self.tabs_source.setCurrentIndex(1)
        self.txt_paste.setPlainText(sample_xrd)

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

    def _load_sample_spec(self):
        sample_spec = (
            "---------------------------------------------------\n"
            "Varian Cary 5000 UV-Vis-NIR Spectrophotometer\n"
            "Scan Speed: 600 nm/min, SBW: 2.0 nm\n"
            "Example: Synthetic spectroscopy data\n"
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

    def _update_plot_series(self, result=None):
        previous = self.series_combo.currentData()
        self.series_combo.clear()
        self.series_combo.addItem("First Y series", "first")
        self.series_combo.addItem("All Y series", "all")
        if result is not None and (self.tabs_source.currentIndex() == 1 or len(self.filepaths) == 1):
            columns = list(result.dataframe.columns)
            y_indices = [index for index, name in enumerate(columns)
                         if result.column_roles.get(name, ColumnRole.Y) == ColumnRole.Y]
            if not y_indices and columns:
                y_indices = [1 if len(columns) > 1 else 0]
            for index in y_indices:
                name = columns[index]
                label = result.column_long_names.get(name, str(name))
                units = result.column_units.get(name)
                if units:
                    label = f"{label} ({units})"
                self.series_combo.addItem(label, ("column", index))
        index = self.series_combo.findData(previous)
        self.series_combo.setCurrentIndex(max(0, index))

    def _render_preview(self, result, title):
        frame = result.dataframe
        preview = frame.head(15)
        self.imported_dataframe = frame
        self.table_prev.setColumnCount(len(preview.columns))
        self.table_prev.setHorizontalHeaderLabels([str(column) for column in preview.columns])
        self.table_prev.setRowCount(len(preview))
        for row in range(len(preview)):
            for column in range(len(preview.columns)):
                value = preview.iloc[row, column]
                display = "" if pd.isna(value) else (f"{value:.5g}" if isinstance(value, float) else str(value))
                self.table_prev.setItem(row, column, QTableWidgetItem(display))

        self._update_plot_series(result)
        metadata = result.metadata
        self.lbl_preview_title.setText(f"{title} · {len(frame):,} rows × {len(frame.columns)} numeric columns")
        row = metadata.get("HeaderRow", 1)
        details = {
            "first_row": f"Column names from row {row}.",
            "two_rows": f"Names from row {row}, units from row {row + 1}.",
            "none": "No header row. Column names were generated.",
            "fallback": "The table was irregular. Numbers were extracted by line; check the preview before importing.",
        }.get(metadata.get("HeaderMode"), "Column names follow the file format.")
        if metadata.get("Sheet"):
            details = f"Excel sheet: {metadata['Sheet']}. {details}"
        invalid_count = metadata.get("InvalidNumericCount", 0)
        if invalid_count:
            details += f" {invalid_count:,} nonnumeric or nonfinite values will be blank."
        dropped = metadata.get("DroppedColumns", [])
        if dropped:
            names = ", ".join(name[:30] for name in dropped[:3])
            details += f" {len(dropped)} columns without numbers will be skipped ({names})."
        if frame.empty:
            details += " No numeric data to import."
        self.preview_details.setText(details)
        self.preview_details.setToolTip("\n".join(metadata.get("InvalidNumericExamples", [])))
        self.btn_ok.setEnabled(not frame.empty or (self.tabs_source.currentIndex() == 0 and len(self.filepaths) > 1))
        index = self.combo_plot_type.findText(result.recommended_plot)
        if index >= 0:
            self.combo_plot_type.setCurrentIndex(index)

    def _clear_preview(self, message):
        self.imported_dataframe = None
        self.table_prev.setRowCount(0)
        self.table_prev.setColumnCount(0)
        self.lbl_preview_title.setText("Data preview")
        self.preview_details.setText(message)
        self.preview_details.setToolTip("")
        self._update_plot_series()
        self.btn_ok.setEnabled(False)

    def _reading_options(self):
        delimiter = self.combo_delim.currentData()
        return {
            "header_mode": self.combo_header.currentData(),
            "delimiter_override": None if delimiter == "auto" else (r"\s+" if delimiter == "whitespace" else delimiter),
        }

    def _load_text_preview(self):
        raw_text = self.txt_paste.toPlainText().strip()
        self.lbl_file_count_badge.setText("Pasted text")
        self.btn_ok.setText("Import pasted data")
        if not raw_text:
            self._clear_preview("Paste data to see a preview.")
            return
        try:
            result = SmartDataExtractor.extract_from_text(raw_text, source_name="Pasted_Data", **self._reading_options())
            self._render_preview(result, "Pasted text")
        except Exception as error:
            self._clear_preview(f"Could not read pasted data: {error}")

    def _load_file_preview(self):
        count = len(self.filepaths)
        self.lbl_file_count_badge.setText(f"{count} files" if count != 1 else "1 file")
        self.btn_ok.setText(f"Import {count} files" if count > 1 else "Import file")
        if not count or not self.filepath or not os.path.exists(self.filepath):
            self._clear_preview("Choose a file to see a preview.")
            return
        try:
            result = SmartDataExtractor.extract_from_file(self.filepath, **self._reading_options())
            self._render_preview(result, os.path.basename(self.filepath))
        except Exception as error:
            self._clear_preview(f"Could not read the selected file: {error}")
            self.btn_ok.setEnabled(count > 1)

    def _on_accept(self):
        """Processes either pasted raw text or selected files for import."""
        reading_options = self._reading_options()
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
                    **reading_options,
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
                        **reading_options,
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
        self.add_to_active_graph = self.auto_plot and self.graph_destination.currentData() is True
        self.series_choice = self.series_combo.currentData()

        self.accept()
