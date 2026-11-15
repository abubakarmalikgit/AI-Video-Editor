@echo off
setlocal
title MalixAris Studio - Setup
cd /d "%~dp0"
set PYTHONUTF8=1

echo ============================================
echo   MALIXARIS STUDIO - SETUP AND VERIFY
echo ============================================
echo.

echo [1/6] Checking Python...
set "PY="
py -3.11 -c "import sys" >nul 2>&1 && set "PY=py -3.11"
if not defined PY py -3.12 -c "import sys" >nul 2>&1 && set "PY=py -3.12"
if not defined PY py -3.10 -c "import sys" >nul 2>&1 && set "PY=py -3.10"
if not defined PY python -c "import sys; sys.exit(0 if sys.version_info[:2] in [(3,10),(3,11),(3,12)] else 1)" >nul 2>&1 && set "PY=python"
if defined PY goto py_ok

echo Python 3.10 to 3.12 was not found.
where winget >nul 2>&1
if errorlevel 1 goto py_manual
echo Installing Python 3.11 with winget...
winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
echo.
echo Python installed. CLOSE this window and double-click main.bat again.
pause
exit /b 0

:py_manual
echo Please install Python 3.11 from https://www.python.org/downloads/release/python-3119/
echo IMPORTANT: tick "Add python.exe to PATH" in the installer.
echo Then run main.bat again.
pause
exit /b 1

:py_ok
echo     Found: %PY%

echo [2/6] Checking FFmpeg...
if not exist tools mkdir tools
where ffmpeg >nul 2>&1
if errorlevel 1 goto ffmpeg_ok
if exist "tools\ffmpeg\bin\ffmpeg.exe" goto ffmpeg_local
echo     FFmpeg not found. Downloading (about 80 MB), please wait...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile 'tools\ffmpeg.zip'"
if errorlevel 1 goto fail
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Force -Path 'tools\ffmpeg.zip' -DestinationPath 'tools\_ff'"
if errorlevel 1 goto fail
for /d %%D in (tools\_ff\ffmpeg-*) do move "%%D" "tools\ffmpeg" >nul
del /q tools\ffmpeg.zip >nul 2>&1
rmdir /s /q tools\_ff >nul 2>&1
if not exist "tools\ffmpeg\bin\ffmpeg.exe" goto fail
:ffmpeg_local
set "PATH=%~dp0tools\ffmpeg\bin;%PATH%"
:ffmpeg_ok
echo     FFmpeg is ready.

echo [3/6] Checking Microsoft Edge WebView2 (needed for the app window)...
reg query "HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" /v pv >nul 2>&1
if errorlevel 1 goto wv_ok
reg query "HKCU\Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" /v pv >nul 2>&1
if errorlevel 1 goto wv_ok
echo     WebView2 not found. Downloading installer...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' -OutFile 'tools\wv2setup.exe'"
if errorlevel 1 goto fail
tools\wv2setup.exe /silent /install
:wv_ok
echo     WebView2 is ready.

echo [4/6] Preparing virtual environment...
if not exist ".venv\Scripts\python.exe" %PY% -m venv .venv
if errorlevel 1 goto fail
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip >nul 2>&1

echo [5/6] Installing packages (first time can take 5-10 minutes)...
pip install -r requirements.txt
if errorlevel 1 goto fail

nvidia-smi >nul 2>&1
if errorlevel 1 goto fonts
echo     NVIDIA GPU detected - installing optional GPU libraries...
pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"

:fonts
python fonts.py

echo [6/6] Verifying everything...
echo.
python check_system.py
if errorlevel 1 goto fail

echo.
echo Starting MalixAris Video Maker...
python app.py
if errorlevel 1 goto fail
exit /b 0

:fail
echo.
echo ============================================
echo   SOMETHING FAILED. Scroll up, copy the error
echo   message and send it to me.
echo ============================================
pause
exit /b 1
