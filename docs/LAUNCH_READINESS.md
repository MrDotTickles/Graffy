# Launch readiness

Prepared on November 2, 2026. Source version remains `1.0.0`; publish `1.0.1` or higher.
No new commit, push, tag, or GitHub release was created during this cleanup.

After the latest verification, the final Windows installer and measured size
report are retained in `dist/`. Local `.venv`, build caches, and the unpacked app
were removed to avoid duplicate disk use. Windows source launch/release buttons
restore the development environment through `Setup_Graffy.bat` when needed.
See [package size and verification details](PACKAGE_SIZE.md).

## Verified on this Windows development machine

- Full regression suite: **401 passed**, with one SciPy precision-loss warning
  from an existing nearly-identical-data statistics test.
- Windows installer compiled successfully: 71.2 MB download, 241.4 MB application files.
- The packaged app passed fitting, project round-trips, CSV/Excel, and raster/vector exports.
- A fresh Windows standalone app compiled using the organized paths and shared
  build script. `dist/Graffy/Graffy.exe --smoke-test` returned exit code **0**.
- Python source syntax and workflow YAML parse successfully.
- Download selection covers Windows installer preference, Mac architecture,
  DMG preference, legacy ZIP compatibility, and unavailable-platform behavior.
- Saved personal projects remain in `Projects/`, excluded from Git.
- Stale debug packages and caches were removed. Root icon duplicates were checked
  against the canonical icons before removal.

## Ready to run when you push a version tag

- Tests and executable launch checks on Windows, Apple Silicon Mac, and Intel Mac.
- Windows per-user installer, desktop/Start shortcuts, and portable ZIP.
- Mac disk images with an Applications shortcut, plus compatibility ZIPs.
- SHA-256 checksum list and complete-asset checks before publishing.
- README download links pointing to the latest public release.
- Automatic in-app update notices and verified downloads.

## Remaining launch checks

The GitHub matrix has not yet run with these unpushed files. Windows installer
install/upgrade and Mac disk-image creation/install/upgrade need the
first Actions run and checks on real target computers. This machine's app-launch
test does not verify those installation paths.

The repository is connected locally. Review and commit the source with GitHub
Desktop, push it, then run `Release_Graffy.bat`. Your Git author name/email and
GitHub authentication must be configured before committing or releasing.

## Signing for a smoother public download

Windows packages are not code signed. A trusted code-signing certificate or a
supported signing service is needed to establish publisher identity; signing
does not guarantee that every SmartScreen or organization policy warning disappears.

Mac packages are not Developer ID signed or notarized. For normal Gatekeeper
acceptance outside the App Store, arrange Apple Developer credentials, sign the
app and its bundled executable code with hardened runtime, submit for notarization,
and staple the notarization ticket before distributing. Recreating a DMG alone
does not perform those steps. Credentials and CI signing are not configured here.

Until signing is in place, describe these as unsigned preview builds. Do not
promise a warning-free installation or ask users to disable system protections.
Desktop packages currently target Windows 64-bit and Mac; no Linux/mobile package
is provided. Older macOS versions have not been validated.

See [release steps](../RELEASING.md) and [installation help](INSTALLING.md).

References: [Microsoft SmartScreen reputation](https://learn.microsoft.com/windows/apps/package-and-deploy/smartscreen-reputation)
and [Apple downloaded-app checks](https://support.apple.com/en-us/102445).
