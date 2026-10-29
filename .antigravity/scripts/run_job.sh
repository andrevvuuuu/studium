#!/bin/bash
# ==============================================================================
# .antigravity/scripts/run_job.sh
# 
# Launcher script dell'Automazione Antigravity per Obsidian Vault.
# Invocato automaticamente da antigravity_menu.js in background.
# Esegue orchestrator.py con runtime isolato in /tmp/antigravity_runtime/
# per evitare qualsiasi riscrittura all'interno del vault durante l'esecuzione.
# ==============================================================================

set -e

# Iniezione tassativa del PATH macOS
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/opt/homebrew/sbin:$HOME/Library/Python/3.14/bin:/Library/Frameworks/Python.framework/Versions/3.14/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# Il vault è due cartelle sopra questo script (.antigravity/scripts/), anche se lanciato da un collegamento
VAULT_DIR="${ANTIGRAVITY_VAULT_DIR:-$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../.." && pwd)}"
RUNTIME_DIR="${ANTIGRAVITY_RUNTIME_DIR:-/tmp/antigravity_runtime}"
mkdir -p "$RUNTIME_DIR"

cd "$VAULT_DIR"

JOB_FILE="$RUNTIME_DIR/current-job.json"
STATUS_FILE="$RUNTIME_DIR/job-status.json"
ORCHESTRATOR="$VAULT_DIR/.antigravity/tools/orchestrator.py"
PROMPT_FILE="$RUNTIME_DIR/current-prompt.md"

# Determina TARGET_FILE iniziale dal job file se presente
TARGET_FILE=""
if [ -f "$JOB_FILE" ]; then
    TARGET_FILE=$(python3 -c "import json; j=json.load(open('$JOB_FILE')); print(j.get('target_file_rel') or j.get('target_file_path') or '')" 2>/dev/null || echo "")
fi

MONITOR_PID=""

# Cleanup automatico all'uscita per prevenire processi orfani o zombie
cleanup() {
    if [ -n "$MONITOR_PID" ] && kill -0 "$MONITOR_PID" 2>/dev/null; then
        kill -15 "$MONITOR_PID" 2>/dev/null || true
        sleep 0.2
        kill -9 "$MONITOR_PID" 2>/dev/null || true
    fi
}
trap 'cleanup' EXIT

# Funzione helper per aggiornamento stato atomico della pipeline
update_status() {
    local percent="$1"
    local step="$2"
    local message="$3"
    local detail="${4:-}"
    local status="${5:-running}"
    local error_msg="${6:-}"
    local target="${7:-$TARGET_FILE}"

    if [ -f "$ORCHESTRATOR" ]; then
        python3 "$ORCHESTRATOR" --set-status \
            --percent "$percent" \
            --step "$step" \
            --total-steps 6 \
            --message "$message" \
            --detail "$detail" \
            --status "$status" \
            ${target:+--target-file "$target"} \
            ${error_msg:+--error "$error_msg"} 2>/dev/null || true
    fi
}

# Trap degli errori per aggiornare lo stato in /tmp/antigravity_runtime/job-status.json
handle_error() {
    local exit_code=$?
    echo "❌ Errore durante l'esecuzione del job (exit code: $exit_code)"
    # Preserva il messaggio d'errore descrittivo se già registrato da orchestrator.py
    local current_status=""
    local current_detail=""
    if [ -f "$STATUS_FILE" ]; then
        current_status=$(python3 -c "import json; s=json.load(open('$STATUS_FILE')); print(s.get('status', ''))" 2>/dev/null || echo "")
        current_detail=$(python3 -c "import json; s=json.load(open('$STATUS_FILE')); print(s.get('detail', ''))" 2>/dev/null || echo "")
    fi
    if [ "$current_status" != "error" ] || [ -z "$current_detail" ] || [[ "$current_detail" == *"exit code"* ]]; then
        update_status 0 0 "Errore critico durante l'esecuzione della pipeline" "Processo terminato con exit code $exit_code" "error" "Processo terminato in modo anomalo (codice $exit_code)"
    fi
}
trap 'handle_error' ERR

echo "======================================================================"
echo "   🚀 ANTIGRAVITY AUTOMATION ENGINE — OBSIDIAN PIPELINE               "
echo "======================================================================"

if [ ! -f "$JOB_FILE" ]; then
    echo "❌ Nessun job attivo trovato in: $JOB_FILE"
    echo "Avvia il menu da Obsidian tramite la scorciatoia Templater."
    if [ -f "$ORCHESTRATOR" ]; then
        python3 "$ORCHESTRATOR" --set-status \
            --status "error" \
            --percent 0 \
            --step 0 \
            --message "File job non trovato" \
            --detail "current-job.json mancante in $RUNTIME_DIR" \
            --error "Nessun job attivo configurato" 2>/dev/null || true
    fi
    exit 1
fi

# Esecuzione dell'orchestratore Python con job-file isolato
echo "⚡ Avvio dell'orchestratore e pre-processing delle fonti..."
python3 "$ORCHESTRATOR" --job-file "$JOB_FILE"

# Aggiorna TARGET_FILE con il percorso risolto dall'orchestratore
if [ -f "$JOB_FILE" ]; then
    RESOLVED_TARGET=$(python3 -c "import json; j=json.load(open('$JOB_FILE')); print(j.get('target_file_rel') or j.get('target_file_path') or '')" 2>/dev/null || echo "")
    if [ -n "$RESOLVED_TARGET" ]; then
        TARGET_FILE="$RESOLVED_TARGET"
    fi
fi

# Verifica che il prompt sia stato generato in /tmp/antigravity_runtime/
if [ -f "$PROMPT_FILE" ]; then
    echo "----------------------------------------------------------------------"
    echo "📄 Prompt Operativo Generato con Successo:"
    echo "   $PROMPT_FILE"
    echo "----------------------------------------------------------------------"
    
    # Avvio del monitor live in background per tracciare la scrittura (70% -> 92% -> 95% -> 100%)
    echo "👀 Avvio del monitor live per la generazione della nota..."
    nohup python3 "$ORCHESTRATOR" --monitor --job-file "$JOB_FILE" > "$RUNTIME_DIR/monitor.log" 2>&1 &
    MONITOR_PID=$!

    # Individuazione ed esecuzione dell'agente Antigravity via agy CLI (Opzione A: automatica in background)
    AGY_BIN="$HOME/.local/bin/agy"
    if [ ! -x "$AGY_BIN" ]; then
        AGY_BIN=$(command -v agy || true)
    fi

    if [ -x "$AGY_BIN" ]; then
        echo "🤖 Avvio automatico dell'agente Antigravity ($AGY_BIN)..."
        # Output di agy in un file suo (job-output.log viene riscritto da chi lancia lo script)
        AGY_LOG="$RUNTIME_DIR/agy-output.log"
        touch "$RUNTIME_DIR/agy-start.marker"
        AGY_EXIT=0
        "$AGY_BIN" -p "Leggi attentamente ed esegui la missione operativa descritta nel file $PROMPT_FILE. Genera la nota completa e salvala direttamente nel file target indicato nel prompt." --dangerously-skip-permissions > "$AGY_LOG" 2>&1 || AGY_EXIT=$?
        echo "   agy terminato (codice $AGY_EXIT). Ultime righe:"
        tail -n 5 "$AGY_LOG" | sed 's/^/   | /'
    else
        echo "⚠️  Binario agy non trovato. Il prompt è disponibile in: $PROMPT_FILE"
        update_status 0 0 "Comando agy non trovato" "Impossibile trovare il binario agy su $AGY_BIN" "error" "Binario agy non trovato"
        exit 1
    fi

    # Recupera il target_file effettivo aggiornato dal monitor se presente
    if [ -f "$STATUS_FILE" ]; then
        LIVE_TARGET=$(python3 -c "import json; print(json.load(open('$STATUS_FILE')).get('target_file', ''))" 2>/dev/null || echo "")
        if [ -n "$LIVE_TARGET" ]; then
            TARGET_FILE="$LIVE_TARGET"
        fi
    fi

    # agy deve aver scritto (o modificato) la nota: altrimenti errore esplicito, niente post-processing
    if [ -n "$TARGET_FILE" ] && ! [ "$VAULT_DIR/$TARGET_FILE" -nt "$RUNTIME_DIR/agy-start.marker" ]; then
        if [ -n "$MONITOR_PID" ]; then kill -15 "$MONITOR_PID" 2>/dev/null || true; fi
        if grep -qiE "quota_exhausted|resource_exhausted|quota|exhausted|rate.?limit|\b429\b|credits?" "$AGY_LOG" 2>/dev/null; then
            RESET_AT=$(grep -oE '"quotaResetTimeStamp": *"[^"]+"' "$AGY_LOG" | head -1 | sed -E 's/.*"([^"]+)"$/\1/')
            AGY_ERR="⏳ agy ha finito la quota di Antigravity${RESET_AT:+ (ripristino: $RESET_AT)}"
        else
            AGY_ERR="❌ agy non ha scritto la nota (codice $AGY_EXIT): $(grep -v '^[[:space:]]*$' "$AGY_LOG" 2>/dev/null | tail -n 1 | cut -c1-200)"
        fi
        echo "$AGY_ERR"
        update_status 0 5 "$AGY_ERR" "Output completo di agy: $AGY_LOG" "error" "$AGY_ERR"
        exit 1
    fi

    # Determina messaggio di successo specifico per l'operazione
    SUCCESS_MSG="✅ Nota completata con successo!"
    if [ -f "$JOB_FILE" ]; then
        RESOLVED_OP=$(python3 -c "import json; j=json.load(open('$JOB_FILE')); print(j.get('operation_type') or j.get('operation') or '')" 2>/dev/null || echo "")
        if [ "$RESOLVED_OP" = "edit" ]; then
            SUCCESS_MSG="✅ Nota modificata con successo!"
        elif [ "$RESOLVED_OP" = "moc" ]; then
            SUCCESS_MSG="✅ MOC completato con successo!"
        fi
    fi

    # L'agente ha finito di scrivere: lascia al monitor fino a 20s per sanificare e sincronizzare Anki
    if [ -n "$MONITOR_PID" ]; then
        for i in $(seq 1 40); do
            if ! kill -0 "$MONITOR_PID" 2>/dev/null; then
                break
            fi
            sleep 0.5
        done
        if kill -0 "$MONITOR_PID" 2>/dev/null; then
            kill -15 "$MONITOR_PID" 2>/dev/null || true
            sleep 0.2
            kill -9 "$MONITOR_PID" 2>/dev/null || true
        fi
    fi

    CURRENT_STATUS=$(python3 -c "import json; print(json.load(open('$STATUS_FILE')).get('status', ''))" 2>/dev/null || echo "")
    if [ "$CURRENT_STATUS" != "error" ] && [ "$CURRENT_STATUS" != "cancelled" ]; then
        # Post-processing: metadati NotebookLM del MOC, verifica di esclusività ("Solo NotebookLM"),
        # collocazione nella cartella del corso e ordine di Manual Sorting
        echo "🛡️ Post-processing (metadati MOC / verifica esclusività NotebookLM)..."
        python3 "$ORCHESTRATOR" --post-process --job-file "$JOB_FILE" >> "$RUNTIME_DIR/job-output.log" 2>&1 || true

        GROUNDING_SUMMARY=$(python3 -c "import json; print(json.load(open('$JOB_FILE')).get('grounding_summary', ''))" 2>/dev/null || echo "")
        # Il post-processing può aver spostato la nota nella cartella del suo corso (vault_layout.py)
        MOVED_TARGET=$(python3 -c "import json; print(json.load(open('$JOB_FILE')).get('target_file_rel', ''))" 2>/dev/null || echo "")
        if [ -n "$MOVED_TARGET" ]; then
            TARGET_FILE="$MOVED_TARGET"
        fi
        update_status 100 6 "$SUCCESS_MSG" "${GROUNDING_SUMMARY:-Generazione completata}" "completed" "" "$TARGET_FILE"
    fi
fi

echo "======================================================================"
echo "   🏁 PIPELINE ANTIGRAVITY COMPLETATA CON SUCCESSO                    "
echo "======================================================================"
