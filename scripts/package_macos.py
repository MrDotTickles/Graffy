"""Create a drag-to-Applications DMG and a compatibility ZIP on macOS."""
import argparse
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arch", choices=["arm64", "x86_64"], default=platform.machine())
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error("DMG creation requires macOS.")
    app = ROOT / "dist" / "Graffy.app"
    if not (app / "Contents" / "MacOS" / "Graffy").is_file():
        parser.error("Build dist/Graffy.app first with scripts/build_app.py.")
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    stem = ROOT / "dist" / f"Graffy_macOS_{args.arch}"
    with tempfile.TemporaryDirectory(prefix="dmg-", dir=build) as temporary:
        staging = Path(temporary)
        subprocess.run(["ditto", str(app), str(staging / "Graffy.app")], check=True)
        (staging / "Applications").symlink_to("/Applications", target_is_directory=True)
        (staging / "Install Graffy.txt").write_text(
            "Drag Graffy.app onto Applications to install.\n"
            "Then eject this disk and open Graffy from Applications.\n\n"
            "Updating? Save your work and quit Graffy before replacing it.\n"
            "Support: https://github.com/MrDotTickles/Graffy/issues\n",
            encoding="utf-8")
        subprocess.run(["hdiutil", "create", "-volname", "Graffy", "-srcfolder",
                        str(staging), "-ov", "-format", "UDZO", str(stem) + ".dmg"], check=True)
    subprocess.run(["hdiutil", "verify", str(stem) + ".dmg"], check=True)
    subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent",
                    str(app), str(stem) + ".zip"], check=True)
    print(f"Ready: {stem}.dmg and {stem}.zip")


if __name__ == "__main__":
    main()
