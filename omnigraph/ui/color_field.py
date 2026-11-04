"""Accessible color picking with a visible swatch, hex value, and automatic reset."""
from PyQt6.QtCore import Qt,pyqtSignal
from PyQt6.QtGui import QColor,QPixmap,QPainter,QPen,QIcon
from PyQt6.QtWidgets import QWidget,QPushButton,QToolButton,QHBoxLayout,QColorDialog,QMenu

class ColorButton(QPushButton):
    colorChanged=pyqtSignal(str)
    def __init__(self,color="auto",parent=None,title="Choose a color"):
        super().__init__(parent)
        self.dialog_title=title
        self.setAutoDefault(False)
        self.clicked.connect(self.choose_color)
        self.set_color(color)

    def color(self):
        return self._color

    def set_color(self,color):
        self._color=color if color=="none" or (color and color!="auto" and QColor(color).isValid()) else "auto"
        self.setText("Transparent" if self._color=="none" else self._color if self._color!="auto" else "Automatic")
        swatch=QPixmap(20,20)
        swatch.fill(Qt.GlobalColor.transparent)
        painter=QPainter(swatch)
        painter.setPen(QPen(QColor("#64748b"),1))
        painter.setBrush(QColor(self._color if self._color not in ("auto","none") else "#d4dbea"))
        painter.drawRoundedRect(1,1,17,17,3,3)
        painter.end()
        self.setIcon(QIcon(swatch))
        self.setToolTip(self.dialog_title+" ("+self.text()+")")
        self.setAccessibleName(self.dialog_title+": "+self.text())

    def choose_color(self):
        color=QColorDialog.getColor(QColor(self._color if self._color not in ("auto","none") else "#4f46e5"),self,self.dialog_title)
        if color.isValid():
            self.set_color(color.name())
            self.colorChanged.emit(self._color)

class ColorField(QWidget):
    colorChanged=pyqtSignal(str)
    def __init__(self,color="auto",parent=None,title="Choose a color",allow_transparent=False):
        super().__init__(parent)
        row=QHBoxLayout(self)
        row.setContentsMargins(0,0,0,0)
        row.setSpacing(4)
        self.button=ColorButton(color,self,title)
        row.addWidget(self.button,1)
        self.reset_button=QToolButton()
        self.reset_button.setText("Auto")
        self.reset_button.setToolTip("Use the figure theme or automatic series palette")
        if allow_transparent:
            self.reset_button.setText("Options")
            self.reset_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            menu=QMenu(self.reset_button)
            menu.addAction("Automatic",self.reset_color)
            menu.addAction("Transparent",self.make_transparent)
            self.reset_button.setMenu(menu)
        else:
            self.reset_button.clicked.connect(self.reset_color)
        row.addWidget(self.reset_button)
        self.button.colorChanged.connect(self.colorChanged)
    def color(self):
        return self.button.color()
    def set_color(self,color):
        self.button.set_color(color)
    def reset_color(self):
        self.set_color("auto")
        self.colorChanged.emit("auto")

    def make_transparent(self):
        self.set_color("none")
        self.colorChanged.emit("none")
