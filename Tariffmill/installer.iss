; Inno Setup Script for TariffMill
; Build with: iscc installer.iss

#define MyAppName "TariffMill"
#define MyAppVersion "0.96.20"
#define MyAppPublisher "Process Logic Labs, LLC"
#define MyAppExeName "TariffMill.exe"

[Setup]
; Application info
AppId={{8F3B9A2E-5C7D-4E1F-B8A6-9D2C3E4F5A6B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=TariffMill_Setup_{#MyAppVersion}
SetupIconFile=Resources\icon.ico
; Use faster compression for quicker installer startup
; lzma2/max gives best compression but slow startup
; lzma/fast gives good compression with faster startup
Compression=lzma/fast
SolidCompression=no
WizardStyle=modern

; Privileges - no admin needed
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Uninstall info
UninstallDisplayIcon={app}\Resources\icon.ico
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main executable
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Resources directory (includes databases, icons, etc.)
Source: "Resources\*"; DestDir: "{app}\Resources"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "vc_redist.x64.exe"
; Templates directory (invoice templates)
Source: "templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Always recreate shortcuts to update icons
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\Resources\icon.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\Resources\icon.ico"; Tasks: desktopicon

[Run]
; Launch app after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[InstallDelete]
; Delete old shortcuts to force recreation with new icons
Type: files; Name: "{group}\{#MyAppName}.lnk"
Type: files; Name: "{autodesktop}\{#MyAppName}.lnk"

[Code]
var
  RemoveDatabase: Boolean;
  RemoveTemplates: Boolean;

function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
  TempDir: String;
  FindRec: TFindRec;
begin
  Result := True;

  // Kill any running TariffMill processes before installing
  Exec('taskkill.exe', '/F /IM TariffMill.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  // Small delay to ensure process is fully terminated
  Sleep(500);

  // Clean up old PyInstaller temp folders (_MEI*)
  TempDir := ExpandConstant('{tmp}\..');
  if FindFirst(TempDir + '\_MEI*', FindRec) then
  begin
    try
      repeat
        if (FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
        begin
          DelTree(TempDir + '\' + FindRec.Name, True, True, True);
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
end;

function InitializeUninstall(): Boolean;
var
  Choice: Integer;
begin
  Result := True;
  RemoveDatabase := False;
  RemoveTemplates := False;

  // Ask about database
  Choice := MsgBox(
    'Do you want to KEEP your database (tariffmill.db)?' + #13#10 + #13#10 +
    'This contains your parts, MIDs, profiles, and settings.' + #13#10 + #13#10 +
    'Click YES to keep it, NO to delete it, or CANCEL to abort uninstall.',
    mbConfirmation, MB_YESNOCANCEL);

  if Choice = IDCANCEL then
  begin
    Result := False;
    Exit;
  end;

  RemoveDatabase := (Choice = IDNO);

  // Ask about templates
  Choice := MsgBox(
    'Do you want to KEEP your OCRmill templates?' + #13#10 + #13#10 +
    'These are your custom invoice parsing templates.' + #13#10 + #13#10 +
    'Click YES to keep them, NO to delete them, or CANCEL to abort uninstall.',
    mbConfirmation, MB_YESNOCANCEL);

  if Choice = IDCANCEL then
  begin
    Result := False;
    Exit;
  end;

  RemoveTemplates := (Choice = IDNO);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDir: String;
  TemplatesDir: String;
  DatabasePath: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    AppDir := ExpandConstant('{app}');
    DatabasePath := AppDir + '\Resources\tariffmill.db';
    TemplatesDir := AppDir + '\templates';

    // Handle database removal based on user choice
    if RemoveDatabase then
    begin
      if FileExists(DatabasePath) then
        DeleteFile(DatabasePath);
    end;

    // Handle templates removal based on user choice
    if RemoveTemplates then
    begin
      if DirExists(TemplatesDir) then
        DelTree(TemplatesDir, True, True, True);
    end;

    // Clean up empty directories if both were removed
    if RemoveDatabase and RemoveTemplates then
    begin
      // Try to remove Resources dir if empty
      RemoveDir(AppDir + '\Resources');
      // Try to remove app dir if empty
      RemoveDir(AppDir);
    end;
  end;
end;
