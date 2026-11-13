; Inno Setup 6 - instalador de CONTA JB para WINDOWS 7 SP1 (32 bits): mismas funciones y apariencia que la edición Windows 10/11.
; Instala solo para el usuario actual (no pide permisos de administrador) y crea el acceso directo en el escritorio.
#define Version "2.4.0"

[Setup]
MinVersion=6.1sp1
AppId={{B8E5A0C1-4D2F-4A7B-9E36-7C1F2A5D8B40}
AppName=CONTA JB
AppVersion={#Version}
AppPublisher=Jaime Blanco
DefaultDirName={autopf}\ContaJB
DefaultGroupName=CONTA JB
OutputDir=..\dist
OutputBaseFilename=ContaJB_Setup_Win7_32bits
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
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
Name: "{autoprograms}\CONTA JB - Restablecer contraseña de administrador"; Filename: "{app}\ContaJB.exe"; Parameters: "--restablecer-admin"; IconFilename: "{app}\ContaJB.exe"

[Run]
Filename: "{app}\ContaJB.exe"; Description: "Abrir CONTA JB ahora"; Flags: nowait postinstall skipifsilent

; los datos del usuario (%LOCALAPPDATA%\ContaJB) NO se eliminan al desinstalar
