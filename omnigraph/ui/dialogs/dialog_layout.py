"""Shared, accessible progressive disclosure for task dialogs."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QScrollArea, QVBoxLayout, QWidget, QToolButton, QLayout


def fold_section(group, title):
    """Collapse existing controls without recreating or resetting their values."""
    button = QToolButton()
    button.setText(title)
    button.setCheckable(True)
    button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    button.setArrowType(Qt.ArrowType.RightArrow)
    button.setAccessibleName(title)
    layout = group.layout()
    content = QWidget()
    content.setLayout(layout)
    outer = QVBoxLayout(group)
    outer.setContentsMargins(8, 8, 8, 8)
    outer.addWidget(button)
    outer.addWidget(content)
    group.setTitle("")
    group.setStyleSheet(group.styleSheet() + "QGroupBox { margin-top: 0px; padding-top: 0px; padding-bottom: 0px; }")
    content.hide()
    group.setMaximumHeight(button.sizeHint().height() + 32)
    def toggle(checked):
        content.setVisible(checked)
        group.setMaximumHeight(16777215 if checked else button.sizeHint().height() + 32)
        button.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
    button.toggled.connect(toggle)
    return button, content


def finish_dialog(dialog, scroll_body=True):
    """Keep the final action row visible while the body scrolls on small screens."""
    root = dialog.layout()
    if scroll_body:
        footer = root.takeAt(root.count() - 1)
        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(0, 0, 4, 0)
        def move_item(item, target):
            if item.widget():
                target.addWidget(item.widget())
            elif item.layout():
                nested = item.layout()
                nested.setParent(None)
                target.addLayout(nested)
            else:
                target.addItem(item)
        while root.count():
            move_item(root.takeAt(0), body)
        scroll = QScrollArea()
        scroll.setObjectName("DialogBodyScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setMinimumSize(0, 0)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)
        move_item(footer, root)
    root.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
    screen = dialog.screen() or QApplication.primaryScreen()
    if screen:
        available = screen.availableGeometry()
        width = min(dialog.width(), max(280, available.width() - 32))
        height = min(dialog.height(), max(240, available.height() - 48))
        dialog.setMinimumSize(min(480, width), min(320, height))
        dialog.resize(width, height)
