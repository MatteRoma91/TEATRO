"""Colori e costanti UI (come TeatroApp.m)."""

from pathlib import Path

BG = (0.08, 0.09, 0.11)
PANEL = (0.13, 0.145, 0.17)
GOLD = (0.83, 0.69, 0.35)
TXT = (0.95, 0.93, 0.89)
DIM = (0.7, 0.67, 0.62)

SLOTS = (
    "Sopra",
    "Gilet",
    "Giacca",
    "Mantello",
    "Sotto",
    "Abito",
    "Scarpe",
    "Cappello",
    "Accessorio",
    "Accessorio",
)
SLOT_LABELS = (
    "Maglia / camicia",
    "Gilet",
    "Giacca",
    "Mantello",
    "Pantaloni / gonna",
    "Abito intero",
    "Scarpe",
    "Cappello",
    "Accessorio 1",
    "Accessorio 2",
)

SKINS = (
    ("Molto chiara", (0.96, 0.84, 0.74)),
    ("Chiara", (0.93, 0.76, 0.62)),
    ("Media", (0.82, 0.62, 0.46)),
    ("Olivastra", (0.74, 0.55, 0.38)),
    ("Scura", (0.55, 0.37, 0.25)),
    ("Molto scura", (0.36, 0.24, 0.17)),
)

EYES = (
    ("Castani", (0.29, 0.2, 0.14)),
    ("Nocciola", (0.45, 0.32, 0.18)),
    ("Verdi", (0.24, 0.42, 0.23)),
    ("Azzurri", (0.29, 0.48, 0.66)),
    ("Grigi", (0.45, 0.48, 0.5)),
    ("Neri", (0.1, 0.08, 0.07)),
)

BROWS = ("sottili", "normali", "folte")

MAKEUP = (
    ("lips", "Rossetto"),
    ("lashes", "Rimmel / eyeliner"),
    ("shadow", "Ombretto"),
    ("blush", "Fard"),
)

THEATER_PRESETS = (
    "Personalizzato",
    "Piccolo (8 x 7 m, h 5 m, 2 quinte)",
    "Medio (10 x 9 m, h 7 m, 3 quinte)",
    "Grande (14 x 11,5 m, h 9 m, 4 quinte)",
    "Molto grande (18 x 16 m, h 12 m, 5 quinte)",
)

THEATER_PRESET_VALUES = [
    None,
    (8, 7, 5, 2, 1.0),
    (10, 9.2, 7, 3, 1.2),
    (14, 11.5, 9, 4, 1.5),
    (18, 16, 12, 5, 2.0),
]

BACKDROP_OPTIONS = (
    "Nero",
    "Ciclorama bianco",
    "Grigio",
    "Immagine (foto o disegno)",
    "Modello 3D",
)

ZONES = (
    "Tutto il palco",
    "Avanti",
    "Centro",
    "Fondo",
    "Sinistra",
    "Destra",
    "Fondale (ciclorama)",
    "Puntiforme (centro)",
    "Segue un personaggio",
)


def app_root() -> Path:
    """Cartella con TeatroApp.exe e spettacoli/ (dati utente)."""
    import sys

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def bundle_root() -> Path:
    """Risorse incluse nel pacchetto (PyInstaller 6: sotto _internal/)."""
    import sys

    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
        internal = base / "_internal"
        if internal.is_dir():
            return internal
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return base
    return app_root()


def libreria_dir() -> Path:
    return bundle_root() / "libreria"


def spettacoli_dir() -> Path:
    d = app_root() / "spettacoli"
    d.mkdir(parents=True, exist_ok=True)
    return d
