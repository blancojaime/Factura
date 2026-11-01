; Inno Setup 6 - instalador sencillo de CONTA JB: sin preguntas, un solo clic en "Instalar".
; Instala solo para el usuario actual (no pide permisos de administrador) y crea el acceso directo en el escritorio.
#define Version "2.1.0"

[Setup]
AppId={{B8E5A0C1-4D2F-4A7B-9E36-7C1F2A5D8B40}
AppName=CONTA JB
AppVersion={#Version}
AppPublisher=Jaime Blanco
DefaultDirName={autopf}\ContaJB
DefaultGroupName=CONTA JB
OutputDir=..\dist
OutputBaseFilename=ContaJB_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\ContaJB.exe
SetupIconFile=contabol.ico
ShowLanguageDialog=no
DisableWelcomePage=yes
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=yes
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "..\dist\ContaJB\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autodesktop}\CONTA JB"; Filename: "{app}\ContaJB.exe"; IconFilename: "{app}\ContaJB.exe"
Name: "{autoprograms}\CONTA JB"; Filename: "{app}\ContaJB.exe"

[Run]
Filename: "{app}\ContaJB.exe"; Description: "Abrir CONTA JB ahora"; Flags: nowait postinstall skipifsilent

; los datos del usuario (%LOCALAPPDATA%\ContaJB) NO se eliminan al desinstalar
