$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$pythonWindowed = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonWindowed)) {
    throw 'Create the local .venv first. See RELEASING.md. Installed app users already get a shortcut from the installer.'
}
$shortcutPath = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Graffy.lnk'
$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonWindowed
$shortcut.Arguments = '"' + (Join-Path $projectRoot 'main.py') + '"'
$shortcut.WorkingDirectory = $projectRoot
$shortcut.IconLocation = (Join-Path $projectRoot 'omnigraph\ui\styles\icons\graffy.ico') + ',0'
$shortcut.Description = 'Graffy - Scientific Graphing & Data Analysis'
$shortcut.Save()
Write-Host "Created $shortcutPath" -ForegroundColor Green
