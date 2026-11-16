"""Show layout tiles for a drop that did not land on a specific layout."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QSizePolicy, QVBoxLayout

from omnigraph.ui.chart_layout_picker import ChartLayoutPicker
from omnigraph.ui.dialogs.dialog_layout import finish_dialog


class ChartDropDialog(QDialog):
    def __init__(self, source, chart_title, parent=None):
        super().__init__(parent)
        self.choice = None
        self.setWindowTitle("Plot dropped data")
        self.source_text = f"{source} → {chart_title}"
        self.setAccessibleDescription(self.source_text)
        layout = QVBoxLayout(self)
        self.source_label = QLabel(self.source_text)
        self.source_label.setTextFormat(Qt.TextFormat.PlainText)
        self.source_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.source_label.setToolTip(self.source_text)
        self.source_label.setProperty("role", "muted")
        layout.addWidget(self.source_label)

        self.picker = ChartLayoutPicker("Choose a layout")
        self.picker.selected.connect(self._choose)
        layout.addWidget(self.picker)
        layout.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(460, 350)
        finish_dialog(self)
        self.picker.tiles["add"].setFocus()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        display = self.source_label.fontMetrics().elidedText(
            self.source_text, Qt.TextElideMode.ElideRight, max(0, self.width() - 40),
        )
        self.source_label.setText(display)

    def _choose(self, choice):
        self.choice = choice
        self.accept()
