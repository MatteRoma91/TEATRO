"""Editor singolo passo (port stepEditor MATLAB)."""

from __future__ import annotations

import copy
import re

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from teatro.scene_logic import cast_code, cue_text, normalize_step, simplify_path, state_at
from teatro.scene_objects import alloc_uid, mk_eff, new_obj, plan_color, set_cast
from teatro.theater import fix_theater, zone_geom
from teatro.ui.plan_canvas import PlanCanvas


class StepEditorDialog(QDialog):
    def __init__(self, parent, sh: dict, sc: dict, k: int, is_new: bool) -> None:
        super().__init__(parent)
        self.sh = sh
        self.sc = copy.deepcopy(sc)
        self.k = k
        self.is_new = is_new
        self.step_effects: list[dict] = []
        self.step_cue = ""
        self.step_ens = ""
        self.objs = copy.deepcopy(self.sc.get("objects", []))
        self.cast = copy.deepcopy(self.sc.get("cast", []))
        if is_new:
            self.eff: list[dict] = []
            self.desc = ""
            self.ens = ""
        else:
            self.eff = normalize_step(self.sc["steps"][k - 1])
            self.desc = cue_text(self.sc, k)
            ens_list = self.sc.get("ens", [])
            self.ens = ens_list[k - 1] if k - 1 < len(ens_list) else ""
        self.st0 = state_at(self.sc, k - 1)
        self._tg_k: list[str] = []
        self._tg_r: list[str] = []
        self._tg_n: list[str] = []
        self._build_targets()
        self._P = np.zeros((0, 2))
        self._drawing = False
        self._start_pt: np.ndarray | None = None
        self._path_line = None
        self._start_mark = None
        self.setWindowTitle(f"Passo {k} — {sc.get('title', '')}")
        self.resize(1100, 720)
        self._build()
        self._wash_sel()
        self._draw_plan()
        self._show_actions()
        self._new_action_hint()

    def result_scene(self) -> dict:
        sc = copy.deepcopy(self.sc)
        sc["objects"] = self.objs
        sc["cast"] = self.cast
        return sc

    def _build_targets(self) -> None:
        for ch in self.sh.get("chars", []):
            self._tg_k.append("char")
            self._tg_r.append(ch["name"])
            self._tg_n.append(ch["name"])
        for e in self.sh.get("elements", []):
            if e.get("fixed"):
                continue
            self._tg_k.append("el")
            self._tg_r.append(e["name"])
            self._tg_n.append(f"Elemento: {e['name']}")
        if not self._tg_k:
            QMessageBox.warning(self, "Passo", "Crea almeno un personaggio o un elemento scenico.")
        self._FOL = [L for L in self.sh.get("lights", []) if L.get("zone") == "Segue un personaggio"]
        if not self._FOL:
            from teatro.models import new_light

            self._FOL = [
                new_light("Occhio di bue", "Seguipersona (occhio di bue)", 1, "Bianco", [1, 1, 0.95], "Segue un personaggio")
            ]
        self._WL = [L for L in self.sh.get("lights", []) if L.get("zone") != "Segue un personaggio"]

    def _build(self) -> None:
        root = QHBoxLayout(self)
        left = QVBoxLayout()
        self.canvas = PlanCanvas(self)
        left.addWidget(self.canvas, stretch=1)
        self.hint = QLabel("")
        self.hint.setStyleSheet("color:#e6c96e;")
        self.hint.setWordWrap(True)
        left.addWidget(self.hint)
        root.addLayout(left, 3)

        right = QVBoxLayout()
        right.addWidget(QLabel("Descrizione del passo"))
        self.ed_desc = QLineEdit(self.desc)
        right.addWidget(self.ed_desc)
        right.addWidget(QLabel("Corpo di ballo / note (facoltativo)"))
        self.ed_ens = QLineEdit(self.ens)
        right.addWidget(self.ed_ens)
        right.addWidget(QLabel("Azioni di questo passo"))
        self.lb_actions = QListWidget()
        right.addWidget(self.lb_actions)
        del_a = QPushButton("Elimina l'azione selezionata")
        del_a.clicked.connect(self._del_action)
        right.addWidget(del_a)
        right.addWidget(QLabel("NUOVA AZIONE"))
        self.pop_who = QComboBox()
        self.pop_who.addItems(self._tg_n or ["(nessuno)"])
        self.pop_who.currentIndexChanged.connect(self._new_action_hint)
        right.addWidget(self.pop_who)
        self.pop_type = QComboBox()
        self.pop_type.addItems(["Movimento", "Entra in scena", "Esce di scena"])
        self.pop_type.currentIndexChanged.connect(self._new_action_hint)
        right.addWidget(self.pop_type)
        self.pop_path = QComboBox()
        self.pop_path.addItems(["Linea retta (clicca arrivo)", "Percorso libero (tieni premuto)"])
        self.pop_path.currentIndexChanged.connect(self._new_action_hint)
        right.addWidget(self.pop_path)
        self.pop_light = QComboBox()
        self.pop_light.addItem("Nessuna")
        for L in self._FOL:
            self.pop_light.addItem(L["name"])
        right.addWidget(self.pop_light)
        self.chk_start = QCheckBox("Scegli anche il punto di partenza (primo clic)")
        self.chk_start.stateChanged.connect(self._new_action_hint)
        right.addWidget(self.chk_start)
        row = QHBoxLayout()
        row.addWidget(QLabel("Durata (s)"))
        self.sp_dur = QDoubleSpinBox()
        self.sp_dur.setRange(0.1, 600)
        self.sp_dur.setValue(2.0)
        row.addWidget(self.sp_dur)
        row.addWidget(QLabel("Ritardo (s)"))
        self.sp_del = QDoubleSpinBox()
        self.sp_del.setRange(0, 600)
        row.addWidget(self.sp_del)
        right.addLayout(row)
        add = QPushButton("+ Aggiungi questa azione")
        add.setStyleSheet("font-weight:bold;")
        add.clicked.connect(self._add_action)
        right.addWidget(add)
        clr = QPushButton("Cancella il disegno")
        clr.clicked.connect(self._new_action_hint)
        right.addWidget(clr)
        right.addWidget(QLabel("LUCI GENERALI DEL PASSO"))
        self.lb_wash = QListWidget()
        self.lb_wash.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for L in self._WL:
            self.lb_wash.addItem(f"{L['name']}  ({L.get('cname','')}, {L.get('zone','')})")
        right.addWidget(self.lb_wash)
        wrow = QHBoxLayout()
        wp = QPushButton("Come il passo precedente")
        wp.clicked.connect(self._wash_prev)
        wrow.addWidget(wp)
        wb = QPushButton("Buio (spegni tutto)")
        wb.clicked.connect(lambda: self.lb_wash.clearSelection())
        wrow.addWidget(wb)
        right.addLayout(wrow)
        brow = QHBoxLayout()
        save = QPushButton("Salva passo")
        save.setStyleSheet("font-weight:bold;font-size:12px;")
        save.clicked.connect(self._save_step)
        brow.addWidget(save)
        cancel = QPushButton("Annulla")
        cancel.clicked.connect(self.reject)
        brow.addWidget(cancel)
        right.addLayout(brow)
        root.addLayout(right, 2)

        self.canvas.set_handlers(self._m_down, self._m_move, self._m_up)

    def _tg_index(self, t: int) -> int | None:
        if t < 0 or t >= len(self._tg_r):
            return None
        for i, o in enumerate(self.objs):
            if o.get("kind") == self._tg_k[t] and o.get("ref") == self._tg_r[t]:
                return i
        return None

    def _cur_pos(self, ip: int) -> np.ndarray:
        c = self.st0[ip, :2].copy()
        oid = self.objs[ip].get("id")
        for ej in self.eff:
            if ej.get("spid") == oid and ej.get("cls") == "path":
                pts = np.asarray(ej.get("pts", [[0, 0]]))
                c = pts[-1, :2]
        return c

    def _cur_vis(self, ip: int) -> bool:
        a = self.st0[ip, 2] > 0.5
        oid = self.objs[ip].get("id")
        for ej in self.eff:
            if ej.get("spid") == oid:
                if ej.get("cls") == "entr":
                    a = True
                elif ej.get("cls") == "exit":
                    a = False
        return a

    def _draw_plan(self) -> None:
        sc_vis = dict(self.sc)
        sc_vis["objects"] = self.objs
        n = len(self.objs)
        pos = np.zeros((n, 2))
        alpha = np.zeros(n)
        for i in range(n):
            if self._cur_vis(i):
                pos[i] = self._cur_pos(i)
                alpha[i] = 1.0
        self.canvas._plan.draw(self.sh, sc_vis, pos, alpha)
        self.canvas._plan.draw_fixed(self.sh)
        ax = self.canvas.ax
        for ej in self.eff:
            if ej.get("cls") != "path":
                continue
            ii = next((i for i, o in enumerate(self.objs) if o.get("id") == ej.get("spid")), None)
            if ii is None or self.objs[ii].get("kind") == "light":
                continue
            q = np.asarray(ej.get("pts", [[0, 0]])) + np.array([self.objs[ii]["x"], self.objs[ii]["y"]])
            ax.plot(q[:, 0], q[:, 1], "-", linewidth=2, color=self.objs[ii].get("rgb", [0.8, 0.8, 0.2]))
            ax.plot(q[-1, 0], q[-1, 1], "s", markersize=8)
        if self._path_line:
            try:
                self._path_line.remove()
            except Exception:
                pass
        if self._P.shape[0] >= 2:
            self._path_line = ax.plot(self._P[:, 0], self._P[:, 1], "-", linewidth=3, color=[1, 0.85, 0.3])[0]
        elif self._P.shape[0] == 1:
            self._path_line = ax.plot(self._P[:, 0], self._P[:, 1], "o", markersize=10, color=[1, 0.85, 0.3])[0]
        ax.set_title("Pianta del palco  (pubblico in basso)", color="#d4b059", fontsize=11)
        self.canvas.draw_idle()

    def _show_actions(self) -> None:
        self.lb_actions.clear()
        for ej in self.eff:
            ii = next((i for i, o in enumerate(self.objs) if o.get("id") == ej.get("spid")), None)
            nm = self.objs[ii]["label"] if ii is not None else "?"
            cls = ej.get("cls")
            if cls == "path":
                v = f"si muove ({len(ej.get('pts', []))} punti)"
            elif cls == "entr":
                v = "entra / si accende"
            else:
                v = "esce / si spegne"
            self.lb_actions.addItem(f"{nm}: {v}  —  {float(ej.get('dur',0)):.1f} s, ritardo {float(ej.get('delay',0)):.1f} s")
        if not self.eff:
            self.lb_actions.addItem("(nessuna azione)")

    def _new_action_hint(self) -> None:
        self._P = np.zeros((0, 2))
        self._drawing = False
        self._start_pt = None
        t = self.pop_who.currentIndex()
        ty = self.pop_type.currentIndex()
        nm = self._tg_r[t] if t < len(self._tg_r) else ""
        ip = self._tg_index(t)
        if ip is not None and not self._cur_vis(ip) and ty != 1:
            ip = None
        if ty == 0:
            if ip is None:
                self.hint.setText(f"{nm} non è in scena: clicca dove compare, poi indica il percorso.")
            elif self.chk_start.isChecked():
                self.hint.setText("Primo clic: punto di partenza. Poi indica il percorso.")
            elif self.pop_path.currentIndex() == 0:
                self.hint.setText("Clicca sulla pianta il punto di arrivo (il cerchio giallo è la partenza).")
            else:
                self.hint.setText("Tieni premuto il mouse e disegna il percorso, poi rilascia.")
        elif ty == 1:
            self.hint.setText('Clicca dove deve comparire. Poi premi "+ Aggiungi questa azione".')
        else:
            self.hint.setText('Premi "+ Aggiungi questa azione": esce dalla posizione attuale.')
        self._draw_plan()

    def _del_action(self) -> None:
        v = self.lb_actions.currentRow()
        if v < 0 or v >= len(self.eff):
            return
        del self.eff[v]
        self._show_actions()
        self._draw_plan()
        self._new_action_hint()

    def _m_down(self, x: float, y: float) -> None:
        t = self.pop_who.currentIndex()
        ty = self.pop_type.currentIndex()
        ip = self._tg_index(t)
        if ip is not None and not self._cur_vis(ip):
            ip = None
        need_start = ip is None or self.chk_start.isChecked() or ty == 1
        if need_start and self._start_pt is None:
            self._start_pt = np.array([x, y])
            self._P = np.array([[x, y]])
            if ty == 1:
                self.hint.setText('Punto scelto. Premi "+ Aggiungi questa azione".')
            else:
                self.hint.setText("Partenza scelta: ora indica il percorso.")
            self._draw_plan()
            return
        if ty != 0:
            return
        s0 = self._start_pt
        if s0 is None and ip is not None:
            o = self.objs[ip]
            s0 = np.array([o["x"], o["y"]]) + self._cur_pos(ip)
        elif s0 is None:
            return
        self._P = np.array([s0, [x, y]])
        self._drawing = self.pop_path.currentIndex() == 1
        self._draw_plan()
        if not self._drawing:
            self.hint.setText('Percorso pronto: regola durata/ritardo, poi "+ Aggiungi questa azione".')

    def _m_move(self, x: float, y: float) -> None:
        if not self._drawing or self._P.shape[0] == 0:
            return
        if np.linalg.norm([x, y] - self._P[-1]) > 0.05:
            self._P = np.vstack([self._P, [x, y]])
            self._draw_plan()

    def _m_up(self) -> None:
        if self._drawing:
            self._drawing = False
            self.hint.setText('Percorso disegnato: premi "+ Aggiungi questa azione" (o "Cancella il disegno").')

    def _add_obj(self, o: dict) -> int:
        self.objs.append(o)
        row = np.array([0.0, 0.0, 0.0])
        self.st0 = np.vstack([self.st0, row]) if self.st0.size else np.array([row])
        return len(self.objs) - 1

    def _add_target(self, t: int, pt: np.ndarray) -> int:
        if self._tg_k[t] == "char":
            ch = next(c for c in self.sh["chars"] if c["name"] == self._tg_r[t])
            oid = alloc_uid(self.sh)
            ip = self._add_obj(new_obj(oid, "char", self._tg_r[t], self._tg_r[t], pt[0], pt[1], ch.get("pawn", [0.8, 0.3, 0.3]), "", 0, 0, 0, False))
            sc_tmp = set_cast({"cast": self.cast}, self._tg_r[t], cast_code({"cast": self.cast}, self._tg_r[t]))
            self.cast = sc_tmp["cast"]
        else:
            e = next(el for el in self.sh["elements"] if el["name"] == self._tg_r[t])
            sz = e.get("size", [1, 1, 1])
            oid = alloc_uid(self.sh)
            ip = self._add_obj(
                new_obj(oid, "el", e["name"], e["name"], pt[0], pt[1], plan_color(e), "", float(sz[0]), float(sz[1]), 0, False)
            )
        return ip

    def _light_obj(self, L: dict, label: str, center: np.ndarray) -> int:
        for i, o in enumerate(self.objs):
            if o.get("kind") == "light" and o.get("label") == label:
                return i
        oid = alloc_uid(self.sh)
        return self._add_obj(new_obj(oid, "light", L["name"], label, center[0], center[1], L["rgb"], L["zone"], 0, 0, 0, False))

    def _add_action(self) -> None:
        t = self.pop_who.currentIndex()
        ty = self.pop_type.currentIndex() + 1
        du = float(self.sp_dur.value())
        dl = float(self.sp_del.value())
        ip = self._tg_index(t)
        if ty == 1 and self._P.shape[0] < 2:
            QMessageBox.warning(self, "Passo", "Prima indica il movimento sulla pianta.")
            return
        if ip is None or not self._cur_vis(ip):
            if ty == 3:
                QMessageBox.warning(self, "Passo", f"{self._tg_r[t]} non è in scena.")
                return
            if self._start_pt is None:
                QMessageBox.warning(self, "Passo", "Clicca sulla pianta il punto in cui compare.")
                return
            if ip is None:
                ip = self._add_target(t, self._start_pt)
            o = self.objs[ip]
            self.eff.append(mk_eff("path", o["id"], [self._cur_pos(ip).tolist(), (self._start_pt - [o["x"], o["y"]]).tolist()], 0.01, dl))
            self.eff.append(mk_eff("entr", o["id"], [], 0.5, dl))
            if ty == 1:
                dl += 0.5
            if ty == 2:
                ty = 0
        o = self.objs[ip]
        org = np.array([o["x"], o["y"]])
        if ty == 1:
            rel = simplify_path(self._P - org)
            self.eff.append(mk_eff("path", o["id"], rel.tolist(), du, dl))
        elif ty == 2:
            if self._start_pt is not None:
                self.eff.append(mk_eff("path", o["id"], [self._cur_pos(ip).tolist(), (self._start_pt - org).tolist()], 0.01, dl))
            self.eff.append(mk_eff("entr", o["id"], [], du, dl))
        elif ty == 3:
            self.eff.append(mk_eff("exit", o["id"], [], du, dl))
            pat = re.compile(r" su " + re.escape(o.get("label", "")) + r"$")
            for ii, oo in enumerate(self.objs):
                if oo.get("kind") == "light" and pat.search(oo.get("label", "")) and self._cur_vis(ii):
                    self.eff.append(mk_eff("exit", oo["id"], [], du, dl))
        sp = self.pop_light.currentIndex()
        if sp > 0 and ty == 1 and self._P.shape[0] >= 2:
            L = self._FOL[sp - 1]
            lab = f"{L['name']} su {o['label']}"
            il = self._light_obj(L, lab, self._P[0])
            lo = self.objs[il]
            lorg = np.array([lo["x"], lo["y"]])
            if not self._cur_vis(il):
                self.eff.append(mk_eff("path", lo["id"], [self._cur_pos(il).tolist(), (self._P[0] - lorg).tolist()], 0.01, max(0, dl - 0.5)))
                self.eff.append(mk_eff("entr", lo["id"], [], 0.5, max(0, dl - 0.5)))
            self.eff.append(mk_eff("path", lo["id"], simplify_path(self._P - lorg).tolist(), du, dl))
        self._show_actions()
        self._new_action_hint()
        self.hint.setText("Azione aggiunta. Aggiungi altre azioni contemporanee o Salva passo.")

    def _wash_obj(self, q: int) -> int | None:
        nm = self._WL[q]["name"]
        for i, o in enumerate(self.objs):
            if o.get("kind") == "light" and o.get("label") == nm:
                return i
        return None

    def _wash_sel(self) -> None:
        rows = []
        for q, L in enumerate(self._WL):
            wi = self._wash_obj(q)
            if wi is not None and self._cur_vis(wi):
                rows.append(q)
        for r in rows:
            self.lb_wash.item(r).setSelected(True)

    def _wash_prev(self) -> None:
        rows = []
        for q in range(len(self._WL)):
            wi = self._wash_obj(q)
            if wi is not None and self.st0[wi, 2] > 0.5:
                rows.append(q)
        self.lb_wash.clearSelection()
        for r in rows:
            self.lb_wash.item(r).setSelected(True)

    def _apply_wash(self) -> None:
        keep = []
        for ej in self.eff:
            ii = next((i for i, o in enumerate(self.objs) if o.get("id") == ej.get("spid")), None)
            if ii is not None and self.objs[ii].get("kind") == "light" and self.objs[ii].get("zone") != "Segue un personaggio":
                if ej.get("cls") in ("entr", "exit"):
                    continue
            keep.append(ej)
        self.eff = keep
        T = fix_theater(self.sh["theater"])
        selected = {self.lb_wash.row(it) for it in self.lb_wash.selectedItems()}
        for q, L in enumerate(self._WL):
            on = q in selected
            wi = self._wash_obj(q)
            before = wi is not None and self.st0[wi, 2] > 0.5
            if on and not before:
                if wi is None:
                    gz = zone_geom(L["zone"], T, np.array([0.0, 0.0]))
                    wi = self._light_obj(L, L["name"], np.array([gz["cx"], gz["cy"]]))
                self.eff.append(mk_eff("entr", self.objs[wi]["id"], [], 1.2, 0))
            elif not on and before and wi is not None:
                self.eff.append(mk_eff("exit", self.objs[wi]["id"], [], 1.2, 0))

    def _save_step(self) -> None:
        self._apply_wash()
        dsc = self.ed_desc.text().strip() or f"passo {self.k}"
        en = self.ed_ens.text().strip()
        self.step_effects = self.eff
        self.step_cue = dsc
        self.step_ens = en
        self.sc["objects"] = self.objs
        self.sc["cast"] = self.cast
        self.accept()
