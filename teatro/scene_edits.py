"""Modifiche a scene quando si rinomina/elimina personaggi o elementi."""

from __future__ import annotations

import re


def used_in_scenes(sh: dict, kind: str, name: str) -> bool:
    for sc in sh.get("scenes", []):
        for ob in sc.get("objects", []):
            if ob.get("kind") == kind and ob.get("ref") == name:
                return True
    return False


def remove_from_scenes(sh: dict, kind: str, name: str) -> None:
    for sc in sh.get("scenes", []):
        objs = sc.get("objects", [])
        if not objs:
            continue
        rm = [ob.get("kind") == kind and ob.get("ref") == name for ob in objs]
        if not any(rm):
            continue
        ids = [ob["id"] for ob, r in zip(objs, rm) if r and "id" in ob]
        if kind == "char":
            pat = re.compile(r" su " + re.escape(name) + r"$")
            for i, ob in enumerate(objs):
                if ob.get("kind") == "light" and pat.search(ob.get("label", "")):
                    rm[i] = True
            ids = [ob["id"] for ob, r in zip(objs, rm) if r and "id" in ob]
        sc["objects"] = [ob for ob, r in zip(objs, rm) if not r]
        for ki, step in enumerate(sc.get("steps", [])):
            if not step:
                continue
            if isinstance(step, list):
                sc["steps"][ki] = [e for e in step if e.get("spid") not in ids]
        if kind == "char":
            sc["cast"] = [c for c in sc.get("cast", []) if c.get("name") != name]
    return None


def rename_in_scenes(sh: dict, kind: str, old: str, new: str) -> None:
    for sc in sh.get("scenes", []):
        for ob in sc.get("objects", []):
            if ob.get("kind") == kind and ob.get("ref") == old:
                ob["ref"] = new
                ob["label"] = new
            if kind == "char" and ob.get("kind") == "light":
                ob["label"] = re.sub(r" su " + re.escape(old) + r"$", " su " + new, ob.get("label", ""))
        if kind == "char":
            for c in sc.get("cast", []):
                if c.get("name") == old:
                    c["name"] = new


def unique_el_name(elements: list[dict], base: str) -> str:
    names = {e.get("name") for e in elements}
    nm = base or "Elemento"
    k = 2
    while nm in names:
        nm = f"{base} {k}"
        k += 1
    return nm
