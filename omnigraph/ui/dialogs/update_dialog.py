"""
Update checking and downloading dialog for Graffy.
Supports 1-click in-app streaming downloads from GitHub Releases or custom cloud servers.
"""

import os
import sys
import tempfile
from html import escape
from urllib.parse import urlparse, unquote
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QCheckBox, QGroupBox, QProgressBar,
    QMessageBox, QWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices

import omnigraph
from omnigraph.core.updater import (
    UpdateInfo, check_for_updates, get_configured_update_url,
    set_configured_update_url, get_check_on_startup, set_check_on_startup,
    FileDownloadWorker
)
from omnigraph.ui.styles.app_icon import render_graffy_pixmap, get_app_icon


class UpdateWorker(QThread):
    """Background worker thread to check for updates without freezing the GUI."""
    result_ready = pyqtSignal(object)

    def __init__(self, manifest_url: str = None, parent=None):
        super().__init__(parent)
        self.manifest_url = manifest_url

    def run(self):
        info = check_for_updates(self.manifest_url)
        self.result_ready.emit(info)


class UpdateDialog(QDialog):
    """Dialog for checking, configuring, streaming downloads, and installing Graffy updates."""

    def __init__(self, parent=None, manifest_url: str = None, auto_check: bool = True):
        super().__init__(parent)
        self.setWindowTitle("Graffy Software Update")
        self.setWindowIcon(get_app_icon())
        self.resize(560, 520)
        self.setMinimumSize(480, 420)

        self.override_url = manifest_url
        self.worker = None
        self.downloader = None
        self.last_info = None
        self.downloaded_file_path = None

        self._build_ui()

        if auto_check:
            self.check_updates()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. Header with App Icon and Version Information
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)

        lbl_icon = QLabel()
        lbl_icon.setPixmap(render_graffy_pixmap(64))
        lbl_icon.setFixedSize(64, 64)
        header_layout.addWidget(lbl_icon)

        title_layout = QVBoxLayout()
        lbl_title = QLabel("<h2>Graffy Update Center</h2>")
        lbl_title.setStyleSheet("margin: 0; padding: 0;")
        
        current_ver = getattr(omnigraph, "__version__", "1.0.0")
        self.lbl_current_ver = QLabel(f"Current Installed Version: <b>v{current_ver}</b>")
        self.lbl_status = QLabel("Ready to check for updates.")
        self.lbl_status.setStyleSheet("color: #38bdf8; font-weight: bold;")

        title_layout.addWidget(lbl_title)
        title_layout.addWidget(self.lbl_current_ver)
        title_layout.addWidget(self.lbl_status)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # 2. Progress Bar & Download Progress Label
        self.progress_container = QWidget()
        prog_layout = QVBoxLayout(self.progress_container)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        prog_layout.setSpacing(4)

        self.lbl_download_progress = QLabel("Downloading update...")
        self.lbl_download_progress.setStyleSheet("color: #38bdf8; font-size: 11px;")
        prog_layout.addWidget(self.lbl_download_progress)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setFixedHeight(8)
        prog_layout.addWidget(self.progress_bar)
        
        self.progress_container.hide()
        layout.addWidget(self.progress_container)

        # 3. Release Notes / Update Details Box
        self.group_notes = QGroupBox("Release Notes & Changes")
        notes_layout = QVBoxLayout(self.group_notes)
        self.txt_notes = QTextEdit()
        self.txt_notes.setReadOnly(True)
        self.txt_notes.setPlaceholderText("Release notes and changelog will appear here...")
        notes_layout.addWidget(self.txt_notes)
        layout.addWidget(self.group_notes, stretch=1)

        # 4. Action Banner (Download / Install buttons)
        self.action_layout = QHBoxLayout()
        
        self.btn_download = QPushButton("⬇️ Download & Update Now")
        self.btn_download.setObjectName("PrimaryActionButton")
        self.btn_download.setStyleSheet("""
            QPushButton#PrimaryActionButton {
                background-color: #22c55e;
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 18px;
                border-radius: 6px;
            }
            QPushButton#PrimaryActionButton:hover {
                background-color: #16a34a;
            }
        """)
        self.btn_download.clicked.connect(self._on_download_clicked)
        self.btn_download.hide()
        self.action_layout.addWidget(self.btn_download)

        self.btn_open_file = QPushButton("🚀 Launch / Install Update")
        self.btn_open_file.setStyleSheet("""
            QPushButton {
                background-color: #38bdf8;
                color: #0f172a;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 18px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #0284c7;
                color: #ffffff;
            }
        """)
        self.btn_open_file.clicked.connect(self._on_open_downloaded_file)
        self.btn_open_file.hide()
        self.action_layout.addWidget(self.btn_open_file)

        self.btn_browser_fallback = QPushButton("🌐 View on Web")
        self.btn_browser_fallback.clicked.connect(self._on_browser_fallback_clicked)
        self.btn_browser_fallback.hide()
        self.action_layout.addWidget(self.btn_browser_fallback)

        self.action_layout.addStretch()
        layout.addLayout(self.action_layout)

        # 5. Configuration Box (GitHub Repo or Cloud Server)
        self.group_config = QGroupBox("Update Source Settings")
        config_layout = QVBoxLayout(self.group_config)
        config_layout.setSpacing(8)

        lbl_desc = QLabel(
            "Enter your <b>GitHub Repository</b> (e.g. <code>kyle/graffy</code>) "
            "or a custom Google Drive / server URL:"
        )
        lbl_desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        config_layout.addWidget(lbl_desc)

        url_row = QHBoxLayout()
        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("e.g. kyle/graffy  or  https://github.com/kyle/graffy")
        self.txt_url.setText(get_configured_update_url())
        url_row.addWidget(self.txt_url)

        self.btn_save_url = QPushButton("Save Source")
        self.btn_save_url.clicked.connect(self._save_settings)
        url_row.addWidget(self.btn_save_url)
        config_layout.addLayout(url_row)

        self.chk_startup = QCheckBox("Automatically check for updates on startup")
        self.chk_startup.setChecked(get_check_on_startup())
        self.chk_startup.toggled.connect(lambda val: set_check_on_startup(val))
        config_layout.addWidget(self.chk_startup)

        layout.addWidget(self.group_config)

        # 6. Bottom Controls
        bottom_layout = QHBoxLayout()
        self.btn_toggle_config = QPushButton("⚙️ Source Settings")
        self.btn_toggle_config.setCheckable(True)
        self.btn_toggle_config.setChecked(False)
        self.group_config.setVisible(False)
        self.btn_toggle_config.toggled.connect(self.group_config.setVisible)
        bottom_layout.addWidget(self.btn_toggle_config)

        bottom_layout.addStretch()

        self.btn_check_again = QPushButton("🔄 Check Again")
        self.btn_check_again.clicked.connect(self.check_updates)
        bottom_layout.addWidget(self.btn_check_again)

        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        bottom_layout.addWidget(self.btn_close)

        layout.addLayout(bottom_layout)

    def check_updates(self):
        """Starts asynchronous update check."""
        if self._busy():
            return
        url = self.override_url or self.txt_url.text().strip()
        if not url:
            self.lbl_status.setText("No update source configured.")
            self.lbl_status.setStyleSheet("color: #f59e0b; font-weight: bold;")
            self.txt_notes.setHtml(
                "<p style='color: #94a3b8; font-size: 12px;'>"
                "To enable automatic updates, enter your GitHub repository slug (e.g. <b>username/graffy</b>) "
                "or your cloud manifest URL.<br><br>"
                "Click <b>⚙️ Source Settings</b> below to configure your update source."
                "</p>"
            )
            self.group_config.setVisible(True)
            self.btn_toggle_config.setChecked(True)
            return

        self.lbl_status.setText("Checking for updates...")
        self.lbl_status.setStyleSheet("color: #38bdf8; font-weight: bold;")
        self.progress_bar.setRange(0, 0)
        self.lbl_download_progress.setText("Querying update server...")
        self.progress_container.show()
        self.btn_check_again.setEnabled(False)
        self.btn_download.hide()
        self.btn_open_file.hide()
        self.btn_browser_fallback.hide()
        self.btn_download.setEnabled(True)
        self.downloaded_file_path = None

        self.worker = UpdateWorker(manifest_url=url, parent=self)
        self.worker.result_ready.connect(self._on_update_result)
        self.worker.start()

    def _on_update_result(self, info: UpdateInfo):
        """Handles completion of the update check."""
        self.last_info = info
        self.btn_download.hide()
        self.btn_open_file.hide()
        self.btn_browser_fallback.hide()
        self.progress_container.hide()
        self.btn_check_again.setEnabled(True)

        if info.error:
            self.lbl_status.setText("Update check failed")
            self.lbl_status.setStyleSheet("color: #ef4444; font-weight: bold;")
            self.txt_notes.setHtml(
                f"<p style='color: #ef4444;'><b>Error:</b> {escape(info.error)}</p>"
                "<p style='color: #94a3b8; font-size: 11px;'>Please verify your GitHub repository name or network connection.</p>"
            )
            return

        if info.is_newer:
            self.lbl_status.setText(f"🎉 New version available: v{info.latest_version}!")
            self.lbl_status.setStyleSheet("color: #22c55e; font-weight: bold;")
            
            html_body = f"""
            <div style="font-family: sans-serif; padding: 4px;">
                <p style="font-size: 14px; margin-top: 0;"><b>Version {escape(info.latest_version)}</b> ({escape(info.release_date)})</p>
                <div style="background-color: rgba(56, 189, 248, 0.08); padding: 10px; border-radius: 6px;">
                    <b>What's New:</b><br>
                    <pre style="font-family: inherit; white-space: pre-wrap; margin: 6px 0 0 0;">{escape(info.release_notes)}</pre>
                </div>
            </div>
            """
            self.txt_notes.setHtml(html_body)

            if info.download_url:
                self.btn_download.setText(f"⬇️ Download v{info.latest_version}")
                self.btn_download.show()
            else:
                self.btn_download.hide()

            if info.html_url:
                self.btn_browser_fallback.show()
            if not info.download_url:
                self.txt_notes.append("No compatible download is available for this computer. View the release on the web.")
        else:
            self.lbl_status.setText(f"✓ Graffy is up to date (v{info.current_version})")
            self.lbl_status.setStyleSheet("color: #22c55e; font-weight: bold;")
            self.txt_notes.setHtml(
                f"<div style='text-align: center; padding: 30px; color: #94a3b8;'>"
                f"<h3 style='color: #38bdf8;'>You have the latest version of Graffy</h3>"
                f"<p>Installed version: <b>v{info.current_version}</b></p>"
                f"<p style='font-size: 11px;'>No new updates are available at this time.</p>"
                f"</div>"
            )
            self.btn_download.hide()
            self.btn_open_file.hide()
            self.btn_browser_fallback.hide()

    def _on_download_clicked(self):
        """Starts in-app streamed download with live progress bar."""
        if not self.last_info or not self.last_info.download_url:
            return
        if self._busy():
            return

        url = self.last_info.download_url
        
        # Determine appropriate download filename
        filename = os.path.basename(unquote(urlparse(url).path).replace("\\", "/"))
        if not filename or len(filename) < 3:
            ext = ".dmg" if sys.platform == "darwin" else ".zip"
            filename = f"Graffy_v{self.last_info.latest_version}{ext}"

        dest_folder = tempfile.mkdtemp(prefix="Graffy_Update_")
        dest_path = os.path.join(dest_folder, filename)

        self.btn_download.setEnabled(False)
        self.btn_download.setText("Downloading...")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.lbl_download_progress.setText("Connecting to download server...")
        self.progress_container.show()

        asset = next((a for a in self.last_info.assets if a.download_url == url), None)
        self.downloader = FileDownloadWorker(
            url, dest_path, parent=self,
            expected_size=asset.size_bytes if asset else 0,
            digest=asset.digest if asset else "")
        self.btn_check_again.setEnabled(False)
        self.btn_save_url.setEnabled(False)
        self.downloader.finished.connect(lambda _: self.btn_check_again.setEnabled(True))
        self.downloader.error.connect(lambda _: self.btn_check_again.setEnabled(True))
        self.downloader.finished.connect(lambda _: self.btn_save_url.setEnabled(True))
        self.downloader.error.connect(lambda _: self.btn_save_url.setEnabled(True))
        self.downloader.progress.connect(self._on_download_progress)
        self.downloader.finished.connect(self._on_download_finished)
        self.downloader.error.connect(self._on_download_error)
        self.downloader.start()

    def _on_download_progress(self, downloaded: int, total: int, pct: float):
        """Updates download progress bar and byte counters."""
        self.progress_bar.setValue(int(pct))
        dl_mb = downloaded / (1024 * 1024)
        if total > 0:
            tot_mb = total / (1024 * 1024)
            self.lbl_download_progress.setText(f"Downloading: {dl_mb:.1f} MB / {tot_mb:.1f} MB ({pct:.0f}%)")
        else:
            self.lbl_download_progress.setText(f"Downloaded: {dl_mb:.1f} MB")

    def _on_download_finished(self, file_path: str):
        """Called when download is complete."""
        self.downloaded_file_path = file_path
        self.progress_container.hide()
        self.btn_download.hide()
        self.btn_open_file.setText(f"🚀 Open {os.path.basename(file_path)}")
        self.btn_open_file.show()
        self.lbl_status.setText("✓ Download complete! Ready to install.")
        self.lbl_status.setStyleSheet("color: #22c55e; font-weight: bold;")

        # Automatically launch or prompt to open
        reply = QMessageBox.question(
            self,
            "Update Downloaded",
            f"Graffy v{self.last_info.latest_version} has been successfully downloaded!\n\n"
            f"File: {os.path.basename(file_path)}\n\n"
            "Save your work before installing. On Windows, close Graffy and follow the installer. "
            "On macOS, quit Graffy, open the disk image (or extract the ZIP), "
            "and drag Graffy.app into Applications to replace the old version.\n\n"
            "Would you like to open the update package now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._on_open_downloaded_file()

    def _on_download_error(self, err_msg: str):
        """Handles download failure and provides browser fallback."""
        self.progress_container.hide()
        self.btn_download.setEnabled(True)
        self.btn_download.setText("⬇️ Retry Download")
        self.lbl_status.setText("Download failed")
        self.lbl_status.setStyleSheet("color: #ef4444; font-weight: bold;")
        
        QMessageBox.warning(
            self,
            "Download Error",
            f"Could not complete the automatic download:\n\n{err_msg}\n\n"
            "You can click 'View on Web' to download directly from your browser."
        )
        self.btn_browser_fallback.show()

    def _on_open_downloaded_file(self):
        """Opens downloaded DMG or ZIP in native OS file manager / installer."""
        if self.downloaded_file_path and os.path.exists(self.downloaded_file_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.downloaded_file_path))

    def _on_browser_fallback_clicked(self):
        """Opens release page in web browser."""
        if self.last_info:
            target_url = self.last_info.html_url or self.last_info.download_url
            if target_url:
                QDesktopServices.openUrl(QUrl(target_url))

    def _save_settings(self):
        """Saves custom update manifest or GitHub repository."""
        new_url = self.txt_url.text().strip()
        set_configured_update_url(new_url)
        QMessageBox.information(self, "Settings Saved", f"Update source saved as:\n{new_url}")
        self.check_updates()

    def _busy(self):
        return any(w is not None and w.isRunning() for w in (self.worker, self.downloader))

    def done(self, result):
        # Keep the owning dialog alive until its QThreads have stopped.
        if self._busy():
            self.lbl_status.setText("Please wait for the update check or download to finish.")
            return
        super().done(result)

    def closeEvent(self, event):
        if self._busy():
            event.ignore()
            self.lbl_status.setText("Please wait for the update check or download to finish.")
        else:
            super().closeEvent(event)
