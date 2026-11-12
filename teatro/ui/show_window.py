"""Finestra spettacolo — elenco scene."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QInputDialog,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from teatro.pdf_export import export_full_script

from teatro.mat_io import save_show
from teatro.models import new_scene, roman
from teatro.shows import find_music_file
from teatro.ui.scene_window import SceneWindow
from teatro.ui.settings_dialog import SettingsDialog


class ShowWindow(QWidget):
    back_home = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.show_dir: Path | None = None
        self.sh: dict | None = None
        self._scene_win: SceneWindow | None = None
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        self.title_lbl = QLabel("")
        self.title_lbl.setStyleSheet("font-size:20px;font-weight:bold;color:#d4b059;")
        lay.addWidget(self.title_lbl)
        self.info_lbl = QLabel("")
        self.info_lbl.setStyleSheet("color:#b3aba0;font-size:11px;")
        lay.addWidget(self.info_lbl)

        tools = QHBoxLayout()
        for name, slot in [
            ("Teatro", lambda: self._settings(0)),
            ("Luci", lambda: self._settings(1)),
            ("Scenografia", lambda: self._settings(2)),
            ("Personaggi", lambda: self._settings(3)),
            ("Cartella canzoni", self._open_audio),
        ]:
            b = QPushButton(name)
            b.clicked.connect(slot)
            tools.addWidget(b)
        lay.addLayout(tools)

        lay.addWidget(QLabel("SCENE  (doppio clic per aprire)"))
        body = QHBoxLayout()
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self._open_scene)
        body.addWidget(self.list, 3)

        col = QVBoxLayout()
        for label, slot, bold in [
            ("+ Nuova scena", self._new_scene, True),
            ("▶ Apri scena", self._open_scene, True),
            ("Titolo / atto / numero", self._edit_scene, False),
            ("Elimina scena", self._del_scene, False),
            ("Stampa copione PDF", self._print_script, False),
            ("Salva", self._save, False),
            ("◀ I miei spettacoli", self._back, False),
        ]:
            b = QPushButton(label)
            if bold:
                f = b.font()
                f.setBold(True)
                b.setFont(f)
            b.clicked.connect(slot)
            col.addWidget(b)
        col.addStretch()
        body.addLayout(col, 1)
        lay.addLayout(body)
        self.status = QLabel("")
        lay.addWidget(self.status)

    def load(self, show_dir: Path, sh: dict) -> None:
        self.show_dir = show_dir
        self.sh = sh
        self.setWindowTitle(f"Spettacolo  -  {sh['title']}")
        self.showMaximized()
        self._refresh()

    def _refresh(self) -> None:
        sh = self.sh
        if not sh:
            return
        self.title_lbl.setText(sh["title"])
        t = sh["theater"]
        self.info_lbl.setText(
            f"Palco {t['W']} x {t['D']} m, altezza {t['H']} m, {t['nq']} quinte   |   "
            f"{len(sh.get('chars', []))} personaggi   |   {len(sh.get('elements', []))} elementi   |   "
            f"{len(sh.get('lights', []))} luci"
        )
        self.list.clear()
        scenes = sh.get("scenes", [])
        self._sort_scenes()
        for sc in scenes:
            mf = find_music_file(self.show_dir, int(sc.get("num", 0))) if self.show_dir else None
            mk = "♪" if mf else f"(manca {sc.get('num', 0):02d}.mp3)"
            nsteps = len(sc.get("steps", []))
            self.list.addItem(
                f"Atto {roman(int(sc.get('act', 1))):<4} Scena {int(sc.get('num', 0)):2d}   "
                f"{sc.get('title', ''):<36} {nsteps:3d} passi  {mk}"
            )
        if not scenes:
            self.list.addItem("(nessuna scena)")

    def _sort_scenes(self) -> None:
        scenes = self.sh.get("scenes", [])
        scenes.sort(key=lambda s: (int(s.get("act", 1)), int(s.get("num", 0))))
        self.sh["scenes"] = scenes

    def _scene_index(self) -> int:
        row = self.list.currentRow()
        scenes = self.sh.get("scenes", []) if self.sh else []
        if row < 0 or row >= len(scenes):
            return -1
        return row

    def _new_scene(self) -> None:
        act, num = 1, 1
        scenes = self.sh.get("scenes", [])
        if scenes:
            act = int(scenes[-1].get("act", 1))
            num = int(scenes[-1].get("num", 0)) + 1
        act_s, ok1 = QInputDialog.getText(self, "Nuova scena", "Atto:", text=str(act))
        num_s, ok2 = QInputDialog.getText(self, "Nuova scena", "Numero scena (0=intro):", text=str(num))
        title, ok3 = QInputDialog.getText(self, "Nuova scena", "Titolo:")
        if not (ok1 and ok2 and ok3):
            return
        self.sh["nextId"] = int(self.sh.get("nextId", 0)) + 1
        uid = self.sh["nextId"]
        sc = new_scene(uid, int(act_s or act), int(num_s or num), title.strip(), "")
        self.sh.setdefault("scenes", []).append(sc)
        self._save()
        self._refresh()

    def _open_scene(self) -> None:
        i = self._scene_index()
        if i < 0:
            return
        if self._scene_win is None:
            self._scene_win = SceneWindow()
            self._scene_win.closed.connect(self._on_scene_closed)
        self.hide()
        self._scene_win.open(self.show_dir, self.sh, i, on_dirty=self._on_dirty)

    def _on_scene_closed(self) -> None:
        self.show()
        self._refresh()

    def _on_dirty(self) -> None:
        if self.show_dir and self.sh:
            save_show(self.show_dir, self.sh)

    def _edit_scene(self) -> None:
        i = self._scene_index()
        if i < 0:
            return
        sc = self.sh["scenes"][i]
        title, ok = QInputDialog.getText(self, "Modifica scena", "Titolo:", text=sc.get("title", ""))
        if ok:
            sc["title"] = title.strip()
            self._refresh()

    def _del_scene(self) -> None:
        i = self._scene_index()
        if i < 0:
            return
        if QMessageBox.question(self, "Elimina", "Eliminare questa scena?") == QMessageBox.StandardButton.Yes:
            del self.sh["scenes"][i]
            self._refresh()

    def _save(self) -> None:
        if self.show_dir and self.sh:
            save_show(self.show_dir, self.sh)
            self.status.setText(f"Salvato ({self.sh.get('modified', '')})")

    def _back(self) -> None:
        self._save()
        self.hide()
        self.back_home.emit()

    def _settings(self, tab: int) -> None:
        if not self.sh or not self.show_dir:
            return
        dlg = SettingsDialog(
            self,
            self.sh,
            show_dir=self.show_dir,
            tab=tab,
            on_save=lambda: save_show(self.show_dir, self.sh),
        )
        if dlg.exec():
            self._refresh()

    def _print_script(self) -> None:
        if not self.show_dir or not self.sh:
            return
        if not self.sh.get("scenes"):
            QMessageBox.warning(self, "Copione", "Lo spettacolo non ha scene.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salva copione PDF",
            str(self.show_dir / f"{self.sh.get('title', 'copione')}.pdf"),
            "PDF (*.pdf)",
        )
        if path:
            try:
                export_full_script(Path(path), self.sh, self.show_dir)
                QMessageBox.information(self, "Copione", f"PDF salvato:\n{path}")
            except Exception as ex:
                QMessageBox.critical(self, "Copione", str(ex))

    def _open_audio(self) -> None:
        if not self.show_dir:
            return
        d = str(self.show_dir / "audio")
        if sys.platform == "win32":
            subprocess.Popen(["explorer", d])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", d])
        else:
            subprocess.Popen(["xdg-open", d])
