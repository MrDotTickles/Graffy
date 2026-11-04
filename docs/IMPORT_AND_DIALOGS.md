# Import and popup usability

Both import windows use `SmartDataExtractor`, a local heuristic parser. There is
no separate AI model or external AI service. The old AI name exaggerated the difference.

- **File → Import data** is the standard path for CSV, Excel, instrument files,
  multiple files, or pasted text. Detection, table preview, and an explicit
  Create a graph checkbox are visible. Reading and batch options are expandable.
- **Plot → Import data into a graph** retains the specialist single-source route:
  inspect original text and choose a new or existing graph. Its shortcut remains
  Ctrl+Shift+I. The old Python class name is retained for compatibility.

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

Validation: 419 tests passed in the full suite, including five new checks for
shared parser results, advanced-option preservation, overwrite cancellation,
small-screen action access, and visible specialized preview. A further 36 focused
checks passed after final styling and export-preview adjustments. Scientific
calculation defaults and extraction algorithms are unchanged.

Actual 200% scaling checks fit all five dialogs into a 400×400 logical screen
(each dialog was 368×352), with action buttons retained outside the scrolling body.
The final compiled scientific-feature check passed and the Windows installer compiled.

Dialog screenshots are in `docs/images/`. The matching installer is rebuilt in
`dist/`. Mac binary creation and real-machine installation remain separate checks.
