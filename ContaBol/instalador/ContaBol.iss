; Script de Inno Setup 6 para ContaBol. Genera ContaBol_Setup_<arq>.exe
; Compilar:  iscc /DArq=x64 /DOrigen=..\publicar\win-x64 ContaBol.iss
#ifndef Arq
  #define Arq "x64"
#endif
#ifndef Origen
  #define Origen "..\publicar\win-x64"
#endif
#define Version "1.0.0"

[Setup]
AppId={{6F3C1A52-8B7D-4E2A-9C41-3D5B7A1E0F24}
AppName=ContaBol
AppVersion={#Version}
AppPublisher=ContaBol
DefaultDirName={autopf}\ContaBol
DefaultGroupName=ContaBol
OutputDir=salida
OutputBaseFilename=ContaBol_Setup_{#Arq}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayIcon={app}\ContaBol.exe
#if Arq == "x64"
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
#endif
ShowLanguageDialog=no

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "{#Origen}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion; Excludes: "*.pdb"

[Icons]
Name: "{group}\ContaBol"; Filename: "{app}\ContaBol.exe"
Name: "{group}\Desinstalar ContaBol"; Filename: "{uninstallexe}"
Name: "{autodesktop}\ContaBol"; Filename: "{app}\ContaBol.exe"; Tasks: escritorio

[Run]
Filename: "{app}\ContaBol.exe"; Description: "Ejecutar ContaBol"; Flags: nowait postinstall skipifsilent

[Code]
function MotorAccessInstalado(): Boolean;
begin
  Result := RegKeyExists(HKCR, 'Microsoft.ACE.OLEDB.16.0') or RegKeyExists(HKCR, 'Microsoft.ACE.OLEDB.12.0');
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  if not MotorAccessInstalado() then
    if MsgBox('No se detectó Microsoft Access Database Engine (ACE OLEDB), necesario para las bases de datos de ContaBol.' + #13#10 +
              'Instálelo (gratuito, misma arquitectura x64/x86) desde microsoft.com/download/details.aspx?id=54920 antes de usar el programa.' + #13#10#13#10 +
              '¿Continuar con la instalación de todas formas?', mbConfirmation, MB_YESNO) = IDNO then
      Result := False;
end;
