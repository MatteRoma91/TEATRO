"""Dialogo import modello 3D."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from teatro.mesh_io import import_to_show_models


def import_model_dialog(parent, show_dir: Path, y_up: bool | None = None) -> tuple[str, list[float], str] | None:
    path, _ = QFileDialog.getOpenFileName(
        parent,
        "Importa modello 3D",
        "",
        "Modelli (*.glb *.obj *.stl *.mat)",
    )
    if not path:
        return None
    src = Path(path)
    if src.suffix.lower() == ".mat":
        import shutil

        models = show_dir / "modelli"
        models.mkdir(parents=True, exist_ok=True)
        dst = models / src.name
        if not dst.exists():
            shutil.copy2(src, dst)
        return src.name, [1, 1, 1], src.stem
    if y_up is None and src.suffix.lower() == ".obj":
        ans = QMessageBox.question(
            parent,
            "Importa",
            "Asse verticale nel file OBJ?\nSì = Y (Blender), No = Z",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        y_up = ans == QMessageBox.StandardButton.Yes
    try:
        return import_to_show_models(show_dir, src, y_up=bool(y_up))
    except Exception as ex:
        QMessageBox.critical(parent, "Import", f"Importazione non riuscita:\n{ex}")
        return None
