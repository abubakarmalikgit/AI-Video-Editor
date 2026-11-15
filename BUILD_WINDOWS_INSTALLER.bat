@echo off
setlocal EnableExtensions
title Build MalixAris Studio Windows Installer
cd /d "%~dp0"
set "PY="
py -3.11 -c "import sys" >nul 2>&1 && set "PY=py -3.11"
if not defined PY (
  echo Python 3.11 is required for this build.
  echo Install it from https://www.python.org/downloads/
  pause
  exit /b 1
)
echo [1/6] Preparing build environment...
if not exist ".buildenv\Scripts\python.exe" %PY% -m venv .buildenv
if errorlevel 1 goto fail
call ".buildenv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto fail
echo [2/6] Installing application dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 goto fail
python -m pip install pyinstaller
if errorlevel 1 goto fail
echo [3/7] Preparing WebView2 bootstrapper for the final single-file installer...
if not exist "installer_assets" mkdir "installer_assets"
if not exist "installer_assets\MicrosoftEdgeWebView2Setup.exe" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' -OutFile 'installer_assets\MicrosoftEdgeWebView2Setup.exe'"
  if errorlevel 1 goto fail
)
if not exist "installer_assets\MicrosoftEdgeWebView2Setup.exe" goto fail
echo [4/7] Preparing FFmpeg...
if not exist "tools\ffmpeg\bin\ffmpeg.exe" (
  if not exist "tools" mkdir tools
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile 'tools\ffmpeg-release.zip'"
  if errorlevel 1 goto fail
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Force 'tools\ffmpeg-release.zip' 'tools\ffmpeg_extract'"
  if errorlevel 1 goto fail
  for /d %%D in (tools\ffmpeg_extract\ffmpeg-*) do (
    if not exist "tools\ffmpeg" mkdir "tools\ffmpeg"
    xcopy "%%D\*" "tools\ffmpeg\" /E /I /Y >nul
  )
  rmdir /s /q "tools\ffmpeg_extract" >nul 2>&1
  del "tools\ffmpeg-release.zip" >nul 2>&1
)
if not exist "tools\ffmpeg\bin\ffmpeg.exe" (
  echo FFmpeg was not found after extraction.
  goto fail
)
echo [5/7] Building standalone application folder...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
python -m PyInstaller --noconfirm --clean --windowed --onedir ^
  --contents-directory "." ^
  --name "MalixAris Studio" ^
  --add-data "web;web" ^
  --add-data "tools;tools" ^
  --add-data "system_report.json;." ^
  --collect-all webview ^
  --collect-all faster_whisper ^
  --collect-all ctranslate2 ^
  --collect-all av ^
  --collect-all huggingface_hub ^
  --collect-all tokenizers ^
  --collect-all clr_loader ^
  --collect-all pythonnet ^
  --hidden-import win32timezone ^
  --hidden-import pythoncom ^
  --hidden-import pywintypes ^
  app.py
if errorlevel 1 goto fail
if not exist "dist\MalixAris Studio\MalixAris Studio.exe" goto fail
echo [6/7] Checking installer compiler...
set "ISCC="
where ISCC.exe >nul 2>&1 && set "ISCC=ISCC.exe"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  echo Inno Setup Compiler was not found.
  echo Install Inno Setup from https://jrsoftware.org/isdl.php
  echo Then reopen this window and run this file again.
  pause
  exit /b 1
)
echo [7/7] Compiling single-file setup installer...
if not exist installer mkdir installer
call "%ISCC%" "MalixAris_Setup.iss"
if errorlevel 1 goto fail
echo.
echo BUILD COMPLETE:
echo %CD%\installer\MalixAris_Studio_Setup.exe
pause
exit /b 0

:fail
echo.
echo BUILD FAILED. Copy the error above for troubleshooting.
pause
exit /b 1
