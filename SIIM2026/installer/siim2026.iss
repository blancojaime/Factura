; Inno Setup 6 – instalador de SIIM 2026 para Windows 10/11 (x64)
#define AppName "SIIM 2026"
#define AppVersion "1.0.1"
[Setup]
AppId={{6F1B7C52-3E0A-4C57-9D4B-51A4F0C2E126}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Proveedor SIIM
DefaultDirName={autopf}\SIIM2026
DefaultGroupName=SIIM 2026
OutputDir=..\dist
OutputBaseFilename=SIIM2026_Setup_{#AppVersion}
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
WizardStyle=modern
DisableWelcomePage=yes
DisableDirPage=yes
DisableReadyPage=yes
ShowLanguageDialog=no
LanguageDetectionMethod=none
CloseApplications=yes
UsePreviousTasks=yes
SetupIconFile=..\siim\resources\icon.ico
UninstallDisplayIcon={app}\SIIM2026.exe
DisableProgramGroupPage=yes
[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
[Tasks]
Name: "desktopicon"; Description: "Crear un icono en el escritorio"; GroupDescription: "Accesos directos:"
[Files]
Source: "..\dist\SIIM2026\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Dirs]
; Datos fuera de la carpeta del programa; todos los usuarios de Windows pueden operar el sistema
Name: "{commonappdata}\SIIM2026"; Permissions: users-modify
[Icons]
Name: "{group}\SIIM 2026"; Filename: "{app}\SIIM2026.exe"
Name: "{autodesktop}\SIIM 2026"; Filename: "{app}\SIIM2026.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\SIIM2026.exe"; Description: "Iniciar SIIM 2026"; Flags: nowait postinstall skipifsilent
[UninstallDelete]
; NO se borran los datos ni los respaldos de {commonappdata}\SIIM2026 al desinstalar (protección de la información)
Type: filesandordirs; Name: "{app}"
