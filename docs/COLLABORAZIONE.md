# Collaborare su TEATRO (con Claude / Cursor)

Questa guida è per **modificare il codice**, **correggere bug** e **ottenere nuovi `.exe`** senza passare dal proprietario del PC.

## 1. Accesso alla repository

Il proprietario (`MatteRoma91`) deve aggiungerti su GitHub:

1. Repo **TEATRO** → **Settings** → **Collaborators** → **Add people**
2. Inserisci il tuo username GitHub (es. `aleporrari93`)
3. Ruolo consigliato: **Write** (push su `main`) oppure **Maintain** se gestisci anche le Release
4. Accetta l’invito dall’email o da [github.com/notifications](https://github.com/notifications)

Senza questo passaggio non puoi fare push né usare Claude Code collegato al repo privato/pubblico in scrittura.

### Alternativa: fork + Pull Request

Se preferisci non essere collaborator: fork del repo, lavori sul fork, apri PR verso `MatteRoma91/TEATRO`.  
Dopo il merge su `main`, la **GitHub Action** compila comunque l’exe.

---

## 2. Clonare il progetto sul tuo PC

```bash
git clone https://github.com/MatteRoma91/TEATRO.git
cd TEATRO
```

Configura git (una volta):

```bash
git config user.name "TuoNome"
git config user.email "tua@email"
```

---

## 3. Usare **Claude** per sviluppare

Puoi usare uno di questi strumenti; in tutti i casi fai leggere all’AI **`AGENTS.md`** e questa guida.

### A) **Cursor** (consigliato, come sul VPS)

1. Installa [Cursor](https://cursor.com)
2. **File → Open Folder** → cartella `TEATRO`
3. Le regole in `.cursor/rules/` danno contesto automatico
4. Chiedi all’agente: *«Correggi … leggi AGENTS.md e fai push su main»*  
   (il push richiede che tu abbia configurato GitHub: HTTPS + token o SSH)

### B) **Claude Code** (CLI Anthropic)

1. Installa Claude Code e autenticati
2. Nella cartella del repo: avvia una sessione e incolla:

   > Lavora su TeatroApp Python. Leggi AGENTS.md e docs/COLLABORAZIONE.md. Repo MatteRoma91/TEATRO. Dopo le modifiche, aumenta __version__, committa e pusha su main per triggerare l’exe Windows.

3. Claude può editare file ed eseguire comandi git (se gli dai permesso).

### C) **Claude.ai** (solo chat)

Meno comodo: incolla diff o file, poi applichi tu le modifiche. Meglio Cursor o Claude Code con cartella locale.

### D) **GitHub Copilot / Codex** nell’editor

Stesso flusso: apri repo, riferimento a `AGENTS.md`.

---

## 4. Come nasce l’**exe** automatico

| Evento | Cosa succede |
|--------|----------------|
| **Push su `main`** | Workflow `Build Windows (TeatroApp.exe)` |
| Build OK | Nuova **Release** (`build-N`) con zip `TeatroApp-x.y.z-Windows-x64.zip` |
| Build KO | Actions mostra log; correggi e ripusha |

Avvio manuale: repo → **Actions** → workflow → **Run workflow**.

L’exe **non** viene creato su Linux/macOS in CI (solo `windows-latest`).

---

## 5. Checklist dopo ogni correzione

- [ ] Bug risolto / funzione aggiunta
- [ ] `teatro/__init__.py` → `__version__` incrementata (es. `0.4.2`)
- [ ] Se tocca percorsi file: verificare `bundle_root()` / `_internal` (PyInstaller)
- [ ] Commit con messaggio chiaro
- [ ] Push su `main`
- [ ] Actions verde → ultima [Release](https://github.com/MatteRoma91/TEATRO/releases)
- [ ] Test Windows: estrarre **tutto** lo zip, avviare `TeatroApp.exe`

---

## 6. Permessi utili su GitHub

Per chi gestisce le release:

- **Settings → Actions → General**: workflow allowed, permessi **Read and write** per `GITHUB_TOKEN` (già usato dal workflow per pubblicare le release)

Il collaborator **non** serve segreti personali per la build: il token è quello del repo.

---

## 7. Contatti e riferimenti

- Codice sorgente MATLAB originale: [aleporrari93/TeatroApp](https://github.com/aleporrari93/TeatroApp)
- Issue e bug: tab **Issues** su TEATRO (apri issue prima di fix grossi, se volete coordinarvi)

---

## 8. Invito rapido (per MatteRoma91)

Da terminale con `gh` autenticato:

```bash
gh api -X PUT repos/MatteRoma91/TEATRO/collaborators/USERNAME_GITHUB -f permission=push
```

Sostituisci `USERNAME_GITHUB` con l’account del collaboratore.
