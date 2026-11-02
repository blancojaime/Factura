; Instalador de un solo clic de ComexBol Pro (NSIS). No requiere administrador: instala para el usuario actual.
Unicode true
!include "MUI2.nsh"
!ifndef VERSION
  !define VERSION "1.0.0"
!endif
!define APP "ComexBol Pro"
!define EXE "ComexBolPro.exe"
!define UNINST "Software\Microsoft\Windows\CurrentVersion\Uninstall\ComexBolPro"

Name "${APP}"
OutFile "..\dist\ComexBolPro-Setup-${VERSION}.exe"
InstallDir "$LOCALAPPDATA\Programs\ComexBolPro"
RequestExecutionLevel user
SetCompressor /SOLID lzma
BrandingText "${APP} ${VERSION}"
!define MUI_ICON "..\src\ComexBol.App\app.ico"
!define MUI_UNICON "..\src\ComexBol.App\app.ico"
!define MUI_INSTFILESPAGE_FINISHHEADER_TEXT "Instalación completada"
!define MUI_INSTFILESPAGE_FINISHHEADER_SUBTEXT "ComexBol Pro se abrirá en unos segundos."

!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Spanish"

VIProductVersion "${VERSION}.0"
VIAddVersionKey /LANG=${LANG_SPANISH} "ProductName" "${APP}"
VIAddVersionKey /LANG=${LANG_SPANISH} "FileVersion" "${VERSION}"
VIAddVersionKey /LANG=${LANG_SPANISH} "FileDescription" "Instalador de ${APP}"

Section "Instalar"
  SetAutoClose true
  SetOutPath "$INSTDIR"
  ; Cierra la versión anterior si está abierta (actualización sobre la marcha)
  nsExec::Exec 'taskkill /F /IM ${EXE}'
  File /r "..\dist\publish\*.*"
  SetOutPath "$INSTDIR\ocr"
  File /r "..\dist\ocr\*.*"
  SetOutPath "$INSTDIR\docs"
  File /nonfatal /r "..\dist\docs\*.*"

  SetOutPath "$INSTDIR"
  CreateDirectory "$SMPROGRAMS\${APP}"
  CreateShortcut "$SMPROGRAMS\${APP}\${APP}.lnk" "$INSTDIR\${EXE}"
  CreateShortcut "$SMPROGRAMS\${APP}\Manual del usuario.lnk" "$INSTDIR\docs\Manual-de-Usuario.pdf"
  CreateShortcut "$SMPROGRAMS\${APP}\Desinstalar.lnk" "$INSTDIR\Desinstalar.exe"
  CreateShortcut "$DESKTOP\${APP}.lnk" "$INSTDIR\${EXE}"

  WriteUninstaller "$INSTDIR\Desinstalar.exe"
  WriteRegStr HKCU "${UNINST}" "DisplayName" "${APP}"
  WriteRegStr HKCU "${UNINST}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${UNINST}" "DisplayIcon" "$INSTDIR\${EXE}"
  WriteRegStr HKCU "${UNINST}" "UninstallString" '"$INSTDIR\Desinstalar.exe"'
  WriteRegStr HKCU "${UNINST}" "QuietUninstallString" '"$INSTDIR\Desinstalar.exe" /S'
  WriteRegStr HKCU "${UNINST}" "InstallLocation" "$INSTDIR"
  WriteRegDWORD HKCU "${UNINST}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINST}" "NoRepair" 1
SectionEnd

Function .onInstSuccess
  IfSilent +2
  Exec '"$INSTDIR\${EXE}"'
FunctionEnd

Section "Uninstall"
  nsExec::Exec 'taskkill /F /IM ${EXE}'
  RMDir /r "$INSTDIR"
  Delete "$DESKTOP\${APP}.lnk"
  RMDir /r "$SMPROGRAMS\${APP}"
  DeleteRegKey HKCU "${UNINST}"
  ; Los datos del usuario (%LocalAppData%\ComexBolPro\comex.db) NO se borran.
SectionEnd
