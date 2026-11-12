"""Caricamento/salvataggio spettacolo (.mat MATLAB + .json nativo Python)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import scipy.io as sio

from teatro.models import norm_show


def _to_python(obj: Any) -> Any:
    if isinstance(obj, np.ndarray):
        if obj.dtype == object:
            if obj.ndim == 0:
                return _to_python(obj.item())
            return [_to_python(x) for x in obj.flatten()]
        if obj.size == 1:
            item = obj.item()
            if isinstance(item, (bytes, str)):
                return item.decode() if isinstance(item, bytes) else item
            if isinstance(item, (int, float, bool)):
                return item
        if obj.ndim == 1 and obj.dtype.kind in "SU":
            return [str(x) for x in obj.tolist()]
        return obj.tolist()
    if hasattr(obj, "_fieldnames"):  # matlab struct
        return {fn: _to_python(getattr(obj, fn)) for fn in obj._fieldnames}
    if isinstance(obj, dict):
        return {k: _to_python(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_python(x) for x in obj]
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    return obj


def _struct_list_to_dicts(items: list) -> list[dict]:
    out = []
    for it in items:
        if isinstance(it, dict):
            out.append(it)
        elif hasattr(it, "_fieldnames"):
            out.append(_to_python(it))
    return out


def load_show(show_dir: Path) -> dict:
    json_path = show_dir / "spettacolo.json"
    mat_path = show_dir / "spettacolo.mat"
    if json_path.is_file():
        sh = json.loads(json_path.read_text(encoding="utf-8"))
        return norm_show(sh)
    if not mat_path.is_file():
        raise FileNotFoundError(f"Nessun spettacolo in {show_dir}")
    raw = sio.loadmat(str(mat_path), squeeze_me=True, struct_as_record=False)
    if "SH" not in raw:
        raise ValueError("File spettacolo.mat senza campo SH")
    sh = _to_python(raw["SH"])
    if not isinstance(sh, dict):
        raise ValueError("Formato SH non riconosciuto")
    for key in ("scenes", "lights", "elements", "chars"):
        val = sh.get(key)
        if val is None:
            sh[key] = []
        elif isinstance(val, dict):
            sh[key] = [val]
        elif not isinstance(val, list):
            sh[key] = list(val)
    sh["scenes"] = [_normalize_scene(sc) for sc in sh.get("scenes", [])]
    sh["lights"] = _struct_list_to_dicts(sh.get("lights", []))
    sh["elements"] = _struct_list_to_dicts(sh.get("elements", []))
    sh["chars"] = [_normalize_char(ch) for ch in sh.get("chars", [])]
    return norm_show(sh)


def _normalize_scene(sc: dict) -> dict:
    sc = dict(sc)
    for key in ("steps", "cues", "ens"):
        v = sc.get(key)
        if v is None:
            sc[key] = []
        elif isinstance(v, str):
            sc[key] = [v]
        elif not isinstance(v, list):
            sc[key] = list(v)
    cast = sc.get("cast")
    if cast is None:
        sc["cast"] = []
    elif hasattr(cast, "_fieldnames"):
        sc["cast"] = [_to_python(cast)]
    elif isinstance(cast, dict):
        sc["cast"] = [cast]
    objs = sc.get("objects")
    if objs is None:
        sc["objects"] = []
    elif hasattr(objs, "_fieldnames"):
        sc["objects"] = [_to_python(objs)]
    elif isinstance(objs, dict):
        sc["objects"] = [objs]
    steps_out = []
    for st in sc.get("steps", []):
        if st is None:
            steps_out.append([])
            continue
        if isinstance(st, dict):
            steps_out.append([st])
            continue
        if hasattr(st, "_fieldnames"):
            steps_out.append([_to_python(st)])
            continue
        if isinstance(st, (list, tuple)):
            effs = []
            for e in st:
                if isinstance(e, dict):
                    effs.append(e)
                elif hasattr(e, "_fieldnames"):
                    effs.append(_to_python(e))
            steps_out.append(effs)
            continue
        if isinstance(st, np.ndarray) and st.dtype == object:
            effs = []
            for e in st.flatten():
                if isinstance(e, dict):
                    effs.append(e)
                elif hasattr(e, "_fieldnames"):
                    effs.append(_to_python(e))
            steps_out.append(effs)
        else:
            steps_out.append([])
    sc["steps"] = steps_out
    return sc


def _normalize_char(ch: dict) -> dict:
    ch = dict(ch)
    costumes = ch.get("costumes")
    if costumes is None:
        ch["costumes"] = []
    elif hasattr(costumes, "_fieldnames"):
        ch["costumes"] = [_to_python(costumes)]
    elif isinstance(costumes, dict):
        ch["costumes"] = [costumes]
    elif not isinstance(costumes, list):
        ch["costumes"] = list(costumes)
    for i, co in enumerate(ch["costumes"]):
        if hasattr(co, "_fieldnames"):
            ch["costumes"][i] = _to_python(co)
        if isinstance(ch["costumes"][i], dict) and "items" in ch["costumes"][i]:
            items = ch["costumes"][i]["items"]
            if isinstance(items, np.ndarray):
                ch["costumes"][i]["items"] = list(items.flatten())
            elif isinstance(items, str):
                ch["costumes"][i]["items"] = [items] + [""] * 9
    return ch


def save_show(show_dir: Path, sh: dict) -> None:
    from teatro.models import _now_str

    sh = norm_show(sh)
    sh["modified"] = _now_str()
    show_dir.mkdir(parents=True, exist_ok=True)
    json_path = show_dir / "spettacolo.json"
    json_path.write_text(json.dumps(sh, ensure_ascii=False, indent=2), encoding="utf-8")
    # Mantieni anche .mat per compatibilità parziale (solo campi semplici via scipy — opzionale)
    try:
        sio.savemat(str(show_dir / "spettacolo.mat"), {"SH": _to_mat(sh)}, do_compression=True)
    except Exception:
        pass


def _to_mat(sh: dict) -> Any:
    """Converte dict in struct numpy per savemat (best effort)."""
    return _nested_to_mat(sh)


def _nested_to_mat(obj: Any) -> Any:
    if isinstance(obj, dict):
        if not obj:
            return np.array([])
        # scipy expects structured array for struct lists — use object array of dicts
        return {k: _nested_to_mat(v) for k, v in obj.items()}
    if isinstance(obj, list):
        if not obj:
            return np.array([], dtype=object)
        if all(isinstance(x, dict) for x in obj):
            return np.array([_nested_to_mat(x) for x in obj], dtype=object)
        if all(isinstance(x, (int, float)) for x in obj):
            return np.array(obj, dtype=float)
        return np.array([_nested_to_mat(x) if not isinstance(x, (str, int, float, bool)) else x for x in obj], dtype=object)
    if isinstance(obj, bool):
        return int(obj)
    return obj
