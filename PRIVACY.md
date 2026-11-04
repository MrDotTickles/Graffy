# Graffy privacy information

Graffy processes imported files, formulas, fitting and statistics on your computer. The local table importer does not contact an AI service and needs no API key. The app contains no configured analytics, advertising or crash-upload service.

Projects contain the data you import, graph settings, formulas and reports. Save and share them deliberately. Exported CSV, spreadsheets and figures contain the content you choose to export. Reports, figure labels and document metadata may include text you entered. Do not upload confidential projects, screenshots or logs to a public support issue.

The app stores preferences and recently opened file paths locally through Qt's platform settings storage (for example the Windows registry). Downloaded updates are cached locally until installed or removed. Local settings, your Projects folder and caches are not included in the packaged downloads.

## Network access

With automatic checks enabled, the app contacts GitHub after startup and about every six hours to check for releases. The request identifies the Graffy version and operating-system platform; the remote service also receives normal connection information such as your IP address. No worksheet data or project file is attached. Disable automatic checks in Help → Check for Updates → Settings. Manual checks and downloads still contact the selected update service. Configuring a custom update source sends those requests to that service instead.

Updates are installed only after your action. The app does not silently uninstall itself or upload your documents. Its checksum checks detect corrupt downloads; they do not replace trusted publisher signing.

The download website requests public release information from GitHub and loads its web fonts from Google Fonts. Hosting, GitHub and Google can receive normal web-request metadata. The static site has no app-account login, project-upload form or application analytics script. Your ChatGPT Sites access and hosting policies are separate from the desktop app.

Support information posted to GitHub is public unless you use a private channel. To report a security issue, follow SECURITY.md without posting keys or private data.
