"""Immediate, compact editing of the selected data series."""
from PyQt6.QtCore import pyqtSignal,QSignalBlocker
from PyQt6.QtWidgets import QWidget,QFormLayout,QComboBox,QLineEdit,QCheckBox,QDoubleSpinBox,QLabel,QGroupBox
from omnigraph.ui.color_field import ColorField
from omnigraph.core.plot_editing import PLOT_CHOICES, DISTRIBUTION_TYPES, change_series_plot_type, set_series_color
from omnigraph.graphing.themes import get_theme_palette
from omnigraph.ui.dialogs.dialog_layout import fold_section

class SeriesEditor(QWidget):
    changed=pyqtSignal()
    def __init__(self,graph,parent=None):
        super().__init__(parent)
        self.graph=graph
        self._loading=False
        form=QFormLayout(self)
        self.form=form
        form.setContentsMargins(0,14,0,8)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setSpacing(8)
        self.selector=QComboBox()
        self.selector.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.selector.setMinimumContentsLength(8)
        form.addRow("Data series",self.selector)
        self.plot_type=QComboBox()
        for label,value in PLOT_CHOICES:
            self.plot_type.addItem(label,value)
        form.addRow("Plot type",self.plot_type)
        self.plot_type.setToolTip("Change this series on the existing chart. Your worksheet data is preserved.")
        self.name_edit=QLineEdit()
        form.addRow("Name in legend",self.name_edit)
        self.color=ColorField(title="Series color")
        form.addRow("Line and symbol color",self.color)
        self.visible=QCheckBox("Show this series")
        form.addRow(self.visible)
        self.line_width=QDoubleSpinBox()
        self.line_width.setRange(0.1,20)
        self.line_width.setSingleStep(0.2)
        self.line_width.setSuffix(" pt")
        form.addRow("Line width",self.line_width)
        self.line_style=QComboBox()
        for label,value in [("Solid","-"),("Dashed","--"),("Dotted",":"),("Dash-dot","-."),("None","none")]:
            self.line_style.addItem(label,value)
        form.addRow("Line style",self.line_style)
        self.marker=QComboBox()
        for label,value in [("None","none"),("Circle","o"),("Square","s"),("Triangle","^"),("Diamond","D"),("Plus","+"),("Cross","x"),("Star","*")]:
            self.marker.addItem(label,value)
        form.addRow("Symbol",self.marker)
        self.marker_size=QDoubleSpinBox()
        self.marker_size.setRange(0.1,50)
        self.marker_size.setSuffix(" pt")
        form.addRow("Symbol size",self.marker_size)
        self.marker_fill=ColorField(title="Symbol fill color",allow_transparent=True)
        self.marker_edge=ColorField(title="Symbol outline color",allow_transparent=True)
        self.symbol_options=QGroupBox()
        symbol_form=QFormLayout(self.symbol_options)
        symbol_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        symbol_form.addRow("Fill",self.marker_fill)
        symbol_form.addRow("Outline",self.marker_edge)
        self.symbol_toggle,_=fold_section(self.symbol_options,"Symbol colors")
        form.addRow(self.symbol_options)
        self.hint=QLabel()
        self.hint.setWordWrap(True)
        self.hint.setProperty("role","muted")
        form.addRow(self.hint)
        self.selector.currentIndexChanged.connect(self._load_curve)
        self.plot_type.currentIndexChanged.connect(self._change_plot_type)
        self.name_edit.editingFinished.connect(self._apply)
        self.color.colorChanged.connect(self._apply)
        self.visible.toggled.connect(self._apply)
        self.line_width.valueChanged.connect(self._apply)
        self.marker.currentIndexChanged.connect(self._apply)
        self.marker_size.valueChanged.connect(self._apply)
        self.line_style.currentIndexChanged.connect(self._apply)
        self.marker_fill.colorChanged.connect(self._apply)
        self.marker_edge.colorChanged.connect(self._apply)
        self.sync()

    def sync(self):
        self._loading=True
        current_id=self.selector.currentData()
        expected=[(c.label or f"Series {i+1}",c.id) for i,c in enumerate(self.graph.curves)]
        actual=[(self.selector.itemText(i),self.selector.itemData(i)) for i in range(self.selector.count())]
        if expected!=actual:
            blocker=QSignalBlocker(self.selector)
            self.selector.clear()
            for label,curve_id in expected:
                self.selector.addItem(label,curve_id)
            selected=self.selector.findData(current_id)
            self.selector.setCurrentIndex(max(0,selected) if expected else -1)
            del blocker
        self._loading=False
        self._load_curve()

    def current_curve(self):
        curve_id=self.selector.currentData()
        return next((c for c in self.graph.curves if c.id==curve_id),None)

    def _load_curve(self,*_):
        if self._loading:
            return
        self._loading=True
        curve=self.current_curve()
        controls=(self.plot_type,self.name_edit,self.color,self.visible,self.line_width,self.marker,self.marker_size,self.line_style,self.marker_fill,self.marker_edge)
        for control in controls:
            control.setEnabled(curve is not None)
        if curve:
            supported=self.plot_type.findData(curve.plot_type)
            self.form.setRowVisible(self.plot_type,supported>=0)
            if supported>=0:
                self.plot_type.setCurrentIndex(supported)
            self.name_edit.setText(curve.label or "")
            self.color.set_color(curve.color)
            self.visible.setChecked(curve.visible)
            self.line_width.setValue(curve.line_width)
            self.line_style.setCurrentIndex(max(0,self.line_style.findData(curve.line_style)))
            self.marker_fill.set_color(curve.marker_face_color)
            self.marker_edge.set_color(curve.marker_edge_color)
            index=self.marker.findData(curve.marker or "none")
            if index<0:
                self.marker.addItem(str(curve.marker),curve.marker)
                index=self.marker.count()-1
            self.marker.setCurrentIndex(index)
            self.marker_size.setValue(curve.marker_size)
            has_lines=curve.plot_type in ("line","line_symbol","step","spline","area","errorbar")
            has_symbols=curve.plot_type in ("scatter","line_symbol","errorbar","spline")
            self.line_width.setEnabled(has_lines)
            self.line_style.setEnabled(has_lines and curve.plot_type!="errorbar")
            self.marker_fill.setEnabled(has_symbols)
            self.marker_edge.setEnabled(has_symbols)
            self.marker.setEnabled(has_symbols)
            self.marker_size.setEnabled(has_symbols and curve.marker not in (None,"none",""))
            self.form.setRowVisible(self.line_width,has_lines)
            self.form.setRowVisible(self.line_style,has_lines and curve.plot_type!="errorbar")
            self.form.setRowVisible(self.marker,has_symbols)
            self.form.setRowVisible(self.marker_size,has_symbols and curve.marker not in (None,"none",""))
            self.form.setRowVisible(self.symbol_options,has_symbols)
            if curve.plot_type=="histogram":
                note="Histogram shows the frequency of Y values; the source X values are kept for other plot types."
            elif curve.plot_type in DISTRIBUTION_TYPES:
                note="Each series summarizes its Y values as a group; the source X values are kept."
            elif curve.plot_type=="errorbar" and curve.y_err_col_idx is None:
                note="No error column is linked, so only symbols are shown."
            else:
                note="Changes update this chart immediately without changing the worksheet."
            self.hint.setText(note)
        else:
            self.hint.setText("Add a data series to start styling this figure.")
        self._loading=False

    def _change_plot_type(self,*_):
        if self._loading:
            return
        curve=self.current_curve()
        if curve is not None:
            change_series_plot_type(curve,self.plot_type.currentData())
            self._load_curve()
            self.changed.emit()

    def _apply(self,*_):
        if self._loading:
            return
        curve=self.current_curve()
        if curve is None:
            return
        curve.label=self.name_edit.text().strip() or "Series"
        new_color=self.color.color()
        curve.visible=self.visible.isChecked()
        if self.line_width.isEnabled():
            curve.line_width=self.line_width.value()
            curve.line_style=self.line_style.currentData()
        if self.marker.isEnabled():
            curve.marker=self.marker.currentData()
            curve.marker_size=self.marker_size.value()
            curve.marker_face_color=self.marker_fill.color()
            curve.marker_edge_color=self.marker_edge.color()
        palette=get_theme_palette(self.graph.theme)
        effective=palette[self.graph.curves.index(curve)%len(palette)] if curve.color=="auto" else curve.color
        set_series_color(curve,new_color,effective)
        self.changed.emit()
