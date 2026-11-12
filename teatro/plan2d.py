"""Disegno pianta con oggetti in scena (montaggio 2D)."""

from __future__ import annotations

import numpy as np
import matplotlib.patches as mpatches

from teatro.theater import draw_stage_plan, fix_theater, zone_geom


class ScenePlan2D:
    def __init__(self, ax) -> None:
        self.ax = ax
        self._patches: list = []
        self._texts: list = []

    def clear(self) -> None:
        for a in self._patches + self._texts:
            try:
                a.remove()
            except Exception:
                pass
        self._patches.clear()
        self._texts.clear()

    def draw(self, sh: dict, sc: dict, pos: np.ndarray, alpha: np.ndarray) -> None:
        self.clear()
        self.ax.clear()
        draw_stage_plan(self.ax, sh["theater"])
        objs = sc.get("objects", [])
        t = fix_theater(sh["theater"])
        for i, o in enumerate(objs):
            a = float(alpha[i]) if i < len(alpha) else 0.0
            if a < 0.02:
                continue
            dx, dy = (float(pos[i, 0]), float(pos[i, 1])) if i < len(pos) else (0.0, 0.0)
            x = float(o.get("x", 0)) + dx
            y = float(o.get("y", 0)) + dy
            kind = o.get("kind", "")
            if kind == "char":
                rgb = o.get("rgb", [0.8, 0.2, 0.2])
                circ = mpatches.Circle((x, y), 0.3, facecolor=rgb, edgecolor="white", linewidth=1.2, alpha=a)
                self.ax.add_patch(circ)
                self._patches.append(circ)
                lbl = self.ax.text(x, y, (o.get("label") or "")[:3], ha="center", va="center", fontsize=7, color="white")
                self._texts.append(lbl)
            elif kind == "el":
                w, d = max(float(o.get("w", 0.5)), 0.1), max(float(o.get("d", 0.5)), 0.1)
                rot = np.radians(float(o.get("rot", 0)))
                c = np.array([[-w, -d], [w, -d], [w, d], [-w, d]]) / 2
                rm = np.array([[np.cos(rot), -np.sin(rot)], [np.sin(rot), np.cos(rot)]])
                c = c @ rm.T + np.array([x, y])
                rgb = np.array(o.get("rgb", [0.6, 0.6, 0.6]))
                poly = mpatches.Polygon(c, facecolor=0.5 + 0.5 * rgb, edgecolor=rgb * 0.6, alpha=0.85 * a)
                self.ax.add_patch(poly)
                self._patches.append(poly)
            else:
                g = zone_geom(o.get("zone", ""), t, np.array([x, y]))
                if g["shape"] == "circle":
                    circ = mpatches.Circle((x, y), g["r"], facecolor=o.get("rgb", [1, 1, 0.5]), alpha=0.35 * a)
                    self.ax.add_patch(circ)
                    self._patches.append(circ)
                else:
                    w, h = g["w"], g["h"]
                    rect = mpatches.Rectangle((x - w / 2, y - h / 2), w, h, facecolor=o.get("rgb", [1, 1, 0.5]), alpha=0.26 * a)
                    self.ax.add_patch(rect)
                    self._patches.append(rect)
