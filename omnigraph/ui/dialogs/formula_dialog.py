"""
Set Column Values dialog (Origin-style formula evaluator with assistant keypad, presets, and live preview).
"""

import re
from typing import Optional, List
import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialogButtonBox, QMessageBox, QGroupBox, QWidget, QScrollArea, QFrame,
    QTabWidget, QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, QTimer, QEvent
from PyQt6.QtGui import QFont, QColor
from omnigraph.core.worksheet import Worksheet
from omnigraph.core.column_formula import FormulaEvaluator
from omnigraph.core.undo_manager import FormulaCommand


class FormulaDialog(QDialog):
    """
    OriginLab-style 'Set Column Values' dialog with:
      - Common scientific formula presets (scaling, normalization, z-score, log, diff, etc.)
      - Clickable column insertion buttons (col(A), col(B)...)
      - Interactive math keypad (operators, trigonometric, logarithmic, statistics)
      - Real-time debounced live preview table showing input columns and calculated output
      - Native QUndoStack support for instant undo (Ctrl+Z)
    """

    PRESET_TEMPLATES = [
        ("-- Select a Quick Formula Template --", ""),
        ("Linear Scaling: 2.0 * col(A) + 5.0", "2.0 * col({col}) + 5.0"),
        ("Normalize [0 to 1]: norm(col(A))", "norm(col({col}))"),
        ("Standardize (Z-Score): zscore(col(A))", "zscore(col({col}))"),
        ("Baseline Subtraction: col(A) - min(col(A))", "col({col}) - min(col({col}))"),
        ("Log10 Transform: log10(col(A))", "log10(col({col}))"),
        ("Natural Log (ln): ln(col(A))", "ln(col({col}))"),
        ("Square Root: sqrt(col(A))", "sqrt(col({col}))"),
        ("Exponential: exp(col(A))", "exp(col({col}))"),
        ("Power of 2: col(A)^2", "col({col})^2"),
        ("Percentage of Total: (col(A) / sum(col(A))) * 100", "(col({col}) / sum(col({col}))) * 100"),
        ("First Difference / Derivative: diff(col(A))", "diff(col({col}))"),
        ("Cumulative Sum: cumsum(col(A))", "cumsum(col({col}))"),
        ("Sequence Generator: (i - 1) * 0.1", "(i - 1) * 0.1"),
        ("Add Gaussian Noise: col(A) + normal(0, 0.05, n)", "col({col}) + normal(0, 0.05, n)"),
    ]

    def __init__(self, worksheet: Worksheet, target_col_idx: int = 0, undo_stack=None, parent=None):
        super().__init__(parent)
        self.worksheet = worksheet
        self.target_col_idx = target_col_idx
        self.undo_stack = undo_stack
        self.setWindowTitle("Set Column Values (Formula)")
        self.resize(720, 580)
        self.setMinimumSize(640, 480)

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(120)
        self._debounce_timer.timeout.connect(self._update_live_preview)

        self._init_ui()
        self._update_live_preview()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(14, 12, 14, 12)

        app = QApplication.instance()
        is_dark = getattr(app, "is_dark_theme", False) or "background-color: #181825" in (app.styleSheet() if app else "")

        # 1. Target Column & Scope
        top_group = QGroupBox("Target Column and Scope")
        top_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        top_layout = QGridLayout(top_group)
        top_layout.setSpacing(8)

        lbl_target = QLabel("Target Column:")
        lbl_target.setStyleSheet("font-weight: 600;")
        top_layout.addWidget(lbl_target, 0, 0)

        self.combo_target = QComboBox()
        self.combo_target.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_target.setMinimumContentsLength(8)
        self.combo_target.setStyleSheet("padding: 4px 8px; font-weight: 600;")
        for i, c in enumerate(self.worksheet.columns):
            label = f"Col({c.name}) - {c.display_label}" if c.long_name else f"Col({c.name})"
            self.combo_target.addItem(label, i)
        target_idx = max(0, min(self.target_col_idx, self.worksheet.column_count() - 1))
        self.combo_target.setCurrentIndex(target_idx)
        self.combo_target.currentIndexChanged.connect(self._on_target_col_changed)
        top_layout.addWidget(self.combo_target, 0, 1)

        lbl_scope = QLabel("Row Scope:")
        lbl_scope.setStyleSheet("font-weight: 600;")
        top_layout.addWidget(lbl_scope, 0, 2)

        self.combo_scope = QComboBox()
        self.combo_scope.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_scope.setMinimumContentsLength(8)
        self.combo_scope.setStyleSheet("padding: 4px 8px;")
        self.combo_scope.addItem("All Active Rows (1..N)", None)
        self.combo_scope.addItem("First 50 Rows", 50)
        self.combo_scope.addItem("First 100 Rows", 100)
        self.combo_scope.addItem("First 500 Rows", 500)
        self.combo_scope.currentIndexChanged.connect(self._trigger_preview)
        top_layout.addWidget(self.combo_scope, 0, 3)

        lbl_preset = QLabel("Template:")
        lbl_preset.setStyleSheet("font-weight: 600;")
        top_layout.addWidget(lbl_preset, 1, 0)

        self.combo_presets = QComboBox()
        self.combo_presets.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_presets.setMinimumContentsLength(10)
        self.combo_presets.setStyleSheet("padding: 4px 8px;")
        for title, _ in self.PRESET_TEMPLATES:
            self.combo_presets.addItem(title)
        self.combo_presets.currentIndexChanged.connect(self._on_preset_selected)
        top_layout.addWidget(self.combo_presets, 1, 1, 1, 3)

        main_layout.addWidget(top_group)

        # 2. Formula Expression
        formula_group = QGroupBox("Formula Expression")
        formula_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        formula_layout = QVBoxLayout(formula_group)
        formula_layout.setSpacing(8)

        formula_header = QLabel("Enter equation: (supports col(A), A, B, i (row 1..N), ^ for power, sin, exp, log10, norm, etc.)")
        formula_header.setWordWrap(True)
        formula_header.setStyleSheet("font-weight: 500;")
        formula_layout.addWidget(formula_header)

        self.txt_formula = QLineEdit()
        self.txt_formula.setObjectName("FormulaInput")
        current_col = self.worksheet.get_column(target_idx)
        if current_col and current_col.formula:
            self.txt_formula.setText(current_col.formula)
        else:
            first_col_name = self.worksheet.columns[0].name if self.worksheet.columns else "A"
            self.txt_formula.setText(f"col({first_col_name}) * 2.0")

        self.txt_formula.textChanged.connect(self._trigger_preview)
        formula_layout.addWidget(self.txt_formula)

        # Column Insertion Strip
        col_strip_layout = QHBoxLayout()
        col_strip_layout.setSpacing(6)
        lbl_insert = QLabel("Insert Column:")
        lbl_insert.setStyleSheet("font-weight: bold;")
        col_strip_layout.addWidget(lbl_insert)

        scroll_cols = QScrollArea()
        scroll_cols.setFixedHeight(36)
        scroll_cols.setWidgetResizable(True)
        scroll_cols.setFrameShape(QFrame.Shape.NoFrame)
        cols_container = QWidget()
        cols_btn_layout = QHBoxLayout(cols_container)
        cols_btn_layout.setContentsMargins(0, 0, 0, 0)
        cols_btn_layout.setSpacing(6)

        self._col_buttons = []
        for col in self.worksheet.columns:
            btn = QPushButton(f"+ Col({col.name})")
            btn.setToolTip(f"Insert col({col.name}) into formula [Role: {col.role.value}]")
            btn.clicked.connect(lambda checked, name=col.name: self._insert_token(f"col({name})"))
            cols_btn_layout.addWidget(btn)
            self._col_buttons.append(btn)

        cols_btn_layout.addStretch()
        scroll_cols.setWidget(cols_container)
        col_strip_layout.addWidget(scroll_cols)
        formula_layout.addLayout(col_strip_layout)

        # Basic Operators row - directly visible
        r_ops = QHBoxLayout()
        r_ops.setSpacing(5)
        lbl_op = QLabel("Operators:")
        lbl_op.setStyleSheet("font-weight: bold;")
        r_ops.addWidget(lbl_op)
        operators = [
            ("+", "+"), ("-", "-"), ("*", "*"), ("/", "/"), ("^ (Power)", "^"),
            ("(", "("), (")", ")"), ("i (Row)", "i"), ("pi", "pi"), ("e", "e")
        ]
        self._op_buttons = []
        for label, token in operators:
            b = QPushButton(label)
            b.clicked.connect(lambda checked, t=token: self._insert_token(t))
            r_ops.addWidget(b)
            self._op_buttons.append(b)
        r_ops.addStretch()
        formula_layout.addLayout(r_ops)

        # Tabs for Functions and Transforms
        keypad_tabs = QTabWidget()

        # Tab 1: Math & Trig Functions (2 rows of 6)
        w_fn = QWidget()
        l_fn = QGridLayout(w_fn)
        l_fn.setSpacing(6)
        l_fn.setContentsMargins(2, 2, 2, 2)
        functions1 = [
            ("sin", "sin()"), ("cos", "cos()"), ("tan", "tan()"),
            ("asin", "asin()"), ("acos", "acos()"), ("atan", "atan()"),
            ("exp", "exp()"), ("ln", "ln()"), ("log10", "log10()"),
            ("sqrt", "sqrt()"), ("x² (Square)", "()^2"), ("abs", "abs()")
        ]
        self._math_buttons = []
        for idx, (label, snippet) in enumerate(functions1):
            r = idx // 6
            c = idx % 6
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked, s=snippet: self._insert_function_snippet(s))
            l_fn.addWidget(btn, r, c)
            self._math_buttons.append(btn)
        keypad_tabs.addTab(w_fn, "Math & Trig Functions")

        # Tab 2: Statistics & Transforms (2 rows of 5)
        w_tr = QWidget()
        l_tr = QGridLayout(w_tr)
        l_tr.setSpacing(6)
        l_tr.setContentsMargins(2, 2, 2, 2)
        functions2 = [
            ("mean", "mean()"), ("std", "std()"), ("min", "min()"),
            ("max", "max()"), ("sum", "sum()"),
            ("diff (Difference)", "diff()"), ("cumsum (Integral)", "cumsum()"),
            ("norm [0 to 1]", "norm()"), ("zscore (Standardize)", "zscore()")
        ]
        for idx, (label, snippet) in enumerate(functions2):
            r = idx // 5
            c = idx % 5
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked, s=snippet: self._insert_function_snippet(s))
            l_tr.addWidget(btn, r, c)
            self._math_buttons.append(btn)
        keypad_tabs.addTab(w_tr, "Statistics & Transforms")

        self._apply_keypad_theme()

        formula_layout.addWidget(keypad_tabs)
        main_layout.addWidget(formula_group)

        # 3. Live Interactive Preview Table
        prev_group = QGroupBox("Live Preview (First 8 Rows)")
        prev_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        prev_layout = QVBoxLayout(prev_group)
        prev_layout.setSpacing(8)
        prev_layout.setContentsMargins(10, 10, 10, 10)

        self.table_preview = QTableWidget(8, 0)
        self.table_preview.setMinimumHeight(90)
        self.table_preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table_preview.setAlternatingRowColors(True)
        self.table_preview.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_preview.verticalHeader().setDefaultSectionSize(22)
        prev_layout.addWidget(self.table_preview, stretch=1)

        # Dedicated Status Badge below preview with guaranteed spacing and zero overlap
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setFixedHeight(30)
        self.lbl_status.setStyleSheet("font-weight: 600; padding: 4px 10px; border-radius: 4px;")
        prev_layout.addWidget(self.lbl_status, stretch=0)

        main_layout.addWidget(prev_group, stretch=1)

        # 4. Action Buttons
        button_bar = QHBoxLayout()
        btn_clear = QPushButton("Clear")
        btn_clear.setStyleSheet("padding: 5px 14px;")
        btn_clear.clicked.connect(self.txt_formula.clear)
        button_bar.addWidget(btn_clear)

        button_bar.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("padding: 5px 14px;")
        btn_cancel.clicked.connect(self.reject)
        button_bar.addWidget(btn_cancel)

        self.btn_apply = QPushButton("Apply Formula")
        self.btn_apply.setDefault(True)
        self.btn_apply.setStyleSheet(
            "padding: 6px 20px; font-weight: bold; background: #0284c7; color: white; border-radius: 4px;"
        )
        self.btn_apply.clicked.connect(self._on_accept)
        button_bar.addWidget(self.btn_apply)

        main_layout.addLayout(button_bar)

    def _on_target_col_changed(self, index: int):
        target_idx = self.combo_target.currentData()
        if target_idx is not None:
            col = self.worksheet.get_column(target_idx)
            if col and col.formula:
                self.txt_formula.setText(col.formula)
        self._trigger_preview()

    def _on_preset_selected(self, index: int):
        if index <= 0 or index >= len(self.PRESET_TEMPLATES):
            return
        _, template = self.PRESET_TEMPLATES[index]
        # Find a suitable reference column: first X or first column
        source_col = "A"
        for c in self.worksheet.columns:
            if c.name != self.combo_target.currentText():
                source_col = c.name
                break
        expr = template.replace("{col}", source_col)
        self.txt_formula.setText(expr)
        self.txt_formula.setFocus()
        self.combo_presets.setCurrentIndex(0)

    def _insert_token(self, token: str):
        self.txt_formula.insert(token)
        self.txt_formula.setFocus()

    def _insert_function_snippet(self, snippet: str):
        cursor_pos = self.txt_formula.cursorPosition()
        self.txt_formula.insert(snippet)
        # Position cursor inside parentheses if present
        if "()" in snippet:
            idx = snippet.find("()")
            self.txt_formula.setCursorPosition(cursor_pos + idx + 1)
        self.txt_formula.setFocus()

    def _trigger_preview(self):
        self._debounce_timer.start()

    def _update_live_preview(self):
        """Calculates formula result for first 8 rows and populates preview table."""
        formula_str = self.txt_formula.text().strip()
        target_idx = self.combo_target.currentData()
        if target_idx is None:
            return

        target_col = self.worksheet.get_column(target_idx)
        target_name = target_col.name if target_col else f"Col {target_idx+1}"

        # Determine target length
        scope_val = self.combo_scope.currentData()
        target_len = scope_val if scope_val is not None else None

        # Build preview columns: show other columns + calculated target column
        display_cols = []
        for idx, col in enumerate(self.worksheet.columns):
            if idx != target_idx and len(display_cols) < 3:
                display_cols.append((idx, col.name, col.to_numpy_array(length=8)))

        self.table_preview.clear()
        num_headers = len(display_cols) + 1
        self.table_preview.setColumnCount(num_headers)
        headers = [f"Col({name})" for _, name, _ in display_cols] + [f"Result: Col({target_name})"]
        self.table_preview.setHorizontalHeaderLabels(headers)

        app = QApplication.instance()
        is_dark = getattr(app, "is_dark_theme", False) or "background-color: #181825" in (app.styleSheet() if app else "")

        if not formula_str:
            self.lbl_status.setText("Enter a formula above to see live calculated preview.")
            if is_dark:
                self.lbl_status.setStyleSheet("color: #a6adc8; background: #1e1e2e; border: 1px solid #313244; border-radius: 4px; padding: 4px 10px; font-weight: 500;")
            else:
                self.lbl_status.setStyleSheet("color: #475569; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px 10px; font-weight: 500;")
            self.btn_apply.setEnabled(False)
            return

        try:
            result = FormulaEvaluator.evaluate(formula_str, self.worksheet, target_length=target_len)
            preview_rows = min(8, len(result))

            for r in range(preview_rows):
                col_offset = 0
                for _, _, arr in display_cols:
                    val_str = f"{arr[r]:.4g}" if r < len(arr) and not np.isnan(arr[r]) else "--"
                    item = QTableWidgetItem(val_str)
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table_preview.setItem(r, col_offset, item)
                    col_offset += 1

                res_val = result[r]
                if np.isnan(res_val):
                    res_str = "NaN"
                elif np.isinf(res_val):
                    res_str = "Inf"
                else:
                    res_str = f"{res_val:.4g}"
                res_item = QTableWidgetItem(res_str)
                res_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                res_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if is_dark:
                    res_item.setBackground(QColor(49, 50, 68))
                    res_item.setForeground(QColor(137, 180, 250))
                else:
                    res_item.setBackground(QColor(240, 249, 255))
                    res_item.setForeground(QColor(2, 132, 199))
                res_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                self.table_preview.setItem(r, col_offset, res_item)

            self.lbl_status.setText(f"✓ Formula valid: Successfully computed {len(result)} rows.")
            if is_dark:
                self.lbl_status.setStyleSheet("color: #4ade80; background: #064e3b; border: 1px solid #059669; border-radius: 4px; padding: 4px 10px; font-weight: bold;")
            else:
                self.lbl_status.setStyleSheet("color: #166534; background: #ecfdf5; border: 1px solid #86efac; border-radius: 4px; padding: 4px 10px; font-weight: bold;")
            self.btn_apply.setEnabled(True)

        except Exception as e:
            err_msg = str(e)
            if "syntax" in err_msg.lower():
                self.lbl_status.setText("Incomplete formula syntax (continue typing...)")
                if is_dark:
                    self.lbl_status.setStyleSheet("color: #a6adc8; background: #1e1e2e; border: 1px solid #313244; border-radius: 4px; padding: 4px 10px; font-weight: 500;")
                else:
                    self.lbl_status.setStyleSheet("color: #475569; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px 10px; font-weight: 500;")
            else:
                self.lbl_status.setText(f"⚠ Error: {err_msg}")
                if is_dark:
                    self.lbl_status.setStyleSheet("color: #f87171; background: #450a0a; border: 1px solid #dc2626; border-radius: 4px; padding: 4px 10px; font-weight: bold;")
                else:
                    self.lbl_status.setStyleSheet("color: #991b1b; background: #fef2f2; border: 1px solid #fca5a5; border-radius: 4px; padding: 4px 10px; font-weight: bold;")
            self.btn_apply.setEnabled(False)

    def _on_accept(self):
        formula_str = self.txt_formula.text().strip()
        target_idx = self.combo_target.currentData()
        if not formula_str or target_idx is None:
            QMessageBox.warning(self, "Warning", "Please provide a valid formula expression.")
            return

        target_col = self.worksheet.get_column(target_idx)
        if not target_col:
            return

        scope_val = self.combo_scope.currentData()

        try:
            new_data = FormulaEvaluator.evaluate(formula_str, self.worksheet, target_length=scope_val)
            new_data_list = [None if (np.isnan(v) or np.isinf(v)) else float(v) for v in new_data]

            old_data = list(target_col.data)
            old_formula = target_col.formula

            if self.undo_stack is not None:
                parent_sw = self.parent()
                cb = parent_sw.refresh_view if parent_sw and hasattr(parent_sw, "refresh_view") else None
                cmd = FormulaCommand(
                    self.worksheet,
                    target_idx,
                    old_formula,
                    old_data,
                    formula_str,
                    new_data_list,
                    callback=cb,
                )
                self.undo_stack.push(cmd)
            else:
                target_col.formula = formula_str
                target_col.data = new_data_list

            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Formula Error", f"Failed to apply formula:\n{e}")

    def _apply_keypad_theme(self):
        app = QApplication.instance()
        is_dark = getattr(app, "is_dark_theme", False) or "background-color: #181825" in (app.styleSheet() if app else "")
        if is_dark:
            btn_col_style = (
                "QPushButton { padding: 4px 12px; font-weight: bold; "
                "background: #1e293b; border: 1px solid #38bdf8; border-radius: 4px; color: #38bdf8; min-height: 24px; } "
                "QPushButton:hover { background: #0369a1; color: #ffffff; }"
            )
            btn_style_ops = (
                "QPushButton { padding: 4px 9px; font-weight: bold; "
                "background: #313244; border: 1px solid #45475a; border-radius: 4px; color: #cdd6f4; min-height: 25px; min-width: 32px; } "
                "QPushButton:hover { background: #45475a; border-color: #89b4fa; color: #89b4fa; }"
            )
            btn_style_math = (
                "QPushButton { padding: 4px 10px; font-weight: 600; "
                "background: #313244; border: 1px solid #45475a; border-radius: 4px; color: #cdd6f4; min-height: 26px; } "
                "QPushButton:hover { background: #45475a; border-color: #89b4fa; color: #89b4fa; font-weight: bold; }"
            )
        else:
            btn_col_style = (
                "QPushButton { padding: 4px 12px; font-weight: bold; "
                "background: #e0f2fe; border: 1px solid #7dd3fc; border-radius: 4px; color: #0369a1; min-height: 24px; } "
                "QPushButton:hover { background: #bae6fd; border-color: #0284c7; }"
            )
            btn_style_ops = (
                "QPushButton { padding: 4px 9px; font-weight: bold; "
                "background: #f1f5f9; border: 1px solid #94a3b8; border-radius: 4px; color: #0f172a; min-height: 25px; min-width: 32px; } "
                "QPushButton:hover { background: #e2e8f0; border-color: #0284c7; color: #0284c7; }"
            )
            btn_style_math = (
                "QPushButton { padding: 4px 10px; font-weight: 600; "
                "background: #ffffff; border: 1px solid #94a3b8; border-radius: 4px; color: #0f172a; min-height: 26px; } "
                "QPushButton:hover { background: #e0f2fe; border-color: #0284c7; color: #0284c7; font-weight: bold; }"
            )

        for btn in getattr(self, "_col_buttons", []):
            btn.setStyleSheet(btn_col_style)
        for btn in getattr(self, "_op_buttons", []):
            btn.setStyleSheet(btn_style_ops)
        for btn in getattr(self, "_math_buttons", []):
            btn.setStyleSheet(btn_style_math)
