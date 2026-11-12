"""Finestra scena — pianta, vista 3D, montaggio, PDF, audio."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from teatro.audio_player import MusicPlayer
from teatro.cues import load_cues
from teatro.models import roman
from teatro.parts3d import PartsCache
from teatro.pdf_export import export_scene_pdf
from teatro.plan2d import ScenePlan2D
from teatro.scene_logic import (
    apply_effects_at_time,
    cue_text,
    describe_step,
    normalize_step,
    state_at,
    step_duration,
)
from teatro.shows import find_music_file
from teatro.stage3d import draw_stage_3d


class SceneWindow(QWidget):
    closed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.show_dir: Path | None = None
        self.sh: dict | None = None
        self.idx = 0
        self._on_dirty: Callable[[], None] | None = None
        self._player = MusicPlayer()
        self._cache = PartsCache()
        self._view3d = False
        self._step = 0
        self._running = False
        self._objs: list[dict] = []
        self._pos = np.zeros((0, 2))
        self._alpha = np.zeros(0)
        self._plan: ScenePlan2D | None = None
        self._anim_t0 = 0.0
        self._anim_eff: list[dict] = []
        self._anim_a0 = np.zeros(0)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
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
        stack = QStackedWidget()
        self.fig2 = Figure(figsize=(8, 5), facecolor=(0.08, 0.09, 0.11))
        self.ax2 = self.fig2.add_subplot(111)
        self.canvas2 = FigureCanvasQTAgg(self.fig2)
        self._plan = ScenePlan2D(self.ax2)
        self.fig3 = Figure(figsize=(8, 5), facecolor=(0, 0, 0))
        self.ax3 = self.fig3.add_subplot(111, projection="3d")
        self.canvas3 = FigureCanvasQTAgg(self.fig3)
        stack.addWidget(self.canvas2)
        stack.addWidget(self.canvas3)
        self._stack = stack
        body.addWidget(stack, stretch=4)

        side = QVBoxLayout()
        self.btn_view = QPushButton("Vista da pubblico")
        self.btn_view.setStyleSheet("font-weight:bold;")
        self.btn_view.clicked.connect(self._toggle_view)
        side.addWidget(self.btn_view)
        for label, slot in [
            ("▶▶ Montaggio", self._run_montaggio),
            ("Passo singolo", self._run_step),
            ("Ricomincia", self._reset),
            ("♪ Sync", self._sync),
            ("♪ Play", self._play_music),
            ("⏸ Pausa", self._pause_music),
            ("Salva PDF passi", self._pdf_scene),
        ]:
            b = QPushButton(label)
            b.clicked.connect(slot)
            side.addWidget(b)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.sliderReleased.connect(self._seek)
        side.addWidget(self.slider)
        self.time_lbl = QLabel("00:00 / --:--")
        side.addWidget(self.time_lbl)
        self.music_lbl = QLabel("")
        self.music_lbl.setWordWrap(True)
        self.music_lbl.setStyleSheet("font-size:10px;color:#b3aba0;")
        side.addWidget(self.music_lbl)
        side.addStretch()
        self.btn_show = QPushButton("Elenco scene")
        self.btn_show.clicked.connect(self._close_to_show)
        side.addWidget(self.btn_show)
        body.addLayout(side, 1)
        lay.addLayout(body)

        self.comment = QTextEdit()
        self.comment.setReadOnly(True)
        lay.addWidget(self.comment)

    def open(self, show_dir: Path, sh: dict, idx: int, on_dirty: Callable[[], None] | None = None) -> None:
        self.show_dir = show_dir
        self.sh = sh
        self.idx = idx
        self._on_dirty = on_dirty
        self.showMaximized()
        self.go_scene(idx)

    def _sc(self) -> dict:
        return self.sh["scenes"][self.idx]

    def go_scene(self, k: int) -> None:
        if not self.sh:
            return
        n = len(self.sh.get("scenes", []))
        if n == 0:
            return
        self._timer.stop()
        self._player.stop()
        k = max(0, min(k, n - 1))
        self.idx = k
        sc = self._sc()
        self.setWindowTitle(f"Scena — Atto {roman(int(sc.get('act', 1)))} · {sc.get('num', 0)} · {sc.get('title', '')}")
        self.title_lbl.setText(sc.get("title", "") or "(senza titolo)")
        self.sub_lbl.setText(f"Atto {sc.get('act', 1)} · Scena {sc.get('num', 0)} · {len(sc.get('steps', []))} passi")
        self._objs = list(sc.get("objects", []))
        self._pos = np.zeros((len(self._objs), 2))
        self._alpha = np.array([1.0 if o.get("start") else 0.0 for o in self._objs])
        self._step = 0
        self._cache.clear()
        self._draw()
        self._reset_comment()
        self._load_music(sc)

    def _draw(self) -> None:
        if not self.sh or not self.show_dir:
            return
        sc = self._sc()
        if self._view3d:
            draw_stage_3d(self.ax3, self.sh, sc, self.show_dir, self._pos, self._alpha, self._cache)
            self.canvas3.draw_idle()
        else:
            self._plan.draw(self.sh, sc, self._pos, self._alpha)
            self.canvas2.draw_idle()

    def _toggle_view(self) -> None:
        self._view3d = not self._view3d
        self.btn_view.setText("Vista dall'alto" if self._view3d else "Vista da pubblico")
        self._stack.setCurrentIndex(1 if self._view3d else 0)
        self._draw()

    def _reset(self) -> None:
        self._timer.stop()
        self._step = 0
        self._pos = np.zeros((len(self._objs), 2))
        self._alpha = np.array([1.0 if o.get("start") else 0.0 for o in self._objs])
        self._draw()
        self._reset_comment()

    def _reset_comment(self) -> None:
        sc = self._sc()
        start = sc.get("start") or "Inizio della scena."
        self.comment.setPlainText(f"0  {start}\n\nSync = canzone+passi; Montaggio = tutta la scena; Passo singolo = un passo alla volta.")

    def _run_montaggio(self) -> None:
        sc = self._sc()
        if self._step >= len(sc.get("steps", [])):
            self._reset()
        self._auto_chain = True
        self._run_step()

    def _run_step(self) -> None:
        sc = self._sc()
        steps = sc.get("steps", [])
        if self._step >= len(steps):
            self.comment.append("— Fine scena —")
            return
        self._step += 1
        eff = normalize_step(steps[self._step - 1])
        txt = [f"{self._step}  {cue_text(sc, self._step)}"]
        txt.extend(describe_step(self._objs, eff, self.sh["theater"]))
        self.comment.setPlainText("\n".join(txt))
        self._anim_eff = eff
        self._anim_a0 = self._alpha.copy()
        self._anim_t0 = time.monotonic()
        self._anim_duration = max(step_duration(eff), 0.4)
        self._running = True
        self._timer.start(33)

    def _on_tick(self) -> None:
        t = time.monotonic() - self._anim_t0
        apply_effects_at_time(self._objs, self._anim_eff, self._pos, self._alpha, self._anim_a0, t)
        self._draw()
        if t >= self._anim_duration:
            self._timer.stop()
            self._running = False
            if getattr(self, "_auto_chain", False):
                sc = self._sc()
                if self._step < len(sc.get("steps", [])):
                    QTimer.singleShot(400, self._run_step)
                else:
                    self._auto_chain = False

    def _sync(self) -> None:
        mp = self._music_path()
        if not mp or not self._player.load(mp):
            QMessageBox.warning(self, "Sync", "Carica prima la canzone della scena.")
            return
        self._reset()
        self._player.play()
        self._auto_chain = True
        self._run_step()

    def _music_path(self) -> Path | None:
        if not self.show_dir:
            return None
        return find_music_file(self.show_dir, int(self._sc().get("num", 0)))

    def _load_music(self, sc: dict) -> None:
        if not self.show_dir:
            return
        f = find_music_file(self.show_dir, int(sc.get("num", 0)))
        if f:
            self.music_lbl.setText(f.name)
            self._player.load(f)
            self.slider.setRange(0, max(1, int(self._player.duration * 1000)))
        else:
            self.music_lbl.setText(f"Manca audio/{sc.get('num', 0):02d}.*")

    def _play_music(self) -> None:
        self._player.play()

    def _pause_music(self) -> None:
        self._player.pause()

    def _seek(self) -> None:
        t = self.slider.value() / 1000.0
        self._player.seek(t)

    def _pdf_scene(self) -> None:
        if not self.show_dir or not self.sh:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Salva PDF", str(self.show_dir), "PDF (*.pdf)")
        if path:
            try:
                export_scene_pdf(Path(path), self.sh, self._sc(), self.show_dir)
                QMessageBox.information(self, "PDF", f"Salvato:\n{path}")
            except Exception as ex:
                QMessageBox.critical(self, "PDF", str(ex))

    def _close_to_show(self) -> None:
        self._timer.stop()
        self._player.stop()
        self.hide()
        self.closed.emit()

    def closeEvent(self, event) -> None:
        self._timer.stop()
        self._player.stop()
        self.closed.emit()
        super().closeEvent(event)
