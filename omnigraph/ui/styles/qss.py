"""
Modern QSS Stylesheets for Graffy.
Provides clean scientific Light and Dark themes.
"""

DARK_THEME_QSS = """
QMainWindow, QDialog {
    background-color: #181825;
    color: #cdd6f4;
}

QWidget {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #cdd6f4;
}

QMenuBar {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border-bottom: 1px solid #313244;
    padding: 3px;
}

QMenuBar::item {
    background: transparent;
    padding: 4px 10px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #313244;
    color: #89b4fa;
}

QMenu {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 24px 6px 20px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #313244;
    color: #89b4fa;
}

QMenu::separator {
    height: 1px;
    background-color: #313244;
    margin: 4px 8px;
}

QToolBar {
    background-color: #1e1e2e;
    border-bottom: 1px solid #313244;
    padding: 4px;
    spacing: 6px;
}

QToolButton {
    background-color: transparent;
    color: #cdd6f4;
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 5px 8px;
    font-weight: 500;
}

QToolButton:hover {
    background-color: #313244;
    border: 1px solid #45475a;
}

QToolButton:pressed {
    background-color: #45475a;
}

QToolButton:checked {
    background-color: #313244;
    border: 1px solid #89b4fa;
    color: #89b4fa;
}

QDockWidget {
    background-color: #181825;
    color: #f8fafc;
    font-weight: bold;
    titlebar-close-icon: url(close.png);
    titlebar-normal-icon: url(float.png);
}

QDockWidget::title {
    background: #181825;
    padding: 8px 10px;
    border-bottom: 2px solid #313244;
    font-size: 12px;
    font-weight: 700;
    color: #f8fafc;
}

QWidget#ProjectHeaderCard {
    background-color: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 5px;
}
QWidget#ProjectHeaderCard QLabel {
    color: #cdd6f4;
}

QWidget#QuickLabelBar, QWidget#LinkedSourceBar {
    background-color: #1e1e2e;
    border-bottom: 1px solid #313244;
    padding: 3px 6px;
}

QWidget#QuickLabelBar QLabel, QWidget#LinkedSourceBar QLabel {
    color: #cdd6f4;
    font-weight: 600;
    font-size: 11px;
}

QWidget#QuickLabelBar QLineEdit {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 3px 6px;
    font-size: 11px;
}

QWidget#QuickLabelBar QLineEdit:focus {
    border: 1px solid #89b4fa;
}

QWidget#QuickLabelBar QToolButton, QWidget#LinkedSourceBar QToolButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 500;
}

QWidget#QuickLabelBar QToolButton:hover, QWidget#LinkedSourceBar QToolButton:hover {
    background-color: #45475a;
    border-color: #89b4fa;
    color: #89b4fa;
}

QWidget#PropertyInspectorWidget {
    background-color: #181825;
}

QLabel {
    color: #cdd6f4;
    font-weight: 600;
}

QCheckBox {
    color: #cdd6f4;
    font-weight: 500;
    spacing: 6px;
}

QScrollArea {
    background-color: #181825;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: #181825;
}

QTabWidget::pane {
    border: 1px solid #313244;
    background: #181825;
}

QTabBar::tab {
    background: #1e1e2e;
    color: #cdd6f4;
    padding: 7px 24px 7px 12px;
    border: 1px solid #313244;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
    font-weight: 600;
}

QDockWidget QTabBar::tab {
    padding: 6px 11px;
    font-size: 11px;
}

QTabBar::tab:selected {
    background: #181825;
    color: #89b4fa;
    border-top: 2.5px solid #89b4fa;
    border-bottom: 1px solid #181825;
    font-weight: bold;
}

QTabBar::tab:hover:!selected {
    background: #28283d;
    color: #ffffff;
}

QTabBar::close-button {
    image: url(__CLOSE_DARK_ICON__);
    subcontrol-position: right;
    margin-right: 4px;
    padding: 2px;
    border-radius: 3px;
}

QTabBar::close-button:hover {
    image: url(__CLOSE_HOVER_ICON__);
    background-color: #3b4261;
}

QTextBrowser {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 8px;
    selection-background-color: #45475a;
    selection-color: #89b4fa;
}

QTableView, QTableWidget {
    background-color: #181825;
    alternate-background-color: #1e1e2e;
    gridline-color: #313244;
    color: #cdd6f4;
    border: 1px solid #313244;
    selection-background-color: #45475a;
    selection-color: #89b4fa;
}

QTextEdit, QPlainTextEdit {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 6px;
    selection-background-color: #45475a;
    selection-color: #89b4fa;
}

QHeaderView {
    background-color: #1e1e2e;
}

QHeaderView::section {
    background-color: #1e1e2e;
    color: #cdd6f4;
    padding: 4px 6px;
    border: 1px solid #313244;
    font-weight: 600;
}

QHeaderView::section:checked {
    background-color: #313244;
    color: #89b4fa;
    border: 1px solid #89b4fa;
}

QTableCornerButton::section {
    background-color: #1e1e2e;
    border: 1px solid #313244;
}

QTreeWidget, QListWidget {
    background-color: #181825;
    border: 1px solid #313244;
    color: #cdd6f4;
    border-radius: 4px;
}

QTreeWidget::item {
    padding: 4px 6px;
    border-radius: 3px;
    margin: 1px 0px;
}

QTreeWidget::item:hover {
    background-color: #262738;
}

QTreeWidget::item:selected, QListWidget::item:selected {
    background-color: #313244;
    color: #89b4fa;
    font-weight: 600;
}

QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 5px;
    padding: 6px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #45475a;
    border-color: #89b4fa;
}

QPushButton:pressed {
    background-color: #585b70;
}

QPushButton:default {
    background-color: #89b4fa;
    color: #181825;
    font-weight: bold;
    border-color: #89b4fa;
}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 5px 8px;
    selection-background-color: #45475a;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #89b4fa;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #45475a;
}

QComboBox QAbstractItemView {
    background-color: #1e1e2e;
    border: 1px solid #45475a;
    color: #cdd6f4;
    selection-background-color: #313244;
}

QStatusBar {
    background-color: #1e1e2e;
    color: #a6adc8;
    border-top: 1px solid #313244;
    font-size: 11px;
}

QGroupBox {
    border: 1.5px solid #313244;
    border-radius: 6px;
    margin-top: 14px;
    padding: 10px 8px 6px 8px;
    background-color: #181825;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 1px 8px;
    color: #89b4fa;
    font-weight: 700;
    font-size: 11px;
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 3px;
}

QGroupBox QLabel, QGroupBox QCheckBox {
    color: #f8fafc;
    font-weight: 500;
}

QScrollBar:vertical {
    background: #181825;
    width: 12px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #45475a;
    min-height: 20px;
    border-radius: 6px;
}

QScrollBar::handle:vertical:hover {
    background: #585b70;
}

QScrollBar:horizontal {
    background: #181825;
    height: 12px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #45475a;
    min-width: 20px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal:hover {
    background: #585b70;
}

NavigationToolbar2QT {
    background-color: #1e1e2e;
    border-bottom: 1px solid #313244;
    padding: 2px;
}

NavigationToolbar2QT QLabel {
    color: #cdd6f4;
    font-size: 11px;
    font-weight: 600;
}

QStatusBar {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border-top: 1px solid #313244;
}

QStatusBar QLabel {
    color: #cdd6f4;
}

QLabel#StatusCoords {
    font-family: monospace;
    font-weight: bold;
    color: #89b4fa;
    padding: 0 8px;
}

QLabel#SpreadsheetColInfo {
    font-weight: bold;
    color: #89b4fa;
    padding-left: 4px;
    padding-right: 8px;
}

QLabel#SpreadsheetPlotTag {
    font-weight: 600;
    color: #a6adc8;
    font-size: 11px;
}

QLabel#LinkedSourceIcon {
    font-weight: 700;
    color: #89b4fa;
    padding-right: 4px;
}

QLabel#LinkedSourceNone {
    color: #a6adc8;
    font-style: italic;
    font-size: 11px;
}

QLineEdit#FormulaInput {
    font-family: "SF Mono", Monaco, Menlo, Consolas, monospace;
    font-size: 12px;
    font-weight: bold;
    padding: 7px 10px;
    color: #cdd6f4;
    background: #181825;
    border: 2px solid #89b4fa;
    border-radius: 4px;
}
"""

LIGHT_THEME_QSS = """
QMainWindow, QDialog {
    background-color: #f8fafc;
    color: #0f172a;
}

QWidget {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #0f172a;
}

QMenuBar {
    background-color: #ffffff;
    color: #0f172a;
    border-bottom: 1px solid #e2e8f0;
    padding: 3px;
}

QMenuBar::item {
    background: transparent;
    padding: 4px 10px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #f1f5f9;
    color: #0284c7;
}

QMenu {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 24px 6px 20px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #f0f9ff;
    color: #0284c7;
}

QMenu::separator {
    height: 1px;
    background-color: #e2e8f0;
    margin: 4px 8px;
}

QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    padding: 4px;
    spacing: 6px;
}

QToolButton {
    background-color: transparent;
    color: #334155;
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 5px 8px;
    font-weight: 500;
}

QToolButton:hover {
    background-color: #f1f5f9;
    border: 1px solid #cbd5e1;
}

QToolButton:pressed {
    background-color: #e2e8f0;
}

QToolButton:checked {
    background-color: #e0f2fe;
    border: 1px solid #0284c7;
    color: #0284c7;
}

QDockWidget {
    background-color: #f8fafc;
    color: #0f172a;
    font-weight: 700;
}

QDockWidget::title {
    background: #e2e8f0;
    padding: 8px 10px;
    border-bottom: 2px solid #cbd5e1;
    font-weight: 700;
    color: #0f172a;
    font-size: 12px;
}

QWidget#ProjectHeaderCard {
    background-color: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
}
QWidget#ProjectHeaderCard QLabel {
    color: #0f172a;
}

QWidget#QuickLabelBar, QWidget#LinkedSourceBar {
    background-color: #f1f5f9;
    border-bottom: 1px solid #cbd5e1;
    padding: 3px 6px;
}

QWidget#QuickLabelBar QLabel, QWidget#LinkedSourceBar QLabel {
    color: #0f172a;
    font-weight: 600;
    font-size: 11px;
}

QWidget#QuickLabelBar QLineEdit {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #94a3b8;
    border-radius: 4px;
    padding: 3px 6px;
    font-size: 11px;
}

QWidget#QuickLabelBar QLineEdit:focus {
    border: 1px solid #0284c7;
}

QWidget#QuickLabelBar QToolButton, QWidget#LinkedSourceBar QToolButton {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 500;
}

QWidget#QuickLabelBar QToolButton:hover, QWidget#LinkedSourceBar QToolButton:hover {
    background-color: #e2e8f0;
    border-color: #0284c7;
    color: #0284c7;
}

QWidget#PropertyInspectorWidget {
    background-color: #f8fafc;
}

QScrollArea {
    background-color: #ffffff;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: #ffffff;
}

QTabWidget::pane {
    border: 1.5px solid #cbd5e1;
    background: #ffffff;
}

QTabBar::tab {
    background: #e2e8f0;
    color: #334155;
    padding: 7px 24px 7px 12px;
    border: 1px solid #cbd5e1;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 3px;
    font-weight: 600;
}

QTabBar::tab:hover:!selected {
    background: #cbd5e1;
    color: #0f172a;
}

QTabBar::tab:selected {
    background: #ffffff;
    color: #0369a1;
    border-top: 3px solid #0284c7;
    border-bottom: 1px solid #ffffff;
    font-weight: 700;
}

QTabBar::close-button {
    image: url(__CLOSE_LIGHT_ICON__);
    subcontrol-position: right;
    margin-right: 4px;
    padding: 2px;
    border-radius: 3px;
}

QTabBar::close-button:hover {
    image: url(__CLOSE_HOVER_ICON__);
    background-color: #fee2e2;
}

QTextBrowser {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px;
    selection-background-color: #bae6fd;
    selection-color: #0369a1;
}

QDockWidget QTabBar::tab {
    padding: 6px 12px;
    font-size: 11px;
}

QLabel {
    color: #0f172a;
    font-weight: 600;
}

QCheckBox {
    color: #0f172a;
    font-weight: 500;
    spacing: 6px;
}

QTableView, QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #f8fafc;
    gridline-color: #e2e8f0;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    selection-background-color: #bae6fd;
    selection-color: #0369a1;
}

QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #94a3b8;
    border-radius: 4px;
    padding: 6px;
    selection-background-color: #bae6fd;
    selection-color: #0369a1;
}

QHeaderView {
    background-color: #f1f5f9;
}

QHeaderView::section {
    background-color: #f1f5f9;
    color: #0f172a;
    padding: 4px 6px;
    border: 1px solid #cbd5e1;
    font-weight: 700;
}

QHeaderView::section:checked {
    background-color: #e0f2fe;
    color: #0284c7;
    border: 1px solid #0284c7;
}

QTableCornerButton::section {
    background-color: #f1f5f9;
    border: 1px solid #cbd5e1;
}

QTreeWidget, QListWidget {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    color: #0f172a;
    border-radius: 4px;
}

QTreeWidget::item {
    padding: 4px 6px;
    border-radius: 3px;
    margin: 1px 0px;
}

QTreeWidget::item:hover {
    background-color: #f1f5f9;
}

QTreeWidget::item:selected, QListWidget::item:selected {
    background-color: #e0f2fe;
    color: #0284c7;
    font-weight: 600;
}

QPushButton {
    background-color: #f8fafc;
    color: #0f172a;
    border: 1.5px solid #94a3b8;
    border-radius: 4px;
    padding: 5px 12px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #f1f5f9;
    border-color: #64748b;
    color: #0284c7;
}

QPushButton:pressed {
    background-color: #cbd5e1;
}

QPushButton:default {
    background-color: #0284c7;
    color: #ffffff;
    font-weight: bold;
    border-color: #0284c7;
}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    color: #0f172a;
    border: 1.5px solid #94a3b8;
    border-radius: 4px;
    padding: 5px 8px;
    font-weight: 500;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1.5px solid #0284c7;
    background-color: #ffffff;
}

QStatusBar {
    background-color: #f8fafc;
    color: #334155;
    border-top: 1px solid #cbd5e1;
    font-size: 11px;
    font-weight: 500;
}

QGroupBox {
    border: 1.5px solid #cbd5e1;
    border-radius: 6px;
    margin-top: 14px;
    padding: 10px 8px 6px 8px;
    background-color: #ffffff;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 1px 8px;
    color: #0369a1;
    font-weight: 700;
    font-size: 11px;
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
}

QGroupBox QLabel, QGroupBox QCheckBox {
    color: #0f172a;
    font-weight: 600;
}

QScrollBar:vertical {
    background: #f8fafc;
    width: 12px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #cbd5e1;
    min-height: 20px;
    border-radius: 6px;
}

QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}

QScrollBar:horizontal {
    background: #f8fafc;
    height: 12px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #cbd5e1;
    min-width: 20px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal:hover {
    background: #94a3b8;
}

NavigationToolbar2QT {
    background-color: #f8fafc;
    border-bottom: 1px solid #e2e8f0;
    padding: 2px;
}

NavigationToolbar2QT QLabel {
    color: #0f172a;
    font-size: 11px;
    font-weight: 600;
}

QStatusBar {
    background-color: #f1f5f9;
    color: #0f172a;
    border-top: 1px solid #e2e8f0;
}

QStatusBar QLabel {
    color: #0f172a;
}

QLabel#StatusCoords {
    font-family: monospace;
    font-weight: bold;
    color: #0284c7;
    padding: 0 8px;
}

QLabel#SpreadsheetColInfo {
    font-weight: bold;
    color: #0284c7;
    padding-left: 4px;
    padding-right: 8px;
}

QLabel#SpreadsheetPlotTag {
    font-weight: 600;
    color: #475569;
    font-size: 11px;
}

QLabel#LinkedSourceIcon {
    font-weight: 700;
    color: #0284c7;
    padding-right: 4px;
}

QLabel#LinkedSourceNone {
    color: #64748b;
    font-style: italic;
    font-size: 11px;
}

QLineEdit#FormulaInput {
    font-family: "SF Mono", Monaco, Menlo, Consolas, monospace;
    font-size: 12px;
    font-weight: bold;
    padding: 7px 10px;
    color: #0f172a;
    background: #ffffff;
    border: 2px solid #0284c7;
    border-radius: 4px;
}
"""

try:
    from omnigraph.ui.styles.icons import ensure_style_icons
    _icons = ensure_style_icons()
    DARK_THEME_QSS = DARK_THEME_QSS.replace("__CLOSE_DARK_ICON__", _icons["close_dark"]).replace("__CLOSE_HOVER_ICON__", _icons["close_hover"])
    LIGHT_THEME_QSS = LIGHT_THEME_QSS.replace("__CLOSE_LIGHT_ICON__", _icons["close_light"]).replace("__CLOSE_HOVER_ICON__", _icons["close_hover"])
except Exception:
    pass
