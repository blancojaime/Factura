; Inno Setup 6 — genera Setup_ImportadorVSIAF_<version>.exe
#define MyAppName "Importador Excel a VSIAF"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#define MyAppExe "ImportadorVSIAF.exe"

[Setup]
AppId={{6C2A5F3E-9B64-4F0B-A1D8-7E0B8D6F1A21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Importador VSIAF
DefaultDirName={autopf}\ImportadorVSIAF
DefaultGroupName=Importador VSIAF
OutputDir=..\dist
OutputBaseFilename=Setup_ImportadorVSIAF_{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExe}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un icono en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "..\dist\ImportadorVSIAF\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\dist\docs\*"; DestDir: "{app}\documentos"; Flags: recursesubdirs ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\Importador Excel a VSIAF"; Filename: "{app}\{#MyAppExe}"
Name: "{group}\Guía de uso"; Filename: "{app}\documentos\GUIA_DE_USO.docx"; Check: FileExists(ExpandConstant('{app}\documentos\GUIA_DE_USO.docx'))
Name: "{group}\Plantilla Excel (vacía)"; Filename: "{app}\documentos\plantilla_importacion_vsiaf.xlsx"
Name: "{autodesktop}\Importador Excel a VSIAF"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "Abrir el importador"; Flags: nowait postinstall skipifsilent
