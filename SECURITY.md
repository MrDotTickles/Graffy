# Security policy

Use the latest release for security fixes. Older releases may lack current protections. Do not use Graffy to open executable installers from untrusted sources. Formula input is restricted to approved mathematical syntax and functions; it is not a general Python interpreter. Project loading uses JSON, not pickle, and does not execute saved formulas on opening.

## Reporting a vulnerability

Use the repository's **Security → Report a vulnerability** option if available. If private reporting is unavailable, open a minimal issue asking the maintainer for a private contact channel; do not publish exploit details, credentials, personal files or confidential data in the issue. Remove identifying data from reproductions. Known credentials that were exposed must be revoked or rotated; deleting a file does not invalidate them or remove Git history.

## Release controls

Public releases must pass tracked-file privacy checks, redacted Git-history secret scanning, dependency advisory auditing, all application tests and packaged-app checks. Distribution artifacts must exclude local settings, credentials, private keys, user projects and debug logs, and include licenses and privacy notices. Do not bypass these gates to publish a failing build.

SHA-256 checksums protect download integrity. Builds remain unsigned until trusted Windows signing and Apple Developer ID signing/notarization are configured. Describe unsigned builds as previews, and do not promise warning-free installation or ask users to disable OS protections.
