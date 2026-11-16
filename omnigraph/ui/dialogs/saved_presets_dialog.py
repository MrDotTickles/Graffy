"""Rename or remove the presets used in import and charting."""

from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QInputDialog, QLabel, QListWidget,
    QMessageBox, QPushButton, QVBoxLayout,
)

from omnigraph.ui.dialogs.dialog_layout import finish_dialog
from omnigraph.ui.saved_settings import load_settings, store_settings


class SavedPresetsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage saved presets")
        self.resize(460, 385)
        layout = QVBoxLayout(self)
        self.kind = QComboBox()
        self.kind.setAccessibleName("Preset category")
        self.kind.addItem("Chart setups", "charts/setups")
        self.kind.addItem("Import reading presets", "import/reading_profiles")
        layout.addWidget(self.kind)

        self.names = QListWidget()
        self.names.setAccessibleName("Saved preset names")
        layout.addWidget(self.names, 1)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.hint.setProperty("role", "muted")
        layout.addWidget(self.hint)

        actions = QHBoxLayout()
        self.rename = QPushButton("Rename…")
        self.rename.clicked.connect(self._rename)
        actions.addWidget(self.rename)
        self.remove = QPushButton("Remove…")
        self.remove.clicked.connect(self._remove)
        actions.addWidget(self.remove)
        actions.addStretch()
        layout.addLayout(actions)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.kind.currentIndexChanged.connect(lambda: self._refresh())
        self.names.currentItemChanged.connect(self._update_buttons)
        self.names.itemActivated.connect(self._rename)
        finish_dialog(self, scroll_body=False)
        self._refresh()

    def _refresh(self, *, select=None):
        key = self.kind.currentData()
        self.presets = load_settings(key)
        self.names.clear()
        self.names.addItems(sorted(self.presets, key=str.casefold))
        if self.names.count():
            names = [self.names.item(index).text() for index in range(self.names.count())]
            self.names.setCurrentRow(names.index(select) if select in names else 0)
            self.hint.setText("These presets are stored on this computer.")
        elif key == "charts/setups":
            self.hint.setText("Save a chart setup from a chart’s Data menu.")
        else:
            self.hint.setText("Save a reading preset from the import window’s Reading options.")
        self._update_buttons()

    def _update_buttons(self):
        selected = self.names.currentItem() is not None
        self.rename.setEnabled(selected)
        self.remove.setEnabled(selected)

    def _rename(self):
        item = self.names.currentItem()
        if item is None:
            return
        original = item.text()
        name, confirmed = QInputDialog.getText(self, "Rename preset", "New name", text=original)
        name = name.strip()
        if not confirmed or not name or name == original:
            return
        if name in self.presets:
            QMessageBox.information(self, "Name already used", "Choose a different preset name.")
            return
        self.presets[name] = self.presets.pop(original)
        store_settings(self.kind.currentData(), self.presets)
        self._refresh(select=name)

    def _remove(self):
        item = self.names.currentItem()
        if item is None:
            return
        name = item.text()
        response = QMessageBox.question(
            self, "Remove saved preset?", f"Remove “{name}” from the saved presets on this computer?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
        )
        if response == QMessageBox.StandardButton.Yes:
            del self.presets[name]
            store_settings(self.kind.currentData(), self.presets)
            self._refresh()
