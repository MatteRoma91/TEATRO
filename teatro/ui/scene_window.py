"""Finestra scena — pianta, vista 3D, montaggio, PDF, audio."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent
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
from teatro.cues import load_cues, save_cues
from teatro.models import roman
from teatro.scene_commit import commit_scene
from teatro.parts3d import PartsCache
from teatro.pdf_export import export_scene_pdf
from teatro.plan2d import ScenePlan2D
from teatro.scene_logic import (
    apply_effects_at_time,
    cue_text,
    describe_step,
    fast_forward_state,
    fill_cues,
    normalize_step,
    step_duration,
)
from teatro.ui.cue_table_dialog import CueTableDialog
from teatro.ui.scene_setup_dialog import SceneSetupDialog
from teatro.ui.step_list_dialog import StepListDialog
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
        self._sync_timer = QTimer(self)
        self._sync_timer.timeout.connect(self._on_sync_tick)
        self._cue_t = np.array([])
        self._cue_k0 = 1
        self._syncing = False
        self._recording = False
        self._rec_t: np.ndarray | None = None
        self._auto_chain = False
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
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
        bar = QHBoxLayout()
        for label, slot, bold in [
            ("Elenco passi", self._open_steps, True),
            ("Imposta scena", self._open_setup, False),
        ]:
            b = QPushButton(label)
            if bold:
                f = b.font()
                f.setBold(True)
                b.setFont(f)
            b.clicked.connect(slot)
            bar.addWidget(b)
        bar.addStretch()
        lay.addLayout(bar)
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
        self.btn_rec = QPushButton("● Registra")
        self.btn_rec.clicked.connect(self._toggle_record)
        side.addWidget(self.btn_rec)
        self.btn_cues = QPushButton("Tempi passi")
        self.btn_cues.clicked.connect(self._open_cues)
        side.addWidget(self.btn_cues)
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
        self._sync_timer.stop()
        self._syncing = False
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

    def _sync(self, k0: int = 1) -> None:
        if self._recording:
            self._stop_recording(True)
        mp = self._music_path()
        if not mp or not self._player.load(mp):
            QMessageBox.warning(self, "Sync", "Carica prima la canzone della scena.")
            return
        sc = self._sc()
        n = len(sc.get("steps", []))
        if n == 0:
            self._player.play()
            return
        self._reset()
        t, _e = load_cues(self.show_dir, sc)
        dur = self._player.duration
        if np.any(~np.isnan(t)):
            tk = fill_cues(t, dur)
            how = "tempi registrati"
        else:
            tk = fill_cues(np.full(n, np.nan), dur)
            how = "distribuiti in modo uniforme"
        k0 = max(1, min(k0, n))
        if k0 > 1:
            self._fast_forward(k0 - 1)
        t0 = 0.0 if k0 <= 1 else max(0.0, float(tk[k0 - 1]) - 3.0)
        self._player.seek(t0)
        self._player.play()
        self._syncing = True
        self._cue_t = tk
        self._cue_k0 = k0
        self._sync_step = k0
        self.comment.append(f"\nSync: {n} passi, {how}.")
        self._sync_timer.start(40)

    def _on_sync_tick(self) -> None:
        if not self._syncing:
            return
        sc = self._sc()
        n = len(sc.get("steps", []))
        if self._sync_step > n:
            self._sync_timer.stop()
            self._syncing = False
            return
        if self._running:
            return
        t = self._player.current_time
        if self._sync_step <= n and t >= self._cue_t[self._sync_step - 1]:
            self._auto_chain = False
            self._run_step()
            self._sync_step += 1
        if self._sync_step > n and not self._running:
            self._sync_timer.stop()
            self._syncing = False
        if not self._player.is_playing() and not self._running:
            self._sync_timer.stop()
            self._syncing = False

    def _fast_forward(self, m: int) -> None:
        sc = self._sc()
        pos, alpha = fast_forward_state(sc, m)
        self._pos = pos
        self._alpha = alpha
        self._step = m
        self._draw()

    def _toggle_record(self) -> None:
        if self._recording:
            self._stop_recording(True)
            return
        if self._running or self._syncing:
            return
        sc = self._sc()
        n = len(sc.get("steps", []))
        if n == 0:
            QMessageBox.information(self, "Registra", "Questa scena non ha passi da sincronizzare.")
            return
        mp = self._music_path()
        if not mp or not self._player.load(mp):
            QMessageBox.warning(self, "Registra", "Carica prima la canzone della scena.")
            return
        self._reset()
        t, e = load_cues(self.show_dir, sc)
        self._recording = True
        self._rec_t = np.full(n, np.nan)
        self._rec_e = e.copy() if e.size == n else np.full(n, np.nan)
        self.btn_rec.setText("■ Stop")
        self.btn_rec.setStyleSheet("color:#c02020;font-weight:bold;")
        self.comment.setPlainText(
            f"REGISTRAZIONE TEMPI — {sc.get('title','')}\n\n"
            "Premi la BARRA SPAZIATRICE quando deve partire ogni passo.\n"
            f"Passi da segnare: {n}.  Esc o Stop per terminare.\n\n"
            f"Prossimo: 1  {cue_text(sc, 1)}"
        )
        self._player.play()
        self._rec_watch = QTimer(self)
        self._rec_watch.timeout.connect(self._on_rec_poll)
        self._rec_watch.start(50)

    def _on_rec_poll(self) -> None:
        if not self._recording or self._rec_t is None:
            return
        sc = self._sc()
        n = len(sc.get("steps", []))
        done = int(np.sum(~np.isnan(self._rec_t)))
        if done > self._step and not self._running:
            self._run_step()
            if self._step < n:
                self.comment.append(f"\nProssimo: {self._step + 1}  {cue_text(sc, self._step + 1)}")
        if self._step >= n and not self._running:
            QTimer.singleShot(500, lambda: self._stop_recording(True))
        elif not self._player.is_playing() and not self._running and done == self._step:
            self._stop_recording(True)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self._recording and event.key() == Qt.Key.Key_Space:
            self._mark_cue()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape and self._recording:
            self._stop_recording(True)
            return
        super().keyPressEvent(event)

    def _mark_cue(self) -> None:
        if not self._recording or self._rec_t is None:
            return
        miss = np.where(np.isnan(self._rec_t))[0]
        if miss.size == 0:
            return
        k = int(miss[0])
        self._rec_t[k] = self._player.current_time

    def _stop_recording(self, save: bool) -> None:
        if not self._recording:
            return
        self._recording = False
        if hasattr(self, "_rec_watch"):
            self._rec_watch.stop()
        self._player.stop()
        self.btn_rec.setText("● Registra")
        self.btn_rec.setStyleSheet("")
        if save and self._rec_t is not None:
            done = int(np.sum(~np.isnan(self._rec_t)))
            if done > 0:
                save_cues(self.show_dir, self._sc(), self._rec_t, self._rec_e)
                self.comment.append(f"\nSalvati {done} tempi su {len(self._rec_t)}.")
                self.music_lbl.setText(self.music_lbl.text() + "  (tempi registrati)")

    def _open_setup(self) -> None:
        if not self.sh:
            return
        dlg = SceneSetupDialog(self, self.sh, self._sc(), self._apply_scene)
        dlg.exec()

    def _open_steps(self) -> None:
        if not self.show_dir or not self.sh:
            return
        dlg = StepListDialog(self, self.show_dir, self.sh, self.idx, self._apply_show, self._try_step_k)
        dlg.exec()

    def _open_cues(self) -> None:
        if not self.show_dir or not self.sh:
            return
        dlg = CueTableDialog(self, self.show_dir, self.sh, self.idx, self._player, lambda k: self._sync(k))
        dlg.exec()

    def _apply_scene(self, sc: dict) -> None:
        self.sh = commit_scene(self.sh, self.idx, sc)
        if self._on_dirty:
            self._on_dirty()
        self.go_scene(self.idx)

    def _apply_show(self, sh: dict) -> None:
        self.sh = sh
        if self._on_dirty:
            self._on_dirty()
        self.go_scene(self.idx)

    def _try_step_k(self, k: int) -> None:
        self._reset()
        self._fast_forward(k - 1)
        self._auto_chain = False
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
        if self._recording:
            self._stop_recording(True)
        self._timer.stop()
        self._sync_timer.stop()
        self._player.stop()
        self.hide()
        self.closed.emit()

    def closeEvent(self, event) -> None:
        if self._recording:
            self._stop_recording(True)
        self._timer.stop()
        self._sync_timer.stop()
        self._player.stop()
        self.closed.emit()
        super().closeEvent(event)
