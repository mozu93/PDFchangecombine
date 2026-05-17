[Setup]
AppName=PDF変換・結合ツール
AppVersion=1.12.0
AppPublisher=mozu93
AppPublisherURL=https://github.com/mozu93/PDFchangecombine
AppSupportURL=https://github.com/mozu93/PDFchangecombine/issues
AppUpdatesURL=https://github.com/mozu93/PDFchangecombine/releases
DefaultDirName={localappdata}\PDFConverter
DefaultGroupName=PDF変換・結合ツール
AllowNoIcons=yes
OutputDir=..\dist\installer
OutputBaseFilename=PDFConverter-setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\PDFConverter.exe
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\PDFConverter\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\PDF変換・結合ツール"; Filename: "{app}\PDFConverter.exe"; IconFilename: "{app}\PDFConverter.exe"; IconIndex: 0
Name: "{group}\{cm:UninstallProgram,PDF変換・結合ツール}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\PDF変換・結合ツール"; Filename: "{app}\PDFConverter.exe"; IconFilename: "{app}\PDFConverter.exe"; IconIndex: 0; Tasks: desktopicon

[Run]
Filename: "{app}\PDFConverter.exe"; Description: "{cm:LaunchProgram,PDF変換・結合ツール}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssDone then
  begin
    { インストール完了後にWindowsのアイコンキャッシュを強制更新 }
    Exec(ExpandConstant('{sys}\ie4uinit.exe'), '-show', '', SW_HIDE,
         ewWaitUntilTerminated, ResultCode);
  end;
end;
