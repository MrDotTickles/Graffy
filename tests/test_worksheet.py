import pytest
import numpy as np
import pandas as pd
from omnigraph.core.worksheet import Worksheet, Column, ColumnRole, Workbook


def test_column_roles_and_properties():
    col = Column(name="A", long_name="Time", units="s", role=ColumnRole.X)
    assert col.name == "A"
    assert col.display_label == "Time (s)"
    assert col.role == ColumnRole.X


def test_worksheet_crud_and_pairing():
    ws = Worksheet("TestSheet")
    col_x = ws.add_column("A", "Wavelength", "nm", ColumnRole.X)
    col_y1 = ws.add_column("B", "Absorbance 1", "a.u.", ColumnRole.Y)
    col_err1 = ws.add_column("C", "Error 1", "a.u.", ColumnRole.Y_ERR)
    col_y2 = ws.add_column("D", "Absorbance 2", "a.u.", ColumnRole.Y)

    assert ws.column_count() == 4
    assert ws.find_x_column_for(1) == 0
    assert ws.find_y_error_column_for(1) == 2
    assert ws.find_x_column_for(3) == 0
    assert ws.find_y_error_column_for(3) is None


def test_sorting():
    ws = Worksheet.create_default(num_rows=5)
    ws.columns[0].data = [3.0, 1.0, 4.0, 2.0, 5.0]
    ws.columns[1].data = [30.0, 10.0, 40.0, 20.0, 50.0]

    ws.sort_by_column(0, ascending=True)
    assert ws.columns[0].data == [1.0, 2.0, 3.0, 4.0, 5.0]
    assert ws.columns[1].data == [10.0, 20.0, 30.0, 40.0, 50.0]

    ws.sort_by_column(0, ascending=False)
    assert ws.columns[0].data == [5.0, 4.0, 3.0, 2.0, 1.0]
    assert ws.columns[1].data == [50.0, 40.0, 30.0, 20.0, 10.0]


def test_dataframe_roundtrip():
    df = pd.DataFrame({
        "X_vals": [1, 2, 3, 4],
        "Y_vals": [10.5, 20.5, 30.5, 40.5],
    })
    ws = Worksheet("DF_Test")
    ws.from_dataframe(df)

    assert ws.column_count() == 2
    assert ws.row_count() == 4
    assert ws.columns[0].long_name == "X_vals"
    assert ws.columns[1].long_name == "Y_vals"

    df_out = ws.to_dataframe()
    assert len(df_out) == 4
