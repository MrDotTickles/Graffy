"""
High-precision scientific curve fitting engine.
Provides Linear Regression, Polynomial Fitting, and Non-Linear Curve Fitting
(Exponential, Gaussian, Lorentzian, Hill/Dose-Response, Power Law, Michaelis-Menten, Custom).
Computes R^2, Adjusted R^2, Standard Errors, 95% Confidence & Prediction Bands, and HTML reports.
"""

import math
from typing import Dict, Any, Tuple, Optional, Callable, List
import numpy as np
from scipy import optimize, stats


class FitResult:
    """Stores complete results of a curve fit."""

    def __init__(
        self,
        model_name: str,
        formula_str: str,
        parameters: Dict[str, float],
        param_errors: Dict[str, float],
        r_squared: float,
        adj_r_squared: float,
        rmse: float,
        rss: float,
        dof: int,
        x_dense: np.ndarray,
        y_dense: np.ndarray,
        residuals: np.ndarray,
        x_orig: np.ndarray,
        y_orig: np.ndarray,
        conf_band_lower: Optional[np.ndarray] = None,
        conf_band_upper: Optional[np.ndarray] = None,
        pred_band_lower: Optional[np.ndarray] = None,
        pred_band_upper: Optional[np.ndarray] = None,
        cov_matrix: Optional[np.ndarray] = None,
        success: bool = True,
        message: str = "",
    ):
        self.model_name = model_name
        self.formula_str = formula_str
        self.parameters = parameters
        self.param_errors = param_errors
        self.r_squared = r_squared
        self.adj_r_squared = adj_r_squared
        self.rmse = rmse
        self.rss = rss
        self.dof = dof
        self.x_dense = x_dense
        self.y_dense = y_dense
        self.residuals = residuals
        self.x_orig = x_orig
        self.y_orig = y_orig
        self.conf_band_lower = conf_band_lower
        self.conf_band_upper = conf_band_upper
        self.pred_band_lower = pred_band_lower
        self.pred_band_upper = pred_band_upper
        self.cov_matrix = cov_matrix
        self.success = success
        self.message = message

    def to_html_report(self, *, source="", details=True) -> str:
        """Summarize the model, then show fit quality and parameter estimates."""
        from omnigraph.analysis.reporting import report_document, report_table, result_number

        parameters = []
        for name, value in self.parameters.items():
            error = self.param_errors.get(name)
            interval = (
                f"{result_number(value - 1.96 * error)} to {result_number(value + 1.96 * error)}"
                if error is not None and np.isfinite(error) else "—"
            )
            parameters.append((name, result_number(value), result_number(error), interval))
        summary = [
            ("Equation", self.formula_str),
            ("Points fitted", len(self.x_orig)),
            ("R²", result_number(self.r_squared)),
            ("Root mean square error (RMSE)", result_number(self.rmse)),
        ]
        if details:
            summary.extend([
                ("Adjusted R²", result_number(self.adj_r_squared)),
                ("Residual sum of squares", result_number(self.rss)),
                ("Degrees of freedom", self.dof),
            ])
        table = report_table(
            ("Parameter", "Estimate", "Std. error", "Approx. 95% interval"),
            parameters, numeric=(1, 2, 3),
        )
        return report_document(
            f"Curve fit · {self.model_name}", source=source, summary=summary,
            sections=[("Fitted parameters", table)],
        )


class CurveFitter:
    """Core fitting algorithms for scientific data analysis."""

    @staticmethod
    def linear_fit(
        x: np.ndarray,
        y: np.ndarray,
        fix_intercept: bool = False,
        intercept_val: float = 0.0,
        x_min: Optional[float] = None,
        x_max: Optional[float] = None,
    ) -> FitResult:
        """
        Fits y = m * x + b (or fixed intercept).
        Calculates confidence & prediction bands.
        """
        # Range filter
        mask = np.ones(len(x), dtype=bool)
        if x_min is not None:
            mask &= (x >= x_min)
        if x_max is not None:
            mask &= (x <= x_max)
        x_sub = x[mask]
        y_sub = y[mask]

        n = len(x_sub)
        if n < 2:
            raise ValueError("Linear fit requires at least 2 data points.")

        if fix_intercept:
            # y - b0 = m * x => m = sum((y - b0) * x) / sum(x^2)
            y_adj = y_sub - intercept_val
            m = float(np.sum(y_adj * x_sub) / np.sum(x_sub ** 2))
            b = float(intercept_val)
            dof = n - 1
            y_pred = m * x_sub + b
            residuals = y_sub - y_pred
            rss = float(np.sum(residuals ** 2))
            s_err = math.sqrt(rss / dof) if dof > 0 else 0.0
            se_m = s_err / math.sqrt(np.sum(x_sub ** 2)) if np.sum(x_sub ** 2) > 0 else 0.0
            se_b = 0.0
        else:
            dof = n - 2
            res = stats.linregress(x_sub, y_sub)
            m = float(res.slope)
            b = float(res.intercept)
            se_m = float(res.stderr) if res.stderr is not None else 0.0
            se_b = float(res.intercept_stderr) if res.intercept_stderr is not None else 0.0
            y_pred = m * x_sub + b
            residuals = y_sub - y_pred
            rss = float(np.sum(residuals ** 2))

        # R^2 and Adj-R^2
        ss_tot = float(np.sum((y_sub - np.mean(y_sub)) ** 2))
        r2 = 1.0 - (rss / ss_tot) if ss_tot > 0 else 1.0
        adj_r2 = 1.0 - ((1.0 - r2) * (n - 1) / dof) if dof > 0 and (n - 1) > 0 else r2
        rmse = math.sqrt(rss / dof) if dof > 0 else 0.0

        # Dense evaluation for curve plotting
        x_dense = np.linspace(np.min(x_sub), np.max(x_sub), 200)
        y_dense = m * x_dense + b

        # 95% Confidence Bands & Prediction Bands
        t_val = stats.t.ppf(0.975, dof) if dof > 0 else 1.96
        x_bar = np.mean(x_sub)
        s_xx = np.sum((x_sub - x_bar) ** 2)
        if s_xx > 0:
            se_fit = rmse * np.sqrt(1.0 / n + ((x_dense - x_bar) ** 2) / s_xx)
            se_pred = rmse * np.sqrt(1.0 + 1.0 / n + ((x_dense - x_bar) ** 2) / s_xx)
            conf_low = y_dense - t_val * se_fit
            conf_high = y_dense + t_val * se_fit
            pred_low = y_dense - t_val * se_pred
            pred_high = y_dense + t_val * se_pred
        else:
            conf_low, conf_high = y_dense, y_dense
            pred_low, pred_high = y_dense, y_dense

        params = {"Slope (m)": m, "Intercept (b)": b}
        param_errs = {"Slope (m)": se_m, "Intercept (b)": se_b}

        formula_str = f"y = {m:.4g} * x + {b:.4g}" if b >= 0 else f"y = {m:.4g} * x - {abs(b):.4g}"

        return FitResult(
            model_name="Linear Regression",
            formula_str=formula_str,
            parameters=params,
            param_errors=param_errs,
            r_squared=r2,
            adj_r_squared=adj_r2,
            rmse=rmse,
            rss=rss,
            dof=dof,
            x_dense=x_dense,
            y_dense=y_dense,
            residuals=residuals,
            x_orig=x_sub,
            y_orig=y_sub,
            conf_band_lower=conf_low,
            conf_band_upper=conf_high,
            pred_band_lower=pred_low,
            pred_band_upper=pred_high,
        )

    @staticmethod
    def polynomial_fit(x: np.ndarray, y: np.ndarray, degree: int = 2) -> FitResult:
        """Fits polynomial of given degree (2 to 6)."""
        n = len(x)
        if n <= degree:
            raise ValueError(f"Polynomial of degree {degree} requires at least {degree + 1} data points.")

        dof = n - (degree + 1)
        coeffs, cov = np.polyfit(x, y, degree, cov=True)
        p = np.poly1d(coeffs)

        y_pred = p(x)
        residuals = y - y_pred
        rss = float(np.sum(residuals ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r2 = 1.0 - (rss / ss_tot) if ss_tot > 0 else 1.0
        adj_r2 = 1.0 - ((1.0 - r2) * (n - 1) / dof) if dof > 0 else r2
        rmse = math.sqrt(rss / dof) if dof > 0 else 0.0

        errors = np.sqrt(np.diag(cov))

        params = {}
        param_errs = {}
        eq_parts = []
        for i, c in enumerate(coeffs):
            power = degree - i
            name = f"c_{power}"
            params[name] = float(c)
            param_errs[name] = float(errors[i])
            if power == 0:
                eq_parts.append(f"{c:.4g}")
            elif power == 1:
                eq_parts.append(f"{c:.4g}*x")
            else:
                eq_parts.append(f"{c:.4g}*x^{power}")

        x_dense = np.linspace(np.min(x), np.max(x), 200)
        y_dense = p(x_dense)

        formula_str = "y = " + " + ".join(eq_parts)

        return FitResult(
            model_name=f"Polynomial (Degree {degree})",
            formula_str=formula_str,
            parameters=params,
            param_errors=param_errs,
            r_squared=r2,
            adj_r_squared=adj_r2,
            rmse=rmse,
            rss=rss,
            dof=dof,
            x_dense=x_dense,
            y_dense=y_dense,
            residuals=residuals,
            x_orig=x,
            y_orig=y,
            cov_matrix=cov,
        )

    @staticmethod
    def nonlinear_fit(
        x: np.ndarray,
        y: np.ndarray,
        model_type: Optional[str] = None,
        initial_guesses: Optional[Dict[str, float]] = None,
        custom_func: Optional[Callable] = None,
        custom_param_names: Optional[List[str]] = None,
        custom_formula_str: Optional[str] = None,
        model: Optional[str] = None,
    ) -> FitResult:
        """
        Nonlinear curve fitting for standard scientific models and user-defined equations.
        Models: 'exp_decay', 'exp_growth', 'gaussian', 'lorentzian', 'hill', 'power', 'michaelis_menten', 'custom'
        """
        if model_type is None:
            model_type = model or "gaussian"
        n = len(x)
        if n < 4:
            raise ValueError("Non-linear fitting requires at least 4 data points.")

        # Dispatch built-in models
        if model_type == "exp_decay":
            # y = y0 + A * exp(-x / t)
            func = lambda x, y0, A, t: y0 + A * np.exp(-x / t)
            param_names = ["y0", "A", "t"]
            formula_str = "y = y0 + A * exp(-x / t)"
            # Automatic initial guesses
            y_min, y_max = float(np.min(y)), float(np.max(y))
            x_range = float(np.ptp(x)) or 1.0
            p0 = [y_min, y_max - y_min, max(x_range / 3.0, 1e-6)]

        elif model_type == "exp_growth":
            # y = y0 + A * exp(k * x)
            func = lambda x, y0, A, k: y0 + A * np.exp(np.clip(k * x, -50, 50))
            param_names = ["y0", "A", "k"]
            formula_str = "y = y0 + A * exp(k * x)"
            p0 = [float(np.min(y)), 1.0, 0.1]

        elif model_type == "gaussian":
            # y = y0 + (A / (w * sqrt(pi/2))) * exp(-2 * ((x - xc) / w)^2)
            func = lambda x, y0, xc, w, A: y0 + (A / (w * np.sqrt(np.pi / 2.0))) * np.exp(-2.0 * ((x - xc) / w) ** 2)
            param_names = ["y0 (Baseline)", "xc (Center)", "w (Width)", "A (Area)"]
            formula_str = "y = y0 + (A / (w*√(π/2))) * exp(-2*((x-xc)/w)²)"
            # Smart guesses
            y0_guess = float(np.percentile(y, 10))
            max_idx = np.argmax(y)
            xc_guess = float(x[max_idx])
            height = float(y[max_idx] - y0_guess)
            w_guess = float(np.ptp(x) / 6.0) or 1.0
            A_guess = height * w_guess * np.sqrt(np.pi / 2.0)
            p0 = [y0_guess, xc_guess, max(w_guess, 1e-6), A_guess]

        elif model_type == "lorentzian":
            # y = y0 + (2 * A / pi) * (w / (4 * (x - xc)^2 + w^2))
            func = lambda x, y0, xc, w, A: y0 + (2.0 * A / np.pi) * (w / (4.0 * (x - xc) ** 2 + w ** 2))
            param_names = ["y0 (Baseline)", "xc (Center)", "w (FWHM)", "A (Area)"]
            formula_str = "y = y0 + (2*A/π) * (w / (4*(x-xc)² + w²))"
            y0_guess = float(np.percentile(y, 10))
            max_idx = np.argmax(y)
            xc_guess = float(x[max_idx])
            height = float(y[max_idx] - y0_guess)
            w_guess = float(np.ptp(x) / 6.0) or 1.0
            A_guess = height * w_guess * (np.pi / 2.0)
            p0 = [y0_guess, xc_guess, max(w_guess, 1e-6), A_guess]

        elif model_type == "hill":
            # 4PL / Sigmoidal: y = Bottom + (Top - Bottom) / (1 + 10^((logEC50 - x) * HillSlope))
            func = lambda x, Bottom, Top, logEC50, HillSlope: Bottom + (Top - Bottom) / (
                1.0 + 10.0 ** np.clip((logEC50 - x) * HillSlope, -50, 50)
            )
            param_names = ["Bottom", "Top", "logEC50", "HillSlope"]
            formula_str = "y = Bottom + (Top - Bottom) / (1 + 10^((logEC50 - x) * HillSlope))"
            bot = float(np.min(y))
            top = float(np.max(y))
            mid_x = float(np.median(x))
            p0 = [bot, top, mid_x, 1.0]

        elif model_type == "power":
            # y = a * x^b
            func = lambda x, a, b: a * (np.maximum(x, 1e-12) ** b)
            param_names = ["a", "b"]
            formula_str = "y = a * x^b"
            p0 = [1.0, 1.0]

        elif model_type == "michaelis_menten":
            # v = (Vmax * x) / (Km + x)
            func = lambda x, Vmax, Km: (Vmax * np.maximum(x, 0.0)) / (Km + np.maximum(x, 0.0))
            param_names = ["Vmax", "Km"]
            formula_str = "y = (Vmax * x) / (Km + x)"
            vmax_guess = float(np.max(y))
            half_v = vmax_guess / 2.0
            # find x closest to half_v
            idx = np.argmin(np.abs(y - half_v))
            km_guess = float(x[idx]) if x[idx] > 0 else 1.0
            p0 = [vmax_guess, km_guess]

        elif model_type == "custom":
            if custom_func is None or custom_param_names is None:
                raise ValueError("Custom model requires custom_func and custom_param_names.")
            func = custom_func
            param_names = custom_param_names
            formula_str = custom_formula_str or "y = f(x, ...)"
            p0 = [1.0] * len(param_names)

        else:
            raise ValueError(f"Unknown nonlinear model type: {model_type}")

        # Override initial guesses if user specified
        if initial_guesses:
            for i, p_name in enumerate(param_names):
                if p_name in initial_guesses:
                    p0[i] = initial_guesses[p_name]

        # Fit curve
        try:
            popt, pcov = optimize.curve_fit(func, x, y, p0=p0, maxfev=10000)
        except Exception as e:
            raise RuntimeError(f"Fit did not converge: {e}")

        dof = n - len(param_names)
        y_pred = func(x, *popt)
        residuals = y - y_pred
        rss = float(np.sum(residuals ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r2 = 1.0 - (rss / ss_tot) if ss_tot > 0 else 1.0
        adj_r2 = 1.0 - ((1.0 - r2) * (n - 1) / dof) if dof > 0 else r2
        rmse = math.sqrt(rss / dof) if dof > 0 else 0.0

        # Parameter errors from covariance matrix
        if pcov is not None and not np.isinf(pcov).any():
            errors = np.sqrt(np.abs(np.diag(pcov)))
        else:
            errors = [0.0] * len(popt)

        params_dict = {name: float(popt[i]) for i, name in enumerate(param_names)}
        errors_dict = {name: float(errors[i]) for i, name in enumerate(param_names)}

        if model_type == "hill" and "logEC50" in params_dict:
            log_ec50 = params_dict["logEC50"]
            log_err = errors_dict.get("logEC50", 0.0)
            ec50_val = 10.0 ** log_ec50
            ec50_err = math.log(10.0) * ec50_val * log_err if log_err else 0.0
            params_dict["EC50 / IC50"] = float(ec50_val)
            errors_dict["EC50 / IC50"] = float(ec50_err)

        # Dense fitted line
        x_dense = np.linspace(np.min(x), np.max(x), 300)
        y_dense = func(x_dense, *popt)

        model_display_names = {
            "exp_decay": "Exponential Decay",
            "exp_growth": "Exponential Growth",
            "gaussian": "Gaussian Peak Fit",
            "lorentzian": "Lorentzian Peak Fit",
            "hill": "Dose-Response 4PL (Hill / IC50)",
            "power": "Power Law Fit",
            "michaelis_menten": "Michaelis-Menten Kinetics",
            "custom": "Custom Equation Fit",
        }

        return FitResult(
            model_name=model_display_names.get(model_type, "Non-linear Fit"),
            formula_str=formula_str,
            parameters=params_dict,
            param_errors=errors_dict,
            r_squared=r2,
            adj_r_squared=adj_r2,
            rmse=rmse,
            rss=rss,
            dof=dof,
            x_dense=x_dense,
            y_dense=y_dense,
            residuals=residuals,
            x_orig=x,
            y_orig=y,
            cov_matrix=pcov,
        )
