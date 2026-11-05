"""Small vector icons shared by the desktop interface; no external assets."""
from PyQt6.QtCore import Qt, QByteArray
from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication

_icon_specs = {}

PATHS = {
    "import": '<path d="M12 3v12m-4-4 4 4 4-4M4 16v5h16v-5"/>',
    "chart": '<path d="M4 3v17h17M7 15l4-5 4 3 5-8"/>',
    "legend": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M7 10h2m3 0h5M7 14h2m3 0h5"/>',
    "sheet": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M9 4v16M3 14h18"/>',
    "report": '<path d="M7 3h10l4 4v14H3V3h4M8 10h8M8 14h8M8 18h5"/>',
    "save": '<path d="M4 3h13l4 4v14H3V3h1M7 3v7h10V3M7 21v-7h10v7"/>',
    "export": '<path d="M12 16V3m-4 4 4-4 4 4M4 14v7h16v-7"/>',
    "analyze": '<path d="M3 19h18M4 16c4 0 3-12 8-12s4 12 8 12"/>',
    "undo": '<path d="M8 5 3 10l5 5M3 10h11a6 6 0 0 1 0 12"/>',
    "redo": '<path d="m16 5 5 5-5 5m5-5H10a6 6 0 0 0 0 12"/>',
    "panel": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/>',
    "edit": '<path d="m14 4 6 6M4 20l5-1L21 7l-4-4L5 15l-1 5Z"/>',
    "copy": '<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>',
    "zoom": '<circle cx="10" cy="10" r="7"/><path d="m15 15 6 6M7 10h6m-3-3v6"/>',
    "folder": '<path d="M3 6h7l2 3h9v11H3V6Z"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 1 1 4 3c-1 1-1 1-1 3m0 3h.01"/>',
    "more": '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
}

def icon(name, color=None):
    app=QApplication.instance()
    requested_color=color
    color=color or ("#d8def0" if getattr(app,"is_dark_theme",False) else "#526078")
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{PATHS[name]}</svg>'
    result=QIcon()
    for size in (16,20,24,32,40,48):
        pix=QPixmap(size,size)
        pix.fill(Qt.GlobalColor.transparent)
        painter=QPainter(pix)
        QSvgRenderer(QByteArray(svg.encode())).render(painter)
        painter.end()
        result.addPixmap(pix)
    _icon_specs[result.cacheKey()]=(name,requested_color)
    return result


def refresh_icons(root):
    """Regenerate named icons when the app palette changes."""
    from PyQt6.QtGui import QAction
    from PyQt6.QtWidgets import QAbstractButton, QTabWidget
    for widget in root.findChildren(QAbstractButton)+root.findChildren(QAction):
        spec=_icon_specs.get(widget.icon().cacheKey())
        if spec:
            widget.setIcon(icon(*spec))
    for tabs in root.findChildren(QTabWidget):
        for i in range(tabs.count()):
            spec=_icon_specs.get(tabs.tabIcon(i).cacheKey())
            if spec:
                tabs.setTabIcon(i,icon(*spec))
