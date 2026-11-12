# PyInstaller — build su Windows: pyinstaller teatroapp.spec
# Su Linux produce un binario Linux (per .exe serve build da PC Windows).

import sys
from pathlib import Path

block_cipher = None
root = Path(SPECPATH)

a = Analysis(
    [str(root / "main.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / "libreria"), "libreria"),
        (str(root / "spettacoli"), "spettacoli"),
        (str(root / "TeatroApp_Manuale.pdf"), "."),
        (str(root / "LEGGIMI.txt"), "."),
    ],
    hiddenimports=["scipy.io.matlab", "matplotlib.backends.backend_qtagg"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TeatroApp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TeatroApp",
)
