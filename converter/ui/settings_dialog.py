"""Modal settings dialog: output folder and CRF quality (M8).

A QDialog runs its own event loop via exec(); it blocks the main window until
the user accepts or cancels. On accept we write the chosen values back into the
Settings store so they persist across launches.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from converter.settings import CRF_MAX, CRF_MIN, Settings


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        """Build the dialog pre-filled from the current settings."""
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("Settings")

        form = QFormLayout()
        form.addRow("Output folder:", self._build_output_row())
        form.addRow("Quality (CRF, lower = better):", self._build_crf_row())

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _build_output_row(self) -> QWidget:
        """Read-only path field with Browse/Clear; empty = next to source."""
        self._output_edit = QLineEdit(self._settings.output_dir)
        self._output_edit.setReadOnly(True)
        self._output_edit.setPlaceholderText("Same folder as each source file")

        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        clear = QPushButton("Clear")
        clear.clicked.connect(self._output_edit.clear)

        row = QHBoxLayout()
        row.addWidget(self._output_edit)
        row.addWidget(browse)
        row.addWidget(clear)
        container = QWidget()
        container.setLayout(row)
        return container

    def _build_crf_row(self) -> QWidget:
        """CRF slider with a live numeric label."""
        self._crf_slider = QSlider(Qt.Orientation.Horizontal)
        self._crf_slider.setRange(CRF_MIN, CRF_MAX)
        self._crf_slider.setValue(self._settings.crf)

        self._crf_value = QLabel(str(self._settings.crf))
        self._crf_slider.valueChanged.connect(
            lambda value: self._crf_value.setText(str(value))
        )

        row = QHBoxLayout()
        row.addWidget(self._crf_slider)
        row.addWidget(self._crf_value)
        container = QWidget()
        container.setLayout(row)
        return container

    def _browse(self) -> None:
        """Pick an output folder with the native directory chooser."""
        folder = QFileDialog.getExistingDirectory(
            self, "Choose output folder", self._output_edit.text()
        )
        if folder:
            self._output_edit.setText(folder)

    def accept(self) -> None:
        """Persist the chosen settings, then close the dialog."""
        self._settings.output_dir = self._output_edit.text()
        self._settings.crf = self._crf_slider.value()
        super().accept()
