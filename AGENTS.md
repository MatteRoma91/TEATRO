# Guida per agenti AI (Claude, Cursor, ecc.)

Repository: **https://github.com/MatteRoma91/TEATRO**  
App desktop **TeatroApp** (port Python di TeatroApp MATLAB). Target principale: **Windows .exe** via GitHub Actions.

## Obiettivo

Correggere bug, aggiungere funzioni in parità con MATLAB, mantenere release Windows funzionanti.

## Layout

| Percorso | Ruolo |
|----------|--------|
| `main.py` | Avvio Qt |
| `teatro/` | Logica e UI |
| `teatro/ui/` | Finestre e dialoghi |
| `libreria/` | Costumi/scenografia (inclusa nel build) |
| `teatroapp.spec` | PyInstaller (cartella `dist/TeatroApp/`, exe + `_internal/`) |
| `.github/workflows/release-windows.yml` | Build zip su ogni push a `main` |

## Regole build Windows (critiche)

1. **PyInstaller 6**: la libreria è in `_internal/libreria/`, non accanto all’exe. Usare `teatro.constants.bundle_root()` e `libreria_dir()`, non hardcodare percorsi.
2. Dopo fix importanti: aggiornare `teatro/__init__.py` → `__version__`.
3. **NON** committare `dist/`, `.exe`, `.venv`, segreti.
4. L’exe Windows **non** si genera su Linux/macOS: push su `main` e verificare Actions/Releases.
5. `console=False` in spec: errori all’avvio devono usare `QMessageBox` (vedi `main.py`).
6. Riferimento comportamento MATLAB: repo originale `aleporrari93/TeatroApp`, file `TeatroApp.m`.

## Flusso consigliato per una correzione

1. Leggere il bug / confrontare con MATLAB se serve.
2. Modificare codice Python (diff minimo).
3. `python -m py_compile` sui file toccati (se hai Python).
4. Bump versione patch in `teatro/__init__.py`.
5. Commit chiaro; push su `main` (o apri PR se il team usa review).
6. Controllare workflow **Build Windows (TeatroApp.exe)** su GitHub Actions.
7. Scaricare release `TeatroApp-<version>-Windows-x64.zip` e testare su Windows (cartella intera, non solo exe).

## Test locale (senza exe)

```bash
pip install -r requirements.txt
python main.py
```

Su Windows: `pyinstaller teatroapp.spec --noconfirm` per provare il pacchetto prima del push.

## Documenti utente

- `INSTALLA_WINDOWS.txt` — SmartScreen, Defender, cartella `_internal`
- `README.md` — panoramica
- `docs/COLLABORAZIONE.md` — accesso GitHub e setup Claude per il collaboratore
