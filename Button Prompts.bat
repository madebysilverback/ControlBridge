@echo off
title ControlBridge - Button Prompts
cd /d "%~dp0"
set "PY=python"
where py >nul 2>nul && set "PY=py -3"
%PY% --version >nul 2>nul
if errorlevel 1 (
  echo Python is not installed - run Start.bat first.
  pause
  exit /b
)
echo Close the game before changing its prompts.
echo.
%PY% prompts_patcher.py
pause
