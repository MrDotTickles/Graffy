"""Match worksheet columns conservatively when reusing a data workflow."""

import numpy as np


def column_signature(column):
    return [column.long_name or column.name, column.units, column.role.value]


def match_column(sheet, signature):
    if signature is None:
        return None
    name, units, role = signature
    matches = [
        index for index, column in enumerate(sheet.columns)
        if (column.long_name or column.name).strip().casefold() == name.strip().casefold()
        and column.units == units
        and column.role.value == role
    ]
    return matches[0] if len(matches) == 1 else None


def numeric_pairs(sheet, x_index, y_index):
    x = sheet.get_column(x_index)
    y = sheet.get_column(y_index)
    if x is None or y is None or x is y:
        return np.array([]), np.array([])
    xs, ys, _ = x.get_valid_numeric_pairs(y)
    finite = np.isfinite(xs) & np.isfinite(ys)
    return xs[finite], ys[finite]
