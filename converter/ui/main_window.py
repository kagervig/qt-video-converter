"""The main application window.

M1: an empty, titled window with a placeholder label.
M2: a temporary "Convert test file" button that runs one hardcoded file through
    JobRunner and prints the result. Removed in M4.
M4: enable drops (setAcceptDrops) and show a QTableWidget of jobs.
M5: wire the table to a JobQueue.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from converter.job import Job
from converter.runner import JobRunner

WINDOW_TITLE = "H.264 Converter"
MIN_WIDTH = 600
MIN_HEIGHT = 400

# TODO(M2): point this at a real H.265 file to test, then remove in M4.
TEST_INPUT = ""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)

        central = QWidget()
        layout = QVBoxLayout(central)
        placeholder = QLabel("Drag video files here (coming in M4)")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(placeholder)

        # Temporary M2 test button (removed in M4).
        test_button = QPushButton("Convert test file")
        test_button.clicked.connect(self._convert_test_file)
        layout.addWidget(test_button)

        self.setCentralWidget(central)

        # Hold a reference to the runner: if we let it go out of scope, Python
        # would garbage-collect the QObject mid-encode. This is the classic
        # PySide lifetime gotcha.
        self._runner: JobRunner | None = None

        # TODO(M4): self.setAcceptDrops(True) and implement dragEnterEvent /
        #           dropEvent; replace the placeholder with a QTableWidget.

    def _convert_test_file(self) -> None:
        if not TEST_INPUT or not Path(TEST_INPUT).exists():
            print(f"Set TEST_INPUT to a real file first (got: {TEST_INPUT!r})")
            return

        job = Job(input_path=TEST_INPUT)
        self._runner = JobRunner(self)
        self._runner.finished.connect(lambda: print(f"Done: {job.output_path}"))
        self._runner.failed.connect(lambda msg: print(f"Failed: {msg}"))
        print(f"Encoding {job.input_path} -> {job.output_path}")
        self._runner.start(job)
