"""Resolves ffmpeg/ffprobe binary locations.

During development we find the Homebrew binaries directly. We deliberately do
NOT trust PATH: a macOS .app bundle launched from Finder does not inherit your
shell PATH, so relying on it would break the packaged app.

When frozen by PyInstaller we prefer a binary bundled inside the app (under
sys._MEIPASS), falling back to these Homebrew locations for development.
"""

import sys
from pathlib import Path

HOMEBREW_BIN_DIRS = ("/opt/homebrew/bin", "/usr/local/bin")


def _bundled_dir() -> Path | None:
    """The directory PyInstaller unpacks bundled files into, or None if not frozen."""
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) if base else None


def _resolve(name: str) -> str:
    """Return the full path to `name`, preferring a bundled copy, or raise."""
    search_dirs: list[Path] = []
    bundled = _bundled_dir()
    if bundled is not None:
        search_dirs.append(bundled)
    search_dirs.extend(Path(d) for d in HOMEBREW_BIN_DIRS)

    for directory in search_dirs:
        candidate = directory / name
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError(
        f"Could not find '{name}'. Install it with: brew install ffmpeg"
    )


def ffmpeg_path() -> str:
    """Absolute path to the ffmpeg binary."""
    return _resolve("ffmpeg")


def ffprobe_path() -> str:
    """Absolute path to the ffprobe binary."""
    return _resolve("ffprobe")
