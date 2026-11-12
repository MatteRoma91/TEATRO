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
