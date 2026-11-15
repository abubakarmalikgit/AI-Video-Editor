# MalixAris Studio 3.1

MalixAris Studio is a Windows desktop video-production application built with Python and pywebview. This package combines the supplied project archive with the previously implemented Part 3A Premium Look, Part 3B Polish & Export, and Part 3D Voice Commands modules, plus a redesigned hybrid studio shell.

## Install and launch

For a fresh installation:
1. Extract the entire ZIP to a writable folder (do not run it from inside the ZIP).
2. On Windows, double-click `main.bat`.

For an update that preserves your previous projects and renders:
1. Close MalixAris Studio.
2. Back up your current application folder.
3. Extract this ZIP **into the same existing application folder** and allow source files to be replaced.
4. Keep the existing `data`, `output`, `work` and `logs` folders. This update ZIP intentionally does not overwrite them.
5. Double-click `main.bat`.
3. The setup script checks for Python 3.10–3.12, FFmpeg and WebView2, creates `.venv`, installs `requirements.txt`, verifies dependencies, and launches the application.
4. On first launch, allow the setup process to download FFmpeg/WebView2 if they are missing. An internet connection is required for first-time setup and AI/model downloads.

You can also activate the virtual environment and run `python app.py` after setup.

## Included capabilities

- Existing clip-folder, voiceover and script workflow.
- Timeline generation and clip/script matching.
- Existing AI agent and AI Director workflow.
- Existing captions and background-music controls.
- Polish & Export finishing panel.
- Voice command and microphone integration.
- Premium visual layer and redesigned Home/navigation/command-palette interface.
- Existing logs, system diagnostics and local rendering pipeline.

## Important scope note

The current backend assembles videos from numbered media clips, a voiceover and script/timestamp mapping. Its Timeline page is a generated sequence overview. This release does **not** add a new, full non-linear editor with manual drag-and-drop multitrack clip editing, keyframes, proxy media or a new rendering engine. Those require a separate timeline/render-engine implementation. The new interface does not present those capabilities as working controls.

Part 3C was not present in the supplied implementation instructions, so it is not represented as implemented.

## Project structure

- `app.py`: desktop application and pywebview API registration.
- `engine.py`: existing media assembly/rendering engine.
- `director.py`, `agent.py`, `ai.py`: existing AI workflow.
- `finish.py`, `polish.py`: captions/music and finishing/export.
- `voicecmd.py`: voice command integration.
- `web/`: interface, styles and JavaScript modules.
- `main.bat`: Windows setup, dependency verification and launcher.

## Notes

- Keep the folder structure intact.
- Do not delete `web/fonts/`; these are bundled interface fonts.
- Generated settings, caches, logs and output files are created at runtime.
- Test microphone permission in Windows privacy settings if voice input is unavailable.
- AI features require a configured API key and a supported network connection.


## Update: reliability fixes

- Source media scanning now includes supported video/image files without numeric filenames by assigning stable sequential library IDs after explicit numeric IDs.
- Timeline statistics distinguish source assets, script lines and timeline clip pieces. These are different counts and are displayed separately.
- Agent and Director transition requests receive deterministic transition actions if the model omits them. Transition render failures are reported and are not silently counted as successful effects.
- Editing state and timeline snapshots are stored per production fingerprint (script, source folder and voiceover), with migration support for the previous script-only project file, so switching projects no longer wipes edits from the previous one.
- The Output workspace lists prior rendered video files and provides in-app playback controls.
- Gemini is pinned to `gemini-3.6-flash`; streaming and non-streaming requests use bounded rate-limit retries without silently rotating to other models.

Gemini 3.6 Flash still depends on availability and quota for the configured API key. Software cannot override a provider-side exhausted quota.


## Playback and project retention

Open the **Output** workspace and use **Refresh library** to see and play previously rendered videos stored in the application's `output` folder. Agent edits and transition settings are now separated by script fingerprint and are retained when you switch to another script.

## Transition behavior

When the user explicitly asks for transitions, the AI Director returns validated transition operations. If the model omits them, the application selects a small number of boundaries automatically. The timeline shows the transition assigned after each line. If FFmpeg cannot render a selected effect, the log and render warnings clearly say that a hard cut was used instead.
