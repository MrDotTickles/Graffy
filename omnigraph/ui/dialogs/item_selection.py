"""A checklist for running the same operation on several project items."""

from PyQt6.QtCore import Qt, QSignalBlocker
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout,
)

from omnigraph.ui.dialogs.dialog_layout import finish_dialog


def choose_items(parent, title, hint, action, labels, selected):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.resize(440, 390)
    layout = QVBoxLayout(dialog)
    prompt = QLabel(hint)
    prompt.setWordWrap(True)
    layout.addWidget(prompt)
    items = QListWidget()
    for index, label in enumerate(labels):
        item = QListWidgetItem(label, items)
        item.setCheckState(Qt.CheckState.Checked if index in selected else Qt.CheckState.Unchecked)
    toolbar = QHBoxLayout()
    layout.addLayout(toolbar)
    layout.addWidget(items)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    proceed = buttons.button(QDialogButtonBox.StandardButton.Ok)
    proceed.setText(action)
    proceed.setProperty("role", "primary")

    def checked_indices():
        return [index for index in range(items.count())
                if items.item(index).checkState() == Qt.CheckState.Checked]

    def set_all(checked):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        with QSignalBlocker(items):
            for index in range(items.count()):
                items.item(index).setCheckState(state)
        proceed.setEnabled(checked and bool(items.count()))

    if len(labels) > 1:
        check_all = QPushButton("Select all")
        check_all.clicked.connect(lambda: set_all(True))
        toolbar.addWidget(check_all)
        clear = QPushButton("Clear selection")
        clear.clicked.connect(lambda: set_all(False))
        toolbar.addWidget(clear)
        toolbar.addStretch()
    items.itemChanged.connect(lambda: proceed.setEnabled(bool(checked_indices())))
    proceed.setEnabled(bool(selected))
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    finish_dialog(dialog, scroll_body=False)
    return checked_indices() if dialog.exec() else []
