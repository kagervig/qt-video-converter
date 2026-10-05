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

    def __init__(self) -> None:
        super().__init__()
        self.started: list[Job] = []

    def start(self, job: Job) -> None:
        self.started.append(job)


def test_adding_a_job_marks_it_encoding():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    job = Job(input_path="/a.mp4")

    queue.add(job)

    assert job.status == JobStatus.ENCODING


def test_adding_a_job_starts_the_runner():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    job = Job(input_path="/a.mp4")

    queue.add(job)

    assert runner.started == [job]


def test_second_job_waits_while_first_encodes():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    queue.add(Job(input_path="/a.mp4"))
    second = Job(input_path="/b.mp4")

    queue.add(second)

    assert second.status == JobStatus.PENDING


def test_finishing_marks_the_job_done():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    job = Job(input_path="/a.mp4")
    queue.add(job)

    runner.finished.emit()

    assert job.status == JobStatus.DONE


def test_finishing_starts_the_next_pending_job():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    first = Job(input_path="/a.mp4")
    second = Job(input_path="/b.mp4")
    queue.add(first)
    queue.add(second)

    runner.finished.emit()

    assert second.status == JobStatus.ENCODING


def test_failure_marks_the_job_failed():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    job = Job(input_path="/a.mp4")
    queue.add(job)

    runner.failed.emit("boom")

    assert job.status == JobStatus.FAILED


def test_failure_still_starts_the_next_job():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    first = Job(input_path="/a.mp4")
    second = Job(input_path="/b.mp4")
    queue.add(first)
    queue.add(second)

    runner.failed.emit("boom")

    assert second.status == JobStatus.ENCODING


def test_progress_updates_the_current_job():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    job = Job(input_path="/a.mp4")
    queue.add(job)

    runner.progress.emit(42)

    assert job.progress == 42


def test_job_added_mid_queue_is_processed_after_current():
    runner = FakeRunner()
    queue = JobQueue(runner=runner)
    queue.add(Job(input_path="/a.mp4"))  # starts encoding
    late = Job(input_path="/b.mp4")
    queue.add(late)  # appended while busy

    runner.finished.emit()  # first finishes -> late should start

    assert late.status == JobStatus.ENCODING
