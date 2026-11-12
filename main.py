#!/usr/bin/env python3
"""Avvio TeatroApp (port Python)."""

from __future__ import annotations

import sys
import traceback


def _fatal(msg: str, detail: str = "") -> int:
    """Messaggio visibile anche con build senza console (PyInstaller)."""
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance() or QApplication(sys.argv)
        body = msg
        if detail:
            body += "\n\n" + detail
        QMessageBox.critical(None, "TeatroApp", body)
    except Exception:
        print(msg, file=sys.stderr)
        if detail:
            print(detail, file=sys.stderr)
    return 1


def main() -> int:
    try:
        from teatro.constants import app_root, bundle_root, libreria_dir
        from teatro.ui.home_window import HomeWindow
        from teatro.ui.styles import app_stylesheet
        from PySide6.QtWidgets import QApplication
    except Exception:
        return _fatal(
            "Impossibile avviare TeatroApp (mancano componenti).",
            traceback.format_exc()[-1200:],
        )

    cat = libreria_dir() / "catalogo.csv"
    if not cat.is_file():
        return _fatal(
            "Libreria costumi/scenografia non trovata.",
            f"Cercato:\n{cat}\n\n"
            f"Cartella programma: {app_root()}\n"
            f"Risorse interne: {bundle_root()}\n\n"
            "Riestrai tutto lo zip: servono TeatroApp.exe e la cartella _internal.",
        )

    try:
        app = QApplication(sys.argv)
        app.setApplicationName("TeatroApp")
        app.setStyleSheet(app_stylesheet())
        win = HomeWindow()
        win.resize(900, 600)
        win.show()
        return app.exec()
    except Exception:
        return _fatal("Errore all'avvio di TeatroApp.", traceback.format_exc()[-1200:])


if __name__ == "__main__":
    raise SystemExit(main())
