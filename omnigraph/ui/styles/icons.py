"""
Icon generator and registry for Graffy UI styles.
Generates crisp, high-contrast UI icons (e.g. tab close buttons) on-demand.
"""

import os
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen
from PyQt6.QtCore import Qt


ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")


def ensure_style_icons() -> dict:
    """Ensures that UI icons exist on disk and returns their normalized file paths."""
    os.makedirs(ICONS_DIR, exist_ok=True)

    icons = {
        "close_light": os.path.join(ICONS_DIR, "close_light.png"),
        "close_hover": os.path.join(ICONS_DIR, "close_hover.png"),
        "close_dark": os.path.join(ICONS_DIR, "close_dark.png"),
    }

    # Generate close_light.png (dark slate cross for light theme tabs)
    if not os.path.exists(icons["close_light"]):
        pix = QPixmap(16, 16)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#334155"), 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawLine(4, 4, 12, 12)
        p.drawLine(12, 4, 4, 12)
        p.end()
        pix.save(icons["close_light"])

    # Generate close_hover.png (red circle with white cross on hover)
    if not os.path.exists(icons["close_hover"]):
        pix_h = QPixmap(16, 16)
        pix_h.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix_h)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#ef4444"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(1, 1, 14, 14, 3, 3)
        pen_w = QPen(QColor("#ffffff"), 1.8)
        pen_w.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen_w)
        p.drawLine(4, 4, 12, 12)
        p.drawLine(12, 4, 4, 12)
        p.end()
        pix_h.save(icons["close_hover"])

    # Generate close_dark.png (soft lavender cross for dark theme tabs)
    if not os.path.exists(icons["close_dark"]):
        pix_d = QPixmap(16, 16)
        pix_d.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix_d)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen_d = QPen(QColor("#cdd6f4"), 2.0)
        pen_d.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen_d)
        p.drawLine(4, 4, 12, 12)
        p.drawLine(12, 4, 4, 12)
        p.end()
        pix_d.save(icons["close_dark"])

    # SVG indicator glyphs stay crisp at fractional and high display scaling.
    glyphs = {
        "check": '<path d="m4 10 4 4 8-9"/>',
        "mixed": '<path d="M5 10h10"/>',
        "radio": '<circle cx="10" cy="10" r="4" fill="white" stroke="none"/>',
    }
    for name, shape in glyphs.items():
        path=os.path.join(ICONS_DIR, name+".svg")
        if not os.path.exists(path):
            with open(path,"w",encoding="utf-8") as stream:
                stream.write('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="white" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">'+shape+'</svg>')
        icons[name]=path

    for tone, color in (("light","#334155"),("dark","#e6ebf5")):
        for direction, shape in (("down","m3 5 5 5 5-5"),("up","m3 10 5-5 5 5")):
            name="arrow_"+direction+"_"+tone
            path=os.path.join(ICONS_DIR,name+".svg")
            if not os.path.exists(path):
                with open(path,"w",encoding="utf-8") as stream:
                    stream.write('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16"><path d="'+shape+'" fill="none" stroke="'+color+'" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>')
            icons[name]=path

    # Return normalized paths with forward slashes for QSS url()
    return {k: v.replace("\\", "/") for k, v in icons.items()}
