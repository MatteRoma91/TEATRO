"""Finestra scena — pianta palco, passi, audio base."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from teatro.audio_player import MusicPlayer
from teatro.models import roman
from teatro.shows import find_music_file
from teatro.theater import draw_stage_plan, plot_objects_on_plan


class SceneWindow(QWidget):
    closed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.show_dir: Path | None = None
        self.sh: dict | None = None
        self.idx = 0
        self._on_dirty: Callable[[], None] | None = None
        self._player = MusicPlayer()
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.btn_prev = QPushButton("◀")
        self.btn_prev.clicked.connect(lambda: self.go_scene(self.idx - 1))
        top.addWidget(self.btn_prev)
        self.title_lbl = QLabel("")
        self.title_lbl.setStyleSheet("font-size:17px;font-weight:bold;color:#d4b059;")
        top.addWidget(self.title_lbl, stretch=1)
        self.btn_next = QPushButton("▶")
        self.btn_next.clicked.connect(lambda: self.go_scene(self.idx + 1))
        top.addWidget(self.btn_next)
        lay.addLayout(top)

        self.sub_lbl = QLabel("")
        self.sub_lbl.setStyleSheet("color:#b3aba0;")
        lay.addWidget(self.sub_lbl)

        body = QHBoxLayout()
        self.fig = Figure(figsize=(8, 5), facecolor=(0.08, 0.09, 0.11))
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasQTAgg(self.fig)
        body.addWidget(self.canvas, stretch=4)

        side = QVBoxLayout()
        self.btn_play = QPushButton("♪ Play")
        self.btn_play.clicked.connect(self._play_music)
        side.addWidget(self.btn_play)
        self.btn_pause = QPushButton("⏸ Pausa")
        self.btn_pause.clicked.connect(self._pause_music)
        side.addWidget(self.btn_pause)
        self.music_lbl = QLabel("")
        self.music_lbl.setWordWrap(True)
        self.music_lbl.setStyleSheet("font-size:10px;color:#b3aba0;")
        side.addWidget(self.music_lbl)
        side.addStretch()
        self.btn_show = QPushButton("Elenco scene")
        self.btn_show.clicked.connect(self._close_to_show)
        side.addWidget(self.btn_show)
        body.addLayout(side, stretch=1)
        lay.addLayout(body)

        self.comment = QTextEdit()
        self.comment.setReadOnly(True)
        self.comment.setPlaceholderText("Passi della scena…")
        lay.addWidget(self.comment)

    def open(
        self,
        show_dir: Path,
        sh: dict,
        idx: int,
        on_dirty: Callable[[], None] | None = None,
    ) -> None:
        self.show_dir = show_dir
        self.sh = sh
        self.idx = idx
        self._on_dirty = on_dirty
        self.showMaximized()
        self.go_scene(idx)

    def go_scene(self, k: int) -> None:
        if not self.sh:
            return
        n = len(self.sh.get("scenes", []))
        if n == 0:
            return
        k = max(0, min(k, n - 1))
        self.idx = k
        sc = self.sh["scenes"][k]
        self.setWindowTitle(
            f"Scena — Atto {roman(int(sc.get('act', 1)))} · {sc.get('num', 0)} · {sc.get('title', '')}"
        )
        self.title_lbl.setText(sc.get("title", "") or "(senza titolo)")
        self.sub_lbl.setText(
            f"Atto {sc.get('act', 1)}  ·  Scena {sc.get('num', 0)}  ·  {len(sc.get('steps', []))} passi"
        )
        self._draw_plan(sc)
        self._fill_steps(sc)
        self._load_music(sc)

    def _draw_plan(self, sc: dict) -> None:
        self.ax.clear()
        draw_stage_plan(self.ax, self.sh["theater"])
        plot_objects_on_plan(self.ax, sc.get("objects", []), self.sh.get("chars", []))
        self.canvas.draw_idle()

    def _fill_steps(self, sc: dict) -> None:
        lines = []
        for i, st in enumerate(sc.get("steps", []), start=1):
            if isinstance(st, dict):
                txt = st.get("text") or st.get("cue") or str(st)
            else:
                txt = str(st)
            lines.append(f"{i}. {txt}")
        if sc.get("start"):
            lines.insert(0, f"Situazione iniziale: {sc['start']}")
        self.comment.setPlainText("\n".join(lines) if lines else "(Nessun passo — da implementare montaggio completo)")

    def _load_music(self, sc: dict) -> None:
        if not self.show_dir:
            return
        f = find_music_file(self.show_dir, int(sc.get("num", 0)))
        if f:
            self.music_lbl.setText(f.name)
            self._player.load(f)
        else:
            self.music_lbl.setText(f"Nessun file {sc.get('num', 0):02d}.* in audio/")

    def _play_music(self) -> None:
        self._player.play()

    def _pause_music(self) -> None:
        self._player.pause()

    def _close_to_show(self) -> None:
        self._player.stop()
        self.hide()
        self.closed.emit()

    def closeEvent(self, event) -> None:
        self._player.stop()
        self.closed.emit()
        super().closeEvent(event)
