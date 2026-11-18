"""Builds ffmpeg/ffprobe argument lists.

Pure Python: no Qt imports, no process execution. This keeps the command
construction trivially testable (see tests/test_ffmpeg_cmd.py). The returned
lists are the arguments *after* the program name, ready to hand to QProcess
alongside the resolved binary path.
"""

from pathlib import Path

# Default encode settings (see build plan). Pulled out as constants so there
# are no magic values buried in the argument list.
VIDEO_CODEC = "libx264"
DEFAULT_CRF = 23
PRESET = "medium"
AUDIO_CODEC = "copy"
OUTPUT_SUFFIX = "_h264"


def build_encode_args(
    input_path: str, output_path: str, crf: int = DEFAULT_CRF
) -> list[str]:
    """Arguments to transcode H.265 -> H.264 MP4.

    crf               quality level (lower = better/larger); 18-28 is typical
    -tag:v avc1       mark the stream so QuickTime recognizes it as H.264
    -movflags +faststart  move the moov atom to the front for streaming
    -progress pipe:1  emit machine-readable progress on stdout (parsed in M3)
    -nostats          suppress the default human-readable progress on stderr
    """
    return [
        "-y",
        "-i", input_path,
        "-c:v", VIDEO_CODEC,
        "-crf", str(crf),
        "-preset", PRESET,
        "-c:a", AUDIO_CODEC,
        "-tag:v", "avc1",
        "-movflags", "+faststart",
        "-progress", "pipe:1",
        "-nostats",
        output_path,
    ]


def build_probe_args(input_path: str) -> list[str]:
    """Arguments to read the container duration (seconds) as a bare number."""
    return [
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        input_path,
    ]


def default_output_path(input_path: str, output_dir: str | None = None) -> str:
    """`<name>_h264.mp4` in `output_dir`, or next to the source when unset."""
    source = Path(input_path)
    name = f"{source.stem}{OUTPUT_SUFFIX}.mp4"
    folder = Path(output_dir) if output_dir else source.parent
    return str(folder / name)
