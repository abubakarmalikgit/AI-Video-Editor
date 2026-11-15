# MalixAris Studio 3.1 — Reliability Update

## Fixed
- Source scanner counts all supported video/image files. Files without numeric names and duplicate numeric IDs receive deterministic unused library IDs instead of being silently ignored.
- Timeline overview now distinguishes source assets, script lines and timeline clip pieces. Numbered script lines also accept `001.`, `001 -`, `001:` and equivalent formats.
- Explicit transition requests are enforced with a deterministic fallback when the AI omits a transition action.
- FFmpeg xfade graph no longer resets timestamps/timebase in a way that produced invalid `1/0` frame-rate metadata on common builds. Dissolve, slide, wipe and dip-to-black were tested.
- Failed transition effects are reported as hard-cut fallbacks and are not silently cached as successful transitions.
- Project edits, transition maps, history and timeline snapshots are separated by script + clips folder + voiceover. Legacy Studio 3.0 state is migrated when the matching script is opened.
- Output workspace lists prior rendered videos and allows in-app playback.
- Gemini requests are pinned to `gemini-3.6-flash`, serialized, use longer streaming timeouts and bounded 429/503 retries. Model discovery and silent model rotation were removed from the normal path.

## Validation performed
- Python compilation across project modules.
- JavaScript syntax checks for all frontend scripts and the inline HTML script.
- Script parser tests for numbered line formats.
- 12-file media scan test including unnumbered names.
- Legacy project migration and project-isolation tests.
- Simulated Gemini 429 followed by a successful Gemini 3.6 Flash retry.
- FFmpeg tests for dissolve, slide-left, wipe-left and fade-to-black.
- Full short-video render test with a real transition and audio mux.

## Limits
- Gemini 3.6 Flash still depends on API-key access and provider quota. No client can bypass a provider-side exhausted quota.
- The app remains a script/voiceover-driven video assembler with a generated timeline overview, not a new full manual multitrack NLE.
