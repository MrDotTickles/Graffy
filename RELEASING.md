# Publish Graffy from this folder

This folder already tracks `https://github.com/MrDotTickles/Graffy.git` on `main`.
The current source version is `1.0.3`; choose an unused higher version for the next release (for example **1.0.4**). The release helper also checks existing Git tags.
**Graffy v1.0.3 is published**, including the Windows installer and both Mac DMGs. Downloads are available from https://github.com/MrDotTickles/Graffy/releases/latest and the Graffy website.

## 1. Upload these changes

1. Open **GitHub Desktop** and sign in to the account with access to the repository.
2. Choose **File → Add local repository**, then select this `KyleGraphingSoftware` folder.
3. Review the Changes list. It should include `.github`, application source, icons,
   docs, scripts, packaging, tests, and requirements files. It should exclude
   `.venv`, `build`, `dist`, caches, and your personal `Projects`.
4. Enter a commit message such as **Prepare Graffy for launch** and choose **Commit to main**.
   Set your Git name/email if GitHub Desktop asks.
5. Choose **Push origin**. Do not create a second repository or overwrite existing tags.

The GitHub repository gets the source. You do not manually upload the `dist` folder.
A normal push runs tests without publishing a new version.

## 2. Publish the app

1. Double-click **scripts/Release_Graffy.bat** in this folder.
2. Enter a version higher than the source version and all existing release tags, such as **1.0.4** if it is available.
3. The helper checks Git and your author identity, updates the app's version, runs
   every test, commits that version, creates its tag, and pushes the branch and tag together.
4. Open [GitHub Actions](https://github.com/MrDotTickles/Graffy/actions).
   Wait for **Test, Build & Release Graffy** to finish successfully.
5. Open [the latest release](https://github.com/MrDotTickles/Graffy/releases/latest)
   and verify the Windows installer and both Mac DMGs are attached.

The workflow tests all three target platforms, launches each compiled app briefly,
creates the Windows installer and Mac disk images, and uploads all packages to a
hidden draft. Only a complete set is published. A failed build does not announce an update.

Keep the repository **public** so everyone can download and the app can check for
updates without a login. Repository Settings → Actions must allow workflows.
The publish job requests `contents: write` using GitHub's built-in token.
Organization policy can restrict this. Do not embed GitHub credentials in the app.

## 3. Give people one link

**Share this link:** https://github.com/MrDotTickles/Graffy

The README begins with download links for Windows, Apple Silicon Mac, and Intel Mac.
You can also share https://github.com/MrDotTickles/Graffy/releases/latest directly.
The links always lead to the latest published version. They will not work until
that release contains the corresponding package.

Users download a finished app, not the repository's **Code → Download ZIP** source.
They need no Python installation or GitHub account. Windows uses a normal installer;
Mac users drag the app from the disk image into Applications.
See [the installation guide](docs/INSTALLING.md).

## 4. Test the first rollout

Before advertising broadly, install the actual downloaded package on a clean
Windows computer and on each supported Mac architecture. Test an upgrade from the
previous app, confirm your saved project reopens, and confirm Help → Check for
Updates reports the new version correctly. macOS packaging and installer upgrades
cannot be fully validated by the Windows development machine alone.

The packages are currently unsigned. For a smoother public launch, arrange Windows
code signing and Apple Developer ID signing/notarization; these credentials are not
configured. DMGs alone do not satisfy Gatekeeper. See [launch readiness](docs/LAUNCH_READINESS.md).

## Future updates

Make changes → commit with GitHub Desktop → double-click `scripts/Release_Graffy.bat` →
enter a higher version → wait for Actions. The helper pushes the committed changes
with the release tag. Startup and six-hour checks notify users of the published version.
Users who disabled checks keep that choice. Users on an older app without update
notices need to download this new build once.

## Developer commands

From this folder on Windows:

Double-click `scripts/Setup_Graffy.bat` to restore the local development libraries after
cleanup. The launch and release buttons also do this automatically when `.venv`
is missing. This needs Python 3.13 and an internet connection. The large `.venv`,
`build`, and `dist` folders are generated locally and never uploaded to GitHub.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe -m pytest tests/ -q
.\.venv\Scripts\python.exe scripts/release.py 1.0.4
```

On macOS, use `python3 -m venv .venv`, then `.venv/bin/python` for the commands.
Use `scripts/build_windows_dist.bat` for a local portable build, or
`bash scripts/build_mac_app.sh` on a Mac. GitHub also builds the Windows installer.
Core release dependency versions are pinned in `constraints-release.txt`; update
those deliberately and validate every platform. Transitive dependencies still
resolve from the package index. Installed versions appear in the workflow logs.

The ordinary-user start button and START HERE guide stay at the root. Developer source launch buttons are under scripts/. Supporting tools are in `scripts/`,
installer configuration is in `packaging/`, icons are in
`omnigraph/ui/styles/icons/`, and generated packages are in ignored `dist/`.
`docs/examples/version.json` is a legacy server-manifest example; the app uses
GitHub Releases by default. The release helper also locates Git bundled with GitHub Desktop.

## If a release stops

Read the error above the release button's pause, or open the failed Actions job.
Fix errors and publish a new version. Do not reuse or force-push a published tag.
The workflow can resume an incomplete draft, but refuses to overwrite a public release.
If the helper's push fails, its local version commit and tag remain. After fixing
Git authentication or connectivity, push the existing branch and tag; do not rerun
that version bump. With Git on PATH, for version 1.0.1 on main:

```powershell
git push --atomic origin main refs/tags/v1.0.1
```

The helper does not commit your other edits or force-push. `--prepare-only` changes
the version and tests locally without committing or pushing. Manual **Run workflow**
on a branch builds artifacts; publishing requires a matching version tag.

References: [GitHub latest-download links](https://docs.github.com/en/repositories/releasing-projects-on-github/linking-to-releases),
[GitHub release creation](https://cli.github.com/manual/gh_release_create),
[Apple's app-download checks](https://support.apple.com/en-us/102445).
