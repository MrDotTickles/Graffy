"""Shared, accessible progressive disclosure for task dialogs."""
from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtWidgets import (
    QApplication, QBoxLayout, QDialogButtonBox, QLayout, QScrollArea, QToolButton, QVBoxLayout, QWidget,
)


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


class _ResponsiveFooter(QObject):
    def __init__(self, dialog, footer):
        super().__init__(dialog)
        self.footer = footer
        dialog.installEventFilter(self)

    def eventFilter(self, dialog, event):
        if event.type() in {QEvent.Type.Show, QEvent.Type.Resize, QEvent.Type.LayoutRequest}:
            margins = dialog.layout().contentsMargins()
            available = dialog.width() - margins.left() - margins.right()
            footer = self.footer
            self._adapt_button_box(footer, available)
            if isinstance(footer, QBoxLayout):
                widths = []
                for index in range(footer.count()):
                    item = footer.itemAt(index)
                    if item.isEmpty():
                        continue
                    widget = item.widget()
                    if isinstance(widget, QDialogButtonBox):
                        self._adapt_button_box(widget, available)
                    widths.append(item.minimumSize().width())
                required = sum(widths) + max(0, len(widths) - 1) * max(0, footer.spacing())
                direction = (QBoxLayout.Direction.TopToBottom if required > available
                             else QBoxLayout.Direction.LeftToRight)
                if footer.direction() != direction:
                    footer.setDirection(direction)
        return super().eventFilter(dialog, event)

    @staticmethod
    def _adapt_button_box(widget, available):
        if not isinstance(widget, QDialogButtonBox):
            return
        buttons = [button for button in widget.buttons() if not button.isHidden()]
        width = sum(max(button.minimumWidth(), button.minimumSizeHint().width()) for button in buttons)
        width += max(0, len(buttons) - 1) * max(0, widget.layout().spacing())
        orientation = Qt.Orientation.Vertical if width > available else Qt.Orientation.Horizontal
        if widget.orientation() != orientation:
            widget.setOrientation(orientation)


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
    footer = root.itemAt(root.count() - 1) if root.count() else None
    if footer:
        control = footer.widget() or footer.layout()
        if isinstance(control, (QDialogButtonBox, QBoxLayout)):
            dialog._responsive_footer = _ResponsiveFooter(dialog, control)
