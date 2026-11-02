"""
Unit and integration tests for Graffy application icon and Windows taskbar integration.
"""

import os
import sys
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon, QPixmap
from omnigraph.ui.styles.app_icon import (
    render_graffy_pixmap, get_app_icon, setup_windows_app_id,
    ICO_PATH, PNG_PATH, ICNS_PATH, ROOT_ICO_PATH, ROOT_ICNS_PATH
)
from omnigraph.ui.main_window import MainWindow
from omnigraph.ui.samples import SampleProjects


@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_render_graffy_pixmap(qapp):
    """Verify icon pixmap rendering at multiple resolutions."""
    for size in [16, 24, 32, 48, 64, 128, 256, 512]:
        pix = render_graffy_pixmap(size)
        assert isinstance(pix, QPixmap)
        assert not pix.isNull(), f"Rendered pixmap for size {size} must not be null"
        assert pix.width() == size
        assert pix.height() == size


def test_get_app_icon(qapp):
    """Verify that get_app_icon returns a valid QIcon with all standard mipmaps."""
    icon = get_app_icon()
    assert isinstance(icon, QIcon)
    assert not icon.isNull(), "Graffy QIcon must not be null"
    
    # Check that key display resolutions can be retrieved
    for s in [16, 32, 48, 64, 128, 256]:
        pix = icon.pixmap(s, s)
        assert not pix.isNull(), f"Icon pixmap for {s}x{s} must be valid"


def test_icon_files_exist(qapp):
    """Verify that the ICO, PNG, and macOS ICNS icon files are generated on disk."""
    get_app_icon()
    assert os.path.exists(ICO_PATH), f"ICO file should exist at {ICO_PATH}"
    assert os.path.exists(PNG_PATH), f"PNG file should exist at {PNG_PATH}"
    assert os.path.exists(ICNS_PATH), f"macOS ICNS file should exist at {ICNS_PATH}"
    assert os.path.getsize(ICO_PATH) > 1000, "ICO file must be non-empty"
    assert os.path.getsize(PNG_PATH) > 1000, "PNG file must be non-empty"
    assert os.path.getsize(ICNS_PATH) > 1000, "macOS ICNS file must be non-empty"


def test_setup_windows_app_id():
    """Verify setup_windows_app_id runs safely without throwing exceptions."""
    setup_windows_app_id("test.app.id.1.0")


def test_main_window_has_icon(qapp):
    """Verify that MainWindow is instantiated with the custom Graffy icon."""
    win = MainWindow(project=SampleProjects.create_spectroscopy_sample())
    assert not win.windowIcon().isNull(), "MainWindow must have custom window icon set"
