Plot switching final validation: 459 tests passed, 200% editor check and Windows packaged scientific smoke passed. Six changed compiled modules match source. Latest installer is 71,091,092 bytes; see docs/PLOT_SWITCHING.md for checksum and behavior. No commit/push/release.

Latest plot switching update: see docs/PLOT_SWITCHING.md. Shared conversion and matching-series-color helpers live in omnigraph/core/plot_editing.py. GraphModel.plot_axis_settings persists labels/scales by representation. Change plot converts measured series in place; fitted curves remain unchanged. Keep the conversion tests in test_chart_editing_polish.py. The legend retains Apply/Save; the reported color issue was an older installed copy.

Final contrast/editing validation: 441 tests passed, thirteen dialogs checked at 200%, compiled scientific smoke check passed, eighteen packaged modules matched source, indicator SVGs bundled. Installer rebuilt locally (71.1 MB). Source version remains 1.0.1; publish a higher version for update notices. No commit/push/release was performed.

Latest chart/contrast work: see docs/UI_POLISH.md. New reusable ColorField and SeriesEditor controls live in omnigraph/ui/. Legend color/opacity fields are persisted on GraphModel. Automatic palette rendering must not mutate saved curve colors. SVG indicators are bundled under styles/icons/. Keep tests/test_chart_editing_polish.py when modifying these paths.

Final desktop-redesign validation: 429 tests passed; seven dialogs verified at 200% scaling; packaged scientific smoke check passed; fourteen compiled UI modules match source; Windows installer rebuilt (71.1 MB). Local build only; no commit, push, or GitHub release performed in this redesign.

Latest desktop redesign: see docs/DESKTOP_REDESIGN.md. Tab closing is now non-destructive; deleted items must use explicit project Delete actions. The chart editor is a side panel at wide sizes and a separate scrollable window at compact sizes. Named SVG icons live in omnigraph/ui/styles/design.py and shared themes in qss.py. Keep the compact action visibility and tab identity tests when changing navigation.

# Graffy — AI Pair Programming Handover & Context Document

> Latest dialog refresh: 419 full-suite tests passed, plus 36 final focused layout
> checks. Import routes share the local parser; misleading AI branding removed
> from UI. Five task dialogs simplified. See [details](IMPORT_AND_DIALOGS.md).

> Current chart redesign:compact chart toolbar, collapsible Edit chart settings,
> readable Explore navigation, contextual Data→Chart→Export workflow, and blank
> worksheet Import/Paste starter. Full414 tests passed and final packaged smoke
> passed. Matching Windows installer is71.1MB; application files241.1MB.

> Latest package verification: Windows installer **71.2 MB**, application files
> **241.4 MB**. Full suite: 401 passed. Packaged fitting/project/spreadsheet and
> raster/vector-export checks passed. PDF/SVG/EPS backends are explicitly bundled.
> A final installer and size report are retained in `dist/`; local build and Python
> environment copies were removed. See [package details](PACKAGE_SIZE.md).

> Size cleanup: generated `.venv`, `build`, and `dist` folders were removed after
> validation. `scripts/Setup_Graffy.bat` restores Windows development dependencies, and
> launch/release buttons invoke it when the environment is missing. Do not assume
> a local compiled executable or Python environment still exists.

> Current layout (2026-11-02): build/shortcut tools are in `scripts/`; icons have
> one canonical home in `omnigraph/ui/styles/icons/`. This handover is now in
> `docs/`; the legacy manifest is `docs/examples/version.json`. Read
> [RELEASING.md](../RELEASING.md) and [launch readiness](LAUNCH_READINESS.md)
> for current paths and status. The original architecture listing below is historical.
> Current validation: **401 tests passed** and the fresh Windows app passed its
> launch smoke test. GitHub now packages Mac DMGs as well as compatibility ZIPs.
> Core release versions are pinned in `constraints-release.txt`; developers install
> `requirements-dev.txt`, and builders install `requirements-build.txt`.
>
> Release setup update (2026-11-02): see `../RELEASING.md` for the current workflow.
> This folder is now a Git checkout tracking `MrDotTickles/Graffy` on `main`.
> Existing remote tag: `v1.0.0`; no new commit/tag/release was published during setup.
> Startup/six-hour update notices, architecture-specific Mac packages, verified
> downloads, a Windows Inno Setup installer, and `scripts/Release_Graffy.bat` are implemented.
> Shared builds use `scripts/build_app.py` to prevent DLL contamination from PATH.
> Fixed missing `Tuple` / `Optional` imports that blocked startup on Python 3.13.
> Validation: 397 tests passed in the full suite; the focused updater suite then
> passed 25 tests after two additional notification tests were added. A fresh
> Windows PyInstaller package passed `--smoke-test`. macOS builds and installer
> install/upgrade behavior still need the first GitHub run and platform validation.
> The original feature notes below predate these changes; dependencies have minimum
> bounds rather than a lockfile, and Mac updates require manual app replacement.

> **Instructions for the AI Assistant:**  
> Read this document to get 100% up to speed on **Graffy**. This is an active, production-grade Python/PyQt6 scientific graphing and data analysis software suite inspired by OriginLab and GraphPad Prism. The codebase is well-structured, thoroughly tested (382 automated tests, 100% pass rate), and natively cross-platform (Windows & macOS).

---

## 1. Project Overview & Tech Stack

* **Name**: Graffy
* **Author / Repository**: `MrDotTickles/Graffy` (`https://github.com/MrDotTickles/Graffy.git`)
* **Current Version**: `1.0.0` (defined in `omnigraph/__init__.py`)
* **Language & Runtime**: Python 3.10+ (tested through 3.14)
* **GUI Framework**: PyQt6 (Qt 6.5+)
* **Scientific & Data Libraries**: NumPy, SciPy (curve fitting & signal processing), Matplotlib (FigureCanvasQTAgg), Pandas (Excel/CSV I/O), OpenPyXL, Pillow (icon & image rendering)
* **Primary Entry Point**: `python main.py` (supports CLI flags like `--sample spectroscopy`, `--sample kinetics`, `--sample dose_response`, `--sample dual_axis`)

---

## 2. Directory Architecture

```
KyleGraphingSoftware/
├── main.py                     # Main application entry point & sample loader
├── requirements.txt            # Pinned cross-platform Python dependencies
├── scripts/Launch_Graffy.bat           # Windows 1-click launcher
├── scripts/Launch_Graffy.command       # macOS Finder double-clickable launcher
├── build_windows_dist.bat      # 1-click PyInstaller Windows compiler & ZIP packager
├── build_mac_app.sh            # 1-click PyInstaller macOS standalone .app builder
├── Create_Desktop_Shortcut.bat # Windows desktop shortcut creator with custom icon
├── graffy.ico / graffy.icns    # Windows multi-res ICO & Apple Icon Image (16 to 512px)
├── graffy.png                  # Master 512x512 logo
├── version.json                # Update manifest template for cloud / web hosting
├── .github/workflows/          # GitHub Actions CI/CD (auto-builds Windows & Mac on release tag)
│   └── build_releases.yml
├── omnigraph/
│   ├── core/                   # Pure business logic & data structures
│   │   ├── worksheet.py        # Column (with roles X/Y/YErr/XErr/Label/Disregard), Worksheet, Workbook
│   │   ├── project.py          # Project, GraphModel, CurveModel, ReportModel (.kgraph JSON serializer)
│   │   ├── column_formula.py   # Safe mathematical formula engine (supports column names, math, numpy)
│   │   └── updater.py          # GitHub Releases API updater & chunked binary stream downloader
│   ├── analysis/               # Scientific computation engines
│   │   ├── fitting.py          # Linear, Polynomial (deg 2-6), & Non-linear fitting (Gaussian, 4PL Hill, etc.)
│   │   ├── peak_analysis.py    # Peak detection, baseline correction (linear/poly/min), FWHM, AUC
│   │   ├── smoothing.py        # Savitzky-Golay, Moving Average, Numerical Derivatives, FFT
│   │   └── statistics.py       # Descriptive statistics & Two-Sample t-test
│   ├── graphing/               # Matplotlib & PyQt6 rendering bridge
│   │   ├── plot_manager.py     # Bridges GraphModel to FigureCanvas, manages subplots & waterfall offsets
│   │   ├── plot_types.py       # Renderers for Scatter, Line, Bar, Box, Violin, Waterfall, Area, etc.
│   │   ├── themes.py           # Publication themes: Nature, Science, Origin Classic, Modern Dark, Prism
│   │   ├── tools.py            # Origin-style crosshair Data Reader & ROI Range Selector
│   │   └── canvas.py           # Interactive FigureCanvas with pan/zoom and DPI clipboard export
│   └── ui/                     # PyQt6 user interface components
│       ├── main_window.py      # Primary window with 4-step workflow ribbon, menus, tabs, docks
│       ├── spreadsheet_view.py # QTableView with Origin-style headers, undo/redo, -Col / +Col actions
│       ├── graph_view.py       # Embedded canvas with quick graph toolbar, export, and copy
│       ├── report_view.py      # HTML analysis report viewer
│       ├── project_explorer.py # Left dock project tree
│       ├── property_dock.py    # Right dock dynamic real-time styling inspector
│       ├── samples.py          # Pre-built scientific demo datasets
│       ├── dialogs/            # Fit, Peak, Smooth, Formula, Stats, Export, Import, Update dialogs
│       └── styles/             # Modern Light & Dark QSS stylesheets with native Apple & Windows fonts
└── tests/                      # 23 automated pytest test files (382 tests, 100% passing)
```

---

## 3. Key Features Implemented So Far

1. **Worksheet & Data Entry**:
   - Origin-style multi-attribute columns: Column Name (unified from previous Short/Long split), Units, Role (`X`, `Y`, `Y Error`, `X Error`, `Label`, `Disregard`).
   - Local worksheet toolbar: `[ + Col ] [ - Col ] [ Set Role ▾ ] [ 🎯 Mask (M) ▾ ] | [ ↶ Undo ] [ ↷ Redo ]`.
   - Explicit column deletion (`- Col` or `Shift+Delete` / `Shift+Backspace`) prompting with exact column names and full undo/redo snapshot recovery (`Ctrl+Z`, `Ctrl+Y`).
   - Origin formula engine (`fx`): supports column names as direct variables (e.g. `Velocity * 2` or `col('A') + 10`).

2. **Graphing & Publication Styling**:
   - 12+ Scientific Plot Types: Scatter, Line, Line+Symbol, Step, Spline, Bar, Area, Error Bars, Box & Whisker, Violin, Jitter, Waterfall/Offset Spectra, Dose-Response 4PL.
   - Publication Themes: Nature, Science, Origin Classic, Modern Dark, Prism, High-Contrast B&W.
   - Multi-panel Figure Layout Builder (2×2, 1×2, 2×1 subplots with publication labels `(A)`, `(B)`).
   - High-DPI & Retina export to PNG, PDF (vector), SVG, TIFF at 150, 300, 600 DPI, and 1-click clipboard copy.

3. **Analysis & Signal Calculus**:
   - Linear regression with 95% Confidence & Prediction Bands.
   - Non-linear curve fitting wizard (SciPy Levenberg-Marquardt): Exponential, Gaussian, Hill/IC50 4PL, Michaelis-Menten.
   - Peak deconvolution: 2-column responsive dialog, baseline subtraction, FWHM, and AUC.
   - Signal smoothing (Savitzky-Golay, Moving Average, FFT, Numerical Derivatives).
   - Outlier masking (`M` hotkey) with automatic live curve fit recalculation.

4. **Cross-Platform Compatibility (Windows & macOS)**:
   - Mac keyboard adaptation: `Shift+Backspace` (MacBook delete) deletes columns.
   - macOS Native Menus: `About` and `Quit` configured with `QAction.MenuRole`.
   - Native Apple San Francisco / SF Mono typography in QSS stylesheets.
   - Double-clickable `scripts/Launch_Graffy.command` for Mac, `scripts/Launch_Graffy.bat` for Windows.

5. **GitHub-Powered In-App Auto-Updater**:
   - Configured out-of-the-box for `MrDotTickles/Graffy`.
   - Available under **Help ➔ Check for Updates...**.
   - Streams downloads in 64 KB chunks in a background thread with a live progress bar.
   - Pairs Mac users with `Graffy_macOS.zip` and Windows users with `Graffy_Windows.zip`.
   - Builds standalone packages via `build_windows_dist.bat` and `build_mac_app.sh`, plus automated GitHub Actions CI/CD (`.github/workflows/build_releases.yml`).

---

## 4. Critical Architectural Rules & Gotchas for the AI

* **Unmanaged Qt Widgets at (0, 0)**: In PyQt6, never instantiate a `QWidget` or `QToolButton` with `parent=self` unless it is explicitly added to a layout (`layout.addWidget(...)`) or toolbar. In Qt, unmanaged child widgets default to position `(0, 0)` and paint over menus or other buttons.
* **Undo/Redo via `QUndoStack`**: Data changes and column additions/deletions must push commands to `worksheet_widget.undo_stack` so that `Ctrl+Z` and `Ctrl+Y` work reliably.
* **Column Name Formula Scope**: The formula engine (`omnigraph/core/column_formula.py`) evaluates mathematical expressions using column names (e.g. `col.name` and normalized `col.long_name`).
* **Test Integrity**: Always maintain the passing state of the automated test suite (`python -m pytest tests/`). Regressions must not be introduced.

---

## 5. How to Run & Test

```bash
# Run application
python main.py

# Run with a pre-loaded sample dataset
python main.py --sample spectroscopy

# Run all 382 automated tests
python -m pytest tests/
```
