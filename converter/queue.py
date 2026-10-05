"""Manages the list of jobs and runs them one at a time (M5).

Holds the jobs, owns a single JobRunner, and starts the next Pending job when
the current one finishes. Only one encode runs at a time.

JobQueue is the authoritative owner of job state: it mutates each Job's status
and progress, then emits job_changed(job) so the UI can re-render that row. The
UI never changes job state itself.

Note: this module is named `queue` but lives inside the `converter` package, so
`import queue` elsewhere still resolves to the standard library module.
"""

from PySide6.QtCore import QObject, Signal

from converter.job import Job, JobStatus
from converter.runner import JobRunner


class JobQueue(QObject):
    # Emitted whenever a job's status or progress changes. Payload is the Job.
    job_changed = Signal(object)

    def __init__(
        self, runner: JobRunner | None = None, parent: QObject | None = None
    ) -> None:
        """Create the queue and wire it to a runner (injectable for tests)."""
        super().__init__(parent)
        self._jobs: list[Job] = []
        self._current: Job | None = None
        self._runner = runner if runner is not None else JobRunner(self)
        self._runner.progress.connect(self._on_progress)
        self._runner.finished.connect(self._on_finished)
        self._runner.failed.connect(self._on_failed)

    def add(self, job: Job) -> None:
        """Enqueue a job; start it now if nothing is currently encoding."""
        self._jobs.append(job)
        self._start_next_if_idle()

    def _start_next_if_idle(self) -> None:
        """Begin the first Pending job, unless one is already encoding."""
        if self._current is not None:
            return  # busy; the running job starts the next one when it finishes
        next_job = self._next_pending()
        if next_job is None:
            return  # queue drained
        self._current = next_job
        next_job.status = JobStatus.ENCODING
        self.job_changed.emit(next_job)
        self._runner.start(next_job)

    def _next_pending(self) -> Job | None:
        """Return the first job still waiting to encode, or None."""
        for job in self._jobs:
            if job.status == JobStatus.PENDING:
                return job
        return None

    def _on_progress(self, percent: int) -> None:
        """Record encode progress on the current job and notify the UI."""
        if self._current is None:
            return
        self._current.progress = percent
        self.job_changed.emit(self._current)

    def _on_finished(self) -> None:
        """Mark the current job Done, then advance to the next Pending one."""
        assert self._current is not None
        self._current.status = JobStatus.DONE
        self._current.progress = 100
        self.job_changed.emit(self._current)
        self._current = None
        self._start_next_if_idle()

    def _on_failed(self, message: str) -> None:
        """Mark the current job Failed, then advance to the next Pending one."""
        assert self._current is not None
        self._current.status = JobStatus.FAILED
        self.job_changed.emit(self._current)
        self._current = None
        self._start_next_if_idle()
