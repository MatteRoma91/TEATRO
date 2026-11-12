"""Scheda Luci."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from teatro.constants import ZONES
from teatro.models import light_colours, light_library, new_light

class LightsTab(QWidget):
    def __init__(self, sh: dict, parent=None) -> None:
        super().__init__(parent)
        self.sh = sh
        self._col_names, self._col_values = light_colours()
        self._lib = light_library()
        self._sel_row = -1
        self._build()
        self._fill_table()

    def _build(self) -> None:
        lay = QHBoxLayout(self)
        left = QVBoxLayout()
        lay.addLayout(left, stretch=1)
        left.addWidget(QLabel("Libreria luci"))
        self.lib_list = QListWidget()
        for L in self._lib:
            self.lib_list.addItem(f"{L['type']}  —  {L['note']}")
        self.lib_list.itemDoubleClicked.connect(self._add_light)
        left.addWidget(self.lib_list)
        btn_add = QPushButton("Aggiungi →")
        btn_add.clicked.connect(self._add_light)
        left.addWidget(btn_add)

        right = QVBoxLayout()
        lay.addLayout(right, stretch=2)
        right.addWidget(QLabel("Luci di questo spettacolo"))
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Nome", "Tipo", "Qtà", "Colore", "Zona"])
        self.table.cellChanged.connect(self._cell_changed)
        self.table.cellClicked.connect(lambda r, c: setattr(self, "_sel_row", r))
        right.addWidget(self.table)
        row = QHBoxLayout()
        btn_rem = QPushButton("Rimuovi luce selezionata")
        btn_rem.clicked.connect(self._rem_light)
        row.addWidget(btn_rem)
        self.custom_color = QPushButton("Colore personalizzato…")
        self.custom_color.clicked.connect(self._custom_color)
        row.addWidget(self.custom_color)
        right.addLayout(row)
        right.addWidget(
            QLabel(
                "«Segue un personaggio» = occhio di bue. Le altre zone sono luci generali "
                "(nei passi scegli quali restano accese)."
            )
        )

    def _fill_table(self) -> None:
        self.table.blockSignals(True)
        lights = self.sh.setdefault("lights", [])
        self.table.setRowCount(len(lights))
        for r, L in enumerate(lights):
            self._set_row(r, L)
        self.table.blockSignals(False)

    def _set_row(self, r: int, L: dict) -> None:
        self.table.setItem(r, 0, QTableWidgetItem(L.get("name", "")))
        self.table.setItem(r, 1, QTableWidgetItem(L.get("type", "")))
        qi = QTableWidgetItem(str(int(L.get("qty", 1))))
        qi.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(r, 2, qi)
        self.table.setItem(r, 3, QTableWidgetItem(L.get("cname", "Bianco")))
        self.table.setItem(r, 4, QTableWidgetItem(L.get("zone", ZONES[0])))
        for c in (1,):
            it = self.table.item(r, c)
            if it:
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)

    def _add_light(self) -> None:
        row = self.lib_list.currentRow()
        if row < 0:
            row = 0
        L = self._lib[row]
        ci = L["col"]
        if ci not in self._col_names:
            ci = self._col_names[0]
        idx = self._col_names.index(ci)
        nm = L["type"]
        k = 2
        names = {x.get("name") for x in self.sh["lights"]}
        while nm in names:
            nm = f"{L['type']} {k}"
            k += 1
        self.sh["lights"].append(
            new_light(nm, L["type"], L["qty"], ci, self._col_values[idx], L["zone"])
        )
        self._fill_table()

    def _cell_changed(self, r: int, c: int) -> None:
        lights = self.sh.get("lights", [])
        if r >= len(lights):
            return
        L = lights[r]
        item = self.table.item(r, c)
        if not item:
            return
        val = item.text()
        if c == 0:
            nm = val.strip()
            others = {lights[i].get("name") for i in range(len(lights)) if i != r}
            if nm and nm not in others:
                L["name"] = nm
            else:
                self._set_row(r, L)
        elif c == 2:
            try:
                L["qty"] = max(0, int(float(val)))
            except ValueError:
                pass
            self._set_row(r, L)
        elif c == 3:
            L["cname"] = val
            if val in self._col_names:
                L["rgb"] = self._col_values[self._col_names.index(val)]
            elif val == "Personalizzato":
                pass
            self._set_row(r, L)
        elif c == 4:
            if val in ZONES:
                L["zone"] = val
            else:
                self._set_row(r, L)

    def _rem_light(self) -> None:
        r = self._sel_row
        if 0 <= r < len(self.sh.get("lights", [])):
            del self.sh["lights"][r]
            self._sel_row = -1
            self._fill_table()

    def _custom_color(self) -> None:
        r = self._sel_row
        if r < 0 or r >= len(self.sh.get("lights", [])):
            return
        L = self.sh["lights"][r]
        rgb = L.get("rgb", [1, 1, 1])
        c = QColorDialog.getColor(QColor(*(int(255 * x) for x in rgb[:3])), self, "Colore della luce")
        if c.isValid():
            L["rgb"] = [c.redF(), c.greenF(), c.blueF()]
            L["cname"] = "Personalizzato"
            self._set_row(r, L)
