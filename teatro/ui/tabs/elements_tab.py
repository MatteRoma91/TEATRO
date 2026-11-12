"""Scheda Scenografia."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from teatro.catalog import CatalogItem, read_catalog
from teatro.constants import libreria_dir
from teatro.models import new_element
from teatro.scene_edits import remove_from_scenes, unique_el_name, used_in_scenes
from teatro.ui.widgets import ColorButton
from teatro.ui.import_model import import_model_dialog


class ElementsTab(QWidget):
    def __init__(self, sh: dict, show_dir: Path | None = None, parent=None) -> None:
        super().__init__(parent)
        self.sh = sh
        self.show_dir = show_dir
        catalog = read_catalog(libreria_dir() / "catalogo.csv")
        self._lib_scen: list[CatalogItem] = [c for c in catalog if c.cat == "Scenografia"]
        self._cur = -1
        self._build()
        self._fill_list()

    def _build(self) -> None:
        lay = QHBoxLayout(self)
        col1 = QVBoxLayout()
        lay.addLayout(col1, stretch=1)
        col1.addWidget(QLabel("Elementi predefiniti"))
        self.cat_list = QListWidget()
        for c in self._lib_scen:
            self.cat_list.addItem(c.name)
        self.cat_list.itemDoubleClicked.connect(self._add_lib)
        col1.addWidget(self.cat_list)
        b = QPushButton("Aggiungi →")
        b.clicked.connect(self._add_lib)
        col1.addWidget(b)
        imp = QPushButton("Importa modello 3D…")
        imp.clicked.connect(self._add_import)
        col1.addWidget(imp)

        col2 = QVBoxLayout()
        lay.addLayout(col2, stretch=1)
        col2.addWidget(QLabel("Elementi dello spettacolo"))
        self.el_list = QListWidget()
        self.el_list.currentRowChanged.connect(self._show_el)
        col2.addWidget(self.el_list)
        row = QHBoxLayout()
        for label, fn in [("Duplica", self._dup), ("Elimina", self._del)]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            row.addWidget(b)
        col2.addLayout(row)

        col3 = QVBoxLayout()
        lay.addLayout(col3, stretch=2)
        form = QFormLayout()
        self.e_name = QLineEdit()
        self.e_name.editingFinished.connect(self._read_el)
        form.addRow("Nome", self.e_name)
        sz_row = QHBoxLayout()
        self.e_sx = self._spin(1)
        self.e_sy = self._spin(1)
        self.e_sz = self._spin(1)
        for sp in (self.e_sx, self.e_sy, self.e_sz):
            sp.valueChanged.connect(self._read_el)
        sz_row.addWidget(self.e_sx)
        sz_row.addWidget(self.e_sy)
        sz_row.addWidget(self.e_sz)
        form.addRow("L × P × H (m)", self._wrap(sz_row))
        self.e_color = ColorButton()
        self.e_color.color_changed.connect(self._pick_col)
        form.addRow("Colore", self.e_color)
        self.e_fixed = QCheckBox("Fisso: in tutte le scene, stesso punto")
        self.e_fixed.stateChanged.connect(self._read_el)
        form.addRow(self.e_fixed)
        pos_row = QHBoxLayout()
        self.e_x = self._spin(0)
        self.e_y = self._spin(0)
        self.e_rot = self._spin(0, 360)
        for sp in (self.e_x, self.e_y, self.e_rot):
            sp.valueChanged.connect(self._read_el)
        pos_row.addWidget(self.e_x)
        pos_row.addWidget(self.e_y)
        pos_row.addWidget(self.e_rot)
        form.addRow("X, Y (m), rotazione (°)", self._wrap(pos_row))
        col3.addLayout(form)
        self.e_occ = QPlainTextEdit()
        self.e_occ.setPlaceholderText("Occorrente…")
        self.e_occ.textChanged.connect(self._read_el)
        col3.addWidget(QLabel("Occorrente"))
        col3.addWidget(self.e_occ)
        self.e_how = QPlainTextEdit()
        self.e_how.setPlaceholderText("Come costruirlo…")
        self.e_how.textChanged.connect(self._read_el)
        col3.addWidget(QLabel("Come costruirlo"))
        col3.addWidget(self.e_how)
        col3.addWidget(QLabel("Anteprima 3D disponibile in finestra scena (vista platea)."))
        self._editors = [
            self.e_name,
            self.e_sx,
            self.e_sy,
            self.e_sz,
            self.e_x,
            self.e_y,
            self.e_rot,
            self.e_occ,
            self.e_how,
            self.e_fixed,
        ]

    def _wrap(self, lay: QHBoxLayout) -> QWidget:
        w = QWidget()
        w.setLayout(lay)
        return w

    def _spin(self, val: float, mx: float = 99) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(-mx, mx)
        s.setDecimals(2)
        s.setValue(float(val))
        return s

    def _fill_list(self) -> None:
        self.el_list.clear()
        els = self.sh.setdefault("elements", [])
        for e in els:
            fx = "  [fisso]" if e.get("fixed") else ""
            self.el_list.addItem(f"{e.get('name', '')}{fx}")
        if not els:
            self.el_list.addItem("(nessun elemento)")
        self._show_el(max(0, self._cur))

    def _cur_index(self) -> int:
        row = self.el_list.currentRow()
        els = self.sh.get("elements", [])
        if row < 0 or row >= len(els):
            return -1
        return row

    def _add_import(self) -> None:
        if not self.show_dir:
            QMessageBox.warning(self, "Import", "Cartella spettacolo non disponibile.")
            return
        r = import_model_dialog(self, self.show_dir)
        if not r:
            return
        fn, bb, nm = r
        e = new_element()
        e.update(name=unique_el_name(self.sh["elements"], nm), src="import", file=fn, size=list(bb), rgb=[0.6, 0.5, 0.4], tint=False)
        self.sh["elements"].append(e)
        self._cur = len(self.sh["elements"]) - 1
        self._fill_list()
        self.el_list.setCurrentRow(self._cur)

    def _add_lib(self) -> None:
        row = self.cat_list.currentRow()
        if row < 0:
            return
        c = self._lib_scen[row]
        nm = unique_el_name(self.sh["elements"], c.name)
        e = new_element()
        e.update(
            name=nm,
            src="lib",
            file=c.id,
            size=list(c.size),
            rgb=list(c.rgb),
            tint=bool(c.hex),
        )
        self.sh["elements"].append(e)
        self._cur = len(self.sh["elements"]) - 1
        self._fill_list()
        self.el_list.setCurrentRow(self._cur)

    def _dup(self) -> None:
        i = self._cur_index()
        if i < 0:
            return
        e = dict(self.sh["elements"][i])
        e["name"] = unique_el_name(self.sh["elements"], e.get("name", "Elemento"))
        self.sh["elements"].append(e)
        self._fill_list()
        self.el_list.setCurrentRow(len(self.sh["elements"]) - 1)

    def _del(self) -> None:
        i = self._cur_index()
        if i < 0:
            return
        nm = self.sh["elements"][i].get("name", "")
        if used_in_scenes(self.sh, "el", nm):
            ok = (
                QMessageBox.question(
                    self,
                    "Elimina",
                    f'"{nm}" è usato in alcune scene. Eliminarlo comunque?',
                )
                == QMessageBox.StandardButton.Yes
            )
            if not ok:
                return
            remove_from_scenes(self.sh, "el", nm)
        del self.sh["elements"][i]
        self._cur = -1
        self._fill_list()

    def _show_el(self, row: int) -> None:
        self._cur = row
        i = self._cur_index()
        on = i >= 0
        for w in self._editors:
            w.setEnabled(on)
        self.e_color.setEnabled(on)
        if not on:
            return
        e = self.sh["elements"][i]
        self.e_name.blockSignals(True)
        self.e_name.setText(e.get("name", ""))
        self.e_name.blockSignals(False)
        sz = e.get("size", [1, 1, 1])
        for sp, v in zip((self.e_sx, self.e_sy, self.e_sz), sz):
            sp.blockSignals(True)
            sp.setValue(float(v))
            sp.blockSignals(False)
        self.e_color.set_rgb(e.get("rgb", [0.6, 0.6, 0.6]))
        self.e_color.setEnabled(bool(e.get("tint", True)))
        self.e_fixed.blockSignals(True)
        self.e_fixed.setChecked(bool(e.get("fixed")))
        self.e_fixed.blockSignals(False)
        for sp, v in zip((self.e_x, self.e_y, self.e_rot), (e.get("x", 0), e.get("y", 0), e.get("rot", 0))):
            sp.blockSignals(True)
            sp.setValue(float(v))
            sp.blockSignals(False)
        en_pos = e.get("fixed", False)
        for sp in (self.e_x, self.e_y, self.e_rot):
            sp.setEnabled(en_pos)
        self.e_occ.blockSignals(True)
        self.e_occ.setPlainText(e.get("occ", ""))
        self.e_occ.blockSignals(False)
        self.e_how.blockSignals(True)
        self.e_how.setPlainText(e.get("how", ""))
        self.e_how.blockSignals(False)

    def _read_el(self) -> None:
        i = self._cur_index()
        if i < 0:
            return
        e = self.sh["elements"][i]
        old = e.get("name", "")
        nm = self.e_name.text().strip()
        names = {x.get("name") for j, x in enumerate(self.sh["elements"]) if j != i}
        if nm and nm not in names:
            if nm != old:
                from teatro.scene_edits import rename_in_scenes

                rename_in_scenes(self.sh, "el", old, nm)
            e["name"] = nm
        e["size"] = [self.e_sx.value(), self.e_sy.value(), self.e_sz.value()]
        e["fixed"] = self.e_fixed.isChecked()
        if e["fixed"]:
            e["x"] = self.e_x.value()
            e["y"] = self.e_y.value()
            e["rot"] = self.e_rot.value()
            T = self.sh["theater"]
            if e["y"] == 0 and e["x"] == 0:
                e["y"] = float(T["D"]) - e["size"][1] / 2 - 0.1
        e["occ"] = self.e_occ.toPlainText().strip()
        e["how"] = self.e_how.toPlainText().strip()
        self._fill_list()
        self.el_list.setCurrentRow(i)

    def _pick_col(self, rgb: list[float]) -> None:
        i = self._cur_index()
        if i < 0:
            return
        self.sh["elements"][i]["rgb"] = rgb
