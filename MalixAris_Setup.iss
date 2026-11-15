#define MyAppName "MalixAris Studio"
#define MyAppVersion "3.2"
#define MyAppPublisher "MalixAris"
#define MyAppExeName "MalixAris Studio.exe"

[Setup]
AppId={{A91F4D21-6B20-4C3A-9D15-72B4C0A81E32}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\MalixAris Studio
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
OutputDir=installer
OutputBaseFilename=MalixAris_Studio_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=no
ArchitecturesInstallIn64BitMode=x64

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Dirs]
Name: "{app}\data"
Name: "{app}\output"
Name: "{app}\work"
Name: "{app}\logs"
Name: "{app}\projects"

[Files]
Source: "dist\MalixAris Studio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "installer_assets\MicrosoftEdgeWebView2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\MalixAris Studio"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\MalixAris Studio"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{tmp}\MicrosoftEdgeWebView2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Installing Microsoft Edge WebView2 Runtime..."; Flags: waituntilterminated runhidden
Filename: "{app}\{#MyAppExeName}"; Description: "Launch MalixAris Studio"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
; Keep user-created project and render data by design.
Type: filesandordirs; Name: "{app}\_internal"
