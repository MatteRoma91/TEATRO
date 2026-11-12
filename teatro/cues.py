"""File tempi passi (cue CSV)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from teatro.scene_logic import cue_text


def cue_file(show_dir: Path, scene_uid: int) -> Path:
    d = show_dir / "cue"
    d.mkdir(exist_ok=True)
    return d / f"scena_{scene_uid}.cue.csv"


def parse_time(s: str) -> float:
    s = str(s).strip().replace(",", ".")
    if not s:
        return float("nan")
    if ":" in s:
        parts = s.split(":")
        try:
            return float(parts[-2]) * 60 + float(parts[-1])
        except (ValueError, IndexError):
            return float("nan")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def fmt_time(t: float) -> str:
    if t != t:
        return ""
    m = int(t // 60)
    x = t - 60 * m
    return f"{m:02d}:{x:04.1f}"


def load_cues(show_dir: Path, sc: dict) -> tuple[np.ndarray, np.ndarray]:
    n = len(sc.get("steps", []))
    t = np.full(n, np.nan)
    e = np.full(n, np.nan)
    f = cue_file(show_dir, int(sc.get("uid", 0)))
    if not f.is_file():
        return t, e
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
        parts = line.split(";")
        if len(parts) < 2:
            continue
        try:
            k = int(parts[0])
        except ValueError:
            continue
        if k < 1 or k > n:
            continue
        t[k - 1] = parse_time(parts[1])
        if len(parts) >= 3:
            e[k - 1] = parse_time(parts[2])
    return t, e


def save_cues(show_dir: Path, sc: dict, t: np.ndarray, e: np.ndarray) -> None:
    f = cue_file(show_dir, int(sc.get("uid", 0)))
    lines = ["passo;inizio;fine;descrizione\n"]
    for k in range(len(t)):
        desc = cue_text(sc, k + 1).replace(";", ",")
        lines.append(f"{k + 1};{fmt_time(t[k])};{fmt_time(e[k])};{desc}\n")
    f.write_text("".join(lines), encoding="utf-8")
