; Compile only after the Windows frozen bundle and smoke test succeed.
; AppId is stable: keep it for future upgrades of this same product.
#define ProductName "Crystallographic Orthogonal Indexer"
#define ProductVersion "1.0"
#define ExeName "CrystallographicOrthogonalIndexer.exe"

[Setup]
AppId={{B11BE05C-E5E8-4447-8DB4-A8289A009D74}
AppName={#ProductName}
AppVersion={#ProductVersion}
AppVerName={#ProductName} {#ProductVersion}
VersionInfoVersion=1.0.0.0
VersionInfoProductName={#ProductName}
; AppPublisher intentionally omitted; no company/signing identity was supplied.
DefaultDirName={localappdata}\Programs\Crystallographic Orthogonal Indexer
DefaultGroupName={#ProductName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0
SourceDir=..
OutputDir=release
OutputBaseFilename=CrystallographicOrthogonalIndexer-{#ProductVersion}-windows-x64-Setup
SetupIconFile=packaging\app.ico
UninstallDisplayIcon={app}\{#ExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
Uninstallable=yes
CreateUninstallRegKey=yes
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
; No signing directive: this candidate is unsigned, not publisher-verified.

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "dist\CrystallographicOrthogonalIndexer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#ProductName}"; Filename: "{app}\{#ExeName}"; WorkingDir: "{app}"
Name: "{group}\User guide"; Filename: "{app}\_internal\USER_GUIDE.txt"
Name: "{group}\Uninstall {#ProductName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#ProductName}"; Filename: "{app}\{#ExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ExeName}"; Description: "Launch {#ProductName}"; Flags: nowait postinstall skipifsilent unchecked

; No registry machine settings, PATH edits, services, network downloads,
; autorun/startup entries, or broad UninstallDelete entries.
; User TXT reports outside the installation are not removed by uninstall.
