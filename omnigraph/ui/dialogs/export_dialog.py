"""
High-resolution graph export dialog for Graffy.
Provides publication-standard presets (Nature/Science single column, double column, slides),
custom dimensions in inches/cm/pixels, aspect ratio lock, DPI selection, tight bounding crop,
live thumbnail preview, and native clipboard copying.
"""

import os
from typing import Tuple, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QGroupBox, QComboBox, QDoubleSpinBox, QSpinBox, QCheckBox,
    QLineEdit, QPushButton, QLabel, QFileDialog, QMessageBox,
    QFrame, QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, QByteArray, QTimer, QSize, QMimeData
from PyQt6.QtGui import QImage, QPixmap, QIcon, QClipboard, QFont
from omnigraph.graphing.plot_manager import PlotManager


class ExportDialog(QDialog):
    """Dialog for exporting publication-quality graph figures with dimension controls and preview."""

    PRESETS = [
        ("Publication Standard (7.0 x 5.0 in)", 7.0, 5.0),
        ("Journal Single Column (3.5 x 2.8 in)", 3.5, 2.8),
        ("Journal Double Column (7.0 x 4.5 in)", 7.0, 4.5),
        ("Presentation Slide 16:9 (10.0 x 5.62 in)", 10.0, 5.625),
        ("Presentation Slide 4:3 (8.0 x 6.0 in)", 8.0, 6.0),
        ("Square Figure (6.0 x 6.0 in)", 6.0, 6.0),
        ("Current Screen Window", None, None),
        ("Custom Dimensions...", None, None),
    ]

    def __init__(self, plot_manager: PlotManager, parent=None):
        super().__init__(parent)
        self.plot_manager = plot_manager
        self.setWindowTitle("Save or copy graph")
        self.resize(760, 560)
        self.setMinimumSize(660, 480)

        # Internal state in inches
        self._width_in = 7.0
        self._height_in = 5.0
        self._aspect_ratio = 7.0 / 5.0
        self._updating_controls = False

        self._init_ui()
        self._apply_preset(0)
        self._update_preview()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        # Header Banner
        app = QApplication.instance()
        is_dark = getattr(app, "is_dark_theme", False) or "background-color: #181825" in (app.styleSheet() if app else "")
        sub_color = "#a6adc8" if is_dark else "#475569"
        border_color = "#313244" if is_dark else "#e2e8f0"
        header = QLabel(
            f"<h3 style='margin:0; color:#4f46e5;'>Save your graph</h3>"
            f"<span style='color:{sub_color};'>Choose an image format and where to save it. "
            "Use PNG for images, or PDF and SVG for scalable figures.</span>"
        )
        header.setWordWrap(True)
        header.setStyleSheet(f"padding-bottom: 4px; border-bottom: 1px solid {border_color};")
        main_layout.addWidget(header)

        # Content Layout (Split Left: Controls, Right: Live Preview)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # --- LEFT PANEL: Controls ---
        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)

        # 1. Dimensions Group
        grp_dim = QGroupBox("Target Dimensions and Sizing")
        dim_layout = QGridLayout(grp_dim)
        dim_layout.setSpacing(8)

        # Preset
        dim_layout.addWidget(QLabel("Preset:"), 0, 0)
        self.combo_presets = QComboBox()
        self.combo_presets.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_presets.setMinimumContentsLength(10)
        for label, w, h in self.PRESETS:
            self.combo_presets.addItem(label)
        self.combo_presets.currentIndexChanged.connect(self._on_preset_changed)
        dim_layout.addWidget(self.combo_presets, 0, 1, 1, 2)

        # Units
        dim_layout.addWidget(QLabel("Units:"), 1, 0)
        self.combo_units = QComboBox()
        self.combo_units.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_units.setMinimumContentsLength(8)
        self.combo_units.addItems(["Inches (in)", "Centimeters (cm)", "Pixels (px)"])
        self.combo_units.currentIndexChanged.connect(self._on_units_changed)
        dim_layout.addWidget(self.combo_units, 1, 1, 1, 2)

        # Width
        dim_layout.addWidget(QLabel("Width:"), 2, 0)
        self.spn_width = QDoubleSpinBox()
        self.spn_width.setRange(0.5, 100.0)
        self.spn_width.setSingleStep(0.5)
        self.spn_width.setDecimals(2)
        self.spn_width.setValue(7.0)
        self.spn_width.valueChanged.connect(self._on_width_changed)
        dim_layout.addWidget(self.spn_width, 2, 1, 1, 2)

        # Height
        dim_layout.addWidget(QLabel("Height:"), 3, 0)
        self.spn_height = QDoubleSpinBox()
        self.spn_height.setRange(0.5, 100.0)
        self.spn_height.setSingleStep(0.5)
        self.spn_height.setDecimals(2)
        self.spn_height.setValue(5.0)
        self.spn_height.valueChanged.connect(self._on_height_changed)
        dim_layout.addWidget(self.spn_height, 3, 1, 1, 2)

        # Lock Aspect Ratio
        self.chk_lock_aspect = QCheckBox("Lock Aspect Ratio")
        self.chk_lock_aspect.setChecked(True)
        self.chk_lock_aspect.toggled.connect(self._on_lock_aspect_toggled)
        dim_layout.addWidget(self.chk_lock_aspect, 4, 0, 1, 3)

        # Dimension summary badge
        app = QApplication.instance()
        is_dark = getattr(app, "is_dark_theme", False) or "background-color: #181825" in (app.styleSheet() if app else "")
        self.lbl_dim_summary = QLabel()
        self.lbl_dim_summary.setWordWrap(True)
        self.lbl_dim_summary.setMinimumHeight(32)
        if is_dark:
            self.lbl_dim_summary.setStyleSheet(
                "background: #1e1e2e; color: #cdd6f4; border: 1px solid #313244; padding: 4px 8px; "
                "border-radius: 4px; font-weight: 600; font-family: monospace; font-size: 11px;"
            )
        else:
            self.lbl_dim_summary.setStyleSheet(
                "background: #f1f5f9; color: #0f172a; padding: 4px 8px; "
                "border-radius: 4px; font-weight: 600; font-family: monospace; font-size: 11px;"
            )
        dim_layout.addWidget(self.lbl_dim_summary, 5, 0, 1, 3)

        left_panel.addWidget(grp_dim)

        # 2. Format & Quality Group
        grp_fmt = QGroupBox("Format and Resolution")
        fmt_form = QFormLayout(grp_fmt)
        fmt_form.setSpacing(8)

        # File format
        self.combo_format = QComboBox()
        self.combo_format.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_format.setMinimumContentsLength(8)
        self.combo_format.addItem("PNG Image (*.png)", "png")
        self.combo_format.addItem("PDF Vector (*.pdf)", "pdf")
        self.combo_format.addItem("SVG Scalable Vector (*.svg)", "svg")
        self.combo_format.addItem("TIFF High-Resolution (*.tiff)", "tiff")
        self.combo_format.addItem("JPEG Image (*.jpg)", "jpg")
        self.combo_format.currentIndexChanged.connect(self._on_format_changed)
        fmt_form.addRow("Format:", self.combo_format)

        # Resolution DPI
        self.combo_dpi = QComboBox()
        self.combo_dpi.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_dpi.setMinimumContentsLength(10)
        self.combo_dpi.addItem("300 DPI - Standard Publication Quality", 300)
        self.combo_dpi.addItem("600 DPI - High-Resolution Print / Archival", 600)
        self.combo_dpi.addItem("150 DPI - Screen / Presentation", 150)
        self.combo_dpi.addItem("100 DPI - Draft / Web", 100)
        self.combo_dpi.addItem("Custom DPI...", -1)
        self.combo_dpi.currentIndexChanged.connect(self._on_dpi_changed)
        fmt_form.addRow("Resolution:", self.combo_dpi)

        # Custom DPI spinbox
        self.spn_custom_dpi = QSpinBox()
        self.spn_custom_dpi.setRange(50, 2400)
        self.spn_custom_dpi.setSingleStep(50)
        self.spn_custom_dpi.setValue(300)
        self.spn_custom_dpi.setEnabled(False)
        self.spn_custom_dpi.valueChanged.connect(self._on_custom_dpi_changed)
        fmt_form.addRow("Custom DPI:", self.spn_custom_dpi)

        # Tight Bounding Box & Transparent
        self.chk_tight = QCheckBox("Tight Bounding Box (Trim margins)")
        self.chk_tight.setChecked(True)
        self.chk_tight.toggled.connect(self._update_preview)
        fmt_form.addRow(self.chk_tight)

        self.chk_transparent = QCheckBox("Transparent Background")
        fmt_form.addRow(self.chk_transparent)

        fmt_form.setRowVisible(self.spn_custom_dpi, False)
        self.combo_dpi.currentIndexChanged.connect(lambda: fmt_form.setRowVisible(self.spn_custom_dpi, self.combo_dpi.currentData() == -1))
        grp_fmt.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        left_panel.addWidget(grp_fmt)
        content_layout.addLayout(left_panel, stretch=3)

        # --- RIGHT PANEL: Live Visual Preview ---
        right_panel = QVBoxLayout()
        grp_preview = QGroupBox("Figure Preview")
        prev_layout = QVBoxLayout(grp_preview)
        prev_layout.setSpacing(8)

        self.lbl_preview_img = QLabel("Generating preview...")
        self.lbl_preview_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview_img.setMinimumSize(280, 220)
        self.lbl_preview_img.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.lbl_preview_img.setStyleSheet(
            f"background: {'#1e1e2e' if is_dark else '#ffffff'}; color: {'#cdd6f4' if is_dark else '#0f172a'}; border: 1px solid {'#45475a' if is_dark else '#cbd5e1'}; border-radius: 6px; padding: 4px;"
        )
        prev_layout.addWidget(self.lbl_preview_img)

        self.lbl_preview_hint = QLabel("Scaled thumbnail representation")
        self.lbl_preview_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview_hint.setStyleSheet(f"color: {'#a6adc8' if is_dark else '#64748b'}; font-size: 11px;")
        prev_layout.addWidget(self.lbl_preview_hint)

        btn_refresh_prev = QPushButton("Refresh Preview")
        btn_refresh_prev.clicked.connect(self._update_preview)
        prev_layout.addWidget(btn_refresh_prev)

        self.lbl_preview_img.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.lbl_preview_img.setMaximumHeight(220)
        grp_preview.setMaximumHeight(300)
        right_panel.addWidget(grp_preview)
        content_layout.addLayout(right_panel, stretch=2)

        main_layout.addLayout(content_layout)

        # --- Destination File Path ---
        path_group = QGroupBox("Destination File")
        path_layout = QHBoxLayout(path_group)
        self.txt_path = QLineEdit()
        # Clean default name based on model title
        import re
        clean_title = re.sub(r'[<>:"/\\|?*]', "_", self.plot_manager.model.title or "Graph").strip(" .").replace(" ", "_") or "Graph"
        from PyQt6.QtCore import QStandardPaths
        destination = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation) or os.path.expanduser("~")
        self.txt_path.setText(os.path.join(destination, f"{clean_title}.png"))
        path_layout.addWidget(self.txt_path)

        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_path)
        path_layout.addWidget(btn_browse)
        main_layout.insertWidget(1, path_group)

        # --- Bottom Actions ---
        bottom_bar = QHBoxLayout()

        self.btn_copy_clipboard = QPushButton("Copy image")
        self.btn_copy_clipboard.setToolTip("Copy figure directly to system clipboard at current dimensions and DPI")
        if is_dark:
            self.btn_copy_clipboard.setStyleSheet("")
        else:
            self.btn_copy_clipboard.setStyleSheet("")
        self.btn_copy_clipboard.clicked.connect(self._on_copy_to_clipboard)
        bottom_bar.addWidget(self.btn_copy_clipboard)

        self.lbl_copy_status = QLabel("")
        self.lbl_copy_status.setStyleSheet("color: #16a34a; font-weight: bold; padding-left: 8px;")
        bottom_bar.addWidget(self.lbl_copy_status)

        bottom_bar.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        bottom_bar.addWidget(btn_cancel)

        self.btn_export = QPushButton("Save graph")
        self.btn_export.setDefault(True)
        self.btn_export.setProperty("role","primary")
        self.btn_export.setStyleSheet("")
        self.btn_export.clicked.connect(self._on_export)
        bottom_bar.addWidget(self.btn_export)

        main_layout.addLayout(bottom_bar)
        from omnigraph.ui.dialogs.dialog_layout import fold_section, finish_dialog
        self.sizing_toggle, self.sizing_options = fold_section(grp_dim, "Change figure size")
        self.lbl_preview_img.setMinimumSize(120, 100)
        self.lbl_copy_status.setWordWrap(True)
        finish_dialog(self)

    def get_dpi(self) -> int:
        dpi_val = self.combo_dpi.currentData()
        if dpi_val == -1:
            return self.spn_custom_dpi.value()
        return dpi_val

    def get_target_dimensions_in(self) -> Tuple[float, float]:
        return self._width_in, self._height_in

    def _apply_preset(self, index: int):
        if index < 0 or index >= len(self.PRESETS):
            return
        _, w, h = self.PRESETS[index]
        if w is not None and h is not None:
            self._width_in = float(w)
            self._height_in = float(h)
            self._aspect_ratio = self._width_in / self._height_in
        elif self.PRESETS[index][0] == "Current Screen Window":
            fig_w, fig_h = self.plot_manager.fig.get_size_inches()
            self._width_in = float(fig_w)
            self._height_in = float(fig_h)
            self._aspect_ratio = self._width_in / self._height_in

        self._sync_spinboxes_from_inches()
        self._update_dim_summary()

    def _sync_spinboxes_from_inches(self):
        self._updating_controls = True
        unit = self.combo_units.currentText()
        dpi = self.get_dpi()

        if "Inches" in unit:
            self.spn_width.setRange(0.5, 50.0)
            self.spn_width.setSingleStep(0.25)
            self.spn_width.setDecimals(2)
            self.spn_width.setValue(self._width_in)

            self.spn_height.setRange(0.5, 50.0)
            self.spn_height.setSingleStep(0.25)
            self.spn_height.setDecimals(2)
            self.spn_height.setValue(self._height_in)

        elif "Centimeters" in unit:
            self.spn_width.setRange(1.0, 130.0)
            self.spn_width.setSingleStep(0.5)
            self.spn_width.setDecimals(2)
            self.spn_width.setValue(self._width_in * 2.54)

            self.spn_height.setRange(1.0, 130.0)
            self.spn_height.setSingleStep(0.5)
            self.spn_height.setDecimals(2)
            self.spn_height.setValue(self._height_in * 2.54)

        elif "Pixels" in unit:
            self.spn_width.setRange(100, 20000)
            self.spn_width.setSingleStep(50)
            self.spn_width.setDecimals(0)
            self.spn_width.setValue(round(self._width_in * dpi))

            self.spn_height.setRange(100, 20000)
            self.spn_height.setSingleStep(50)
            self.spn_height.setDecimals(0)
            self.spn_height.setValue(round(self._height_in * dpi))

        self._updating_controls = False

    def _on_preset_changed(self, index: int):
        if self._updating_controls:
            return
        self._apply_preset(index)
        self._update_preview()

    def _on_units_changed(self):
        self._sync_spinboxes_from_inches()

    def _on_width_changed(self, val: float):
        if self._updating_controls:
            return

        unit = self.combo_units.currentText()
        dpi = self.get_dpi()

        if "Inches" in unit:
            self._width_in = val
        elif "Centimeters" in unit:
            self._width_in = val / 2.54
        elif "Pixels" in unit:
            self._width_in = val / dpi

        if self.chk_lock_aspect.isChecked() and self._aspect_ratio > 0:
            self._height_in = self._width_in / self._aspect_ratio
            self._sync_spinboxes_from_inches()

        self._set_preset_to_custom()
        self._update_dim_summary()

    def _on_height_changed(self, val: float):
        if self._updating_controls:
            return

        unit = self.combo_units.currentText()
        dpi = self.get_dpi()

        if "Inches" in unit:
            self._height_in = val
        elif "Centimeters" in unit:
            self._height_in = val / 2.54
        elif "Pixels" in unit:
            self._height_in = val / dpi

        if self.chk_lock_aspect.isChecked() and self._height_in > 0:
            self._width_in = self._height_in * self._aspect_ratio
            self._sync_spinboxes_from_inches()

        self._set_preset_to_custom()
        self._update_dim_summary()

    def _on_lock_aspect_toggled(self, checked: bool):
        if checked and self._height_in > 0:
            self._aspect_ratio = self._width_in / self._height_in

    def _set_preset_to_custom(self):
        self._updating_controls = True
        custom_idx = len(self.PRESETS) - 1
        self.combo_presets.setCurrentIndex(custom_idx)
        self._updating_controls = False

    def _update_dim_summary(self):
        dpi = self.get_dpi()
        px_w = int(round(self._width_in * dpi))
        px_h = int(round(self._height_in * dpi))
        cm_w = self._width_in * 2.54
        cm_h = self._height_in * 2.54

        self.lbl_dim_summary.setText(
            f"Output: {px_w} x {px_h} px @ {dpi} DPI  |  {self._width_in:.2f} x {self._height_in:.2f} in ({cm_w:.1f} x {cm_h:.1f} cm)"
        )

    def _on_dpi_changed(self, index: int):
        is_custom = (self.combo_dpi.currentData() == -1)
        self.spn_custom_dpi.setEnabled(is_custom)
        if "Pixels" in self.combo_units.currentText():
            self._sync_spinboxes_from_inches()
        self._update_dim_summary()
        self._update_preview()

    def _on_custom_dpi_changed(self, val: int):
        if "Pixels" in self.combo_units.currentText():
            self._sync_spinboxes_from_inches()
        self._update_dim_summary()

    def _on_format_changed(self):
        ext = self.combo_format.currentData()
        current = self.txt_path.text()
        base, _ = os.path.splitext(current)
        self.txt_path.setText(f"{base}.{ext}")

        # Vector formats disable DPI, bitmap formats enable DPI
        is_vector = ext in ("pdf", "svg")
        self.combo_dpi.setEnabled(not is_vector)
        self.spn_custom_dpi.setEnabled(not is_vector and self.combo_dpi.currentData() == -1)

        # Transparent available for PNG, SVG, TIFF
        self.chk_transparent.setEnabled(ext in ("png", "svg", "tiff"))

    def _browse_path(self):
        ext = self.combo_format.currentData()
        filter_str = f"{ext.upper()} Files (*.{ext})"
        path, _ = QFileDialog.getSaveFileName(self, "Export Figure", self.txt_path.text(), filter_str)
        if path:
            self.txt_path.setText(path)

    def _update_preview(self):
        """Generates scaled preview thumbnail honoring user dimensions and margins."""
        try:
            pixmap = self.plot_manager.export_to_pixmap(
                dpi=100,
                width_in=self._width_in,
                height_in=self._height_in,
                tight_crop=self.chk_tight.isChecked(),
            )
            scaled = pixmap.scaled(
                self.lbl_preview_img.size() - QSize(16, 16),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.lbl_preview_img.setPixmap(scaled)
        except Exception:
            # Fallback direct preview
            try:
                pixmap = self.plot_manager.export_to_pixmap(dpi=90)
                self.lbl_preview_img.setPixmap(
                    pixmap.scaled(260, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                )
            except Exception:
                self.lbl_preview_img.setText("Preview unavailable")

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(20, self._update_preview)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(50, self._update_preview)

    def _on_copy_to_clipboard(self):
        """Copies graph to clipboard at currently configured dimensions & DPI."""
        dpi = self.get_dpi()
        tight = self.chk_tight.isChecked()
        transparent = self.chk_transparent.isChecked()

        png_bytes = self.plot_manager.export_png_bytes(
            dpi=dpi,
            transparent=transparent,
            width_in=self._width_in,
            height_in=self._height_in,
            tight_crop=tight,
        )
        if not png_bytes:
            QMessageBox.warning(self, "Copy Error", "Failed to render graph to clipboard.")
            return

        qimg = QImage()
        qimg.loadFromData(png_bytes)

        mime = QMimeData()
        mime.setImageData(qimg)
        mime.setData("image/png", QByteArray(png_bytes))

        QApplication.clipboard().setMimeData(mime, QClipboard.Mode.Clipboard)
        px_w = int(round(self._width_in * dpi))
        px_h = int(round(self._height_in * dpi))
        self.lbl_copy_status.setText(f"[OK] Copied to clipboard ({px_w} x {px_h} px)!")
        QTimer.singleShot(4000, lambda: self.lbl_copy_status.setText(""))

    def _on_export(self):
        path = self.txt_path.text().strip()
        if not path:
            QMessageBox.warning(self, "Path Error", "Please specify an export destination file path.")
            return

        if os.path.exists(path):
            answer = QMessageBox.question(self, "Replace existing file?", "A file with this name already exists. Replace it?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        dpi = self.get_dpi()
        transparent = self.chk_transparent.isChecked()
        tight = self.chk_tight.isChecked()

        try:
            self.plot_manager.export_image(
                path,
                dpi=dpi,
                transparent=transparent,
                width_in=self._width_in,
                height_in=self._height_in,
                tight_crop=tight,
            )
            px_w = int(round(self._width_in * dpi))
            px_h = int(round(self._height_in * dpi))
            QMessageBox.information(
                self,
                "Export Successful",
                f"Figure exported successfully!\n\n"
                f"Destination: {path}\n"
                f"Dimensions: {px_w} x {px_h} px @ {dpi} DPI\n"
                f"Physical Size: {self._width_in:.2f} x {self._height_in:.2f} inches"
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export figure:\n{e}")
