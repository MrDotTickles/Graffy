"""Compact chart note editor and controls for chart overlays."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QActionGroup, QTextDocument
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu,
    QPushButton, QTextEdit, QToolButton, QVBoxLayout, QWidgetAction,
)

from omnigraph.core.project import CurveModel
from omnigraph.graphing.rich_text import formatted_runs, insert_runs
from omnigraph.ui.color_field import ColorField
from omnigraph.ui.dialogs.dialog_layout import finish_dialog


class NoteTextEdit(QTextEdit):
    def insertFromMimeData(self, source):
        if not source.hasHtml():
            self.insertPlainText(source.text())
            return
        document = QTextDocument()
        document.setHtml(source.html())
        runs = formatted_runs(document)
        if not runs:
            self.insertPlainText(source.text())
            return
        cursor = self.textCursor()
        cursor.beginEditBlock()
        insert_runs(cursor, runs)
        cursor.endEditBlock()
        self.setTextCursor(cursor)


class AnnotationDialog(QDialog):
    def __init__(self, annotation, parent=None, *, adding=False):
        super().__init__(parent)
        self.result_annotation = None
        self.original = annotation
        self.kind = annotation["type"]
        self.is_text = self.kind == "text"
        name = {"text": "text note", "ref_line": "reference line", "fit": "best-fit line",
                "band": "band", "bracket": "significance bracket",
                "significance": "significance bracket"}[self.kind]
        self.setWindowTitle(f"{'Add' if adding else 'Edit'} {name}")
        self.resize(410, 236 if self.is_text else 280)
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        self.color = ColorField(annotation.get("color", "auto"),
                                title="Text color" if self.is_text else "Color")
        if self.is_text:
            self._build_text_editor(layout, annotation)
        else:
            self._build_overlay_form(layout, annotation)

        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.hide()
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.save_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.save_button.setText(f"Add {name}" if adding else "Save")
        self.save_button.setProperty("role", "primary")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        finish_dialog(self, scroll_body=not self.is_text)
        if self.is_text:
            self.text.textChanged.connect(self._update_save)
            self._update_save()
            self.text.setFocus()

    def _build_text_editor(self, layout, annotation):
        self.text = NoteTextEdit()
        self.text.setPlaceholderText("Type or paste text")
        self.text.setAccessibleName("Note text")
        self.text.setMinimumHeight(58)
        self.text.setMaximumHeight(96)
        self.text.setTabChangesFocus(True)
        if annotation.get("runs"):
            insert_runs(self.text.textCursor(), annotation["runs"])
        else:
            self.text.setPlainText(annotation.get("text", ""))

        self.size = self._number(4, 200, annotation.get("font_size", 10), decimals=1, suffix=" pt")
        self.size.setAccessibleName("Font size")
        self.size.setToolTip("Font size")
        angle = float(annotation.get("rotation", 0))
        self.rotation = self._number(-360, 360, (angle + 180) % 360 - 180, decimals=1, suffix="°")
        self.rotation.setAccessibleName("Rotation")
        self.rotation.setToolTip("Rotation in degrees. Positive values turn counterclockwise.")
        self.bold = self._text_toggle("B", "Bold", annotation.get("bold", False))
        self.italic = self._text_toggle("I", "Italic", annotation.get("italic", False))
        bold_font = self.bold.font()
        bold_font.setBold(True)
        self.bold.setFont(bold_font)
        italic_font = self.italic.font()
        italic_font.setItalic(True)
        self.italic.setFont(italic_font)

        options = QToolButton()
        options.setText("Style")
        options.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(options)
        self.family = self._choices(menu.addMenu("Typeface"), (
            ("Theme default", ""), ("Sans serif", "sans-serif"), ("Serif", "serif"),
            ("Monospace", "monospace"),
        ), annotation.get("font_family", ""))
        self.alignment = self._choices(menu.addMenu("Alignment"), (
            ("Left", "left"), ("Center", "center"), ("Right", "right"),
        ), annotation.get("alignment", "left"))
        self.background = ColorField(annotation.get("background", "none"), title="Note background",
                                     allow_transparent=True)
        background_menu = menu.addMenu("Background")
        background = QWidgetAction(background_menu)
        background.setDefaultWidget(self.background)
        background_menu.addAction(background)
        self.math = menu.addAction("Render math inside $…$")
        self.math.setToolTip("Applies to plain text. Pasted formatting keeps its original notation.")
        self.math.setCheckable(True)
        self.math.setChecked(annotation.get("parse_math", "text" in annotation))
        options.setMenu(menu)

        tools = QGridLayout()
        tools.setContentsMargins(0, 0, 0, 0)
        tools.setSpacing(4)
        for column, widget in enumerate((self.bold, self.italic, self.size, self.rotation, options)):
            tools.addWidget(widget, 0, column)
        tools.setColumnStretch(5, 1)
        tools.addWidget(self.color, 1, 0, 1, 6)
        layout.addLayout(tools)
        layout.addWidget(self.text)

    def _build_overlay_form(self, layout, annotation):
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        if self.kind == "ref_line":
            self.value = self._coordinate(annotation.get("value", 0))
            form.addRow("Y value" if annotation.get("orientation") == "h" else "X value", self.value)
        if self.kind in {"fit", "band", "ref_line"}:
            self.label = QLineEdit(annotation.get("label", ""))
            self.label.setPlaceholderText("Optional")
            form.addRow("Legend label", self.label)
        if self.kind in {"fit", "ref_line"}:
            self.line_style = QComboBox()
            for label, code in (("Solid", "-"), ("Dashed", "--"), ("Dotted", ":"), ("Dash-dot", "-.")):
                self.line_style.addItem(label, code)
            self.line_style.setCurrentIndex(max(0, self.line_style.findData(annotation.get("style", "--"))))
            form.addRow("Line style", self.line_style)
        if self.kind != "band":
            self.width = self._number(0.1, 20, annotation.get("line_width", 1.2), decimals=1, suffix=" pt")
            form.addRow("Line width", self.width)
        if self.kind in {"fit", "band"}:
            self.opacity = self._number(0, 100, annotation.get("alpha", 1) * 100, decimals=0, suffix="%")
            form.addRow("Opacity", self.opacity)
        if self.kind in {"bracket", "significance"}:
            self.label = QLineEdit(annotation.get("text", "***"))
            form.addRow("Text", self.label)
            for key, caption, default in (("x1", "Left X", 1), ("x2", "Right X", 2),
                                          ("y", "Y position", 1), ("h", "Height", 0.5)):
                widget = self._coordinate(annotation.get(key, default))
                setattr(self, key, widget)
                form.addRow(caption, widget)
            self.size = self._number(4, 200, annotation.get("font_size", 11), decimals=1, suffix=" pt")
            form.addRow("Font size", self.size)
        form.addRow("Color", self.color)
        layout.addLayout(form)

    @staticmethod
    def _choices(menu, choices, value):
        group = QActionGroup(menu)
        group.setExclusive(True)
        for label, key in choices:
            action = menu.addAction(label)
            action.setData(key)
            action.setCheckable(True)
            group.addAction(action)
            action.setChecked(key == value)
        if group.checkedAction() is None:
            group.actions()[0].setChecked(True)
        return group

    @staticmethod
    def _text_toggle(label, name, checked):
        button = QToolButton()
        button.setText(label)
        button.setToolTip(name)
        button.setAccessibleName(name)
        button.setCheckable(True)
        button.setChecked(checked)
        return button

    @staticmethod
    def _number(low, high, value, *, decimals, suffix=""):
        field = QDoubleSpinBox()
        field.setRange(low, high)
        field.setDecimals(decimals)
        field.setSuffix(suffix)
        field.setValue(value)
        return field

    def _coordinate(self, value):
        return self._number(-1e15, 1e15, value, decimals=10)

    def _update_save(self):
        self.save_button.setEnabled(bool(self.text.toPlainText().strip()))
        self.error.hide()

    def _save(self):
        updated = {**self.original, "color": self.color.color()}
        if self.is_text:
            text = self.text.toPlainText().strip()
            if not text:
                return
            runs = formatted_runs(self.text.document())
            rich = any(set(run) - {"text"} for run in runs)
            if not rich and self.math.isChecked():
                from matplotlib.cbook import is_math_text
                from matplotlib.mathtext import MathTextParser

                parser = MathTextParser("path")
                try:
                    for line in text.splitlines():
                        if is_math_text(line):
                            parser.parse(line)
                except ValueError:
                    self.error.setText("Check the expression inside $…$, or turn off math rendering in Style.")
                    self.error.show()
                    self.adjustSize()
                    return
            updated.update(text=text, font_size=self.size.value(), rotation=self.rotation.value(),
                           font_family=self.family.checkedAction().data(), bold=self.bold.isChecked(),
                           italic=self.italic.isChecked(), alignment=self.alignment.checkedAction().data(),
                           background=self.background.color(), parse_math=self.math.isChecked())
            if rich:
                updated["runs"] = runs
            else:
                updated.pop("runs", None)
        else:
            if self.kind in {"fit", "band", "ref_line"}:
                updated["label"] = self.label.text().strip()
            if self.kind in {"fit", "ref_line"}:
                updated["style"] = self.line_style.currentData()
            if self.kind != "band":
                updated["line_width"] = self.width.value()
            if self.kind == "ref_line":
                updated["value"] = self.value.value()
            if self.kind in {"fit", "band"}:
                updated["alpha"] = self.opacity.value() / 100
            if self.kind in {"bracket", "significance"}:
                updated.update(text=self.label.text().strip(), font_size=self.size.value())
                updated.update({key: getattr(self, key).value() for key in ("x1", "x2", "y", "h")})
        self.result_annotation = updated
        self.accept()


class AnnotationListDialog(QDialog):
    def __init__(self, graph, edit, remove, parent=None, *, toggle=None, analysis=False):
        super().__init__(parent)
        self.graph, self.edit, self.remove = graph, edit, remove
        self.toggle, self.analysis = toggle, analysis
        self.setWindowTitle("Analysis overlays" if analysis else "Chart annotations")
        self.resize(420, 350)
        layout = QVBoxLayout(self)
        hint = QLabel("Check an item to show it. Select an item to edit its appearance." if analysis
                      else "On the chart, select a text box to move, resize, or rotate it. Double-click to edit.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.items = QListWidget()
        self.items.setAccessibleName("Chart annotations")
        self.items.itemActivated.connect(self._edit_selected)
        self.items.itemChanged.connect(self._toggle_selected)
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
        self.items.blockSignals(True)
        self.items.clear()
        types = {"band", "bracket", "significance"}
        self.annotations = [ann for ann in self.graph.annotations if (ann.get("type") in types) == self.analysis]
        if self.analysis:
            self.annotations = [c for c in self.graph.curves if c.is_fit_curve] + self.annotations
        fits = {c.id: c.label or "Best-fit line" for c in self.graph.curves if c.is_fit_curve}
        for ann in self.annotations:
            if isinstance(ann, CurveModel):
                label, visible = ann.label or "Best-fit line", ann.visible
            else:
                label = ann.get("text") or ann.get("label")
                if ann.get("type") == "ref_line" and not label:
                    axis = "Y" if ann.get("orientation") == "h" else "X"
                    label = f"{axis} reference line at {ann.get('value', 0):g}"
                elif ann.get("type") == "band":
                    label = label or "Confidence band"
                    if ann.get("fit_curve_id") in fits:
                        label = f"{label} · {fits[ann['fit_curve_id']]}"
                elif ann.get("type") in {"bracket", "significance"}:
                    label = f"Significance bracket · {label or ''}".rstrip(" ·")
                visible = ann.get("visible", True)
            item = QListWidgetItem(str(label or "Annotation").replace("\n", " "))
            if self.toggle:
                item.setCheckState(Qt.CheckState.Checked if visible else Qt.CheckState.Unchecked)
            self.items.addItem(item)
        self.items.blockSignals(False)
        self.items.setCurrentRow(min(row, self.items.count() - 1))
        self._update_buttons()

    def _toggle_selected(self, item):
        if self.toggle is not None:
            self.toggle(self.annotations[self.items.row(item)], item.checkState() == Qt.CheckState.Checked)

    def _selected(self):
        index = self.items.currentRow()
        return self.annotations[index] if 0 <= index < len(self.annotations) else None

    def _update_buttons(self):
        chosen = self._selected()
        self.edit_button.setEnabled(isinstance(chosen, CurveModel) or (
            chosen is not None and chosen.get("type") in {"text", "ref_line", "band", "bracket", "significance"}
        ))
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
