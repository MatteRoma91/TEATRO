"""Vista 3D platea (matplotlib)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from teatro.parts3d import PartsCache, char_parts, element_parts
from teatro.scene_logic import cast_code
from teatro.theater import fix_theater, quinte_width, quinte_y


def _add_parts(ax, parts: list[dict], tx: float, ty: float, rot_deg: float = 0, alpha: float = 1.0) -> None:
    rot = np.radians(rot_deg)
    rm = np.array([[np.cos(rot), -np.sin(rot), 0], [np.sin(rot), np.cos(rot), 0], [0, 0, 1]])
    for part in parts:
        v = part["V"] @ rm.T + np.array([tx, ty, 0])
        f = np.asarray(part["F"], dtype=int)
        c = np.asarray(part["C"])
        polys = []
        cols = []
        for tri in f:
            if tri.max() >= v.shape[0]:
                continue
            polys.append(v[tri])
            cols.append(c[tri[0]])
        if not polys:
            continue
        coll = Poly3DCollection(
            polys,
            facecolors=cols,
            edgecolors="none",
            alpha=float(part.get("alpha", 1)) * alpha,
        )
        ax.add_collection3d(coll)


def draw_stage_3d(
    ax,
    sh: dict,
    sc: dict,
    show_dir: Path,
    pos: np.ndarray,
    alpha: np.ndarray,
    cache: PartsCache,
) -> None:
    ax.cla()
    ax.set_facecolor((0, 0, 0))
    T = fix_theater(sh["theater"])
    w, d, p, wg, hh = float(T["W"]), float(T["D"]), float(T["P"]), float(T["wing"]), float(T["H"])
    xa, xb = -w / 2 - wg, w / 2 + wg
    # pavimento
    floor = [[xa, -p, 0], [xb, -p, 0], [xb, d, 0], [xa, d, 0]]
    ax.add_collection3d(
        Poly3DCollection([floor], facecolors=[(0.36, 0.27, 0.19)], edgecolors="none", alpha=1.0)
    )
    # fondale
    bc = {
        "Ciclorama bianco": (0.85, 0.85, 0.85),
        "Grigio": (0.35, 0.35, 0.36),
    }.get(T.get("back", "Nero"), (0.05, 0.05, 0.06))
    back = [[xa, d, 0], [xb, d, 0], [xb, d, hh], [xa, d, hh]]
    ax.add_collection3d(Poly3DCollection([back], facecolors=[bc], edgecolors="none", alpha=1.0))
  # quinte
    for yy in quinte_y(T):
        qw = quinte_width(T)
        for sd in (-1, 1):
            x0 = sd * (w / 2 - 0.2)
            q = [[x0, yy, 0], [x0 + sd * qw, yy, 0], [x0 + sd * qw, yy, hh], [x0, yy, hh]]
            ax.add_collection3d(Poly3DCollection([q], facecolors=[(0.06, 0.06, 0.07)], edgecolors="none"))
    # elementi fissi
    for e in sh.get("elements", []):
        if not e.get("fixed"):
            continue
        pp = element_parts(sh, show_dir, e, cache)
        if pp:
            _add_parts(ax, pp, float(e.get("x", 0)), float(e.get("y", 0)), float(e.get("rot", 0)))
    objs = sc.get("objects", [])
    chars = sh.get("chars", [])
    for i, o in enumerate(objs):
        a = float(alpha[i]) if i < len(alpha) else 0.0
        if a < 0.02:
            continue
        dx, dy = (float(pos[i, 0]), float(pos[i, 1])) if i < len(pos) else (0.0, 0.0)
        x = float(o.get("x", 0)) + dx
        y = float(o.get("y", 0)) + dy
        if o.get("kind") == "char":
            ci = next((j for j, c in enumerate(chars) if c.get("name") == o.get("ref")), -1)
            if ci >= 0:
                code = cast_code(sc, o.get("ref", ""))
                pp = char_parts(sh, show_dir, ci, code, cache)
                if pp:
                    _add_parts(ax, pp, x, y, alpha=a)
        elif o.get("kind") == "el":
            ei = next((j for j, e in enumerate(sh.get("elements", [])) if e.get("name") == o.get("ref")), -1)
            if ei >= 0:
                pp = element_parts(sh, show_dir, sh["elements"][ei], cache)
                if pp:
                    _add_parts(ax, pp, x, y, float(o.get("rot", 0)), alpha=a)
    ax.set_xlim(xa - 2, xb + 2)
    ax.set_ylim(-p - 3, d + 2)
    ax.set_zlim(-0.5, hh + 1)
    ax.set_box_aspect((1, 1, 0.5))
    ax.view_init(elev=18, azim=-65)
    ax.set_axis_off()
