"""Export PDF copione e passi scena."""

from __future__ import annotations

import textwrap
from pathlib import Path

import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from teatro.models import roman, safe_name
from teatro.scene_logic import cast_code, cue_text, describe_step, normalize_step, state_at
from teatro.cues import fmt_time, load_cues


def _wrap(s: str, width: int = 92) -> list[str]:
    return textwrap.wrap(s, width=width) or [""]


def scene_rows(sh: dict, sc: dict, cue_t: np.ndarray | None) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    if sc.get("start"):
        for ln in _wrap(f"Situazione iniziale: {sc['start']}"):
            rows.append((ln, "i"))
    chars_seen = []
    for o in sc.get("objects", []):
        if o.get("kind") != "char" or o.get("ref") in chars_seen:
            continue
        chars_seen.append(o.get("ref"))
        ci = next((j for j, c in enumerate(sh.get("chars", [])) if c.get("name") == o.get("ref")), -1)
        desc = ""
        if ci >= 0:
            code = cast_code(sc, o.get("ref", ""))
            for co in sh["chars"][ci].get("costumes", []):
                if co.get("code") == code:
                    desc = co.get("desc", "")
        part = f"{o.get('ref')} (costume {code}" + (f": {desc}" if desc else "") + ")"
        for ln in _wrap("Personaggi: " + ", ".join([part])):
            rows.append((ln, "i"))
    if rows:
        rows.append(("", "g"))
    steps = sc.get("steps", [])
    for k, eff in enumerate(steps, start=1):
        t = f"Passo {k} — {cue_text(sc, k)}"
        if cue_t is not None and k <= len(cue_t) and cue_t[k - 1] == cue_t[k - 1]:
            t += f"   [{fmt_time(float(cue_t[k - 1]))}]"
        for ln in _wrap(t, 78):
            rows.append((ln, "h"))
        objs = sc.get("objects", [])
        for ac in describe_step(objs, normalize_step(eff), sh.get("theater", {})):
            for ln in _wrap("     " + ac):
                rows.append((ln, "d"))
        ens = sc.get("ens", [])
        if k <= len(ens) and ens[k - 1]:
            for ln in _wrap(f"     Corpo di ballo: {ens[k - 1]}"):
                rows.append((ln, "b"))
        rows.append(("", "g"))
    if not steps:
        rows.append(("Nessun passo in questa scena.", "d"))
    return rows


def _render_pdf(path: Path, title: str, subtitle: str, rows: list[tuple[str, str]], footer: str) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    y = h - 2 * cm
    page = 1

    def new_page() -> None:
        nonlocal y, page
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawRightString(w - 2 * cm, 1.2 * cm, f"{footer} — pag. {page}")
        c.showPage()
        page += 1
        y = h - 2 * cm

    c.setFont("Helvetica-Bold", 18)
    c.setFillColorRGB(0.45, 0.3, 0.05)
    c.drawCentredString(w / 2, y, title)
    y -= 1.2 * cm
    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawCentredString(w / 2, y, subtitle)
    y -= 1.5 * cm
    for tx, kind in rows:
        if y < 3 * cm:
            new_page()
        if not tx and kind == "g":
            y -= 0.3 * cm
            continue
        if kind == "h":
            c.setFont("Helvetica-Bold", 11)
            c.setFillColorRGB(0.1, 0.1, 0.1)
            dy = 0.45 * cm
        elif kind == "d":
            c.setFont("Helvetica", 9.5)
            c.setFillColorRGB(0.22, 0.22, 0.22)
            dy = 0.38 * cm
        elif kind == "b":
            c.setFont("Helvetica-Oblique", 9.5)
            c.setFillColorRGB(0.35, 0.22, 0.45)
            dy = 0.38 * cm
        else:
            c.setFont("Helvetica", 10)
            c.setFillColorRGB(0.3, 0.25, 0.15)
            dy = 0.4 * cm
        c.drawString(2 * cm, y, tx[:120])
        y -= dy
    c.save()


def export_scene_pdf(path: Path, sh: dict, sc: dict, show_dir: Path) -> None:
    cue_t, _ = load_cues(show_dir, sc)
    rows = scene_rows(sh, sc, cue_t)
    subtitle = f"Atto {roman(int(sc.get('act', 1)))} · Scena {sc.get('num', 0)} · {sh.get('title', '')}"
    _render_pdf(path, sc.get("title", "Scena"), subtitle, rows, sc.get("title", ""))


def export_full_script(path: Path, sh: dict, show_dir: Path) -> None:
    scenes = sorted(sh.get("scenes", []), key=lambda s: (int(s.get("act", 1)), int(s.get("num", 0))))
    rows: list[tuple[str, str]] = []
    rows.append((sh.get("title", "Spettacolo"), "s"))
    rows.append(("", "g"))
    for sc in scenes:
        cue_t, _ = load_cues(show_dir, sc)
        hdr = f"ATTO {roman(int(sc.get('act', 1)))} — SCENA {sc.get('num', 0)} — {sc.get('title', '')}"
        rows.append((hdr, "h"))
        rows.extend(scene_rows(sh, sc, cue_t))
    _render_pdf(path, sh.get("title", "Copione"), "Copione completo", rows, sh.get("title", ""))
