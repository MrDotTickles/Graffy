"""
Quick Edit Labels dialog.
Fast, intuitive dialog to edit Graph Title, Axis Titles, and Legend Series Names in one place.
"""

from typing import List
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QGroupBox,
    QDialogButtonBox, QLabel, QScrollArea, QWidget
)
from omnigraph.core.project import GraphModel


class QuickLabelsDialog(QDialog):
    """Dialog to easily edit all titles and labels for a graph."""

    def __init__(self, graph: GraphModel, parent=None):
        super().__init__(parent)
        self.graph = graph
        self.setWindowTitle(f"Edit Labels & Titles - {graph.title}")
        self.resize(460, 400)
        self.setMinimumSize(400, 320)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # 1. Main Axis Titles
        grp_axes = QGroupBox("Graph & Axis Titles")
        fl_axes = QFormLayout(grp_axes)

        self.txt_title = QLineEdit(self.graph.title_text)
        fl_axes.addRow("Graph Title:", self.txt_title)

        self.txt_x = QLineEdit(self.graph.x_title)
        fl_axes.addRow("X Axis (Bottom):", self.txt_x)

        self.txt_y = QLineEdit(self.graph.y_title)
        fl_axes.addRow("Y Axis (Left):", self.txt_y)

        has_twin_x = any(c.axis == "secondary" for c in self.graph.curves) or self.graph.layout_mode == "twin_x"
        if has_twin_x or self.graph.y2_title:
            self.txt_y2 = QLineEdit(self.graph.y2_title)
            fl_axes.addRow("Y Axis (Right / Twin-Y):", self.txt_y2)
        else:
            self.txt_y2 = None

        if self.graph.layout_mode == "stacked_2x1":
            self.txt_y_bottom = QLineEdit(self.graph.y_bottom_title)
            fl_axes.addRow("Y Axis (Bottom Panel):", self.txt_y_bottom)
        else:
            self.txt_y_bottom = None

        layout.addWidget(grp_axes)

        # 2. Curve / Series Legend Labels
        grp_curves = QGroupBox("Legend Series Labels")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w_curves = QWidget()
        fl_curves = QFormLayout(w_curves)

        self.curve_edits: List[QLineEdit] = []
        for i, curve in enumerate(self.graph.curves):
            edit = QLineEdit(curve.label)
            lbl = QLabel(f"<span style='color: {curve.color};'>●</span> <b>Layer {i + 1}</b> ({curve.plot_type}):")
            fl_curves.addRow(lbl, edit)
            self.curve_edits.append(edit)

        scroll.setWidget(w_curves)
        cl = QVBoxLayout(grp_curves)
        cl.addWidget(scroll)
        layout.addWidget(grp_curves)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        self.graph.title_text = self.txt_title.text().strip()
        self.graph.x_title = self.txt_x.text().strip()
        self.graph.y_title = self.txt_y.text().strip()
        if self.txt_y2:
            self.graph.y2_title = self.txt_y2.text().strip()
        if self.txt_y_bottom:
            self.graph.y_bottom_title = self.txt_y_bottom.text().strip()

        for i, edit in enumerate(self.curve_edits):
            if i < len(self.graph.curves):
                self.graph.curves[i].label = edit.text().strip() or f"Curve {i + 1}"

        self.accept()
