#!/usr/bin/env python3
"""Avvio TeatroApp (port Python)."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from teatro.constants import libreria_dir
from teatro.ui.home_window import HomeWindow
from teatro.ui.styles import app_stylesheet


def main() -> int:
    if not (libreria_dir() / "catalogo.csv").is_file():
        print('Libreria non trovata: serve la cartella "libreria" accanto al programma.')
        return 1

    app = QApplication(sys.argv)
    app.setApplicationName("TeatroApp")
    app.setStyleSheet(app_stylesheet())
    win = HomeWindow()
    win.resize(900, 600)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
