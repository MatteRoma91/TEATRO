"""Caricamento/salvataggio parti 3D (.mat interno, .obj, .glb)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import scipy.io as sio
import trimesh

from teatro.models import safe_name


def _part_to_dict(p) -> dict[str, Any]:
    if isinstance(p, dict):
        return p
    d: dict[str, Any] = {}
    for fn in ("V", "F", "C", "alpha", "shiny", "name", "tint", "mix"):
        if hasattr(p, fn):
            d[fn] = getattr(p, fn)
    return d


def triangulate_faces(faces: np.ndarray) -> np.ndarray:
    f = np.asarray(faces, dtype=np.int64)
    if f.ndim == 1:
        f = f.reshape(-1, 3)
    if f.shape[1] == 4:
        a = f[:, [0, 1, 2]] - 1
        b = f[:, [0, 2, 3]] - 1
        return np.vstack([a, b])
    return f - 1


def normalize_colors(c: np.ndarray, n: int) -> np.ndarray:
    c = np.asarray(c, dtype=float)
    if c.size == 0:
        return np.tile([0.75, 0.75, 0.75], (n, 1))
    if c.ndim == 1:
        c = np.tile(c.reshape(1, -1), (n, 1))
    if c.shape[0] != n:
        c = np.tile(c[0].reshape(1, -1), (n, 1))
    if c.max() > 1.0:
        c = c / 255.0
    return np.clip(c, 0, 1)


def load_parts_file(path: Path | str) -> list[dict]:
    path = Path(path)
    if not path.is_file():
        return []
    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, list) else []
    m = sio.loadmat(str(path), squeeze_me=True, struct_as_record=False)
    if "parts" not in m:
        return []
    parts = m["parts"]
    out: list[dict] = []
    if isinstance(parts, np.ndarray) and parts.dtype == object:
        items = parts.flatten()
    elif hasattr(parts, "_fieldnames"):
        items = [parts]
    else:
        items = []
    for p in items:
        d = _part_to_dict(p)
        v = np.asarray(d.get("V", []), dtype=float)
        if v.size == 0:
            continue
        f = triangulate_faces(np.asarray(d.get("F", [])))
        c = normalize_colors(np.asarray(d.get("C", [0.75, 0.75, 0.75])), v.shape[0])
        out.append(
            {
                "V": v,
                "F": f,
                "C": c,
                "alpha": float(np.asarray(d.get("alpha", 1)).reshape(-1)[0]),
                "name": str(d.get("name", "") or "parte"),
                "tint": float(np.asarray(d.get("tint", 0)).reshape(-1)[0]),
                "mix": np.asarray(d.get("mix", [])),
            }
        )
    return out


def save_parts_file(path: Path | str, parts: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    mats = []
    for p in parts:
        f = np.asarray(p["F"], dtype=np.int32) + 1
        c = np.asarray(p["C"], dtype=np.float32)
        if c.max() <= 1:
            c = (c * 255).astype(np.uint8)
        mats.append(
            {
                "V": np.asarray(p["V"], dtype=np.float32),
                "F": f,
                "C": c,
                "alpha": np.float32(p.get("alpha", 1)),
                "shiny": np.float32(0.2),
                "name": str(p.get("name", "parte")),
                "tint": np.float32(p.get("tint", 0)),
                "mix": np.zeros((0, 1), dtype=np.float32),
            }
        )
    sio.savemat(str(path), {"parts": np.array(mats, dtype=object)}, do_compression=True)


def import_mesh_file(
    src: Path,
    y_up: bool = True,
    max_faces: int = 80000,
) -> tuple[list[dict], np.ndarray]:
    """Importa .glb/.obj/.stl in parti normalizzate (metri, centrato)."""
    mesh = trimesh.load(str(src), force="mesh")
    meshes: list[trimesh.Trimesh] = []
    if isinstance(mesh, trimesh.Scene):
        for g in mesh.geometry.values():
            if isinstance(g, trimesh.Trimesh):
                meshes.append(g)
    elif isinstance(mesh, trimesh.Trimesh):
        meshes = [mesh]
    if not meshes:
        raise ValueError("Nessuna geometria nel file")
    combined = trimesh.util.concatenate(meshes) if len(meshes) > 1 else meshes[0]
    v = np.asarray(combined.vertices, dtype=float)
    if y_up:
        v = np.column_stack([v[:, 0], -v[:, 2], v[:, 1]])
    ext = v.max(axis=0) - v.min(axis=0)
    big = float(ext.max())
    scale = 1.0
    if big > 300:
        scale = 0.001
    elif big > 30:
        scale = 0.01
    v = v * scale
    mn = v.min(axis=0)
    mx = v.max(axis=0)
    center = np.array([(mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, mn[2]])
    v = v - center
    f = np.asarray(combined.faces, dtype=np.int64)
    if f.shape[0] > max_faces:
        ratio = max_faces / f.shape[0]
        simp = combined.simplify_quadric_decimation(int(combined.faces.shape[0] * ratio))
        v = np.asarray(simp.vertices, dtype=float) * scale - center
        f = np.asarray(simp.faces, dtype=np.int64)
    try:
        vc = np.asarray(combined.visual.vertex_colors[:, :3], dtype=float) / 255.0
        if vc.shape[0] != v.shape[0]:
            vc = np.tile([0.7, 0.65, 0.6], (v.shape[0], 1))
    except Exception:
        vc = np.tile([0.7, 0.65, 0.6], (v.shape[0], 1))
    parts = [
        {
            "V": v,
            "F": f,
            "C": vc,
            "alpha": 1.0,
            "name": src.stem,
            "tint": 0.0,
            "mix": np.array([]),
        }
    ]
    bb = v.max(axis=0) - v.min(axis=0)
    return parts, bb


def import_to_show_models(show_dir: Path, src: Path, y_up: bool = True) -> tuple[str, list[float], str]:
    parts, bb = import_mesh_file(src, y_up=y_up)
    models = show_dir / "modelli"
    models.mkdir(parents=True, exist_ok=True)
    base = safe_name(src.stem)
    fn = f"{base}.mat"
    k = 2
    while (models / fn).exists():
        fn = f"{base}_{k}.mat"
        k += 1
    save_parts_file(models / fn, parts)
    return fn, bb.tolist(), src.stem
