"""Start a workspace or reopen a recent project."""
from pathlib import Path
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (QDialog,QVBoxLayout,QLabel,QPushButton,
                            QScrollArea,QWidget,QCheckBox,QMenu,QToolButton)
from omnigraph.ui.styles.design import icon

class WelcomeDialog(QDialog):
    def __init__(self, parent=None, *, recent_projects=()):
        super().__init__(parent)
        self.choice = None
        self.recent_path = None
        self.setWindowTitle("Welcome to Graffy")
        available=self.screen().availableGeometry()
        self.resize(min(560,available.width()-32),min(650,available.height()-48))
        outer=QVBoxLayout(self)
        outer.setContentsMargins(16,16,16,16)
        scroll=QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        body=QWidget()
        content=QVBoxLayout(body)
        content.setContentsMargins(20,20,20,20)
        content.setSpacing(12)
        brand=QLabel("graffy")
        brand.setObjectName("Brand")
        content.addWidget(brand)
        title=QLabel("From data to a figure worth sharing.")
        title.setProperty("role","heading")
        title.setWordWrap(True)
        content.addWidget(title)
        intro=QLabel("Import your data, create a chart, and export a clear result. Choose where to begin.")
        intro.setProperty("role","muted")
        intro.setWordWrap(True)
        content.addWidget(intro)
        content.addSpacing(6)
        for label,description,choice,glyph in [
            ("Import data","Excel, CSV, text, or instrument files","import","import"),
            ("Open a project","Continue a saved Graffy project","open","folder"),
            ("Explore an example","Try a complete scientific graph","sample","chart"),
            ("Blank worksheet","Type or paste your own values","new","sheet")]:
            button=QPushButton(label+"\n"+description)
            button.setObjectName("WelcomeChoice")
            button.setIcon(icon(glyph,"#ffffff" if choice=="import" else None))
            button.setIconSize(QSize(24,24))
            button.setMinimumHeight(66)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            if choice=="import":
                button.setProperty("role","primary")
            button.clicked.connect(lambda checked=False,value=choice:self.select(value))
            content.addWidget(button)
        if recent_projects:
            recent_button = QToolButton()
            recent_button.setText("Recent projects")
            recent_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            recent_button.setIcon(icon("folder"))
            recent_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            recent_menu = QMenu(recent_button)
            recent_menu.setToolTipsVisible(True)
            for path in recent_projects:
                name = Path(path).name.replace("&", "&&")
                action = recent_menu.addAction(name, lambda checked=False, selected=path: self.open_recent(selected))
                action.setToolTip(str(path))
            recent_button.setMenu(recent_menu)
            content.addWidget(recent_button)

        hint=QLabel("Your data is processed locally on your computer.")
        hint.setProperty("role","muted")
        hint.setWordWrap(True)
        content.addWidget(hint)
        content.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll,1)
        self.show_again=QCheckBox("Show this when Graffy starts")
        self.show_again.setChecked(True)
        outer.addWidget(self.show_again)
        close=QPushButton("Continue to workspace")
        close.clicked.connect(self.reject)
        outer.addWidget(close)

    def open_recent(self, path):
        self.recent_path = path
        self.select("recent")

    def select(self,choice):
        self.choice=choice
        self.accept()
