# Building the macOS app (M9)

The app is packaged with PyInstaller into `dist/H264 Converter.app`, with
`ffmpeg` and `ffprobe` bundled inside so it runs without Homebrew on `PATH`.

## Build

```sh
source .venv/bin/activate
pip install -r requirements.txt     # includes pyinstaller
pyinstaller H264Converter.spec
open "dist/H264 Converter.app"
```

At runtime `converter/ffmpeg_path.py` looks for the bundled binaries first
(under `sys._MEIPASS`), then falls back to `/opt/homebrew/bin` and
`/usr/local/bin`. A Finder-launched `.app` does not inherit your shell `PATH`,
which is why we never rely on it.

## Caveat: dynamic vs static ffmpeg

Homebrew's `ffmpeg` is **dynamically linked** against dylibs under
`/opt/homebrew` (libx264, etc.). Bundling only the `ffmpeg` binary works on a
machine where Homebrew is installed (the dylibs exist at their absolute paths)
even if Homebrew is not on `PATH` — which satisfies the milestone's goal.

For a build that runs on a machine **without Homebrew installed at all**, use a
**static** ffmpeg/ffprobe (e.g. from https://evermeet.cx/ffmpeg/) and point the
spec at it, or add the required dylibs to `bundled_binaries` in
`H264Converter.spec`.

## Not in scope

Code signing and notarization are out of scope, so Gatekeeper will warn on other
machines (right-click → Open to bypass for personal use).
