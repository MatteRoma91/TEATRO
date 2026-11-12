"""Lettura catalogo.csv."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class CatalogItem:
    cat: str
    id: str
    name: str
    hex: str
    rgb: tuple[float, float, float]
    size: tuple[float, float, float]


def read_catalog(path: Path) -> list[CatalogItem]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = [ln.strip() for ln in text.replace("\r\n", "\n").split("\n") if ln.strip()]
    out: list[CatalogItem] = []
    for line in lines[1:]:
        parts = line.split(";")
        while len(parts) < 8:
            parts.append("")
        hx = parts[4].strip()
        if len(hx) == 6:
            rgb = (
                int(hx[0:2], 16) / 255.0,
                int(hx[2:4], 16) / 255.0,
                int(hx[4:6], 16) / 255.0,
            )
        else:
            rgb = (0.6, 0.6, 0.6)

        def _f(s: str) -> float:
            try:
                v = float(s.strip())
                return 1.0 if v != v else v
            except ValueError:
                return 1.0

        sz = (_f(parts[5]), _f(parts[6]), _f(parts[7]))
        out.append(
            CatalogItem(
                cat=parts[0].strip(),
                id=parts[1].strip(),
                name=parts[2].strip(),
                hex=hx,
                rgb=rgb,
                size=sz,
            )
        )
    return out
