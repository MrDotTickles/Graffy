"""
Cross-platform update checking and downloading engine for Graffy.
Supports:
1. GitHub Releases API (Native 1-click updates, direct binary downloads, release notes).
2. Custom cloud storage manifests (Google Drive, Dropbox, lab servers, local network folders).
"""

import sys
import os
import json
import re
import platform
import hashlib
import tempfile
from urllib.parse import urlparse
from packaging.version import Version
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict
from PyQt6.QtCore import QSettings, QThread, pyqtSignal

import omnigraph

DEFAULT_UPDATE_URL = "MrDotTickles/Graffy"


@dataclass
class UpdateAsset:
    """Represents a downloadable update file asset."""
    name: str
    download_url: str
    size_bytes: int = 0
    digest: str = ""


@dataclass
class UpdateInfo:
    """Represents the results of an update check."""
    current_version: str
    latest_version: str
    is_newer: bool
    release_date: str
    release_notes: str
    download_url: str
    assets: List[UpdateAsset] = field(default_factory=list)
    html_url: str = ""
    error: Optional[str] = None


def normalize_version(v_str: str) -> Tuple[int, ...]:
    """Parses a version string like '1.2.3' or 'v1.0' into a tuple of integers."""
    clean = re.sub(r'^[^\d]*', '', v_str.strip())
    parts = []
    for chunk in re.split(r'[-_.]', clean):
        digits = re.match(r'^\d+', chunk)
        if digits:
            parts.append(int(digits.group(0)))
        else:
            break
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def compare_versions(v1: str, v2: str) -> int:
    """
    Compares two version strings.
    Returns:
        1 if v1 > v2
       -1 if v1 < v2
        0 if v1 == v2
    """
    t1 = Version(v1.lstrip("vV"))
    t2 = Version(v2.lstrip("vV"))
    if t1 > t2:
        return 1
    elif t1 < t2:
        return -1
    return 0


def is_github_repo_or_url(text: str) -> bool:
    """Checks whether the input is a GitHub repository slug or URL."""
    text = text.strip()
    if urlparse(text).hostname in ("api.github.com", "github.com"):
        return True
    # Matches 'owner/repo' shorthand (e.g. 'kyle/graffy')
    if re.match(r'^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$', text):
        return True
    return False


def normalize_github_api_url(text: str) -> str:
    """
    Normalizes a GitHub repo shorthand or URL into the official GitHub releases API endpoint.
    Examples:
      - 'kyle/graffy' -> 'https://api.github.com/repos/kyle/graffy/releases/latest'
      - 'https://github.com/kyle/graffy' -> 'https://api.github.com/repos/kyle/graffy/releases/latest'
    """
    text = text.strip()
    if text.startswith("https://api.github.com/repos/") and text.endswith("/releases/latest"):
        return text

    # Extract owner and repo from github.com/owner/repo
    gh_match = re.search(r'github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)', text)
    if gh_match:
        owner, repo = gh_match.group(1), gh_match.group(2)
        repo = repo.replace('.git', '')
        return f"https://api.github.com/repos/{owner}/{repo}/releases/latest"

    # Shorthand: owner/repo
    slug_match = re.match(r'^([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)$', text)
    if slug_match:
        owner, repo = slug_match.group(1), slug_match.group(2)
        return f"https://api.github.com/repos/{owner}/{repo}/releases/latest"

    return text


def normalize_cloud_url(url: str) -> str:
    """Translates cloud storage links (Dropbox, Google Drive) into direct download links."""
    url = url.strip()
    if is_github_repo_or_url(url):
        return normalize_github_api_url(url)

    # Dropbox: change www.dropbox.com to dl.dropboxusercontent.com or append dl=1
    if "dropbox.com" in url:
        if "dl=0" in url:
            url = url.replace("dl=0", "dl=1")
        elif "dl=1" not in url:
            url = url + ("&dl=1" if "?" in url else "?dl=1")
        url = url.replace("www.dropbox.com", "dl.dropboxusercontent.com")

    # Google Drive: convert /file/d/<id>/view into direct export url
    gd_match = re.search(r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)', url)
    if gd_match:
        file_id = gd_match.group(1)
        url = f"https://drive.google.com/uc?export=download&id={file_id}"

    return url


def get_configured_update_url() -> str:
    """Retrieves the update manifest or GitHub repo from user preferences, defaulting to official repo."""
    settings = QSettings("Graffy", "Graffy")
    val = settings.value("updater/manifest_url", DEFAULT_UPDATE_URL)
    if not val:
        return DEFAULT_UPDATE_URL
    return str(val).strip()


def set_configured_update_url(url: str):
    """Saves the update manifest or GitHub repo to user preferences."""
    settings = QSettings("Graffy", "Graffy")
    settings.setValue("updater/manifest_url", url.strip())


def get_check_on_startup() -> bool:
    """Checks whether Graffy should check for updates silently on startup."""
    settings = QSettings("Graffy", "Graffy")
    val = settings.value("updater/check_on_startup", True)
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("true", "1", "yes")


def set_check_on_startup(enabled: bool):
    """Sets whether Graffy checks for updates on startup."""
    settings = QSettings("Graffy", "Graffy")
    settings.setValue("updater/check_on_startup", enabled)


def _require_https(url):
    parsed=urlparse(url)
    if parsed.scheme.lower()!="https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Remote updates require HTTPS without embedded credentials.")


def fetch_update_manifest(manifest_url: str, timeout: float = 6.0) -> dict:
    """
    Fetches and parses the update data from GitHub API, HTTP JSON, or local file.
    """
    if not manifest_url:
        raise ValueError("No update manifest or GitHub repository has been configured.")

    # 1. Local or network drive path
    if os.path.exists(manifest_url) or manifest_url.startswith("file://"):
        local_path = manifest_url.replace("file://", "")
        with open(local_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # 2. Remote HTTP/HTTPS URL (including GitHub Releases API)
    clean_url = normalize_cloud_url(manifest_url)
    _require_https(clean_url)
    req = urllib.request.Request(
        clean_url,
        headers={
            "User-Agent": f"Graffy-Updater/{omnigraph.__version__} ({sys.platform})",
            "Accept": "application/vnd.github.v3+json, application/json"
        }
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        _require_https(response.geturl() if hasattr(response,"geturl") else clean_url)
        raw_bytes = response.read(4*1024*1024+1)
        if len(raw_bytes)>4*1024*1024:
            raise ValueError("Update manifest is too large.")
        return json.loads(raw_bytes.decode("utf-8"))


def check_for_updates(manifest_url: Optional[str] = None, timeout: float = 6.0) -> UpdateInfo:
    try:
        return _check_for_updates(manifest_url, timeout)
    except Exception as exc:
        return UpdateInfo(omnigraph.__version__, omnigraph.__version__, False,
                          "", "", "", error=f"Invalid update response: {exc}")


def select_asset(assets: List[UpdateAsset]) -> Optional[UpdateAsset]:
    """Select only a compatible package, preferring the Windows installer."""
    if sys.platform == "win32":
        candidates = [a for a in assets if "windows" in a.name.lower()
                      and a.name.lower().endswith((".exe", ".zip"))]
        return next((a for a in candidates if a.name.lower().endswith(".exe")),
                    candidates[0] if candidates else None)
    if sys.platform == "darwin":
        arch = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "x86_64"
        names = [f"graffy_macos_{arch}.dmg", f"graffy_macos_{arch}.zip",
                 "graffy_macos_universal2.dmg", "graffy_macos_universal2.zip",
                 "graffy_macos.dmg", "graffy_macos.zip"]
        return next((a for name in names for a in assets if a.name.lower() == name), None)
    return next((a for a in assets if "linux" in a.name.lower()
                 and a.name.lower().endswith((".appimage", ".tar.gz"))), None)


def _check_for_updates(manifest_url: Optional[str] = None, timeout: float = 6.0) -> UpdateInfo:
    """
    Checks if a newer version of Graffy is available via GitHub or custom cloud JSON.
    Automatically parses assets and selects the appropriate download link for macOS vs Windows.
    """
    current_ver = getattr(omnigraph, "__version__", "1.0.0")
    url = manifest_url or get_configured_update_url()

    if not url:
        return UpdateInfo(
            current_version=current_ver,
            latest_version=current_ver,
            is_newer=False,
            release_date="",
            release_notes="",
            download_url="",
            error="No update source configured. Enter your GitHub repository (e.g. username/repo) in Settings."
        )

    try:
        data = fetch_update_manifest(url, timeout=timeout)
    except urllib.error.HTTPError as e:
        if e.code == 404 and is_github_repo_or_url(url):
            # GitHub returns 404 when no releases have been published yet
            return UpdateInfo(
                current_version=current_ver,
                latest_version=current_ver,
                is_newer=False,
                release_date="",
                release_notes="",
                download_url="",
                error="No published release was found. Check that the repository is public and has a release."
            )
        elif e.code == 404:
            err_msg = f"No update manifest found at '{url}'."
        else:
            err_msg = f"HTTP Error {e.code}: {e.reason}"
        return UpdateInfo(
            current_version=current_ver,
            latest_version=current_ver,
            is_newer=False,
            release_date="",
            release_notes="",
            download_url="",
            error=err_msg
        )
    except Exception as e:
        return UpdateInfo(
            current_version=current_ver,
            latest_version=current_ver,
            is_newer=False,
            release_date="",
            release_notes="",
            download_url="",
            error=f"Could not check for updates: {str(e)}"
        )

    # Check if this is a GitHub Releases response (contains 'tag_name')
    is_github = "tag_name" in data

    if is_github:
        latest_ver = str(data.get("tag_name", current_ver)).lstrip("vV ").strip()
        pub_at = str(data.get("published_at", ""))
        release_date = pub_at[:10] if pub_at else ""
        release_notes = str(data.get("body", "No release notes provided.")).strip()
        html_url = str(data.get("html_url", ""))

        raw_assets = data.get("assets", [])
        parsed_assets = [
            UpdateAsset(
                name=a.get("name", "Asset"),
                download_url=a.get("browser_download_url", ""),
                size_bytes=a.get("size", 0),
                digest=a.get("digest") or ""
            )
            for a in raw_assets
        ]

        selected = select_asset(parsed_assets)
        download_url = selected.download_url if selected else ""

    else:
        # Standard custom JSON format (Google Drive / Dropbox / web server)
        latest_ver = str(data.get("version", data.get("latest_version", current_ver))).lstrip("vV ").strip()
        release_date = str(data.get("release_date", data.get("date", ""))).strip()
        release_notes = str(data.get("release_notes", data.get("notes", "No release notes provided."))).strip()
        html_url = str(data.get("url", data.get("download_url", "")))
        parsed_assets = []

        if sys.platform == "darwin":
            download_url = data.get("download_mac") or data.get("download_url") or data.get("download", "")
        elif sys.platform == "win32":
            download_url = data.get("download_windows") or data.get("download_url") or data.get("download", "")
        else:
            download_url = data.get("download_linux") or data.get("download_url") or data.get("download", "")

    is_newer = compare_versions(latest_ver, current_ver) > 0

    return UpdateInfo(
        current_version=current_ver,
        latest_version=latest_ver,
        is_newer=is_newer,
        release_date=release_date,
        release_notes=release_notes,
        download_url=download_url,
        assets=parsed_assets,
        html_url=html_url,
        error=None
    )


class FileDownloadWorker(QThread):
    """
    Streams file downloads chunk-by-chunk in a background thread,
    emitting live progress updates for smooth UI progress bars.
    """
    progress = pyqtSignal(int, int, float)  # downloaded_bytes, total_bytes, percent (0.0 to 100.0)
    finished = pyqtSignal(str)              # local_file_path
    error = pyqtSignal(str)                 # error_message

    def __init__(self, url: str, destination_path: str, parent=None,
                 expected_size: int = 0, digest: str = ""):
        super().__init__(parent)
        self.url = url
        self.destination_path = destination_path
        self._is_cancelled = False
        self.expected_size = expected_size
        self.digest = digest

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        partial_path = None
        try:
            _require_https(self.url)
            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": f"Graffy-Downloader/{omnigraph.__version__} ({sys.platform})"}
            )
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                _require_https(resp.geturl() if hasattr(resp,"geturl") else self.url)
                total_size = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 64 * 1024  # 64 KB chunks

                os.makedirs(os.path.dirname(os.path.abspath(self.destination_path)), exist_ok=True)
                fd, partial_path = tempfile.mkstemp(
                    prefix=".graffy-", suffix=".part",
                    dir=os.path.dirname(os.path.abspath(self.destination_path)))
                hasher = hashlib.sha256()
                with os.fdopen(fd, "wb") as f:
                    while True:
                        if self._is_cancelled:
                            return
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        hasher.update(chunk)
                        downloaded += len(chunk)
                        pct = (downloaded / total_size * 100.0) if total_size > 0 else 0.0
                        self.progress.emit(downloaded, total_size, pct)

            if not self._is_cancelled:
                if (total_size and downloaded != total_size) or (
                        self.expected_size and downloaded != self.expected_size):
                    raise ValueError("Download is incomplete. Please retry.")
                if self.digest and self.digest != f"sha256:{hasher.hexdigest()}":
                    raise ValueError("Download checksum does not match the release asset.")
                os.replace(partial_path, self.destination_path)
                self.finished.emit(self.destination_path)
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))
        finally:
            if partial_path and os.path.exists(partial_path):
                os.remove(partial_path)
