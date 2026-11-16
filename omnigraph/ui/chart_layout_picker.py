"""Visual chart layouts shared by the drag overlay and the keyboard picker."""

from PyQt6.QtCore import QEvent, QPointF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QSizePolicy, QToolButton, QVBoxLayout

CHART_LAYOUTS = (
    ("add", "Overlay", "Add the dropped data to this chart’s axes."),
    ("side_by_side", "Side by side", "Compare the current and dropped data on separate axes."),
    ("waterfall", "Waterfall", "Offset two or more traces vertically."),
    ("new", "New chart", "Plot the dropped data in its own chart."),
)


def _preview_icon(layout):
    pixmap = QPixmap(200, 100)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(2, 2)

    existing = QColor("#6366f1")
    incoming = QColor("#0d9488")
    frame = QColor("#7c8da8")
    shape = [(0, .78), (.19, .62), (.37, .69), (.54, .22), (.68, .46), (.84, .33), (1, .19)]

    def panel(x, width):
        painter.setPen(QPen(frame, 1.15))
        painter.drawRoundedRect(x, 4, width, 42, 4, 4)

    def trace(x, y, width, height, color, variant=False):
        painter.setPen(QPen(color, 1.9, cap=Qt.PenCapStyle.RoundCap, join=Qt.PenJoinStyle.RoundJoin))
        points = [(s, 1 - t * .8) if variant else (s, t) for s, t in shape]
        painter.drawPolyline(QPolygonF([QPointF(x + s * width, y + t * height) for s, t in points]))

    if layout == "side_by_side":
        panel(4, 43)
        panel(53, 43)
        trace(10, 12, 31, 27, existing)
        trace(59, 12, 31, 27, incoming, variant=True)
    else:
        panel(4, 92)
        if layout == "waterfall":
            for y, color in ((25, existing), (17, existing), (9, incoming)):
                trace(13, y, 74, 14, color)
        else:
            if layout == "add":
                trace(13, 9, 74, 29, existing)
            trace(13, 9, 74, 29, incoming, variant=True)
    painter.end()
    return QIcon(pixmap)


class ChartLayoutPicker(QFrame):
    selected = pyqtSignal(str)

    def __init__(self, heading, parent=None):
        super().__init__(parent)
        self.setObjectName("ChartLayoutPicker")
        self.tiles = {}
        self.active_layout = ""
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)
        title = QLabel(heading)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        root.addWidget(title)
        grid = QGridLayout()
        grid.setSpacing(6)
        for index, (mode, label, description) in enumerate(CHART_LAYOUTS):
            tile = QToolButton()
            tile.setObjectName("ChartLayoutTile")
            tile.setText(label)
            tile.setIcon(_preview_icon(mode))
            tile.setIconSize(QSize(100, 50))
            tile.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            tile.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            tile.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            tile.installEventFilter(self)
            tile.setAccessibleName(label)
            tile.setAccessibleDescription(description)
            tile.setToolTip(f"{label} · {description}")
            tile.setCursor(Qt.CursorShape.PointingHandCursor)
            tile.clicked.connect(lambda checked=False, mode=mode: self.selected.emit(mode))
            grid.addWidget(tile, index // 2, index % 2)
            self.tiles[mode] = tile
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        root.addLayout(grid)

    def preferred_size(self):
        widest_label = max(tile.fontMetrics().horizontalAdvance(tile.text()) for tile in self.tiles.values())
        return QSize(2 * max(128, widest_label + 34) + 22, self.sizeHint().height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        style = (Qt.ToolButtonStyle.ToolButtonTextUnderIcon if self.width() >= self.preferred_size().width()
                 else Qt.ToolButtonStyle.ToolButtonIconOnly)
        for tile in self.tiles.values():
            tile.setToolButtonStyle(style)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
                watched.click()
                return True
            directions = {
                Qt.Key.Key_Left: (0, -1), Qt.Key.Key_Right: (0, 1),
                Qt.Key.Key_Up: (-1, 0), Qt.Key.Key_Down: (1, 0),
            }
            if key in directions:
                tiles = list(self.tiles.values())
                row, column = divmod(tiles.index(watched), 2)
                dy, dx = directions[key]
                row, column = max(0, min(1, row + dy)), max(0, min(1, column + dx))
                tiles[2 * row + column].setFocus()
                return True
        return super().eventFilter(watched, event)

    def layout_at(self, point):
        if self.isVisible():
            for mode, tile in self.tiles.items():
                if tile.geometry().contains(point):
                    return mode
        return ""

    def highlight(self, mode):
        if mode == self.active_layout:
            return
        for key in (self.active_layout, mode):
            if key:
                tile = self.tiles[key]
                tile.setProperty("dropTarget", key == mode)
                tile.style().unpolish(tile)
                tile.style().polish(tile)
                tile.update()
        self.active_layout = mode
