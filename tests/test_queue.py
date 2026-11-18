"""Behaviour tests for JobQueue (M5).

The real JobRunner launches ffmpeg (a system boundary), so we inject a fake
runner whose signals we emit by hand to simulate encodes completing.
"""

from PySide6.QtCore import QCoreApplication, QObject, Signal

from converter.job import Job, JobStatus
from converter.queue import JobQueue

# QObject signals need an application instance to exist; a core app is enough.
_app = QCoreApplication.instance() or QCoreApplication([])


class FakeRunner(QObject):
    progress = Signal(int)
    finished = Signal()
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.started: list[Job] = []
        self.cancel_calls = 0

    def start(self, job: Job) -> None:
        self.started.append(job)

    def cancel(self) -> None:
        self.cancel_calls += 1


def test_adding_a_job_does_not_start_it():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    job = Job(input_path="/a.mp4")

    queue.add(job)

    assert job.status == JobStatus.PENDING
    assert runner.started == []


def test_starting_marks_the_first_job_encoding():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    job = Job(input_path="/a.mp4")
    queue.add(job)

    queue.start()

    assert job.status == JobStatus.ENCODING


def test_starting_runs_the_first_job():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    job = Job(input_path="/a.mp4")
    queue.add(job)

    queue.start()

    assert runner.started == [job]


def test_second_job_waits_while_first_encodes():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    queue.add(Job(input_path="/a.mp4"))
    second = Job(input_path="/b.mp4")
    queue.add(second)

    queue.start()

    assert second.status == JobStatus.PENDING


def test_finishing_marks_the_job_done():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    job = Job(input_path="/a.mp4")
    queue.add(job)
    queue.start()

    runner.finished.emit()

    assert job.status == JobStatus.DONE


def test_finishing_starts_the_next_pending_job():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    first = Job(input_path="/a.mp4")
    second = Job(input_path="/b.mp4")
    queue.add(first)
    queue.add(second)
    queue.start()

    runner.finished.emit()

    assert second.status == JobStatus.ENCODING


def test_failure_marks_the_job_failed():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    job = Job(input_path="/a.mp4")
    queue.add(job)
    queue.start()

    runner.failed.emit("boom")

    assert job.status == JobStatus.FAILED


def test_failure_still_starts_the_next_job():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    first = Job(input_path="/a.mp4")
    second = Job(input_path="/b.mp4")
    queue.add(first)
    queue.add(second)
    queue.start()

    runner.failed.emit("boom")

    assert second.status == JobStatus.ENCODING


def test_failure_records_the_error_on_the_job():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    job = Job(input_path="/a.mp4")
    queue.add(job)
    queue.start()

    runner.failed.emit("ffmpeg: boom")

    assert job.error == "ffmpeg: boom"


def test_cancel_requests_the_runner_to_cancel():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    job = Job(input_path="/a.mp4")
    queue.add(job)
    queue.start()

    queue.cancel()

    assert runner.cancel_calls == 1


def test_cancel_when_idle_does_nothing():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)

    queue.cancel()

    assert runner.cancel_calls == 0


def test_cancelling_marks_the_current_job_cancelled():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    job = Job(input_path="/a.mp4")
    queue.add(job)
    queue.start()

    runner.cancelled.emit()

    assert job.status == JobStatus.CANCELLED


def test_cancelling_does_not_start_the_next_job():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    first = Job(input_path="/a.mp4")
    second = Job(input_path="/b.mp4")
    queue.add(first)
    queue.add(second)
    queue.start()

    runner.cancelled.emit()

    assert second.status == JobStatus.PENDING


def test_progress_updates_the_current_job():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    job = Job(input_path="/a.mp4")
    queue.add(job)
    queue.start()

    runner.progress.emit(42)

    assert job.progress == 42


def test_job_added_mid_queue_is_processed_after_current():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    queue.add(Job(input_path="/a.mp4"))
    queue.start()  # first starts encoding
    late = Job(input_path="/b.mp4")
    queue.add(late)  # appended while busy

    runner.finished.emit()  # first finishes -> late should start

    assert late.status == JobStatus.ENCODING
