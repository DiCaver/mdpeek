#ifndef AppVersion
  #error AppVersion must be supplied from mdpeek/version.py with /DAppVersion=x.y.z
#endif
#ifndef OutputBaseFilename
  #error OutputBaseFilename must be supplied by the build script
#endif

#define AppName "MDPeek"
#define AppPublisher "MDPeek contributors"
#define AppProgID "MDPeek.Markdown"

[Setup]
AppId={{D9A47D7C-2626-44DC-91AB-A13CE92E636A}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=MDPeek Markdown Viewer installer
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\MDPeek
DefaultGroupName=MDPeek
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\mdpeek.ico
UninstallDisplayIcon={app}\MDPeek.exe
OutputDir=output
OutputBaseFilename={#OutputBaseFilename}
CloseApplications=yes
ChangesAssociations=yes

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "fileassoc"; Description: "Register MDPeek for .md and .markdown files"; GroupDescription: "File integration:"; Flags: checkedonce

[Files]
Source: "..\dist\MDPeek\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\MDPeek"; Filename: "{app}\MDPeek.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\MDPeek"; Filename: "{app}\MDPeek.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\{#AppProgID}"; ValueType: string; ValueData: "Markdown document"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\{#AppProgID}\DefaultIcon"; ValueType: string; ValueData: "{app}\MDPeek.exe,0"; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\{#AppProgID}\shell\open\command"; ValueType: string; ValueData: """{app}\MDPeek.exe"" ""%1"""; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\.md\OpenWithProgids"; ValueType: none; ValueName: "{#AppProgID}"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\.markdown\OpenWithProgids"; ValueType: none; ValueName: "{#AppProgID}"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\Applications\MDPeek.exe"; ValueType: string; ValueData: "MDPeek Markdown Viewer"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\Applications\MDPeek.exe\DefaultIcon"; ValueType: string; ValueData: "{app}\MDPeek.exe,0"; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\Applications\MDPeek.exe\shell\open\command"; ValueType: string; ValueData: """{app}\MDPeek.exe"" ""%1"""; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\Applications\MDPeek.exe\SupportedTypes"; ValueType: string; ValueName: ".md"; ValueData: ""; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\Applications\MDPeek.exe\SupportedTypes"; ValueType: string; ValueName: ".markdown"; ValueData: ""; Tasks: fileassoc

[Run]
Filename: "{app}\MDPeek.exe"; Description: "Launch MDPeek"; Flags: nowait postinstall skipifsilent unchecked

[Code]
function ClassesRoot(): Integer;
begin
  if IsAdminInstallMode then Result := HKLM else Result := HKCU;
end;

procedure AssociateIfUnowned(const Extension: String);
var
  Existing, UserChoice: String;
begin
  { HKCR observes the merged per-user and machine registration. UserChoice is
    protected by Windows; its presence always means the user has a default. }
  if RegQueryStringValue(HKCU,
       'Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\' + Extension + '\UserChoice',
       'ProgId', UserChoice) and (Trim(UserChoice) <> '') then
    exit;
  if ((not RegQueryStringValue(HKCR, Extension, '', Existing)) or
      (Trim(Existing) = '')) then
    RegWriteStringValue(ClassesRoot(), 'Software\Classes\' + Extension, '', '{#AppProgID}');
end;

procedure RemoveAssociationIfStillOurs(const Extension: String);
var
  Existing: String;
begin
  if RegQueryStringValue(ClassesRoot(), 'Software\Classes\' + Extension, '', Existing) and
     (CompareText(Existing, '{#AppProgID}') = 0) then
    RegDeleteValue(ClassesRoot(), 'Software\Classes\' + Extension, '');
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and WizardIsTaskSelected('fileassoc') then begin
    AssociateIfUnowned('.md');
    AssociateIfUnowned('.markdown');
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then begin
    RemoveAssociationIfStillOurs('.md');
    RemoveAssociationIfStillOurs('.markdown');
  end;
end;
