@echo off
title Tapsquatch - Profile Maker
cd /d "%~dp0"
set "PY=python"
where py >nul 2>nul && set "PY=py -3"
%PY% --version >nul 2>nul
if errorlevel 1 (
  echo Python is not installed - run Start.bat first.
  pause
  exit /b
)
%PY% profile_maker.py
pause
