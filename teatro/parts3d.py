"""Assemblaggio modelli 3D (corpi, costumi, scenografia)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np

from teatro.constants import SLOTS, libreria_dir
from teatro.mesh_io import load_parts_file, triangulate_faces


def blend_c(c: np.ndarray, w: np.ndarray, rgb: np.ndarray) -> np.ndarray:
    w = np.asarray(w).reshape(-1, 1)
    rgb = np.asarray(rgb).reshape(1, 3)
    return c * (1 - w) + rgb * w


@lru_cache(maxsize=8)
def load_body(sex: str) -> dict:
    import scipy.io as sio

    fn = libreria_dir() / "corpi" / f"corpo_{sex}.mat"
    if not fn.is_file():
        return {}
    raw = sio.loadmat(str(fn), squeeze_me=True, struct_as_record=False)
    body: dict = {}
    for key in ("V", "F", "masks", "maskNames", "eyesV", "eyesF", "iris", "pupil", "H0"):
        if key not in raw:
            continue
        val = raw[key]
        body[key] = np.asarray(val, dtype=float) if key in ("V", "F", "masks", "eyesV", "eyesF", "iris", "pupil") else val
    if "maskNames" in body and not isinstance(body["maskNames"], list):
        body["maskNames"] = list(np.atleast_1d(body["maskNames"]))
    body["F"] = triangulate_faces(np.asarray(body["F"]))
    body["eyesF"] = triangulate_faces(np.asarray(body["eyesF"]))
    return body


def lib_parts(sub: str, sex: str, item_id: str) -> list[dict]:
    if not item_id:
        return []
    fn = libreria_dir() / sub / f"{sex}_{item_id}.mat"
    if not fn.is_file():
        fn = libreria_dir() / sub / f"{item_id}.mat"
    return load_parts_file(fn)


def prep_parts(parts: list[dict], rgb: list[float] | None) -> list[dict]:
    out = []
    for p in parts:
        v = np.asarray(p["V"], dtype=float)
        c = np.asarray(p["C"], dtype=float)
        if c.shape[0] != v.shape[0]:
            c = np.tile(c[0], (v.shape[0], 1))
        if rgb and p.get("tint", 0) > 0:
            c = np.clip(c / max(p.get("tint", 1), 0.01), 0, 1.15) * np.array(rgb)
        out.append({**p, "V": v, "C": np.clip(c, 0, 1)})
    return out


class PartsCache:
    def __init__(self) -> None:
        self._p: dict[str, list[dict]] = {}
        self._l: dict[str, list[dict]] = {}

    def clear(self) -> None:
        self._p.clear()
        self._l.clear()


def char_parts(sh: dict, show_dir: Path, char_index: int, code: str, cache: PartsCache) -> list[dict]:
    chars = sh.get("chars", [])
    if char_index < 0 or char_index >= len(chars):
        return []
    ch = chars[char_index]
    key = f"{ch['name']}|{code}|{ch.get('rev', 1)}"
    if key in cache._p:
        return cache._p[key]
    costumes = ch.get("costumes", [])
    j = 0
    for i, co in enumerate(costumes):
        if co.get("code") == code:
            j = i
            break
    if not costumes:
        return []
    co = costumes[j]
    if co.get("mode") == "import":
        fn = show_dir / "modelli" / co.get("file", "")
        parts = prep_parts(load_parts_file(fn), None)
        if parts:
            zmax = max(max(p["V"][:, 2]) for p in parts)
            if zmax > 0:
                sc = float(ch.get("height", 1.78)) / zmax
                for p in parts:
                    p["V"] = p["V"] * sc
        cache._p[key] = parts
        return parts

    sex = ch.get("sex", "M")
    b = load_body(sex)
    if not b:
        return []
    v = np.asarray(b["V"])
    sk = np.asarray(ch.get("skin", [0.93, 0.76, 0.62]))
    masks = np.asarray(b.get("masks", np.zeros((v.shape[0], 0))))
    names = list(b.get("maskNames", []))

    def mk(nm: str) -> np.ndarray:
        if masks.size == 0:
            return np.zeros(v.shape[0])
        try:
            idx = names.index(nm)
            return masks[:, idx]
        except ValueError:
            return np.zeros(v.shape[0])

    cs = np.tile(sk, (v.shape[0], 1))
    cs = blend_c(cs, mk("labbra") * 0.55, sk * np.array([0.86, 0.6, 0.58]))
    mkd = co.get("mk", {})
    if mkd.get("blush"):
        cs = blend_c(cs, mk("fard") * 0.35, mkd.get("blushRGB", [0.85, 0.45, 0.45]))
    if mkd.get("shadow"):
        cs = blend_c(cs, mk("ombretto") * 0.7, mkd.get("shadowRGB", [0.45, 0.35, 0.55]))
    if mkd.get("lashes"):
        cs = blend_c(cs, mk("rimmel") * 0.95, mkd.get("lashesRGB", [0.06, 0.05, 0.05]))
    if mkd.get("lips"):
        cs = blend_c(cs, mk("labbra") * 0.9, mkd.get("lipsRGB", [0.7, 0.15, 0.2]))
    brows = mkd.get("brows", "normali")
    cs = blend_c(cs, mk(f"sopr_{brows}") * 0.9, mkd.get("browsRGB", [0.2, 0.13, 0.08]))
    parts: list[dict] = [{"V": v, "F": b["F"], "C": np.clip(cs, 0, 1), "alpha": 1.0, "name": "Corpo"}]
    if "eyesV" in b and "eyesF" in b:
        ce = np.tile([0.87, 0.84, 0.8], (b["eyesV"].shape[0], 1))
        ce = blend_c(ce, b.get("iris", np.zeros(b["eyesV"].shape[0])), ch.get("eyes", [0.29, 0.2, 0.14]))
        ce = blend_c(ce, b.get("pupil", np.zeros(b["eyesV"].shape[0])), [0.07, 0.055, 0.05])
        parts.append({"V": b["eyesV"], "F": b["eyesF"], "C": ce, "alpha": 1, "name": "Occhi"})

    def append(qparts: list[dict], rgb: list[float]) -> None:
        for p in qparts:
            vv = np.asarray(p["V"], dtype=float)
            cc = np.asarray(p["C"], dtype=float)
            if p.get("mix", np.array([])).size:
                w = np.asarray(p["mix"]).reshape(-1, 1)
                cc = sk * (1 - w) + np.array(rgb) * w
            elif p.get("tint", 0) > 0:
                cc = np.clip(cc / max(p["tint"], 0.01), 0, 1.15) * np.array(rgb)
            parts.append({**p, "V": vv, "C": np.clip(cc, 0, 1)})

    items = co.get("items", [""] * 10)
    irgb = co.get("irgb", [[0.5, 0.5, 0.5]] * 10)
    for q, slot in enumerate(SLOTS):
        iid = items[q] if q < len(items) else ""
        if not iid:
            continue
        sub = "cappelli" if slot == "Cappello" else "capi"
        append(lib_parts(sub, sex, iid), irgb[q] if q < len(irgb) else [0.5, 0.5, 0.5])
    if co.get("hair"):
        append(lib_parts("capelli", sex, co["hair"]), co.get("hairRGB", [0.23, 0.14, 0.09]))
    if co.get("facial"):
        append(lib_parts("barba", sex, co["facial"]), co.get("facialRGB", [0.2, 0.13, 0.08]))
    h0 = float(np.asarray(b.get("H0", 1.78)).reshape(-1)[0]) if "H0" in b else 1.78
    sc = float(ch.get("height", 1.78)) / h0
    for p in parts:
        p["V"] = p["V"] * sc
    cache._p[key] = parts
    return parts


def element_parts(sh: dict, show_dir: Path, element: dict, cache: PartsCache) -> list[dict]:
    e = element
    key = f"{e.get('src')}|{e.get('file')}|{e.get('size')}|{e.get('rgb')}"
    if key in cache._l:
        return cache._l[key]
    if e.get("src") == "lib":
        fn = libreria_dir() / "scenografia" / f"{e.get('file')}.mat"
    else:
        fn = show_dir / "modelli" / e.get("file", "")
    raw = load_parts_file(fn)
    if not raw:
        return []
    rgb = e.get("rgb") if e.get("tint") else None
    p = prep_parts(raw, rgb)
    v = np.vstack([x["V"] for x in p])
    mn = v.min(axis=0)
    mx = v.max(axis=0)
    sz = np.maximum(mx - mn, 1e-3)
    target = np.asarray(e.get("size", [1, 1, 1]), dtype=float)
    k = target / sz
    c = np.array([(mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, mn[2]])
    for part in p:
        part["V"] = (part["V"] - c) * k
    cache._l[key] = p
    return p
