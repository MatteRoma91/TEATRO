"""Finestra impostazioni spettacolo (4 schede)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTabWidget, QVBoxLayout

from teatro.ui.tabs.chars_tab import CharsTab
from teatro.ui.tabs.elements_tab import ElementsTab
from teatro.ui.tabs.lights_tab import LightsTab
from teatro.ui.tabs.theater_tab import TheaterTab


class SettingsDialog(QDialog):
    def __init__(
        self,
        parent,
        sh: dict,
        show_dir: Path | None = None,
        tab: int = 0,
        on_save=None,
    ) -> None:
        super().__init__(parent)
        self.sh = sh
        self._on_save = on_save
        self.setWindowTitle(f"Impostazioni — {sh.get('title', '')}")
        self.resize(1100, 720)

        lay = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tab_theater = TheaterTab(sh, show_dir)
        self.tab_lights = LightsTab(sh)
        self.tab_elements = ElementsTab(sh)
        self.tab_chars = CharsTab(sh)
        self.tabs.addTab(self.tab_theater, "1. Teatro")
        self.tabs.addTab(self.tab_lights, "2. Luci")
        self.tabs.addTab(self.tab_elements, "3. Scenografia")
        self.tabs.addTab(self.tab_chars, "4. Personaggi e costumi")
        self.tabs.setCurrentIndex(min(tab, 3))
        lay.addWidget(self.tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Salva e chiudi")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def _accept(self) -> None:
        self.tab_theater._read_fields()
        if self._on_save:
            self._on_save()
        self.accept()
