"""Canvas matplotlib interattivo per la pianta del palco."""

from __future__ import annotations

from typing import Callable

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from teatro.plan2d import ScenePlan2D


class PlanCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None) -> None:
        self.fig = Figure(figsize=(7, 5), facecolor=(0.08, 0.09, 0.11))
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self._plan = ScenePlan2D(self.ax)
        self._on_click: Callable[[float, float], None] | None = None
        self._on_drag: Callable[[float, float], None] | None = None
        self._on_release: Callable[[], None] | None = None
        self._dragging = False
        self.mpl_connect("button_press_event", self._press)
        self.mpl_connect("motion_notify_event", self._move)
        self.mpl_connect("button_release_event", self._release)

    def set_handlers(
        self,
        on_click=None,
        on_drag=None,
        on_release=None,
    ) -> None:
        self._on_click = on_click
        self._on_drag = on_drag
        self._on_release = on_release

    def draw_scene(self, sh: dict, sc: dict, pos: np.ndarray, alpha: np.ndarray, fixed_only: bool = False) -> None:
        self._plan.draw(sh, sc, pos, alpha)
        if fixed_only:
            pass  # fixed drawn via objects with start in sc
        self.draw_idle()

    def draw_base(self, sh: dict) -> None:
        self.ax.clear()
        draw_stage_plan(self.ax, sh["theater"])
        self.draw_idle()

    def _pt(self, event) -> tuple[float, float] | None:
        if event.inaxes != self.ax or event.xdata is None:
            return None
        return float(event.xdata), float(event.ydata)

    def _press(self, event) -> None:
        p = self._pt(event)
        if p and self._on_click:
            self._on_click(p[0], p[1])
        self._dragging = True

    def _move(self, event) -> None:
        if not self._dragging or not self._on_drag:
            return
        p = self._pt(event)
        if p:
            self._on_drag(p[0], p[1])

    def _release(self, event) -> None:
        self._dragging = False
        if self._on_release:
            self._on_release()
