# Change the plot without creating another graph

Use **Change plot** in the toolbar above a chart. Choose an XY plot or a distribution. The same graph and linked worksheet remain in place.

To change a single series on a mixed chart, choose **Change plot → Change just one series…**, select the data series, and choose **Plot type**. The editor now offers the full supported set, including bars, histogram, box, violin and individual points.

Whole-chart conversion retains series identities, names, colors, worksheet links, error-column links, fitted curves and annotations. It automatically fits the new view. Histogram uses Y values and counts; grouped distributions summarize each series' Y values. Axis labels and scales are remembered separately for XY, horizontal bars, histograms and grouped distributions, including after saving and reopening a project. Switching back restores those labels and scales. Whole-chart conversion leaves fitted curves unchanged.

Horizontal bars now use the original X values as positions and the original Y measurements as bar lengths, consistently with vertical bars. Existing horizontal-bar charts therefore render with this corrected interpretation. An error column no longer incorrectly forces a selected histogram or grouped distribution to render as error bars. Source error columns remain linked when changing back to error bars.

The legend retains its existing **Apply / Save changes** workflow. A matching symbol fill or outline follows a changed series color; an intentional white or transparent fill is retained. Legend controls also have a direct toolbar shortcut.

## Local package

The updated installer is `dist/Graffy_Windows_Setup.exe`: **71,091,092 bytes (71.1 MB)**. Application files use **241.1 MB**. Installer SHA-256: `03F1ADFEB39E7DF741885D8D0D0375865D5470E2F892837EDD19FC2C653F1BA5`.

Close Graffy and run this installer over the existing installation to see the changes. A local source edit does not update a previously installed copy. Source version remains 1.0.1; no commit, push or GitHub release was performed. A published release needs a higher unused version.

## Validation

- Focused conversion/rendering checks: 57 passed, including all 15 offered plot types, data preservation, error-column recovery, fitted-line preservation, labels after save/reopen, and matching symbol colors.
- Change plot toolbar access checked at 640, 800 and 1180 logical pixels.
- Compact series editor checked at 200% display scaling on a 400 by 400 logical screen; editor bounds 368 by 352 with its Done action accessible.
- Windows compiled scientific/file/export smoke check passed. All six changed packaged modules match source; GUI subsystem confirmed, with no Python console.
- Full regression suite: **459 passed**, with one existing SciPy precision-loss warning (490.00 seconds).

Screenshots: `docs/images/change-plot-chart.png`, `change-plot-menu.png`, and `change-plot-compact-editor.png`.
