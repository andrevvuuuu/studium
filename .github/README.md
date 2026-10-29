# Studium

**Studium** trasforma le fonti di un corso, caricate in NotebookLM, in note di studio per Obsidian. Le note sono collegate tra loro, ordinate in cartelle e verificate: ogni affermazione deve trovarsi nelle fonti.

Si avvia con una scorciatoia da tastiera in Obsidian. Scegli cosa fare e da quali fonti; poi un agente AI (Antigravity, comando `agy`) scrive la nota nel vault mentre una barra mostra l'avanzamento. Le cartelle interne si chiamano ancora `.antigravity/` per motivi storici.

> Progetto personale, nato per studiare all'università. Funziona su macOS ed è scritto in italiano (interfaccia, istruzioni all'AI, note prodotte).

## Cosa fa

- **Nota singola:** da NotebookLM (anche più notebook insieme), da un video YouTube, da una pagina web o da file locali (PDF, audio di una lezione).
- **MOC (mappa di un corso):** costruita sull'indice del libro, con il diario delle lezioni come aggiunta facoltativa. Gli argomenti vengono verificati su NotebookLM e quelli assenti dalle fonti vengono tolti. I titoli doppi vengono unificati tra MOC diversi e gli accenti corretti. Le note sono poche e sostanziose: i dettagli diventano sezioni (`[[Nota#Sezione]]`).
- **Batch:** crea in automatico tutte le note mancanti di un MOC.
  - Due note alla volta, mai dello stesso modulo.
  - Ogni nota interroga tutti i notebook dei MOC che la collegano.
  - Tiene sveglio il Mac, stima il tempo rimanente e scrive un rapporto.
  - Manda notifiche sul Mac e sul telefono (via [ntfy](https://ntfy.sh)).
- **Modifica di una nota esistente:** miglioramento, oppure fusione di una nuova fonte.
- **Esclusività delle fonti:** in modalità "Solo NotebookLM" un revisore controlla la nota e ogni affermazione sospetta viene sottoposta a NotebookLM. Ciò che le fonti non contengono viene tolto.
- **Ordine nel vault:** le note vanno in `Disciplina/Corso/NN Modulo/`, con l'ordine del plugin Manual Sorting. Le basi comuni a più corsi (es. logica, insiemi) vanno nella cartella della disciplina. Gli spostamenti fatti a mano vengono rispettati.
- **Resistenza ai limiti di NotebookLM:** quando la chat di NotebookLM rifiuta le domande per il limite di utilizzo, la nota viene scritta e verificata sul testo originale dei documenti del notebook. Il testo resta in cache sul Mac e il batch torna alla chat appena possibile.

## Requisiti

- macOS, [Obsidian](https://obsidian.md)
- Plugin di Obsidian: **Templater** (obbligatorio); **Manual Sorting** di kh4f (per l'ordine delle cartelle); Mermaid e Dataview consigliati per visualizzare le note
- Python 3.11 o successivo
- [`nlm`](https://github.com/jacob-bd/gemini-notebook-mcp-cli) (CLI di NotebookLM), con accesso fatto: `nlm login`
- `agy` (CLI di Antigravity), con accesso fatto
- Facoltativi:
  - `ffmpeg` e `yt-dlp` per video e audio;
  - `pip install pymupdf trafilatura youtube-transcript-api requests`;
  - `mlx-whisper` per trascrivere l'audio su Apple Silicon.

## Installazione

1. Copia nel tuo vault le cartelle `.antigravity/` e `Scripts/` di questo repository.
2. In Templater:
   - imposta **Script files folder location** su `Scripts`;
   - copia `.antigravity/Antigravity Trigger.md` nella cartella dei template;
   - aggiungilo agli **Template hotkeys**;
   - assegnagli una scorciatoia nelle impostazioni dei tasti rapidi di Obsidian.
3. Rendi eseguibile lo script: `chmod +x .antigravity/scripts/run_job.sh`.
4. (Facoltativo) Per le notifiche sul telefono:
   - copia `.antigravity/notify.example.json` in `.antigravity/notify.json`;
   - scegli un nome di topic casuale;
   - iscriviti allo stesso topic dall'app ntfy;
   - prova con `python3 .antigravity/tools/notify.py --test`.

`run_job.sh` trova il vault da solo; se serve, si può indicarlo con la variabile `ANTIGRAVITY_VAULT_DIR`. I file temporanei vanno in `/tmp/antigravity_runtime`, fuori dal vault.

## Uso

Premi la scorciatoia e scegli:

| Voce del menu | Cosa fa |
|---|---|
| 📝 Crea Nota Normale | Scrive una nota da una fonte |
| 🗺️ Crea / Aggiorna MOC | Scrivi solo l'argomento (es. `Analisi 1`), poi allega l'indice del libro e, se vuoi, il diario delle lezioni |
| 🛠️ Modifica / Migliora Nota | Migliora una nota o vi fonde una nuova fonte |
| 🤖 Crea Note in Automatico dal MOC | Avvia il batch sul MOC aperto; con un batch attivo, la scorciatoia apre i suoi controlli |

La barra in basso a sinistra mostra:
- la fase (fonti, contesto, scrittura, verifica);
- l'avanzamento reale;
- per il batch, le note in corso e i pulsanti *Rapporto*, *Ferma dopo questa*, *Ferma subito*.

Comandi utili da terminale:

```bash
python3 .antigravity/tools/moc_batch.py --plan --moc "01 MOC's/Analisi 1 MOC.md"   # note che il batch creerebbe
python3 .antigravity/tools/vault_layout.py --sync-all --dry-run                     # spostamenti che farebbe
python3 .antigravity/tools/nlm_local.py --sync <notebook_id>                         # scarica il testo delle fonti
```

## Come è fatto

```
Scorciatoia → Antigravity Trigger.md (Templater)
            → Scripts/antigravity_menu.js      menu, barra di avanzamento, avvio del job
            → .antigravity/scripts/run_job.sh  esecuzione in background
            → .antigravity/tools/orchestrator.py
                 fonti (NotebookLM, YouTube, web, PDF) → istruzioni → agy scrive la nota
                 → verifica di esclusività → collegamenti → posizione nel vault
```

| File | Ruolo |
|---|---|
| `tools/orchestrator.py` | Pipeline: estrazione delle fonti, prompt, controllo dell'agente, verifica |
| `tools/moc_batch.py` | Batch delle note di un MOC: parallelo, ritentativi, attese sui limiti, rapporto |
| `tools/moc_postprocess.py` | Revisione dei MOC: titoli unificati, accenti, argomenti verificati |
| `tools/vault_layout.py` | Cartelle `Disciplina/Corso/Modulo` e ordine Manual Sorting |
| `tools/nlm_local.py` | Testo originale delle fonti NotebookLM in cache, ricerca dei passaggi |
| `tools/notify.py` | Notifiche macOS e ntfy |
| `core-guidelines.md`, `disciplines/`, `snippets/` | Regole di scrittura generali e per disciplina |

## Limiti noti

- Scritto e provato solo su macOS, con un vault in italiano.
- Dipende da strumenti esterni (`nlm`, `agy`) che possono cambiare.
- NotebookLM ha un limite di utilizzo a finestra breve che `nlm usage` non mostra. In quel caso si usa il testo dei documenti, ma la ricerca dei passaggi è per parole chiave ed è meno raffinata della chat. Inoltre i PDF fatti solo di immagini non hanno testo.
- Una nota con verifica richiede circa 10-15 minuti.

## Licenza

[MIT](../LICENSE)
