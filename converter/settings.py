"""Persisted user settings, backed by QSettings (M8).

QSettings stores values in the platform's native location (a plist under
~/Library/Preferences on macOS), keyed by organization + application name. This
class is a thin typed wrapper so the rest of the app never touches raw keys.
"""

from PySide6.QtCore import QSettings

from converter.ffmpeg_cmd import DEFAULT_CRF

ORG = "QtVideoConverter"
APP = "H264Converter"

# CRF slider bounds (lower = higher quality / larger file).
CRF_MIN = 18
CRF_MAX = 28


class Settings:
    def __init__(self) -> None:
        """Open the app's persisted settings store."""
        self._qs = QSettings(ORG, APP)

    @property
    def output_dir(self) -> str:
        """Destination folder, or "" meaning 'next to each source file'."""
        return self._qs.value("output_dir", "", str)

    @output_dir.setter
    def output_dir(self, value: str) -> None:
        self._qs.setValue("output_dir", value)

    @property
    def crf(self) -> int:
        """Encode quality level; defaults to the app-wide default CRF."""
        return self._qs.value("crf", DEFAULT_CRF, int)

    @crf.setter
    def crf(self, value: int) -> None:
        self._qs.setValue("crf", value)
