"""Manages the list of jobs and runs them one at a time. Built in M5.

Holds the pending jobs, owns a single JobRunner, and starts the next Pending
job when the current one finishes. Only one encode runs at a time.

Note: this module is named `queue` but lives inside the `converter` package, so
`import queue` elsewhere still resolves to the standard library module.
"""

from PySide6.QtCore import QObject, Signal

from converter.job import Job


class JobQueue(QObject):
    # TODO(M5): signals for the UI, e.g. job_changed(Job) so the table can
    #           refresh a row's status/progress.
    job_changed = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._jobs: list[Job] = []
        # TODO(M5): create one JobRunner; connect its finished/failed/progress
        #           signals to slots that update the current job and advance.

    def add(self, job: Job) -> None:
        """Append a job; start processing if nothing is currently running."""
        self._jobs.append(job)
        raise NotImplementedError("M5: enqueue + kick off processing if idle")

    # TODO(M5): def _start_next(self) -> None: find the first PENDING job, set
    #           it ENCODING, and hand it to the runner. If none, go idle.
