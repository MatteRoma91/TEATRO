"""Gestione cartelle spettacoli."""

from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from teatro.constants import spettacoli_dir
from teatro.mat_io import load_show, save_show
from teatro.models import default_show, norm_show, safe_name


@dataclass
class ShowEntry:
    folder: str
    title: str
    date: str
    n_scenes: int
    path: Path


def list_shows() -> list[ShowEntry]:
    root = spettacoli_dir()
    out: list[ShowEntry] = []
    for p in sorted(root.iterdir()):
        if not p.is_dir() or p.name.startswith("."):
            continue
        mat = p / "spettacolo.mat"
        js = p / "spettacolo.json"
        if not mat.is_file() and not js.is_file():
            continue
        try:
            sh = load_show(p)
            title = sh.get("title", p.name)
            dt = sh.get("modified", "")
            n = len(sh.get("scenes", []))
        except Exception:
            title, dt, n = p.name, "", 0
        out.append(ShowEntry(folder=p.name, title=title, date=dt, n_scenes=n, path=p))
    out.sort(key=lambda e: e.date or "", reverse=True)
    return out


def unique_folder(base: str) -> str:
    root = spettacoli_dir()
    if not base:
        base = "Spettacolo"
    f = base
    n = 2
    while (root / f).exists():
        f = f"{base} ({n})"
        n += 1
    return f


def create_show(title: str) -> tuple[Path, dict]:
    root = spettacoli_dir()
    folder = unique_folder(safe_name(title))
    dd = root / folder
    dd.mkdir(parents=True)
    (dd / "audio").mkdir(exist_ok=True)
    (dd / "modelli").mkdir(exist_ok=True)
    (dd / "cue").mkdir(exist_ok=True)
    sh = default_show(title.strip())
    save_show(dd, sh)
    return dd, sh


def open_show_folder(dd: Path) -> dict:
    sh = load_show(dd)
    return norm_show(sh)


def duplicate_show(src: Path, title: str | None = None) -> Path:
    sh = load_show(src)
    t = title or f"{sh['title']} (copia)"
    sh["title"] = t
    folder = unique_folder(safe_name(t))
    dst = spettacoli_dir() / folder
    shutil.copytree(src, dst)
    save_show(dst, sh)
    return dst


def delete_show(dd: Path) -> None:
    shutil.rmtree(dd)


def rename_show(dd: Path, new_title: str) -> None:
    sh = load_show(dd)
    sh["title"] = new_title.strip()
    save_show(dd, sh)


def export_zip(dd: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in dd.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(dd.parent))


def import_zip(zip_path: Path) -> Path:
    root = spettacoli_dir()
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        top = names[0].split("/")[0] if names else "import"
        folder = unique_folder(top)
        dest = root / folder
        dest.mkdir(parents=True)
        zf.extractall(dest.parent)
        extracted = dest.parent / top
        if extracted != dest and extracted.exists():
            if dest.exists():
                shutil.rmtree(dest)
            extracted.rename(dest)
    return dest


def find_music_file(show_dir: Path, scene_num: int) -> Path | None:
    audio = show_dir / "audio"
    if not audio.is_dir():
        return None
    prefix = f"{scene_num:02d}"
    exts = (".mp3", ".wav", ".m4a", ".ogg", ".flac")
    for f in sorted(audio.iterdir()):
        if f.suffix.lower() in exts and f.name.startswith(prefix):
            return f
    return None
