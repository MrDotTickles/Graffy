"""
Local rule-based data extractor for Graffy.
Reads supported table and instrument formats (TXT, CSV, DAT, LOG, TSV, Excel, JSON, raw dumps),
detects headers, units, metadata skip lines, delimiters, and automatically infers
column roles (X, Y, Y Error) and recommends the optimal scientific plot type.
"""

import os
import re
import io
import json
from typing import Optional, List, Dict, Any, Tuple
import numpy as np
import pandas as pd

from omnigraph.core.worksheet import Worksheet, Column, ColumnRole


class ExtractionResult:
    """Encapsulates parsed data and inferred column metadata."""

    def __init__(
        self,
        dataframe: pd.DataFrame,
        column_roles: Dict[str, ColumnRole],
        column_units: Dict[str, str],
        column_long_names: Dict[str, str],
        recommended_plot: str = "line_symbol",
        metadata: Optional[Dict[str, Any]] = None,
        notes: str = "",
    ):
        self.dataframe = dataframe
        self.column_roles = column_roles
        self.column_units = column_units
        self.column_long_names = column_long_names
        self.recommended_plot = recommended_plot
        self.metadata = metadata if metadata is not None else {}
        self.notes = notes

    def to_worksheet(self, sheet_name: str = "ExtractedData") -> Worksheet:
        """Converts extracted data into a fully configured Graffy Worksheet."""
        ws = Worksheet(name=sheet_name)
        cols: List[Column] = []

        for i, col_name in enumerate(self.dataframe.columns):
            raw_vals = self.dataframe[col_name].tolist()
            # Clean values: convert NaN to None
            clean_vals = [None if pd.isna(v) else v for v in raw_vals]

            role = self.column_roles.get(col_name, ColumnRole.Y)
            units = self.column_units.get(col_name, "")
            long_name = self.column_long_names.get(col_name, str(col_name))

            col_letter = chr(65 + (i % 26)) if i < 26 else f"C{i+1}"
            c = Column(
                name=col_letter,
                long_name=long_name,
                units=units,
                role=role,
                data=clean_vals,
            )
            cols.append(c)

        ws.columns = cols
        return ws


class SmartDataExtractor:
    """Local heuristic parser; no model, API, or network request is used."""

    # Keywords commonly indicating independent variable (X)
    X_KEYWORDS = [
        "time", "wavelength", "wl", "wavenumber", "freq", "frequency",
        "energy", "temp", "temperature", "voltage", "volt", "potential",
        "conc", "concentration", "dose", "depth", "position", "pos",
        "distance", "dist", "step", "index", "row", "date", "sec", "second",
        "min", "minute", "hour", "day", "nm", "cm-1", "hz", "khz", "mhz", "ev",
        "omega", "2theta", "twotheta", "theta", "angle", "arcsec", "q", "d-spacing",
        "scattering_angle", "rocking_angle"
    ]

    # Keywords commonly indicating error bars (Y_ERR)
    ERR_KEYWORDS = ["err", "error", "sd", "std", "sem", "stdev", "uncert", "sigma"]

    @classmethod
    def extract_from_file(
        cls,
        filepath: str,
        custom_prompt: str = "",
        header_mode: str = "auto",
        delimiter_override: Optional[str] = None,
    ) -> ExtractionResult:
        """Inspects any file format, extracts tabular data, and infers metadata."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        ext = os.path.splitext(filepath)[1].lower()

        # XRD / Rocking curve sequential files (.x01, .x02, etc.)
        if re.search(r"^\.x\d{2}$", ext):
            return cls._extract_from_x01(filepath, custom_prompt=custom_prompt)

        # Excel
        if ext in [".xlsx", ".xls"]:
            return cls._extract_from_excel(filepath, header_mode=header_mode)

        # JSON
        if ext in [".json"]:
            return cls._extract_from_json(filepath)

        # Text-based (CSV, TSV, TXT, DAT, LOG, PRN, etc.)
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            with open(filepath, "r", encoding="latin-1", errors="replace") as f:
                content = f.read()

        return cls.extract_from_text(
            content,
            source_name=os.path.basename(filepath),
            header_mode=header_mode,
            delimiter_override=delimiter_override,
        )

    @classmethod
    def _is_numeric_token(cls, token: str) -> bool:
        """Determines if a string token represents a valid number."""
        tok = token.strip().strip("'\"").rstrip("%")
        if not tok:
            return False
        try:
            float(tok)
            return True
        except (ValueError, TypeError):
            return False

    @classmethod
    def _detect_header_mode(cls, data_lines: List[str], delimiter: str) -> str:
        """
        Determines whether the first line of data_lines is pure data ('none'),
        a single header row ('first_row'), or two header rows ('two_rows').
        """
        if not data_lines:
            return "none"

        def tokenize(line: str) -> List[str]:
            s = line.strip()
            if not s:
                return []
            if delimiter == r"\s+":
                return [p for p in re.split(r"\s+", s) if p]
            return [p.strip() for p in s.split(delimiter) if p.strip()]

        row0_tokens = tokenize(data_lines[0])
        if not row0_tokens:
            return "none"

        num_count_0 = sum(1 for t in row0_tokens if cls._is_numeric_token(t))
        frac_numeric_0 = num_count_0 / len(row0_tokens)

        # If 50% or more tokens in the first line are numeric, it's pure data (no header row!)
        if frac_numeric_0 >= 0.5:
            return "none"

        # Otherwise, row 0 is text / column names.
        # Now check row 1 to see if it's units or data.
        if len(data_lines) > 1:
            row1_tokens = tokenize(data_lines[1])
            if row1_tokens:
                num_count_1 = sum(1 for t in row1_tokens if cls._is_numeric_token(t))
                frac_numeric_1 = num_count_1 / len(row1_tokens)
                # If row 1 is ALSO predominantly non-numeric text/units (e.g. [nm], [OD], a.u., sec),
                # and len(data_lines) > 2, then row 0 is names and row 1 is units!
                if frac_numeric_1 < 0.5 and len(data_lines) > 2:
                    return "two_rows"

        return "first_row"

    @classmethod
    def extract_from_text(
        cls,
        text: str,
        source_name: str = "RawText",
        header_mode: str = "auto",
        delimiter_override: Optional[str] = None,
    ) -> ExtractionResult:
        """Parses raw text containing tables, scientific outputs, or instrument dumps."""
        text_lower = text.lower()
        # If text looks like INI-style XRD/rocking curve or has [Data] / [Header] tags
        if "[data]" in text_lower or "[header]" in text_lower or "scan mode" in text_lower or "omega (arcsec)" in text_lower:
            return cls._parse_x01_ascii(text, source_name=source_name)

        lines = text.strip().splitlines()
        if not lines:
            return ExtractionResult(pd.DataFrame(), {}, {}, {}, notes="Empty text input.")

        # 1. Identify and extract preamble metadata (e.g., "Instrument: UV-1800", "# Date: 2026-10-19")
        metadata = {}
        data_start_idx = 0

        for idx, line in enumerate(lines):
            line_str = line.strip()
            if not line_str:
                continue

            # Section marker in INI-style headers: [Header], [Metadata], [Parameters]
            if line_str.startswith("[") and line_str.endswith("]"):
                sec_name = line_str[1:-1].strip().lower()
                if sec_name in ["data", "scan", "scandata", "results", "points", "table"]:
                    data_start_idx = idx + 1
                    break
                continue

            if line_str.lower().startswith("data:"):
                data_start_idx = idx + 1
                break

            # Horizontal dividers like --------------------- or =====================
            if re.match(r"^[-=_*#]{3,}$", line_str):
                continue

            # Check comments
            if line_str.startswith(("#", "//", ";", "%", "*", "!", "@")):
                clean_comment = line_str.lstrip("#/;%*!@ ").strip()
                if ":" in clean_comment:
                    k, v = clean_comment.split(":", 1)
                    metadata[k.strip()] = v.strip()
                elif "=" in clean_comment:
                    k, v = clean_comment.split("=", 1)
                    metadata[k.strip()] = v.strip()
                continue

            # Key = Value or Key: Value metadata lines (without multiple numbers)
            if "=" in line_str and not cls._contains_multiple_numbers(line_str):
                k, v = line_str.split("=", 1)
                metadata[k.strip()] = v.strip()
                continue

            if ":" in line_str and not cls._contains_multiple_numbers(line_str):
                k, v = line_str.split(":", 1)
                metadata[k.strip()] = v.strip()
                continue

            # Check if this line looks like column headers
            tokens = re.split(r"[,\t;|\s]+", line_str)
            if len(tokens) >= 2 and any(t.lower() in cls.X_KEYWORDS + ["absorbance", "intensity", "counts", "cps", "value", "signal", "response", "od", "bar"] for t in tokens):
                data_start_idx = idx
                break

            # If line has multiple numbers, data has begun!
            if cls._contains_multiple_numbers(line_str):
                data_start_idx = idx
                break

            # Found first line of data or table header!
            data_start_idx = idx
            break

        data_lines = lines[data_start_idx:]
        if not data_lines:
            return ExtractionResult(pd.DataFrame(), {}, {}, {}, notes="No data found after metadata header.")

        # 2. Detect delimiter (comma, tab, semicolon, whitespace)
        sample_chunk = "\n".join(data_lines[:min(25, len(data_lines))])
        delimiter = delimiter_override if delimiter_override else cls._detect_delimiter(sample_chunk)

        # Determine effective header mode
        if header_mode == "auto":
            effective_header_mode = cls._detect_header_mode(data_lines, delimiter)
        else:
            effective_header_mode = header_mode

        # 3. Read into DataFrame using Pandas according to effective_header_mode
        extra_units = {}
        try:
            if effective_header_mode == "two_rows" and len(data_lines) >= 3:
                def tokenize(line: str) -> List[str]:
                    s = line.strip()
                    if delimiter == r"\s+":
                        return [p for p in re.split(r"\s+", s) if p]
                    return [p.strip() for p in s.split(delimiter) if p.strip()]

                raw_names = tokenize(data_lines[0])
                raw_units = tokenize(data_lines[1])
                header_names = [n if n else f"Col {i+1}" for i, n in enumerate(raw_names)]
                for i, u in enumerate(raw_units):
                    clean_u = u.strip("[]() /")
                    col_key = header_names[i] if i < len(header_names) else f"Col {i+1}"
                    if clean_u:
                        extra_units[col_key] = clean_u

                data_content = "\n".join(data_lines[2:])
                if delimiter == r"\s+":
                    df = pd.read_csv(io.StringIO(data_content), sep=r"\s+", header=None, names=header_names, engine="python")
                else:
                    df = pd.read_csv(io.StringIO(data_content), sep=delimiter, header=None, names=header_names, engine="python")

            elif effective_header_mode == "none":
                data_content = "\n".join(data_lines)
                if delimiter == r"\s+":
                    df = pd.read_csv(io.StringIO(data_content), sep=r"\s+", header=None, engine="python")
                else:
                    df = pd.read_csv(io.StringIO(data_content), sep=delimiter, header=None, engine="python")
                df.columns = [f"Col {chr(65 + i) if i < 26 else i + 1}" for i in range(len(df.columns))]

            else:  # "first_row"
                data_content = "\n".join(data_lines)
                if delimiter == r"\s+":
                    df = pd.read_csv(io.StringIO(data_content), sep=r"\s+", header=0, engine="python")
                else:
                    df = pd.read_csv(io.StringIO(data_content), sep=delimiter, header=0, engine="python")

        except Exception:
            # Fallback line-by-line regex parsing
            effective_header_mode = "fallback"
            df = cls._fallback_parse_lines(data_lines)

        # 4. Clean column names and extract units
        df, col_units, col_long_names = cls._parse_headers_and_units(df)
        if extra_units:
            for k, u in extra_units.items():
                if k in col_units and not col_units[k]:
                    col_units[k] = u
                elif k not in col_units:
                    col_units[k] = u

        df = cls._clean_numeric_columns(df, metadata)

        # 6. Infer Column Roles (X, Y, Y_ERR)
        col_roles = cls._infer_column_roles(df, col_long_names)

        # 7. Recommend Plot Type
        rec_plot = cls._recommend_plot(df, col_roles)

        mode_display = {
            "none": "Pure Data (Row 1 is Data)",
            "first_row": "First Row as Column Names",
            "two_rows": "First 2 Rows as Names & Units",
        }.get(effective_header_mode, effective_header_mode)

        metadata["HeaderMode"] = effective_header_mode
        metadata["HeaderRow"] = data_start_idx + 1

        return ExtractionResult(
            dataframe=df,
            column_roles=col_roles,
            column_units=col_units,
            column_long_names=col_long_names,
            recommended_plot=rec_plot,
            metadata=metadata,
            notes=f"Extracted {len(df)} rows × {len(df.columns)} columns from {source_name} ({mode_display}).",
        )

    @classmethod
    def _extract_from_excel(cls, filepath: str, header_mode: str = "auto") -> ExtractionResult:
        """Read the first Excel sheet, honoring the selected header option."""
        with pd.ExcelFile(filepath) as excel_file:
            sheet_name = excel_file.sheet_names[0]
            df = excel_file.parse(sheet_name, header=None)
        header_row = 0
        if header_mode == "auto" and not df.empty:
            for row in range(min(15, len(df))):
                if df.iloc[row].notna().sum() >= max(2, len(df.columns) * 0.5):
                    header_row = row
                    break
            values = df.iloc[header_row].dropna().tolist()
            numbers = sum(isinstance(value, (int, float)) for value in values)
            header_mode = "none" if not values or numbers / len(values) >= 0.5 else "first_row"
        if df.empty:
            return ExtractionResult(df, {}, {}, {}, notes="The first Excel sheet is empty.")

        if header_mode == "none":
            df.columns = [f"Col {chr(65 + i) if i < 26 else i + 1}" for i in range(len(df.columns))]
        else:
            names = df.iloc[header_row].tolist()
            units = df.iloc[header_row + 1].tolist() if header_mode == "two_rows" and len(df) > header_row + 1 else []
            labels = []
            for index, name in enumerate(names):
                label = f"Column {index + 1}" if pd.isna(name) else str(name).strip()
                if units and not pd.isna(units[index]) and str(units[index]).strip():
                    label += f" [{str(units[index]).strip('[]() ')}]"
                unique = label
                suffix = 2
                while unique in labels:
                    unique = f"{label} ({suffix})"
                    suffix += 1
                labels.append(unique)
            df = df.iloc[header_row + (2 if units else 1):].reset_index(drop=True)
            df.columns = labels

        df, col_units, col_long_names = cls._parse_headers_and_units(df)
        metadata = {"Sheet": sheet_name, "Source": filepath, "HeaderMode": header_mode, "HeaderRow": header_row + 1}
        df = cls._clean_numeric_columns(df, metadata)
        col_roles = cls._infer_column_roles(df, col_long_names)

        return ExtractionResult(
            dataframe=df,
            column_roles=col_roles,
            column_units=col_units,
            column_long_names=col_long_names,
            recommended_plot=cls._recommend_plot(df, col_roles),
            metadata=metadata,
            notes=f"Excel import from sheet '{sheet_name}'.",
        )

    @staticmethod
    def _clean_numeric_columns(df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """Record nonempty values that become blank, including those in dropped columns."""
        invalid_count = 0
        examples = []
        for column in df.columns:
            raw = df[column]
            numeric = pd.to_numeric(raw, errors="coerce").replace([np.inf, -np.inf], np.nan)
            invalid = raw.notna() & numeric.isna()
            invalid_count += int(invalid.sum())
            for row in np.flatnonzero(invalid.to_numpy())[:max(0, 3 - len(examples))]:
                examples.append(f"{str(column)[:32]}, data row {row + 1}: {str(raw.iloc[row])[:30]!r}")
            df[column] = numeric
        metadata["InvalidNumericCount"] = invalid_count
        metadata["InvalidNumericExamples"] = examples
        metadata["DroppedColumns"] = [str(column) for column in df.columns[df.isna().all()]]
        return df.dropna(how="all", axis=1)

    @classmethod
    def _extract_from_json(cls, filepath: str) -> ExtractionResult:
        """Extracts table from JSON records or key-array structures."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            # Check for records list or dictionary of lists
            first_val = next(iter(data.values())) if data else None
            if isinstance(first_val, list):
                df = pd.DataFrame(data)
            else:
                df = pd.json_normalize(data)
        else:
            df = pd.DataFrame()

        df, col_units, col_long_names = cls._parse_headers_and_units(df)
        metadata = {"Format": "JSON"}
        df = cls._clean_numeric_columns(df, metadata)
        col_roles = cls._infer_column_roles(df, col_long_names)
        rec_plot = cls._recommend_plot(df, col_roles)

        return ExtractionResult(
            dataframe=df,
            column_roles=col_roles,
            column_units=col_units,
            column_long_names=col_long_names,
            recommended_plot=rec_plot,
            metadata=metadata,
            notes=f"JSON structured extraction ({len(df)} rows).",
        )

    @classmethod
    def _detect_delimiter(cls, text_sample: str) -> str:
        """Sniffs the most probable column separator."""
        lines = [line for line in text_sample.splitlines() if line.strip()]
        if not lines:
            return ","

        # 1. Check explicit delimiters first: tab, comma, semicolon, pipe
        explicit_cands = ["\t", ",", ";", "|"]
        for cand in explicit_cands:
            counts = [line.count(cand) for line in lines[:10]]
            if counts and min(counts) > 0 and (max(counts) - min(counts) <= 1):
                return cand

        # 2. Check for whitespace separated columns
        ws_counts = [len(re.split(r"\s+", line.strip())) for line in lines[:10]]
        if ws_counts and min(ws_counts) > 1 and (max(ws_counts) - min(ws_counts) <= 1):
            return r"\s+"

        # 3. Fallback to comma or whitespace
        for cand in explicit_cands:
            if sum(line.count(cand) for line in lines) > 0:
                return cand

        return r"\s+"

    @classmethod
    def _parse_headers_and_units(cls, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str], Dict[str, str]]:
        """
        Parses column names containing embedded units like 'Wavelength (nm)',
        'Absorbance [a.u.]', 'Time / min', or 'Signal (uV)'.
        """
        col_units: Dict[str, str] = {}
        col_long_names: Dict[str, str] = {}
        new_cols: List[str] = []

        unit_regexes = [
            r"^(.*?)\s*[\(\[]([^\(\)\[\]]+)[\)\]]$",  # Name (Units) or Name [Units]
            r"^(.*?)\s*/\s*([a-zA-Z0-9_\-%\^\*\./]+)$",  # Name / Units
        ]

        for orig_col in df.columns:
            orig_str = str(orig_col).strip()
            clean_name = orig_str
            unit = ""

            for rx in unit_regexes:
                m = re.match(rx, orig_str)
                if m:
                    clean_name = m.group(1).strip()
                    unit = m.group(2).strip()
                    break

            if not clean_name:
                clean_name = orig_str

            col_units[orig_str] = unit
            col_long_names[orig_str] = clean_name
            new_cols.append(orig_str)

        df.columns = new_cols
        return df, col_units, col_long_names

    @classmethod
    def _infer_column_roles(cls, df: pd.DataFrame, col_long_names: Dict[str, str]) -> Dict[str, ColumnRole]:
        """Infers X, Y, and Y_ERR roles intelligently from names and data distributions."""
        roles: Dict[str, ColumnRole] = {}
        assigned_x = False

        for col in df.columns:
            name_lower = str(col_long_names.get(col, col)).lower()

            # 1. Error column check
            if any(err_kw in name_lower for err_kw in cls.ERR_KEYWORDS):
                roles[col] = ColumnRole.Y_ERR
                continue

            # 2. X column check (only first plausible candidate becomes X)
            if not assigned_x:
                if any(x_kw in name_lower for x_kw in cls.X_KEYWORDS):
                    roles[col] = ColumnRole.X
                    assigned_x = True
                    continue

                # Also check if numeric and strictly increasing (typical time/independent series)
                series = pd.to_numeric(df[col], errors="coerce").dropna()
                if len(series) > 3 and series.is_monotonic_increasing:
                    roles[col] = ColumnRole.X
                    assigned_x = True
                    continue

            # Default
            roles[col] = ColumnRole.Y

        # If no X was assigned, make first column X if > 1 columns exist
        if not assigned_x and len(df.columns) > 1:
            first_col = df.columns[0]
            roles[first_col] = ColumnRole.X

        return roles

    @classmethod
    def _recommend_plot(cls, df: pd.DataFrame, roles: Dict[str, ColumnRole]) -> str:
        """Determines the most publication-appropriate plot type."""
        y_count = sum(1 for r in roles.values() if r == ColumnRole.Y)
        has_err = any(r == ColumnRole.Y_ERR for r in roles.values())

        if has_err:
            return "errorbar"

        # Check for continuous spectral/diffraction profiles
        col_names_str = " ".join(str(c).lower() for c in df.columns)
        if any(k in col_names_str for k in ["omega", "2theta", "twotheta", "diffract", "intensity", "counts", "wavelength", "retention"]):
            return "line"

        if y_count > 1 and len(df) < 50:
            return "line_symbol"
        if len(df) < 20:
            return "line_symbol"
        return "line"

    @classmethod
    def _contains_multiple_numbers(cls, line: str) -> bool:
        """Checks if a text line contains 2 or more numeric tokens."""
        tokens = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", line)
        return len(tokens) >= 2

    @classmethod
    def _fallback_parse_lines(cls, lines: List[str]) -> pd.DataFrame:
        """Robust line-by-line regex fallback parser for irregular whitespace/tabs."""
        rows = []
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            parts = re.split(r"[,\t;|\s]+", line_str)
            if parts:
                rows.append(parts)

        if not rows:
            return pd.DataFrame()

        # If first row contains strings and second contains numbers, treat first as header
        first_row_numbers = sum(1 for x in rows[0] if re.match(r"^[-+]?\d*\.?\d+", x))
        has_header = first_row_numbers < len(rows[0]) * 0.5

        if has_header and len(rows) > 1:
            header = rows[0]
            data = rows[1:]
        else:
            header = [f"Col{i+1}" for i in range(len(rows[0]))]
            data = rows

        if not data:
            data = [header]
            header = [f"Col{i+1}" for i in range(len(header))]

        max_cols = max(len(r) for r in ([header] + data))
        if len(header) < max_cols:
            header = header + [f"Col{i+1}" for i in range(len(header), max_cols)]
        elif len(header) > max_cols:
            header = header[:max_cols]

        clean_data = [r + [None] * (max_cols - len(r)) if len(r) < max_cols else r[:max_cols] for r in data]
        return pd.DataFrame(clean_data, columns=header)

    @classmethod
    def _extract_from_x01(cls, filepath: str, custom_prompt: str = "") -> ExtractionResult:
        """
        Specialized extractor for .x01/.X01 files (XRD rocking curves, epitaxial scans,
        diffractometers, Bede Scientific, Philips/PANalytical, and sequential lab detectors).
        Handles both ASCII formatted scans and binary telemetry/scan blocks.
        """
        basename = os.path.basename(filepath)
        try:
            with open(filepath, "rb") as f:
                raw_bytes = f.read()
        except Exception as e:
            raise IOError(f"Could not read {filepath}: {e}")

        # Check if file has null bytes or unprintable bytes indicating binary format
        sample_chunk = raw_bytes[:min(4096, len(raw_bytes))]
        null_count = sample_chunk.count(b"\x00")
        is_binary = null_count > 2

        if not is_binary:
            # ASCII text format
            try:
                content = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                content = raw_bytes.decode("latin-1", errors="replace")
            return cls._parse_x01_ascii(content, source_name=basename)
        else:
            # Binary format
            return cls._parse_x01_binary(raw_bytes, source_name=basename)

    @classmethod
    def _parse_x01_ascii(cls, text: str, source_name: str = "Scan.x01") -> ExtractionResult:
        """
        Parses ASCII .x01 XRD/rocking curve/detector files.
        Extracts key-value header parameters, identifies data start,
        handles Omega, 2Theta, Angle, Intensity, Counts, CPS,
        and constructs high-accuracy column roles and units.
        """
        lines = text.strip().splitlines()
        if not lines:
            return ExtractionResult(pd.DataFrame(), {}, {}, {}, notes="Empty .x01 file.")

        metadata: Dict[str, Any] = {}
        data_start_idx = 0
        header_keys = []

        for idx, line in enumerate(lines):
            line_str = line.strip()
            if not line_str:
                continue

            # Check section markers like [Header], [Data], [Scan], *Scan Data*
            if line_str.startswith("[") and line_str.endswith("]"):
                sec_name = line_str[1:-1].strip()
                if sec_name.lower() in ["data", "scan", "scandata", "results"]:
                    data_start_idx = idx + 1
                    break
                continue

            if line_str.lower().startswith("data:"):
                data_start_idx = idx + 1
                break

            # Comments or metadata lines
            clean_str = line_str.lstrip("#;/*!%@ ").strip()
            if "=" in clean_str:
                k, v = clean_str.split("=", 1)
                metadata[k.strip()] = v.strip()
                continue
            elif ":" in clean_str and not cls._contains_multiple_numbers(clean_str):
                k, v = clean_str.split(":", 1)
                metadata[k.strip()] = v.strip()
                continue

            # If the line contains letters that look like column names (e.g. Omega Counts, Angle Intensity)
            tokens = re.split(r"[,\t;|\s]+", line_str)
            if len(tokens) >= 2 and any(t.lower() in cls.X_KEYWORDS + ["omega", "2theta", "angle", "counts", "intensity", "cps"] for t in tokens):
                header_keys = tokens
                data_start_idx = idx + 1
                break

            # If line has multiple numbers, this is where numerical scan points begin!
            if cls._contains_multiple_numbers(line_str):
                data_start_idx = idx
                break

        data_lines = lines[data_start_idx:]
        if not data_lines:
            # Fall back to standard extract_from_text
            return cls.extract_from_text(text, source_name=source_name)

        # Detect delimiter and load into DataFrame
        sample_chunk = "\n".join(data_lines[:min(25, len(data_lines))])
        delimiter = cls._detect_delimiter(sample_chunk)

        try:
            if delimiter == r"\s+":
                df = pd.read_csv(io.StringIO("\n".join(data_lines)), sep=r"\s+", header=None, engine="python")
            else:
                df = pd.read_csv(io.StringIO("\n".join(data_lines)), sep=delimiter, header=None, engine="python")
        except Exception:
            df = cls._fallback_parse_lines(data_lines)

        # If first row is headers (text)
        first_row_numbers = sum(1 for x in df.iloc[0] if str(x).replace(".", "", 1).replace("-", "", 1).isdigit()) if len(df) > 0 else 0
        if len(df) > 1 and first_row_numbers < len(df.columns) * 0.5:
            df.columns = [str(x) for x in df.iloc[0]]
            df = df.iloc[1:].reset_index(drop=True)
        elif header_keys and len(header_keys) == len(df.columns):
            df.columns = header_keys
        else:
            # Infer standard XRD columns based on column count and metadata
            col_count = len(df.columns)
            if col_count == 2:
                scan_mode = str(metadata.get("Scan Mode", metadata.get("Scan Type", metadata.get("Scan", "")))).lower()
                if "2theta" in scan_mode:
                    df.columns = ["2Theta (deg)", "Intensity (Counts)"]
                elif "omega" in scan_mode or "rocking" in scan_mode:
                    df.columns = ["Omega (arcsec)", "Intensity (Counts)"]
                else:
                    df.columns = ["Angle (deg)", "Intensity (Counts)"]
            elif col_count >= 3:
                df.columns = ["Angle (deg)", "Intensity (Counts)", "Error"] + [f"Col{i+1}" for i in range(3, col_count)]
            else:
                df.columns = [f"Col{i+1}" for i in range(col_count)]

        # Parse units and headers
        df, col_units, col_long_names = cls._parse_headers_and_units(df)

        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(how="all", axis=1)

        col_roles = cls._infer_column_roles(df, col_long_names)

        rec_plot = "line"
        notes = f"XRD / Rocking Curve scan extracted from {source_name} ({len(df)} points)."
        if metadata:
            notes += f" Meta: {', '.join(f'{k}={v}' for k, v in list(metadata.items())[:3])}"

        return ExtractionResult(
            dataframe=df,
            column_roles=col_roles,
            column_units=col_units,
            column_long_names=col_long_names,
            recommended_plot=rec_plot,
            metadata=metadata,
            notes=notes,
        )

    @classmethod
    def _parse_x01_binary(cls, raw_bytes: bytes, source_name: str = "Scan.x01") -> ExtractionResult:
        """
        Parses binary .x01 files (e.g., proprietary Bede / Philips XRD rocking curves).
        Extracts embedded ASCII metadata strings, sniffs float array payload,
        and constructs monotonic angular axis with intensity counts.
        """
        metadata: Dict[str, Any] = {"Format": "Binary .x01"}

        # 1. Extract printable ASCII strings from header
        ascii_matches = re.findall(b"[ -~]{4,}", raw_bytes[:1024])
        for match in ascii_matches:
            s = match.decode("latin-1", errors="ignore").strip()
            if "=" in s:
                k, v = s.split("=", 1)
                metadata[k.strip()] = v.strip()
            elif ":" in s:
                k, v = s.split(":", 1)
                metadata[k.strip()] = v.strip()

        # 2. Search for numeric payloads (float32, float64, int32)
        data_arr = None
        for offset in [512, 256, 128, 64, 0, 1024]:
            if offset >= len(raw_bytes):
                continue
            payload = raw_bytes[offset:]
            if len(payload) < 16:
                continue

            # Try float32
            if len(payload) % 4 == 0:
                arr32 = np.frombuffer(payload, dtype="<f4")
                if np.all(np.isfinite(arr32)) and len(arr32) >= 8:
                    if np.any(arr32 > 0) and not np.all(arr32 == 0):
                        data_arr = arr32
                        break

            # Try float64
            if len(payload) % 8 == 0:
                arr64 = np.frombuffer(payload, dtype="<f8")
                if np.all(np.isfinite(arr64)) and len(arr64) >= 8:
                    if np.any(arr64 > 0) and not np.all(arr64 == 0):
                        data_arr = arr64
                        break

        if data_arr is None:
            rem = len(raw_bytes) % 4
            trimmed = raw_bytes[:-rem] if rem > 0 else raw_bytes
            arr = np.frombuffer(trimmed, dtype="<f4")
            finite_mask = np.isfinite(arr)
            data_arr = arr[finite_mask] if np.any(finite_mask) else np.arange(10, dtype=float)

        # Check if data is paired (x, y) coordinates
        if len(data_arr) >= 20 and len(data_arr) % 2 == 0:
            x_cand = data_arr[0::2]
            y_cand = data_arr[1::2]
            diffs = np.diff(x_cand)
            if np.all(diffs > 0) or np.all(diffs < 0):
                df = pd.DataFrame({"Angle (arcsec)": x_cand, "Intensity (Counts)": y_cand})
                col_roles = {"Angle (arcsec)": ColumnRole.X, "Intensity (Counts)": ColumnRole.Y}
                col_units = {"Angle (arcsec)": "arcsec", "Intensity (Counts)": "Counts"}
                col_long_names = {"Angle (arcsec)": "Angle", "Intensity (Counts)": "Intensity"}
                return ExtractionResult(
                    dataframe=df,
                    column_roles=col_roles,
                    column_units=col_units,
                    column_long_names=col_long_names,
                    recommended_plot="line",
                    metadata=metadata,
                    notes=f"Binary .x01 parsed as (X, Y) curve ({len(df)} points).",
                )

        # Single stream of intensities: construct angular coordinate
        start_angle = -1000.0
        step_size = 5.0
        for k, v in metadata.items():
            kl = k.lower()
            if "start" in kl:
                m = re.search(r"[-+]?\d*\.?\d+", str(v))
                if m:
                    start_angle = float(m.group(0))
            if "step" in kl:
                m = re.search(r"[-+]?\d*\.?\d+", str(v))
                if m:
                    step_size = float(m.group(0))

        n = len(data_arr)
        angles = start_angle + np.arange(n) * step_size
        df = pd.DataFrame({"Omega (arcsec)": angles, "Intensity (Counts)": data_arr})
        col_roles = {"Omega (arcsec)": ColumnRole.X, "Intensity (Counts)": ColumnRole.Y}
        col_units = {"Omega (arcsec)": "arcsec", "Intensity (Counts)": "Counts"}
        col_long_names = {"Omega (arcsec)": "Omega", "Intensity (Counts)": "Intensity"}

        return ExtractionResult(
            dataframe=df,
            column_roles=col_roles,
            column_units=col_units,
            column_long_names=col_long_names,
            recommended_plot="line",
            metadata=metadata,
            notes=f"Binary .x01 intensity array parsed ({n} points).",
        )
