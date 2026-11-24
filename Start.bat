@echo off
title ControlBridge
cd /d "%~dp0"

set "PY=python"
where py >nul 2>nul && set "PY=py -3"

%PY% --version >nul 2>nul
if errorlevel 1 (
  echo Python is not installed.
  echo A download page will open. Install it, and tick "Add python.exe to PATH".
  echo Then run Start.bat again.
  start "" https://www.python.org/downloads/
  pause
  exit /b
)

%PY% -c "import pygame, customtkinter, PIL" >nul 2>nul
if errorlevel 1 (
  echo First run: installing what ControlBridge needs, one moment...
  %PY% -m pip install --user -r requirements.txt
)

%PY% controlbridge.py %*
pause
