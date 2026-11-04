# Licensing and corresponding source

Graffy is licensed under **GNU GPL version 3 only**, as selected by its copyright holder. See LICENSE. No warranty is provided. Third-party components retain their own copyrights and licenses; their inclusion does not imply endorsement.

Finished packages include a LICENSES directory containing the installed dependency license texts and DEPENDENCIES.json with their exact versions, Python version and OpenSSL version. This inventory includes build-time tools as well as runtime packages; it is not a claim that every listed tool is bundled as executable code.

Major components include Python (PSF license), PyQt6 (GPLv3 or commercial; these public builds use GPLv3), Qt (its applicable LGPL/GPL and third-party terms), NumPy/SciPy/pandas (BSD terms), Matplotlib (its license), Pillow (HPND), OpenPyXL (MIT), packaging (Apache/BSD), and the PyInstaller bootloader (GPL with its distribution exception). Refer to the included complete texts rather than this summary.

## Source and rebuilding

The exact Graffy source for a release is available from the matching version tag at https://github.com/MrDotTickles/Graffy/tags and GitHub's source archives. The repository includes build, packaging and installation scripts. See RELEASING.md and requirements-build.txt. Dependencies are installed from PyPI; obtain their matching source distributions from the package's PyPI Files page and upstream repository. Qt source is available from https://download.qt.io/archive/qt/ and Python source from https://www.python.org/downloads/source/. Match the versions recorded in LICENSES/DEPENDENCIES.json, including the Qt version in PyQt6-Qt6.

Keep the license directory and notices when redistributing the app. GPL distribution must provide the corresponding source and build instructions under the applicable terms. If adding a new library or changing its license, review it before a public release. Do not replace the GPL distribution terms with proprietary terms without resolving all affected licenses.
