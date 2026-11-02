"""
Signal processing, filtering, differentiation, integration, and FFT analysis.
"""

from typing import Tuple, Dict, Any
import numpy as np
from scipy import signal, ndimage, integrate


class SignalProcessor:
    """Methods for signal smoothing, calculus, and Fourier transforms."""

    @staticmethod
    def savitzky_golay(
        y: np.ndarray,
        window_length: int = 11,
        polyorder: int = 2,
    ) -> np.ndarray:
        """Applies Savitzky-Golay smoothing filter preserving peak heights and widths."""
        n = len(y)
        if n < 3:
            return y.copy()
        # window_length must be odd and <= len(y)
        w = min(window_length, n if n % 2 != 0 else n - 1)
        if w <= polyorder:
            w = polyorder + 2 if (polyorder + 2) % 2 != 0 else polyorder + 3
        if w > n:
            return y.copy()
        return signal.savgol_filter(y, window_length=w, polyorder=min(polyorder, w - 1))

    @staticmethod
    def moving_average(y: np.ndarray, window_size: int = 5) -> np.ndarray:
        """Applies moving average boxcar filter."""
        w = max(1, min(window_size, len(y)))
        if w == 1:
            return y.copy()
        box = np.ones(w) / w
        return np.convolve(y, box, mode="same")

    @staticmethod
    def gaussian_filter(y: np.ndarray, sigma: float = 2.0) -> np.ndarray:
        """Applies 1D Gaussian smoothing filter."""
        return ndimage.gaussian_filter1d(y, sigma=max(0.1, sigma))

    @staticmethod
    def derivative_1st(x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Calculates 1st numerical derivative dy/dx."""
        return np.gradient(y, x)

    @staticmethod
    def derivative_2nd(x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Calculates 2nd numerical derivative d²y/dx²."""
        d1 = np.gradient(y, x)
        return np.gradient(d1, x)

    @staticmethod
    def cumulative_integral(x: np.ndarray, y: np.ndarray, initial: float = 0.0) -> np.ndarray:
        """Calculates cumulative trapezoidal integral of y with respect to x."""
        return integrate.cumulative_trapezoid(y, x, initial=initial)

    @staticmethod
    def fft_spectrum(x: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculates one-sided Fast Fourier Transform (FFT) Power Spectrum.
        Returns: (frequencies, power_amplitudes).
        """
        n = len(x)
        if n < 4:
            return np.array([]), np.array([])

        # Assume uniform sampling using average dx
        dx = float(np.mean(np.diff(x))) or 1.0
        # Detrend signal to remove DC offset
        y_detrend = signal.detrend(y)
        fft_vals = np.fft.rfft(y_detrend)
        freqs = np.fft.rfftfreq(n, d=dx)
        magnitudes = 2.0 * np.abs(fft_vals) / n

        return freqs, magnitudes
