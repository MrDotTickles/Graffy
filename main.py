"""
Entry point for Graffy.
Launches the scientific graphing desktop application.
"""

import sys
import os
import argparse
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer

from omnigraph.ui.main_window import MainWindow
from omnigraph.core.project import Project
from omnigraph.ui.samples import SampleProjects
from omnigraph.ui.styles.app_icon import setup_windows_app_id, get_app_icon


def main():
    # Set Windows AppUserModelID before QApplication is created so the Windows taskbar
    # groups Graffy under its own identity and displays its custom icon instead of python.exe
    setup_windows_app_id()

    # Setup High-DPI support: ensure fractional scaling (125%, 150%) passes through without rounding
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    app = QApplication(sys.argv)
    app.setApplicationName("Graffy")
    app.setOrganizationName("Graffy")

    # Set application-wide window icon
    app_icon = get_app_icon()
    app.setWindowIcon(app_icon)

    parser = argparse.ArgumentParser(description="Graffy - Scientific Graphing & Data Analysis")
    parser.add_argument("project_file", nargs="?", default=None, help="Path to .kgraph project file to open")
    parser.add_argument("--sample", choices=["spectroscopy", "kinetics", "dose_response", "dual_axis"], help="Open with pre-loaded scientific sample dataset")
    parser.add_argument("--smoke-test", action="store_true", help="Open the packaged application briefly, then exit (release verification)")

    args, _ = parser.parse_known_args()

    # Load initial project
    project = None
    if args.sample:
        if args.sample == "spectroscopy":
            project = SampleProjects.create_spectroscopy_sample()
        elif args.sample == "kinetics":
            project = SampleProjects.create_enzyme_kinetics_sample()
        elif args.sample == "dose_response":
            project = SampleProjects.create_dose_response_sample()
        elif args.sample == "dual_axis":
            project = SampleProjects.create_dual_axis_sample()
    elif args.project_file and os.path.exists(args.project_file):
        try:
            project = Project.load_from_file(args.project_file)
        except Exception as e:
            print(f"Warning: Failed to load project {args.project_file}: {e}")

    # Fallback to rich spectroscopy sample on first launch so user immediately sees awesome graphs and data
    if project is None:
        project = SampleProjects.create_spectroscopy_sample()

    window = MainWindow(project=project)
    window.setWindowIcon(app_icon)
    window.showMaximized()
    if args.smoke_test:
        from omnigraph.core.release_smoke import run_packaged_checks
        try:
            run_packaged_checks(project)
        except Exception:
            import tempfile
            import traceback
            from pathlib import Path
            report = Path(tempfile.gettempdir()) / "Graffy_smoke_error.txt"
            report.write_text(traceback.format_exc(), encoding="utf-8")
            sys.exit(1)
        QTimer.singleShot(1000, app.quit)
    else:
        QTimer.singleShot(2500, window.check_updates_in_background)
        update_timer = QTimer(window)
        update_timer.setInterval(6 * 60 * 60 * 1000)
        update_timer.timeout.connect(window.check_updates_in_background)
        update_timer.start()
    app.aboutToQuit.connect(window.wait_for_update_check)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
