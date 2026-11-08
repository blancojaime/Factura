; Instalador sencillo de "Gestión de Personal y Asistencia Municipal" (Windows 10+ x64)
; Se compila con build_installer.py (define VERSION, STAGE y OUT).
Unicode true
!include "MUI2.nsh"
!define APP "Gestión de Personal y Asistencia Municipal"
!define UNINST "Software\Microsoft\Windows\CurrentVersion\Uninstall\GAMPersonal"
Name "${APP} ${VERSION}"
OutFile "${OUT}"
InstallDir "$LOCALAPPDATA\Programs\GAMPersonal"
RequestExecutionLevel user          ; sin permisos de administrador: se instala para el usuario actual
SetCompressor /SOLID lzma
BrandingText "${APP}"

!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_FUNCTION LanzarApp
!define MUI_FINISHPAGE_RUN_TEXT "Abrir el sistema ahora"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Spanish"

Function LanzarApp
  SetOutPath "$INSTDIR\desktop"
  Exec '"$INSTDIR\python\python.exe" "$INSTDIR\desktop\launcher.py"'
FunctionEnd

Section "Instalar"
  SetOutPath "$INSTDIR"
  File /r "${STAGE}\*.*"
  SetOutPath "$INSTDIR\desktop"
  CreateDirectory "$SMPROGRAMS\GAM Personal"
  CreateShortcut "$SMPROGRAMS\GAM Personal\${APP}.lnk" "$INSTDIR\python\python.exe" '"$INSTDIR\desktop\launcher.py"' "" 0 SW_SHOWMINIMIZED
  CreateShortcut "$SMPROGRAMS\GAM Personal\Manuales.lnk" "$INSTDIR\docs"
  CreateShortcut "$DESKTOP\${APP}.lnk" "$INSTDIR\python\python.exe" '"$INSTDIR\desktop\launcher.py"' "" 0 SW_SHOWMINIMIZED
  WriteUninstaller "$INSTDIR\Desinstalar.exe"
  CreateShortcut "$SMPROGRAMS\GAM Personal\Desinstalar.lnk" "$INSTDIR\Desinstalar.exe"
  WriteRegStr HKCU "${UNINST}" "DisplayName" "${APP}"
  WriteRegStr HKCU "${UNINST}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${UNINST}" "UninstallString" '"$INSTDIR\Desinstalar.exe"'
  WriteRegDWORD HKCU "${UNINST}" "NoModify" 1
SectionEnd

Section "Uninstall"
  ; Los datos (%APPDATA%\GAMPersonal: base de datos y respaldos) NO se borran al desinstalar.
  RMDir /r "$INSTDIR"
  Delete "$DESKTOP\${APP}.lnk"
  RMDir /r "$SMPROGRAMS\GAM Personal"
  DeleteRegKey HKCU "${UNINST}"
SectionEnd
