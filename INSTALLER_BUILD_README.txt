MALIXARIS STUDIO 3.2 — SINGLE-FILE ONLINE WINDOWS INSTALLER
==========================================================

GOAL
----
The output is ONE file:
  installer\MalixAris_Studio_Setup.exe

Share that one EXE with friends. They do not need Python, FFmpeg, PyInstaller,
Inno Setup, or a ZIP on their computers.

WHAT THE SETUP EXE INSTALLS
---------------------------
- MalixAris Studio desktop application and bundled Python runtime
- Python dependencies collected by PyInstaller
- Web interface, scripts, CSS and local assets
- FFmpeg and FFprobe (bundled in the application payload)
- Microsoft Edge WebView2 Runtime bootstrapper (embedded in the setup EXE;
  it downloads/installs the runtime if it is missing)
- Desktop shortcut (selected by default)
- Start Menu shortcut
- Windows uninstaller
- Fresh per-user data, output, work, logs and projects folders

ONLINE REQUIREMENTS
-------------------
The installer needs an internet connection to install WebView2 if it is not
already installed. FFmpeg is downloaded during the BUILD process and included
inside the final setup EXE. Speech recognition model files may be downloaded
on first use by the application. Each friend supplies their own Gemini API key.

BUILD THE SHAREABLE EXE (BUILD MACHINE ONLY)
--------------------------------------------
Build on Windows 10/11 x64:
1. Extract this package.
2. Install Python 3.11 and Inno Setup 6 on the BUILD machine.
3. Run BUILD_WINDOWS_INSTALLER.bat.
4. Wait for the build to complete.
5. Share only:
   installer\MalixAris_Studio_Setup.exe

Friends installing the app do NOT need Python or Inno Setup.

AUTOMATED WINDOWS BUILD OPTION
------------------------------
The package includes:
  .github\workflows\build-windows-installer.yml

Push the package contents to a GitHub repository and run the workflow
"Build MalixAris Studio Windows Installer" from the Actions tab. Download the
MalixAris-Studio-Setup artifact after the workflow succeeds. Only distribute
the generated Setup.exe.

USER DATA AND PROJECTS
----------------------
Every new installation starts with its own empty local project library.
Projects, settings, output and model caches are created separately for each
Windows user. The setup does not copy the developer's private projects,
Gemini key, footage, or voice recordings to friends' computers.

The app's data folders are under the installation directory in the current
application architecture. Do not delete these folders when updating. Back up
data, projects, output, work and logs before uninstalling or moving the app.
Original video/audio source files are not embedded in project files; users
must import or relink their own media.

IMPORTANT VALIDATION
--------------------
This environment cannot compile or run a Windows GUI installer. The package
and scripts are prepared, but the actual Setup.exe must be built on Windows
(or by the included GitHub Actions workflow) and tested on a clean Windows
10/11 machine before public distribution. Do not share an untested build.
