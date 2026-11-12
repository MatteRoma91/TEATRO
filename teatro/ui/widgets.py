"""Widget riutilizzabili."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog, QPushButton


def rgb_to_css(rgb: list[float]) -> str:
    r, g, b = (max(0, min(255, int(255 * x))) for x in rgb[:3])
    return f"background-color: rgb({r},{g},{b});"


class ColorButton(QPushButton):
    color_changed = Signal(list)

    def __init__(self, rgb: list[float] | None = None, title: str = "Colore", parent=None) -> None:
        super().__init__(parent)
        self._rgb = list(rgb or [0.6, 0.6, 0.6])
        self._title = title
        self.setFixedSize(36, 28)
        self.clicked.connect(self._pick)
        self._apply_style()

    def rgb(self) -> list[float]:
        return self._rgb

    def set_rgb(self, rgb: list[float]) -> None:
        self._rgb = [float(x) for x in rgb[:3]]
        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet(rgb_to_css(self._rgb) + "border: 1px solid #666;")

    def _pick(self) -> None:
        c = QColorDialog.getColor(
            QColor(*(int(255 * x) for x in self._rgb)),
            self,
            self._title,
        )
        if c.isValid():
            self._rgb = [c.redF(), c.greenF(), c.blueF()]
            self._apply_style()
            self.color_changed.emit(self._rgb)
