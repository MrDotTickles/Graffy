"""Select new worksheet columns for the measured series on a chart."""
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QLabel, QMessageBox, QVBoxLayout,
)

from omnigraph.ui.dialogs.dialog_layout import finish_dialog


class ReplaceDataDialog(QDialog):
    def __init__(self, project, graph, duplicate=False, parent=None):
        super().__init__(parent)
        self.series = [curve for curve in graph.curves if not curve.is_fit_curve]
        self.sources = [(wb, ws) for wb in project.workbooks for ws in wb.sheets if ws.column_count()]
        self.mappings = []
        self.setWindowTitle("Duplicate chart with new data" if duplicate else "Replace chart data")
        self.resize(520, 530)
        layout = QVBoxLayout(self)
        hint = QLabel(
            "Choose a worksheet and match its columns to the chart’s series. "
            "Colors, axes and layout are kept. Legend names follow the new data. Fits and significance marks are cleared."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)
        source_form = QFormLayout()
        self.source = self._column_combo()
        for wb, ws in self.sources:
            self.source.addItem(f"{wb.name} / {ws.name}")
        if self.series:
            first = self.series[0]
            original = next((i for i, (wb, ws) in enumerate(self.sources)
                             if (wb.name, ws.name) == (first.source_workbook, first.source_sheet)), 0)
            self.source.setCurrentIndex(original)
        source_form.addRow("Worksheet", self.source)
        layout.addLayout(source_form)
        self.column_controls = []
        for curve in self.series:
            group = QGroupBox(curve.label.replace("&", "&&"))
            form = QFormLayout(group)
            form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
            x, y, err = (self._column_combo() for _ in range(3))
            form.addRow("Horizontal (X)", x)
            form.addRow("Vertical (Y)", y)
            form.addRow("Y error", err)
            self.column_controls.append((x, y, err))
            layout.addWidget(group)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        confirm = buttons.button(QDialogButtonBox.StandardButton.Ok)
        confirm.setText("Create copy" if duplicate else "Replace data")
        confirm.setProperty("role", "primary")
        confirm.setEnabled(bool(self.sources and self.series))
        buttons.accepted.connect(self._accept_mapping)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.source.currentIndexChanged.connect(self._populate_columns)
        self._populate_columns()
        finish_dialog(self)

    @staticmethod
    def _column_combo():
        combo = QComboBox()
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(9)
        return combo

    def _populate_columns(self):
        if not self.sources:
            return
        _, sheet = self.sources[self.source.currentIndex()]
        for curve, controls in zip(self.series, self.column_controls):
            for combo in controls:
                combo.clear()
            x, y, err = controls
            err.addItem("None", None)
            for index, column in enumerate(sheet.columns):
                name = f"{column.name} · {column.display_label}" if column.long_name or column.units else column.name
                for combo in controls:
                    combo.addItem(name, index)
            x.setCurrentIndex(min(curve.x_col_idx, sheet.column_count() - 1))
            y.setCurrentIndex(min(curve.y_col_idx, sheet.column_count() - 1))
            error_index = sheet.find_y_error_column_for(y.currentData())
            err.setCurrentIndex(error_index + 1 if error_index is not None else 0)

    def _accept_mapping(self):
        workbook, sheet = self.sources[self.source.currentIndex()]
        mappings = []
        for curve, (x, y, err) in zip(self.series, self.column_controls):
            x_idx, y_idx = x.currentData(), y.currentData()
            x_col, y_col = sheet.columns[x_idx], sheet.columns[y_idx]
            x_values, _, _ = x_col.get_valid_numeric_pairs(y_col)
            if not len(x_values):
                QMessageBox.warning(self, "Choose numeric columns",
                                    f"“{curve.label}” needs at least one pair of included numeric values.")
                return
            mappings.append((workbook.name, sheet.name, x_idx, y_idx, err.currentData(), y_col.display_label))
        self.mappings = mappings
        self.accept()
