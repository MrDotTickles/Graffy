#ifndef AppVersion
  #error AppVersion must be supplied with /DAppVersion=1.2.3
#endif
#ifndef AppFiles
  #define AppFiles "..\dist\Graffy"
#endif
#define GraffyShellId "kyle.graffy.scientific.graphing.1.0"

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
WizardImageFile=graffy-wizard.bmp
WizardSmallImageFile=graffy-wizard-mark.bmp
DisableWelcomePage=no
DisableDirPage=yes
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no

[Messages]
SetupWindowTitle=Graffy Setup
WelcomeLabel1=Install Graffy
WelcomeLabel2=Graffy brings scientific plotting and data analysis into one workspace.%n%nClick Next to continue.
FinishedHeadingLabel=Graffy is ready
FinishedLabel=Open Graffy from the Start menu whenever you want to make a figure.

[Tasks]
Name: "desktopicon"; Description: "Add a Graffy shortcut to the desktop"; Flags: unchecked

[InstallDelete]
; Replace bundled dependencies completely to avoid loading obsolete DLLs on upgrade.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#AppFiles}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Graffy"; Filename: "{app}\Graffy.exe"; IconFilename: "{app}\Graffy.exe"; AppUserModelID: "{#GraffyShellId}"
Name: "{autodesktop}\Graffy"; Filename: "{app}\Graffy.exe"; IconFilename: "{app}\Graffy.exe"; AppUserModelID: "{#GraffyShellId}"; Tasks: desktopicon

[Run]
Filename: "{app}\Graffy.exe"; Description: "Open Graffy"; Flags: nowait postinstall skipifsilent
