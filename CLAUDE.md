# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

VoxExtract: desktop app (Tkinter GUI + CLI) that extracts audio from video files via FFmpeg and converts to MP3/AAC/FLAC/WAV. Primary target platform is Windows (PyInstaller `.exe`). Code comments, docstrings, log messages and README are in Italian.

## Commands

```bash
# Run GUI (no args) or CLI (positional: input [output] [quality] [format])
python vox_extract.py
python vox_extract.py video.mp4 audio.flac high FLAC

# Tests (stdlib unittest, no pytest)
python -m unittest test_vox_extract -v
python -m unittest test_vox_extract.TestExtractAudio.test_extract_audio_file_not_exists

# Build Windows executable -> dist/VoxExtract.exe (ffmpeg.exe must be copied next to it)
pyinstaller VoxExtract.spec

# Regenerate icon.ico (requires Pillow)
python create_icon.py
```

Requirements: Python 3.10+ (code uses `X | None` syntax), FFmpeg/ffprobe on PATH or next to the script. No third-party runtime dependencies.

**Tests import `vox_extract`, which imports `tkinter` at module level** — the interpreter must have Tk support (`_tkinter`), even for non-GUI tests. A pyenv Python built without Tk fails at import.

## Architecture

Everything lives in a single module, `vox_extract.py`, organized in banner-delimited sections:

- **i18n**: `TRANSLATIONS` dict keyed by `Language` enum value (`"it"`, `"en"`); `get_text(key, lang, **kwargs)` falls back to Italian, then to the key itself. All user-facing strings should go through this. Note `extract_audio` calls `get_text` without a `lang`, so its error messages are always Italian.
- **Config**: `QUALITY_PRESETS` (low/medium/high/best → 128k–320k) and `AUDIO_FORMATS` (key → extension, ffmpeg `-f` muxer, codec) dataclass tables. Adding a format = adding an entry here; WAV is special-cased in `extract_audio` to omit `-ab`.
- **Core (GUI-independent)**: `find_ffmpeg()` searches the app dir first (`sys.executable` dir when PyInstaller-frozen, else script dir; also `bin/`), then PATH. `get_video_duration()` derives ffprobe path by string-replacing `ffmpeg`. `extract_audio()` runs FFmpeg via `Popen`, parses `time=HH:MM:SS.cc` from stderr against the duration to drive an optional `progress_callback(0–100)`, and returns `(success, error_msg)` instead of raising.
- **GUI**: `VoxExtractGUI` builds a custom neon/dark Tk UI. Extraction runs on a daemon `threading.Thread`; all UI updates from the worker are marshalled back via `root.after(0, ...)` — keep that pattern for any new worker→UI calls.
- **Entry**: `__main__` dispatches to `run_gui()` with no args, else `run_cli(sys.argv[1:])`.

All `subprocess` calls pass `creationflags=CREATE_NO_WINDOW` on win32 to avoid console flashes in the windowed (`console=False`) build — preserve this on new subprocess calls.

The window icon is an embedded base64 PNG in `get_icon_data()` (tests check it decodes to a PNG); `icon.ico` is used only by PyInstaller.

Logging writes to `vox_extract.log` in the CWD plus stderr.

`audio_extractor.py` is an older, gitignored predecessor — not part of the app; don't edit it.

## Web app (`web/`)

Static PWA port of the same tool, built on ffmpeg.wasm — the recommended distribution, since unsigned `.exe`/`.app` builds get blocked by Windows Smart App Control and macOS Gatekeeper. No build step, no npm: plain ES modules served as-is.

```bash
cd web && python3 -m http.server 8000   # any static server; must be http(s), not file://
```

- `app.js` mirrors `QUALITY_PRESETS`/`AUDIO_FORMATS`/i18n keys from `vox_extract.py` — keep both in sync when changing formats or strings.
- ffmpeg.wasm is **vendored** in `web/vendor/` (single-thread core, so no SharedArrayBuffer / COOP-COEP headers needed; works on GitHub Pages). Update procedure in `web/vendor/README.md`.
- Input files are mounted with `WORKERFS` (read in place, not copied into wasm memory); output is read back from MEMFS. Progress comes from parsing `Duration:`/`time=` in ffmpeg log lines, like the Python version.
- Cancel = `ffmpeg.terminate()` + reload the engine; the old instance's FS is gone, which is why cleanup in `extractOne` is skipped when `cancelRequested`.
- `sw.js` precaches every asset (including the ~31 MB wasm) under a versioned cache name. **Bump `VERSION` in `sw.js` on every change to `web/`**, otherwise installed clients keep serving the old files. New files must also be added to its `ASSETS` list.
- Deployed to GitHub Pages by `.github/workflows/pages.yml` on push to `main` touching `web/`. All URLs are relative so it works under the `/VoxExtract/` subpath.
