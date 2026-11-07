@echo off
cd /d "%~dp0"
title Desktop Watch
python server.py %*
if errorlevel 1 pause
