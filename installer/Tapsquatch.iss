; Tapsquatch installer (Inno Setup 6) - Made by Silverback
; Built automatically by GitHub Actions (.github/workflows/build-installer.yml)

#ifndef AppVersion
  #define AppVersion "0.9.2"
#endif

[Setup]
AppId={{8F3C2A51-6B7D-4E2A-9C1F-5A0D3B7E9A11}
AppName=Tapsquatch
AppVersion={#AppVersion}
AppPublisher=Made by Silverback
AppPublisherURL=https://madebysilverback.com
; Installs for the current user only: no admin prompt, and profiles stay editable.
DefaultDirName={localappdata}\Programs\Tapsquatch
DefaultGroupName=Tapsquatch
DisableProgramGroupPage=yes
; Tapsquatch was called ControlBridge. Same AppId, so it replaces the old install,
; but in its own new folder (settings are moved across in [Code] below).
UsePreviousAppDir=no
UsePreviousGroup=no
PrivilegesRequired=lowest
OutputDir=..\dist-installer
OutputBaseFilename=Tapsquatch-Setup
SetupIconFile=..\icon.ico
UninstallDisplayIcon={app}\Tapsquatch.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=Tapsquatch

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\Tapsquatch.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\Tapsquatch Prompts.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\Tapsquatch Profile Maker.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\assets\controller.png"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\assets\logo-header.png"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\assets\controller-small.png"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\fonts\*.ttf"; DestDir: "{app}\fonts"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\controller_layout.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\profiles\*.json"; DestDir: "{app}\profiles"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\profiles\library\*.json"; DestDir: "{app}\profiles\library"; Flags: ignoreversion
Source: "..\README.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD-PARTY-NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Tapsquatch"; Filename: "{app}\Tapsquatch.exe"
Name: "{group}\Tapsquatch - Button Prompts"; Filename: "{app}\Tapsquatch Prompts.exe"
Name: "{group}\Tapsquatch - Profile Maker"; Filename: "{app}\Tapsquatch Profile Maker.exe"
Name: "{group}\Tapsquatch - Game Profiles"; Filename: "{app}\profiles"
Name: "{group}\Read me"; Filename: "{app}\README.txt"
Name: "{group}\Credits and licences"; Filename: "{app}\THIRD-PARTY-NOTICES.txt"
Name: "{userdesktop}\Tapsquatch"; Filename: "{app}\Tapsquatch.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Tapsquatch.exe"; Description: "Start Tapsquatch now"; Flags: postinstall nowait skipifsilent

[UninstallRun]
; Put the games' original keyboard prompts back before removing the app.
Filename: "{app}\Tapsquatch Prompts.exe"; Parameters: "--restore-all"; RunOnceId: "RestorePrompts"; Flags: waituntilterminated

[UninstallDelete]
Type: filesandordirs; Name: "{app}\backups"
Type: filesandordirs; Name: "{app}\profile_maker"

[Code]
{ Tapsquatch used to be called ControlBridge. Before installing, move the
  player's own settings, profiles and prompt backups from the old folder to
  the new one, then remove the old program files and shortcuts. }
procedure MoveIfThere(const OldPath, NewPath: String);
begin
  if (FileExists(OldPath) or DirExists(OldPath)) and
     not (FileExists(NewPath) or DirExists(NewPath)) then
    RenameFile(OldPath, NewPath);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  OldDir, NewDir: String;
begin
  if CurStep = ssInstall then
  begin
    OldDir := ExpandConstant('{localappdata}\Programs\ControlBridge');
    NewDir := ExpandConstant('{app}');
    if DirExists(OldDir) and (CompareText(OldDir, NewDir) <> 0) then
    begin
      ForceDirectories(NewDir);
      MoveIfThere(OldDir + '\profiles', NewDir + '\profiles');
      MoveIfThere(OldDir + '\backups', NewDir + '\backups');
      MoveIfThere(OldDir + '\controller_layout.json', NewDir + '\controller_layout.json');
      DelTree(OldDir, True, True, True);
    end;
    DelTree(ExpandConstant('{userprograms}\ControlBridge'), True, True, True);
    DeleteFile(ExpandConstant('{userdesktop}\ControlBridge.lnk'));
  end;
end;
