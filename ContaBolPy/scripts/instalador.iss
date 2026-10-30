; Inno Setup 6 - instalador de ContaBol (Python/PySide6). Compilar:  iscc scripts\instalador.iss
#define Version "2.0.0"

[Setup]
AppId={{B8E5A0C1-4D2F-4A7B-9E36-7C1F2A5D8B40}
AppName=ContaBol
AppVersion={#Version}
AppPublisher=ContaBol
DefaultDirName={autopf}\ContaBol
DefaultGroupName=ContaBol
OutputDir=..\dist
OutputBaseFilename=ContaBol_Setup_{#Version}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\ContaBol.exe
SetupIconFile=contabol.ico
ShowLanguageDialog=no

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "..\dist\ContaBol\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\ContaBol"; Filename: "{app}\ContaBol.exe"
Name: "{group}\Desinstalar ContaBol"; Filename: "{uninstallexe}"
Name: "{autodesktop}\ContaBol"; Filename: "{app}\ContaBol.exe"; Tasks: escritorio

[Run]
Filename: "{app}\ContaBol.exe"; Description: "Ejecutar ContaBol"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; los datos del usuario (%LOCALAPPDATA%\ContaBol) NO se eliminan al desinstalar
Type: filesandordirs; Name: "{app}"
