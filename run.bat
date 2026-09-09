@echo off
set PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
if not exist "%PYEXE%" set PYEXE=python
"%PYEXE%" main.py
pause