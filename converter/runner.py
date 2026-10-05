"""Runs ONE job with QProcess. M2 (run) — M3 adds progress parsing.

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


class JobRunner(QObject):
    progress = Signal(int)   # 0-100 (wired up in M3)
    finished = Signal()      # encode completed successfully
    failed = Signal(str)     # encode failed; payload is an error message

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._process: QProcess | None = None
        self._job: Job | None = None
        self._duration_s: float = 0.0  # from ffprobe; used by M3 progress math

    def start(self, job: Job) -> None:
        """Probe the duration, then (on probe finish) start the encode."""
        self._job = job
        self._run_probe(job)

    def _run_probe(self, job: Job) -> None:
        self._process = QProcess(self)
        self._process.finished.connect(self._on_probe_finished)
        self._process.start(ffprobe_path(), build_probe_args(job.input_path))

    def _on_probe_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        output = bytes(self._process.readAllStandardOutput()).decode().strip()
        try:
            self._duration_s = float(output)
        except ValueError:
            self._duration_s = 0.0  # couldn't read duration; M3 falls back gracefully
        assert self._job is not None
        self._run_encode(self._job)

    def _run_encode(self, job: Job) -> None:
        self._process = QProcess(self)
        self._process.finished.connect(self._on_encode_finished)
        # TODO(M3): self._process.readyReadStandardOutput.connect(self._on_ready_read)
        self._process.start(
            ffmpeg_path(), build_encode_args(job.input_path, job.output_path)
        )

    def _on_encode_finished(
        self, exit_code: int, status: QProcess.ExitStatus
    ) -> None:
        if exit_code == 0 and status == QProcess.ExitStatus.NormalExit:
            self.finished.emit()
        else:
            stderr = bytes(self._process.readAllStandardError()).decode()
            self.failed.emit(stderr or f"ffmpeg exited with code {exit_code}")

    # TODO(M3): _on_ready_read — parse out_time_ms (MICROSECONDS despite the
    #           name), buffer partial lines, emit progress(int) using _duration_s.
    # TODO(M7): cancel() — kill the process and delete the partial output.
