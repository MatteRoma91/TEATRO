"""Salvataggio scena dopo editor passi / imposta scena."""

from __future__ import annotations

import copy

from teatro.scene_objects import prune_objs


def pad_cell(lst: list, n: int) -> list:
    out = list(lst or [])
    while len(out) < n:
        out.append("")
    return out


def commit_scene(sh: dict, idx: int, sc: dict) -> dict:
    sh = copy.deepcopy(sh)
    sc = prune_objs(copy.deepcopy(sc))
    n = len(sc.get("steps", []))
    sc["cues"] = pad_cell(sc.get("cues", []), n)[:n]
    sc["ens"] = pad_cell(sc.get("ens", []), n)[:n]
    sh["scenes"][idx] = sc
    return sh
