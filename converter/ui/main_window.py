"""The main application window.

M1: an empty, titled window with a placeholder label.
M4: drag-and-drop adds files to a QTableWidget as Pending jobs.
M5: wire the table to a JobQueue so dropped files are converted in sequence.
"""

from pathlib import Path

from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from converter.ffmpeg_cmd import default_output_path
from converter.job import Job, JobStatus
from converter.queue import JobQueue
from converter.settings import Settings
from converter.ui.settings_dialog import SettingsDialog

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

# How many trailing stderr lines to show in the log pane when a job fails.
LOG_TAIL_LINES = 20


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        """Build the window and its drag-and-drop job table."""
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)
        self.setAcceptDrops(True)  # without this, drops are rejected by Qt

        self._jobs: list[Job] = []  # row i in the table corresponds to _jobs[i]
        self._settings = Settings()  # persisted output folder + CRF

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

        button_row = QHBoxLayout()
        self._start_button = QPushButton("Start Encoding")
        self._start_button.clicked.connect(self._on_start_encoding_clicked)
        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.clicked.connect(self._on_cancel_clicked)
        self._settings_button = QPushButton("Settings…")
        self._settings_button.clicked.connect(self._on_settings_clicked)
        button_row.addWidget(self._start_button)
        button_row.addWidget(self._cancel_button)
        button_row.addStretch()  # push Settings to the right
        button_row.addWidget(self._settings_button)
        layout.addLayout(button_row)

        # Collapsible error log: hidden until a job fails.
        self._log_toggle = QPushButton("Show log")
        self._log_toggle.setCheckable(True)
        self._log_toggle.toggled.connect(self._on_log_toggled)
        layout.addWidget(self._log_toggle)
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.hide()
        layout.addWidget(self._log)

        self.setCentralWidget(central_widget)

        self._update_buttons()  # Start disabled until a Pending job is added

    def _on_log_toggled(self, shown: bool) -> None:
        """Show or hide the error log pane and update the toggle label."""
        self._log.setVisible(shown)
        self._log_toggle.setText("Hide log" if shown else "Show log")

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

        output_path = default_output_path(path, self._settings.output_dir or None)
        job = Job(input_path=path, output_path=output_path, crf=self._settings.crf)
        self._jobs.append(job)
        self._append_row(job)
        self._queue.add(job)  # enqueue as Pending; Start button begins encoding
        self._update_buttons()

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
        if job.status == JobStatus.FAILED and job.error:
            self._append_log(job)
        self._update_buttons()

    def _append_log(self, job: Job) -> None:
        """Show the last few stderr lines for a failed job and reveal the log."""
        tail = "\n".join(job.error.strip().splitlines()[-LOG_TAIL_LINES:])
        name = Path(job.input_path).name
        self._log.appendPlainText(f"--- {name} failed ---\n{tail}\n")
        self._log_toggle.setChecked(True)  # reveals the pane via _on_log_toggled

    def _update_buttons(self) -> None:
        """Start enabled when a job is Pending and idle; Cancel only while encoding."""
        has_pending = any(j.status == JobStatus.PENDING for j in self._jobs)
        is_encoding = any(j.status == JobStatus.ENCODING for j in self._jobs)
        self._start_button.setEnabled(has_pending and not is_encoding)
        self._cancel_button.setEnabled(is_encoding)

    def _on_start_encoding_clicked(self) -> None:
        """Start processing the queued Pending jobs."""
        self._queue.start()

    def _on_cancel_clicked(self) -> None:
        """Cancel the job currently encoding."""
        self._queue.cancel()

    def _on_settings_clicked(self) -> None:
        """Open the modal settings dialog; new settings apply to future drops."""
        SettingsDialog(self._settings, self).exec()
