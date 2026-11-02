"""Regression coverage for release selection, failed downloads and notifications."""
import hashlib
import io
import json

import pytest
from PyQt6.QtWidgets import QApplication

from omnigraph.core import updater
from omnigraph.ui.dialogs.update_dialog import UpdateDialog


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def asset(name):
    return updater.UpdateAsset(name, f"https://example.com/{name}")


def test_windows_prefers_installer_and_never_darwin(monkeypatch):
    monkeypatch.setattr(updater.sys, "platform", "win32")
    assets = [asset("Graffy_Darwin.zip"), asset("Graffy_Windows.zip"),
              asset("Graffy_Windows_Setup.exe")]
    assert updater.select_asset(assets) == assets[2]
    assert updater.select_asset(assets[:1]) is None


@pytest.mark.parametrize("machine,filename", [("arm64", "Graffy_macOS_arm64.zip"),
                                              ("x86_64", "Graffy_macOS_x86_64.zip")])
def test_mac_selects_architecture(monkeypatch, machine, filename):
    monkeypatch.setattr(updater.sys, "platform", "darwin")
    monkeypatch.setattr(updater.platform, "machine", lambda: machine)
    assets = [asset("Graffy_macOS_arm64.zip"), asset("Graffy_macOS_x86_64.zip")]
    assert updater.select_asset(assets).name == filename


def test_prerelease_comparison():
    assert updater.compare_versions("1.2.0rc1", "1.2.0") == -1
    assert updater.compare_versions("1.2.0", "1.2.0-beta.1") == 1


@pytest.mark.parametrize("machine", ["arm64", "x86_64"])
def test_mac_prefers_compatible_disk_image(monkeypatch, machine):
    monkeypatch.setattr(updater.sys, "platform", "darwin")
    monkeypatch.setattr(updater.platform, "machine", lambda: machine)
    other = "arm64" if machine == "x86_64" else "x86_64"
    assets = [asset(f"Graffy_macOS_{other}.dmg"),
              asset(f"Graffy_macOS_{machine}.zip"),
              asset(f"Graffy_macOS_{machine}.dmg")]
    assert updater.select_asset(assets) == assets[2]
    assert updater.select_asset(assets[:1]) is None


@pytest.mark.parametrize("data", [[], None, {"version": "nonsense"}, {"tag_name": "1.2.0", "assets": None}])
def test_malformed_manifest_is_an_error(monkeypatch, data):
    monkeypatch.setattr(updater, "fetch_update_manifest", lambda *a, **kw: data)
    assert updater.check_for_updates("owner/repo").error


def test_no_compatible_asset_does_not_download_html(monkeypatch):
    monkeypatch.setattr(updater.sys, "platform", "win32")
    monkeypatch.setattr(updater, "fetch_update_manifest", lambda *a, **kw: {
        "tag_name": "v9.0.0", "html_url": "https://github.com/owner/repo/releases",
        "assets": [{"name": "Graffy_macOS_arm64.zip", "browser_download_url": "https://example.com/mac.zip"}]})
    info = updater.check_for_updates("owner/repo")
    assert info.is_newer
    assert not info.download_url
    assert info.html_url


class Response(io.BytesIO):
    def __init__(self, data, length):
        super().__init__(data)
        self.headers = {"Content-Length": str(length)}


@pytest.mark.parametrize("failure", ["truncated", "checksum", "cancelled", "none"])
def test_download_is_atomic_and_verified(monkeypatch, tmp_path, app, failure):
    content = b"installer bytes"
    monkeypatch.setattr(updater.urllib.request, "urlopen", lambda *a, **kw:
                        Response(content, len(content) + (1 if failure == "truncated" else 0)))
    destination = tmp_path / "update.exe"
    destination.write_bytes(b"previous download")
    digest = "sha256:" + hashlib.sha256(content).hexdigest()
    worker = updater.FileDownloadWorker("https://example.com/update.exe", str(destination),
                                       digest="sha256:wrong" if failure == "checksum" else digest)
    completed, errors = [], []
    worker.finished.connect(completed.append)
    worker.error.connect(errors.append)
    if failure == "cancelled":
        worker.cancel()
    worker.run()
    assert not list(tmp_path.glob("*.part"))
    if failure == "none":
        assert destination.read_bytes() == content
        assert completed and not errors
    else:
        assert destination.read_bytes() == b"previous download"
        assert not completed
        assert bool(errors) == (failure != "cancelled")


def test_release_notes_are_plain_text_and_stale_actions_hidden(app):
    dialog = UpdateDialog(auto_check=False)
    info = updater.UpdateInfo("1.0.0", "2.0.0", True, "", "<b>literal notes</b>", "https://example.com/update.zip")
    dialog._on_update_result(info)
    assert "<b>literal notes</b>" in dialog.txt_notes.toPlainText()
    info.error = "Network failed"
    dialog._on_update_result(info)
    assert dialog.btn_download.isHidden()
    dialog.close()


def test_busy_dialog_cannot_destroy_worker(app):
    dialog = UpdateDialog(auto_check=False)
    class Busy:
        def isRunning(self):
            return True
    dialog.worker = Busy()
    dialog.show()
    dialog.reject()
    assert dialog.isVisible()
    dialog.worker = None
    dialog.close()


def test_startup_checks_default_on_and_respect_opt_out(monkeypatch):
    class Settings:
        stored = None

        def __init__(self, *args):
            pass

        def value(self, key, default):
            return default if self.stored is None else self.stored

    monkeypatch.setattr(updater, "QSettings", Settings)
    assert updater.get_check_on_startup()
    Settings.stored = False
    assert not updater.get_check_on_startup()
    Settings.stored = "true"
    assert updater.get_check_on_startup()


def test_startup_notification_only_for_new_versions(monkeypatch):
    from omnigraph.ui.main_window import MainWindow
    from omnigraph.ui.dialogs import update_dialog

    shown = []

    class Dialog:
        def __init__(self, *args, **kwargs):
            pass

        def _on_update_result(self, info):
            shown.append(info.latest_version)

        def exec(self):
            pass

    class Window:
        pass

    monkeypatch.setattr(update_dialog, "UpdateDialog", Dialog)
    window = Window()
    info = updater.UpdateInfo("1.0.0", "2.0.0", False, "", "", "")
    MainWindow._notify_update(window, info)
    assert not shown
    info.is_newer = True
    info.error = "offline"
    MainWindow._notify_update(window, info)
    assert not shown
    info.error = None
    MainWindow._notify_update(window, info)
    MainWindow._notify_update(window, info)
    assert shown == ["2.0.0"]
