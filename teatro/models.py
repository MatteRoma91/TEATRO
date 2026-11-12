"""Modelli dati spettacolo (equivalente struct SH MATLAB)."""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Any


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def light_colours() -> tuple[list[str], list[list[float]]]:
    names = [
        "Bianco",
        "Bianco caldo",
        "Ambra",
        "Rosso",
        "Rosa",
        "Viola",
        "Blu",
        "Azzurro",
        "Verde",
        "Personalizzato",
    ]
    values = [
        [1, 1, 0.95],
        [1, 0.86, 0.62],
        [1, 0.68, 0.25],
        [1, 0.15, 0.12],
        [1, 0.45, 0.7],
        [0.62, 0.3, 1],
        [0.25, 0.4, 1],
        [0.45, 0.75, 1],
        [0.3, 0.9, 0.4],
        [1, 1, 1],
    ]
    return names, values


def light_library() -> list[dict[str, Any]]:
    def add(t, n, z, c, q):
        return {"type": t, "note": n, "zone": z, "col": c, "qty": q}

    return [
        add("Piazzato PC", "luce generale morbida", "Tutto il palco", "Bianco caldo", 6),
        add("Fresnel", "luce generale, bordi morbidi", "Avanti", "Bianco caldo", 4),
        add("PAR LED RGB", "colore a scelta", "Tutto il palco", "Blu", 8),
        add("Controluce", "da dietro, stacca le figure", "Fondo", "Azzurro", 4),
        add("Testa mobile wash", "luce colorata su una zona", "Centro", "Viola", 2),
        add("Sagomatore", "luce precisa su un punto", "Puntiforme (centro)", "Bianco", 2),
        add("Gobo", "disegni proiettati a terra", "Centro", "Verde", 2),
        add("Seguipersona (occhio di bue)", "segue un personaggio", "Segue un personaggio", "Bianco", 1),
        add("Testa mobile spot", "segue un personaggio", "Segue un personaggio", "Bianco", 2),
        add("Strip LED ciclorama", "colora il fondale", "Fondale (ciclorama)", "Blu", 4),
        add("Ribalta", "dal basso, sul proscenio", "Avanti", "Ambra", 4),
        add("Luce da sinistra", "taglio laterale", "Sinistra", "Bianco", 2),
        add("Luce da destra", "taglio laterale", "Destra", "Bianco", 2),
        add("Strobo", "lampi", "Tutto il palco", "Bianco", 1),
    ]


def new_light(name: str, typ: str, qty: int, cname: str, rgb: list[float], zone: str) -> dict:
    return {
        "name": name,
        "type": typ,
        "qty": int(qty),
        "cname": cname,
        "rgb": list(rgb),
        "zone": zone,
    }


def new_element() -> dict:
    return {
        "name": "",
        "src": "lib",
        "file": "",
        "size": [1.0, 1.0, 1.0],
        "rgb": [1.0, 1.0, 1.0],
        "tint": False,
        "fixed": False,
        "x": 0.0,
        "y": 0.0,
        "rot": 0.0,
        "occ": "",
        "how": "",
    }


def new_char(name: str, sex: str, idx: int) -> dict:
    pal = [
        [0.85, 0.15, 0.15],
        [0.2, 0.45, 0.9],
        [0.2, 0.7, 0.3],
        [0.95, 0.8, 0.2],
        [0.55, 0.35, 0.18],
        [0.6, 0.3, 0.8],
        [0.1, 0.1, 0.1],
        [0.95, 0.5, 0.15],
        [0.62, 0.62, 0.65],
        [0.1, 0.65, 0.7],
    ]
    ht = 1.78 if sex == "M" else 1.66
    return {
        "name": name,
        "pawn": pal[(idx - 1) % len(pal)],
        "sex": sex,
        "height": ht,
        "skin": [0.93, 0.76, 0.62],
        "eyes": [0.29, 0.2, 0.14],
        "costumes": [new_costume("A", sex)],
        "rev": 1,
    }


def new_costume(code: str, sex: str) -> dict:
    mk = {
        "lips": 0,
        "lipsRGB": [0.7, 0.15, 0.2],
        "lashes": 0,
        "lashesRGB": [0.06, 0.05, 0.05],
        "shadow": 0,
        "shadowRGB": [0.45, 0.35, 0.55],
        "blush": 0,
        "blushRGB": [0.85, 0.45, 0.45],
        "brows": "normali",
        "browsRGB": [0.2, 0.13, 0.08],
    }
    co = {
        "code": code,
        "desc": f"costume {code}",
        "mode": "lib",
        "file": "",
        "items": [""] * 10,
        "irgb": [[0.5, 0.5, 0.5]] * 10,
        "hair": "corti",
        "hairRGB": [0.23, 0.14, 0.09],
        "facial": "",
        "facialRGB": [0.2, 0.13, 0.08],
        "mk": mk,
    }
    _set_item(co["items"], "Sopra", "tshirt")
    co["irgb"][0] = [0.95, 0.95, 0.95]
    _set_item(co["items"], "Sotto", "jeans")
    co["irgb"][4] = [0.23, 0.36, 0.55]
    _set_item(co["items"], "Scarpe", "scarpe")
    co["irgb"][6] = [0.16, 0.11, 0.07]
    if sex == "F":
        co["hair"] = "lisci"
        co["hairRGB"] = [0.35, 0.2, 0.1]
        co["mk"]["brows"] = "sottili"
    return co


def _set_item(items: list[str], slot: str, item_id: str) -> None:
    from teatro.constants import SLOTS

    try:
        k = SLOTS.index(slot)
        items[k] = item_id
    except ValueError:
        pass


def new_scene(uid: int, act: int, num: int, title: str, start: str) -> dict:
    return {
        "uid": int(uid),
        "act": int(act) if act == act else 1,
        "num": int(num) if num == num else 1,
        "title": title,
        "start": start,
        "cast": [],
        "objects": [],
        "steps": [],
        "cues": [],
        "ens": [],
    }


def default_show(title: str) -> dict:
    from teatro.theater import fix_theater

    names, values = light_colours()

    def c(n: str) -> list[float]:
        i = names.index(n)
        return values[i]

    created = _now_str()
    return {
        "title": title,
        "created": created,
        "modified": created,
        "theater": fix_theater(
            {
                "W": 10.0,
                "Dtot": 9.2,
                "D": 8.0,
                "H": 7.0,
                "nq": 3,
                "wing": 2.0,
                "P": 1.2,
                "back": "Nero",
                "backImg": "",
                "backModel": "",
            }
        ),
        "lights": [
            new_light("Piazzato caldo", "Piazzato PC", 6, "Bianco caldo", c("Bianco caldo"), "Tutto il palco"),
            new_light("Controluce blu", "Controluce", 4, "Blu", c("Blu"), "Fondo"),
            new_light("Ciclorama", "Strip LED ciclorama", 4, "Azzurro", c("Azzurro"), "Fondale (ciclorama)"),
            new_light(
                "Occhio di bue",
                "Seguipersona (occhio di bue)",
                1,
                "Bianco",
                c("Bianco"),
                "Segue un personaggio",
            ),
        ],
        "elements": [],
        "chars": [],
        "scenes": [],
        "nextId": 0,
    }


def norm_show(sh: dict) -> dict:
    """Allinea campi mancanti (come normShow in MATLAB)."""
    d = default_show(sh.get("title", "Spettacolo"))
    for key, val in d.items():
        if key not in sh:
            sh[key] = copy.deepcopy(val)
    th = sh["theater"]
    dth = d["theater"]
    if "Dtot" not in th and "D" in th and "P" in th:
        th["Dtot"] = float(th["D"]) + float(th["P"])
    for fk, fv in dth.items():
        if fk not in th:
            th[fk] = fv
    from teatro.theater import fix_theater

    sh["theater"] = fix_theater(th)
    if not isinstance(sh["scenes"], list):
        sh["scenes"] = list(sh["scenes"])
    mx = int(sh.get("nextId", 0))
    scenes_out = []
    for sc in sh["scenes"]:
        if not isinstance(sc, dict):
            continue
        base = new_scene(0, 1, 1, "", "")
        for fk, fv in base.items():
            if fk not in sc:
                sc[fk] = copy.deepcopy(fv)
        if not isinstance(sc.get("steps"), list):
            sc["steps"] = list(sc.get("steps") or [])
        sc["cues"] = _pad_cell(sc.get("cues"), len(sc["steps"]))
        sc["ens"] = _pad_cell(sc.get("ens"), len(sc["steps"]))
        mx = max(mx, int(sc.get("uid", 0)))
        objs = sc.get("objects") or []
        if objs:
            mx = max(mx, max(int(o.get("id", 0)) for o in objs if isinstance(o, dict)))
        scenes_out.append(sc)
    sh["scenes"] = scenes_out
    sh["nextId"] = mx
    return sh


def _pad_cell(cues, n: int) -> list:
    if cues is None:
        cues = []
    cues = list(cues)
    while len(cues) < n:
        cues.append("")
    return cues[:n]


def safe_name(title: str) -> str:
    bad = '<>:"/\\|?*'
    t = "".join("_" if c in bad else c for c in title.strip())
    return t or "Spettacolo"


def roman(n: int) -> str:
    vals = [
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    ]
    out = ""
    x = int(n)
    for v, s in vals:
        while x >= v:
            out += s
            x -= v
    return out or "I"
