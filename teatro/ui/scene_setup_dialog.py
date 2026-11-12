"""GUI Imposta scena (port di sceneSetup MATLAB)."""

from __future__ import annotations

import copy

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from teatro.models import roman
from teatro.scene_logic import cast_code
from teatro.scene_objects import alloc_uid, new_obj, plan_color, prune_objs, set_cast
from teatro.theater import fix_theater, zone_geom
from teatro.ui.plan_canvas import PlanCanvas


class SceneSetupDialog(QDialog):
    def __init__(self, parent, sh: dict, sc: dict, on_save) -> None:
        super().__init__(parent)
        self.sh = sh
        self.sc = copy.deepcopy(sc)
        self._on_save = on_save
        self._pending: dict | None = None
        self._drag_idx: int | None = None
        self.setWindowTitle(f"Imposta scena  —  {sc.get('title', '')}")
        self.resize(1100, 700)
        self._build()
        self._fill_all()
        self._redraw()
        self.hint.setText('Scegli un personaggio o un elemento e premi "Metti in scena", poi clicca sulla pianta.')

    def _build(self) -> None:
        root = QHBoxLayout(self)
        left = QVBoxLayout()
        self.canvas = PlanCanvas(self)
        left.addWidget(self.canvas, stretch=1)
        self.hint = QLabel("")
        self.hint.setStyleSheet("color:#e6c96e;font-size:11px;")
        left.addWidget(self.hint)
        root.addLayout(left, 3)

        right = QVBoxLayout()
        sc = self.sc
        right.addWidget(
            QLabel(
                f"Atto {roman(int(sc.get('act', 1)))}  —  Scena {int(sc.get('num', 0))}  —  {sc.get('title', '')}",
                styleSheet="font-size:14px;font-weight:bold;color:#d4b059;",
            )
        )
        right.addWidget(QLabel("PERSONAGGI  (in scena all'inizio = pallino pieno)"))
        self.lb_chars = QListWidget()
        self.lb_chars.currentRowChanged.connect(self._sel_char)
        right.addWidget(self.lb_chars)
        row = QHBoxLayout()
        row.addWidget(QLabel("Costume in questa scena"))
        self.cmb_cost = QComboBox()
        self.cmb_cost.currentIndexChanged.connect(self._set_costume)
        row.addWidget(self.cmb_cost, stretch=1)
        right.addLayout(row)
        for label, slot in [
            ("Metti in scena / sposta", lambda: self._start_place("char")),
            ("Togli dalla scena", lambda: self._remove_start("char")),
        ]:
            b = QPushButton(label)
            b.clicked.connect(slot)
            right.addWidget(b)

        right.addWidget(QLabel('ELEMENTI SCENICI  (quelli "fissi" ci sono sempre)'))
        self.lb_els = QListWidget()
        right.addWidget(self.lb_els)
        for label, slot in [
            ("Metti in scena / sposta", lambda: self._start_place("el")),
            ("Togli dalla scena", lambda: self._remove_start("el")),
            ("Ruota di 90°", self._rotate_el),
        ]:
            b = QPushButton(label)
            b.clicked.connect(slot)
            right.addWidget(b)

        right.addWidget(QLabel("LUCI ACCESE ALL'INIZIO"))
        self.lb_lights = QListWidget()
        self.lb_lights.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.lb_lights.itemSelectionChanged.connect(self._read_lights)
        right.addWidget(self.lb_lights)
        right.addWidget(
            QLabel(
                "Chi entra più tardi non va messo qui: lo fai entrare nei passi.\n"
                "Clic su una pedina e trascina per spostarla."
            )
        )
        btns = QHBoxLayout()
        save = QPushButton("Salva")
        save.setStyleSheet("font-weight:bold;font-size:12px;")
        save.clicked.connect(self._do_save)
        btns.addWidget(save)
        cancel = QPushButton("Annulla")
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)
        right.addLayout(btns)
        root.addLayout(right, 2)

        self.canvas.set_handlers(self._on_click, self._on_drag, self._on_release)

    def _movable(self) -> list[int]:
        return [i for i, e in enumerate(self.sh.get("elements", [])) if not e.get("fixed")]

    def _washes(self) -> list[int]:
        out = []
        for i, L in enumerate(self.sh.get("lights", [])):
            if L.get("zone") != "Segue un personaggio":
                out.append(i)
        return out

    def _obj_idx(self, kind: str, ref: str) -> int | None:
        for i, o in enumerate(self.sc.get("objects", [])):
            if o.get("kind") == kind and o.get("ref") == ref:
                return i
        return None

    def _fill_all(self) -> None:
        self.lb_chars.blockSignals(True)
        self.lb_chars.clear()
        for ch in self.sh.get("chars", []):
            nm = ch["name"]
            i = self._obj_idx("char", nm)
            on = i is not None and self.sc["objects"][i].get("start")
            mk = "●" if on else "○"
            self.lb_chars.addItem(f"{mk}  {nm}   (costume {cast_code(self.sc, nm)})")
        if not self.sh.get("chars"):
            self.lb_chars.addItem("(nessun personaggio)")
        self.lb_chars.blockSignals(False)

        self.lb_els.clear()
        mov = self._movable()
        for qi in mov:
            e = self.sh["elements"][qi]
            i = self._obj_idx("el", e["name"])
            on = i is not None and self.sc["objects"][i].get("start")
            mk = "●" if on else "○"
            self.lb_els.addItem(f"{mk}  {e['name']}")
        if not mov:
            self.lb_els.addItem("(nessun elemento mobile)")

        self.lb_lights.blockSignals(True)
        self.lb_lights.clear()
        for wi in self._washes():
            L = self.sh["lights"][wi]
            self.lb_lights.addItem(f"{L['name']}   ({L.get('cname','')}, {L.get('zone','')})")
        sel_rows = []
        for row, wi in enumerate(self._washes()):
            i = self._obj_idx("light", self.sh["lights"][wi]["name"])
            if i is not None and self.sc["objects"][i].get("start"):
                sel_rows.append(row)
        for r in sel_rows:
            self.lb_lights.item(r).setSelected(True)
        self.lb_lights.blockSignals(False)
        self._sel_char()

    def _sel_char(self) -> None:
        row = self.lb_chars.currentRow()
        chars = self.sh.get("chars", [])
        if row < 0 or row >= len(chars):
            return
        ch = chars[row]
        self.cmb_cost.blockSignals(True)
        self.cmb_cost.clear()
        for co in ch.get("costumes", []):
            self.cmb_cost.addItem(f"{co.get('code','')}  —  {co.get('desc','')}")
        code = cast_code(self.sc, ch["name"])
        idx = 0
        for j, co in enumerate(ch.get("costumes", [])):
            if co.get("code") == code:
                idx = j
                break
        self.cmb_cost.setCurrentIndex(min(idx, max(0, self.cmb_cost.count() - 1)))
        self.cmb_cost.blockSignals(False)

    def _set_costume(self) -> None:
        row = self.lb_chars.currentRow()
        chars = self.sh.get("chars", [])
        if row < 0 or row >= len(chars):
            return
        ch = chars[row]
        costumes = ch.get("costumes", [])
        j = self.cmb_cost.currentIndex()
        if j < 0 or j >= len(costumes):
            return
        self.sc = set_cast(self.sc, ch["name"], costumes[j]["code"])
        self._fill_all()

    def _start_place(self, kind: str) -> None:
        if kind == "char":
            row = self.lb_chars.currentRow()
            chars = self.sh.get("chars", [])
            if row < 0 or row >= len(chars):
                return
            self._pending = {"kind": "char", "ref": chars[row]["name"]}
        else:
            row = self.lb_els.currentRow()
            mov = self._movable()
            if row < 0 or row >= len(mov):
                return
            self._pending = {"kind": "el", "ref": self.sh["elements"][mov[row]]["name"]}
        self.hint.setText(f"Clicca sulla pianta dove si trova all'inizio: {self._pending['ref']}")

    def _remove_start(self, kind: str) -> None:
        if kind == "char":
            row = self.lb_chars.currentRow()
            chars = self.sh.get("chars", [])
            if row < 0 or row >= len(chars):
                return
            nm = chars[row]["name"]
        else:
            row = self.lb_els.currentRow()
            mov = self._movable()
            if row < 0 or row >= len(mov):
                return
            nm = self.sh["elements"][mov[row]]["name"]
        i = self._obj_idx(kind, nm)
        if i is None:
            return
        self.sc["objects"][i]["start"] = False
        self.sc = prune_objs(self.sc)
        self._fill_all()
        self._redraw()
        self.hint.setText(f"{nm} non è in scena all'inizio (può entrare durante i passi).")

    def _rotate_el(self) -> None:
        row = self.lb_els.currentRow()
        mov = self._movable()
        if row < 0 or row >= len(mov):
            return
        nm = self.sh["elements"][mov[row]]["name"]
        i = self._obj_idx("el", nm)
        if i is None:
            self.hint.setText("Prima mettilo in scena.")
            return
        self.sc["objects"][i]["rot"] = (float(self.sc["objects"][i].get("rot", 0)) + 90) % 360
        self._redraw()

    def _read_lights(self) -> None:
        T = fix_theater(self.sh["theater"])
        washes = self._washes()
        selected = {self.lb_lights.row(it) for it in self.lb_lights.selectedItems()}
        for row, wi in enumerate(washes):
            L = self.sh["lights"][wi]
            on = row in selected
            i = self._obj_idx("light", L["name"])
            if on and i is None:
                g = zone_geom(L["zone"], T, np.array([0.0, 0.0]))
                oid = alloc_uid(self.sh)
                self.sc.setdefault("objects", []).append(
                    new_obj(oid, "light", L["name"], L["name"], g["cx"], g["cy"], L["rgb"], L["zone"], 0, 0, 0, True)
                )
            elif i is not None:
                self.sc["objects"][i]["start"] = on
        self.sc = prune_objs(self.sc)
        self._redraw()

    def _redraw(self) -> None:
        self.canvas._plan.draw_setup(self.sh, self.sc)
        self.canvas.draw_idle()

    def _place_at(self, x: float, y: float) -> None:
        if self._pending:
            kind = self._pending["kind"]
            ref = self._pending["ref"]
            i = self._obj_idx(kind, ref)
            if i is None:
                if kind == "char":
                    ch = next(c for c in self.sh["chars"] if c["name"] == ref)
                    oid = alloc_uid(self.sh)
                    self.sc.setdefault("objects", []).append(
                        new_obj(oid, "char", ref, ref, x, y, ch.get("pawn", [0.8, 0.3, 0.3]), "", 0, 0, 0, True)
                    )
                    self.sc = set_cast(self.sc, ref, cast_code(self.sc, ref))
                else:
                    e = next(el for el in self.sh["elements"] if el["name"] == ref)
                    sz = e.get("size", [1, 1, 1])
                    oid = alloc_uid(self.sh)
                    self.sc.setdefault("objects", []).append(
                        new_obj(
                            oid,
                            "el",
                            e["name"],
                            e["name"],
                            x,
                            y,
                            plan_color(e),
                            "",
                            float(sz[0]),
                            float(sz[1]),
                            0,
                            True,
                        )
                    )
            else:
                self.sc["objects"][i]["x"] = x
                self.sc["objects"][i]["y"] = y
                self.sc["objects"][i]["start"] = True
            self._pending = None
            self.hint.setText(f"{ref} posizionato. Puoi trascinarlo per correggere.")
            self._fill_all()
            self._redraw()
            return
        best, drag = 0.6, None
        for i, o in enumerate(self.sc.get("objects", [])):
            if not o.get("start") or o.get("kind") == "light":
                continue
            d = np.hypot(o["x"] - x, o["y"] - y)
            if d < best:
                best, drag = d, i
        self._drag_idx = drag

    def _on_click(self, x: float, y: float) -> None:
        self._place_at(x, y)

    def _on_drag(self, x: float, y: float) -> None:
        if self._drag_idx is not None:
            self.sc["objects"][self._drag_idx]["x"] = x
            self.sc["objects"][self._drag_idx]["y"] = y
            self._redraw()

    def _on_release(self) -> None:
        self._drag_idx = None

    def _do_save(self) -> None:
        self.sc = prune_objs(self.sc)
        self._on_save(self.sc)
        self.accept()
