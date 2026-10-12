#define AppName "PSEEK"
[Setup]
AppId={{2b6a7b8a-b878-4b38-a482-134b99c0de17}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Andrej Ristic
AppPublisherURL=https://github.com/andrejristic/pseek
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile={#SourceDir}\LICENSE.txt
OutputDir={#OutDir}
OutputBaseFilename=PSEEK-Setup-{#AppVersion}
SetupIconFile={#SourceDir}\pseek.ico
UninstallDisplayIcon={app}\pseek.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\pseek.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\pseek.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\pseek.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
