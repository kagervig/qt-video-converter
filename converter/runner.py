"""Runs ONE job with QProcess. M2 (run), M3 (progress parsing).

Why QProcess and not subprocess: QProcess is asynchronous and integrates with
Qt's event loop. It emits signals as output arrives and when the process exits,
so ffmpeg runs without blocking the UI thread. subprocess would freeze the
window for the whole encode.

A "signal" is an event a QObject emits; a "slot" is a function connected to it.
This runner emits progress/finished/failed; callers connect slots to react.

The flow is two processes in sequence: ffprobe (read duration) then ffmpeg
(encode). We chain them by starting ffmpeg from ffprobe's finished handler.
"""

from PySide6.QtCore import QObject, QProcess, Signal

from converter.ffmpeg_cmd import build_encode_args, build_probe_args
from converter.ffmpeg_path import ffmpeg_path, ffprobe_path
from converter.job import Job

# ffmpeg's -progress output reports elapsed encode position under this key.
# NOTE: out_time_us is microseconds (verified on ffmpeg 8.1.2); out_time_ms
# reports the same microsecond value despite its name.
PROGRESS_KEY = "out_time_us"
MICROSECONDS_PER_SECOND = 1_000_000


class JobRunner(QObject):
    progress = Signal(int)   # 0-100
    finished = Signal()      # encode completed successfully
    failed = Signal(str)     # encode failed; payload is an error message

    def __init__(self, parent: QObject | None = None) -> None:
        """Set up empty state. No process runs until start() is called."""
        super().__init__(parent)
        self._process: QProcess | None = None
        self._job: Job | None = None
        self._duration_s: float = 0.0  # from ffprobe; drives the progress math
        self._stdout_buffer: str = ""  # holds a partial trailing line between reads
        self._last_percent: int = -1   # avoid emitting the same value repeatedly

    def start(self, job: Job) -> None:
        """Probe the duration, then (on probe finish) start the encode."""
        self._job = job
        self._run_probe(job)

    def _run_probe(self, job: Job) -> None:
        """Launch ffprobe to read the clip's duration (needed for % progress)."""
        self._process = QProcess(self)
        self._process.finished.connect(self._on_probe_finished)
        self._process.start(ffprobe_path(), build_probe_args(job.input_path))

    def _on_probe_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        """Store the duration ffprobe printed, then start the encode."""
        output = bytes(self._process.readAllStandardOutput()).decode().strip()
        try:
            self._duration_s = float(output)
        except ValueError:
            self._duration_s = 0.0  # couldn't read duration; progress stays at 0
        assert self._job is not None
        self._run_encode(self._job)

    def _run_encode(self, job: Job) -> None:
        """Launch ffmpeg and wire up its stdout (progress) and exit signals."""
        self._process = QProcess(self)
        self._stdout_buffer = ""
        self._last_percent = -1
        self._process.finished.connect(self._on_encode_finished)
        self._process.readyReadStandardOutput.connect(self._on_ready_read)
        self._process.start(
            ffmpeg_path(), build_encode_args(job.input_path, job.output_path)
        )

    def _on_ready_read(self) -> None:
        """Called whenever ffmpeg has written more to stdout (the -progress stream).

        Output arrives in arbitrary chunks that may split mid-line, so we keep
        any unfinished trailing line in a buffer and only parse complete lines.
        """
        self._stdout_buffer += bytes(
            self._process.readAllStandardOutput()
        ).decode(errors="replace")
        *complete_lines, self._stdout_buffer = self._stdout_buffer.split("\n")
        for line in complete_lines:
            self._handle_progress_line(line.strip())

    def _handle_progress_line(self, line: str) -> None:
        """Turn one `out_time_us=...` line into a 0-100 percent and emit it."""
        if self._duration_s <= 0 or not line.startswith(f"{PROGRESS_KEY}="):
            return
        value = line.split("=", 1)[1]
        try:
            elapsed_s = int(value) / MICROSECONDS_PER_SECOND
        except ValueError:
            return  # ffmpeg emits "N/A" before the first real timestamp
        percent = int(min(100, max(0, elapsed_s / self._duration_s * 100)))
        if percent != self._last_percent:
            self._last_percent = percent
            self.progress.emit(percent)

    def _on_encode_finished(
        self, exit_code: int, status: QProcess.ExitStatus
    ) -> None:
        """Emit finished on a clean exit, else failed with ffmpeg's stderr."""
        if exit_code == 0 and status == QProcess.ExitStatus.NormalExit:
            self.finished.emit()
        else:
            stderr = bytes(self._process.readAllStandardError()).decode()
            self.failed.emit(stderr or f"ffmpeg exited with code {exit_code}")

    # TODO(M7): cancel() — kill the process and delete the partial output.
