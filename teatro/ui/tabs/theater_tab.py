"""Scheda Teatro."""

from __future__ import annotations

import shutil
from pathlib import Path

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from teatro.constants import BACKDROP_OPTIONS, THEATER_PRESET_VALUES, THEATER_PRESETS
from teatro.theater import draw_stage_plan, fix_theater, quinte_step, quinte_width
from teatro.ui.import_model import import_model_dialog


class TheaterTab(QWidget):
    def __init__(self, sh: dict, show_dir: Path | None, parent=None) -> None:
        super().__init__(parent)
        self.sh = sh
        self.show_dir = show_dir
        self._build()

    def _build(self) -> None:
        root = QHBoxLayout(self)
        left = QVBoxLayout()
        root.addLayout(left, stretch=1)

        left.addWidget(QLabel("Il teatro"))
        self.preset = QComboBox()
        self.preset.addItems(THEATER_PRESETS)
        self.preset.currentIndexChanged.connect(self._apply_preset)
        left.addWidget(QLabel("Modello di partenza"))
        left.addWidget(self.preset)

        form = QFormLayout()
        t = fix_theater(self.sh["theater"])
        self.sp_w = self._spin(t["W"], 3, 40)
        self.sp_dtot = self._spin(t.get("Dtot", t["D"] + t["P"]), 4, 40)
        self.sp_h = self._spin(t["H"], 3, 25)
        self.sp_nq = self._spin(t["nq"], 0, 12, decimals=0)
        self.sp_p = self._spin(t["P"], 0.5, 5)
        for sp in (self.sp_w, self.sp_dtot, self.sp_h, self.sp_nq, self.sp_p):
            sp.valueChanged.connect(self._read_fields)
        form.addRow("Larghezza palco (m)", self.sp_w)
        form.addRow("Profondità totale, proscenio compreso (m)", self.sp_dtot)
        form.addRow("Altezza graticcio (m)", self.sp_h)
        form.addRow("Quinte per lato", self.sp_nq)
        form.addRow("Proscenio (m)", self.sp_p)
        left.addLayout(form)

        self.info = QLabel("")
        self.info.setStyleSheet("color:#ffcc77;font-size:11px;")
        self.info.setWordWrap(True)
        left.addWidget(self.info)

        left.addWidget(QLabel("Fondale"))
        self.back = QComboBox()
        self.back.addItems(BACKDROP_OPTIONS)
        cur = self.sh["theater"].get("back", "Nero")
        idx = self.back.findText(cur)
        self.back.setCurrentIndex(max(0, idx))
        self.back.currentTextChanged.connect(self._pick_back)
        left.addWidget(self.back)
        self.btn_file = QPushButton("Scegli il file…")
        self.btn_file.clicked.connect(self._choose_back)
        left.addWidget(self.btn_file)
        self.file_lbl = QLabel("")
        self.file_lbl.setStyleSheet("color:#b3aba0;font-size:10px;")
        left.addWidget(self.file_lbl)
        left.addStretch()

        self.fig = Figure(figsize=(5, 4), facecolor=(0.08, 0.09, 0.11))
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasQTAgg(self.fig)
        root.addWidget(self.canvas, stretch=1)
        self._read_fields()

    def _spin(self, val, lo, hi, decimals=2) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setDecimals(decimals)
        s.setValue(float(val))
        s.setSingleStep(0.1 if decimals else 1)
        return s

    def _apply_preset(self, idx: int) -> None:
        pv = THEATER_PRESET_VALUES[idx] if idx < len(THEATER_PRESET_VALUES) else None
        if not pv:
            return
        w, dtot, h, nq, p = pv
        self.sp_w.setValue(w)
        self.sp_dtot.setValue(dtot)
        self.sp_h.setValue(h)
        self.sp_nq.setValue(nq)
        self.sp_p.setValue(p)
        self._read_fields()

    def _read_fields(self) -> None:
        p = float(self.sp_p.value())
        dtot = float(self.sp_dtot.value())
        self.sh["theater"] = fix_theater(
            {
                **self.sh["theater"],
                "W": float(self.sp_w.value()),
                "Dtot": dtot,
                "D": dtot - p,
                "H": float(self.sp_h.value()),
                "nq": int(self.sp_nq.value()),
                "P": p,
            }
        )
        T = self.sh["theater"]
        self.info.setText(
            f"Calcolato: palco {T['D']:.2f} m + proscenio {T['P']:.2f} m.\n"
            f"{T['nq']} quinte, passo {quinte_step(T):.2f} m, larghe {quinte_width(T):.2f} m; "
            f"spazio dietro quinte {T['wing']:.2f} m."
        )
        self._update_back_ui()
        self._draw()

    def _pick_back(self, text: str) -> None:
        th = self.sh["theater"]
        if text == "Immagine (foto o disegno)" and not th.get("backImg"):
            if not self._choose_back(silent=False):
                self.back.blockSignals(True)
                self.back.setCurrentText(th.get("back", "Nero"))
                self.back.blockSignals(False)
                return
        elif text == "Modello 3D" and not th.get("backModel"):
            if self.show_dir and self._choose_back(silent=False):
                th["back"] = "Modello 3D"
            else:
                self.back.blockSignals(True)
                self.back.setCurrentText(th.get("back", "Nero"))
                self.back.blockSignals(False)
            return
        th["back"] = text
        self._update_back_ui()
        self._draw()

    def _choose_back(self, silent: bool = True) -> bool:
        th = self.sh["theater"]
        if th.get("back") == "Immagine (foto o disegno)":
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Immagine fondale",
                "",
                "Immagini (*.jpg *.jpeg *.png *.bmp *.tif)",
            )
            if not path:
                return False
            if not self.show_dir:
                QMessageBox.warning(self, "Fondale", "Cartella spettacolo non disponibile.")
                return False
            dest_dir = self.show_dir / "fondale"
            dest_dir.mkdir(exist_ok=True)
            src = Path(path)
            dst = dest_dir / src.name
            shutil.copy2(src, dst)
            th["backImg"] = src.name
            th["back"] = "Immagine (foto o disegno)"
            self.back.blockSignals(True)
            self.back.setCurrentText(th["back"])
            self.back.blockSignals(False)
            self._update_back_ui()
            self._draw()
            return True
        if th.get("back") == "Modello 3D" and self.show_dir:
            r = import_model_dialog(self, self.show_dir)
            if r:
                th["backModel"] = r[0]
                th["back"] = "Modello 3D"
                self.back.blockSignals(True)
                self.back.setCurrentText(th["back"])
                self.back.blockSignals(False)
                self._update_back_ui()
                self._draw()
                return True
        if not silent:
            QMessageBox.information(self, "Fondale", 'Scegli prima "Immagine" o "Modello 3D" come fondale.')
        return False

    def _update_back_ui(self) -> None:
        th = self.sh["theater"]
        is_file = th.get("back") in ("Immagine (foto o disegno)", "Modello 3D")
        self.btn_file.setEnabled(is_file)
        if th.get("back") == "Immagine (foto o disegno)":
            self.file_lbl.setText(f"Immagine: {th.get('backImg', '')}")
        elif th.get("back") == "Modello 3D":
            self.file_lbl.setText(f"Modello: {th.get('backModel', '')}")
        else:
            self.file_lbl.setText("")

    def _draw(self) -> None:
        self.ax.clear()
        draw_stage_plan(self.ax, self.sh["theater"], labels=True)
        self.ax.set_title("Pianta (pubblico in basso)", color=(0.83, 0.69, 0.35), fontsize=11)
        self.canvas.draw_idle()
