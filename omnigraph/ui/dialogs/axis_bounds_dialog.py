"""Edit numeric limits saved with a chart."""
from math import isfinite

from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QLabel, QLineEdit,
    QVBoxLayout,
)

from omnigraph.ui.dialogs.dialog_layout import finish_dialog


class AxisBoundsDialog(QDialog):
    def __init__(self, graph, axes, focus_axis="", parent=None):
        super().__init__(parent)
        self.graph = graph
        self.controls = {}
        self.setWindowTitle("Axis bounds")
        self.resize(425, 385)
        layout = QVBoxLayout(self)
        hint = QLabel("Use Automatic to fit the data. Turn it off to enter a minimum and maximum.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        for key, title, axis, direction in axes:
            group = QGroupBox(title)
            form = QFormLayout(group)
            form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
            automatic = QCheckBox("Automatic")
            automatic.setChecked(getattr(graph, f"{key}_auto_limits"))
            form.addRow(automatic)
            limits = axis.get_xlim() if direction == "x" else axis.get_ylim()
            if not automatic.isChecked():
                saved = getattr(graph, f"{key}_min"), getattr(graph, f"{key}_max")
                if all(isinstance(value, (int, float)) and isfinite(value) for value in saved):
                    limits = saved
            lower, upper = (QLineEdit(format(value, ".15g")) for value in limits)
            for name, field in (("Minimum", lower), ("Maximum", upper)):
                field.setAccessibleName(f"{title} {name.lower()}")
                field.setEnabled(not automatic.isChecked())
                automatic.toggled.connect(lambda checked, field=field: field.setEnabled(not checked))
                form.addRow(name, field)
            self.controls[key] = (title, automatic, lower, upper, axis, direction)
            layout.addWidget(group)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setProperty("role", "muted")
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        apply = buttons.button(QDialogButtonBox.StandardButton.Ok)
        apply.setText("Apply bounds")
        apply.setProperty("role", "primary")
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        finish_dialog(self)
        if focus_axis in self.controls:
            _, automatic, lower, _, _, _ = self.controls[focus_axis]
            (automatic if automatic.isChecked() else lower).setFocus()

    def _apply(self):
        settings = {}
        for key, (title, automatic, lower, upper, axis, direction) in self.controls.items():
            if automatic.isChecked():
                settings[key] = (True, None, None)
                continue
            try:
                minimum, maximum = float(lower.text()), float(upper.text())
            except ValueError:
                self.error.setText(f"{title} needs two numbers. You can enter a value like 1e-6.")
                lower.setFocus()
                return
            if not isfinite(minimum) or not isfinite(maximum) or minimum >= maximum:
                self.error.setText(f"{title} minimum must be smaller than the maximum. Both need to be finite.")
                lower.setFocus()
                return
            scale = axis.get_xscale() if direction == "x" else axis.get_yscale()
            if scale == "log" and minimum <= 0:
                self.error.setText(f"{title} is logarithmic, so both bounds must be greater than zero.")
                lower.setFocus()
                return
            settings[key] = (False, minimum, maximum)
        for key, (automatic, minimum, maximum) in settings.items():
            setattr(self.graph, f"{key}_auto_limits", automatic)
            setattr(self.graph, f"{key}_min", minimum)
            setattr(self.graph, f"{key}_max", maximum)
        self.accept()
