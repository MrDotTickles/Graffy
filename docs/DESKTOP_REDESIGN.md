# Desktop redesign

Graffy now uses one consistent desktop design: a compact command bar, quiet project navigation, a large figure stage, and an editor that opens only when needed. Light and dark themes share the same spacing, typography, icons, focus treatment, and action hierarchy.

## Everyday workflow

1. Choose **Import data**, paste cells, or type in a worksheet.
2. Use **Create chart** to choose a common graph type. More scientific plot types remain in Plot.
3. Choose **Edit chart** for Labels and Style. On a wide workspace, the editor sits beside the figure. On a small screen it opens in its own scrollable window with a fixed Done button.
4. Use **Analyze** for fitting, peaks, and statistics. Optional controls stay expandable.
5. **Save project** keeps editable data and graphs. **Export graph** saves an image or vector figure; Copy graph is also available above the figure.

The project panel button restores navigation on smaller displays. Worksheet, graph, and result names are kept concise; source information and counts are available in tooltips. Advanced tools remain available from View and the application menus.

## Safer behavior

- Closing a tab closes its view. It no longer removes data, graphs, or reports from the project. Click the item in the project panel to reopen it.
- Closing all tabs shows a clear path back to project navigation.
- Dragging tabs retains the correct association between each view and its actions.
- Opening a recent project asks about unsaved changes before replacing the current project.
- Rebuilding project views releases old widgets rather than retaining hidden copies.
- Import, export, fitting, adding a series, and editing labels use explicit primary buttons; Cancel stays secondary.

## Validation

**Final regression result: 429 tests passed**, with one existing SciPy precision-loss warning.

Automated coverage includes tab movement, non-destructive tab closing and reopening, compact action visibility, editor movement between layouts, preservation of edits, theme changes, and cancellation when opening a recent project.

All seven task dialogs (regular import, graph import, export, fitting, statistics, adding a series, and labels) were rendered and inspected. At 200% display scaling on an 800 by 800 physical offscreen display, all fit within 368 by 352 logical pixels. Main action buttons remained within each dialog. Workspace previews include large, compact, light, and dark layouts.

The compiled Windows app passed its scientific smoke check (fits, project save/reopen, CSV/Excel round-trips, and raster/vector exports). Fourteen packaged UI modules were compared with current source, and the executable's Windows GUI subsystem was confirmed. The rebuilt 1.0.1 installer is 71,077,527 bytes (71.1 MB); application files total 241.1 MB. Users do not install Python separately.

The build measurements above belong to the original redesign build. For the current installer size and checksum, see [UI polish](UI_POLISH.md).

Windows executable validation does not replace a real-machine first-install/upgrade check, a macOS installation check, or configure application signing. Publishing a new GitHub release is separate from producing this local installer.

## Preview files

See `docs/images/redesign-chart.png`, `redesign-editor.png`, `redesign-dark.png`, `redesign-compact.png`, `redesign-compact-editor.png`, `redesign-worksheet.png`, `redesign-welcome.png`, and the corresponding task-dialog images.

Further contrast, series editing, and popup improvements are documented in [UI polish](UI_POLISH.md).
