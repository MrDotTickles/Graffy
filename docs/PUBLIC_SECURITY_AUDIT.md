# Public distribution security review

Review date: November 4, 2026. Scope: current tracked source, reachable local Git history, the source history of the download website, runtime network paths, dependency advisories and the published Windows ZIP plus a newly built hardened Windows app.

## Findings and changes

- Gitleaks 8.30.1 found no known credential leaks in the 13 pre-audit app commits or the 3 website source commits scanned. Current application source also passed. Reports were fully redacted; private key/token values are never printed by the new release gate.
- No tracked saved projects, credential files, local user-directory paths or email addresses were found by the source metadata review. Git author identities remain ordinary public repository metadata.
- The published Windows ZIP had 1,202 entries, with three public Matplotlib sample CSVs and no saved Graffy projects. App code inspection covered 1,025 code objects with no personal build paths. The newly built hardened app passed the artifact gate over 1,269 files before the final security-notice inclusion; final CI repeats this check for the exact release.
- One byte sequence initially resembled a token in SciPy's compiled HiGHS module. It was a C++ symbol in a byte-identical copy of the installed upstream SciPy module. Token boundary checking removed that false positive without exempting the library from scanning.
- The formula evaluator previously exposed the complete NumPy module. It now validates math-only syntax and exposes a limited math namespace, blocking file I/O, Python internals, indirect calls and comprehensions. Regression tests cover attempted file access and normal scientific formulas.
- Remote update traffic now requires HTTPS, rejects embedded URL credentials and downgrade redirects, bounds manifest size, and limits browser fallback to HTTPS. Existing checksum/length validation and atomic downloads remain.
- Added defusedxml for Excel imports; installed and resolved dependency advisory audits reported no known vulnerabilities at review time.
- Fixed a non-default interface-scale view-rebuild crash. Tests now use isolated temporary preferences rather than the maintainer's real recent-project settings.
- Added the owner's selected GPLv3 license, privacy/security policies, corresponding-source guidance, per-build dependency inventory and dependency license collection. Notices are included in Windows/Mac packages.
- Added mandatory source/history/dependency gates before release builds and artifact inspection before packaging. Action versions are pinned to exact upstream commits. GitHub secret scanning and push protection were already enabled; dependency alerts/security updates and private vulnerability reporting were enabled and verified.

## Validation

The complete suite passed 485 tests after runtime fixes, and the final release-gate extension passed its focused security tests. The final version's release helper and Windows/Mac CI repeat the complete suite; use those results for the exact shipped version. Compiled smoke, license inclusion and package privacy checks must all pass before publishing.

## Remaining launch limits

Windows installers are not code signed; Mac apps are not Developer ID signed or notarized. Credentials/accounts and real-machine installation/upgrade checks remain necessary. These are unsigned previews until [the launch checklist](LAUNCH_READINESS.md) is completed. This is a documented code/distribution review, not a claim of formal penetration testing, legal certification or guaranteed absence of every possible vulnerability.
