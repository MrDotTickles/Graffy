# Interface size, waterfall axes and chart editing

Use the **UI 100%** selector at the bottom right, or **View → Interface size**, to scale the interface from 80% to 200%. Text, shared control dimensions, icons, menus and dialogs scale together. The choice is saved across restarts. Figure DPI and exported figure styling are unchanged by this setting. The existing graph/data zoom commands remain separate.

**Edit chart** stays inside the main workspace. At wide sizes it appears beside the graph; at narrow sizes it appears below it. Resizing never opens a separate editor window, and unsaved label edits survive resizing. Close it with **Done editing** to regain the full figure area.

For waterfall/stacked spectra, open **Edit chart → Style**. **Stack spectra (waterfall)** enables the offsets, **Vertical spacing** adjusts them (zero means automatic), and **Show intensity axis** optionally restores the vertical axis. Waterfall plots hide that axis by default because the displayed values include offsets. Other plot types keep their normal Y axes. This choice is saved in projects; data values are preserved.

Validation: **463 tests passed**, and Windows, Apple Silicon Mac and Intel Mac release jobs passed their tests and compiled-app scientific/project/spreadsheet/export checks. Wide, compact and 200% interface layouts were rendered. Release v1.0.3 is published; all three website downloads were verified.
