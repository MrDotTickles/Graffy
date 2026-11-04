#ifndef AppVersion
  #error AppVersion must be supplied with /DAppVersion=1.2.3
#endif

[Setup]
AppId={{2CD4E23B-E1B3-47AF-BCBF-638825724688}
AppName=Graffy
AppVersion={#AppVersion}
AppPublisher=Graffy
LicenseFile=..\LICENSE
AppPublisherURL=https://github.com/MrDotTickles/Graffy
DefaultDirName={localappdata}\Programs\Graffy
DefaultGroupName=Graffy
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=Graffy_Windows_Setup
SetupIconFile=..\omnigraph\ui\styles\icons\graffy.ico
UninstallDisplayIcon={app}\Graffy.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
DisableDirPage=yes
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no

[InstallDelete]
; Replace bundled dependencies completely to avoid loading obsolete DLLs on upgrade.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\Graffy\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Graffy"; Filename: "{app}\Graffy.exe"
Name: "{autodesktop}\Graffy"; Filename: "{app}\Graffy.exe"

[Run]
Filename: "{app}\Graffy.exe"; Description: "Launch Graffy"; Flags: nowait postinstall skipifsilent
