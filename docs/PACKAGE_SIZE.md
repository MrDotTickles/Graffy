# Download and installed size

Measured from the Windows 1.0.1 redesigned desktop build on November 2, 2026:

| Item | Size |
| --- | --- |
| Windows installer download | **71.1 MB** (67.8 MiB) |
| Application files after installation | **241.1 MB** (229.9 MiB) |

These are actual artifact measurements, not estimates from the source folder.
Installed disk allocation and uninstall bookkeeping add a little overhead.
Mac sizes must be measured by the Mac build jobs; Windows numbers do not apply to Mac.

The installer includes Python, Qt, NumPy, SciPy, Matplotlib, pandas, and the runtime
libraries. Users do not install Python or run terminal commands. Most installed
space is the interface toolkit and scientific libraries, rather than Graffy's own code.
This is a full scientific desktop app, not a few-megabyte utility.

## What was improved

- Omitted the unused AVIF image encoder from the package.
- Kept necessary graphics fallbacks and numerical libraries for compatibility.
- Explicitly included PDF, SVG, and EPS export backends after the stronger packaged
  feature test discovered they were missing from the earlier builds.
- Used a compressed single-file Windows installer with per-user installation,
  automatic install location, Start menu/desktop shortcuts, and a launch option.
- Added a size report to each future GitHub release and its Actions summary.

The corrected compiled app passed fitting, project save/reopen, CSV/Excel round-trips,
and PNG/JPEG/TIFF/PDF/SVG/EPS export checks. The source suite passed 401 tests.
The installer compiled successfully; real-machine first installation and upgrade
checks are still separate from these executable tests. Signing is not configured.

The final installer and its size report are kept in ignored `dist/`. Unpacked app,
build cache, diagnostic packages, and local Python environment were removed after
verification to avoid duplicate disk use. The source launch/release buttons restore
`.venv` when needed; app users should open the installer instead.

## Measuring future releases

After building and packaging, run `python scripts/report_package_size.py`.
The workflow does this automatically on Windows and both Mac architectures.
Sizes can change as functionality or library versions change.

[Installation instructions](INSTALLING.md) · [Release instructions](../RELEASING.md)
