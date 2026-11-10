; Instalador de JB-Personal (Windows 10+ x64). Se compila con build_installer.py (define VERSION, STAGE, OUT, ICON).
; Instala como SERVICIO (tarea programada de arranque, cuenta SYSTEM): funciona sin sesión de usuario abierta.
Unicode true
!include "MUI2.nsh"
!define APP "JB-Personal"
!define PUERTO 8765
!define UNINST "Software\Microsoft\Windows\CurrentVersion\Uninstall\JBPersonal"
Name "${APP} ${VERSION}"
OutFile "${OUT}"
InstallDir "$PROGRAMFILES64\JB-Personal"
RequestExecutionLevel admin
SetCompressor /SOLID lzma
BrandingText "JB-Personal · Jaime Blanco — Consultor Administrativo Financiero"

!define MUI_ICON "${ICON}"
!define MUI_UNICON "${ICON}"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_TEXT "Abrir JB-Personal en el navegador"
!define MUI_FINISHPAGE_RUN_FUNCTION AbrirApp
!define MUI_WELCOMEPAGE_TEXT "Este asistente instala JB-Personal en un solo paso. Se inicia solo al encender el equipo y NO necesita que haya una sesión de usuario abierta.$\r$\n$\r$\nLos datos se guardan en C:\ProgramData\JB-Personal y no se borran al desinstalar."
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Spanish"

Function AbrirApp
  ExecShell "open" "http://127.0.0.1:${PUERTO}/"
FunctionEnd

Section "JB-Personal (servicio)" SEC_APP
  SectionIn RO
  SetShellVarContext all
  ; si ya estaba instalado: detener el servicio para poder reemplazar archivos
  IfFileExists "$INSTDIR\desktop\windows\detener_servicio.ps1" 0 +2
    nsExec::ExecToLog 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\desktop\windows\detener_servicio.ps1" -Dir "$INSTDIR"'
  SetOutPath "$INSTDIR"
  File /r "${STAGE}\*.*"
  File "${ICON}"
  CreateDirectory "$SMPROGRAMS\JB-Personal"
  WriteINIStr "$SMPROGRAMS\JB-Personal\JB-Personal.url" "InternetShortcut" "URL" "http://127.0.0.1:${PUERTO}/"
  WriteINIStr "$SMPROGRAMS\JB-Personal\JB-Personal.url" "InternetShortcut" "IconFile" "$INSTDIR\jb-personal.ico"
  WriteINIStr "$SMPROGRAMS\JB-Personal\JB-Personal.url" "InternetShortcut" "IconIndex" "0"
  WriteINIStr "$DESKTOP\JB-Personal.url" "InternetShortcut" "URL" "http://127.0.0.1:${PUERTO}/"
  WriteINIStr "$DESKTOP\JB-Personal.url" "InternetShortcut" "IconFile" "$INSTDIR\jb-personal.ico"
  WriteINIStr "$DESKTOP\JB-Personal.url" "InternetShortcut" "IconIndex" "0"
  CreateShortcut "$SMPROGRAMS\JB-Personal\Administrar el servicio.lnk" "$INSTDIR\desktop\windows\Administrar JB-Personal.bat" "" "$INSTDIR\jb-personal.ico"
  CreateShortcut "$SMPROGRAMS\JB-Personal\Habilitar acceso desde la red.lnk" "$INSTDIR\desktop\windows\Habilitar acceso en red.bat" "" "$INSTDIR\jb-personal.ico"
  CreateShortcut "$SMPROGRAMS\JB-Personal\Solo esta PC (quitar acceso de red).lnk" "$INSTDIR\desktop\windows\Solo esta PC.bat" "" "$INSTDIR\jb-personal.ico"
  CreateShortcut "$SMPROGRAMS\JB-Personal\Manuales.lnk" "$INSTDIR\docs"
  CreateShortcut "$SMPROGRAMS\JB-Personal\Desinstalar JB-Personal.lnk" "$INSTDIR\Desinstalar.exe"
  WriteUninstaller "$INSTDIR\Desinstalar.exe"
  WriteRegStr HKLM "${UNINST}" "DisplayName" "${APP}"
  WriteRegStr HKLM "${UNINST}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKLM "${UNINST}" "DisplayIcon" "$INSTDIR\jb-personal.ico"
  WriteRegStr HKLM "${UNINST}" "Publisher" "Jaime Blanco"
  WriteRegStr HKLM "${UNINST}" "UninstallString" '"$INSTDIR\Desinstalar.exe"'
  WriteRegDWORD HKLM "${UNINST}" "NoModify" 1
SectionEnd

Section "-Registrar servicio"
  DetailPrint "Registrando el servicio de arranque…"
  nsExec::ExecToLog 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\desktop\windows\instalar_servicio.ps1" -Dir "$INSTDIR" -Puerto ${PUERTO}'
  Pop $2
  StrCmp $2 "0" ok
    MessageBox MB_ICONEXCLAMATION "El servicio se instaló pero no respondió a tiempo (código $2).$\r$\nRevise C:\ProgramData\JB-Personal\logs\servicio.log o use «Administrar el servicio» del menú Inicio."
  ok:
SectionEnd

Section "Uninstall"
  SetShellVarContext all
  nsExec::ExecToLog 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\desktop\windows\detener_servicio.ps1" -Dir "$INSTDIR" -Quitar'
  ; Los datos (C:\ProgramData\JB-Personal: base de datos y respaldos) NO se borran al desinstalar.
  RMDir /r "$INSTDIR"
  Delete "$DESKTOP\JB-Personal.url"
  RMDir /r "$SMPROGRAMS\JB-Personal"
  DeleteRegKey HKLM "${UNINST}"
  MessageBox MB_ICONINFORMATION "JB-Personal se desinstaló.$\r$\nSus datos siguen en C:\ProgramData\JB-Personal (elimínelos manualmente solo si ya no los necesita)."
SectionEnd
