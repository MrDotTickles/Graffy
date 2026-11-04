"""One editor for series names/colors and legend appearance."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,
    QTabWidget,QWidget,QCheckBox,QComboBox,QSpinBox,QPushButton,QTableWidget,
    QTableWidgetItem,QHeaderView,QInputDialog,QMessageBox,QToolButton,QMenu)
from omnigraph.ui.color_field import ColorButton,ColorField
from omnigraph.core.plot_editing import set_series_color
from omnigraph.graphing.themes import get_theme_palette
from omnigraph.ui.dialogs.dialog_layout import finish_dialog

class LegendEditorDialog(QDialog):
    def __init__(self,graph,parent=None,on_apply_callback=None,project=None):
        super().__init__(parent)
        self.graph=graph
        self.project=project
        self.on_apply_callback=on_apply_callback
        self.setWindowTitle("Series and legend")
        self.resize(620,580)
        self._init_ui()

    def _init_ui(self):
        layout=QVBoxLayout(self)
        title=QLabel("Series and legend")
        title.setProperty("role","heading")
        layout.addWidget(title)
        hint=QLabel("Choose series colors and names, then set how the legend looks.")
        hint.setProperty("role","muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.tabs=QTabWidget()
        layout.addWidget(self.tabs,1)
        series=QWidget()
        content=QVBoxLayout(series)
        hint=QLabel("Click a color to recolor the matching line, symbols and legend key. Double-click a name to rename it. Uncheck a series to hide it.")
        hint.setWordWrap(True)
        content.addWidget(hint)
        self.table_series=QTableWidget(0,4)
        self.table_series.setHorizontalHeaderLabels(["Show","Color","Plot","Series name"])
        for column in range(3):
            self.table_series.horizontalHeader().setSectionResizeMode(column,QHeaderView.ResizeMode.ResizeToContents)
        self.table_series.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeMode.Stretch)
        self.table_series.verticalHeader().hide()
        self.table_series.setAlternatingRowColors(True)
        self.table_series.setMinimumHeight(130)
        self._populate_series_table()
        content.addWidget(self.table_series,1)
        batch=QToolButton()
        batch.setText("Rename all…")
        batch.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu=QMenu(batch)
        menu.addAction("Number series",self._preset_number_series)
        menu.addAction("Add a prefix…",self._preset_add_prefix)
        menu.addAction("Add a suffix…",self._preset_add_suffix)
        menu.addSeparator()
        menu.addAction("Use source column names",self._preset_reset_to_columns)
        batch.setMenu(menu)
        content.addWidget(batch,0,Qt.AlignmentFlag.AlignLeft)
        self.tabs.addTab(series,"Series")
        legend=QWidget()
        options=QVBoxLayout(legend)
        self.chk_show=QCheckBox("Show legend")
        self.chk_show.setChecked(self.graph.legend_show)
        options.addWidget(self.chk_show)
        self.legend_options=QWidget()
        form=QFormLayout(self.legend_options)
        form.setContentsMargins(0,0,0,0)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.combo_pos=QComboBox()
        self.combo_pos.addItems(["best","upper right","upper left","lower left","lower right","center right","center left","upper center","lower center","center","outside right","outside top"])
        if self.graph.legend_location not in [self.combo_pos.itemText(i) for i in range(self.combo_pos.count())]:
            self.combo_pos.addItem(self.graph.legend_location)
        self.combo_pos.setCurrentText(self.graph.legend_location)
        form.addRow("Position",self.combo_pos)
        self.spn_fs=QSpinBox()
        self.spn_fs.setRange(6,48)
        self.spn_fs.setValue(int(self.graph.legend_font_size))
        form.addRow("Text size (pt)",self.spn_fs)
        self.text_color=ColorField(self.graph.legend_text_color,title="Legend text color")
        form.addRow("Text color",self.text_color)
        self.chk_frame=QCheckBox("Show legend box")
        self.chk_frame.setChecked(self.graph.legend_frame)
        form.addRow(self.chk_frame)
        self.frame_options=QWidget()
        frame_form=QFormLayout(self.frame_options)
        frame_form.setContentsMargins(0,0,0,0)
        frame_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.background_color=ColorField(self.graph.legend_face_color,title="Legend background color")
        self.border_color=ColorField(self.graph.legend_edge_color,title="Legend border color")
        self.opacity=QSpinBox()
        self.opacity.setRange(0,100)
        self.opacity.setSuffix(" %")
        self.opacity.setValue(round(self.graph.legend_frame_alpha*100))
        frame_form.addRow("Background",self.background_color)
        frame_form.addRow("Border",self.border_color)
        frame_form.addRow("Box opacity",self.opacity)
        form.addRow(self.frame_options)
        self.chk_show.toggled.connect(self.legend_options.setEnabled)
        self.legend_options.setEnabled(self.chk_show.isChecked())
        self.chk_frame.toggled.connect(self.frame_options.setEnabled)
        self.frame_options.setEnabled(self.chk_frame.isChecked())
        options.addWidget(self.legend_options)
        note=QLabel("Auto uses the figure theme. Series colors also change the lines or symbols on your graph.")
        note.setWordWrap(True)
        note.setProperty("role","muted")
        options.addWidget(note)
        options.addStretch()
        self.tabs.addTab(legend,"Legend")
        self.status=QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons=QHBoxLayout()
        self.btn_apply=QPushButton("Apply")
        self.btn_apply.clicked.connect(self._apply_changes)
        buttons.addWidget(self.btn_apply)
        buttons.addStretch()
        cancel=QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        self.btn_save=QPushButton("Save changes")
        self.btn_save.setDefault(True)
        self.btn_save.setProperty("role","primary")
        self.btn_save.clicked.connect(self._on_ok)
        buttons.addWidget(self.btn_save)
        layout.addLayout(buttons)
        finish_dialog(self)

    def _populate_series_table(self):
        self.table_series.setRowCount(len(self.graph.curves))
        self.color_buttons=[]
        for row,curve in enumerate(self.graph.curves):
            show=QTableWidgetItem(str(row+1))
            show.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsUserCheckable|Qt.ItemFlag.ItemIsSelectable)
            show.setCheckState(Qt.CheckState.Checked if curve.visible else Qt.CheckState.Unchecked)
            self.table_series.setItem(row,0,show)
            button=ColorButton(curve.color,title=f"Color for {curve.label or 'series '+str(row+1)}")
            self.color_buttons.append(button)
            self.table_series.setCellWidget(row,1,button)
            kind=QTableWidgetItem(curve.plot_type.replace("_"," "))
            kind.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table_series.setItem(row,2,kind)
            self.table_series.setItem(row,3,QTableWidgetItem(curve.label or f"Curve {row+1}"))
            self.table_series.setRowHeight(row,40)

    def _apply_changes(self):
        fields=("legend_show","legend_location","legend_frame","legend_font_size","legend_text_color","legend_face_color","legend_edge_color","legend_frame_alpha")
        previous={key:getattr(self.graph,key) for key in fields}
        previous_curves=[(c,c.label,c.color,c.visible,c.marker_face_color,c.marker_edge_color) for c in self.graph.curves]
        try:
            # Commit any active cell editor before reading names.
            self.table_series.setFocus()
            for row,curve in enumerate(self.graph.curves[:self.table_series.rowCount()]):
                item=self.table_series.item(row,3)
                curve.label=(item.text().strip() if item else "") or f"Curve {row+1}"
                palette=get_theme_palette(self.graph.theme)
                effective=palette[row%len(palette)] if curve.color=="auto" else curve.color
                set_series_color(curve,self.color_buttons[row].color(),effective)
                curve.visible=self.table_series.item(row,0).checkState()==Qt.CheckState.Checked
            self.graph.legend_show=self.chk_show.isChecked()
            self.graph.legend_location=self.combo_pos.currentText()
            self.graph.legend_frame=self.chk_frame.isChecked()
            self.graph.legend_font_size=self.spn_fs.value()
            self.graph.legend_text_color=self.text_color.color()
            self.graph.legend_face_color=self.background_color.color()
            self.graph.legend_edge_color=self.border_color.color()
            self.graph.legend_frame_alpha=self.opacity.value()/100
            if callable(self.on_apply_callback):
                self.on_apply_callback()
            self.status.setText("Changes applied to the figure.")
            return True
        except Exception as error:
            for key,value in previous.items():
                setattr(self.graph,key,value)
            for curve,label,color,visible,fill,edge in previous_curves:
                curve.label,curve.color,curve.visible=label,color,visible
                curve.marker_face_color,curve.marker_edge_color=fill,edge
            QMessageBox.warning(self,"Could not apply changes",str(error))
            return False

    def _on_ok(self):
        if self._apply_changes():
            self.accept()

    def _preset_number_series(self):
        for row in range(self.table_series.rowCount()):
            self.table_series.setItem(row,3,QTableWidgetItem(f"Series {row+1}"))

    def _preset_add_prefix(self):
        prefix,ok=QInputDialog.getText(self,"Rename series","Text to add before each name:")
        if ok and prefix:
            for row in range(self.table_series.rowCount()):
                item=self.table_series.item(row,3)
                self.table_series.setItem(row,3,QTableWidgetItem(prefix+(item.text() if item else "")))

    def _preset_add_suffix(self):
        suffix,ok=QInputDialog.getText(self,"Rename series","Text to add after each name:")
        if ok and suffix:
            for row in range(self.table_series.rowCount()):
                item=self.table_series.item(row,3)
                self.table_series.setItem(row,3,QTableWidgetItem((item.text() if item else "")+suffix))

    def _preset_reset_to_columns(self):
        for row,curve in enumerate(self.graph.curves):
            label=None
            if self.project:
                workbook=self.project.get_workbook(curve.source_workbook)
                sheet=next((s for s in workbook.sheets if s.name==curve.source_sheet),None) if workbook else None
                column=sheet.get_column(curve.y_col_idx) if sheet else None
                label=column.display_label if column else None
            label=label or getattr(curve,"y_col_name",None) or curve.label or f"Curve_{row+1}"
            self.table_series.setItem(row,3,QTableWidgetItem(label))
