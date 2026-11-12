"""Logica montaggio: stato, interpolazione, testi passi."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from teatro.theater import fix_theater, zone_geom


def cast_code(sc: dict, name: str) -> str:
    for c in sc.get("cast", []):
        if c.get("name") == name:
            return c.get("code", "A")
    return "A"


def cue_text(sc: dict, k: int) -> str:
    cues = sc.get("cues", [])
    if 0 < k <= len(cues) and cues[k - 1]:
        return str(cues[k - 1])
    return f"passo {k}"


def path_point(pts: np.ndarray, u: float) -> np.ndarray:
    p = np.asarray(pts, dtype=float)
    if p.ndim == 1:
        p = p.reshape(1, -1)
    if p.shape[0] == 1:
        return p[0, :2]
    seg = np.sqrt(np.sum(np.diff(p, axis=0) ** 2, axis=1))
    length = np.concatenate([[0], np.cumsum(seg)])
    if length[-1] == 0:
        return p[-1, :2]
    t = u * length[-1]
    k = max(0, min(np.searchsorted(length, t, side="right") - 1, p.shape[0] - 2))
    f = (t - length[k]) / max(seg[k], 1e-9)
    return p[k, :2] + f * (p[k + 1, :2] - p[k, :2])


def simplify_path(p: np.ndarray) -> np.ndarray:
    p = np.asarray(p, dtype=float)
    if p.shape[0] <= 2:
        return p
    q = [p[0]]
    for i in range(1, p.shape[0] - 1):
        if np.linalg.norm(p[i] - q[-1]) >= 0.12:
            q.append(p[i])
    q.append(p[-1])
    q = np.array(q)
    if q.shape[0] > 40:
        idx = np.round(np.linspace(0, q.shape[0] - 1, 40)).astype(int)
        q = q[idx]
    return q


def act_summary(sc: dict, k: int) -> str:
    if k < 1 or k > len(sc.get("steps", [])):
        return ""
    e = normalize_step(sc["steps"][k - 1])
    objs = sc.get("objects", [])
    ids = [o.get("id") for o in objs]
    names = []
    for ej in e:
        try:
            i = ids.index(ej.get("spid"))
        except ValueError:
            continue
        o = objs[i]
        cls = ej.get("cls")
        if o.get("kind") == "light":
            v = {"entr": "si accende", "exit": "si spegne"}.get(cls, "si sposta")
            names.append(f"luce {o.get('label')} {v}")
        else:
            v = {"entr": "entra", "exit": "esce"}.get(cls, "si muove")
            names.append(f"{o.get('label')} {v}")
    return ", ".join(dict.fromkeys(names)) if names else "nessuna azione"


def action_lines(sc: dict, k: int, theater: dict) -> list[str]:
    if k < 1 or k > len(sc.get("steps", [])):
        return []
    e = normalize_step(sc["steps"][k - 1])
    objs = sc.get("objects", [])
    ids = [o.get("id") for o in objs]
    lines = []
    for ej in e:
        try:
            i = ids.index(ej.get("spid"))
        except ValueError:
            continue
        o = objs[i]
        nm = o.get("label", "")
        cls = ej.get("cls")
        if o.get("kind") == "light":
            if cls == "path" and float(ej.get("dur", 0)) < 0.05:
                continue
            v = {"entr": "si accende", "exit": "si spegne"}.get(cls, "segue il percorso")
            s = f"Luce {nm}: {v}"
        else:
            if cls == "entr":
                v = "entra in scena"
            elif cls == "exit":
                v = "esce di scena"
            else:
                if float(ej.get("dur", 0)) < 0.05:
                    continue
                pts = np.asarray(ej.get("pts", [[0, 0]]))
                p1 = np.array([o.get("x", 0), o.get("y", 0)]) + pts[-1]
                v = f"va verso {zone_name(p1, theater)}"
                if pts.shape[0] > 2:
                    v += " (percorso libero)"
            s = f"{nm}: {v}"
        s = f"{s}  ({float(ej.get('dur', 0)):.1f} s"
        if float(ej.get("delay", 0)) > 0:
            s += f", dopo {float(ej.get('delay', 0)):.1f} s"
        lines.append(s.replace(".", ",") + ")")
    return lines or ["(nessuna azione)"]


def fill_cues(t: np.ndarray, dur: float) -> np.ndarray:
    t = np.array(t, dtype=float)
    n = len(t)
    if n == 0:
        return t
    known = np.where(~np.isnan(t))[0]
    if known.size == 0:
        lead = min(2.0, 0.05 * dur)
        return lead + np.arange(n) * max(dur * 0.92 - lead, 1.0) / n
    x = np.concatenate([[0], known + 1, [n + 1]])
    y = np.concatenate(
        [[min(0.5, t[known[0]] * 0.5)], t[known], [max(dur * 0.95, t[known[-1]] + 1)]]
    )
    miss = np.isnan(t)
    if np.any(miss):
        t[miss] = np.interp(np.arange(1, n + 1)[miss], x, y)
    return t


def fast_forward_state(sc: dict, m: int) -> tuple[np.ndarray, np.ndarray]:
    """pos e alpha dopo m passi (per anteprima)."""
    objs = sc.get("objects", [])
    n = len(objs)
    pos = np.zeros((n, 2))
    alpha = np.array([1.0 if o.get("start") else 0.0 for o in objs])
    ids = [o.get("id") for o in objs]
    for k in range(min(m, len(sc.get("steps", [])))):
        for e in normalize_step(sc["steps"][k]):
            try:
                i = ids.index(e.get("spid"))
            except ValueError:
                continue
            cls = e.get("cls")
            if cls == "path":
                pts = np.asarray(e.get("pts", [[0, 0]]))
                pos[i] = pts[-1]
            elif cls == "entr":
                alpha[i] = 1.0
            elif cls == "exit":
                alpha[i] = 0.0
    return pos, alpha


def ease(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return 0.5 - 0.5 * math.cos(math.pi * u)


def state_at(sc: dict, m: int) -> np.ndarray:
    objs = sc.get("objects", [])
    n = len(objs)
    st = np.zeros((n, 3))
    if n == 0:
        return st
    for i, o in enumerate(objs):
        st[i, 2] = 1.0 if o.get("start") else 0.0
    ids = [o.get("id") for o in objs]
    for k in range(min(m, len(sc.get("steps", [])))):
        eff = sc["steps"][k]
        if not eff:
            continue
        if isinstance(eff, dict):
            eff = [eff]
        for e in eff:
            if not isinstance(e, dict):
                continue
            try:
                idx = ids.index(e.get("spid"))
            except ValueError:
                continue
            cls = e.get("cls")
            if cls == "path":
                pts = np.asarray(e.get("pts", [[0, 0]]))
                st[idx, :2] = pts[-1, :2]
            elif cls == "entr":
                st[idx, 2] = 1.0
            elif cls == "exit":
                st[idx, 2] = 0.0
    return st


def normalize_step(eff: Any) -> list[dict]:
    if eff is None:
        return []
    if isinstance(eff, dict):
        return [eff]
    if isinstance(eff, (list, tuple)):
        return [e for e in eff if isinstance(e, dict)]
    return []


def step_duration(eff: list[dict]) -> float:
    t = 0.0
    for e in eff:
        t = max(t, float(e.get("delay", 0)) + float(e.get("dur", 0)))
    return t


def apply_effects_at_time(
    objs: list[dict],
    eff: list[dict],
    pos: np.ndarray,
    alpha: np.ndarray,
    a0: np.ndarray,
    t: float,
) -> None:
    ids = [o.get("id") for o in objs]
    for e in eff:
        try:
            i = ids.index(e.get("spid"))
        except ValueError:
            continue
        u = ease((t - float(e.get("delay", 0))) / max(float(e.get("dur", 0.01)), 0.01))
        cls = e.get("cls")
        o = objs[i]
        if cls == "path":
            p = path_point(np.asarray(e.get("pts", [[0, 0]])), u)
            pos[i] = p
        elif cls == "entr" and t >= float(e.get("delay", 0)):
            alpha[i] = max(a0[i], u)
        elif cls == "exit" and t >= float(e.get("delay", 0)):
            alpha[i] = min(a0[i], 1.0 - u)


def zone_name(p: np.ndarray, t: dict) -> str:
    t = fix_theater(t)
    x, y = float(p[0]), float(p[1])
    w, d = float(t["W"]), float(t["D"])
    if x < -w / 2:
        return "la quinta SX"
    if x > w / 2:
        return "la quinta DX"
    if y > d - 0.4:
        return "il fondale"
    side = "centro"
    if x < -w / 6:
        side = "SX"
    elif x > w / 6:
        side = "DX"
    if y < 0:
        return "il centro del proscenio" if side == "centro" else f"il proscenio {side}"
    if y > 2 * d / 3:
        return f"il fondo, al centro" if side == "centro" else f"il fondo {side}"
    if y > d / 3:
        return f"il centro del palco" if side == "centro" else f"il lato {side}"
    return f"il centro, avanti" if side == "centro" else f"avanti {side}"


def describe_step(objs: list[dict], eff: list[dict], theater: dict) -> list[str]:
    lines = []
    ids = [o.get("id") for o in objs]
    for e in eff:
        try:
            i = ids.index(e.get("spid"))
        except ValueError:
            continue
        o = objs[i]
        nm = o.get("label", o.get("ref", ""))
        cls = e.get("cls")
        if cls == "path":
            pts = np.asarray(e.get("pts", [[0, 0]]))
            p0 = np.array([o.get("x", 0), o.get("y", 0)]) + pts[0]
            p1 = np.array([o.get("x", 0), o.get("y", 0)]) + pts[-1]
            if o.get("kind") == "char":
                lines.append(f"• {nm}: si sposta verso {zone_name(p1, theater)}")
            elif o.get("kind") == "light":
                lines.append(f"• Luce «{nm}»: verso {zone_name(p1, theater)}")
            else:
                lines.append(f"• {nm}: verso {zone_name(p1, theater)}")
        elif cls == "entr":
            lines.append(f"• Luce «{nm}»: si accende" if o.get("kind") == "light" else f"• {nm}: entra in scena")
        elif cls == "exit":
            lines.append(f"• Luce «{nm}»: si spegne" if o.get("kind") == "light" else f"• {nm}: esce di scena")
    return lines
