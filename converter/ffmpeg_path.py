"""Resolves ffmpeg/ffprobe binary locations.

During development we find the Homebrew binaries directly. We deliberately do
NOT trust PATH: a macOS .app bundle launched from Finder does not inherit your
shell PATH, so relying on it would break the packaged app.

M9 extends this to prefer a binary bundled inside the frozen .app (relative to
sys._MEIPASS) before falling back to these Homebrew locations.
"""

from pathlib import Path

HOMEBREW_BIN_DIRS = ("/opt/homebrew/bin", "/usr/local/bin")


def _resolve(name: str) -> str:
    """Return the full path to `name` in a known Homebrew bin dir, or raise."""
    for directory in HOMEBREW_BIN_DIRS:
        candidate = Path(directory) / name
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError(
        f"Could not find '{name}'. Install it with: brew install ffmpeg"
    )
    # TODO(M9): check a bundled copy (sys._MEIPASS) before the Homebrew dirs.


def ffmpeg_path() -> str:
    """Absolute path to the ffmpeg binary."""
    return _resolve("ffmpeg")


def ffprobe_path() -> str:
    """Absolute path to the ffprobe binary."""
    return _resolve("ffprobe")
