# TeatroApp (TEATRO)

**Regia di spettacoli teatrali** — port Python open source del progetto [TeatroApp](https://github.com/aleporrari93/TeatroApp) (originariamente MATLAB).

Funziona **senza MATLAB**: crei teatro, luci, scenografia, personaggi, scene e passi; pianta del palco, canzoni, export zip degli spettacoli.

---

## Scarica e installa (Windows)

Non serve Python. L’eseguibile viene compilato automaticamente su GitHub.

1. Vai alla pagina **[Releases](https://github.com/MatteRoma91/TEATRO/releases)** (scegli l’ultima in alto).
2. Scarica **`TeatroApp-*-Windows-x64.zip`**.
3. Estrai tutto in una cartella, ad esempio `C:\TeatroApp`.
4. Doppio clic su **`TeatroApp.exe`**.

La cartella **`spettacoli\`** (accanto all’exe) è dove vengono salvati i tuoi spettacoli. La **`libreria\`** con costumi e scenografia è già inclusa nello zip.

> **Nota:** ogni push sulla branch `main` genera una nuova release con build Windows. Per l’uso quotidiano prendi sempre **l’ultima release**.

Manuale originale: `TeatroApp_Manuale.pdf` e `LEGGIMI.txt` (riferimento MATLAB; l’app Python segue lo stesso flusso dove già portato).

---

## Sviluppatori (codice sorgente)

```bash
git clone https://github.com/MatteRoma91/TEATRO.git
cd TEATRO
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Build locale Windows: `pyinstaller teatroapp.spec`

---

## Stato funzioni (v0.4)

| Area | Stato |
|------|--------|
| Gestione spettacoli, zip, import `.mat` MATLAB | ✅ |
| Impostazioni: teatro, luci, scenografia, personaggi | ✅ |
| Scene: pianta, **vista 3D platea**, montaggio, passi, audio | ✅ |
| **Imposta scena** (personaggi, elementi, luci iniziali) | ✅ |
| **Elenco passi** + **editor passi** (movimenti, entrate, luci) | ✅ |
| **Registra tempi** (barra spaziatrice) + **tabella tempi passi** + sync | ✅ |
| **PDF** copione e passi scena | ✅ |
| **Import GLB/OBJ** (scenografia, costumi, fondale) | ✅ |

---

## Licenza

Vedi `LICENSE` (progetto originale TeatroApp).
