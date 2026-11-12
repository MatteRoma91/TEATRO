"""Oggetti in scena, cast, pruning."""

from __future__ import annotations

import copy

import numpy as np

from teatro.scene_logic import cast_code


def alloc_uid(sh: dict) -> int:
    sh["nextId"] = int(sh.get("nextId", 0)) + 1
    return sh["nextId"]


def new_obj(
    oid: int,
    kind: str,
    ref: str,
    label: str,
    x: float,
    y: float,
    rgb: list,
    zone: str,
    w: float,
    d: float,
    rot: float,
    start: bool,
) -> dict:
    return {
        "id": int(oid),
        "kind": kind,
        "ref": ref,
        "label": label,
        "x": float(x),
        "y": float(y),
        "rgb": list(rgb),
        "zone": zone,
        "w": float(w),
        "d": float(d),
        "rot": float(rot),
        "start": bool(start),
    }


def mk_eff(cls: str, spid: int, pts, dur: float, delay: float) -> dict:
    p = np.asarray(pts, dtype=float) if pts is not None and len(pts) else np.zeros((0, 2))
    if p.ndim == 1 and p.size:
        p = p.reshape(1, -1)
    return {"cls": cls, "spid": int(spid), "pts": p.tolist(), "dur": float(dur), "delay": float(delay)}


def set_cast(sc: dict, name: str, code: str) -> dict:
    sc = copy.deepcopy(sc)
    cast = list(sc.get("cast", []))
    found = False
    for c in cast:
        if c.get("name") == name:
            c["code"] = code
            found = True
            break
    if not found:
        cast.append({"name": name, "code": code})
    sc["cast"] = cast
    return sc


def prune_objs(sc: dict) -> dict:
    sc = copy.deepcopy(sc)
    objs = sc.get("objects", [])
    if not objs:
        return sc
    used = set()
    for step in sc.get("steps", []):
        for e in step if isinstance(step, list) else []:
            if isinstance(e, dict) and "spid" in e:
                used.add(e["spid"])
    keep = []
    for o in objs:
        if o.get("start") or o.get("id") in used:
            keep.append(o)
    sc["objects"] = keep
    return sc


def plan_color(element: dict) -> list:
    if element.get("tint"):
        return list(element.get("rgb", [0.6, 0.5, 0.38]))
    return [0.6, 0.5, 0.38]


