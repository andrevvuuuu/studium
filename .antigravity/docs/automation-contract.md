# Contratto UI ↔ Pipeline dell'automazione note (Studium)

Fonte unica per `Scripts/antigravity_menu.js`, `Scripts/ag_job_bar.js`, `Scripts/ag_job_control.js`,
`.antigravity/tools/orchestrator.py`, `.antigravity/tools/job_progress.py`, `.antigravity/scripts/run_job.sh`.
Runtime: `/tmp/antigravity_runtime` (`RUNTIME_DIR`). Tipi in notazione TypeScript, anche se il codice è JS/Python.

```ts
type SourceType = "notebooklm" | "youtube" | "web" | "local_files" | "studies";
interface NotebookRef { id: string; title: string }
interface SourcePayload {
  type: SourceType;
  label: string;
  value: string | string[] | NotebookRef[]; // URL | percorsi (assoluti o relativi al vault) | notebook
  notebooks?: string[];                     // solo notebooklm
  notebook_details?: NotebookRef[];         // solo notebooklm
}

// current-job.json: campi NUOVI (i vecchi restano per compatibilità)
interface AutomationJob {
  job_id: string;                 // es. `${Date.now()}-${random}`; scritto dal menu
  sources: SourcePayload[];       // >= 1, CANONICO
  strict_sources: boolean;        // toggle «Solo fonti selezionate», vale per TUTTI i tipi
  // legacy, derivati dal menu:
  source: SourcePayload | { type: "multi"; label: string; value: SourcePayload[] }; // sources[0] se una sola
  allow_base_knowledge: boolean;  // = !strict_sources
  notebooks: string[]; notebook_details: NotebookRef[]; // unione dei notebooklm in sources
}
// Job vecchi senza `sources`: sources = [source]; strict = (source.type=="notebooklm" && !allow_base_knowledge).

type Phase = "prep" | "sources" | "context" | "writing" | "verify" | "final";
interface ProgressEvent { done: number; total: number; unit: string } // "fonti" | "risposte" | "righe" | "parti" | "studi"

// job-status.json
interface AutomationJobState {
  job_id?: string;
  status: "running" | "completed" | "error" | "cancelled" | "idle";
  phase: Phase;
  progress: ProgressEvent | null;   // null = fase non misurabile
  overall_percent: number;          // 0..100, monotono nello stesso job_id
  percent: number;                  // = overall_percent
  message: string; detail: string; target_file: string; error: string | null;
  pid: number | null; updated_at: number;
}
```

## Avanzamento ponderato (stesse costanti in `job_progress.py` e `ag_job_control.js`)

| fase | banda |
|---|---|
| prep | 0–3 |
| sources | 3–15 (fraction = fonti lette / N, poi risposte NotebookLM) |
| context | 15–20 |
| writing | 20–85 (righe scritte / righe attese) |
| verify | 85–97 (solo se nel piano) |
| final | 97–100, oppure 85–100 se `verify` non è nel piano |

`overall = lo + (hi - lo) * fraction`; con `fraction` null si usa `lo`. `completed` = 100.
`verify` è nel piano se `op == "moc"` oppure `op == "normal"` e `strict_sources`.

## Annullamento (AbortController centralizzato)

1. UI: `getJobController().abort(reason)` (`Scripts/ag_job_control.js`). Scrive
   `RUNTIME_DIR/cancel-request.json` `{job_id, at}`, manda SIGTERM al gruppo di processi
   (`-pgid`, letto da `RUNTIME_DIR/job.pgid`) e dopo 3 s SIGKILL se è ancora vivo. In ripiego usa
   `pkill -f orchestrator.py|run_job.sh`. Il `signal` del controller va passato a ogni attesa/poll lato UI.
2. `run_job.sh`: scrive `job.pgid` all'avvio; `trap` su TERM/INT: termina i figli (agy, monitor, nlm),
   rimuove la nota parziale (nota nuova creata dopo `agy-start.marker`) oppure ripristina il backup
   (`backup_file` nel job, modalità edit), cancella `job-context`, scrive lo stato `cancelled`, `exit 130`.
3. `orchestrator.py`: gestore SIGTERM → `JobCancelled`; `update_status` non sovrascrive mai uno stato
   `cancelled` quando esiste `cancel-request.json` dello stesso job; i cicli lunghi controllano
   `is_cancel_requested()`.
4. Avvio di un nuovo job: `resetForNewJob(jobId)` cancella `cancel-request.json` e `job.pgid`.
