@echo off
title MediScribe AI Backend Server
echo =======================================================
echo   Starting MediScribe Clinical AI REST Backend
echo   Listening on http://127.0.0.1:8000
echo =======================================================
cd /d "%~dp0"
python server.py
pause
