"""
Safe mathematical formula evaluator for spreadsheet columns.
Supports numpy functions, math constants, column references (e.g. col(A), col('A'), A, B),
Origin-style row indices (i, row), scientific transformations, and friendly error reporting.
"""

import ast
from types import SimpleNamespace
import math
import re
from typing import Optional, Any, Dict
import numpy as np


class FormulaEvaluator:
    """Evaluates mathematical expressions for worksheet columns with rich scientific functions."""

    @staticmethod
    def _robust_normalize(x):
        arr = np.asarray(x, dtype=float)
        mi = np.nanmin(arr)
        ma = np.nanmax(arr)
        if np.isnan(mi) or np.isnan(ma) or ma == mi:
            return np.zeros_like(arr)
        return (arr - mi) / (ma - mi)

    @staticmethod
    def _robust_zscore(x):
        arr = np.asarray(x, dtype=float)
        s = np.nanstd(arr)
        if np.isnan(s) or s == 0:
            return np.zeros_like(arr)
        return (arr - np.nanmean(arr)) / s

    @staticmethod
    def _diff_prepend(x):
        arr = np.asarray(x, dtype=float)
        if len(arr) == 0:
            return arr
        return np.diff(arr, prepend=arr[0])

    @staticmethod
    def _lag_array(x, k=1):
        arr = np.asarray(x, dtype=float)
        res = np.full_like(arr, np.nan)
        if 0 < k < len(arr):
            res[k:] = arr[:-k]
        elif k == 0:
            return arr.copy()
        return res

    SAFE_MATH = {
        # Trigonometric
        "sin": np.sin,
        "cos": np.cos,
        "tan": np.tan,
        "asin": np.arcsin,
        "acos": np.arccos,
        "atan": np.arctan,
        "atan2": np.arctan2,
        "sinh": np.sinh,
        "cosh": np.cosh,
        "tanh": np.tanh,
        "deg2rad": np.deg2rad,
        "rad2deg": np.rad2deg,
        # Exponential & Logarithmic
        "exp": np.exp,
        "exp2": np.exp2,
        "log": np.log,
        "ln": np.log,
        "log10": np.log10,
        "log2": np.log2,
        # Powers & Roots
        "sqrt": np.sqrt,
        "cbrt": np.cbrt,
        "abs": np.abs,
        "power": np.power,
        "hypot": np.hypot,
        # Rounding
        "floor": np.floor,
        "ceil": np.ceil,
        "round": np.round,
        "trunc": np.trunc,
        # Constants
        "pi": math.pi,
        "e": math.e,
        # Random Distributions
        "random": np.random.random,
        "normal": np.random.normal,
        # Nan-Safe Array Statistics
        "mean": np.nanmean,
        "std": np.nanstd,
        "var": np.nanvar,
        "sum": np.nansum,
        "min": np.nanmin,
        "max": np.nanmax,
        "median": np.nanmedian,
        # Calculus, Differences & Transforms
        "diff": _diff_prepend,
        "cumsum": np.nancumsum,
        "deriv": lambda y, x=None: np.gradient(y, x) if x is not None else np.gradient(y),
        "norm": _robust_normalize,
        "normalize": _robust_normalize,
        "zscore": _robust_zscore,
        "clamp": np.clip,
        "clip": np.clip,
        "prev": _lag_array,
        "lag": _lag_array,
        # Numpy alias
        "np": SimpleNamespace(**{name:getattr(np,name) for name in (
            "sin","cos","tan","arcsin","arccos","arctan","arctan2","sinh","cosh","tanh",
            "deg2rad","rad2deg","exp","exp2","log","log10","log2","sqrt","cbrt","abs","power",
            "hypot","floor","ceil","round","trunc","pi","e","nan","inf","mean","std","var",
            "sum","min","max","median","nanmean","nanstd","nanvar","nansum","nanmin","nanmax",
            "nanmedian","diff","cumsum","nancumsum","gradient","clip","where","minimum","maximum",
            "isnan","isfinite","array","arange","linspace","zeros","ones","full")}),
    }

    @staticmethod
    def _validate_expression(expression):
        if len(expression)>4096:
            raise ValueError("Formula is too long (maximum 4096 characters).")
        try:
            tree=ast.parse(expression,mode="eval")
        except (SyntaxError,RecursionError) as error:
            raise ValueError("Incomplete or invalid formula syntax.") from error
        allowed=(ast.Expression,ast.BinOp,ast.UnaryOp,ast.BoolOp,ast.Compare,ast.IfExp,
                 ast.Call,ast.Name,ast.Load,ast.Constant,ast.List,ast.Tuple,ast.Subscript,
                 ast.Slice,ast.keyword,ast.Attribute,ast.Add,ast.Sub,ast.Mult,ast.Div,
                 ast.FloorDiv,ast.Mod,ast.Pow,ast.USub,ast.UAdd,ast.Not,ast.And,ast.Or,
                 ast.Eq,ast.NotEq,ast.Lt,ast.LtE,ast.Gt,ast.GtE,ast.BitAnd,ast.BitOr,ast.Invert)
        approved_numpy=vars(FormulaEvaluator.SAFE_MATH["np"])
        for node in ast.walk(tree):
            if not isinstance(node,allowed):
                raise ValueError("Only mathematical expressions and approved functions are allowed.")
            if isinstance(node,ast.Name) and node.id.startswith("_"):
                raise ValueError("Private Python attributes are not available in formulas.")
            if isinstance(node,ast.Attribute):
                if not (isinstance(node.value,ast.Name) and node.value.id=="np" and node.attr in approved_numpy):
                    raise ValueError("Only approved np math functions are available; file and system access is disabled.")
            if isinstance(node,ast.Call):
                if not isinstance(node.func,(ast.Name,ast.Attribute)):
                    raise ValueError("Indirect function calls are not allowed.")
                if isinstance(node.func,ast.Name) and node.func.id not in {*FormulaEvaluator.SAFE_MATH,"col","Col","COL"}:
                    raise ValueError("Only approved math functions may be called.")
                if any(keyword.arg is None for keyword in node.keywords):
                    raise ValueError("Expanded keyword arguments are not allowed.")
        return tree

    @staticmethod
    def preprocess_formula(formula_str: str) -> str:
        """
        Cleans and normalizes user input into valid executable Python:
          - Strips leading '='
          - Replaces '^' with '**' for exponentiation (e.g. A^2 -> A**2)
          - Quotes unquoted col() arguments (e.g. col(A) -> col('A'), col(1) -> col('1'))
        """
        expr = formula_str.strip()
        if expr.startswith("="):
            expr = expr[1:].strip()

        # Convert ^ to ** (exponentiation)
        expr = re.sub(r'\^', '**', expr)

        # Convert col(A) or col(1) -> col('A') or col('1') if unquoted
        def quote_col(match):
            inner = match.group(1).strip()
            if (inner.startswith("'") and inner.endswith("'")) or (inner.startswith('"') and inner.endswith('"')):
                return match.group(0)
            return f"col('{inner}')"

        expr = re.sub(r'col\s*\(\s*([^()]+)\s*\)', quote_col, expr, flags=re.IGNORECASE)
        return expr

    @staticmethod
    def evaluate(formula_str: str, worksheet, target_length: Optional[int] = None) -> np.ndarray:
        """
        Evaluate a formula string in the context of a worksheet.
        Supported syntax:
          - col(A) or col('A')
          - col(1) (1-indexed column number)
          - A, B, C (direct column letters)
          - i or row (1-based row index array)
          - idx (0-based row index array)
          - n or N (total row count)
          - Scientific functions: sin, cos, exp, log10, ln, sqrt, norm, zscore, diff, cumsum
        """
        cleaned_str = FormulaEvaluator.preprocess_formula(formula_str)
        if not cleaned_str:
            raise ValueError("Formula expression is empty.")

        expression_tree=FormulaEvaluator._validate_expression(cleaned_str)

        # Determine target row count
        if target_length is None:
            active_lens = [len(c.data) for c in worksheet.columns if any(v is not None and v != "" for v in c.data)]
            target_length = max(active_lens) if active_lens else worksheet.row_count()
        if target_length == 0:
            target_length = 50

        col_data_cache: Dict[str, np.ndarray] = {}

        def get_col(identifier: Any) -> np.ndarray:
            # If identifier is already an evaluated array (e.g. from col(A) where A was resolved in scope)
            if isinstance(identifier, np.ndarray):
                return identifier

            key = str(identifier).strip()

            # 1. Try 1-based or 0-based column index
            if isinstance(identifier, int) or key.isdigit():
                idx = int(identifier)
                if 1 <= idx <= worksheet.column_count():
                    col = worksheet.columns[idx - 1]
                    if col.name not in col_data_cache:
                        col_data_cache[col.name] = col.to_numpy_array(length=target_length)
                    return col_data_cache[col.name]
                elif 0 <= idx < worksheet.column_count():
                    col = worksheet.columns[idx]
                    if col.name not in col_data_cache:
                        col_data_cache[col.name] = col.to_numpy_array(length=target_length)
                    return col_data_cache[col.name]

            # 2. Try by column name (case-insensitive name or long_name)
            key_upper = key.upper()
            if key_upper in col_data_cache:
                return col_data_cache[key_upper]

            for col in worksheet.columns:
                if col.name.upper() == key_upper or col.long_name.upper() == key_upper:
                    arr = col.to_numpy_array(length=target_length)
                    col_data_cache[key_upper] = arr
                    return arr

            raise ValueError(f"Column '{identifier}' not found in worksheet '{worksheet.name}'")

        # Build execution scope
        local_scope = dict(FormulaEvaluator.SAFE_MATH)
        local_scope["col"] = get_col
        local_scope["Col"] = get_col
        local_scope["COL"] = get_col
        local_scope["i"] = np.arange(1, target_length + 1, dtype=float)
        local_scope["row"] = np.arange(1, target_length + 1, dtype=float)
        local_scope["idx"] = np.arange(0, target_length, dtype=float)
        local_scope["n"] = target_length
        local_scope["N"] = target_length

        # Populate direct column variables (A, B, C, col_a, etc., and simplified column names)
        for col in worksheet.columns:
            name_clean = col.name.strip().upper()
            arr = col.to_numpy_array(length=target_length)
            local_scope[f"col_{name_clean.lower()}"] = arr
            if name_clean.isidentifier():
                if name_clean.lower() not in local_scope:
                    local_scope[name_clean.lower()] = arr
                local_scope[name_clean] = arr

            # Also populate intuitive column name (col.long_name) as direct variable if valid identifier
            if col.long_name:
                ln_clean = col.long_name.strip()
                if ln_clean.isidentifier() and ln_clean not in FormulaEvaluator.SAFE_MATH:
                    local_scope[ln_clean] = arr
                    if ln_clean.lower() not in local_scope:
                        local_scope[ln_clean.lower()] = arr
                    if ln_clean.upper() not in local_scope:
                        local_scope[ln_clean.upper()] = arr
                safe_tag = "".join(c if c.isalnum() else "_" for c in ln_clean.lower())
                local_scope[f"col_{safe_tag}"] = arr

        # Evaluate expression with friendly error handling
        try:
            # Ignore zero division warnings in numpy during evaluation
            with np.errstate(divide='ignore', invalid='ignore'):
                result = eval(compile(expression_tree,"<formula>","eval"), {"__builtins__": {}}, local_scope)
        except NameError as ne:
            var_match = re.search(r"name '([^']+)' is not defined", str(ne))
            var_name = var_match.group(1) if var_match else "unknown"
            raise ValueError(
                f"Unknown symbol '{var_name}'. Did you mean a column name like col('{var_name}') or col(A)?"
            )
        except SyntaxError:
            raise ValueError("Incomplete or invalid syntax (check for missing operators or parentheses).")
        except ZeroDivisionError:
            result = np.full(target_length, np.nan)
        except Exception as e:
            raise ValueError(f"Formula evaluation error: {e}")

        # Convert result to numpy array
        if np.isscalar(result):
            result = np.full(target_length, float(result))
        elif isinstance(result, (list, tuple)):
            result = np.array(result, dtype=float)
        elif isinstance(result, np.ndarray):
            if np.iscomplexobj(result):
                result = np.real(result)
            if result.ndim == 0:
                result = np.full(target_length, float(result))
            elif len(result) < target_length:
                padded = np.full(target_length, np.nan)
                padded[:len(result)] = result
                result = padded
            elif len(result) > target_length:
                result = result[:target_length]
        else:
            try:
                result = np.array(result, dtype=float)
            except Exception:
                raise ValueError("Formula did not produce numeric values.")

        return result
