"""Tabella tempi passi (port openCueTable)."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from teatro.cues import fmt_time, load_cues, parse_time, save_cues
from teatro.scene_logic import cue_text, fill_cues


class CueTableDialog(QDialog):
    def __init__(self, parent, show_dir, sh: dict, idx: int, player, sync_from_cb) -> None:
        super().__init__(parent)
        self.show_dir = show_dir
        self.sh = sh
        self.idx = idx
        self._player = player
        self._sync_from = sync_from_cb
        sc = sh["scenes"][idx]
        self.setWindowTitle(f"Tempi dei passi — {sc.get('title', '')}")
        self.resize(820, 520)
        sc = self._sc()
        n = len(sc.get("steps", []))
        self.T, self.E = load_cues(show_dir, sc)
        self._sel = 0
        self._build(n)

    def _sc(self) -> dict:
        return self.sh["scenes"][self.idx]

    def _build(self, n: int) -> None:
        lay = QVBoxLayout(self)
        lay.addWidget(
            QLabel(
                "Tempi nel formato mm:ss.d (es. 01:12.4).  "
                "Seleziona una riga e usa i pulsanti per spostarla.\n"
                '"Fine" vuota = durata scritta nel passo.'
            )
        )
        self.table = QTableWidget(n, 4)
        self.table.setHorizontalHeaderLabels(["Passo", "Inizio", "Fine", "Descrizione"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self._on_sel)
        self.table.cellChanged.connect(self._cell_edit)
        self._refresh_table(block=True)
        lay.addWidget(self.table, stretch=1)
        row = QHBoxLayout()
        for label, d in [
            ("◀ 0,5 s", -0.5),
            ("◀ 0,1 s", -0.1),
            ("0,1 s ▶", +0.1),
            ("0,5 s ▶", +0.5),
        ]:
            b = QPushButton(label)
            b.clicked.connect(lambda checked=False, dd=d: self._nudge(dd))
            row.addWidget(b)
        b = QPushButton("▶ Ascolta da questo passo")
        b.clicked.connect(self._listen)
        row.addWidget(b)
        b = QPushButton("Riempi i vuoti")
        b.clicked.connect(self._fill_gaps)
        row.addWidget(b)
        lay.addLayout(row)
        row2 = QHBoxLayout()
        save = QPushButton("Salva")
        save.clicked.connect(self._save)
        row2.addWidget(save)
        close = QPushButton("Chiudi")
        close.clicked.connect(self.accept)
        row2.addWidget(close)
        row2.addStretch()
        self.status = QLabel("")
        row2.addWidget(self.status)
        lay.addLayout(row2)

    def _refresh_table(self, block: bool = False) -> None:
        sc = self._sc()
        n = len(sc.get("steps", []))
        if block:
            self.table.blockSignals(True)
        for k in range(n):
            self.table.setItem(k, 0, QTableWidgetItem(str(k + 1)))
            self.table.item(k, 0).setFlags(Qt.ItemFlag.ItemIsEnabled)
            for col, val in ((1, fmt_time(self.T[k])), (2, fmt_time(self.E[k]))):
                it = QTableWidgetItem(val)
                it.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(k, col, it)
            it = QTableWidgetItem(cue_text(sc, k + 1))
            it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(k, 3, it)
        if block:
            self.table.blockSignals(False)

    def _on_sel(self) -> None:
        rows = {ix.row() for ix in self.table.selectedIndexes()}
        if rows:
            self._sel = min(rows)

    def _cell_edit(self, row: int, col: int) -> None:
        if col not in (1, 2):
            return
        it = self.table.item(row, col)
        if not it:
            return
        v = parse_time(it.text())
        if col == 1:
            self.T[row] = v
        else:
            self.E[row] = v
        self.status.setText("Modificato (premi Salva)")

    def _nudge(self, d: float) -> None:
        if self._sel < 0 or self._sel >= len(self.T) or self.T[self._sel] != self.T[self._sel]:
            self.status.setText("Questo passo non ha ancora un tempo")
            return
        self.T[self._sel] = max(0.0, self.T[self._sel] + d)
        if self.E[self._sel] == self.E[self._sel]:
            self.E[self._sel] += d
        self._refresh_table(block=True)
        self.status.setText(f"Passo {self._sel + 1}  {fmt_time(self.T[self._sel])}  (premi Salva)")

    def _fill_gaps(self) -> None:
        dur = self._player.duration
        if dur <= 0:
            QMessageBox.warning(self, "Tempi", "Carica prima la canzone della scena.")
            return
        self.T = fill_cues(self.T, dur)
        self._refresh_table(block=True)
        self.status.setText("Passi senza tempo riempiti (premi Salva)")

    def _save(self) -> None:
        save_cues(self.show_dir, self._sc(), self.T, self.E)
        self.status.setText("Salvato")

    def _listen(self) -> None:
        self._save()
        self.accept()
        self._sync_from(self._sel + 1)
