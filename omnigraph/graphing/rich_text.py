"""Preserve clipboard text styling and draw formatted notes as vector paths."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QPainterPath, QTextCharFormat, QTextCursor, QTextDocument,
    QTextFormat,
)
from matplotlib.colors import to_rgba, to_hex
from matplotlib.path import Path
from matplotlib.text import Text
from matplotlib.transforms import Affine2D, Bbox


ALIGNMENT = {"left": Qt.AlignmentFlag.AlignLeft, "center": Qt.AlignmentFlag.AlignHCenter,
             "right": Qt.AlignmentFlag.AlignRight}
SCRIPT = {"sub": QTextCharFormat.VerticalAlignment.AlignSubScript,
          "super": QTextCharFormat.VerticalAlignment.AlignSuperScript}


def formatted_runs(document):
    """Convert clipboard text to plain text plus a small set of supported styles."""
    block = document.begin()
    runs = []
    first = True
    while block.isValid():
        if not first:
            runs.append({"text": "\n"})
        first = False
        iterator = block.begin()
        while not iterator.atEnd():
            fragment = iterator.fragment()
            style = fragment.charFormat()
            text = fragment.text().replace("\ufffc", "")
            if text:
                run = {"text": text}
                for key, prop, value in (
                    ("bold", QTextFormat.Property.FontWeight, style.fontWeight() >= QFont.Weight.Bold),
                    ("italic", QTextFormat.Property.FontItalic, style.fontItalic()),
                    ("underline", QTextFormat.Property.TextUnderlineStyle, style.fontUnderline()),
                ):
                    if style.hasProperty(prop):
                        run[key] = value
                color = style.foreground().color()
                if style.hasProperty(QTextFormat.Property.ForegroundBrush) and color.isValid():
                    run["color"] = color.name()
                for key, script in SCRIPT.items():
                    if style.verticalAlignment() == script:
                        run["script"] = key
                runs.append(run)
            iterator += 1
        block = block.next()
    return runs


def insert_runs(cursor, runs, *, default_color=None):
    for run in runs:
        style = QTextCharFormat()
        if "bold" in run:
            style.setFontWeight(QFont.Weight.Bold if run["bold"] else QFont.Weight.Normal)
        if "italic" in run:
            style.setFontItalic(run["italic"])
        if "underline" in run:
            style.setFontUnderline(run["underline"])
        if run.get("script") in SCRIPT:
            style.setVerticalAlignment(SCRIPT[run["script"]])
        color = QColor(run.get("color") or default_color or "")
        if color.isValid():
            style.setForeground(QBrush(color))
        cursor.insertText(run["text"], style)


class RichNoteArtist(Text):
    """A positioned, rotatable Qt text layout exported through Matplotlib."""

    def __init__(self, *args, runs, **kwargs):
        self.runs = runs
        self._rich_layout = None
        super().__init__(*args, **kwargs)

    def _layout(self, renderer):
        size = max(1, round(renderer.points_to_pixels(self.get_fontsize())))
        color = to_hex(self.get_color())
        family = self.get_fontfamily()[0]
        alignment = self.get_ha()
        weight = self.get_fontweight()
        style = self.get_fontstyle()
        key = (size, color, family, alignment, weight, style)
        if self._rich_layout is not None and self._rich_layout[0] == key:
            return self._rich_layout[1:]

        font = QFont({"sans-serif": "DejaVu Sans", "serif": "DejaVu Serif",
                      "monospace": "DejaVu Sans Mono"}.get(family, family))
        font.setPixelSize(size)
        font.setBold(weight == "bold")
        font.setItalic(style == "italic")
        document = QTextDocument()
        document.setDocumentMargin(0)
        document.setDefaultFont(font)
        option = document.defaultTextOption()
        option.setAlignment(ALIGNMENT[alignment])
        document.setDefaultTextOption(option)
        insert_runs(QTextCursor(document), self.runs, default_color=color)
        document.adjustSize()
        document.setTextWidth(document.idealWidth() + 1)
        bounds = document.size()

        paths = []
        block = document.begin()
        while block.isValid():
            layout = block.layout()
            origin = layout.position()
            iterator = block.begin()
            while not iterator.atEnd():
                fragment = iterator.fragment()
                painter_path = QPainterPath()
                for run in layout.glyphRuns(fragment.position() - block.position(), fragment.length()):
                    raw = run.rawFont()
                    for glyph, position in zip(run.glyphIndexes(), run.positions()):
                        glyph_path = raw.pathForGlyph(glyph)
                        glyph_path.translate(origin + position)
                        painter_path.addPath(glyph_path)
                    if run.underline() and run.positions():
                        rect = run.boundingRect().translated(origin)
                        baseline = origin.y() + run.positions()[0].y()
                        painter_path.addRect(rect.left(), baseline + raw.underlinePosition(),
                                             rect.width(), max(1, raw.lineThickness()))
                mpl_path = _matplotlib_path(painter_path)
                if mpl_path is not None:
                    paths.append((mpl_path, fragment.charFormat().foreground().color().name()))
                iterator += 1
            block = block.next()
        self._rich_layout = key, bounds.width(), bounds.height(), paths
        return self._rich_layout[1:]

    def _geometry(self, renderer):
        width, height, paths = self._layout(renderer)
        x, y = self.get_transform().transform(self.get_position())
        horizontal_anchor = {"left": 0, "center": -width / 2, "right": -width}[self.get_ha()]
        transform = (Affine2D().scale(1, -1).translate(horizontal_anchor, height * 0.8)
                     .rotate_deg(self.get_rotation()).translate(x, y))
        return width, height, paths, transform

    def get_window_extent(self, renderer=None, dpi=None):
        renderer = renderer or self.get_figure()._get_renderer()
        width, height, _, transform = self._geometry(renderer)
        corners = transform.transform(((0, 0), (width, 0), (0, height), (width, height)))
        return Bbox.from_extents(
            corners[:, 0].min(), corners[:, 1].min(), corners[:, 0].max(), corners[:, 1].max(),
        )

    def draw(self, renderer):
        if not self.get_visible():
            return
        width, height, paths, transform = self._geometry(renderer)
        gc = renderer.new_gc()
        self._set_gc_clip(gc)
        gc.set_linewidth(0)
        box = self.get_bbox_patch()
        if box is not None:
            box_transform = Affine2D().scale(width + 6, height + 6).translate(-3, -3)
            renderer.draw_path(gc, Path.unit_rectangle(), box_transform + transform, box.get_facecolor())
        for path, color in paths:
            renderer.draw_path(gc, path, transform, to_rgba(color))
        gc.restore()


def _matplotlib_path(qpath):
    vertices, codes = [], []
    for index in range(qpath.elementCount()):
        item = qpath.elementAt(index)
        vertices.append((item.x, item.y))
        codes.append(Path.MOVETO if item.isMoveTo() else Path.LINETO if item.isLineTo() else Path.CURVE4)
    return Path(vertices, codes) if codes else None
