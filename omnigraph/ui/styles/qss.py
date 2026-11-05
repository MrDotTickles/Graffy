"""Graffy's shared desktop design system, in light and dark palettes."""
from omnigraph.ui.styles.icons import ensure_style_icons


def _theme(dark=False):
    c = dict(bg="#f4f6fa", surface="#ffffff", inset="#f8f9fc", text="#202b40",
             muted="#536177", line="#ccd4e0", border="#8492a8", accent="#4f46e5",
             soft="#eeedff", hover="#f0f3f9", disabled="#69758a", selection="#e3e5ff")
    if dark:
        c.update(bg="#151b29",surface="#1d2535",inset="#192131",text="#e6ebf5",
                 muted="#a4b0c5",line="#465269",border="#7b89a3",accent="#b0aaff",
                 soft="#343253",hover="#2a3549",disabled="#778298",selection="#383759")
    q = """
QWidget { font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; color: @text; }
QMainWindow, QDialog { background: @bg; }
QLabel { font-weight: 400; background: transparent; }
QLabel[role="muted"] { color: @muted; }
QWidget#UpdateBanner { background: #ffefb0; border-bottom: 2px solid #986400; }
QWidget#UpdateBanner QLabel { color: #332500; font-weight: 600; }
QWidget#UpdateBanner QPushButton { background: #fff9e5; color: #332500; border: 1px solid #986400; }
QWidget#UpdateBanner QPushButton#UpdateBannerAction { background: #332500; color: #ffffff; border-color: #332500; }
QWidget#UpdateBanner QPushButton:hover { background: #ffe28a; color: #332500; }
QLabel[role="heading"] { font-size: 18px; font-weight: 700; }
QLabel[role="eyebrow"] { color: @muted; font-size: 11px; font-weight: 700; }
QMenuBar { background: @surface; padding: 3px 8px; border-bottom: 1px solid @line; }
QMenuBar::item { padding: 5px 10px; border-radius: 5px; }
QMenuBar::item:selected { background: @soft; color: @accent; }
QMenu { background: @surface; border: 1px solid @border; padding: 6px; }
QMenu::item { padding: 7px 28px 7px 20px; border-radius: 4px; }
QMenu::item:selected { background: @soft; color: @accent; }
QMenu::item:disabled { color: @disabled; }
QMenu::separator { height: 1px; background: @line; margin: 5px 8px; }
QToolBar { background: @surface; border: none; border-bottom: 1px solid @line; spacing: 4px; padding: 7px 10px; }
QToolBar::separator { background: @line; width: 1px; margin: 5px 7px; }
QToolButton, QPushButton { background: @surface; color: @text; border: 1px solid @border; border-radius: 6px; padding: 7px 11px; font-weight: 500; }
QToolButton { background: transparent; border-color: transparent; }
QToolButton:hover, QPushButton:hover { background: @hover; border-color: @border; }
QPushButton:focus, QToolButton:focus { border-color: @accent; }
QToolButton:pressed, QPushButton:pressed { background: @selection; }
QToolButton:checked { background: @soft; color: @accent; border-color: @border; }
QPushButton[role="primary"], QToolButton[role="primary"] { background: #4f46e5; border-color: #4f46e5; color: white; font-weight: 600; }
QPushButton[role="primary"]:hover, QToolButton[role="primary"]:hover { background: #4338ca; border-color: #4338ca; }
QToolButton:disabled, QPushButton:disabled { color: @disabled; background: @inset; border-color: @line; }
QToolButton::menu-button { border: none; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit { background: @surface; color: @text; border: 1px solid @border; border-radius: 5px; padding: 6px 8px; selection-background-color: @selection; selection-color: @text; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus, QPlainTextEdit:focus { border: 1px solid @accent; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled { background: @inset; color: @disabled; }
QComboBox { padding-right: 24px; }
QComboBox::drop-down { width: 24px; border-left: 1px solid @line; }
QComboBox::down-arrow { image: url(@down); width: 12px; height: 12px; }
QSpinBox, QDoubleSpinBox { padding-right: 27px; }
QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 23px; background: @inset; border-left: 1px solid @border; border-bottom: 1px solid @line; }
QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 23px; background: @inset; border-left: 1px solid @border; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url(@up); width: 12px; height: 9px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url(@down); width: 12px; height: 9px; }
QComboBox QAbstractItemView { background: @surface; color: @text; border: 1px solid @border; selection-background-color: @soft; selection-color: @text; padding: 4px; }
QCheckBox, QRadioButton { spacing: 9px; padding: 4px 0; }
QCheckBox::indicator, QRadioButton::indicator, QGroupBox::indicator, QAbstractItemView::indicator { width: 18px; height: 18px; border: 2px solid @border; border-radius: 4px; background: @surface; }
QCheckBox::indicator:hover, QRadioButton::indicator:hover, QGroupBox::indicator:hover { border-color: @accent; }
QCheckBox::indicator:checked, QGroupBox::indicator:checked, QAbstractItemView::indicator:checked { background: #4f46e5; border-color: #4f46e5; image: url(@check); }
QCheckBox::indicator:indeterminate, QAbstractItemView::indicator:indeterminate { background: #4f46e5; border-color: #4f46e5; image: url(@mixed); }
QRadioButton::indicator { border-radius: 10px; }
QRadioButton::indicator:checked { background: #4f46e5; border-color: #4f46e5; image: url(@radio); }
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled, QGroupBox::indicator:disabled { border-color: @disabled; background: @inset; }
QCheckBox::indicator:checked:disabled, QRadioButton::indicator:checked:disabled { background: @disabled; }
QCheckBox:disabled, QRadioButton:disabled { color: @disabled; }
QGroupBox::indicator { subcontrol-origin: margin; subcontrol-position: top left; }

QDockWidget { background: @bg; font-weight: 600; }
QDockWidget::title { background: @bg; color: @muted; padding: 10px 12px; border-bottom: 1px solid @line; }
QWidget#ProjectHeaderCard { background: @surface; border: 1px solid @line; border-radius: 8px; }
QWidget#ProjectExplorerWidget { background: @bg; }
QWidget#ProjectExplorerWidget QTreeWidget { background: transparent; border: none; }
QTreeWidget, QListWidget { background: @surface; border: 1px solid @line; border-radius: 6px; outline: none; }
QTreeWidget::item { padding: 7px 5px; margin: 2px 0; border-radius: 5px; }
QTreeWidget::item:hover { background: @hover; }
QTreeWidget::item:selected, QListWidget::item:selected { background: @soft; color: @accent; }
QTabWidget::pane { background: @surface; border: 1px solid @line; }
QTabBar::tab { font-weight: 500; background: @bg; color: @muted; border: none; border-bottom: 2px solid transparent; padding: 10px 26px 10px 14px; margin-right: 1px; }
QTabBar::tab:selected { background: @surface; color: @accent; border-bottom: 2px solid @accent; }
QTabBar::tab:hover:!selected { background: @hover; color: @text; }
QTabWidget#WorkspaceTabs::pane, QTabWidget#ChartEditorTabs::pane { border: none; }
QTabWidget#WorkspaceTabs QTabBar::base, QTabWidget#ChartEditorTabs QTabBar::base { border: none; }
QTabWidget#WorkspaceTabs QTabBar::tab, QTabWidget#ChartEditorTabs QTabBar::tab {
    border: none; border-top-left-radius: 5px; border-top-right-radius: 5px;
}
QTabWidget#WorkspaceTabs QTabBar::tab:selected, QTabWidget#ChartEditorTabs QTabBar::tab:selected {
    background: @selection; color: @accent; border: none;
}
QToolBar#ChartWorkspaceToolbar { border-bottom: none; }
QTabBar::close-button { image: url(@close); subcontrol-position: right; width: 12px; height: 12px; margin-right: 4px; padding: 2px; }
QTabBar::close-button:hover { image: url(@close_hover); }
QScrollArea { border: none; background: @surface; }
QScrollArea > QWidget > QWidget { background: @surface; }
QGroupBox { background: @surface; border: 1px solid @line; border-radius: 7px; margin-top: 14px; padding: 12px 8px 8px; font-weight: 600; }
QGroupBox::title { font-weight: 600; subcontrol-origin: margin; subcontrol-position: top left; padding: 0 6px; color: @muted; }
QTableView, QTableWidget { background: @surface; alternate-background-color: @inset; gridline-color: @line; color: @text; border: 1px solid @line; selection-background-color: @selection; selection-color: @text; }
QHeaderView::section { background: @inset; color: @muted; padding: 7px 9px; border: none; border-right: 1px solid @line; border-bottom: 1px solid @line; font-weight: 600; }
QHeaderView::section:checked { background: @soft; color: @accent; }
QTableCornerButton::section { background: @inset; border: 1px solid @line; }
QTextBrowser { background: @surface; border: 1px solid @line; padding: 12px; selection-background-color: @selection; }
QStatusBar { background: @bg; color: @muted; border-top: 1px solid @line; padding: 3px 5px; }
QStatusBar QLabel { color: @muted; }
QLabel#StatusCoords { font-family: Consolas, monospace; padding: 0 8px; }
QScrollBar:vertical { background: transparent; width: 12px; margin: 0; }
QScrollBar:horizontal { background: transparent; height: 12px; margin: 0; }
QScrollBar::handle { background: @border; border-radius: 4px; min-height: 28px; min-width: 28px; }
QScrollBar::handle:hover { background: @muted; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QSplitter::handle { background: @line; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }
QWidget#ChartEditorBody, QWidget#SheetHeader { background: @surface; }
QWidget#QuickLabelBar, QWidget#LinkedSourceBar { background: @surface; }
QLabel#Brand { font-size: 20px; font-weight: 800; color: @accent; padding: 0 14px 0 3px; }
QFrame#WorksheetStarterPanel { background: @inset; border: 1px solid @line; border-radius: 10px; }
QPushButton#WelcomeChoice { text-align: left; padding: 13px 16px; background: @surface; border: 1px solid @line; border-radius: 8px; }
QPushButton#WelcomeChoice:hover { background: @soft; border-color: @accent; }
QPushButton#WelcomeChoice[role="primary"] { background: #4f46e5; color: white; border-color: #4f46e5; }
QLineEdit#FormulaInput { font-family: Consolas, monospace; font-size: 12px; }
QToolTip { background: @surface; color: @text; border: 1px solid @border; padding: 6px; }
QProgressBar { background: @inset; border: 1px solid @line; border-radius: 4px; text-align: center; }
QProgressBar::chunk { background: @accent; border-radius: 3px; }
"""
    icons=ensure_style_icons()
    c.update(close=icons["close_dark" if dark else "close_light"],close_hover=icons["close_hover"],check=icons["check"],mixed=icons["mixed"],radio=icons["radio"],down=icons["arrow_down_dark" if dark else "arrow_down_light"],up=icons["arrow_up_dark" if dark else "arrow_up_light"])
    for name in sorted(c,key=len,reverse=True):
        q=q.replace("@"+name,c[name])
    return q

LIGHT_THEME_QSS = _theme()
DARK_THEME_QSS = _theme(True)


def scaled_stylesheet(stylesheet, scale):
    """Scale shared interface geometry from its original values each time."""
    import re
    return re.sub(r"(\d+(?:\.\d+)?)px", lambda match: f"{max(1,round(float(match.group(1))*scale))}px", stylesheet)
