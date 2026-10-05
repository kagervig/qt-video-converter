"""The main application window.

M1: an empty, titled window with a placeholder label.
M4: drag-and-drop adds files to a QTableWidget as Pending jobs.
M5: wire the table to a JobQueue so dropped files are converted in sequence.
"""

from pathlib import Path

from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QHeaderView,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from converter.job import Job
from converter.queue import JobQueue

WINDOW_TITLE = "H.264 Converter"
MIN_WIDTH = 600
MIN_HEIGHT = 400

# Video containers we accept; anything else dropped is ignored.
ACCEPTED_SUFFIXES = {".mp4", ".mov", ".mkv", ".m4v"}

# Table column order.
COL_FILE = 0
COL_STATUS = 1
COL_PROGRESS = 2
COLUMN_HEADERS = ["File", "Status", "Progress"]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        """Build the window and its drag-and-drop job table."""
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)
        self.setAcceptDrops(True)  # without this, drops are rejected by Qt

        self._jobs: list[Job] = []  # row i in the table corresponds to _jobs[i]

        # The queue owns job state; we just reflect its job_changed signal.
        self._queue = JobQueue(parent=self)
        self._queue.job_changed.connect(self._on_job_changed)

        self._table = QTableWidget(0, len(COLUMN_HEADERS))
        self._table.setHorizontalHeaderLabels(COLUMN_HEADERS)
        # Let the File column stretch to fill spare width; the rest stay snug.
        self._table.horizontalHeader().setSectionResizeMode(
            COL_FILE, QHeaderView.ResizeMode.Stretch
        )

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(self._table)
        self._start_button = QPushButton("start encoding")
        self._start_button.clicked.connect(self._on_start_encoding_clicked)
        layout.addWidget(self._start_button)
        self.setCentralWidget(central_widget)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept the drag only if it carries file paths."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """Add each dropped file that is a supported, not-yet-queued video."""
        for url in event.mimeData().urls():
            self._add_file(url.toLocalFile())
        event.acceptProposedAction()

    def _add_file(self, path: str) -> None:
        """Create a Pending Job for `path` and show it as a new table row."""
        if Path(path).suffix.lower() not in ACCEPTED_SUFFIXES:
            return  # ignore unsupported file types
        if any(job.input_path == path for job in self._jobs):
            return  # ignore duplicates already in the table

        job = Job(input_path=path)
        self._jobs.append(job)
        self._append_row(job)
        self._queue.add(job)  # may start encoding immediately if idle

    def _append_row(self, job: Job) -> None:
        """Render one Job as a table row: file name, status, progress bar."""
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(
            row, COL_FILE, QTableWidgetItem(Path(job.input_path).name)
        )
        self._table.setItem(row, COL_STATUS, QTableWidgetItem(job.status.value))

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(job.progress)
        self._table.setCellWidget(row, COL_PROGRESS, progress_bar)

    def _on_job_changed(self, job: Job) -> None:
        """Update the row for `job` when the queue reports a status/progress change."""
        for row, existing in enumerate(self._jobs):
            if existing is job:  # identity match; Job is mutable, don't use ==
                break
        else:
            return  # not a job we're displaying

        self._table.item(row, COL_STATUS).setText(job.status.value)
        self._table.cellWidget(row, COL_PROGRESS).setValue(job.progress)

    def _on_start_encoding_clicked(self) -> None:
        pass
