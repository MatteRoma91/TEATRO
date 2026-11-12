"""Geometria palco e pianta (drawStagePlan)."""

from __future__ import annotations

from typing import Any

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np


def fix_theater(t: dict[str, Any]) -> dict[str, Any]:
    t = dict(t)
    if "Dtot" not in t and "D" in t and "P" in t:
        t["Dtot"] = float(t["D"]) + float(t["P"])
    if "D" not in t and "Dtot" in t and "P" in t:
        t["D"] = float(t["Dtot"]) - float(t["P"])
    for k, default in (
        ("W", 10.0),
        ("H", 7.0),
        ("nq", 3),
        ("wing", 2.0),
        ("P", 1.2),
        ("back", "Nero"),
        ("backImg", ""),
        ("backModel", ""),
    ):
        t.setdefault(k, default)
    return t


def quinte_step(t: dict) -> float:
    nq = int(t["nq"])
    if nq <= 0:
        return 0.0
    return float(t["D"]) / nq


def quinte_width(t: dict) -> float:
    s = quinte_step(t)
    return s * 1.15 if s > 0 else 0.0


def quinte_y(t: dict) -> np.ndarray:
    nq = int(t["nq"])
    if nq <= 0:
        return np.array([])
    s = quinte_step(t)
    return np.array([(i) * s + 0.25 * s for i in range(nq)])


def draw_stage_plan(ax, t: dict, labels: bool = False) -> None:
    t = fix_theater(t)
    w = float(t["W"])
    d = float(t["D"])
    p = float(t["P"])
    wg = float(t["wing"])
    xa, xb = -w / 2 - wg, w / 2 + wg

    ax.set_facecolor((0.08, 0.09, 0.11))
    ax.add_patch(
        mpatches.Polygon(
            [[xa, 0], [xb, 0], [xb, d], [xa, d]],
            closed=True,
            facecolor=(0.12, 0.12, 0.14),
            edgecolor="none",
        )
    )
    ax.add_patch(
        mpatches.Polygon(
            [[-w / 2, 0], [w / 2, 0], [w / 2, d], [-w / 2, d]],
            closed=True,
            facecolor=(0.34, 0.26, 0.19),
            edgecolor="none",
        )
    )
    ax.add_patch(
        mpatches.Polygon(
            [[xa, -p], [xb, -p], [xb, 0], [xa, 0]],
            closed=True,
            facecolor=(0.4, 0.31, 0.22),
            edgecolor="none",
        )
    )
    for yy in range(int(d) + 1):
        ax.plot([-w / 2, w / 2], [yy, yy], color=(0.3, 0.23, 0.17), linewidth=0.5)
    for xx in range(int(np.ceil(-w / 2)), int(np.floor(w / 2)) + 1):
        ax.plot([xx, xx], [0, d], color=(0.3, 0.23, 0.17), linewidth=0.5)
    qw = quinte_width(t)
    for yy in quinte_y(t):
        for sd in (-1, 1):
            x0 = sd * (w / 2 - 0.2)
            x1 = sd * (w / 2 - 0.2 + qw)
            ax.plot([x0, x1], [yy, yy], color="black", linewidth=5, solid_capstyle="butt")
    ax.plot([xa, xb], [d, d], color=(0.05, 0.05, 0.05), linewidth=7)
    ax.plot([xa, xb], [0, 0], color=(0.75, 0.2, 0.2), linewidth=1, linestyle="--")
    ax.plot(0, 0, marker="^", color=(0.9, 0.9, 0.9), markersize=5)
    tc = (0.75, 0.72, 0.66)
    ax.text(0, -p - 0.55, "PUBBLICO", color=tc, fontsize=10, fontweight="bold", ha="center")
    ax.text(0, d + 0.35, "FONDALE", color=tc, fontsize=8, ha="center")
    ax.text(xa + 0.1, d / 2, "QUINTE SX", color=tc, fontsize=8, rotation=90, va="center", ha="center")
    ax.text(xb - 0.1, d / 2, "QUINTE DX", color=tc, fontsize=8, rotation=-90, va="center", ha="center")
    ax.text(xb, -p / 2, "proscenio", color=tc, fontsize=7, ha="right")
    if labels:
        ax.text(0, d / 2, f"{w:g} x {d:g} m", color="white", fontsize=12, ha="center")
    ax.set_xlim(xa - 0.4, xb + 0.4)
    ax.set_ylim(-p - 1.0, d + 0.7)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def plot_objects_on_plan(ax, objects: list[dict], chars: list[dict]) -> None:
    """Disegna pedine oggetti/personaggi sulla pianta."""
    char_by_name = {c["name"]: c for c in chars}
    for ob in objects:
        if not ob.get("start", True):
            continue
        x, y = float(ob.get("x", 0)), float(ob.get("y", 0))
        kind = ob.get("kind", "")
        if kind == "char":
            ch = char_by_name.get(ob.get("ref", ""), {})
            col = ch.get("pawn", [0.9, 0.9, 0.9])
            ax.plot(x, y, "o", color=col, markersize=12, markeredgecolor="white", markeredgewidth=0.8)
            lbl = ob.get("label") or ob.get("ref", "")
            if lbl:
                ax.text(x, y + 0.35, lbl, color=(0.95, 0.93, 0.89), fontsize=8, ha="center")
        else:
            rgb = ob.get("rgb", [0.7, 0.7, 0.7])
            ax.plot(x, y, "s", color=rgb, markersize=10, markeredgecolor="white", markeredgewidth=0.5)


def zone_geom(zone: str, t: dict, p: np.ndarray | None = None) -> dict:
    t = fix_theater(t)
    p = np.array([0.0, 0.0]) if p is None else np.asarray(p, dtype=float)
    w, d, p_proc = float(t["W"]), float(t["D"]), float(t["P"])
    g = {"shape": "rect", "cx": 0.0, "cy": d / 2, "w": w, "h": d, "r": 1.0}
    if zone == "Tutto il palco":
        g["cy"], g["h"] = (d - p_proc) / 2, d + p_proc
    elif zone == "Avanti":
        g["cy"], g["h"] = (-p_proc + 0.4 * d) / 2, 0.4 * d + p_proc
    elif zone == "Centro":
        g["w"], g["h"], g["cy"] = 0.55 * w, 0.5 * d, 0.5 * d
    elif zone == "Fondo":
        g["cy"], g["h"] = 0.8 * d, 0.4 * d
    elif zone == "Sinistra":
        g["cx"], g["w"], g["cy"], g["h"] = -w / 3, w / 3, (d - p_proc) / 2, d + p_proc
    elif zone == "Destra":
        g["cx"], g["w"], g["cy"], g["h"] = w / 3, w / 3, (d - p_proc) / 2, d + p_proc
    elif zone == "Fondale (ciclorama)":
        g.update({"shape": "cyc", "cy": d - 0.15, "w": w + 2 * t["wing"], "h": 0.3})
    elif zone == "Puntiforme (centro)":
        g.update({"shape": "circle", "r": 1.1, "cy": d / 2})
    elif zone == "Segue un personaggio":
        g.update({"shape": "circle", "r": 0.6, "cx": p[0], "cy": p[1]})
    return g


def new_figure_stage(t: dict, objects: list | None = None, chars: list | None = None):
    fig, ax = plt.subplots(figsize=(8, 5))
    draw_stage_plan(ax, t, labels=False)
    if objects:
        plot_objects_on_plan(ax, objects, chars or [])
    fig.tight_layout(pad=0.5)
    return fig, ax
