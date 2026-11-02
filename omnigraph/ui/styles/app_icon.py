"""
Application icon generation and Windows taskbar integration for Graffy.
Ensures Graffy displays a custom scientific graphing icon on the Windows taskbar
instead of the generic python.exe logo.
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QPen, QBrush, 
    QLinearGradient, QRadialGradient, QPainterPath
)
from PyQt6.QtCore import Qt, QPointF, QRectF

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


STYLES_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(STYLES_DIR, "icons")
PROJECT_ROOT = os.path.abspath(os.path.join(STYLES_DIR, "..", "..", ".."))

ICO_PATH = os.path.join(ICONS_DIR, "graffy.ico")
PNG_PATH = os.path.join(ICONS_DIR, "graffy.png")
ICNS_PATH = os.path.join(ICONS_DIR, "graffy.icns")
# Compatibility aliases; icons now have a single canonical location.
ROOT_ICO_PATH = ICO_PATH
ROOT_PNG_PATH = PNG_PATH
ROOT_ICNS_PATH = ICNS_PATH


def setup_windows_app_id(app_id: str = "kyle.graffy.scientific.graphing.1.0"):
    """
    Sets the Windows Application User Model ID (AppUserModelID).
    This tells Windows to treat Graffy as an independent application on the taskbar
    rather than grouping it under python.exe, allowing its custom window icon to appear.
    """
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception as e:
            print(f"Notice: Could not set AppUserModelID: {e}")


def render_graffy_pixmap(size: int = 512) -> QPixmap:
    """
    Renders the modern Graffy application icon at any specified dimension.
    Features:
    - High-tech rounded squircle with ambient navy/indigo gradient
    - Glowing coordinate grid and primary axes with tick marks
    - Smooth, vibrant scientific resonance curve with gradient area fill
    - Glowing experimental data scatter nodes and apex target sparkle
    """
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    s = size / 512.0

    # 1. Subtle drop shadow behind container
    shadow_rect = QRectF(20 * s, 24 * s, 472 * s, 472 * s)
    p.setBrush(QColor(0, 0, 0, 80))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(shadow_rect, 102 * s, 102 * s)

    # 2. Outer App Container (Squircle)
    body_rect = QRectF(18 * s, 18 * s, 476 * s, 476 * s)

    bg_grad = QLinearGradient(18 * s, 18 * s, 494 * s, 494 * s)
    bg_grad.setColorAt(0.0, QColor("#0f172a"))   # Deep slate navy
    bg_grad.setColorAt(0.42, QColor("#1e1b4b"))  # Tech indigo
    bg_grad.setColorAt(1.0, QColor("#080d1a"))   # Midnight abyss
    p.setBrush(QBrush(bg_grad))

    border_pen = QPen(QColor(56, 189, 248, 90), 3.0 * s)
    p.setPen(border_pen)
    p.drawRoundedRect(body_rect, 102 * s, 102 * s)

    # Clip subsequent graph elements inside the rounded container
    clip_path = QPainterPath()
    clip_path.addRoundedRect(body_rect, 102 * s, 102 * s)
    p.setClipPath(clip_path)

    # 3. Ambient radial glow radiating from the peak
    radial_glow = QRadialGradient(265 * s, 150 * s, 280 * s)
    radial_glow.setColorAt(0.0, QColor(14, 165, 233, 60))
    radial_glow.setColorAt(0.45, QColor(99, 102, 241, 30))
    radial_glow.setColorAt(1.0, QColor(0, 0, 0, 0))
    p.setBrush(QBrush(radial_glow))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRect(body_rect)

    # 4. Subtle Coordinate Grid
    grid_pen = QPen(QColor(148, 163, 184, 38), 1.5 * s)
    grid_pen.setStyle(Qt.PenStyle.DashLine)
    p.setPen(grid_pen)
    for gx in [165, 255, 345, 425]:
        p.drawLine(QPointF(gx * s, 90 * s), QPointF(gx * s, 415 * s))
    for gy in [155, 245, 335]:
        p.drawLine(QPointF(85 * s, gy * s), QPointF(435 * s, gy * s))

    # 5. Primary Coordinate Axes with Ticks
    axis_pen = QPen(QColor(125, 211, 252, 180), 3.5 * s)
    axis_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(axis_pen)
    p.drawLine(QPointF(85 * s, 415 * s), QPointF(435 * s, 415 * s))
    p.drawLine(QPointF(85 * s, 415 * s), QPointF(85 * s, 90 * s))

    # Ticks
    for tx in [165, 255, 345, 425]:
        p.drawLine(QPointF(tx * s, 415 * s), QPointF(tx * s, 424 * s))
    for ty in [155, 245, 335]:
        p.drawLine(QPointF(85 * s, ty * s), QPointF(76 * s, ty * s))

    # 6. Smooth Scientific Curve Path
    curve = QPainterPath()
    curve.moveTo(85 * s, 395 * s)
    curve.cubicTo(125 * s, 390 * s, 160 * s, 350 * s, 190 * s, 300 * s)
    curve.cubicTo(220 * s, 240 * s, 235 * s, 125 * s, 270 * s, 125 * s)  # Apex peak
    curve.cubicTo(305 * s, 125 * s, 320 * s, 265 * s, 355 * s, 265 * s)  # Dip
    curve.cubicTo(375 * s, 265 * s, 390 * s, 190 * s, 415 * s, 190 * s)  # Shoulder
    curve.cubicTo(425 * s, 190 * s, 432 * s, 215 * s, 435 * s, 230 * s)

    # 7. Shaded Area Under Curve
    fill_path = QPainterPath(curve)
    fill_path.lineTo(435 * s, 415 * s)
    fill_path.lineTo(85 * s, 415 * s)
    fill_path.closeSubpath()

    area_grad = QLinearGradient(270 * s, 125 * s, 270 * s, 415 * s)
    area_grad.setColorAt(0.0, QColor(6, 182, 212, 120))  # Vibrant Cyan
    area_grad.setColorAt(0.5, QColor(59, 130, 246, 60))   # Royal Blue
    area_grad.setColorAt(1.0, QColor(15, 23, 42, 0))      # Fade to base
    p.setBrush(QBrush(area_grad))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPath(fill_path)

    # 8. Outer Glows
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(6, 182, 212, 70), 18 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawPath(curve)
    p.setPen(QPen(QColor(56, 189, 248, 140), 9 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawPath(curve)

    # 9. Core Curve with Spectral Gradient
    curve_grad = QLinearGradient(85 * s, 395 * s, 435 * s, 190 * s)
    curve_grad.setColorAt(0.0, QColor("#38bdf8"))
    curve_grad.setColorAt(0.35, QColor("#00f0ff"))
    curve_grad.setColorAt(0.55, QColor("#3b82f6"))
    curve_grad.setColorAt(0.80, QColor("#8b5cf6"))
    curve_grad.setColorAt(1.0, QColor("#f43f5e"))
    p.setPen(QPen(QBrush(curve_grad), 5.5 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawPath(curve)

    # 10. Data Scatter Nodes
    nodes = [
        QPointF(190 * s, 300 * s),
        QPointF(270 * s, 125 * s),  # Apex
        QPointF(355 * s, 265 * s),  # Dip
        QPointF(415 * s, 190 * s),  # Shoulder
    ]
    for i, pt in enumerate(nodes):
        halo_r = 15 * s if i == 1 else 11 * s
        p.setBrush(QColor(0, 240, 255, 70))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(pt, halo_r, halo_r)

        ring_r = 8.5 * s if i == 1 else 6.8 * s
        p.setBrush(QColor("#0f172a"))
        p.setPen(QPen(QColor("#38bdf8"), 2.6 * s))
        p.drawEllipse(pt, ring_r, ring_r)

        core_r = 4.2 * s if i == 1 else 3.2 * s
        p.setBrush(QColor("#ffffff"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(pt, core_r, core_r)

    # Apex Diamond Sparkle
    apex = nodes[1]
    p.setPen(QPen(QColor(255, 255, 255, 240), 2.0 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(apex.x() - 13 * s, apex.y()), QPointF(apex.x() + 13 * s, apex.y()))
    p.drawLine(QPointF(apex.x(), apex.y() - 13 * s), QPointF(apex.x(), apex.y() + 13 * s))

    p.end()
    return pix


def ensure_icon_files(force_regenerate: bool = False):
    """Generates PNG and ICO files if they do not already exist."""
    os.makedirs(ICONS_DIR, exist_ok=True)

    needs_gen = force_regenerate or not os.path.exists(PNG_PATH) or not os.path.exists(ICO_PATH) or not os.path.exists(ICNS_PATH)
    if not needs_gen:
        return

    pix512 = render_graffy_pixmap(512)
    pix512.save(PNG_PATH)

    if HAS_PIL:
        try:
            im = Image.open(PNG_PATH)
            sizes = [(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (128, 128), (256, 256)]
            im.save(ICO_PATH, format="ICO", sizes=sizes)

            # Export Apple ICNS format for macOS dock and .app bundle
            try:
                im.save(ICNS_PATH, format="ICNS")
            except Exception:
                pass
        except Exception as e:
            print(f"Warning: Failed to write multi-resolution ICO: {e}")


def get_app_icon() -> QIcon:
    """
    Returns the comprehensive QIcon for Graffy with mipmaps for all standard display scales.
    """
    ensure_icon_files()

    icon = QIcon()
    if os.path.exists(ICO_PATH):
        icon.addFile(ICO_PATH)
    elif os.path.exists(PNG_PATH):
        icon.addFile(PNG_PATH)

    # Explicitly add crisp rendered pixmaps across key taskbar resolutions
    for s in [16, 20, 24, 32, 48, 64, 128, 256]:
        icon.addPixmap(render_graffy_pixmap(s))

    return icon
