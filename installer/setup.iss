[Setup]
AppName=PDF変換・結合ツール
AppVersion=1.13.2
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
{ Shell にアイコン変更を通知するための API 宣言 }
procedure SHChangeNotify(wEventId: Integer; uFlags: Cardinal; dwItem1: Integer; dwItem2: Integer);
  external 'SHChangeNotify@shell32.dll stdcall';

const
  SHCNE_ASSOCCHANGED = $08000000;
  SHCNF_IDLIST       = $0000;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssDone then
  begin
    { Windows 10/11 対応: アイコンキャッシュをクリアして再構築 }
    Exec(ExpandConstant('{sys}\ie4uinit.exe'), '-ClearIconCache', '', SW_HIDE,
         ewWaitUntilTerminated, ResultCode);
    Exec(ExpandConstant('{sys}\ie4uinit.exe'), '-show', '', SW_HIDE,
         ewWaitUntilTerminated, ResultCode);
    { Shell にアイコン変更を通知（エクスプローラーが即時反映） }
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, 0, 0);
  end;
end;
