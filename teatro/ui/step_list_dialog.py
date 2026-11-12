"""Elenco passi — modifica, ordina, prova."""

from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from pathlib import Path

from teatro.pdf_export import export_scene_pdf
from teatro.scene_commit import commit_scene, pad_cell
from teatro.scene_logic import act_summary, cue_text
from teatro.ui.step_editor_dialog import StepEditorDialog


class StepListDialog(QDialog):
    def __init__(self, parent, show_dir, sh: dict, idx: int, on_commit, try_step_cb) -> None:
        super().__init__(parent)
        self.show_dir = show_dir
        self.sh = sh
        self.idx = idx
        self._on_commit = on_commit
        self._try_step = try_step_cb
        sc = sh["scenes"][idx]
        self.setWindowTitle(f"Elenco passi — {sc.get('title', '')}")
        self.resize(720, 560)
        self._build()
        self._fill()

    def _sc(self) -> dict:
        return self.sh["scenes"][self.idx]

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Doppio clic su un passo per modificarlo."))
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self._edit)
        lay.addWidget(self.list, stretch=1)
        row = QHBoxLayout()
        for label, slot, bold in [
            ("+ Aggiungi passo", self._add, True),
            ("Modifica", self._edit, False),
            ("Elimina", self._delete, False),
            ("▲ Su", lambda: self._move(-1), False),
            ("▼ Giù", lambda: self._move(+1), False),
            ("▶ Prova il passo", self._try, False),
        ]:
            b = QPushButton(label)
            if bold:
                f = b.font()
                f.setBold(True)
                b.setFont(f)
            b.clicked.connect(slot)
            row.addWidget(b)
        lay.addLayout(row)
        row2 = QHBoxLayout()
        pdf = QPushButton("⎙ Salva PDF")
        pdf.setStyleSheet("font-weight:bold;")
        pdf.clicked.connect(self._pdf)
        row2.addWidget(pdf)
        row2.addStretch()
        close = QPushButton("Chiudi")
        close.clicked.connect(self.accept)
        row2.addWidget(close)
        lay.addLayout(row2)
        self.status = QLabel("")
        lay.addWidget(self.status)

    def _fill(self) -> None:
        sc = self._sc()
        self.list.clear()
        steps = sc.get("steps", [])
        for k in range(len(steps)):
            self.list.addItem(f"{k + 1:2d}.  {cue_text(sc, k + 1)}   [{act_summary(sc, k + 1)}]")
        if not steps:
            self.list.addItem("(nessun passo: premi \"+ Aggiungi passo\")")

    def _sel(self) -> int:
        row = self.list.currentRow()
        n = len(self._sc().get("steps", []))
        if row < 0 or row >= n:
            return 0
        return row + 1

    def _add(self) -> None:
        k = self._sel() + 1 if self._sel() else 1
        self._open_editor(k, True)

    def _edit(self) -> None:
        k = self._sel()
        if k < 1:
            return
        self._open_editor(k, False)

    def _open_editor(self, k: int, is_new: bool) -> None:
        dlg = StepEditorDialog(self, self.sh, self._sc(), k, is_new)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        if is_new:
            sc2 = dlg.result_scene()
            steps = list(sc2.get("steps", []))
            cues = pad_cell(sc2.get("cues", []), len(steps))
            ens = pad_cell(sc2.get("ens", []), len(steps))
            ins = k - 1
            steps.insert(ins, dlg.step_effects)
            cues.insert(ins, dlg.step_cue)
            ens.insert(ins, dlg.step_ens)
            sc2["steps"] = steps
            sc2["cues"] = cues
            sc2["ens"] = ens
        else:
            sc2 = dlg.result_scene()
            sc2["steps"][k - 1] = dlg.step_effects
            cues = pad_cell(sc2.get("cues", []), len(sc2["steps"]))
            ens = pad_cell(sc2.get("ens", []), len(sc2["steps"]))
            cues[k - 1] = dlg.step_cue
            ens[k - 1] = dlg.step_ens
            sc2["cues"] = cues
            sc2["ens"] = ens
        self.sh = commit_scene(self.sh, self.idx, sc2)
        self._on_commit(self.sh)
        self._fill()
        self.list.setCurrentRow(k - 1)
        self.status.setText(f"Passo {k} salvato.")

    def _delete(self) -> None:
        k = self._sel()
        if k < 1:
            return
        if QMessageBox.question(self, "Elimina", f"Eliminare il passo {k}?") != QMessageBox.StandardButton.Yes:
            return
        sc = copy.deepcopy(self._sc())
        n = len(sc.get("steps", []))
        sc["cues"] = pad_cell(sc.get("cues", []), n)
        sc["ens"] = pad_cell(sc.get("ens", []), n)
        del sc["steps"][k - 1]
        del sc["cues"][k - 1]
        del sc["ens"][k - 1]
        self.sh = commit_scene(self.sh, self.idx, sc)
        self._on_commit(self.sh)
        self._fill()
        self.status.setText(f"Passo {k} eliminato.")

    def _move(self, d: int) -> None:
        k = self._sel()
        if k < 1:
            return
        j = k + d - 1
        sc = copy.deepcopy(self._sc())
        n = len(sc.get("steps", []))
        if j < 0 or j >= n:
            return
        sc["cues"] = pad_cell(sc.get("cues", []), n)
        sc["ens"] = pad_cell(sc.get("ens", []), n)
        for key in ("steps", "cues", "ens"):
            lst = sc[key]
            lst[k - 1], lst[j] = lst[j], lst[k - 1]
        self.sh = commit_scene(self.sh, self.idx, sc)
        self._on_commit(self.sh)
        self._fill()
        self.list.setCurrentRow(j)

    def _try(self) -> None:
        k = self._sel()
        if k < 1:
            return
        self.accept()
        self._try_step(k)

    def _pdf(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Salva PDF", str(self.show_dir), "PDF (*.pdf)")
        if not path:
            return
        try:
            export_scene_pdf(Path(path), self.sh, self._sc(), self.show_dir)
            QMessageBox.information(self, "PDF", f"Salvato:\n{path}")
        except Exception as ex:
            QMessageBox.critical(self, "PDF", str(ex))
