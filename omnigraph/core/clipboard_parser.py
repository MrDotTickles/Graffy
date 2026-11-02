"""
Universal scientific clipboard table parser.
Extracts rows and columns from clipboard data (HTML tables, TSV, CSV, semicolon,
space/whitespace delimited, and Markdown tables) and detects column headers/units.
Guarantees that copied tables from outside apps never collapse into a single cell.
"""

import re
import csv
import io
from html.parser import HTMLParser
from typing import List, Tuple, Any, Optional


class HTMLTableExtractor(HTMLParser):
    """Parses HTML tables from clipboard into 2D string grid."""

    def __init__(self):
        super().__init__()
        self.rows: List[List[str]] = []
        self._curr_row: List[str] = []
        self._curr_cell: List[str] = []
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag.lower() in ("td", "th"):
            self._in_cell = True
            self._curr_cell = []
        elif tag.lower() == "tr":
            self._curr_row = []

    def handle_endtag(self, tag):
        if tag.lower() in ("td", "th"):
            self._in_cell = False
            cell_text = "".join(self._curr_cell).strip()
            self._curr_row.append(cell_text)
        elif tag.lower() == "tr":
            if self._curr_row:
                self.rows.append(self._curr_row)
                self._curr_row = []

    def handle_data(self, data):
        if self._in_cell:
            self._curr_cell.append(data)


class ClipboardTableParser:
    """Universal parser for tables copied from Excel, Google Sheets, browsers, PDFs, and text."""

    @classmethod
    def parse_clipboard(cls, text: str, html: Optional[str] = None) -> List[List[Any]]:
        """
        Parses table into a 2D list of typed values (floats, strings, or None).
        Handles HTML tables, TSV, CSV, semicolons, Markdown, and whitespace delimiters.
        """
        # 1. Try HTML table if present (common when copying from Excel, Google Sheets, or web)
        if html and ("<table" in html.lower() or "<tr" in html.lower()):
            try:
                parser = HTMLTableExtractor()
                parser.feed(html)
                if parser.rows and any(len(r) > 1 for r in parser.rows):
                    return cls._convert_cells(parser.rows)
            except Exception:
                pass

        if not text:
            return []

        # Normalize line endings
        norm_text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not norm_text:
            return []

        raw_lines = [line.strip() for line in norm_text.split("\n")]
        lines = [line for line in raw_lines if line]
        if not lines:
            return []

        # 2. Check for Markdown table (starts and ends with |)
        if all(line.startswith("|") and line.endswith("|") for line in lines):
            parsed_rows = []
            for line in lines:
                if re.match(r"^\|[\s\-:|]+\|$", line):
                    continue
                tokens = [t.strip() for t in line.strip("|").split("|")]
                parsed_rows.append(tokens)
            if parsed_rows:
                return cls._convert_cells(parsed_rows)

        # 3. Check for Tab-separated values (TSV - default for Excel and Google Sheets)
        if any("\t" in line for line in lines):
            parsed_rows = [line.split("\t") for line in lines]
            return cls._convert_cells(parsed_rows)

        # 4. Check for CSV (comma-separated with quote awareness)
        if any("," in line for line in lines):
            try:
                reader = csv.reader(io.StringIO(norm_text))
                parsed_rows = [row for row in reader if row]
                if parsed_rows and any(len(r) > 1 for r in parsed_rows):
                    return cls._convert_cells(parsed_rows)
            except Exception:
                pass

        # 5. Check for Semicolon-separated (European Excel CSV)
        if any(";" in line for line in lines):
            try:
                reader = csv.reader(io.StringIO(norm_text), delimiter=";")
                parsed_rows = [row for row in reader if row]
                if parsed_rows and any(len(r) > 1 for r in parsed_rows):
                    return cls._convert_cells(parsed_rows)
            except Exception:
                pass

        # 6. Space-separated or multi-space whitespace delimited (terminal outputs, PDF tables, logs)
        parsed_rows = []
        for line in lines:
            tokens = re.split(r"\t+|\s{2,}|\s+", line.strip())
            parsed_rows.append(tokens)

        return cls._convert_cells(parsed_rows)

    @classmethod
    def _convert_cells(cls, raw_table: List[List[str]]) -> List[List[Any]]:
        """Converts string tokens to typed floats, strings, or None."""
        table = []
        for row in raw_table:
            row_vals = []
            for cell in row:
                token = cell.strip()
                if token == "" or token.lower() in ("nan", "none", "null"):
                    row_vals.append(None)
                else:
                    try:
                        val = float(token)
                    except ValueError:
                        # Check European decimal comma (e.g. 12,5)
                        if "," in token and "." not in token:
                            try:
                                val = float(token.replace(",", "."))
                            except ValueError:
                                val = token
                        else:
                            val = token
                    row_vals.append(val)
            table.append(row_vals)
        return table

    @classmethod
    def detect_headers(cls, table: List[List[Any]]) -> Tuple[bool, Optional[List[str]], List[List[Any]]]:
        """
        Detects if row 0 of a table contains column names while subsequent rows contain data.
        Returns: (has_headers, header_names, remaining_data_rows)
        """
        if len(table) < 2:
            return False, None, table

        row0 = table[0]
        data_rows = table[1:]

        # Row 0 must be predominantly non-numeric strings
        non_num_count_0 = sum(1 for val in row0 if isinstance(val, str) and val.strip())
        if non_num_count_0 < len(row0) * 0.5:
            return False, None, table

        # Subsequent rows must have numeric values
        num_count_sub = sum(
            1 for r in data_rows for val in r if isinstance(val, (int, float))
        )
        total_sub_cells = sum(len(r) for r in data_rows)

        if total_sub_cells > 0 and (num_count_sub / total_sub_cells) >= 0.4:
            headers = [str(v).strip() if v is not None else f"Col {i+1}" for i, v in enumerate(row0)]
            return True, headers, data_rows

        return False, None, table

    @staticmethod
    def extract_name_and_units(header_text: str) -> Tuple[str, str]:
        """
        Extracts column long name and units from a header string.
        Examples:
            'Wavelength (nm)' -> ('Wavelength', 'nm')
            'Absorbance [a.u.]' -> ('Absorbance', 'a.u.')
            'Velocity / m/s' -> ('Velocity', 'm/s')
            'Concentration' -> ('Concentration', '')
        """
        if not header_text:
            return "", ""

        # Match (units) or [units]
        m = re.match(r"^(.*?)\s*[\(\[]([^\)\]]+)[\)\]]\s*$", header_text)
        if m:
            return m.group(1).strip(), m.group(2).strip()

        # Match / units
        m = re.match(r"^(.*?)\s*/\s*([a-zA-Z%µμ\d\^]+[\w\-\./]*)\s*$", header_text)
        if m:
            return m.group(1).strip(), m.group(2).strip()

        return header_text.strip(), ""
