"""Finestra iniziale — elenco spettacoli."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QInputDialog,
    QFileDialog,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from teatro.constants import spettacoli_dir
from teatro.shows import (
    create_show,
    delete_show,
    duplicate_show,
    export_zip,
    import_zip,
    list_shows,
    rename_show,
)
from teatro.ui.show_window import ShowWindow


class HomeWindow(QWidget):
    open_show = Signal(Path, object)  # show_dir, sh dict — gestito dal main

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Teatro  -  i miei spettacoli")
        self._show_win: ShowWindow | None = None
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        t = QLabel("I MIEI SPETTACOLI")
        t.setProperty("class", "title")
        t.setStyleSheet("font-size:20px;font-weight:bold;color:#d4b059;")
        lay.addWidget(t)
        hint = QLabel(
            "Doppio clic su uno spettacolo per aprirlo. Ogni spettacolo si salva nella cartella spettacoli/."
        )
        hint.setProperty("class", "hint")
        lay.addWidget(hint)

        body = QHBoxLayout()
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self._open_selected)
        body.addWidget(self.list, stretch=3)

        col = QVBoxLayout()
        for label, slot, bold in [
            ("+ Nuovo spettacolo", self._new_show, True),
            ("Apri", self._open_selected, False),
            ("Duplica", self._dup, False),
            ("Rinomina", self._rename, False),
            ("Elimina", self._del, False),
            ("Esporta .zip", self._export, False),
            ("Importa .zip", self._import, False),
            ("Apri cartella", self._open_folder, False),
        ]:
            b = QPushButton(label)
            if bold:
                f = b.font()
                f.setBold(True)
                b.setFont(f)
            b.clicked.connect(slot)
            col.addWidget(b)
        col.addStretch()
        body.addLayout(col, stretch=1)
        lay.addLayout(body)

        self.status = QLabel("")
        lay.addWidget(self.status)
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        self._entries = list_shows()
        for e in self._entries:
            self.list.addItem(f"{e.title}      ({e.n_scenes} scene, modificato {e.date})")
        if not self._entries:
            self.list.addItem("(nessuno spettacolo: premi «+ Nuovo spettacolo»)")

    def _sel_index(self) -> int:
        row = self.list.currentRow()
        if row < 0 or not self._entries or row >= len(self._entries):
            return -1
        return row

    def _new_show(self) -> None:
        title, ok = QInputDialog.getText(self, "Nuovo spettacolo", "Titolo dello spettacolo:")
        if not ok or not title.strip():
            return
        dd, sh = create_show(title.strip())
        self.refresh()
        self._open_path(dd)

    def _open_selected(self) -> None:
        i = self._sel_index()
        if i < 0:
            return
        self._open_path(self._entries[i].path)

    def _open_path(self, dd: Path) -> None:
        from teatro.shows import open_show_folder

        try:
            sh = open_show_folder(dd)
        except Exception as ex:
            QMessageBox.critical(self, "Teatro", f"Impossibile aprire: {ex}")
            return
        self.hide()
        if self._show_win is None:
            self._show_win = ShowWindow()
            self._show_win.back_home.connect(self._on_back)
        self._show_win.load(dd, sh)

    def _on_back(self) -> None:
        self.show()
        self.raise_()
        self.refresh()

    def _dup(self) -> None:
        i = self._sel_index()
        if i < 0:
            return
        duplicate_show(self._entries[i].path)
        self.refresh()
        self.status.setText("Spettacolo duplicato.")

    def _rename(self) -> None:
        i = self._sel_index()
        if i < 0:
            return
        e = self._entries[i]
        title, ok = QInputDialog.getText(self, "Rinomina", "Nuovo titolo:", text=e.title)
        if ok and title.strip():
            rename_show(e.path, title.strip())
            self.refresh()

    def _del(self) -> None:
        i = self._sel_index()
        if i < 0:
            return
        e = self._entries[i]
        if (
            QMessageBox.question(self, "Elimina", f"Eliminare «{e.title}»?") == QMessageBox.StandardButton.Yes
        ):
            delete_show(e.path)
            self.refresh()

    def _export(self) -> None:
        i = self._sel_index()
        if i < 0:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Esporta", f"{self._entries[i].folder}.zip", "Zip (*.zip)")
        if path:
            export_zip(self._entries[i].path, Path(path))
            self.status.setText("Esportato.")

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Importa", "", "Zip (*.zip)")
        if path:
            try:
                import_zip(Path(path))
                self.refresh()
            except Exception as ex:
                QMessageBox.critical(self, "Importa", str(ex))

    def _open_folder(self) -> None:
        d = str(spettacoli_dir())
        if sys.platform == "win32":
            subprocess.Popen(["explorer", d])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", d])
        else:
            subprocess.Popen(["xdg-open", d])
