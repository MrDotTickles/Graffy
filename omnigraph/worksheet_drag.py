"""A local worksheet reference carried by a Qt drag."""
from PyQt6.QtCore import QMimeData


class WorksheetDragData(QMimeData):
    def __init__(self, project, workbook, sheet):
        super().__init__()
        self.project = project
        self.workbook = workbook
        self.sheet = sheet
        self.setData("application/x-graffy-worksheet", b"worksheet")
