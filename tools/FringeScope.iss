#ifndef AppVersion
 #define AppVersion "0.11.0"
#endif
#ifndef BundleDir
 #define BundleDir "..\dist\FringeScope"
#endif
#ifndef ReleaseOutput
 #define ReleaseOutput "..\installer"
#endif
[Setup]
AppId={{E2584836-92DC-4E44-BCA4-40F9B58478C0}
AppName=FringeScope
AppVersion={#AppVersion}
AppPublisher=Michael Raymond Nelson
DefaultDirName={localappdata}\Programs\FringeScope
PrivilegesRequired=lowest
UsePreviousAppDir=yes
DisableProgramGroupPage=yes
DisableDirPage=auto
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#ReleaseOutput}
OutputBaseFilename=FringeScope-setup
SetupIconFile=..\desktop\assets\fringescope.ico
UninstallDisplayIcon={app}\FringeScope.exe
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
WizardStyle=modern
[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"
[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"; Check: KnownInstall
[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\tools\fringescope-install.json"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{autoprograms}\FringeScope"; Filename: "{app}\FringeScope.exe"; AppUserModelID: "Fisicas.FringeScope"
Name: "{autodesktop}\FringeScope"; Filename: "{app}\FringeScope.exe"; Tasks: desktopicon; AppUserModelID: "Fisicas.FringeScope"
[Run]
Filename: "{app}\FringeScope.exe"; Description: "Start FringeScope"; Flags: nowait postinstall skipifsilent
Filename: "{app}\FringeScope.exe"; Flags: nowait; Check: RelaunchRequested
[Code]
function KnownInstall: Boolean;
var Marker: AnsiString;
begin
 Result := False;
 if FileExists(ExpandConstant('{app}\FringeScope.exe')) and LoadStringFromFile(ExpandConstant('{app}\fringescope-install.json'), Marker) then
  Result := Pos('E2584836-92DC-4E44-BCA4-40F9B58478C0', String(Marker)) > 0;
end;
function RelaunchRequested: Boolean;
begin
 Result := ExpandConstant('{param:relaunch|0}') = '1';
end;
