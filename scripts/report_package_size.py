"""Report installed and download sizes from actual build artifacts."""
import os
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    name = "Windows" if sys.platform == "win32" else f"macOS_{platform.machine()}"
    app = ROOT / "dist" / ("Graffy" if sys.platform == "win32" else "Graffy.app")
    if not app.is_dir():
        raise SystemExit(f"Build the app first: {app}")
    size = sum(p.stat().st_size for p in app.rglob("*") if p.is_file() and not p.is_symlink())
    lines = [f"Graffy {name} package sizes", "", f"Application files: {size / 1_000_000:.1f} MB ({size / 1_048_576:.1f} MiB)"]
    for extension in ("exe", "dmg", "zip"):
        for package in sorted((ROOT / "dist").glob(f"Graffy_{name}*.{extension}")):
            size = package.stat().st_size
            lines.append(f"{package.name}: {size / 1_000_000:.1f} MB ({size / 1_048_576:.1f} MiB)")
    lines.extend(["", "MB uses 1,000,000 bytes. MiB uses 1,048,576 bytes.", "Application-file size excludes filesystem allocation and installer bookkeeping.", "The download includes Python and runtime libraries; users do not install them separately."])
    report = "\n".join(lines) + "\n"
    (ROOT / "dist" / f"Graffy_{name}_Size.txt").write_text(report, encoding="utf-8")
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write("```text\n" + report + "```\n")


if __name__ == "__main__":
    main()
