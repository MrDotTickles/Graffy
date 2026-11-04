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

Release v1.0.5 passed **489 tests on each of Windows, Apple Silicon Mac and Intel Mac**, followed by packaged-app scientific/project/spreadsheet/export checks. The mandatory history/source/dependency audit passed. Final artifact inspection checked 1,291 Windows files and 738 files per Mac app with no findings. All three public installer links returned HTTP 200. The Windows installer is 71,667,577 bytes; its SHA-256 matched the published checksum: `E1CD0CFE35CA4A15E20D0F52E96C104F839DAC4F6B7A4FFB4F948375425EC27C`.

The main-branch developer tests also pass independently of packaging tools. Future local commits use the authenticated GitHub account's no-reply address. Historical Git author identities remain public; published history was not destructively rewritten.

The website's privacy, security and GPL links were published as Site version 6. Its source history was scanned before the notice-only footer change; the added links/favicon were reviewed and static asset references validated. No personal data-upload feature was added.

Evidence: [release workflow](https://github.com/MrDotTickles/Graffy/actions/runs/41925096223), [public preview](https://github.com/MrDotTickles/Graffy/releases/tag/v1.0.5). Redacted local scan reports remain in ignored `.tmp/public-audit/` for review; they are not application resources.

## Remaining launch limits

Windows installers are not code signed; Mac apps are not Developer ID signed or notarized. Credentials/accounts and real-machine installation/upgrade checks remain necessary. These are unsigned previews until [the launch checklist](LAUNCH_READINESS.md) is completed. This is a documented code/distribution review, not a claim of formal penetration testing, legal certification or guaranteed absence of every possible vulnerability.
