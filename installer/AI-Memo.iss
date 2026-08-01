; Inno Setup script for the end-user Windows installer.
#define MyAppName "智能日程提醒助手"
#define MyAppVersion "1.0"
#define MyAppPublisher "Have you forgotten?"
#define MyAppExeName "AI-Memo.exe"
#define MyAppId "{{B78A9E93-59F9-4B2E-8D9C-506A0F6F186C}"
#define MyAppUninstallKey "Software\Microsoft\Windows\CurrentVersion\Uninstall\{B78A9E93-59F9-4B2E-8D9C-506A0F6F186C}_is1"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\HaveYouForgotten
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableDirPage=no
UsePreviousAppDir=yes
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename=AI-Memo-Installer
SetupIconFile=..\resources\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
CloseApplicationsFilter={#MyAppExeName}
RestartApplications=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\AI-Memo\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\智能日程提醒助手"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
Type: filesandordirs; Name: "{localappdata}\HaveYouForgotten"

[Code]
var
  IsUpdateInstall: Boolean;

function PreviousInstallationExists: Boolean;
begin
  Result :=
    RegKeyExists(HKEY_CURRENT_USER, '{#MyAppUninstallKey}') or
    RegKeyExists(HKEY_LOCAL_MACHINE, '{#MyAppUninstallKey}');
end;

procedure InitializeWizard;
begin
  IsUpdateInstall := PreviousInstallationExists;
  if IsUpdateInstall then begin
    WizardForm.Caption := '{#MyAppName} 更新';
    WizardForm.WelcomeLabel1.Caption := '更新 {#MyAppName}';
    WizardForm.WelcomeLabel2.Caption :=
      '检测到这台电脑已经安装了 {#MyAppName}。' + #13#10 + #13#10 +
      '点击“更新”即可替换程序文件，现有日程、设置和提醒记录会保留。';
  end;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := IsUpdateInstall and
    (PageID in [wpSelectDir, wpSelectProgramGroup, wpSelectTasks, wpReady]);
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if IsUpdateInstall and (CurPageID = wpWelcome) then
    WizardForm.NextButton.Caption := '更新'
  else if CurPageID = wpFinished then
    WizardForm.NextButton.Caption := SetupMessage(msgButtonFinish)
  else
    WizardForm.NextButton.Caption := SetupMessage(msgButtonNext);
end;

procedure StopRunningApplication;
var
  ResultCode: Integer;
begin
  Exec(
    ExpandConstant('{sys}\taskkill.exe'),
    '/F /T /IM {#MyAppExeName}',
    '', SW_HIDE, ewWaitUntilTerminated, ResultCode
  );
  Sleep(800);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if IsUpdateInstall then
    StopRunningApplication;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then begin
    StopRunningApplication;
    RegDeleteValue(HKEY_CURRENT_USER, 'Software\Microsoft\Windows\CurrentVersion\Run', 'HaveYouForgotten');
  end;
end;

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "安装完成后启动智能日程提醒助手"; Flags: nowait postinstall skipifsilent
