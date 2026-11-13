; Instalador de SICOM-MUNI para Windows (servidor de red local)
; Compilar:  ISCC /DVersion=2.1.3 sicom-muni.iss      (el contenido de _stage lo prepara construir.ps1)
#ifndef Version
  #define Version "2.1.3"
#endif
#define Nombre "SICOM-MUNI"

[Setup]
AppId={{7B1F2C9E-5A3D-4E8B-9C41-2D6E0A5F7B13}
AppName={#Nombre}
AppVersion={#Version}
AppVerName={#Nombre} {#Version}
AppPublisher=SICOM-MUNI
DefaultDirName={autopf}\SICOM-MUNI
DefaultGroupName=SICOM-MUNI
DisableProgramGroupPage=yes
OutputDir=_salida
OutputBaseFilename=SICOM-MUNI-Instalador-{#Version}
Compression=lzma2/max
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
WizardStyle=modern
UninstallDisplayName={#Nombre} (servidor de red local)
SetupLogging=yes
CloseApplications=no
RestartApplications=no
AllowNoIcons=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "_stage\python\*"; DestDir: "{app}\python"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "_stage\site-packages\*"; DestDir: "{app}\site-packages"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "_stage\backend\*"; DestDir: "{app}\backend"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "_stage\web\*"; DestDir: "{app}\web"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "_stage\pgsql\*"; DestDir: "{app}\pgsql"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "_stage\gtk\*"; DestDir: "{app}\gtk"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "_stage\fonts\*"; DestDir: "{app}\fonts"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "_stage\herramientas\*"; DestDir: "{app}\herramientas"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "_stage\prerequisitos\*"; DestDir: "{app}\prerequisitos"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "_stage\docs\*"; DestDir: "{app}\docs"; Flags: recursesubdirs createallsubdirs ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\Abrir SICOM-MUNI"; Filename: "{app}\SICOM-MUNI.url"
Name: "{group}\Activar la licencia"; Filename: "{app}\SICOM-MUNI-Activacion.url"
Name: "{group}\Estado del sistema"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\herramientas\estado.ps1"""
Name: "{group}\Respaldar ahora"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\herramientas\respaldar.ps1"""
Name: "{group}\Restaurar un respaldo"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\herramientas\restaurar.ps1"""
Name: "{group}\Cambiar la dirección o el puerto de red"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\herramientas\configurar-red.ps1"""
Name: "{group}\Restablecer la contraseña de un usuario"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\herramientas\restablecer-clave.ps1"""
Name: "{group}\Reiniciar el servicio"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\herramientas\servicios.ps1"" -Accion reiniciar"
Name: "{group}\Manual de instalación y uso"; Filename: "{app}\docs"
Name: "{group}\Desinstalar SICOM-MUNI"; Filename: "{uninstallexe}"
Name: "{autodesktop}\SICOM-MUNI"; Filename: "{app}\SICOM-MUNI.url"

[Code]
var
  PaginaEntidad, PaginaAdmin, PaginaRed: TInputQueryWizardPage;
  PaginaDemo: TInputOptionWizardPage;
  PaginaArchivoLic: TInputFileWizardPage;
  ArchivoRespuestas: String;

function Param(const Nombre, Defecto: String): String;
begin
  Result := ExpandConstant('{param:' + Nombre + '|' + Defecto + '}');
end;

function EscaparJson(const S: String): String;
begin
  Result := S;
  StringChangeEx(Result, '\', '\\', True);
  StringChangeEx(Result, '"', '\"', True);
end;

function ClaveValida(const C: String): Boolean;
var
  I: Integer;
  May, Min, Dig: Boolean;
begin
  May := False; Min := False; Dig := False;
  for I := 1 to Length(C) do
  begin
    if (C[I] >= 'A') and (C[I] <= 'Z') then May := True;
    if (C[I] >= 'a') and (C[I] <= 'z') then Min := True;
    if (C[I] >= '0') and (C[I] <= '9') then Dig := True;
  end;
  Result := (Length(C) >= 10) and May and Min and Dig;
end;

procedure InitializeWizard;
begin
  PaginaEntidad := CreateInputQueryPage(wpSelectDir, 'Datos de la entidad',
    'Estos datos aparecerán en el membrete de los documentos.', 'Escriba el nombre de su Gobierno Autónomo Municipal y la ciudad.');
  PaginaEntidad.Add('Nombre de la entidad (por ejemplo: GOBIERNO AUTÓNOMO MUNICIPAL DE ...):', False);
  PaginaEntidad.Add('Ciudad:', False);
  PaginaEntidad.Values[0] := Param('ENTIDAD', '');
  PaginaEntidad.Values[1] := Param('CIUDAD', '');

  PaginaAdmin := CreateInputQueryPage(PaginaEntidad.ID, 'Administrador del sistema',
    'Se creará la cuenta con la que se administran usuarios y parámetros.',
    'La contraseña debe tener al menos 10 caracteres, con mayúsculas, minúsculas y números. Anótela en un lugar seguro.');
  PaginaAdmin.Add('Nombre de usuario del administrador:', False);
  PaginaAdmin.Add('Contraseña:', True);
  PaginaAdmin.Add('Repita la contraseña:', True);
  PaginaAdmin.Values[0] := Param('ADMIN', 'admin');
  PaginaAdmin.Values[1] := Param('CLAVE', '');
  PaginaAdmin.Values[2] := Param('CLAVE', '');

  PaginaRed := CreateInputQueryPage(PaginaAdmin.ID, 'Red local',
    'Puerto con el que los demás equipos entrarán al sistema.',
    'Normalmente no necesita cambiarlo. Los usuarios entrarán desde su navegador a http://IP-DE-ESTE-EQUIPO:PUERTO');
  PaginaRed.Add('Puerto de red (recomendado 8080):', False);
  PaginaRed.Values[0] := Param('PUERTO', '8080');

  PaginaDemo := CreateInputOptionPage(PaginaRed.ID, 'Datos de demostración',
    'Puede instalar usuarios y datos de ejemplo para probar el sistema.',
    'Para trabajar con datos reales NO marque la casilla (podrá crear sus usuarios desde el sistema).', False, False);
  PaginaDemo.Add('Cargar usuarios y datos de demostración (solo para pruebas y capacitación)');
  PaginaDemo.Values[0] := (Param('DEMO', 'NO') = 'SI');

  PaginaArchivoLic := CreateInputFilePage(PaginaDemo.ID, 'Licencia (opcional)',
    'Si ya tiene el archivo de licencia (.sicomlic), selecciónelo.',
    'Si no lo tiene, el sistema funcionará 30 días en modo de prueba y podrá activar la licencia después desde el navegador.');
  PaginaArchivoLic.Add('Archivo de licencia:', 'Licencia SICOM-MUNI|*.sicomlic|Todos los archivos|*.*', '.sicomlic');
  PaginaArchivoLic.Values[0] := Param('LICENCIA', '');
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Puerto: Integer;
begin
  Result := True;
  if CurPageID = PaginaEntidad.ID then
  begin
    if Trim(PaginaEntidad.Values[0]) = '' then
    begin
      SuppressibleMsgBox('Escriba el nombre de la entidad.', mbError, MB_OK, IDOK);
      Result := False;
    end;
  end
  else if CurPageID = PaginaAdmin.ID then
  begin
    if Trim(PaginaAdmin.Values[0]) = '' then
    begin
      SuppressibleMsgBox('Escriba el nombre de usuario del administrador.', mbError, MB_OK, IDOK);
      Result := False;
    end
    else if not ClaveValida(PaginaAdmin.Values[1]) then
    begin
      SuppressibleMsgBox('La contraseña debe tener al menos 10 caracteres, con mayúsculas, minúsculas y números.', mbError, MB_OK, IDOK);
      Result := False;
    end
    else if PaginaAdmin.Values[1] <> PaginaAdmin.Values[2] then
    begin
      SuppressibleMsgBox('Las dos contraseñas no coinciden.', mbError, MB_OK, IDOK);
      Result := False;
    end;
  end
  else if CurPageID = PaginaRed.ID then
  begin
    Puerto := StrToIntDef(Trim(PaginaRed.Values[0]), 0);
    if (Puerto < 1024) or (Puerto > 65535) then
    begin
      SuppressibleMsgBox('El puerto debe ser un número entre 1024 y 65535 (recomendado: 8080).', mbError, MB_OK, IDOK);
      Result := False;
    end;
  end;
end;

function ValorEntidad: String; begin if WizardSilent then Result := Param('ENTIDAD', 'GAM de Prueba') else Result := Trim(PaginaEntidad.Values[0]); end;
function ValorCiudad: String; begin if WizardSilent then Result := Param('CIUDAD', '') else Result := Trim(PaginaEntidad.Values[1]); end;
function ValorAdmin: String; begin if WizardSilent then Result := Param('ADMIN', 'admin') else Result := Trim(PaginaAdmin.Values[0]); end;
function ValorClave: String; begin if WizardSilent then Result := Param('CLAVE', '') else Result := PaginaAdmin.Values[1]; end;
function ValorPuerto: String; begin if WizardSilent then Result := Param('PUERTO', '8080') else Result := Trim(PaginaRed.Values[0]); end;
function ValorDemo: String;
begin
  if WizardSilent then Result := Param('DEMO', 'NO')
  else if PaginaDemo.Values[0] then Result := 'SI'
  else Result := 'NO';
end;
function ValorLicencia: String; begin if WizardSilent then Result := Param('LICENCIA', '') else Result := PaginaArchivoLic.Values[0]; end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Codigo: Integer;
begin
  Result := '';
  { Actualización: se detienen los servicios para poder reemplazar los archivos }
  Exec(ExpandConstant('{sys}\net.exe'), 'stop SICOM-MUNI', '', SW_HIDE, ewWaitUntilTerminated, Codigo);
  Exec(ExpandConstant('{sys}\net.exe'), 'stop SICOM-MUNI-BD', '', SW_HIDE, ewWaitUntilTerminated, Codigo);
  { Procesos que quedaron abiertos (p. ej. postgres.exe de un intento anterior) bloquean los archivos: se cierran }
  Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
       '-NoProfile -ExecutionPolicy Bypass -Command "Get-Process | Where-Object { $_.Path -and $_.Path -like ''' + ExpandConstant('{app}') + '\*'' } | Stop-Process -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 3"',
       '', SW_HIDE, ewWaitUntilTerminated, Codigo);
end;

procedure EscribirAccesos(const Puerto: String);
begin
  SaveStringToFile(ExpandConstant('{app}\SICOM-MUNI.url'), '[InternetShortcut]' + #13#10 + 'URL=http://localhost:' + Puerto + '/' + #13#10, False);
  SaveStringToFile(ExpandConstant('{app}\SICOM-MUNI-Activacion.url'), '[InternetShortcut]' + #13#10 + 'URL=http://localhost:' + Puerto + '/activacion/' + #13#10, False);
end;

{ Motivo del fallo (texto sin tildes que deja postinstalacion.ps1), para mostrarlo en el aviso }
function UltimoErrorDelRegistro: String;
var
  Lineas: TArrayOfString;
begin
  Result := 'no se pudo leer el registro.';
  if LoadStringsFromFile(ExpandConstant('{commonappdata}\SICOM-MUNI\logs\ultimo-error.txt'), Lineas) then
    if GetArrayLength(Lineas) > 0 then Result := Lineas[0];
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Json: TArrayOfString;
  Codigo: Integer;
  Demo, Ps: String;
begin
  if CurStep = ssPostInstall then
  begin
    ArchivoRespuestas := ExpandConstant('{tmp}\sicom-respuestas.json');
    Demo := 'false';
    if (Uppercase(ValorDemo) = 'SI') or (Uppercase(ValorDemo) = 'SÍ') or (ValorDemo = '1') or (Uppercase(ValorDemo) = 'YES') then Demo := 'true';
    SetArrayLength(Json, 1);
    Json[0] := '{"entidad":"' + EscaparJson(ValorEntidad) + '","ciudad":"' + EscaparJson(ValorCiudad) +
               '","adminUsuario":"' + EscaparJson(ValorAdmin) + '","adminClave":"' + EscaparJson(ValorClave) +
               '","puerto":' + ValorPuerto + ',"demo":' + Demo + ',"licencia":"' + EscaparJson(ValorLicencia) + '"}';
    SaveStringsToUTF8File(ArchivoRespuestas, Json, False);
    EscribirAccesos(ValorPuerto);
    WizardForm.StatusLabel.Caption := 'Configurando la base de datos, los servicios y el firewall (puede tardar unos minutos)...';
    Ps := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
    if not Exec(Ps, '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\herramientas\postinstalacion.ps1') +
                '" -Respuestas "' + ArchivoRespuestas + '" -InstallDirParam "' + ExpandConstant('{app}') + '"',
                '', SW_HIDE, ewWaitUntilTerminated, Codigo) then
      Codigo := 1;
    if Codigo <> 0 then
    begin
      SuppressibleMsgBox('La configuración no terminó correctamente (código ' + IntToStr(Codigo) + ').' + #13#10 + #13#10 +
        'Motivo: ' + UltimoErrorDelRegistro + #13#10 + #13#10 +
        'El detalle completo está en C:\ProgramData\SICOM-MUNI\logs\instalacion.log. Envíelo a soporte si el problema continúa.', mbError, MB_OK, IDOK);
      { La automatización (CI) comprueba el servicio y deja constancia en el registro }
      SaveStringToFile(ExpandConstant('{app}\INSTALACION-INCOMPLETA.txt'), 'Revise C:\ProgramData\SICOM-MUNI\logs\instalacion.log', False);
    end;
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
var
  Lineas: TArrayOfString;
  Texto: String;
  I: Integer;
begin
  if CurPageID = wpFinished then
  begin
    if LoadStringsFromFile(ExpandConstant('{commonappdata}\SICOM-MUNI\config\resultado.txt'), Lineas) then
    begin
      Texto := 'SICOM-MUNI quedó instalado y funcionando.' + #13#10 + #13#10;
      for I := 0 to GetArrayLength(Lineas) - 1 do
        Texto := Texto + Lineas[I] + #13#10;
      Texto := Texto + #13#10 + 'Anote estas direcciones: los demás equipos de la red entrarán con su navegador a la primera.';
      WizardForm.FinishedLabel.Caption := Texto;
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Codigo: Integer;
  Eliminar: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    Eliminar := '';
    if not UninstallSilent then
    begin
      if MsgBox('¿Desea CONSERVAR la base de datos, los documentos y los respaldos?' + #13#10 + #13#10 +
                'Sí = se conservan (recomendado, podrá reinstalar y seguir trabajando).' + #13#10 +
                'No = se ELIMINAN todos los datos de forma definitiva.', mbConfirmation, MB_YESNO or MB_DEFBUTTON1) = IDNO then
        Eliminar := ' -EliminarDatos';
    end
    else if ExpandConstant('{param:ELIMINARDATOS|0}') = '1' then
      Eliminar := ' -EliminarDatos';
    Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
         '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\herramientas\desinstalar.ps1') + '" -InstallDirParam "' + ExpandConstant('{app}') + '"' + Eliminar,
         '', SW_HIDE, ewWaitUntilTerminated, Codigo);
  end;
end;
