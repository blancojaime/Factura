; Instalador de JB-Activador (herramienta del EMISOR; no se entrega a las entidades). Por usuario, sin administrador.
Unicode true
!include "MUI2.nsh"
Name "JB-Activador ${VERSION}"
OutFile "${OUT}"
InstallDir "$LOCALAPPDATA\Programs\JB-Activador"
RequestExecutionLevel user
SetCompressor /SOLID lzma
!define MUI_ICON "${ICON}"
!define MUI_UNICON "${ICON}"
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_FUNCTION LanzarActivador
!define MUI_FINISHPAGE_RUN_TEXT "Abrir JB-Activador"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Spanish"
Function LanzarActivador
  SetOutPath "$INSTDIR"
  Exec '"$INSTDIR\python\pythonw.exe" "$INSTDIR\jb_activador.py"'
FunctionEnd

Section "Instalar"
  SetOutPath "$INSTDIR"
  File /r "${STAGE}\*.*"
  File "${ICON}"
  CreateShortcut "$DESKTOP\JB-Activador.lnk" "$INSTDIR\python\pythonw.exe" '"$INSTDIR\jb_activador.py"' "$INSTDIR\jb-personal.ico"
  CreateDirectory "$SMPROGRAMS\JB-Activador"
  CreateShortcut "$SMPROGRAMS\JB-Activador\JB-Activador.lnk" "$INSTDIR\python\pythonw.exe" '"$INSTDIR\jb_activador.py"' "$INSTDIR\jb-personal.ico"
  WriteUninstaller "$INSTDIR\Desinstalar.exe"
SectionEnd
Section "Uninstall"
  ; La clave privada y el historial viven en %APPDATA%\JB-Activador y NO se borran.
  RMDir /r "$INSTDIR"
  Delete "$DESKTOP\JB-Activador.lnk"
  RMDir /r "$SMPROGRAMS\JB-Activador"
SectionEnd
