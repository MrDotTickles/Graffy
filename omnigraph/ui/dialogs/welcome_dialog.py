"""A focused starting point with four explicit choices."""
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (QDialog,QVBoxLayout,QLabel,QPushButton,
                            QScrollArea,QWidget,QCheckBox,QHBoxLayout)
from omnigraph.ui.styles.design import icon

class WelcomeDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.choice=None
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

    def select(self,choice):
        self.choice=choice
        self.accept()
