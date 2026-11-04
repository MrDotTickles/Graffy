# Beginner experience and validation

Prepared November 2, 2026. Download website:
https://graffy-scientific-graphing.recentdream1.chatgpt.site

## Ordinary app users

- Open `START HERE.html` for the quick installation guide.
- On Windows, double-click `Start Graffy.vbs`. It opens the installed app, local
  packaged app, or installer, in that order. Its development fallback uses pythonw.
- After installing, use the Graffy desktop/Start menu shortcut. Mac users open
  Graffy from Applications after dragging it there from the disk image.
- The packaged Windows executable is built with `--windowed`, so it does not open
  a Python console. Console-based development buttons are under `scripts/`.

## Inside Graffy

- A scrollable welcome chooser offers Import, Open project, Example, or Blank.
- New ordinary launches use a blank project instead of an unexplained sample.
- A compact toolbar focuses on Open, Import data, Save, Plot, Analyze, and Export.
- Full scientific tools remain available through menus and View → Show advanced tools.
- The project sidebar folds away below 1100px to preserve the workspace.
- Actual startup adapts minimum window dimensions to available screen space.
- Edited guided projects prompt Save / Discard / Cancel on close or New/Open.
- Update timers begin after the welcome dialog closes, avoiding overlapping modals.

## Checks

- Full regression suite: **414 passed**, including thirteen new chart, welcome, responsive
  layout, advanced-tool restoration, and cancel-before-discard checks.
- One existing SciPy precision-loss warning from a nearly-identical-data test.
- Guided workspace checked at 800×600, 1024×768, and 1440×900 logical pixels.
- Actual offscreen 125% and 200% scaling checks passed; the welcome screen and
  workspace fit a 400×400 logical-pixel display after shortening the welcome checkbox.
- Normal and compact app screenshots plus the welcome screenshot were rendered
  and visually inspected. Screenshots are in `docs/images/`.
- Rebuilt Windows package passed the existing fitting, project, CSV/Excel, and
  PNG/JPEG/TIFF/PDF/SVG/EPS feature smoke checks.
- Windows installer rebuilt from the updated source; final sizes are recorded
  in `dist/Graffy_Windows_Size.txt`.

The source tests ran before the final small startup-timer deferral and welcome-checkbox shortening. The final
executable and installer were rebuilt afterward and the packaged smoke check passed.
Mac binary creation and real-machine Windows/Mac installation and upgrade remain
separate validation steps. Packages are unsigned; OS warnings may still appear.
GitHub source changes have not been pushed or released as part of this work.

## Chart-focused redesign

- Replaced permanent theme, linked data, and title/axis settings rows with a single
  compact Chart toolbar. Edit chart expands a scrollable settings panel; collapsing
  it returns the space to the graph and retains all edited settings.
- Replaced the icon-only Matplotlib toolbar with readable Explore menu actions:
  Reset view, Zoom, Pan, Read values, Select range, and Pointer.
- Added View data navigation back to the chart's real source worksheet.
- Guided workflow is 1 Data → 2 Create chart → 3 Export graph. Chart, Analyze,
  and Export actions enable only for suitable current data/chart context.
- Blank worksheets offer clear Import/Paste actions. This starter disappears when
  data arrives. Advanced column tools can be expanded when needed.
- Eight new tests cover collapse at three widths, label preservation, worksheet
  navigation, Explore callbacks, starter state, context state, and all-zero data.
- Full suite after these changes: **414 passed**, one existing SciPy warning.
- Final rebuilt app passed packaged scientific feature checks; matching installer
  compiled successfully. Download:71.1MB, application files:241.1MB.
- 125%/200% graph workspace geometry checks passed. On very small displays,
  close the Edit chart panel to maximize the plot after editing.

Latest popup update: **419 full-suite tests passed**, plus **36 final focused checks**
after styling refinements. Import, graph-import, export, fitting, and statistics
dialogs were simplified; see [popup changes](IMPORT_AND_DIALOGS.md). The final
compiled feature check passed. Temporary build/environment copies were removed.

## Desktop redesign validation

429 tests passed after the workspace redesign. Seven task dialogs fit at 200% display scaling, including primary actions. The compiled Windows app passed its scientific smoke check; fourteen packaged UI modules match source, and the executable uses the Windows GUI subsystem. The matching Windows installer is 71.1 MB. See [Desktop redesign](DESKTOP_REDESIGN.md) for the workflow, preview images, checksum, and remaining real-machine installation/platform checks.

## Contrast and editing refinements

441 tests passed. Thirteen task dialogs fit the available screen at 200% scaling. Checkbox/radio and dropdown/stepper indicators were visually inspected in both themes. Rendered colors and project persistence, automatic palettes, real legend-table typing/Save, plot-appearance changes, and secondary/panel-axis labels were verified. The compiled scientific smoke check passed; eighteen packaged modules match source and indicator assets are bundled. See [UI polish](UI_POLISH.md).

## Existing-chart plot conversion

Full suite: 459 passed (one existing SciPy warning). All 15 offered plot types were checked for preserved graph/series identities, source data and error links. Smaller toolbar widths and the 200% compact editor passed. The compiled Windows build passed scientific/project/spreadsheet/export checks; six changed compiled modules matched source. See [PLOT_SWITCHING.md](PLOT_SWITCHING.md) for the latest installer and screenshots.
