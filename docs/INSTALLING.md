# Install and update Graffy

Download only from [Graffy's official releases](https://github.com/MrDotTickles/Graffy/releases/latest).
You do not need Python, Git, a command prompt, or a GitHub account.
The links below work after a packaged release has been published.

## Windows

1. [Download the Windows installer](https://github.com/MrDotTickles/Graffy/releases/latest/download/Graffy_Windows_Setup.exe).
2. Open `Graffy_Windows_Setup.exe` and follow the installer.
3. Open Graffy from the Start menu or its desktop shortcut.

The app installs for your Windows account without an administrator password.
This package targets 64-bit Windows; there is no 32-bit installer.
The measured build downloads about 71.2 MB and installs about 241.4 MB of app files.
The installer uses the standard per-user location and creates launch shortcuts.
See [package sizes](PACKAGE_SIZE.md) for details.

For a portable copy, download `Graffy_Windows.zip` from the release's Assets,
extract the **entire** ZIP, and run `Graffy.exe` inside the extracted folder.
Keep its `_internal` folder beside the executable.

## macOS

1. Open Apple menu → About This Mac. A **Chip** beginning with Apple M means Apple
   Silicon; **Processor** naming Intel means Intel.
2. Download [Apple Silicon](https://github.com/MrDotTickles/Graffy/releases/latest/download/Graffy_macOS_arm64.dmg)
   or [Intel](https://github.com/MrDotTickles/Graffy/releases/latest/download/Graffy_macOS_x86_64.dmg).
3. Open the DMG and drag **Graffy.app** onto **Applications**.
4. Eject the Graffy disk, then open Graffy from Applications.

Architecture-specific ZIPs are also available under the release's Assets.
The app is built on macOS 15; older macOS versions have not been validated.

## If your computer blocks the app

The initial builds are unsigned. Windows can show an unrecognized-publisher warning,
and macOS can block an app that has not been Developer ID signed and notarized.
Signing and notarization are still needed for a smoother public installation.
Do not disable your antivirus or operating-system protections.

Confirm the download came from the official release. If you are unsure, cancel
and [report the problem](https://github.com/MrDotTickles/Graffy/issues).
See [Apple's explanation of downloaded-app checks](https://support.apple.com/en-us/102445).
A checksum file is available with each release for users who want to verify a download.

## Updating

Graffy shows an update notice when it finds a newer published release. You can also
choose Help → Check for Updates. Download the new package, save your work, and quit Graffy.

- Windows: run the new installer. It updates the existing per-user installation.
- Mac: open the new DMG and drag Graffy into Applications, replacing the previous app.
- Windows portable: extract into a new folder and launch that copy.

Keep `.kgraph` project files in Documents or another personal folder. Do not keep
personal files inside the app bundle or its `_internal` dependency folder.
An older app that lacks automatic checks needs one manual update to gain them.

## Need help?

[Open a support issue](https://github.com/MrDotTickles/Graffy/issues) with your
Windows/macOS version, Mac chip if relevant, Graffy version, and the exact error.
Avoid attaching private research data unless you intend to share it publicly.
