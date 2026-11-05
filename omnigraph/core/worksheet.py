"""
Core Worksheet, Workbook, and Column data structures.
Emulates OriginLab's multi-property column architecture:
Short Name, Long Name, Units, Comments, and Roles (X, Y, Y Error, X Error, Label, Disregard).
"""

from enum import Enum
import math
import numpy as np
import pandas as pd
from typing import List, Optional, Dict, Any, Tuple


class ColumnRole(str, Enum):
    X = "X"
    Y = "Y"
    Y_ERR = "YErr"
    X_ERR = "XErr"
    LABEL = "Label"
    DISREGARD = "Disregard"


class Column:
    """Represents a single data column in a worksheet."""

    def __init__(
        self,
        name: str = "A",
        long_name: str = "",
        units: str = "",
        comments: str = "",
        role: ColumnRole = ColumnRole.Y,
        data: Optional[List[Any]] = None,
        formula: str = "",
        masked_rows: Optional[set] = None,
    ):
        self.name = name.strip()
        self.long_name = long_name.strip()
        self.units = units.strip()
        self.comments = comments.strip()
        self.role = ColumnRole(role) if isinstance(role, str) else role
        self.data: List[Any] = list(data) if data is not None else []
        self.formula = formula.strip()
        self.masked_rows: set = set(masked_rows) if masked_rows is not None else set()

    @property
    def display_label(self) -> str:
        """Returns Origin-style formatted label: LongName (Units) or Name (Units) or Name."""
        base = self.long_name if self.long_name else self.name
        if self.units:
            return f"{base} ({self.units})"
        return base

    def mask_row(self, row: int, masked: bool = True):
        """Mask or unmask a specific row index."""
        if row is not None and row >= 0:
            if masked:
                self.masked_rows.add(int(row))
            else:
                self.masked_rows.discard(int(row))

    def is_row_masked(self, row: int) -> bool:
        """Check if a specific row is masked."""
        return int(row) in self.masked_rows if row is not None else False

    def clear_mask(self):
        """Clear all masked rows in this column."""
        self.masked_rows.clear()

    def get_value(self, row: int) -> Any:
        if row is None or not (0 <= row < len(self.data)):
            return None
        return self.data[row]

    def set_value(self, row: int, val: Any):
        if row is None:
            return
        # Grow list if row is out of bounds
        if row >= len(self.data):
            self.data.extend([None] * (row - len(self.data) + 1))
        self.data[row] = val

    def to_numpy_array(self, length: Optional[int] = None, include_masked: bool = True) -> np.ndarray:
        """Convert column data to a float numpy array, converting invalid or None to NaN.
        If include_masked is False, masked rows are also set to NaN.
        """
        target_len = length if length is not None else len(self.data)
        out = np.full(max(target_len, 0), np.nan, dtype=float)
        for i in range(min(len(self.data), target_len)):
            if not include_masked and i in self.masked_rows:
                continue
            v = self.data[i]
            if v is not None and v != "":
                try:
                    out[i] = float(v)
                except (ValueError, TypeError):
                    out[i] = np.nan
        return out

    def get_valid_numeric_pairs(self, other_col: "Column", include_masked: bool = False) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Return paired numeric (x, y) arrays and their original row indices,
        filtering out rows where either is NaN or non-numeric (and masked rows if include_masked is False).
        """
        n = max(len(self.data), len(other_col.data))
        arr_x = self.to_numpy_array(n, include_masked=include_masked)
        arr_y = other_col.to_numpy_array(n, include_masked=include_masked)
        valid = (~np.isnan(arr_x)) & (~np.isnan(arr_y))
        indices = np.where(valid)[0]
        return arr_x[valid], arr_y[valid], indices

    def get_masked_numeric_pairs(self, other_col: "Column") -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Return paired numeric (x, y) arrays and original row indices for rows
        that contain valid numeric values in both columns BUT are flagged as masked.
        """
        n = max(len(self.data), len(other_col.data))
        raw_x = self.to_numpy_array(n, include_masked=True)
        raw_y = other_col.to_numpy_array(n, include_masked=True)
        valid_nums = (~np.isnan(raw_x)) & (~np.isnan(raw_y))

        is_masked = np.zeros(n, dtype=bool)
        for r in self.masked_rows:
            if r < n:
                is_masked[r] = True
        for r in other_col.masked_rows:
            if r < n:
                is_masked[r] = True

        masked_pairs = valid_nums & is_masked
        indices = np.where(masked_pairs)[0]
        return raw_x[masked_pairs], raw_y[masked_pairs], indices

    def stats(self, include_masked: bool = False) -> Dict[str, Any]:
        """Calculate descriptive statistics for this column."""
        arr = self.to_numpy_array(include_masked=include_masked)
        valid = arr[~np.isnan(arr)]
        n = len(valid)
        if n == 0:
            return {
                "n": 0,
                "missing": len(arr),
                "mean": None,
                "std": None,
                "sem": None,
                "variance": None,
                "sum": None,
                "min": None,
                "q1": None,
                "median": None,
                "q3": None,
                "max": None,
                "iqr": None,
                "skewness": None,
                "kurtosis": None,
            }

        mean = float(np.mean(valid))
        std = float(np.std(valid, ddof=1)) if n > 1 else 0.0
        variance = float(np.var(valid, ddof=1)) if n > 1 else 0.0
        sem = float(std / math.sqrt(n)) if n > 1 else 0.0
        total = float(np.sum(valid))
        vmin = float(np.min(valid))
        vmax = float(np.max(valid))
        median = float(np.median(valid))
        q1 = float(np.percentile(valid, 25))
        q3 = float(np.percentile(valid, 75))
        iqr = float(q3 - q1)

        # Skewness & Kurtosis
        if n > 2 and std > 0:
            skewness = float(np.mean(((valid - mean) / std) ** 3))
            kurtosis = float(np.mean(((valid - mean) / std) ** 4) - 3.0)
        else:
            skewness = None
            kurtosis = None

        return {
            "n": n,
            "missing": len(arr) - n,
            "mean": mean,
            "std": std,
            "sem": sem,
            "variance": variance,
            "sum": total,
            "min": vmin,
            "q1": q1,
            "median": median,
            "q3": q3,
            "max": vmax,
            "iqr": iqr,
            "skewness": skewness,
            "kurtosis": kurtosis,
        }

    def fill_sequence(self, start: float = 1.0, step: float = 1.0, count: int = 50):
        """Fill column with an arithmetic sequence."""
        self.data = [float(start + i * step) for i in range(count)]

    def fill_random_uniform(self, low: float = 0.0, high: float = 1.0, count: int = 50):
        """Fill column with uniform random numbers."""
        vals = np.random.uniform(low, high, count)
        self.data = [float(v) for v in vals]

    def fill_random_normal(self, mean: float = 0.0, std: float = 1.0, count: int = 50):
        """Fill column with normal random numbers."""
        vals = np.random.normal(mean, std, count)
        self.data = [float(v) for v in vals]

    def clear(self):
        self.data.clear()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "long_name": self.long_name,
            "units": self.units,
            "comments": self.comments,
            "role": self.role.value,
            "data": self.data,
            "formula": self.formula,
            "masked_rows": sorted(list(self.masked_rows)),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Column":
        role_str = d.get("role", "Y")
        try:
            role = ColumnRole(role_str)
        except ValueError:
            role = ColumnRole.Y
        return cls(
            name=d.get("name", "A"),
            long_name=d.get("long_name", ""),
            units=d.get("units", ""),
            comments=d.get("comments", ""),
            role=role,
            data=d.get("data", []),
            formula=d.get("formula", ""),
            masked_rows=set(d.get("masked_rows", [])),
        )


class Worksheet:
    """Represents a spreadsheet sheet with columns, metadata, and data rows."""

    def __init__(self, name: str = "Sheet1"):
        self.name = name
        self.columns: List[Column] = []

    @classmethod
    def create_default(cls, name: str = "Sheet1", num_rows: int = 30) -> "Worksheet":
        """Creates a default Origin-style sheet with Col A(X) and Col B(Y)."""
        ws = cls(name=name)
        col_a = Column(name="A", long_name="", units="", role=ColumnRole.X)
        col_b = Column(name="B", long_name="", units="", role=ColumnRole.Y)
        col_a.data = [None] * num_rows
        col_b.data = [None] * num_rows
        ws.columns = [col_a, col_b]
        return ws

    def column_count(self) -> int:
        return len(self.columns)

    def row_count(self) -> int:
        if not self.columns:
            return 0
        return max(len(c.data) for c in self.columns)

    def add_column(
        self,
        name: Optional[str] = None,
        long_name: str = "",
        units: str = "",
        role: ColumnRole = ColumnRole.Y,
    ) -> Column:
        if not name:
            # Generate next letter: A, B, C ... Z, AA, AB ...
            name = self._next_column_name()
        col = Column(name=name, long_name=long_name, units=units, role=role)
        # Pad to current max row count
        r_count = self.row_count()
        if r_count > 0:
            col.data = [None] * r_count
        self.columns.append(col)
        return col

    def insert_column(self, index: int, name: Optional[str] = None, role: ColumnRole = ColumnRole.Y) -> Column:
        if not name:
            name = self._next_column_name()
        col = Column(name=name, role=role)
        r_count = self.row_count()
        if r_count > 0:
            col.data = [None] * r_count
        self.columns.insert(index, col)
        return col

    def remove_column(self, index: int) -> bool:
        if index is None or not (0 <= index < len(self.columns)):
            return False
        self.columns.pop(index)
        return True

    def remove_columns(self, indices: List[int]) -> bool:
        """Removes multiple columns by index in descending order."""
        if not indices:
            return False
        valid_indices = sorted(list(set(i for i in indices if i is not None and 0 <= i < len(self.columns))), reverse=True)
        if not valid_indices:
            return False
        for i in valid_indices:
            self.columns.pop(i)
        return True

    def get_column(self, index: int) -> Optional[Column]:
        if index is None or not (0 <= index < len(self.columns)):
            return None
        return self.columns[index]

    def get_column_by_name(self, name: str) -> Optional[Column]:
        name_clean = name.strip().upper()
        for c in self.columns:
            if c.name.upper() == name_clean or c.long_name.upper() == name_clean:
                return c
        return None

    def get_column_index(self, col: Column) -> int:
        try:
            return self.columns.index(col)
        except ValueError:
            return -1

    def add_row_index_for_single_column(self):
        """Give a one-column dataset an X axis based on its row numbers."""
        if len(self.columns) == 1:
            values = self.columns[0]
            values.name = "B"
            values.role = ColumnRole.Y
            self.columns.insert(0, Column(
                name="A", long_name="Row Number", role=ColumnRole.X,
                data=list(range(1, len(values.data) + 1)),
            ))

    def plot_column_pairs(self, selected_columns=()) -> list[tuple[int, int]]:
        """Resolve X/Y pairs using the current selection, or all Y columns by default."""
        selected = sorted({i for i in selected_columns if self.get_column(i) is not None})
        if selected:
            y_columns = [i for i in selected if self.columns[i].role == ColumnRole.Y]
            x_columns = [i for i in selected if self.columns[i].role == ColumnRole.X]
        else:
            y_columns = [i for i, col in enumerate(self.columns) if col.role == ColumnRole.Y]
            x_columns = []
        if not y_columns and not selected and self.columns:
            y_columns = [1 if len(self.columns) > 1 else 0]
        return [
            (next((x for x in reversed(x_columns) if x < y), x_columns[0]) if x_columns
             else self.find_x_column_for(y), y)
            for y in y_columns
        ]

    def find_x_column_for(self, y_col_index: int) -> Optional[int]:
        """
        Finds the corresponding X column for a given Y column.
        Origin logic: Look backwards from y_col_index to find the nearest preceding X column.
        If none found before it, find the first X column in the sheet.
        If still none found, return column 0.
        """
        if y_col_index is None or not self.columns:
            return None

        # Look backwards
        for i in range(y_col_index - 1, -1, -1):
            if self.columns[i].role == ColumnRole.X:
                return i

        # Look forward for first X column
        for i in range(len(self.columns)):
            if self.columns[i].role == ColumnRole.X:
                return i

        # Fallback to column 0 if available
        return 0 if len(self.columns) > 0 else None

    def find_y_error_column_for(self, y_col_index: int) -> Optional[int]:
        """
        Look forward immediately after y_col_index to find an adjacent YErr column.
        """
        if y_col_index is None:
            return None
        next_idx = y_col_index + 1
        if next_idx < len(self.columns) and self.columns[next_idx].role == ColumnRole.Y_ERR:
            return next_idx
        return None

    def set_cell(self, row: int, col_idx: int, val: Any):
        if row is None or col_idx is None or not (0 <= col_idx < len(self.columns)):
            return
        self.columns[col_idx].set_value(row, val)

    def get_cell(self, row: int, col_idx: int) -> Any:
        if row is None or col_idx is None or not (0 <= col_idx < len(self.columns)):
            return None
        return self.columns[col_idx].get_value(row)

    def insert_rows(self, row_idx: int, count: int = 1):
        """Insert count empty rows at row_idx."""
        if row_idx is None or row_idx < 0 or count <= 0:
            return
        blanks = [None] * count
        for col in self.columns:
            if row_idx > len(col.data):
                col.data.extend([None] * (row_idx - len(col.data)))
            col.data[row_idx:row_idx] = blanks
            col.masked_rows = {row + count if row >= row_idx else row for row in col.masked_rows}

    def delete_rows(self, row_idx: int, count: int = 1):
        """Delete count rows starting at row_idx."""
        if row_idx is None or row_idx < 0 or count <= 0:
            return
        end = row_idx + count
        for col in self.columns:
            del col.data[row_idx:end]
            col.masked_rows = {
                row - count if row >= end else row
                for row in col.masked_rows
                if not row_idx <= row < end
            }

    def clear_cells(self, rows: List[int], cols: List[int]):
        """Clear specified cells."""
        for c_idx in cols:
            if c_idx is not None and 0 <= c_idx < len(self.columns):
                col = self.columns[c_idx]
                for r in rows:
                    if r is not None and 0 <= r < len(col.data):
                        col.data[r] = None

    def mask_cell(self, row: int, col_idx: int, masked: bool = True):
        """Mask or unmask a specific cell."""
        if col_idx is not None and 0 <= col_idx < len(self.columns):
            self.columns[col_idx].mask_row(row, masked=masked)

    def is_cell_masked(self, row: int, col_idx: int) -> bool:
        """Check if a specific cell is masked."""
        if col_idx is not None and 0 <= col_idx < len(self.columns):
            return self.columns[col_idx].is_row_masked(row)
        return False

    def mask_cells(self, rows: List[int], cols: List[int], masked: bool = True):
        """Mask or unmask multiple cells at the given rows and columns."""
        for c_idx in cols:
            if c_idx is not None and 0 <= c_idx < len(self.columns):
                for r in rows:
                    if r is not None:
                        self.columns[c_idx].mask_row(r, masked=masked)

    def clear_all_masks(self):
        """Clear all masks across all columns in this worksheet."""
        for col in self.columns:
            col.clear_mask()

    def has_masked_cells(self) -> bool:
        """Return True if any column in the worksheet contains masked rows."""
        return any(len(c.masked_rows) > 0 for c in self.columns)

    def sort_by_column(self, col_idx: int, ascending: bool = True):
        """Sort entire worksheet rows based on values in col_idx."""
        if col_idx is None or not (0 <= col_idx < len(self.columns)):
            return

        r_count = self.row_count()
        if r_count <= 1:
            return

        sort_column = self.columns[col_idx]

        def sort_key(row):
            v = sort_column.get_value(row)
            if v is None or v == "" or (isinstance(v, float) and np.isnan(v)):
                return (2, "")
            try:
                if isinstance(v, bool):
                    return (1, str(v))
                return (0, float(v))
            except (ValueError, TypeError):
                return (1, str(v))

        rows = sorted(range(r_count), key=sort_key, reverse=not ascending)
        for col in self.columns:
            col.data = [col.get_value(row) for row in rows]
            col.masked_rows = {new for new, old in enumerate(rows) if old in col.masked_rows}

    sort_rows_by_column = sort_by_column

    def apply_formula(self, col_idx: int, formula_str: str, target_length: Optional[int] = None):
        """Evaluate and apply a formula to the specified column."""
        from omnigraph.core.column_formula import FormulaEvaluator
        if not (0 <= col_idx < len(self.columns)):
            raise IndexError("Column index out of range")

        target_col = self.columns[col_idx]
        target_col.formula = formula_str

        # If target_length not provided, find active length from existing data
        if target_length is None:
            active_lens = [len(c.data) for c in self.columns if any(v is not None and v != "" for v in c.data)]
            t_len = max(active_lens) if active_lens else self.row_count()
        else:
            t_len = target_length

        result = FormulaEvaluator.evaluate(formula_str, self, target_length=t_len)
        target_col.data = [None if (np.isnan(v) or np.isinf(v)) else float(v) for v in result]

    def to_dataframe(self) -> pd.DataFrame:
        """Convert worksheet data to a pandas DataFrame."""
        df_dict = {}
        r_count = self.row_count()
        for col in self.columns:
            arr = col.data + [None] * (r_count - len(col.data))
            header = col.display_label
            df_dict[header] = arr
        return pd.DataFrame(df_dict)

    def from_dataframe(self, df: pd.DataFrame):
        """Load data from a pandas DataFrame into this worksheet."""
        self.columns.clear()
        for col_name in df.columns:
            vals = df[col_name].tolist()
            # Clean up NaN
            clean_vals = [None if (isinstance(v, float) and np.isnan(v)) or pd.isna(v) else v for v in vals]
            role = ColumnRole.X if len(self.columns) == 0 else ColumnRole.Y
            col = Column(
                name=self._next_column_name(),
                long_name=str(col_name),
                role=role,
                data=clean_vals,
            )
            self.columns.append(col)

    def _next_column_name(self) -> str:
        idx = len(self.columns)
        result = ""
        while idx >= 0:
            result = chr(ord('A') + (idx % 26)) + result
            idx = idx // 26 - 1
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "columns": [c.to_dict() for c in self.columns],
        }

    def restore_from_dict(self, d: Dict[str, Any]):
        """Restores worksheet state in-place from serialized dictionary."""
        self.name = d.get("name", self.name)
        self.columns = [Column.from_dict(c) for c in d.get("columns", [])]

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Worksheet":
        ws = cls(name=d.get("name", "Sheet1"))
        ws.columns = [Column.from_dict(c) for c in d.get("columns", [])]
        return ws


class Workbook:
    """Represents a workbook containing multiple worksheet tabs."""

    def __init__(self, name: str = "Book1"):
        self.name = name
        self.sheets: List[Worksheet] = []
        self.active_sheet_index: int = 0

    @classmethod
    def create_default(cls, name: str = "Book1") -> "Workbook":
        wb = cls(name=name)
        wb.sheets.append(Worksheet.create_default(name="Sheet1"))
        return wb

    def get_active_sheet(self) -> Optional[Worksheet]:
        if 0 <= self.active_sheet_index < len(self.sheets):
            return self.sheets[self.active_sheet_index]
        return self.sheets[0] if self.sheets else None

    def add_sheet(self, name: Optional[str] = None) -> Worksheet:
        if not name:
            name = f"Sheet{len(self.sheets) + 1}"
        ws = Worksheet.create_default(name=name)
        self.sheets.append(ws)
        self.active_sheet_index = len(self.sheets) - 1
        return ws

    def remove_sheet(self, index: int) -> bool:
        if 0 <= index < len(self.sheets) and len(self.sheets) > 1:
            self.sheets.pop(index)
            if self.active_sheet_index >= len(self.sheets):
                self.active_sheet_index = len(self.sheets) - 1
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "active_sheet_index": self.active_sheet_index,
            "sheets": [s.to_dict() for s in self.sheets],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Workbook":
        wb = cls(name=d.get("name", "Book1"))
        wb.active_sheet_index = d.get("active_sheet_index", 0)
        wb.sheets = [Worksheet.from_dict(s) for s in d.get("sheets", [])]
        if not wb.sheets:
            wb.sheets.append(Worksheet.create_default("Sheet1"))
        return wb
