; ControlBridge installer (Inno Setup 6) - Made by Silverback
; Built automatically by GitHub Actions (.github/workflows/build-installer.yml)

#ifndef AppVersion
  #define AppVersion "0.7.0"
#endif

[Setup]
AppId={{8F3C2A51-6B7D-4E2A-9C1F-5A0D3B7E9A11}
AppName=ControlBridge
AppVersion={#AppVersion}
AppPublisher=Made by Silverback
AppPublisherURL=https://madebysilverback.com
; Installs for the current user only: no admin prompt, and profiles stay editable.
DefaultDirName={localappdata}\Programs\ControlBridge
DefaultGroupName=ControlBridge
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist-installer
OutputBaseFilename=ControlBridge-Setup
SetupIconFile=..\icon.ico
UninstallDisplayIcon={app}\ControlBridge.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=ControlBridge

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\ControlBridge.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ControlBridge Prompts.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ControlBridge Profile Maker.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\assets\controller.png"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\assets\logo-header.png"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\fonts\*.ttf"; DestDir: "{app}\fonts"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\controller_layout.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\profiles\*.json"; DestDir: "{app}\profiles"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\profiles\library\*.json"; DestDir: "{app}\profiles\library"; Flags: ignoreversion
Source: "..\README.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ControlBridge"; Filename: "{app}\ControlBridge.exe"
Name: "{group}\ControlBridge - Button Prompts"; Filename: "{app}\ControlBridge Prompts.exe"
Name: "{group}\ControlBridge - Profile Maker"; Filename: "{app}\ControlBridge Profile Maker.exe"
Name: "{group}\ControlBridge - Game Profiles"; Filename: "{app}\profiles"
Name: "{group}\Read me"; Filename: "{app}\README.txt"
Name: "{userdesktop}\ControlBridge"; Filename: "{app}\ControlBridge.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ControlBridge.exe"; Description: "Start ControlBridge now"; Flags: postinstall nowait skipifsilent

[UninstallRun]
; Put the games' original keyboard prompts back before removing the app.
Filename: "{app}\ControlBridge Prompts.exe"; Parameters: "--restore-all"; RunOnceId: "RestorePrompts"; Flags: waituntilterminated

[UninstallDelete]
Type: filesandordirs; Name: "{app}\backups"
Type: filesandordirs; Name: "{app}\profile_maker"
