"""Select new worksheet columns for the measured series on a chart."""
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QLabel, QMessageBox, QVBoxLayout,
)

from omnigraph.core.plot_editing import match_series
from omnigraph.core.column_matching import column_signature, numeric_pairs
from omnigraph.ui.dialogs.dialog_layout import finish_dialog


class ReplaceDataDialog(QDialog):
    def __init__(self, project, graph, duplicate=False, parent=None, *, source=None, column_specs=None):
        super().__init__(parent)
        self.project = project
        self.column_specs = column_specs
        self.series = [curve for curve in graph.curves if not curve.is_fit_curve]
        self.sources = [(wb, ws) for wb in project.workbooks for ws in wb.sheets if ws.column_count()]
        self.mappings = []
        self.setWindowTitle("Duplicate chart with new data" if duplicate else "Replace chart data")
        self.resize(520, 530)
        layout = QVBoxLayout(self)
        hint = QLabel(
            "Graffy matches columns by name, units, and role. Check the selections and fill in any missing matches. "
            "The chart keeps its styling and uses the new data for its legend."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)
        source_form = QFormLayout()
        self.source = self._column_combo()
        for wb, ws in self.sources:
            self.source.addItem(f"{wb.name} / {ws.name}")
        if self.series:
            first = self.series[0]
            source = source or (first.source_workbook, first.source_sheet)
            original = next((i for i, (wb, ws) in enumerate(self.sources)
                             if (wb.name, ws.name) == source), 0)
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
        combo.setPlaceholderText("Choose a column")
        return combo

    def _populate_columns(self):
        if not self.sources:
            return
        _, sheet = self.sources[self.source.currentIndex()]
        for index, (curve, controls) in enumerate(zip(self.series, self.column_controls)):
            for combo in controls:
                combo.clear()
            x, y, err = controls
            err.addItem("None", None)
            for index, column in enumerate(sheet.columns):
                name = f"{column.name} · {column.display_label}" if column.long_name or column.units else column.name
                for combo in controls:
                    combo.addItem(name, index)
            original = self.project.get_worksheet(curve.source_workbook, curve.source_sheet)
            if self.column_specs is not None:
                specs = self.column_specs[index]
                x_index, y_index, error_index = match_series(sheet, specs)
            elif original is sheet:
                x_index, y_index, error_index = curve.x_col_idx, curve.y_col_idx, curve.y_err_col_idx
                specs = (None, None, error_index)
            elif original is not None:
                indices = (curve.x_col_idx, curve.y_col_idx, curve.y_err_col_idx)
                specs = [column_signature(col) if (col := original.get_column(i)) else None for i in indices]
                x_index, y_index, error_index = match_series(sheet, specs)
            else:
                specs = (None, None, None)
                x_index = y_index = error_index = None
            x.setCurrentIndex(-1 if x_index is None else x_index)
            y.setCurrentIndex(-1 if y_index is None else y_index)
            err.setCurrentIndex(error_index + 1 if error_index is not None else (-1 if specs[2] is not None else 0))

    def _accept_mapping(self):
        workbook, sheet = self.sources[self.source.currentIndex()]
        mappings = []
        for curve, (x, y, err) in zip(self.series, self.column_controls):
            x_idx, y_idx = x.currentData(), y.currentData()
            x_values, _ = numeric_pairs(sheet, x_idx, y_idx)
            if not len(x_values) or err.currentIndex() < 0:
                QMessageBox.warning(self, "Choose numeric columns",
                                    f"Choose X and Y columns with included numeric data and choose a Y error column or None for “{curve.label}”.")
                return
            mappings.append((workbook.name, sheet.name, x_idx, y_idx, err.currentData(), sheet.columns[y_idx].display_label))
        self.mappings = mappings
        self.accept()
