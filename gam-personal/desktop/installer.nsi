; Instalador NSIS (Windows 10+). Compilar con:  makensis installer.nsi
Unicode true
!define APP "Gestión de Personal y Asistencia Municipal"
!define EXE "GAMPersonal.exe"
Name "${APP}"
OutFile "GAMPersonal_Setup.exe"
InstallDir "$PROGRAMFILES64\GAMPersonal"
RequestExecutionLevel admin
SetCompressor /SOLID lzma
Page directory
Page instfiles
UninstPage uninstConfirm
UninstPage instfiles

Section "Instalar"
  SetOutPath "$INSTDIR"
  File /r "dist\GAMPersonal\*.*"
  File "respaldo_programado.bat"
  CreateDirectory "$SMPROGRAMS\GAMPersonal"
  CreateShortcut "$SMPROGRAMS\GAMPersonal\${APP}.lnk" "$INSTDIR\${EXE}"
  CreateShortcut "$DESKTOP\${APP}.lnk" "$INSTDIR\${EXE}"
  WriteUninstaller "$INSTDIR\Desinstalar.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\GAMPersonal" "DisplayName" "${APP}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\GAMPersonal" "UninstallString" "$INSTDIR\Desinstalar.exe"
SectionEnd

Section "Uninstall"
  ; Los datos del usuario (%APPDATA%\GAMPersonal) NO se borran: contienen la base de datos y los respaldos.
  RMDir /r "$INSTDIR"
  Delete "$DESKTOP\${APP}.lnk"
  RMDir /r "$SMPROGRAMS\GAMPersonal"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\GAMPersonal"
SectionEnd
