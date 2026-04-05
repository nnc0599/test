@echo off
setlocal

py -3.12 -m pip install --upgrade pip
if errorlevel 1 exit /b 1

py -3.12 -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

py -3.12 -m pip install pyinstaller
if errorlevel 1 exit /b 1

py -3.12 app_gen\build_onefile.py
if errorlevel 1 exit /b 1

echo Build xong tai app_gen\sales_app.exe