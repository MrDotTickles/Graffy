Latest installer and plot switching update: see [PLOT_SWITCHING.md](PLOT_SWITCHING.md). The validation and installer checksum below describe the preceding polish build.

# Contrast and chart-editing refinements

## Everyday editing

- **Edit chart → Labels** edits the figure, left/right axes, and lower-panel labels. F2 opens this same editor instead of a second labels popup.
- **Edit chart → Series** selects a data series and edits its name, color, visibility, line width/style, symbols, and symbol colors. Only relevant controls are shown. Optional symbol colors are expandable. Line/scatter appearance can be changed directly for compatible series.
- **Edit chart → Style → Series and legend** opens the bulk series editor and legend settings. Color swatches are clickable. Legend text, background, border, and opacity are editable. Auto follows the figure theme or automatic series palette.
- The legend window's Series tab changes plotted series colors/names and visibility; its Legend tab changes the legend itself. Save changes applies and closes. Apply updates the figure while keeping the window open. Cancel discards edits made since the last Apply.
- Bulk rename options live in a single Rename all menu. Reset to column names uses actual source-column labels when the project is available.

## Visual behavior

Checkboxes, radio buttons, table checkboxes, dropdown arrows, and number steppers have explicit indicators that remain visible in both themes. Field borders and secondary text have stronger contrast. Disabled checked boxes keep a visible checkmark.

Processing, peak analysis, formula, column, update, legend, and the existing import/export/fitting/statistics dialogs share bounded window sizes and scrollable content with accessible action rows. Thirteen task dialogs were rendered in ordinary and 200% display scaling. At 200% on an 800 by 800 physical offscreen display, all fit in the available logical screen; most are 368 by 352 pixels. The column dialog fits at 360 by 260 pixels.

## Correctness fixes

- Legend colors are included in project serialization; older projects default to automatic theme colors.
- Rendering automatic series colors no longer converts them into fixed saved colors.
- Right-axis labels are detected from the actual curve assignment and apply to twin-axis layouts.
- Lower-panel labels can be edited inline.
- None symbol selections and step/area/spline line-style selections are honored by rendering.
- Transparent symbol fills remain transparent when other series settings change.
- Applying legend changes refreshes connected controls; a failed Apply stays open and restores prior settings.

Numerical analysis algorithms and statistical defaults were not changed. Plot appearance and UI behavior changed as described above.

## Validation

**Final full regression run: 441 tests passed**, with one existing SciPy precision-loss warning.

New regression checks cover rendered and saved legend colors, legacy project defaults, theme-aware text, cancellation and failed Apply, source-name reset, automatic palettes, actual line/symbol output, secondary/lower-axis labels, and checkbox rendering in both themes. Real keyboard editing in the legend table and switching line/symbol appearance were also exercised.

The compiled Windows app passed its scientific smoke check. Eighteen compiled modules were compared with current source; indicator SVG assets were confirmed bundled; the executable uses the console-free Windows GUI subsystem.

The local installer is 71,095,336 bytes (71.1 MB), with 241.1 MB of application files. SHA-256: `884F7A8600EC5328CCACD55B8329A2F051489A5B9EE2C1F72C2EC367C9E37A5F`.

Windows binary checks do not replace real-machine installation/upgrade and Mac validation. Publishing the local build as a GitHub release remains a separate step.

Screenshots are in `docs/images/polish-*.png`.
