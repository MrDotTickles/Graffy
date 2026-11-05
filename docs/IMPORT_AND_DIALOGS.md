# Import and popup usability

Graffy uses one import dialog and a local parser for files and pasted data.

- **File → Import data** opens the preview for CSV, Excel, instrument files,
  multiple files, or pasted text. Check the detected headers, numeric columns,
  and values that will be left blank. Reading and batch options are expandable.
- **Plot → Import data into a graph** (Ctrl+Shift+I) and dropping files on a chart
  open that same dialog. Choose whether to plot the data and where to put it.

Other changes:

- Export saves to Documents by default, offers Copy image or Save graph, and keeps
  optional figure sizing collapsed. Custom DPI appears only when selected.
- Existing export files require explicit confirmation before replacement.
- Fitting offers Preview fit and Add fit. The default outputs are explained;
  detailed output choices are expandable without losing their settings.
- Statistics has Summary and Compare two groups tabs with plain-language help.
  Copying results shows an inline confirmation instead of another modal popup.
- Shared scrollable bodies keep action buttons outside the scrolling area, and
  window dimensions adapt to the available screen.

Earlier validation: 419 tests passed in the full suite, including five new checks for
shared parser results, advanced-option preservation, overwrite cancellation,
small-screen action access, and visible specialized preview. A further 36 focused
checks passed after final styling and export-preview adjustments. Scientific
calculation defaults and extraction algorithms are unchanged.

Actual 200% scaling checks fit all five dialogs into a 400×400 logical screen
(each dialog was 368×352), with action buttons retained outside the scrolling body.
The final compiled scientific-feature check passed and the Windows installer compiled.

Dialog screenshots are in `docs/images/`. The matching installer is rebuilt in
`dist/`. Mac binary creation and real-machine installation remain separate checks.
