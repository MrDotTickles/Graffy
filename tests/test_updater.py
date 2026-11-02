"""
Unit and integration tests for Graffy cross-platform software updater.
Tests version comparison, manifest parsing, cloud URL normalization, and UpdateDialog UI.
"""

import os
import json
import tempfile
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QAction

from omnigraph.core.updater import (
    compare_versions, normalize_version, normalize_cloud_url,
    fetch_update_manifest, check_for_updates, UpdateInfo,
    is_github_repo_or_url, normalize_github_api_url
)
from omnigraph.ui.dialogs.update_dialog import UpdateDialog
from omnigraph.ui.main_window import MainWindow
from omnigraph.ui.samples import SampleProjects


@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_version_normalization_and_comparison():
    """Verify semantic version parsing and ordering."""
    assert normalize_version("1.0.0") == (1, 0, 0)
    assert normalize_version("v2.1") == (2, 1, 0)
    assert normalize_version("1.10.4-beta") == (1, 10, 4)

    assert compare_versions("1.0.0", "1.0.1") == -1
    assert compare_versions("1.1.0", "1.0.9") == 1
    assert compare_versions("2.0.0", "2.0") == 0
    assert compare_versions("v1.2.3", "1.2.3") == 0
    assert compare_versions("1.10.0", "1.2.0") == 1


def test_cloud_url_normalization():
    """Verify conversion of Dropbox and Google Drive share URLs to direct download links."""
    # Dropbox
    db_url = "https://www.dropbox.com/s/xyz123/version.json?dl=0"
    norm_db = normalize_cloud_url(db_url)
    assert "dl.dropboxusercontent.com" in norm_db
    assert "dl=1" in norm_db

    # Google Drive
    gd_url = "https://drive.google.com/file/d/1A2B3C4D5E/view?usp=sharing"
    norm_gd = normalize_cloud_url(gd_url)
    assert norm_gd == "https://drive.google.com/uc?export=download&id=1A2B3C4D5E"


def test_local_manifest_check_newer():
    """Verify update checker correctly identifies newer versions from a local manifest."""
    manifest_data = {
        "version": "99.0.0",
        "release_date": "2026-12-01",
        "release_notes": "Revolutionary scientific update with quantum fitting",
        "download_windows": "https://example.com/Graffy_Win.zip",
        "download_mac": "https://example.com/Graffy_Mac.dmg",
        "download_url": "https://example.com/Graffy.zip"
    }

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(manifest_data, f)
        temp_path = f.name

    try:
        info = check_for_updates(temp_path)
        assert info.is_newer is True
        assert info.latest_version == "99.0.0"
        assert "Revolutionary" in info.release_notes
        assert info.error is None
        # On Windows or Mac, it should pick the platform link or fallback
        assert info.download_url.startswith("https://example.com/")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_local_manifest_check_up_to_date():
    """Verify update checker correctly identifies current/older versions as up-to-date."""
    manifest_data = {
        "version": "0.1.0",
        "release_date": "2020-01-01",
        "release_notes": "Ancient alpha version",
        "download_url": "https://example.com/old.zip"
    }

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(manifest_data, f)
        temp_path = f.name

    try:
        info = check_for_updates(temp_path)
        assert info.is_newer is False
        assert info.latest_version == "0.1.0"
        assert info.error is None
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_update_dialog_ui(qapp):
    """Verify UpdateDialog instantiates, renders status, and handles UI events."""
    dlg = UpdateDialog(auto_check=False)
    dlg.show()
    assert dlg.windowTitle() == "Graffy Software Update"
    assert dlg.lbl_current_ver.text() != ""

    # Simulate newer version response
    newer_info = UpdateInfo(
        current_version="1.0.0",
        latest_version="1.2.0",
        is_newer=True,
        release_date="2026-11-15",
        release_notes="• Faster calculation engine\n• High-DPI enhancements",
        download_url="https://example.com/download"
    )
    dlg._on_update_result(newer_info)
    assert "New version available" in dlg.lbl_status.text()
    assert not dlg.btn_download.isHidden()
    assert "Faster calculation" in dlg.txt_notes.toPlainText()

    # Simulate up-to-date response
    current_info = UpdateInfo(
        current_version="1.0.0",
        latest_version="1.0.0",
        is_newer=False,
        release_date="2026-11-01",
        release_notes="",
        download_url=""
    )
    dlg._on_update_result(current_info)
    assert "Graffy is up to date" in dlg.lbl_status.text()
    assert dlg.btn_download.isHidden()

    dlg.close()


def test_main_window_has_check_for_updates_menu(qapp):
    """Verify that MainWindow Help menu contains 'Check for Updates...' action."""
    win = MainWindow(project=SampleProjects.create_spectroscopy_sample())
    update_act = None
    for act in win.findChildren(QAction):
        if "Check for Updates" in act.text():
            update_act = act
            break

    assert update_act is not None, "'Check for Updates...' action must exist in Help menu"
    win.close()


def test_github_url_and_repo_detection():
    """Verify detection and normalization of GitHub repository slugs and links."""
    assert is_github_repo_or_url("kyle/graffy") is True
    assert is_github_repo_or_url("https://github.com/kyle/graffy") is True
    assert is_github_repo_or_url("https://api.github.com/repos/kyle/graffy/releases/latest") is True
    assert is_github_repo_or_url("https://drive.google.com/something") is False

    api_url = normalize_github_api_url("kyle/graffy")
    assert api_url == "https://api.github.com/repos/kyle/graffy/releases/latest"

    api_url2 = normalize_github_api_url("https://github.com/kyle/graffy")
    assert api_url2 == "https://api.github.com/repos/kyle/graffy/releases/latest"


def test_github_manifest_parsing():
    """Verify that GitHub Releases API JSON format is correctly parsed into UpdateInfo."""
    gh_response = {
        "tag_name": "v2.5.0",
        "published_at": "2026-11-10T14:32:00Z",
        "body": "## Release 2.5\n* High-speed peak fitting\n* Apple Silicon M3/M4 optimizations",
        "html_url": "https://github.com/kyle/graffy/releases/tag/v2.5.0",
        "assets": [
            {
                "name": "Graffy_Windows.zip",
                "browser_download_url": "https://github.com/kyle/graffy/releases/download/v2.5.0/Graffy_Windows.zip",
                "size": 65000000
            },
            {
                "name": "Graffy_macOS.zip",
                "browser_download_url": "https://github.com/kyle/graffy/releases/download/v2.5.0/Graffy_macOS.zip",
                "size": 72000000
            }
        ]
    }

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(gh_response, f)
        temp_path = f.name

    try:
        info = check_for_updates(temp_path)
        assert info.is_newer is True
        assert info.latest_version == "2.5.0"
        assert info.release_date == "2026-11-10"
        assert "Apple Silicon" in info.release_notes
        assert len(info.assets) == 2
        # Verify platform specific download selection
        if os.name == "nt":
            assert "Windows" in info.download_url
        else:
            assert "macOS" in info.download_url or "Windows" in info.download_url
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

