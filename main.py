#!/usr/bin/env python3
"""GloryDial Studio entry point."""

import sys

from PyQt6.QtWidgets import QApplication

from glorydial.ui.main_window import MainWindow, apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("GloryDial Studio")
    apply_theme(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
