"""
Column properties and rename dialog.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QDialogButtonBox, QLabel
)
from omnigraph.core.worksheet import Column, ColumnRole


class ColumnPropertiesDialog(QDialog):
    """Dialog to edit column name, long name, units, comments, and role."""

    def __init__(self, column: Column, parent=None):
        super().__init__(parent)
        self.column = column
        self.setWindowTitle(f"Column Properties - {column.name}")
        self.resize(360, 260)
        self.setMinimumSize(320, 240)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Simplified single Column Name field
        initial_name = self.column.long_name if self.column.long_name else self.column.name
        self.txt_name = QLineEdit(initial_name)
        self.txt_name.setPlaceholderText("e.g. Time, Absorbance, Concentration...")
        form.addRow("Column Name:", self.txt_name)

        # Retain txt_long_name reference as alias for backwards compatibility
        self.txt_long_name = self.txt_name

        self.lbl_id = QLabel(f"Col {self.column.name}")
        self.lbl_id.setStyleSheet("color: #64748b; font-style: italic;")
        form.addRow("Identifier:", self.lbl_id)

        self.txt_units = QLineEdit(self.column.units)
        form.addRow("Units:", self.txt_units)

        self.txt_comments = QLineEdit(self.column.comments)
        form.addRow("Comments:", self.txt_comments)

        self.combo_role = QComboBox()
        for r in ColumnRole:
            self.combo_role.addItem(r.value)
        self.combo_role.setCurrentText(self.column.role.value)
        form.addRow("Role / Type:", self.combo_role)

        layout.addLayout(form)
        layout.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        val = self.txt_name.text().strip()
        self.column.long_name = val
        if not self.column.name and val:
            self.column.name = val
        self.column.units = self.txt_units.text().strip()
        self.column.comments = self.txt_comments.text().strip()
        self.column.role = ColumnRole(self.combo_role.currentText())
        self.accept()
