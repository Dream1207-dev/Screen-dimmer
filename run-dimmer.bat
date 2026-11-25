@echo off
setlocal
cd /d %~dp0
title Screen Dimmer Launcher

call :find_python
if defined PYW goto run

echo Python was not found on this PC. Installing it now via winget...
echo (This happens only once and may take a few minutes. Do not close this window.)
echo.
winget install -e --id Python.Python.3.13 --scope user --accept-source-agreements --accept-package-agreements
echo.
echo Install step finished. Looking for Python again...
call :find_python
if defined PYW goto run

echo.
echo Automatic install did not complete.
echo Please install Python manually from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" during setup, then run this file again.
pause
exit /b 1

:run
start "" "%PYW%" "%~dp0dimmer.py"
exit /b 0

:find_python
set "PYW="
for /f "delims=" %%D in ('py -3 -c "import sys,os;print(os.path.dirname(sys.executable))" 2^>nul') do (
    if exist "%%D\pythonw.exe" set "PYW=%%D\pythonw.exe"
)
if defined PYW exit /b 0
for /d %%D in ("%LocalAppData%\Programs\Python\Python3*") do (
    if exist "%%D\pythonw.exe" set "PYW=%%D\pythonw.exe"
)
exit /b 0
