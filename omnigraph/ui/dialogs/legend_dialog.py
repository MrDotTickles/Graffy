"""
Key & Legend Editor Dialog.
Allows users to quickly rename series labels in the key, customize legend positioning,
frame borders, font sizes, and apply batch label naming presets.
"""

from typing import List, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QGroupBox,
    QDialogButtonBox, QLabel, QScrollArea, QWidget, QCheckBox, QComboBox,
    QSpinBox, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from omnigraph.core.project import GraphModel


class LegendEditorDialog(QDialog):
    """Intuitive modal for editing series names in the key (legend) and legend styling."""

    def __init__(self, graph: GraphModel, parent=None, on_apply_callback=None):
        super().__init__(parent)
        self.graph = graph
        self.on_apply_callback = on_apply_callback
        self.setWindowTitle(f"🔑 Key & Legend Editor - {graph.title}")
        self.resize(540, 480)
        self.setMinimumSize(460, 380)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header description
        lbl_info = QLabel("<b>Edit Series Labels in the Key</b><br>"
                          "<span style='color: #64748b; font-size: 11px;'>"
                          "Rename how each data layer appears in the legend, or adjust placement and appearance."
                          "</span>")
        lbl_info.setWordWrap(True)
        layout.addWidget(lbl_info)

        # Series Labels Group
        grp_series = QGroupBox("Series Labels in Key")
        v_series = QVBoxLayout(grp_series)
        v_series.setSpacing(6)

        # Table for series labels
        self.table_series = QTableWidget()
        self.table_series.setColumnCount(4)
        self.table_series.setHorizontalHeaderLabels(["Layer", "Color", "Type", "Key Label"])
        self.table_series.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_series.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_series.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_series.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table_series.verticalHeader().setVisible(False)
        self.table_series.setAlternatingRowColors(True)

        self._populate_series_table()
        v_series.addWidget(self.table_series)

        # Quick preset buttons row
        btn_row = QHBoxLayout()
        btn_number = QPushButton("1, 2, 3...")
        btn_number.setToolTip("Auto-number series labels (Series 1, Series 2, ...)")
        btn_number.clicked.connect(self._preset_number_series)
        btn_row.addWidget(btn_number)

        btn_prefix = QPushButton("Add Prefix...")
        btn_prefix.setToolTip("Prepend text to all series labels")
        btn_prefix.clicked.connect(self._preset_add_prefix)
        btn_row.addWidget(btn_prefix)

        btn_suffix = QPushButton("Add Suffix...")
        btn_suffix.setToolTip("Append text to all series labels")
        btn_suffix.clicked.connect(self._preset_add_suffix)
        btn_row.addWidget(btn_suffix)

        btn_clear = QPushButton("Reset to Y Column")
        btn_clear.setToolTip("Reset labels back to their source column names")
        btn_clear.clicked.connect(self._preset_reset_to_columns)
        btn_row.addWidget(btn_clear)

        v_series.addLayout(btn_row)
        layout.addWidget(grp_series)

        # Legend Appearance Group
        grp_opts = QGroupBox("Key / Legend Display Options")
        fl_opts = QFormLayout(grp_opts)

        self.chk_show = QCheckBox("Show Key / Legend on Graph")
        self.chk_show.setChecked(self.graph.legend_show)
        fl_opts.addRow("Visibility:", self.chk_show)

        self.combo_pos = QComboBox()
        self.combo_pos.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_pos.setMinimumContentsLength(8)
        self.combo_pos.addItems([
            "best", "upper right", "upper left", "lower left",
            "lower right", "center right", "outside right"
        ])
        self.combo_pos.setCurrentText(self.graph.legend_location)
        fl_opts.addRow("Position:", self.combo_pos)

        row_style = QHBoxLayout()
        self.chk_frame = QCheckBox("Draw Border Frame")
        self.chk_frame.setChecked(self.graph.legend_frame)
        row_style.addWidget(self.chk_frame)

        row_style.addSpacing(20)
        row_style.addWidget(QLabel("Font Size:"))
        self.spn_fs = QSpinBox()
        self.spn_fs.setRange(6, 28)
        self.spn_fs.setValue(int(self.graph.legend_font_size))
        row_style.addWidget(self.spn_fs)
        row_style.addStretch()

        fl_opts.addRow("Box & Font:", row_style)
        layout.addWidget(grp_opts)

        # Dialog Buttons
        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("Apply")
        self.btn_apply.setToolTip("Apply changes immediately to canvas")
        self.btn_apply.clicked.connect(self._apply_changes)
        btn_layout.addWidget(self.btn_apply)

        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_ok = QPushButton("OK")
        btn_ok.setDefault(True)
        btn_ok.setStyleSheet("font-weight: bold; background-color: #0284c7; color: white; padding: 5px 15px; border-radius: 4px;")
        btn_ok.clicked.connect(self._on_ok)
        btn_layout.addWidget(btn_ok)

        layout.addLayout(btn_layout)

    def _populate_series_table(self):
        self.table_series.setRowCount(len(self.graph.curves))
        for row, curve in enumerate(self.graph.curves):
            # Layer number
            item_num = QTableWidgetItem(f"Layer {row + 1}")
            item_num.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table_series.setItem(row, 0, item_num)

            # Color swatch
            item_col = QTableWidgetItem("  ●  ")
            item_col.setForeground(QColor(curve.color))
            item_col.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table_series.setItem(row, 1, item_col)

            # Plot type
            item_type = QTableWidgetItem(curve.plot_type)
            item_type.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table_series.setItem(row, 2, item_type)

            # Editable Key Label
            item_label = QTableWidgetItem(curve.label or f"Curve {row + 1}")
            self.table_series.setItem(row, 3, item_label)

    def _apply_changes(self):
        """Saves current table edits and legend properties to GraphModel and refreshes."""
        try:
            for row in range(min(len(self.graph.curves), self.table_series.rowCount())):
                item = self.table_series.item(row, 3)
                if item:
                    self.graph.curves[row].label = item.text().strip() or f"Curve {row + 1}"

            self.graph.legend_show = self.chk_show.isChecked()
            self.graph.legend_location = self.combo_pos.currentText()
            self.graph.legend_frame = self.chk_frame.isChecked()
            self.graph.legend_font_size = float(self.spn_fs.value())

            if callable(self.on_apply_callback):
                self.on_apply_callback()
        except Exception as e:
            QMessageBox.warning(self, "Notice", f"Could not apply all legend changes:\n{e}")

    def _on_ok(self):
        try:
            self._apply_changes()
        finally:
            self.accept()

    def _preset_number_series(self):
        for row in range(self.table_series.rowCount()):
            self.table_series.setItem(row, 3, QTableWidgetItem(f"Series {row + 1}"))

    def _preset_add_prefix(self):
        prefix, ok = QInputDialog.getText(self, "Add Prefix", "Enter prefix to prepend to each key label:")
        if ok and prefix:
            for row in range(self.table_series.rowCount()):
                cur = self.table_series.item(row, 3).text() if self.table_series.item(row, 3) else ""
                self.table_series.setItem(row, 3, QTableWidgetItem(f"{prefix}{cur}"))

    def _preset_add_suffix(self):
        suffix, ok = QInputDialog.getText(self, "Add Suffix", "Enter suffix to append to each key label:")
        if ok and suffix:
            for row in range(self.table_series.rowCount()):
                cur = self.table_series.item(row, 3).text() if self.table_series.item(row, 3) else ""
                self.table_series.setItem(row, 3, QTableWidgetItem(f"{cur}{suffix}"))

    def _preset_reset_to_columns(self):
        for row, curve in enumerate(self.graph.curves):
            col_name = getattr(curve, "y_col_name", None) or curve.label or f"Curve_{row + 1}"
            self.table_series.setItem(row, 3, QTableWidgetItem(col_name))
