"""Scheda Personaggi e costumi."""

from __future__ import annotations

import copy
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from teatro.catalog import CatalogItem, read_catalog
from teatro.constants import (
    BROWS,
    EYES,
    MAKEUP,
    SKINS,
    SLOTS,
    SLOT_LABELS,
    libreria_dir,
)
from teatro.models import new_char, new_costume
from teatro.scene_edits import remove_from_scenes, rename_in_scenes
from teatro.ui.widgets import ColorButton
from teatro.ui.import_model import import_model_dialog


class CharsTab(QWidget):
    def __init__(self, sh: dict, show_dir: Path | None = None, parent=None) -> None:
        super().__init__(parent)
        self.sh = sh
        self.show_dir = show_dir
        self._catalog = read_catalog(libreria_dir() / "catalogo.csv")
        self._by_id = {c.id: c for c in self._catalog}
        self._slot_combos: list[QComboBox] = []
        self._slot_colors: list[ColorButton] = []
        self._mk_checks: list[QCheckBox] = []
        self._mk_colors: list[ColorButton] = []
        self._blocking = False
        self._build()
        self._fill_chars()

    def _build(self) -> None:
        lay = QHBoxLayout(self)
        left = QVBoxLayout()
        lay.addLayout(left, stretch=1)
        left.addWidget(QLabel("Personaggi"))
        self.char_list = QListWidget()
        self.char_list.currentRowChanged.connect(self._show_char)
        left.addWidget(self.char_list)
        for label, fn, bold in [
            ("+ Nuovo personaggio", self._add_char, True),
            ("Duplica", self._dup_char, False),
            ("Elimina", self._del_char, False),
        ]:
            b = QPushButton(label)
            if bold:
                b.setFont(b.font())
            b.clicked.connect(fn)
            left.addWidget(b)

        mid = QVBoxLayout()
        lay.addLayout(mid, stretch=2)
        row1 = QHBoxLayout()
        self.e_name = QLineEdit()
        self.e_name.editingFinished.connect(self._read_char)
        row1.addWidget(QLabel("Nome"))
        row1.addWidget(self.e_name)
        self.b_pawn = ColorButton([0.85, 0.15, 0.15], "Pedina")
        self.b_pawn.color_changed.connect(self._pawn_color)
        row1.addWidget(QLabel("Pedina"))
        row1.addWidget(self.b_pawn)
        self.p_sex = QComboBox()
        self.p_sex.addItems(["Uomo", "Donna"])
        self.p_sex.currentIndexChanged.connect(self._read_char)
        row1.addWidget(QLabel("Corpo"))
        row1.addWidget(self.p_sex)
        self.e_ht = QDoubleSpinBox()
        self.e_ht.setRange(0.5, 2.5)
        self.e_ht.setSingleStep(0.01)
        self.e_ht.valueChanged.connect(self._read_char)
        row1.addWidget(QLabel("Altezza (m)"))
        row1.addWidget(self.e_ht)
        mid.addLayout(row1)

        row2 = QHBoxLayout()
        self.p_skin = QComboBox()
        for name, _ in SKINS:
            self.p_skin.addItem(name)
        self.p_skin.addItem("Personalizzata…")
        self.p_skin.currentIndexChanged.connect(self._read_skin)
        row2.addWidget(QLabel("Pelle"))
        row2.addWidget(self.p_skin)
        self.b_skin = ColorButton()
        self.b_skin.setEnabled(False)
        row2.addWidget(self.b_skin)
        self.p_eyes = QComboBox()
        self.p_eyes.addItems([n for n, _ in EYES])
        self.p_eyes.currentIndexChanged.connect(self._read_char)
        row2.addWidget(QLabel("Occhi"))
        row2.addWidget(self.p_eyes)
        mid.addLayout(row2)

        mid.addWidget(QLabel("COSTUMI"))
        cos_row = QHBoxLayout()
        self.cos_list = QListWidget()
        self.cos_list.setMaximumHeight(120)
        self.cos_list.currentRowChanged.connect(self._show_costume)
        cos_row.addWidget(self.cos_list)
        ccol = QVBoxLayout()
        for label, fn in [
            ("+ Costume", self._add_costume),
            ("Duplica", self._dup_costume),
            ("Descrizione", self._desc_costume),
            ("Elimina", self._del_costume),
        ]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            ccol.addWidget(b)
        cos_row.addLayout(ccol)
        mid.addLayout(cos_row)

        mode_row = QHBoxLayout()
        self.p_mode = QComboBox()
        self.p_mode.addItems(["dalla libreria", "da modello importato"])
        self.p_mode.currentIndexChanged.connect(self._read_mode)
        mode_row.addWidget(QLabel("Il costume viene"))
        mode_row.addWidget(self.p_mode)
        self.btn_import = QPushButton("Importa modello 3D…")
        self.btn_import.clicked.connect(self._import_costume)
        mode_row.addWidget(self.btn_import)
        self.lbl_import = QLabel("")
        mid.addLayout(mode_row)
        mid.addWidget(self.lbl_import)

        grid = QGridLayout()
        mid.addWidget(QLabel("CAPI (colore con il quadratino)"))
        for q, slot in enumerate(SLOTS):
            grid.addWidget(QLabel(SLOT_LABELS[q]), q, 0)
            combo = QComboBox()
            items = self._items_for_cat(slot)
            combo.addItem("— nessuno —", "")
            for it in items:
                combo.addItem(it.name, it.id)
            combo.currentIndexChanged.connect(self._read_costume)
            self._slot_combos.append(combo)
            grid.addWidget(combo, q, 1)
            cb = ColorButton()
            cb.color_changed.connect(lambda rgb, qi=q: self._item_color(qi, rgb))
            self._slot_colors.append(cb)
            grid.addWidget(cb, q, 2)
        mid.addLayout(grid)

        mid.addWidget(QLabel("TRUCCO E PARRUCCO"))
        tr = QGridLayout()
        tr.addWidget(QLabel("Capelli"), 0, 0)
        self.p_hair = QComboBox()
        self.p_hair.addItem("Calvo / rasato", "")
        for it in self._items_for_cat("Capelli"):
            self.p_hair.addItem(it.name, it.id)
        self.p_hair.currentIndexChanged.connect(self._read_costume)
        tr.addWidget(self.p_hair, 0, 1)
        self.b_hair = ColorButton()
        self.b_hair.color_changed.connect(lambda rgb: self._mk_color("hairRGB", rgb))
        tr.addWidget(self.b_hair, 0, 2)
        tr.addWidget(QLabel("Barba / baffi"), 1, 0)
        self.p_face = QComboBox()
        self.p_face.addItem("Nessuna", "")
        for it in self._items_for_cat("Barba"):
            self.p_face.addItem(it.name, it.id)
        self.p_face.currentIndexChanged.connect(self._read_costume)
        tr.addWidget(self.p_face, 1, 1)
        self.b_face = ColorButton()
        self.b_face.color_changed.connect(lambda rgb: self._mk_color("facialRGB", rgb))
        tr.addWidget(self.b_face, 1, 2)
        tr.addWidget(QLabel("Sopracciglia"), 2, 0)
        self.p_brows = QComboBox()
        self.p_brows.addItems(list(BROWS))
        self.p_brows.currentIndexChanged.connect(self._read_costume)
        tr.addWidget(self.p_brows, 2, 1)
        self.b_brows = ColorButton()
        self.b_brows.color_changed.connect(lambda rgb: self._set_brows_rgb(rgb))
        tr.addWidget(self.b_brows, 2, 2)
        for qi, (key, label) in enumerate(MAKEUP):
            chk = QCheckBox(label)
            chk.stateChanged.connect(self._read_costume)
            self._mk_checks.append(chk)
            tr.addWidget(chk, 3 + qi, 0, 1, 2)
            cb = ColorButton()
            cb.color_changed.connect(lambda rgb, k=key: self._mk_color(k + "RGB", rgb, key))
            self._mk_colors.append(cb)
            tr.addWidget(cb, 3 + qi, 2)
        mid.addLayout(tr)

        right = QVBoxLayout()
        lay.addLayout(right, stretch=1)
        right.addWidget(QLabel("Anteprima 3D"))
        right.addWidget(
            QLabel(
                "Apri una scena e usa «Vista da pubblico» per l’anteprima 3D\n"
                "con corpo e costumi dalla libreria."
            )
        )
        right.addStretch()

    def _items_for_cat(self, cat: str) -> list[CatalogItem]:
        return [c for c in self._catalog if c.cat == cat]

    def _pi(self) -> int:
        r = self.char_list.currentRow()
        if r < 0 or r >= len(self.sh.get("chars", [])):
            return -1
        return r

    def _ci(self) -> int:
        p = self._pi()
        if p < 0:
            return -1
        r = self.cos_list.currentRow()
        costumes = self.sh["chars"][p].get("costumes", [])
        if r < 0 or r >= len(costumes):
            return -1 if not costumes else 0
        return r

    def _fill_chars(self) -> None:
        self.char_list.clear()
        for c in self.sh.get("chars", []):
            self.char_list.addItem(c.get("name", ""))
        if not self.sh.get("chars"):
            self.char_list.addItem("(nessun personaggio)")
        self._show_char(self.char_list.currentRow())

    def _add_char(self) -> None:
        name, ok = QInputDialog.getText(self, "Nuovo personaggio", "Nome:")
        if not ok or not name.strip():
            return
        sex, ok2 = QInputDialog.getText(self, "Nuovo personaggio", "Corpo (U/D):", text="U")
        if not ok2:
            return
        sx = "F" if sex.strip().upper().startswith("D") else "M"
        names = {c.get("name") for c in self.sh.get("chars", [])}
        if name.strip() in names:
            QMessageBox.warning(self, "Personaggi", "Nome già usato.")
            return
        self.sh.setdefault("chars", []).append(new_char(name.strip(), sx, len(self.sh["chars"]) + 1))
        self._fill_chars()
        self.char_list.setCurrentRow(len(self.sh["chars"]) - 1)

    def _dup_char(self) -> None:
        p = self._pi()
        if p < 0:
            return
        c = copy.deepcopy(self.sh["chars"][p])
        c["name"] = c["name"] + " 2"
        while c["name"] in {x.get("name") for x in self.sh["chars"]}:
            c["name"] += "+"
        c["rev"] = int(c.get("rev", 1)) + 1
        self.sh["chars"].append(c)
        self._fill_chars()
        self.char_list.setCurrentRow(len(self.sh["chars"]) - 1)

    def _del_char(self) -> None:
        p = self._pi()
        if p < 0:
            return
        nm = self.sh["chars"][p]["name"]
        if QMessageBox.question(self, "Elimina", f'Eliminare "{nm}" da tutte le scene?') != QMessageBox.StandardButton.Yes:
            return
        remove_from_scenes(self.sh, "char", nm)
        del self.sh["chars"][p]
        self._fill_chars()

    def _show_char(self, _row: int) -> None:
        p = self._pi()
        on = p >= 0
        for w in (
            self.e_name,
            self.b_pawn,
            self.p_sex,
            self.e_ht,
            self.p_skin,
            self.p_eyes,
            self.cos_list,
            self.p_mode,
        ):
            w.setEnabled(on)
        if not on:
            return
        c = self.sh["chars"][p]
        self._blocking = True
        self.e_name.setText(c.get("name", ""))
        self.b_pawn.set_rgb(c.get("pawn", [0.8, 0.2, 0.2]))
        self.p_sex.setCurrentIndex(1 if c.get("sex") == "F" else 0)
        self.e_ht.setValue(float(c.get("height", 1.78)))
        sk = c.get("skin", SKINS[1][1])
        self.b_skin.set_rgb(sk)
        found = False
        for i, (_, rgb) in enumerate(SKINS):
            if all(abs(a - b) < 0.02 for a, b in zip(rgb, sk)):
                self.p_skin.setCurrentIndex(i)
                found = True
                break
        if not found:
            self.p_skin.setCurrentIndex(len(SKINS))
        self.p_eyes.setCurrentIndex(self._nearest_eyes(c.get("eyes", EYES[0][1])))
        self.cos_list.clear()
        for co in c.get("costumes", []):
            self.cos_list.addItem(f"{co.get('code', '?')}  —  {co.get('desc', '')}")
        self._blocking = False
        self.cos_list.setCurrentRow(0)
        self._show_costume(0)

    def _nearest_eyes(self, rgb) -> int:
        best, bi = 1e9, 0
        for i, (_, er) in enumerate(EYES):
            d = sum((a - b) ** 2 for a, b in zip(rgb, er))
            if d < best:
                best, bi = d, i
        return bi

    def _show_costume(self, _row: int) -> None:
        p, j = self._pi(), self._ci()
        if p < 0 or j < 0:
            return
        co = self.sh["chars"][p]["costumes"][j]
        lib = co.get("mode", "lib") == "lib"
        self._blocking = True
        self.p_mode.setCurrentIndex(0 if lib else 1)
        self.btn_import.setEnabled(not lib)
        self.lbl_import.setText("" if lib else f"File: {co.get('file', '')}")
        for combo in self._slot_combos:
            combo.setEnabled(lib)
        for cb in self._slot_colors:
            cb.setEnabled(lib)
        self.p_hair.setEnabled(lib)
        self.b_hair.setEnabled(lib)
        self.p_face.setEnabled(lib)
        self.b_face.setEnabled(lib)
        self.p_brows.setEnabled(lib)
        self.b_brows.setEnabled(lib)
        for chk in self._mk_checks:
            chk.setEnabled(lib)
        for cb in self._mk_colors:
            cb.setEnabled(lib)
        items = co.get("items", [""] * 10)
        for qi, combo in enumerate(self._slot_combos):
            iid = items[qi] if qi < len(items) else ""
            idx = combo.findData(iid)
            combo.setCurrentIndex(max(0, idx))
            irgb = co.get("irgb", [[0.5, 0.5, 0.5]] * 10)
            self._slot_colors[qi].set_rgb(irgb[qi] if qi < len(irgb) else [0.5, 0.5, 0.5])
        hi = self.p_hair.findData(co.get("hair", ""))
        self.p_hair.setCurrentIndex(max(0, hi))
        self.b_hair.set_rgb(co.get("hairRGB", [0.23, 0.14, 0.09]))
        fi = self.p_face.findData(co.get("facial", ""))
        self.p_face.setCurrentIndex(max(0, fi))
        self.b_face.set_rgb(co.get("facialRGB", [0.2, 0.13, 0.08]))
        bi = list(BROWS).index(co.get("mk", {}).get("brows", "normali"))
        self.p_brows.setCurrentIndex(bi)
        self.b_brows.set_rgb(co.get("mk", {}).get("browsRGB", [0.2, 0.13, 0.08]))
        mk = co.get("mk", {})
        for qi, (key, _) in enumerate(MAKEUP):
            self._mk_checks[qi].setChecked(bool(mk.get(key, 0)))
            self._mk_colors[qi].set_rgb(mk.get(key + "RGB", [0.5, 0.5, 0.5]))
        self._blocking = False

    def _read_char(self) -> None:
        if self._blocking:
            return
        p = self._pi()
        if p < 0:
            return
        c = self.sh["chars"][p]
        old = c.get("name", "")
        nm = self.e_name.text().strip()
        if nm and nm != old and nm not in {x.get("name") for i, x in enumerate(self.sh["chars"]) if i != p}:
            c["name"] = nm
            rename_in_scenes(self.sh, "char", old, nm)
        c["sex"] = "F" if self.p_sex.currentIndex() == 1 else "M"
        c["height"] = float(self.e_ht.value())
        c["eyes"] = list(EYES[self.p_eyes.currentIndex()][1])
        c["rev"] = int(c.get("rev", 1)) + 1
        self._fill_chars()
        self.char_list.setCurrentRow(p)

    def _read_skin(self) -> None:
        if self._blocking:
            return
        p = self._pi()
        if p < 0:
            return
        k = self.p_skin.currentIndex()
        if k >= len(SKINS):
            rgb = self.sh["chars"][p].get("skin", SKINS[1][1])
            from PySide6.QtGui import QColor
            from PySide6.QtWidgets import QColorDialog

            c = QColorDialog.getColor(QColor(*(int(255 * x) for x in rgb)), self, "Pelle")
            if c.isValid():
                self.sh["chars"][p]["skin"] = [c.redF(), c.greenF(), c.blueF()]
        else:
            self.sh["chars"][p]["skin"] = list(SKINS[k][1])
        self.b_skin.set_rgb(self.sh["chars"][p]["skin"])
        self.sh["chars"][p]["rev"] = int(self.sh["chars"][p].get("rev", 1)) + 1
        self._show_char(p)

    def _pawn_color(self, rgb: list[float]) -> None:
        p = self._pi()
        if p >= 0:
            self.sh["chars"][p]["pawn"] = rgb
            self.sh["chars"][p]["rev"] = int(self.sh["chars"][p].get("rev", 1)) + 1

    def _add_costume(self) -> None:
        p = self._pi()
        if p < 0:
            return
        c = self.sh["chars"][p]
        code = chr(ord("A") + len(c["costumes"]))
        co = copy.deepcopy(c["costumes"][-1] if c["costumes"] else new_costume("A", c.get("sex", "M")))
        co["code"] = code
        co["desc"] = f"costume {code}"
        c["costumes"].append(co)
        c["rev"] = int(c.get("rev", 1)) + 1
        self._show_char(p)
        self.cos_list.setCurrentRow(len(c["costumes"]) - 1)

    def _dup_costume(self) -> None:
        p, j = self._pi(), self._ci()
        if p < 0 or j < 0:
            return
        c = self.sh["chars"][p]
        co = copy.deepcopy(c["costumes"][j])
        co["code"] = chr(ord("A") + len(c["costumes"]))
        co["desc"] = co.get("desc", "") + " (copia)"
        c["costumes"].append(co)
        self._show_char(p)
        self.cos_list.setCurrentRow(len(c["costumes"]) - 1)

    def _desc_costume(self) -> None:
        p, j = self._pi(), self._ci()
        if p < 0 or j < 0:
            return
        desc, ok = QInputDialog.getText(
            self,
            "Costume",
            "Descrizione:",
            text=self.sh["chars"][p]["costumes"][j].get("desc", ""),
        )
        if ok:
            self.sh["chars"][p]["costumes"][j]["desc"] = desc.strip()
            self._show_char(p)
            self.cos_list.setCurrentRow(j)

    def _del_costume(self) -> None:
        p, j = self._pi(), self._ci()
        if p < 0 or j < 0:
            return
        if len(self.sh["chars"][p]["costumes"]) <= 1:
            QMessageBox.warning(self, "Costumi", "Almeno un costume per personaggio.")
            return
        del self.sh["chars"][p]["costumes"][j]
        for qi, co in enumerate(self.sh["chars"][p]["costumes"]):
            co["code"] = chr(ord("A") + qi)
        self._show_char(p)
        self.cos_list.setCurrentRow(0)

    def _import_costume(self) -> None:
        p, j = self._pi(), self._ci()
        if p < 0 or j < 0 or not self.show_dir:
            return
        r = import_model_dialog(self, self.show_dir)
        if not r:
            return
        fn, _, _ = r
        self.sh["chars"][p]["costumes"][j]["mode"] = "import"
        self.sh["chars"][p]["costumes"][j]["file"] = fn
        self._show_costume(j)

    def _read_mode(self) -> None:
        if self._blocking:
            return
        p, j = self._pi(), self._ci()
        if p < 0 or j < 0:
            return
        modes = ("lib", "import")
        self.sh["chars"][p]["costumes"][j]["mode"] = modes[self.p_mode.currentIndex()]
        self._show_costume(j)

    def _read_costume(self) -> None:
        if self._blocking:
            return
        p, j = self._pi(), self._ci()
        if p < 0 or j < 0:
            return
        co = self.sh["chars"][p]["costumes"][j]
        items = co.setdefault("items", [""] * 10)
        irgb = co.setdefault("irgb", [[0.5, 0.5, 0.5] for _ in range(10)])
        while len(items) < 10:
            items.append("")
        while len(irgb) < 10:
            irgb.append([0.5, 0.5, 0.5])
        for qi, combo in enumerate(self._slot_combos):
            nid = combo.currentData()
            if nid and nid != items[qi]:
                cat = self._by_id.get(nid)
                if cat and cat.hex:
                    irgb[qi] = list(cat.rgb)
            items[qi] = nid or ""
        co["hair"] = self.p_hair.currentData() or ""
        co["facial"] = self.p_face.currentData() or ""
        co.setdefault("mk", {})
        co["mk"]["brows"] = self.p_brows.currentText()
        for qi, (key, _) in enumerate(MAKEUP):
            co["mk"][key] = 1 if self._mk_checks[qi].isChecked() else 0
        self.sh["chars"][p]["rev"] = int(self.sh["chars"][p].get("rev", 1)) + 1

    def _item_color(self, qi: int, rgb: list[float]) -> None:
        p, j = self._pi(), self._ci()
        if p < 0 or j < 0:
            return
        co = self.sh["chars"][p]["costumes"][j]
        irgb = co.setdefault("irgb", [[0.5, 0.5, 0.5]] * 10)
        while len(irgb) <= qi:
            irgb.append([0.5, 0.5, 0.5])
        irgb[qi] = rgb

    def _mk_color(self, field: str, rgb: list[float], toggle_key: str | None = None) -> None:
        p, j = self._pi(), self._ci()
        if p < 0 or j < 0:
            return
        co = self.sh["chars"][p]["costumes"][j]
        co.setdefault("mk", {})[field] = rgb
        if toggle_key:
            co["mk"][toggle_key] = 1

    def _set_brows_rgb(self, rgb: list[float]) -> None:
        p, j = self._pi(), self._ci()
        if p < 0 or j < 0:
            return
        self.sh["chars"][p]["costumes"][j].setdefault("mk", {})["browsRGB"] = rgb
