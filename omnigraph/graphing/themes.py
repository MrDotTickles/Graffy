"""
Scientific Graph Themes and Styling Presets.
Includes Origin Classic, Nature Publication, Science/Cell, Modern Dark, Prism, and High-Contrast B&W.
"""

from typing import Dict, Any, List


THEMES: Dict[str, Dict[str, Any]] = {
    "Origin Classic": {
        "figure.facecolor": "#ffffff",
        "axes.facecolor": "#ffffff",
        "axes.edgecolor": "#000000",
        "axes.linewidth": 1.2,
        "axes.labelcolor": "#000000",
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "axes.labelweight": "bold",
        "axes.spines.top": True,
        "axes.spines.right": True,
        "axes.spines.bottom": True,
        "axes.spines.left": True,
        "xtick.color": "#000000",
        "ytick.color": "#000000",
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.top": True,
        "ytick.right": True,
        "xtick.minor.visible": True,
        "ytick.minor.visible": True,
        "xtick.major.size": 6,
        "xtick.minor.size": 3.5,
        "ytick.major.size": 6,
        "ytick.minor.size": 3.5,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "legend.frameon": True,
        "legend.facecolor": "#ffffff",
        "legend.edgecolor": "#000000",
        "legend.framealpha": 0.9,
        "legend.fontsize": 10,
        "palette": [
            "#000000",  # Black
            "#d62728",  # Red
            "#1f77b4",  # Blue
            "#2ca02c",  # Green
            "#ff7f0e",  # Orange
            "#9467bd",  # Purple
            "#8c564b",  # Brown
            "#e377c2",  # Pink
        ],
    },
    "Nature": {
        "figure.facecolor": "#ffffff",
        "axes.facecolor": "#ffffff",
        "axes.edgecolor": "#333333",
        "axes.linewidth": 1.0,
        "axes.labelcolor": "#111111",
        "axes.titlesize": 12,
        "axes.titleweight": "normal",
        "axes.labelsize": 10,
        "axes.labelweight": "normal",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.bottom": True,
        "axes.spines.left": True,
        "xtick.color": "#333333",
        "ytick.color": "#333333",
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.top": False,
        "ytick.right": False,
        "xtick.minor.visible": False,
        "ytick.minor.visible": False,
        "xtick.major.size": 4.5,
        "ytick.major.size": 4.5,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "legend.frameon": False,
        "legend.fontsize": 9,
        "palette": [
            "#e64b35",  # Nature Red
            "#4dbbd5",  # Nature Cyan
            "#00a087",  # Nature Teal
            "#3c5488",  # Nature Navy
            "#f39b7f",  # Nature Coral
            "#8491b4",  # Nature Slate
            "#91d1c2",  # Nature Mint
            "#dc0000",  # Dark Red
        ],
    },
    "Science": {
        "figure.facecolor": "#ffffff",
        "axes.facecolor": "#ffffff",
        "axes.edgecolor": "#222222",
        "axes.linewidth": 1.0,
        "axes.labelcolor": "#222222",
        "axes.titlesize": 12,
        "axes.titleweight": "normal",
        "axes.labelsize": 10,
        "axes.labelweight": "normal",
        "axes.spines.top": True,
        "axes.spines.right": True,
        "axes.spines.bottom": True,
        "axes.spines.left": True,
        "xtick.color": "#222222",
        "ytick.color": "#222222",
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.top": True,
        "ytick.right": True,
        "xtick.minor.visible": True,
        "ytick.minor.visible": True,
        "xtick.major.size": 5,
        "ytick.major.size": 5,
        "xtick.minor.size": 3,
        "ytick.minor.size": 3,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans"],
        "legend.frameon": True,
        "legend.facecolor": "#ffffff",
        "legend.edgecolor": "#cccccc",
        "legend.fontsize": 9.5,
        "palette": [
            "#0C5DA5",  # Science Blue
            "#00B945",  # Science Green
            "#FF9500",  # Science Amber
            "#FF2C00",  # Science Crimson
            "#845B97",  # Science Purple
            "#474747",  # Science Charcoal
            "#9e9e9e",  # Science Gray
        ],
    },
    "Modern Dark": {
        "figure.facecolor": "#181825",
        "axes.facecolor": "#1e1e2e",
        "axes.edgecolor": "#45475a",
        "axes.linewidth": 1.2,
        "axes.labelcolor": "#cdd6f4",
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "axes.labelweight": "normal",
        "axes.spines.top": True,
        "axes.spines.right": True,
        "axes.spines.bottom": True,
        "axes.spines.left": True,
        "xtick.color": "#a6adc8",
        "ytick.color": "#a6adc8",
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.top": True,
        "ytick.right": True,
        "xtick.minor.visible": True,
        "ytick.minor.visible": True,
        "xtick.major.size": 5,
        "ytick.major.size": 5,
        "xtick.minor.size": 3,
        "ytick.minor.size": 3,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "font.family": "sans-serif",
        "font.sans-serif": ["Segoe UI", "Arial", "DejaVu Sans"],
        "legend.frameon": True,
        "legend.facecolor": "#1e1e2e",
        "legend.edgecolor": "#45475a",
        "legend.framealpha": 0.95,
        "legend.fontsize": 10,
        "palette": [
            "#89b4fa",  # Neon Blue
            "#f38ba8",  # Neon Red/Pink
            "#a6e3a1",  # Neon Green
            "#fab387",  # Neon Peach
            "#cba6f7",  # Neon Mauve
            "#94e2d5",  # Neon Teal
            "#f9e2af",  # Neon Yellow
        ],
    },
    "Prism": {
        "figure.facecolor": "#ffffff",
        "axes.facecolor": "#ffffff",
        "axes.edgecolor": "#000000",
        "axes.linewidth": 1.2,
        "axes.labelcolor": "#000000",
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "axes.labelweight": "bold",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.bottom": True,
        "axes.spines.left": True,
        "xtick.color": "#000000",
        "ytick.color": "#000000",
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.top": False,
        "ytick.right": False,
        "xtick.minor.visible": False,
        "ytick.minor.visible": False,
        "xtick.major.size": 5,
        "ytick.major.size": 5,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "legend.frameon": False,
        "legend.fontsize": 10,
        "palette": [
            "#0072b2",  # Deep Blue
            "#d55e00",  # Vermilion
            "#009e73",  # Bluish Green
            "#cc79a7",  # Reddish Purple
            "#56b4e9",  # Sky Blue
            "#e69f00",  # Orange
            "#f0e442",  # Yellow
        ],
    },
    "High-Contrast B&W": {
        "figure.facecolor": "#ffffff",
        "axes.facecolor": "#ffffff",
        "axes.edgecolor": "#000000",
        "axes.linewidth": 1.4,
        "axes.labelcolor": "#000000",
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "axes.labelweight": "bold",
        "axes.spines.top": True,
        "axes.spines.right": True,
        "axes.spines.bottom": True,
        "axes.spines.left": True,
        "xtick.color": "#000000",
        "ytick.color": "#000000",
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.top": True,
        "ytick.right": True,
        "xtick.minor.visible": True,
        "ytick.minor.visible": True,
        "xtick.major.size": 6,
        "ytick.major.size": 6,
        "xtick.minor.size": 3.5,
        "ytick.minor.size": 3.5,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans"],
        "legend.frameon": True,
        "legend.facecolor": "#ffffff",
        "legend.edgecolor": "#000000",
        "legend.fontsize": 10,
        "palette": [
            "#000000",  # Black
            "#555555",  # Dark Gray
            "#888888",  # Medium Gray
            "#aaaaaa",  # Light Gray
        ],
    },
    "Colorblind Safe": {
        "figure.facecolor": "#ffffff",
        "axes.facecolor": "#ffffff",
        "axes.edgecolor": "#1e293b",
        "axes.linewidth": 1.1,
        "axes.labelcolor": "#0f172a",
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.labelsize": 10.5,
        "axes.labelweight": "bold",
        "axes.spines.top": True,
        "axes.spines.right": True,
        "axes.spines.bottom": True,
        "axes.spines.left": True,
        "xtick.color": "#1e293b",
        "ytick.color": "#1e293b",
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.top": False,
        "ytick.right": False,
        "xtick.minor.visible": False,
        "ytick.minor.visible": False,
        "xtick.major.size": 5,
        "ytick.major.size": 5,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "legend.frameon": True,
        "legend.facecolor": "#ffffff",
        "legend.edgecolor": "#cbd5e1",
        "legend.fontsize": 9.5,
        "palette": [
            "#0072b2",  # Blue
            "#d55e00",  # Vermilion
            "#009e73",  # Bluish Green
            "#e69f00",  # Orange
            "#56b4e9",  # Sky Blue
            "#cc79a7",  # Reddish Purple
            "#f0e442",  # Yellow
            "#000000",  # Black
        ],
    },
    "ColorBrewer Set1": {
        "figure.facecolor": "#ffffff",
        "axes.facecolor": "#ffffff",
        "axes.edgecolor": "#334155",
        "axes.linewidth": 1.1,
        "axes.labelcolor": "#0f172a",
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.labelsize": 10.5,
        "axes.labelweight": "normal",
        "axes.spines.top": True,
        "axes.spines.right": True,
        "axes.spines.bottom": True,
        "axes.spines.left": True,
        "xtick.color": "#334155",
        "ytick.color": "#334155",
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.top": True,
        "ytick.right": True,
        "xtick.minor.visible": True,
        "ytick.minor.visible": True,
        "xtick.major.size": 5,
        "ytick.major.size": 5,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "legend.frameon": True,
        "legend.facecolor": "#ffffff",
        "legend.edgecolor": "#cbd5e1",
        "legend.fontsize": 9.5,
        "palette": [
            "#e41a1c",  # Red
            "#377eb8",  # Blue
            "#4daf4a",  # Green
            "#984ea3",  # Purple
            "#ff7f00",  # Orange
            "#a65628",  # Brown
            "#f781bf",  # Pink
            "#999999",  # Gray
        ],
    },
}


def apply_theme_to_axes(ax, theme_name: str, box_frame: bool = True, tick_direction: str = "in"):
    """Applies theme styling to a matplotlib Axes object."""
    theme = THEMES.get(theme_name, THEMES["Origin Classic"])

    # Spines
    ax.spines["bottom"].set_color(theme["axes.edgecolor"])
    ax.spines["bottom"].set_linewidth(theme["axes.linewidth"])
    ax.spines["left"].set_color(theme["axes.edgecolor"])
    ax.spines["left"].set_linewidth(theme["axes.linewidth"])

    if box_frame:
        ax.spines["top"].set_visible(True)
        ax.spines["right"].set_visible(True)
        ax.spines["top"].set_color(theme["axes.edgecolor"])
        ax.spines["top"].set_linewidth(theme["axes.linewidth"])
        ax.spines["right"].set_color(theme["axes.edgecolor"])
        ax.spines["right"].set_linewidth(theme["axes.linewidth"])
    else:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # Ticks
    direction = tick_direction if tick_direction in ("in", "out", "inout") else theme["xtick.direction"]
    top_ticks = box_frame and (direction == "in")
    right_ticks = box_frame and (direction == "in")

    ax.tick_params(
        axis="x",
        which="major",
        direction=direction,
        color=theme["xtick.color"],
        labelcolor=theme["xtick.color"],
        labelsize=theme["xtick.labelsize"],
        length=theme["xtick.major.size"],
        top=top_ticks,
    )
    ax.tick_params(
        axis="y",
        which="major",
        direction=direction,
        color=theme["ytick.color"],
        labelcolor=theme["ytick.color"],
        labelsize=theme["ytick.labelsize"],
        length=theme["ytick.major.size"],
        right=right_ticks,
    )

    if theme.get("xtick.minor.visible", False):
        ax.minorticks_on()
        ax.tick_params(
            axis="x",
            which="minor",
            direction=direction,
            color=theme["xtick.color"],
            length=theme.get("xtick.minor.size", 3),
            top=top_ticks,
        )
        ax.tick_params(
            axis="y",
            which="minor",
            direction=direction,
            color=theme["ytick.color"],
            length=theme.get("ytick.minor.size", 3),
            right=right_ticks,
        )

    # Facecolor
    ax.set_facecolor(theme["axes.facecolor"])


def get_theme_palette(theme_name: str) -> List[str]:
    theme = THEMES.get(theme_name, THEMES["Origin Classic"])
    return theme.get("palette", THEMES["Origin Classic"]["palette"])
