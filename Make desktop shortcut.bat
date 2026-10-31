@echo off
setlocal
cd /d "%~dp0"

rem Puts a shortcut called "Novalie" on your desktop that starts it (Start Novalie.bat in this folder).
rem It only creates that one shortcut; delete it like any other shortcut if you do not want it.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d = [Environment]::GetFolderPath('Desktop'); $s = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'Novalie.lnk')); $s.TargetPath = (Join-Path (Get-Location) 'Start Novalie.bat'); $s.WorkingDirectory = (Get-Location).Path; $s.IconLocation = 'shell32.dll,13'; $s.Description = 'Novalie'; $s.Save(); Write-Host ('  Shortcut made: ' + (Join-Path $d 'Novalie.lnk'))"
if errorlevel 1 (
  echo   The shortcut could not be made.
)
echo.
pause
endlocal
