"""
Descriptive statistics, hypothesis tests (t-test), and correlation matrix.
"""

from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from scipy import stats
from omnigraph.core.worksheet import Column


class StatisticsAnalyzer:
    """Computes descriptive and comparative statistical tests."""

    @staticmethod
    def column_summary_table(columns: List[Column]) -> List[Dict[str, Any]]:
        """Returns statistical summaries for a list of columns."""
        results = []
        for col in columns:
            s = col.stats()
            s["column_name"] = col.name
            s["long_name"] = col.long_name
            s["label"] = col.display_label
            results.append(s)
        return results

    @staticmethod
    def two_sample_ttest(
        col1: Column,
        col2: Column,
        paired: bool = False,
        equal_var: bool = True,
    ) -> Dict[str, Any]:
        """Performs two-sample t-test (independent or paired)."""
        arr1 = col1.to_numpy_array()
        arr2 = col2.to_numpy_array()

        if paired:
            # Pairwise complete rows
            n = min(len(arr1), len(arr2))
            valid = (~np.isnan(arr1[:n])) & (~np.isnan(arr2[:n]))
            v1, v2 = arr1[:n][valid], arr2[:n][valid]
            if len(v1) < 2:
                raise ValueError("Paired t-test requires at least 2 valid paired points.")
            res = stats.ttest_rel(v1, v2)
            dof = len(v1) - 1
            mean_diff = float(np.mean(v1 - v2))
        else:
            v1 = arr1[~np.isnan(arr1)]
            v2 = arr2[~np.isnan(arr2)]
            if len(v1) < 2 or len(v2) < 2:
                raise ValueError("Independent t-test requires at least 2 valid points per group.")
            res = stats.ttest_ind(v1, v2, equal_var=equal_var)
            dof = (len(v1) + len(v2) - 2) if equal_var else None
            mean_diff = float(np.mean(v1) - np.mean(v2))

        return {
            "test_type": "Paired t-test" if paired else ("Student's t-test" if equal_var else "Welch's t-test"),
            "col1_name": col1.display_label,
            "col2_name": col2.display_label,
            "t_statistic": float(res.statistic),
            "p_value": float(res.pvalue),
            "dof": dof,
            "mean_difference": mean_diff,
            "n1": len(v1),
            "n2": len(v2),
            "significant_005": bool(res.pvalue < 0.05),
            "significant_001": bool(res.pvalue < 0.01),
        }

    @staticmethod
    def correlation_matrix(columns: List[Column]) -> Tuple[List[str], np.ndarray, np.ndarray]:
        """
        Calculates Pearson correlation matrix and p-value matrix across columns.
        Returns: (labels, r_matrix, p_matrix)
        """
        labels = [c.display_label for c in columns]
        m = len(columns)
        r_mat = np.ones((m, m))
        p_mat = np.zeros((m, m))

        for i in range(m):
            for j in range(i + 1, m):
                x, y, _ = columns[i].get_valid_numeric_pairs(columns[j])
                if len(x) >= 3:
                    r, p = stats.pearsonr(x, y)
                    r_mat[i, j] = r_mat[j, i] = r
                    p_mat[i, j] = p_mat[j, i] = p
                else:
                    r_mat[i, j] = r_mat[j, i] = np.nan
                    p_mat[i, j] = p_mat[j, i] = np.nan

        return labels, r_mat, p_mat

    @staticmethod
    def p_to_stars(p_value: float) -> str:
        """Convert a p-value into publication standard significance stars."""
        if p_value is None or np.isnan(p_value):
            return "ns"
        if p_value < 0.0001:
            return "****"
        elif p_value < 0.001:
            return "***"
        elif p_value < 0.01:
            return "**"
        elif p_value < 0.05:
            return "*"
        return "ns"

    @staticmethod
    def create_significance_bracket(
        x1: float,
        x2: float,
        y: float,
        p_value: Optional[float] = None,
        custom_text: Optional[str] = None,
        h: Optional[float] = None,
        color: str = "#000000",
    ) -> Dict[str, Any]:
        """Creates a significance bracket annotation dictionary."""
        text = custom_text if custom_text is not None else (
            StatisticsAnalyzer.p_to_stars(p_value) if p_value is not None else "***"
        )
        tick_h = h if h is not None else (abs(y) * 0.04 if y != 0 else 0.5)
        return {
            "type": "bracket",
            "x1": float(min(x1, x2)),
            "x2": float(max(x1, x2)),
            "y": float(y),
            "h": float(tick_h),
            "text": str(text),
            "p_value": p_value,
            "color": color,
            "line_width": 1.2,
            "font_size": 11,
        }
