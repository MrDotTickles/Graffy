"""Build Graffy consistently, without collecting DLLs from unrelated PATH tools."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distpath", default="dist")
    parser.add_argument("--workpath", default="build")
    parser.add_argument("--specpath", default="build")
    args = parser.parse_args()
    env = os.environ.copy()
    if sys.platform == "win32":
        # PyInstaller searches PATH for dependent DLLs. Poppler, Git and other
        # tools can expose incompatible copies (notably ICU) with the same name.
        windows = Path(env.get("SystemRoot", r"C:\Windows"))
        env["PATH"] = os.pathsep.join(map(str, [Path(sys.executable).parent,
                                              Path(sys.base_prefix),
                                              windows / "System32", windows]))
    icon = "graffy.icns" if sys.platform == "darwin" else "graffy.ico"
    command = [sys.executable, "-m", "PyInstaller", "--name", "Graffy",
               "--windowed", "--noconfirm", "--clean", "--icon",
               str(ROOT / "omnigraph" / "ui" / "styles" / "icons" / icon),
               "--collect-data", "omnigraph", "--distpath", args.distpath,
               "--workpath", args.workpath, "--specpath", args.specpath]
    if sys.platform == "darwin":
        command.extend(["--osx-bundle-identifier", "com.graffy.desktop"])
    for module in ("pytest", "_pytest", "tkinter", "IPython",
                   "PIL.AvifImagePlugin", "PIL._avif"):
        command.extend(["--exclude-module", module])
    for module in ("scipy.special", "scipy.optimize", "scipy.signal", "scipy.stats",
                   "openpyxl", "PyQt6", "matplotlib", "matplotlib.backends.backend_pdf",
                   "matplotlib.backends.backend_svg", "matplotlib.backends.backend_ps"):
        command.extend(["--hidden-import", module])
    subprocess.run([*command, str(ROOT / "main.py")], cwd=ROOT, env=env, check=True)


if __name__ == "__main__":
    main()
