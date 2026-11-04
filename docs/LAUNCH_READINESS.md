# Public launch requirements

Updated November 4, 2026. This replaces the older launch notes. The owner selected a clearly labeled security-hardened **unsigned public preview**, and v1.0.5 is published. A broad, polished general-public launch still needs publisher signing/notarization and real-machine installation/upgrade checks.

## Mandatory gates before publishing any new app version

- [x] Scan tracked source and all Git history for known credentials; redact scanner reports.
- [x] Exclude local keys, credentials, user projects, databases, debug logs and preferences from source and finished packages.
- [x] Inspect compressed application code and reject personal build paths in artifacts.
- [x] Restrict spreadsheet formulas to approved math syntax/functions; disallow file/system access and Python introspection.
- [x] Require HTTPS for remote update metadata, downloads and browser links, including redirects; retain size/checksum verification and atomic downloads.
- [x] Harden Excel XML parsing with defusedxml.
- [x] Include GPLv3, privacy/security information, dependency licenses and an exact dependency inventory in finished packages.
- [x] Run the full test suite and packaged scientific/project/spreadsheet/export smoke checks.
- [x] Run dependency advisory auditing and all-history secret scanning in CI before release builds.
- [x] Audit each built Windows/Mac app before packaging; publish only a complete set of release assets.
- [x] Pin GitHub Actions to immutable commits; enable dependency monitoring, secret push protection and private vulnerability reporting.
- [x] v1.0.5 release workflow 41925096223 succeeded. Each Windows/Mac job passed 489 tests plus package audits and compiled smoke checks. Public installer downloads were checked and the Windows installer checksum was verified.

## Requirements still needed for a full public launch

- [ ] Trusted Windows code signing configured through a signing provider/certificate. Keep signing keys/passwords in secure CI secrets, never the repo or app.
- [ ] Apple Developer ID signing, hardened runtime, notarization and stapling configured with the owner's Apple account.
- [ ] Fresh install and upgrade from a previous version tested on a clean Windows computer and both supported Mac architectures, including reopening a saved project.
- [ ] Gatekeeper/SmartScreen behavior checked on actual downloaded packages. Never ask users to disable OS protections.
- [ ] Test every additional OS version you intend to claim support for. Mac builds target macOS 15; no installer is provided for Linux/mobile/Chromebook.

Until these are satisfied, label downloads as unsigned previews. An executable checksum is an integrity check, not publisher authentication or a promise of zero vulnerabilities.

## Sharing rules

Share the finished release downloads or a GitHub source archive. **Do not upload this entire working folder.** Your ignored Projects directory, local environment and temporary files are private development material. Keep real user files and screenshots out of public support issues. If a credential is ever exposed, revoke/rotate it; deleting it from the latest files does not erase history or invalidate it.

## Privacy and licensing

See [PRIVACY.md](../PRIVACY.md), [SECURITY.md](../SECURITY.md), [LICENSE](../LICENSE) and [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). The owner selected GPLv3. Preserve the corresponding source, build instructions and dependency notices when distributing.

## Audit limits

Secret scanners recognize known patterns and can have false positives/negatives. Python advisory scans do not exhaustively assess native Qt/OpenSSL/Python binaries or prove that every input parser is safe. GUI smoke checks do not replace independent security review or clean-machine installation tests. Review future new dependencies, code paths and data formats rather than treating this audit as permanent certification.
