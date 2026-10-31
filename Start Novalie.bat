@echo off
setlocal
chcp 65001 >nul
title Novalie
cd /d "%~dp0"

rem Find Python 3.8 or newer: the Windows launcher first, then python on the PATH.
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if defined PY goto found
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>nul
if not errorlevel 1 set "PY=python"
if not defined PY goto nopython

:found
rem What it reads with: numpy (any file) and Pillow (pictures), on this computer or in novalie_libs beside it
rem (see README.md). It runs without them, reading less.
%PY% -c "import sys; sys.path.append('novalie_libs'); import numpy" >nul 2>nul
if errorlevel 1 echo   [!] numpy is not there: it will not read files. To add it: %PY% -m pip install --target novalie_libs numpy
%PY% -c "import sys; sys.path.append('novalie_libs'); import PIL" >nul 2>nul
if errorlevel 1 echo   [!] Pillow is not there: it will not open pictures. To add it: %PY% -m pip install --target novalie_libs pillow

%PY% -m novalie %*
if errorlevel 1 goto failed
goto end

:nopython
echo.
echo   Python 3.8 or newer was not found on this computer.
echo   Install it from https://www.python.org/downloads/
echo   (tick "Add python.exe to PATH"), then double-click this file again.
echo.
pause
goto end

:failed
echo.
echo   Novalie stopped because of an error (shown above).
echo.
pause

:end
endlocal
