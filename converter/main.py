"""Application entry point: `python -m converter.main`.

Creates the one QApplication, shows the MainWindow, and starts the event loop.
The event loop is Qt's central runtime: it waits for events (clicks, drops,
QProcess output, timers) and dispatches them to handlers. app.exec() runs it
until the last window closes.
"""

import sys

from PySide6.QtWidgets import QApplication

from converter.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
