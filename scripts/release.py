"""Test, version, commit and push one stable release. No third party imports."""
import argparse
import pathlib
import re
import subprocess
import sys
import os
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "omnigraph" / "__init__.py"


def find_git():
    executable = shutil.which("git")
    if executable:
        return executable
    # GitHub Desktop bundles Git but does not always add it to PATH.
    desktop = pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "GitHubDesktop"
    candidates = sorted(desktop.glob("app-*/resources/app/git/cmd/git.exe"),
                        key=lambda p: p.stat().st_mtime, reverse=True)
    if candidates:
        return str(candidates[0])
    raise OSError("Install Git for Windows or GitHub Desktop, then try again.")


def run(*args, capture=False):
    if args[0] == "git":
        args = (find_git(), *args[1:])
    return subprocess.run(args, cwd=ROOT, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="New version, e.g. 1.0.1")
    parser.add_argument("--prepare-only", action="store_true", help="Bump version and test without Git changes")
    args = parser.parse_args()
    if not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", args.version):
        parser.error("Use a stable version such as 1.0.1 (no v prefix).")
    original = VERSION_FILE.read_text(encoding="utf-8")
    current = re.search(r'__version__ = "([^"]+)"', original).group(1)
    if tuple(map(int, args.version.split('.'))) <= tuple(map(int, current.split('.'))):
        parser.error(f"Version must be greater than {current}.")
    tag = f"v{args.version}"
    if not args.prepare_only:
        run("git", "rev-parse", "--show-toplevel", capture=True)
        run("git", "var", "GIT_AUTHOR_IDENT", capture=True)
        branch = run("git", "branch", "--show-current", capture=True).strip()
        if not branch:
            parser.error("Check out your release branch first (detached HEAD).")
        remote = run("git", "remote", "get-url", "origin", capture=True).strip()
        print(f"Release target: {remote}, branch {branch}, tag {tag}", flush=True)
        if run("git", "status", "--porcelain", capture=True).strip():
            parser.error("Commit your changes first. This helper commits only the version bump.")
        run("git", "fetch", "origin", "--tags")
        stable_tags = [tuple(map(int, t[1:].split('.'))) for t in
                       run("git", "tag", "--list", capture=True).splitlines()
                       if re.fullmatch(r"v\d+\.\d+\.\d+", t)]
        if stable_tags and tuple(map(int, args.version.split('.'))) <= max(stable_tags):
            parser.error("Use a version higher than all existing stable release tags.")
        if run("git", "tag", "--list", tag, capture=True).strip():
            parser.error(f"Tag {tag} already exists; use a new version.")
    VERSION_FILE.write_text(original.replace(f'__version__ = "{current}"',
                                            f'__version__ = "{args.version}"'), encoding="utf-8")
    try:
        run(sys.executable, "-m", "pytest", "tests/", "-q")
    except BaseException:
        VERSION_FILE.write_text(original, encoding="utf-8")
        raise
    if args.prepare_only:
        print(f"Prepared {tag}. No commit, tag or push performed.")
        return
    run("git", "add", "omnigraph/__init__.py")
    run("git", "commit", "-m", f"Release {tag}")
    run("git", "tag", "-a", tag, "-m", f"Graffy {tag}")
    run("git", "push", "--atomic", "origin", f"HEAD:refs/heads/{branch}", f"refs/tags/{tag}")
    print("Pushed! GitHub Actions will test, build, and publish the release.")


if __name__ == "__main__":
    try:
        main()
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f"Release stopped: {exc}\nNothing is force-pushed. Inspect git status and tags before retrying.", file=sys.stderr)
        sys.exit(1)
