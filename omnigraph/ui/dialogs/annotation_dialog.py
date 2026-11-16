"""Edit chart notes and reference lines with one undoable save."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit,
    QPushButton, QVBoxLayout,
)

from omnigraph.ui.color_field import ColorField
from omnigraph.ui.dialogs.dialog_layout import finish_dialog, fold_section



class AnnotationDialog(QDialog):
    def __init__(self, annotation, parent=None, *, adding=False):
        super().__init__(parent)
        self.result_annotation = None
        self.original = annotation
        self.is_text = annotation["type"] == "text"
        name = "text note" if self.is_text else "reference line"
        self.setWindowTitle(f"{'Add' if adding else 'Edit'} {name}")
        self.resize(420, 450 if self.is_text else 315)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)

        if self.is_text:
            self.text = QPlainTextEdit(annotation.get("text", ""))
            self.text.setPlaceholderText("Type your note")
            self.text.setAccessibleName("Note text")
            self.text.setMaximumHeight(115)
            self.text.setTabChangesFocus(True)
            form.addRow(self.text)
            self.size = QDoubleSpinBox()
            self.size.setRange(4, 200)
            self.size.setDecimals(1)
            self.size.setSuffix(" pt")
            self.size.setValue(annotation.get("font_size", 10))
            form.addRow("Font size", self.size)
            self.rotation = QDoubleSpinBox()
            self.rotation.setRange(-360, 360)
            self.rotation.setDecimals(1)
            self.rotation.setSuffix("°")
            angle = float(annotation.get("rotation", 0))
            self.rotation.setValue((angle + 180) % 360 - 180 if not -360 <= angle <= 360 else angle)
            self.rotation.setToolTip("Positive values rotate the note counterclockwise.")
            form.addRow("Rotation", self.rotation)
        else:
            self.value = QDoubleSpinBox()
            self.value.setRange(-1e15, 1e15)
            self.value.setDecimals(10)
            self.value.setValue(annotation.get("value", 0))
            form.addRow("Y value" if annotation.get("orientation") == "h" else "X value", self.value)
            self.label = QLineEdit(annotation.get("label", ""))
            self.label.setPlaceholderText("Leave blank to omit from the legend")
            form.addRow("Legend label", self.label)
            self.line_style = QComboBox()
            for label, code in (("Solid", "-"), ("Dashed", "--"), ("Dotted", ":"), ("Dash-dot", "-.")):
                self.line_style.addItem(label, code)
            self.line_style.setCurrentIndex(max(0, self.line_style.findData(annotation.get("style", "--"))))
            form.addRow("Line style", self.line_style)
        self.color = ColorField(annotation.get("color", "auto"), title="Note color" if self.is_text else "Line color")
        form.addRow("Text color" if self.is_text else "Line color", self.color)
        layout.addLayout(form)

        if self.is_text:
            group = QGroupBox()
            style = QFormLayout(group)
            style.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
            self.family = QComboBox()
            for label, code in (("Theme default", ""), ("Sans serif", "sans-serif"),
                                ("Serif", "serif"), ("Monospace", "monospace")):
                self.family.addItem(label, code)
            self.family.setCurrentIndex(max(0, self.family.findData(annotation.get("font_family", ""))))
            style.addRow("Typeface", self.family)
            emphasis = QHBoxLayout()
            self.bold = QCheckBox("Bold")
            self.bold.setChecked(annotation.get("bold", False))
            self.italic = QCheckBox("Italic")
            self.italic.setChecked(annotation.get("italic", False))
            emphasis.addWidget(self.bold)
            emphasis.addWidget(self.italic)
            style.addRow("Emphasis", emphasis)
            self.alignment = QComboBox()
            for alignment in ("left", "center", "right"):
                self.alignment.addItem(alignment.capitalize(), alignment)
            self.alignment.setCurrentIndex(max(0, self.alignment.findData(annotation.get("alignment", "left"))))
            style.addRow("Text alignment", self.alignment)
            self.background = ColorField(annotation.get("background", "none"), title="Note background",
                                         allow_transparent=True)
            style.addRow("Background", self.background)
            self.math = QCheckBox("Render math inside $…$")
            self.math.setChecked(annotation.get("parse_math", "text" in annotation))
            style.addRow(self.math)
            layout.addWidget(group)
            fold_section(group, "More text styling")

        self.error = QLabel()
        self.error.setWordWrap(True)
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.save_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.save_button.setText(f"Add {name}" if adding else "Save changes")
        self.save_button.setProperty("role", "primary")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        finish_dialog(self)
        if self.is_text:
            self.text.textChanged.connect(self._update_save)
            self._update_save()
            self.text.setFocus()

    def _update_save(self):
        self.save_button.setEnabled(bool(self.text.toPlainText().strip()))

    def _save(self):
        updated = {**self.original, "color": self.color.color()}
        if self.is_text:
            text = self.text.toPlainText().strip()
            if not text:
                return
            if self.math.isChecked():
                from matplotlib.cbook import is_math_text
                from matplotlib.mathtext import MathTextParser

                parser = MathTextParser("path")
                try:
                    for line in text.splitlines():
                        if is_math_text(line):
                            parser.parse(line)
                except ValueError:
                    self.error.setText("Check the expression inside $…$, or turn off math rendering.")
                    return
            updated.update(text=text, font_size=self.size.value(), rotation=self.rotation.value(),
                           font_family=self.family.currentData(), bold=self.bold.isChecked(),
                           italic=self.italic.isChecked(), alignment=self.alignment.currentData(),
                           background=self.background.color(), parse_math=self.math.isChecked())
        else:
            updated.update(value=self.value.value(), label=self.label.text().strip(),
                           style=self.line_style.currentData())
        self.result_annotation = updated
        self.accept()


class AnnotationListDialog(QDialog):
    def __init__(self, graph, edit, remove, parent=None):
        super().__init__(parent)
        self.graph, self.edit, self.remove = graph, edit, remove
        self.setWindowTitle("Chart annotations")
        self.resize(420, 350)
        layout = QVBoxLayout(self)
        hint = QLabel("Select an annotation below. On the chart, double-click a note to edit it or drag it to move it.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.items = QListWidget()
        self.items.setAccessibleName("Chart annotations")
        self.items.itemActivated.connect(self._edit_selected)
        layout.addWidget(self.items, 1)
        row = QHBoxLayout()
        self.edit_button = QPushButton("Edit…")
        self.edit_button.clicked.connect(self._edit_selected)
        row.addWidget(self.edit_button)
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self._remove_selected)
        row.addWidget(self.remove_button)
        row.addStretch()
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        row.addWidget(close)
        layout.addLayout(row)
        self.items.currentRowChanged.connect(self._update_buttons)
        self._populate()
        finish_dialog(self, scroll_body=False)

    def _populate(self):
        row = max(0, self.items.currentRow())
        self.items.clear()
        self.annotations = [ann for ann in self.graph.annotations if ann.get("type") != "band"]
        for ann in self.annotations:
            label = ann.get("text") or ann.get("label")
            if not label and ann.get("type") == "ref_line":
                axis = "Y" if ann.get("orientation") == "h" else "X"
                label = f"{axis} reference line at {ann.get('value', 0):g}"
            if not label:
                label = "Annotation"
            item = QListWidgetItem(str(label).replace("\n", " "))
            self.items.addItem(item)
        self.items.setCurrentRow(min(row, self.items.count() - 1))
        self._update_buttons()

    def _selected(self):
        index = self.items.currentRow()
        return self.annotations[index] if 0 <= index < len(self.annotations) else None

    def _update_buttons(self):
        chosen = self._selected()
        self.edit_button.setEnabled(chosen is not None and chosen.get("type") in {"text", "ref_line"})
        self.remove_button.setEnabled(chosen is not None)

    def _edit_selected(self):
        chosen = self._selected()
        if chosen is not None and self.edit_button.isEnabled():
            self.edit(chosen)
            self._populate()

    def _remove_selected(self):
        chosen = self._selected()
        if chosen is not None:
            self.remove(chosen)
            self._populate()
