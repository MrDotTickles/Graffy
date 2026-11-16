"""Search common task actions in the current workspace."""

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout,
)

from omnigraph.ui.dialogs.dialog_layout import finish_dialog


class ActionSearchDialog(QDialog):
    def __init__(self, actions, parent=None):
        super().__init__(parent)
        self.actions = actions
        self.selected_action = None
        self.setWindowTitle("Find a Graffy action")
        self.resize(490, 450)

        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search actions, for example axis or export")
        self.search.setAccessibleName("Search Graffy actions")
        self.search.installEventFilter(self)
        layout.addWidget(self.search)
        self.results = QListWidget()
        self.results.setAccessibleName("Matching actions")
        layout.addWidget(self.results, 1)
        self.empty = QLabel("No matching actions in the current workspace.")
        self.empty.setProperty("role", "muted")
        self.empty.setWordWrap(True)
        layout.addWidget(self.empty)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Open | QDialogButtonBox.StandardButton.Cancel)
        self.run = buttons.button(QDialogButtonBox.StandardButton.Open)
        self.run.setText("Run action")
        self.run.setProperty("role", "primary")
        buttons.accepted.connect(self._select_action)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.search.textChanged.connect(self._filter)
        self.results.itemActivated.connect(self._select_action)
        finish_dialog(self, scroll_body=False)
        self._filter()
        self.search.setFocus()

    def _filter(self):
        terms = self.search.text().casefold().split()
        self.results.clear()
        for index, (label, keywords, _) in enumerate(self.actions):
            searchable = f"{label} {keywords}".casefold()
            if all(term in searchable for term in terms):
                item = QListWidgetItem(label, self.results)
                item.setData(Qt.ItemDataRole.UserRole, index)
        have_results = bool(self.results.count())
        self.empty.setVisible(not have_results)
        self.run.setEnabled(have_results)
        if have_results:
            self.results.setCurrentRow(0)

    def eventFilter(self, watched, event):
        if watched is self.search and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key in {Qt.Key.Key_Down, Qt.Key.Key_Up} and self.results.count():
                offset = 1 if key == Qt.Key.Key_Down else -1
                self.results.setCurrentRow((self.results.currentRow() + offset) % self.results.count())
                return True
            if key in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
                self._select_action()
                return True
        return super().eventFilter(watched, event)

    def _select_action(self):
        item = self.results.currentItem()
        if item:
            self.selected_action = self.actions[item.data(Qt.ItemDataRole.UserRole)][2]
            self.accept()
