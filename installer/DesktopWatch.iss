; DeskTrace (桌迹, formerly Desktop Watch) installer (Inno Setup 6). Build with installer\build_installer.py, which stages the
; files and passes /DAppVersion from server.py. Never change the AppIds: they let a newer installer
; find the version installed before, even under its old name "Desktop Watch".
;
; Upgrades: every version uses the same AppId, so a newer installer finds the existing install,
; closes the running app cleanly, replaces only the program files in {app}, and leaves the history in
; %LOCALAPPDATA%\DeskTrace untouched (the app moves an older %LOCALAPPDATA%\Desktop Watch there itself). The app upgrades that data itself on first start
; (server.py: migrate()).

; A test build (/DTestBuild) installs side by side under another name, keeps its data inside its own
; folder (portable.txt) and never touches the real app's shortcuts or registry entries.
#ifdef TestBuild
  #define AppName "DeskTrace Test"
  #define TheAppId "{{3C1D9E52-7A44-4B8F-A0D6-55E2B1F0C9A3}"
  #define OutName "DeskTrace-TEST-Setup"
#else
  #define AppName "DeskTrace"
  #define TheAppId "{{8F3A6C2E-5B1D-4E7A-9C44-2D6B1E0F7A19}"
  #define OutName "DeskTrace-Setup"
#endif
#ifndef AppVersion
  #define AppVersion "0.0"
#endif
#define Pyw "{app}\runtime\pythonw.exe"
#define Server "{app}\app\server.py"
#define UninstKey "Software\Microsoft\Windows\CurrentVersion\Uninstall\" + Copy(TheAppId, 2, 38) + "_is1"

[Setup]
AppId={#TheAppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=DeskTrace
VersionInfoVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\{#AppName}
; Always let the user pick the install location (also on upgrades, prefilled with the current one).
DisableDirPage=no
DisableWelcomePage=no
DisableReadyPage=no
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename={#OutName}-{#AppVersion}
SetupIconFile=..\desktop_watch\static\icon.ico
UninstallDisplayIcon={app}\app\static\icon.ico
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
WizardImageFile=wizard-large-1x.bmp,wizard-large-2x.bmp
WizardSmallImageFile=wizard-small-1x.bmp,wizard-small-2x.bmp
; Always offer English / 简体中文 first (preselected from the Windows display language).
ShowLanguageDialog=yes
CloseApplications=no

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "zh"; MessagesFile: "compiler:Default.isl,ChineseSimplified.isl"

[CustomMessages]
en.DesktopIcon=Create a desktop shortcut
zh.DesktopIcon=创建桌面快捷方式
en.StartWithWindows=Start with Windows (runs quietly in the background)
zh.StartWithWindows=开机自动启动（在后台静默运行）
en.LaunchNow=Open DeskTrace now
zh.LaunchNow=立即打开桌迹
en.DeleteData=Also delete the recorded change history and file snapshots?%n%nChoose No to keep them — reinstalling later picks them up again.
zh.DeleteData=是否同时删除已记录的变更历史和文件快照？%n%n选择“否”将保留它们，以后重新安装时会自动继续使用。

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"
Name: "autostart"; Description: "{cm:StartWithWindows}"

[InstallDelete]
; Replace the program cleanly on upgrade (files a new version no longer has must not linger).
; The history is not in {app}, so nothing of it is touched here.
Type: filesandordirs; Name: "{app}\app"
Type: filesandordirs; Name: "{app}\runtime"
; Shortcuts from any earlier copy, so only the installed version starts.
Type: files; Name: "{userstartup}\{#AppName}.lnk"
Type: files; Name: "{autodesktop}\{#AppName}.lnk"
#ifndef TestBuild
; ... and those of the versions before the rename to DeskTrace
Type: files; Name: "{userstartup}\Desktop Watch.lnk"
Type: files; Name: "{autodesktop}\Desktop Watch.lnk"
Type: files; Name: "{autoprograms}\Desktop Watch.lnk"
#endif

[Files]
Source: "..\build\stage\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#ifdef TestBuild
Source: "..\build\portable.txt"; DestDir: "{app}\app"; Flags: ignoreversion
#endif

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{#Pyw}"; Parameters: """{#Server}"""; WorkingDir: "{app}\app"; IconFilename: "{app}\app\static\icon.ico"
Name: "{autodesktop}\{#AppName}"; Filename: "{#Pyw}"; Parameters: """{#Server}"""; WorkingDir: "{app}\app"; IconFilename: "{app}\app\static\icon.ico"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{#Pyw}"; Parameters: """{#Server}"" --no-browser"; WorkingDir: "{app}\app"; IconFilename: "{app}\app\static\icon.ico"; Tasks: autostart

[Run]
Filename: "{#Pyw}"; Parameters: """{#Server}"""; WorkingDir: "{app}\app"; Description: "{cm:LaunchNow}"; Flags: postinstall nowait skipifsilent
Filename: "{#Pyw}"; Parameters: """{#Server}"" --no-browser"; WorkingDir: "{app}\app"; Flags: nowait runhidden; Check: WizardSilent and WizardIsTaskSelected('autostart')

[UninstallRun]
Filename: "{#Pyw}"; Parameters: """{#Server}"" --quit"; WorkingDir: "{app}\app"; Flags: runhidden waituntilterminated; RunOnceId: "QuitDesktopWatch"

[UninstallDelete]
Type: files; Name: "{userstartup}\{#AppName}.lnk"
Type: filesandordirs; Name: "{app}"

[Code]
var
  OldDir: String;  { where an earlier version is installed ('' if none) }

function InitializeSetup(): Boolean;
begin
  if not RegQueryStringValue(HKCU, '{#UninstKey}', 'Inno Setup: App Path', OldDir) then
    OldDir := '';
  Result := True;
end;

{ Close the running version cleanly before its files are replaced — wherever it was installed. }
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Code: Integer;
  Dir: String;
begin
  Dir := OldDir;
  if Dir = '' then
    Dir := ExpandConstant('{app}');
  if FileExists(Dir + '\runtime\pythonw.exe') and FileExists(Dir + '\app\server.py') then
    Exec(Dir + '\runtime\pythonw.exe', '"' + Dir + '\app\server.py" --quit', Dir + '\app',
         SW_HIDE, ewWaitUntilTerminated, Code);
  Result := '';
end;

{ If the user picked a new location for an upgrade, remove the old program files (never the history). }
procedure CurStepChanged(CurStep: TSetupStep);
begin
  { The app starts in the language chosen here (only on its very first start; later it keeps its own setting). }
  if CurStep = ssPostInstall then
    SaveStringToFile(ExpandConstant('{app}\app\install-lang.txt'), ActiveLanguage, False);
  if (CurStep = ssPostInstall) and (OldDir <> '') and
     (CompareText(RemoveBackslashUnlessRoot(OldDir), RemoveBackslashUnlessRoot(ExpandConstant('{app}'))) <> 0) then
  begin
    DelTree(OldDir + '\app', True, True, True);
    DelTree(OldDir + '\runtime', True, True, True);
    DeleteFile(OldDir + '\unins000.exe');
    DeleteFile(OldDir + '\unins000.dat');
    RemoveDir(OldDir);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
#ifndef TestBuild
    { The Explorer right-click entry the app may have added (Settings). }
    RegDeleteKeyIncludingSubkeys(HKCU, 'Software\Classes\*\shell\DesktopWatch');  { internal key name, kept }
    DataDir := ExpandConstant('{localappdata}\DeskTrace');
    if (DirExists(DataDir) or DirExists(ExpandConstant('{localappdata}\Desktop Watch'))) and not UninstallSilent then
      if MsgBox(CustomMessage('DeleteData'), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      begin
        DelTree(DataDir, True, True, True);
        DelTree(ExpandConstant('{localappdata}\Desktop Watch'), True, True, True);
      end;
#endif
  end;
end;
