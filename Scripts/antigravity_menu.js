/**
 * .antigravity/scripts/antigravity_menu.js
 * 
 * User Script nativo per Obsidian (richiamabile da Templater via tp.user.antigravity_menu(tp)).
 * Gestisce l'intero flusso di configurazione job per Antigravity:
 * 1. Scelta Tipo Operazione (Nota Normale vs MOC vs Modifica)
 * 2. Scelta Disciplina (20 Macro-Discipline divise per Polo Università e Personale)
 * 3. Inserimento Argomento / Titolo / File Target
 * 4. Selezione Dinamica della Fonte (YouTube, Web, File Locali/Lezione, Multi-NotebookLM)
 * 5. Generazione Istantanea di .antigravity/vault-index.json tramite API native Obsidian
 * 6. Salvataggio di .antigravity/current-job.json, Git Snapshot di backup e Avvio nel Terminale con Live Progress HUD
 * 7. Batch MOC: creazione automatica in sequenza delle note mancanti di un MOC (.antigravity/tools/moc_batch.py),
 *    con i NotebookLM di tutti i MOC che collegano ciascuna nota; con un batch attivo la scorciatoia apre i suoi controlli
 *
 * IDEMPOTENZA E PROTEZIONE:
 * - Singleton Lock globale (window._antigravityMenuRunning) contro re-entrancy o loop da shortcut
 * - Chiamate CLI asincrone non bloccanti (nessun freeze dell'interfaccia Electron)
 * - Gestione rigorosa del tasto ESC: annullamento totale e immediato senza esecuzioni fantasma
 * - Debounce tra modali consecutive per garantire lo smontaggio completo dal DOM
 */

const fs = require("fs");
const path = require("path");
const child_process = require("child_process");

// Helper: Cartella runtime isolata FUORI dal vault per non triggerare il file watcher di Obsidian / Dataview
const RUNTIME_DIR = "/tmp/antigravity_runtime";
function getRuntimeDir() {
    try {
        if (!fs.existsSync(RUNTIME_DIR)) {
            fs.mkdirSync(RUNTIME_DIR, { recursive: true });
        }
    } catch (e) {}
    return RUNTIME_DIR;
}

// Helper: Configurazione del PATH completo di macOS per ereditare i binari del sistema
function getMacOSPathEnv() {
    const customBinPaths = [
        path.join(require("os").homedir(), ".local/bin"),
        "/opt/homebrew/bin",
        "/opt/homebrew/sbin",
        path.join(require("os").homedir(), "Library/Python/3.14/bin"),
        "/Library/Frameworks/Python.framework/Versions/3.14/bin",
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
        "/usr/sbin",
        "/sbin"
    ];

    const currentPath = process.env.PATH || "";
    const existingParts = currentPath.split(":").filter(Boolean);
    const combined = Array.from(new Set([...customBinPaths, ...existingParts]));

    const env = Object.assign({}, process.env);
    env.PATH = combined.join(":");
    return env;
}

// Helper: Parsing dell'output della CLI nlm (JSON o testo riga per riga)
function parseNotebooksCliOutput(output) {
    const notebooks = [];
    if (!output || !output.trim()) {
        return notebooks;
    }

    try {
        const jsonArrayMatch = output.match(/\[\s*\{[\s\S]*\}\s*\]/);
        if (jsonArrayMatch) {
            const parsed = JSON.parse(jsonArrayMatch[0]);
            for (const item of parsed) {
                const id = item.id || item.notebook_id || "";
                const title = item.title || item.name || "Senza titolo";
                const sources = item.source_count !== undefined ? item.source_count : (item.sources_count || 0);
                if (id) {
                    notebooks.push({ id, title, sources });
                }
            }
        }
    } catch (e) {
        console.warn("[Antigravity] Parsing JSON di nlm fallito, eseguo fallback a righe:", e);
    }

    if (notebooks.length === 0) {
        const lines = output.split("\n");
        for (const line of lines) {
            const trimmed = line.trim();
            const matchIdTitle = trimmed.match(/^([0-9a-fA-F-]{8,})\s*[:\-]\s*(.+)$/);
            if (matchIdTitle) {
                notebooks.push({
                    id: matchIdTitle[1].trim(),
                    title: matchIdTitle[2].trim(),
                    sources: 0
                });
            }
        }
    }

    return notebooks;
}

// Helper: Lettura e Salvataggio cache NotebookLM locale
function getLocalNotebooksCache(vaultBasePath) {
    const cachePaths = [
        path.join(getRuntimeDir(), "notebooks-cache.json"),
        path.join(vaultBasePath || path.join(require("os").homedir(), "Obsidian Vault"), ".antigravity", "notebooks-cache.json")
    ];
    for (const cp of cachePaths) {
        try {
            if (fs.existsSync(cp)) {
                const raw = fs.readFileSync(cp, "utf8");
                const parsed = JSON.parse(raw);
                if (Array.isArray(parsed) && parsed.length > 0) {
                    return parsed.map(item => ({
                        id: item.id || item.notebook_id || "",
                        title: item.title || item.name || "Senza titolo",
                        sources: item.sources !== undefined ? item.sources : (item.source_count || 0)
                    })).filter(nb => nb.id);
                }
            }
        } catch (_) {}
    }
    return [];
}

function saveLocalNotebooksCache(notebooks, vaultBasePath) {
    if (!Array.isArray(notebooks) || notebooks.length === 0) return;
    const cachePaths = [
        path.join(getRuntimeDir(), "notebooks-cache.json"),
        path.join(vaultBasePath || path.join(require("os").homedir(), "Obsidian Vault"), ".antigravity", "notebooks-cache.json")
    ];
    for (const cp of cachePaths) {
        try {
            const dir = path.dirname(cp);
            if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
            fs.writeFileSync(cp, JSON.stringify(notebooks, null, 2), "utf8");
        } catch (_) {}
    }
}

// Helper ASINCRONO: Recupero lista NotebookLM tramite CLI nlm con fallback resiliente su cache locale
async function getNotebookLMList(vaultBasePath) {
    const env = getMacOSPathEnv();
    const cachedList = getLocalNotebooksCache(vaultBasePath);

    // RESTITUZIONE IMMEDIATA (0ms di latenza): se la cache locale è popolata, aprila all'istante!
    if (cachedList && cachedList.length > 0) {
        // Tenta un refresh silenzioso in background senza bloccare la UI di Obsidian
        child_process.exec("nlm notebook list --json", { env, timeout: 5000 }, (err, stdout) => {
            if (!err && stdout && stdout.trim()) {
                const parsed = parseNotebooksCliOutput(stdout.toString());
                if (parsed.length > 0) {
                    saveLocalNotebooksCache(parsed, vaultBasePath);
                }
            }
        });
        return cachedList;
    }

    return new Promise((resolve) => {
        child_process.exec("nlm notebook list --json", { env, timeout: 2000 }, (err, stdout) => {
            const out1 = stdout ? stdout.toString() : "";
            if (!err && out1.trim()) {
                const parsed = parseNotebooksCliOutput(out1);
                if (parsed.length > 0) {
                    saveLocalNotebooksCache(parsed, vaultBasePath);
                    resolve(parsed);
                    return;
                }
            }

            // Fallback veloce su 'nlm notebook list' testuale
            child_process.exec("nlm notebook list", { env, timeout: 1200 }, (err2, stdout2) => {
                const out2 = stdout2 ? stdout2.toString() : "";
                const parsed2 = parseNotebooksCliOutput(out2);
                if (parsed2.length > 0) {
                    saveLocalNotebooksCache(parsed2, vaultBasePath);
                    resolve(parsed2);
                    return;
                }

                // Fallback definitivo su cache locale o array vuoto
                resolve(cachedList || []);
            });
        });
    });
}

// Helper ASINCRONO: Selettore file multiplo nativo macOS con AppleScript non bloccante
async function pickLocalFilesWithAppleScript() {
    const appleScript = [
        'set outText to ""',
        'tell application "System Events" to activate',
        'try',
        '    set selectedItems to choose file with prompt "Seleziona i file della lezione (PDF, audio, testo, ecc.):" with multiple selections allowed',
        '    repeat with aFile in selectedItems',
        '        set outText to outText & POSIX path of aFile & linefeed',
        '    end repeat',
        '    return outText',
        'on error',
        '    return ""',
        'end try'
    ].join("\n");

    const env = getMacOSPathEnv();
    return new Promise((resolve) => {
        const child = child_process.spawn("osascript", [], { env });
        let stdout = "";
        child.stdout.on("data", (d) => { stdout += d.toString(); });
        child.on("close", () => {
            const lines = stdout.split("\n").map(l => l.trim()).filter(Boolean);
            resolve(lines);
        });
        child.on("error", (err) => {
            console.warn("[Antigravity] AppleScript file chooser fallito:", err);
            resolve([]);
        });
        child.stdin.write(appleScript);
        child.stdin.end();
    });
}

// Helper ASINCRONO: Selettore file multiplo nativo macOS per Indice / Programma / Diario Lezioni (.pdf, .txt, .md)
async function pickSyllabusFilesWithAppleScript() {
    const promptText = "Seleziona Indice del Libro e/o Diario delle Lezioni (.pdf, .txt, .md):";
    const appleScript = [
        'try',
        '    tell application (path to frontmost application as text)',
        '        activate',
        `        set chosenFiles to choose file with prompt "${promptText}" with multiple selections allowed`,
        '        set pathList to {}',
        '        repeat with aFile in chosenFiles',
        '            set end of pathList to POSIX path of (aFile as alias)',
        '        end repeat',
        '        set AppleScript\'s text item delimiters to "\\n"',
        '        return pathList as text',
        '    end tell',
        'on error number -128',
        '    return "__ANTIGRAVITY_CANCELLED__"',
        'on error errMsg number errNum',
        '    return "__ANTIGRAVITY_ERROR__: " & errMsg',
        'end try'
    ].join("\n");

    const env = getMacOSPathEnv();
    return new Promise((resolve) => {
        console.log("[Antigravity][menu] [file picker] Prima di lanciare osascript...");
        const child = child_process.spawn("osascript", [], { env });
        let stdout = "";
        let stderr = "";
        child.stdout.on("data", (d) => { stdout += d.toString(); });
        child.stderr.on("data", (d) => { stderr += d.toString(); });
        child.on("close", (code) => {
            console.log(`[Antigravity][menu] [file picker] Dopo osascript. Exit code: ${code}, stderr: ${stderr.trim() || "(nessuno)"}`);
            const raw = stdout.trim();
            if (raw === "__ANTIGRAVITY_CANCELLED__") {
                console.log("[Antigravity][menu] [file picker] Selezione annullata dall'utente.");
                resolve(null);
                return;
            }
            if (raw.startsWith("__ANTIGRAVITY_ERROR__")) {
                console.warn("[Antigravity][menu] [file picker] Avviso AppleScript:", raw);
                resolve([]);
                return;
            }
            const lines = raw.split("\n").map(l => l.trim()).filter(Boolean);
            console.log(`[Antigravity][menu] [file picker] File estratti (${lines.length}):`, lines);
            resolve(lines);
        });
        child.on("error", (err) => {
            console.warn("[Antigravity][menu] [file picker] Errore spawn osascript:", err);
            resolve([]);
        });
        child.stdin.write(appleScript);
        child.stdin.end();
    });
}

// Helper: Finestra Multi-Riga (Modal nativa DOM Obsidian) per incollare Indice del Libro e/o Diario delle Lezioni
function openMultiLineModal(app, options) {
    const opts = options || {};
    return new Promise((resolve) => {
        let submitted = false;

        // Container principale per la modale inserito direttamente nel DOM di Obsidian
        const modalContainer = document.createElement("div");
        modalContainer.className = "modal-container mod-dim";
        modalContainer.style.position = "fixed";
        modalContainer.style.top = "0";
        modalContainer.style.left = "0";
        modalContainer.style.width = "100vw";
        modalContainer.style.height = "100vh";
        modalContainer.style.display = "flex";
        modalContainer.style.alignItems = "center";
        modalContainer.style.justifyContent = "center";
        modalContainer.style.zIndex = "9999";

        const modalBg = document.createElement("div");
        modalBg.className = "modal-bg";
        modalBg.style.position = "absolute";
        modalBg.style.top = "0";
        modalBg.style.left = "0";
        modalBg.style.width = "100%";
        modalBg.style.height = "100%";
        modalBg.style.backgroundColor = "var(--background-modifier-cover, rgba(0, 0, 0, 0.65))";
        modalContainer.appendChild(modalBg);

        const modalEl = document.createElement("div");
        modalEl.className = "modal";
        modalEl.style.position = "relative";
        modalEl.style.width = "780px";
        modalEl.style.maxWidth = "92vw";
        modalEl.style.maxHeight = "90vh";
        modalEl.style.display = "flex";
        modalEl.style.flexDirection = "column";
        modalEl.style.backgroundColor = "var(--background-primary)";
        modalEl.style.border = "1px solid var(--background-modifier-border)";
        modalEl.style.borderRadius = "var(--radius-l, 8px)";
        modalEl.style.padding = "24px";
        modalEl.style.boxShadow = "var(--shadow-l, 0 16px 32px rgba(0, 0, 0, 0.35))";
        modalEl.style.zIndex = "1";
        modalContainer.appendChild(modalEl);

        // Pulsante di chiusura X in alto a destra
        const closeBtn = document.createElement("div");
        closeBtn.className = "modal-close-button";
        closeBtn.style.position = "absolute";
        closeBtn.style.top = "16px";
        closeBtn.style.right = "16px";
        closeBtn.style.cursor = "pointer";
        closeBtn.style.opacity = "0.7";
        closeBtn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>`;
        closeBtn.onmouseenter = () => { closeBtn.style.opacity = "1"; };
        closeBtn.onmouseleave = () => { closeBtn.style.opacity = "0.7"; };
        modalEl.appendChild(closeBtn);

        // Titolo della modale
        const titleEl = document.createElement("h2");
        titleEl.className = "modal-title";
        titleEl.textContent = opts.title || "📋 Indice del Libro e/o Diario delle Lezioni";
        titleEl.style.margin = "0 0 10px 0";
        titleEl.style.fontSize = "18px";
        titleEl.style.color = "var(--text-normal)";
        modalEl.appendChild(titleEl);

        // Descrizione
        const descEl = document.createElement("p");
        descEl.className = "setting-item-description";
        descEl.textContent = "Incolla qui sotto l'Indice del Libro, il Diario delle Lezioni del professore o entrambi. Verranno integrati con peso paritario (A ∪ B) per mappare tutte le note atomiche necessarie all'esame.";
        descEl.style.margin = "0 0 14px 0";
        descEl.style.fontSize = "13px";
        descEl.style.lineHeight = "1.4";
        descEl.style.color = "var(--text-muted)";
        modalEl.appendChild(descEl);

        // Contenitore Textarea
        const container = document.createElement("div");
        container.style.width = "100%";
        container.style.marginBottom = "14px";
        modalEl.appendChild(container);

        const textarea = document.createElement("textarea");
        textarea.className = "antigravity-multiline-textarea";
        textarea.rows = 18;
        textarea.style.width = "100%";
        textarea.style.minHeight = "280px";
        textarea.style.maxHeight = "55vh";
        textarea.style.fontFamily = "var(--font-monospace, monospace)";
        textarea.style.fontSize = "13px";
        textarea.style.lineHeight = "1.5";
        textarea.style.padding = "10px 12px";
        textarea.style.borderRadius = "6px";
        textarea.style.border = "1px solid var(--background-modifier-border)";
        textarea.style.backgroundColor = "var(--background-secondary)";
        textarea.style.color = "var(--text-normal)";
        textarea.style.boxSizing = "border-box";
        textarea.style.resize = "vertical";
        textarea.placeholder = opts.placeholder || "Incolla qui l'Indice del Libro, il Diario delle Lezioni del professore o entrambi...";
        textarea.value = opts.initialText || "";
        container.appendChild(textarea);

        // Pulsanti di azione
        const btnContainer = document.createElement("div");
        btnContainer.className = "modal-button-container";
        btnContainer.style.display = "flex";
        btnContainer.style.justifyContent = "flex-end";
        btnContainer.style.gap = "10px";
        btnContainer.style.marginTop = "8px";
        modalEl.appendChild(btnContainer);

        const cancelBtn = document.createElement("button");
        cancelBtn.type = "button";
        cancelBtn.textContent = "Annulla";
        btnContainer.appendChild(cancelBtn);

        const confirmBtn = document.createElement("button");
        confirmBtn.type = "button";
        confirmBtn.className = "mod-cta";
        confirmBtn.textContent = opts.confirmButtonText || "✅ Conferma e Avvia";
        btnContainer.appendChild(confirmBtn);

        // Pulizia eventi e rimozione DOM
        const cleanup = () => {
            document.removeEventListener("keydown", handleKeydown, true);
            if (modalContainer.parentNode) {
                modalContainer.parentNode.removeChild(modalContainer);
            }
        };

        const handleKeydown = (e) => {
            if (e.key === "Escape") {
                e.preventDefault();
                e.stopPropagation();
                cleanup();
                if (!submitted) resolve(null);
            } else if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                e.preventDefault();
                e.stopPropagation();
                confirmBtn.click();
            }
        };

        cancelBtn.onclick = () => {
            cleanup();
            if (!submitted) resolve(null);
        };

        closeBtn.onclick = () => {
            cleanup();
            if (!submitted) resolve(null);
        };

        modalBg.onclick = () => {
            cleanup();
            if (!submitted) resolve(null);
        };

        confirmBtn.onclick = () => {
            const val = textarea.value;
            submitted = true;
            cleanup();
            resolve(val);
        };

        document.addEventListener("keydown", handleKeydown, true);
        document.body.appendChild(modalContainer);
        setTimeout(() => textarea.focus(), 60);
    });
}

// Helper: Generazione Indice Leggero del Vault (.antigravity/vault-index.json)
async function generateVaultIndex(app, vaultBasePath) {
    const allFiles = app.vault.getMarkdownFiles();
    const indexRecords = [];

    for (const file of allFiles) {
        if (file.path.startsWith(".antigravity/") || file.path.startsWith(".trash/") || file.path.startsWith(".obsidian/")) {
            continue;
        }

        const cache = app.metadataCache.getFileCache(file) || {};
        const frontmatter = cache.frontmatter || {};

        const title = file.basename;
        const filePath = file.path;

        let aliases = [];
        if (frontmatter.aliases) {
            aliases = Array.isArray(frontmatter.aliases) ? frontmatter.aliases : [frontmatter.aliases];
        } else if (frontmatter.alias) {
            aliases = Array.isArray(frontmatter.alias) ? frontmatter.alias : [frontmatter.alias];
        }
        aliases = aliases.map(a => String(a).trim()).filter(Boolean);

        const tagSet = new Set();
        if (frontmatter.tags) {
            const raw = Array.isArray(frontmatter.tags) ? frontmatter.tags : [frontmatter.tags];
            raw.forEach(t => {
                if (t) tagSet.add(String(t).replace(/^#/, "").trim());
            });
        }
        if (frontmatter.tag) {
            const raw = Array.isArray(frontmatter.tag) ? frontmatter.tag : [frontmatter.tag];
            raw.forEach(t => {
                if (t) tagSet.add(String(t).replace(/^#/, "").trim());
            });
        }
        if (cache.tags) {
            cache.tags.forEach(t => {
                if (t && t.tag) {
                    tagSet.add(String(t.tag).replace(/^#/, "").trim());
                }
            });
        }
        const tags = Array.from(tagSet);

        let disciplina = frontmatter.Disciplina || frontmatter.disciplina || "";
        if (!disciplina) {
            const pathParts = file.path.split("/");
            if (pathParts.length > 1) {
                disciplina = pathParts[0];
            }
        }

        let type = frontmatter.Type || frontmatter.type || [];
        if (!Array.isArray(type)) {
            type = type ? [String(type)] : [];
        }

        const headings = (cache.headings || []).map(h => ({
            level: h.level,
            heading: h.heading
        }));

        indexRecords.push({
            title,
            path: filePath,
            aliases,
            tags,
            disciplina,
            type,
            headings
        });
    }

    const runtimeDir = getRuntimeDir();
    const indexPath = path.join(runtimeDir, "vault-index.json");
    fs.writeFileSync(indexPath, JSON.stringify(indexRecords, null, 2), "utf8");
    return indexRecords;
}

// Helper: Backup silenzioso Git se presente la cartella .git
function runGitBackupSnapshot(vaultBasePath) {
    const gitDir = path.join(vaultBasePath, ".git");
    if (!fs.existsSync(gitDir)) {
        return false;
    }

    const env = getMacOSPathEnv();
    try {
        child_process.execSync('git add -A && git commit -m "pre-antigravity snapshot" --allow-empty', {
            cwd: vaultBasePath,
            env,
            encoding: "utf8",
            timeout: 5000,
            stdio: ["pipe", "pipe", "pipe"]
        });
        return true;
    } catch (err) {
        console.warn("[Antigravity] Git snapshot non riuscito o nessun cambiamento:", err?.message || err);
        return false;
    }
}

// Helper: Escape caratteri HTML per rendering sicuro nell'interfaccia
function escapeHtml(text) {
    if (!text) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Helper: Pulizia preventiva e reset dell'ambiente per idempotenza totale (Zero Zombie, Runtime Isolato)
function preRunCleanup(vaultBasePath, targetRelPath = "") {
    const env = getMacOSPathEnv();
    const runtimeDir = getRuntimeDir();
    
    try {
        child_process.execSync('pkill -f "orchestrator.py" || true', { env, timeout: 2000, stdio: "ignore" });
        child_process.execSync('pkill -f "run_job.sh" || true', { env, timeout: 2000, stdio: "ignore" });
    } catch (e) {}

    const contextDir = path.join(runtimeDir, "job-context");
    try {
        if (fs.existsSync(contextDir)) {
            fs.rmSync(contextDir, { recursive: true, force: true });
        }
        fs.mkdirSync(contextDir, { recursive: true });
    } catch (e) {}

    const statusFile = path.join(runtimeDir, "job-status.json");
    const initialStatus = {
        status: "running",
        percent: 5,
        step_number: 1,
        total_steps: 6,
        message: "🚀 Inizializzazione pipeline Antigravity...",
        detail: "Preparazione ambiente di esecuzione isolato (/tmp/antigravity_runtime)",
        target_file: targetRelPath,
        error: null,
        pid: null,
        updated_at: Date.now()
    };
    try {
        fs.writeFileSync(statusFile, JSON.stringify(initialStatus, null, 2), "utf8");
    } catch (e) {}
}

// Helper: Annullamento immediato del job da pulsante HUD
async function cancelCurrentJob(app, vaultBasePath) {
    const env = getMacOSPathEnv();
    const runtimeDir = getRuntimeDir();
    try {
        child_process.execSync('pkill -f "orchestrator.py" || true', { env, timeout: 2000, stdio: "ignore" });
        child_process.execSync('pkill -f "run_job.sh" || true', { env, timeout: 2000, stdio: "ignore" });
    } catch (e) {}

    const statusFile = path.join(runtimeDir, "job-status.json");
    try {
        const cancelledData = {
            status: "cancelled",
            percent: 0,
            step_number: 0,
            total_steps: 6,
            message: "Operazione annullata dall'utente",
            detail: "Processi interrotti e runtime pulito",
            target_file: "",
            error: "Job cancellato manualmente tramite pulsante Annulla",
            updated_at: Date.now()
        };
        fs.writeFileSync(statusFile, JSON.stringify(cancelledData, null, 2), "utf8");
    } catch (e) {}

    const ctxDir = path.join(runtimeDir, "job-context");
    try {
        if (fs.existsSync(ctxDir)) {
            fs.rmSync(ctxDir, { recursive: true, force: true });
        }
    } catch (e) {}
}

// =============================================================================
// HUD di avanzamento (stile Cupertino: materiale traslucido, variabili del tema Obsidian)
// L'avanzamento è solo quello misurato: risposte NotebookLM ricevute, righe scritte rispetto
// alla lunghezza tipica delle note, verifiche completate. Quando una fase non è misurabile
// (es. l'agente sta ragionando) il suo segmento pulsa invece di avanzare a tempo.
// =============================================================================

const HUD_PHASES = [
    { key: "prep", label: "Preparazione", weight: 5 },
    { key: "sources", label: "Lettura delle fonti", weight: 90 },
    { key: "context", label: "Collegamenti e istruzioni", weight: 15 },
    { key: "writing", label: "Scrittura", weight: 300 },
    { key: "verify", label: "Verifica esclusività", weight: 380 },
    { key: "final", label: "Rifinitura", weight: 10 },
];
const HUD_PHASE_ORDER = HUD_PHASES.map(p => p.key);
// Nel vault (non in /tmp) perché le durate devono sopravvivere ai riavvii
const HUD_STATS_FILE = () => path.join(window.app.vault.adapter.basePath, ".antigravity", "hud-phase-stats.json");

// Durate reali delle fasi nei job precedenti: pesano i segmenti della barra
function loadPhaseStats() {
    try { return JSON.parse(fs.readFileSync(HUD_STATS_FILE(), "utf8")) || {}; } catch (_) { return {}; }
}

function savePhaseDurations(durations) {
    const stats = loadPhaseStats();
    for (const [key, sec] of Object.entries(durations)) {
        if (!(sec > 0)) continue;
        stats[key] = [...(stats[key] || []), Math.round(sec)].slice(-10);
    }
    try { fs.writeFileSync(HUD_STATS_FILE(), JSON.stringify(stats), "utf8"); } catch (_) {}
}

function phaseWeight(key, stats) {
    const list = (stats[key] || []).slice().sort((a, b) => a - b);
    if (list.length) return Math.max(3, list[Math.floor(list.length / 2)]);
    return (HUD_PHASES.find(p => p.key === key) || { weight: 10 }).weight;
}

function phasePlanFor(cfg) {
    const op = (cfg && (cfg.operation || cfg.operation_type)) || "normal";
    const isNlm = cfg && ((cfg.source && cfg.source.type === "notebooklm") || (Array.isArray(cfg.notebooks) && cfg.notebooks.length > 0));
    // Verifica: note "Solo NotebookLM" e tutti i MOC (titoli, accenti, esclusività degli argomenti)
    const strict = (op === "normal" && isNlm && cfg.allow_base_knowledge !== true) || op === "moc";
    return HUD_PHASES.filter(p => p.key !== "verify" || strict).map(p => p.key);
}

function phaseOfStatus(st) {
    if (st.phase && HUD_PHASE_ORDER.includes(st.phase)) return st.phase;
    return ({ 1: "prep", 2: "sources", 3: "context", 4: "context", 5: "writing", 6: "final" })[Number(st.step_number)] || "prep";
}

function formatClock(sec) {
    sec = Math.max(0, Math.floor(sec));
    const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
    return h ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` : `${m}:${String(s).padStart(2, "0")}`;
}

// Icona "x" (stesso disegno della libreria Lucide usata da Obsidian)
const HUD_CLOSE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>';

// Uscita automatica a fine lavoro; il mouse sopra il pannello la rimanda finché non si sposta
function scheduleHudExit(el, delay, onGone) {
    let timer = null;
    const go = () => {
        el.classList.add("is-leaving");
        setTimeout(onGone, 340);
    };
    const arm = ms => { clearTimeout(timer); timer = setTimeout(go, ms); };
    el.addEventListener("mouseenter", () => clearTimeout(timer));
    el.addEventListener("mouseleave", () => arm(2500));
    arm(delay);
}

function injectHudStyle() {
    if (document.getElementById("antigravity-hud-style")) return;
    const styleEl = document.createElement("style");
    styleEl.id = "antigravity-hud-style";
    styleEl.textContent = `
        .ag-hud {
            --ag-surface: color-mix(in srgb, var(--background-primary) 80%, transparent);
            --ag-track: color-mix(in srgb, var(--text-normal) 9%, transparent);
            --ag-done: var(--color-green, #34c759);
            --ag-active: var(--interactive-accent);
            --ag-danger: var(--color-red, #ff3b30);
            position: fixed;
            /* In basso a sinistra, oltre la ribbon delle icone (impostazioni, vault) */
            left: calc(var(--ribbon-width, 44px) + 12px);
            bottom: 16px;
            z-index: var(--layer-notice, 9999);
            width: 372px;
            max-width: calc(100vw - 32px);
            box-sizing: border-box;
            padding: 14px 16px 12px;
            border-radius: 14px;
            border: 1px solid var(--background-modifier-border);
            background: var(--ag-surface);
            -webkit-backdrop-filter: blur(28px) saturate(1.7);
            backdrop-filter: blur(28px) saturate(1.7);
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.12), 0 12px 32px -8px rgba(0, 0, 0, 0.38);
            color: var(--text-normal);
            font-family: var(--font-interface);
            font-size: 13px;
            line-height: 1.4;
            font-variant-numeric: tabular-nums;
            -webkit-user-select: none;
            user-select: none;
            transition: opacity 0.32s cubic-bezier(0.16, 1, 0.3, 1), transform 0.32s cubic-bezier(0.16, 1, 0.3, 1);
            animation: ag-hud-in 0.42s cubic-bezier(0.16, 1, 0.3, 1);
        }
        @keyframes ag-hud-in { from { opacity: 0; transform: translateY(12px) scale(0.98); } }
        .ag-hud-detail, .ag-hud-title { -webkit-user-select: text; user-select: text; }
        .ag-hud-overall { height: 4px; margin: 10px 0 2px; border-radius: 999px; background: var(--ag-track); overflow: hidden; }
        .ag-hud-overall > i { display: block; height: 100%; width: 0; background: var(--ag-done); border-radius: inherit; transition: width 0.5s ease; }
        .ag-hud-note { margin-top: 10px; padding-top: 8px; border-top: 1px solid var(--background-modifier-border); }
        .ag-hud-note .ag-hud-title { font-size: 13px; }
        .ag-hud-note .ag-hud-bar { margin-top: 8px; }
        .ag-hud-head { display: flex; align-items: flex-start; gap: 10px; }
        .ag-hud-heading { flex: 1; min-width: 0; }
        .ag-hud-title {
            font-size: 14px;
            font-weight: 600;
            letter-spacing: -0.01em;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .ag-hud-sub { margin-top: 2px; color: var(--text-muted); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .ag-hud-clock { color: var(--text-muted); font-size: 12px; padding-top: 2px; }
        .ag-hud-x {
            all: unset;
            width: 22px;
            height: 22px;
            margin: -2px -4px 0 0;
            border-radius: 6px;
            display: grid;
            place-items: center;
            color: var(--text-faint);
            cursor: pointer;
        }
        .ag-hud-x svg { width: 14px; height: 14px; }
        .ag-hud-x:hover { background: var(--background-modifier-hover); color: var(--text-normal); }
        .ag-hud-x:focus-visible, .ag-hud-btn:focus-visible { outline: 2px solid var(--ag-active); outline-offset: 2px; }
        .ag-hud-chips { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
        .ag-hud-chip {
            font-size: 11px;
            padding: 1px 8px;
            border-radius: 999px;
            background: var(--ag-track);
            color: var(--text-muted);
            max-width: 100%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .ag-hud-bar { display: flex; gap: 3px; height: 6px; margin: 12px 0 8px; }
        .ag-hud-seg { position: relative; min-width: 6px; border-radius: 999px; background: var(--ag-track); overflow: hidden; }
        .ag-hud-seg > i { position: absolute; inset: 0 auto 0 0; width: 0; border-radius: inherit; background: var(--ag-active); transition: width 0.5s ease; }
        .ag-hud-seg.is-done > i { width: 100%; background: var(--ag-done); }
        .ag-hud-seg.is-idle > i {
            width: 100%;
            background: linear-gradient(90deg, transparent, color-mix(in srgb, var(--ag-active) 55%, transparent), transparent);
            animation: ag-hud-sweep 1.6s ease-in-out infinite;
        }
        @keyframes ag-hud-sweep { from { transform: translateX(-100%); } to { transform: translateX(100%); } }
        .ag-hud-now { display: flex; justify-content: space-between; gap: 10px; align-items: baseline; }
        .ag-hud-now b { font-weight: 600; font-size: 13px; }
        .ag-hud-pct { color: var(--text-muted); font-size: 12px; }
        .ag-hud-detail { color: var(--text-muted); font-size: 12px; margin-top: 1px; min-height: 17px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .ag-hud-steps { list-style: none; margin: 10px 0 0; padding: 8px 0 0; border-top: 1px solid var(--background-modifier-border); }
        .ag-hud-steps li { display: flex; align-items: center; gap: 8px; padding: 2px 0; font-size: 12px; color: var(--text-faint); }
        .ag-hud-steps li > span:nth-child(2) { flex: 1; }
        .ag-hud-steps li > span:last-child { color: var(--text-faint); }
        .ag-hud-steps .ag-hud-mark { width: 7px; height: 7px; border-radius: 50%; border: 1.5px solid currentColor; box-sizing: border-box; flex: none; }
        .ag-hud-steps li.is-done { color: var(--text-muted); }
        .ag-hud-steps li.is-done .ag-hud-mark { background: var(--ag-done); border-color: var(--ag-done); }
        .ag-hud-steps li.is-active { color: var(--text-normal); font-weight: 500; }
        .ag-hud-steps li.is-active .ag-hud-mark { background: var(--ag-active); border-color: var(--ag-active); }
        .ag-hud-actions { display: flex; gap: 6px; margin-top: 10px; flex-wrap: wrap; }
        .ag-hud-actions .ag-hud-spacer { flex: 1; }
        .ag-hud-btn { font-size: 12px; padding: 3px 10px; height: auto; border-radius: 7px; }
        .ag-hud .ag-hud-btn.is-destructive { background: transparent; box-shadow: none; border: 0; color: var(--ag-danger); font-weight: 500; }
        .ag-hud .ag-hud-btn.is-destructive:hover { background: color-mix(in srgb, var(--ag-danger) 12%, transparent); }
        .ag-hud .ag-hud-btn:disabled { opacity: 0.55; cursor: default; }
        .ag-hud-stats { display: flex; gap: 12px; margin-top: 8px; font-size: 12px; color: var(--text-muted); }
        .ag-hud-stats strong { color: var(--text-normal); font-weight: 600; }
        .ag-hud.is-completed .ag-hud-seg > i { width: 100% !important; background: var(--ag-done); animation: none; transition: none; }
        .ag-hud.is-error .ag-hud-seg.is-active > i, .ag-hud.is-error .ag-hud-seg.is-idle > i { width: 100%; background: var(--ag-danger); animation: none; }
        .ag-hud.is-error .ag-hud-now b { color: var(--ag-danger); }
        .ag-hud.is-cancelled .ag-hud-seg > i { animation: none; opacity: 0.4; }
        .ag-hud.is-leaving { opacity: 0; transform: translateY(12px) scale(0.98); pointer-events: none; }
        @media (prefers-reduced-motion: reduce) {
            .ag-hud, .ag-hud * { animation: none !important; transition: none !important; }
            .ag-hud-seg.is-idle > i { background: color-mix(in srgb, var(--ag-active) 40%, transparent); }
        }
    `;
    document.head.appendChild(styleEl);
}

// Barra segmentata: una porzione per fase, larga quanto la sua durata tipica
function buildPhaseBar(container, plan, stats) {
    container.innerHTML = "";
    const segs = {};
    for (const key of plan) {
        const seg = document.createElement("div");
        seg.className = "ag-hud-seg";
        seg.style.flex = `${phaseWeight(key, stats)} 1 0`;
        seg.appendChild(document.createElement("i"));
        container.appendChild(seg);
        segs[key] = seg;
    }
    return segs;
}

// Aggiorna barra ed elenco fasi; restituisce la percentuale misurata complessiva
function paintPhases(segs, stepsEl, plan, stats, active, fraction, phaseTimes, now) {
    const activeIdx = plan.indexOf(active);
    let doneWeight = 0, totalWeight = 0;
    plan.forEach((key, i) => {
        const w = phaseWeight(key, stats);
        totalWeight += w;
        const seg = segs[key];
        seg.classList.toggle("is-done", i < activeIdx);
        seg.classList.toggle("is-active", i === activeIdx);
        seg.classList.toggle("is-idle", i === activeIdx && fraction === null);
        seg.firstChild.style.width = i === activeIdx && fraction !== null ? `${(fraction * 100).toFixed(1)}%` : "";
        if (i < activeIdx) doneWeight += w;
        if (i === activeIdx && fraction !== null) doneWeight += w * fraction;
    });
    if (stepsEl) {
        stepsEl.querySelectorAll("li").forEach((li, i) => {
            const key = plan[i];
            li.className = i < activeIdx ? "is-done" : (i === activeIdx ? "is-active" : "");
            const t = phaseTimes[key];
            li.lastChild.textContent = t ? formatClock(((t.end || now) - t.start) / 1000) : "";
        });
    }
    return totalWeight ? Math.round((doneWeight / totalWeight) * 100) : 0;
}

function buildStepsList(stepsEl, plan) {
    stepsEl.innerHTML = "";
    for (const key of plan) {
        const li = document.createElement("li");
        const mark = document.createElement("span");
        mark.className = "ag-hud-mark";
        const label = document.createElement("span");
        label.textContent = HUD_PHASES.find(p => p.key === key).label;
        li.append(mark, label, document.createElement("span"));
        stepsEl.appendChild(li);
    }
}

function progressFraction(st) {
    const pr = st && st.progress;
    if (!pr || !(pr.total > 0)) return null;
    return Math.max(0, Math.min(1, pr.done / pr.total));
}

function progressDetail(st) {
    const pr = st.progress;
    if (pr && pr.total > 0 && pr.unit === "righe") {
        const heading = (st.detail || "").match(/\((.*?)\.{0,3}\)$/);
        return `${pr.done} di circa ${pr.total} righe${heading ? `, sezione «${heading[1]}»` : ""}`;
    }
    return st.detail || "";
}

// Helper: Pulizia centralizzata dell'HUD della singola nota e dei relativi timer
function cleanupHudAndStyle() {
    if (typeof window !== "undefined") {
        if (window._antigravityHudTimer) {
            clearInterval(window._antigravityHudTimer);
            window._antigravityHudTimer = null;
        }
        if (window._antigravityStopwatchTimer) {
            clearInterval(window._antigravityStopwatchTimer);
            window._antigravityStopwatchTimer = null;
        }
    }
    const existingHud = document.getElementById("antigravity-progress-hud");
    if (existingHud) existingHud.remove();
}

// Helper: HUD flottante di una singola nota, alimentato da /tmp/antigravity_runtime/job-status.json
function renderProgressHud(app, vaultBasePath, targetFilePath, topicTitle, childPid = null, jobConfig = null) {
    window._agCompletedNotified = false;
    window._agErrorNotified = false;
    window._agFileOpened = false;
    cleanupHudAndStyle();
    injectHudStyle();

    let cfg = jobConfig;
    if (!cfg) {
        try {
            const cjPath = path.join(getRuntimeDir(), "current-job.json");
            if (fs.existsSync(cjPath)) cfg = JSON.parse(fs.readFileSync(cjPath, "utf8"));
        } catch (_) {}
    }
    const opType = (cfg && (cfg.operation || cfg.operation_type)) || "normal";
    const noteTitle = (cfg && (cfg.topic || cfg.title)) || topicTitle || "Nuova nota";
    const opLabel = opType === "moc" ? "MOC" : (opType === "edit" ? "Modifica della nota" : "Nuova nota");

    const chips = [];
    if (cfg) {
        const nbs = (Array.isArray(cfg.notebook_details) && cfg.notebook_details.length ? cfg.notebook_details : cfg.notebooks) || [];
        for (const nb of nbs) {
            const t = typeof nb === "object" ? (nb.title || nb.id) : String(nb);
            if (t && !chips.includes(t)) chips.push(t);
        }
        if (!chips.length && cfg.notebook_title) chips.push(cfg.notebook_title);
        if (!chips.length && cfg.source) {
            const typeLabels = {
                youtube: "Video YouTube", web: "Sito web", local_files: "File locali",
                base_knowledge: "Conoscenza di base", vault_consolidation: "Note del vault", vault_file: "Nota del vault"
            };
            const t = cfg.source.label || typeLabels[cfg.source.type];
            if (t) chips.push(t);
        }
        if (chips.length && cfg.allow_base_knowledge === true && opType !== "moc") chips.push("+ conoscenza di base");
    }

    const hudEl = document.createElement("div");
    hudEl.id = "antigravity-progress-hud";
    hudEl.className = "ag-hud";
    hudEl.setAttribute("role", "status");
    hudEl.innerHTML = `
        <div class="ag-hud-head">
            <div class="ag-hud-heading">
                <div class="ag-hud-title"></div>
                <div class="ag-hud-sub"></div>
            </div>
            <span class="ag-hud-clock">0:00</span>
            <button class="ag-hud-x" aria-label="Chiudi" title="Chiudi">${HUD_CLOSE_ICON}</button>
        </div>
        <div class="ag-hud-chips"></div>
        <div class="ag-hud-bar" aria-hidden="true"></div>
        <div class="ag-hud-now"><b>Preparazione</b><span class="ag-hud-pct">0%</span></div>
        <div class="ag-hud-detail"></div>
        <ul class="ag-hud-steps"></ul>
        <div class="ag-hud-actions">
            <span class="ag-hud-spacer"></span>
            <button class="ag-hud-btn ag-hud-cancel is-destructive">Annulla</button>
        </div>`;
    const q = sel => hudEl.querySelector(sel);
    q(".ag-hud-title").textContent = noteTitle;
    const setSubtitle = rel => {
        // Mostra solo corso e modulo (le ultime due cartelle), non l'intero percorso
        const dirs = rel ? path.dirname(rel).split("/").filter(d => d && d !== ".") : [];
        q(".ag-hud-sub").textContent = dirs.length ? `${opLabel} in ${dirs.slice(-2).join(" › ")}` : opLabel;
    };
    setSubtitle(targetFilePath);
    const chipsEl = q(".ag-hud-chips");
    for (const c of chips) {
        const span = document.createElement("span");
        span.className = "ag-hud-chip";
        span.textContent = c;
        chipsEl.appendChild(span);
    }
    if (!chips.length) chipsEl.remove();

    const plan = phasePlanFor(cfg);
    const stats = loadPhaseStats();
    const segs = buildPhaseBar(q(".ag-hud-bar"), plan, stats);
    const stepsEl = q(".ag-hud-steps");
    buildStepsList(stepsEl, plan);
    document.body.appendChild(hudEl);

    const startTime = window._agJobStartTime || Date.now();
    const phaseTimes = {};
    let currentPhase = null;
    let lastPainted = "";

    const leave = (delay) => scheduleHudExit(hudEl, delay, () => {
        // Rimuove solo questo pannello: nel frattempo potrebbe esserne partito un altro
        if (document.getElementById("antigravity-progress-hud") === hudEl) cleanupHudAndStyle();
    });

    const stopTimers = () => {
        if (window._antigravityHudTimer) clearInterval(window._antigravityHudTimer);
        if (window._antigravityStopwatchTimer) clearInterval(window._antigravityStopwatchTimer);
        window._antigravityHudTimer = null;
        window._antigravityStopwatchTimer = null;
    };

    window._antigravityStopwatchTimer = setInterval(() => {
        q(".ag-hud-clock").textContent = formatClock((Date.now() - startTime) / 1000);
        if (currentPhase) {
            const li = stepsEl.children[plan.indexOf(currentPhase)];
            const t = phaseTimes[currentPhase];
            if (li && t) li.lastChild.textContent = formatClock((Date.now() - t.start) / 1000);
        }
    }, 1000);

    const cancelBtn = q(".ag-hud-cancel");
    cancelBtn.addEventListener("click", async () => {
        cancelBtn.disabled = true;
        cancelBtn.textContent = "Annullamento…";
        await cancelCurrentJob(app, vaultBasePath);
    });
    q(".ag-hud-x").addEventListener("click", () => cleanupHudAndStyle());

    const statusFilePath = path.join(getRuntimeDir(), "job-status.json");
    window._antigravityHudTimer = setInterval(() => {
        let st = null;
        try { st = JSON.parse(fs.readFileSync(statusFilePath, "utf8")); } catch (_) { return; }
        if (!st) return;
        const status = st.status || "running";
        const now = Date.now();

        if (status === "idle") {
            cleanupHudAndStyle();
            return;
        }

        if (status === "error" || status === "cancelled") {
            stopTimers();
            hudEl.classList.add(status === "error" ? "is-error" : "is-cancelled");
            q(".ag-hud-now b").textContent = status === "error" ? (st.message || "Errore durante l'elaborazione").replace(/^❌\s*/, "") : "Annullato";
            q(".ag-hud-pct").textContent = "";
            q(".ag-hud-detail").textContent = status === "error"
                ? `${st.error || st.detail || "Errore sconosciuto"}. Riprova dal menu; dettagli in job-output.log`
                : "Processi interrotti";
            q(".ag-hud-detail").title = q(".ag-hud-detail").textContent;
            cancelBtn.style.display = "none";
            if (status === "error" && !window._agErrorNotified) {
                window._agErrorNotified = true;
                try { if (window.Notice) new window.Notice(`Antigravity: ${st.message || "errore durante l'elaborazione"}`, 6000); } catch (_) {}
            }
            // L'errore resta più a lungo (la notifica di Obsidian lo conserva comunque)
            leave(status === "error" ? 15000 : 2500);
            return;
        }

        const targetFile = st.target_file || targetFilePath || "";
        if (st.target_file && st.target_file !== targetFilePath) {
            targetFilePath = st.target_file;
            setSubtitle(targetFilePath);
        }

        if (status === "completed") {
            stopTimers();
            if (currentPhase && phaseTimes[currentPhase]) phaseTimes[currentPhase].end = now;
            const durations = {};
            for (const [k, t] of Object.entries(phaseTimes)) if (t) durations[k] = ((t.end || now) - t.start) / 1000;
            savePhaseDurations(durations);
            paintPhases(segs, stepsEl, plan, stats, plan[plan.length - 1], 1, phaseTimes, now);
            hudEl.classList.add("is-completed");
            stepsEl.querySelectorAll("li").forEach(li => li.className = "is-done");
            q(".ag-hud-now b").textContent = opType === "moc" ? "MOC pronto" : (opType === "edit" ? "Nota aggiornata" : "Nota pronta");
            q(".ag-hud-pct").textContent = "100%";
            q(".ag-hud-detail").textContent = st.detail && !/^Salvat/.test(st.detail) ? st.detail : (targetFile ? `Salvata in ${targetFile}` : "");
            cancelBtn.style.display = "none";
            window._agJobRunning = false;

            if (!window._agFileOpened && targetFile && app && app.workspace) {
                window._agFileOpened = true;
                try {
                    const tFile = app.vault.getAbstractFileByPath(targetFile);
                    if (tFile) app.workspace.getLeaf(false).openFile(tFile);
                } catch (e) {
                    console.warn("[Antigravity] Errore apertura automatica file:", e);
                }
            }
            if (!window._agCompletedNotified) {
                window._agCompletedNotified = true;
                try { if (window.Notice) new window.Notice(`${noteTitle}: ${q(".ag-hud-now b").textContent.toLowerCase()}`, 4500); } catch (_) {}
            }
            leave(6000);
            return;
        }

        // In corso: fase reale e frazione misurata (null = non misurabile, il segmento pulsa)
        let phase = phaseOfStatus(st);
        if (!plan.includes(phase)) phase = phase === "verify" ? "final" : plan[0];
        if (phase !== currentPhase) {
            if (currentPhase && phaseTimes[currentPhase]) phaseTimes[currentPhase].end = now;
            const prevIdx = plan.indexOf(currentPhase);
            plan.forEach((k, i) => {
                // Fasi saltate (es. job ripreso): restano senza durata
                if (i > prevIdx && i < plan.indexOf(phase) && !phaseTimes[k]) phaseTimes[k] = null;
            });
            phaseTimes[phase] = { start: now, end: null };
            currentPhase = phase;
        }
        const fraction = progressFraction(st);
        const signature = `${phase}|${fraction}|${st.message}|${st.detail}`;
        if (signature === lastPainted) return;
        lastPainted = signature;

        const pct = paintPhases(segs, stepsEl, plan, stats, phase, fraction, phaseTimes, now);
        q(".ag-hud-pct").textContent = `${pct}%`;
        q(".ag-hud-now b").textContent = (st.message || HUD_PHASES.find(p => p.key === phase).label)
            .replace(/^[^\p{L}\p{N}]+/u, "").replace(/\.{3}$|…$/, "");
        q(".ag-hud-detail").textContent = progressDetail(st);
    }, 800);
}

// Helper: Lancio del job in background non-bloccante con child_process.spawn
function launchBackgroundJob(app, vaultBasePath, jobData) {
    const runtimeDir = getRuntimeDir();

    // 0. GUARDIA ATOMICA: Non avviare un nuovo job se ce n'è già uno attivo
    const statusFile = path.join(runtimeDir, "job-status.json");
    if (fs.existsSync(statusFile)) {
        try {
            const curStatus = JSON.parse(fs.readFileSync(statusFile, "utf8"));
            if (curStatus && curStatus.status === "running") {
                let isProcessAlive = false;
                if (curStatus.pid) {
                    try {
                        process.kill(curStatus.pid, 0);
                        isProcessAlive = true;
                    } catch (_) {
                        isProcessAlive = false;
                    }
                }
                const lastUpdate = curStatus.updated_at || curStatus.job_start_time || 0;
                const JOB_TIMEOUT_MS = 600000; // 10 minuti max timeout job
                const isFresh = (Date.now() - lastUpdate) < JOB_TIMEOUT_MS;

                if (isProcessAlive && isFresh) {
                    console.warn(`[Antigravity] Job già in esecuzione con PID: ${curStatus.pid}. Nuovo avvio ignorato.`);
                    const Notice = window?.Notice || (typeof app !== "undefined" && app?.plugins?.plugins?.["templater-obsidian"]?.app?.Notice);
                    try {
                        if (Notice) new Notice(`⚠️ Antigravity è già in esecuzione (PID: ${curStatus.pid}). Attendi il completamento.`, 3500);
                    } catch (_) {}
                    return false;
                }
            }
        } catch (_) {}
    }

    const runScriptPath = path.join(vaultBasePath, ".antigravity", "scripts", "run_job.sh");
    if (fs.existsSync(runScriptPath)) {
        try {
            fs.chmodSync(runScriptPath, 0o755);
        } catch (e) {}
    }

    const logFilePath = path.join(runtimeDir, "job-output.log");
    let logFd;
    try {
        logFd = fs.openSync(logFilePath, "w");
    } catch (e) {
        logFd = "ignore";
    }

    // Salva il timestamp di avvio e resetta i flag operativi (senza resettare _agFileOpened se un job è già in corso)
    window._agJobStartTime = Date.now();
    if (!window._agJobRunning || typeof window._agFileOpened === "undefined") {
        window._agFileOpened = false;
    }
    window._agJobRunning = true;
    window._agCompletedNotified = false;
    window._agErrorNotified = false;

    // Reset preventivo dello stato a 5% per reattività istantanea
    const initStatus = {
        status: "running",
        percent: 5,
        step_number: 1,
        total_steps: 6,
        message: "🧹 Preparazione ambiente e backup di sicurezza...",
        detail: "Inizializzazione processo di background...",
        target_file: jobData.target_file_path || "",
        error: null,
        pid: null,
        job_start_time: window._agJobStartTime,
        updated_at: Date.now()
    };
    try {
        fs.writeFileSync(statusFile, JSON.stringify(initStatus, null, 2), "utf8");
    } catch (e) {}

    let childPid = null;
    try {
        console.log(`[Antigravity][menu] [launchBackgroundJob] Esecuzione di ${runScriptPath} con bash...`);
        const child = child_process.spawn("bash", [runScriptPath], {
            cwd: vaultBasePath,
            detached: true,
            stdio: ["ignore", logFd, logFd],
            env: getMacOSPathEnv()
        });
        childPid = child.pid;
        child.unref();
        console.log(`[Antigravity][menu] [launchBackgroundJob] Job avviato in background con PID: ${childPid}`);
    } catch (err) {
        console.error("[Antigravity][menu] [launchBackgroundJob] Errore avvio processo background:", err);
        const errStatus = {
            status: "error",
            percent: 0,
            step_number: 0,
            total_steps: 6,
            message: "Impossibile avviare il processo di background",
            detail: String(err?.message || err),
            target_file: jobData.target_file_path || "",
            error: String(err?.message || err),
            updated_at: Date.now()
        };
        try {
            fs.writeFileSync(statusFile, JSON.stringify(errStatus, null, 2), "utf8");
        } catch (e) {}
    }

    if (childPid) {
        try {
            initStatus.pid = childPid;
            initStatus.detail = `Processo attivo in background (PID: ${childPid})`;
            fs.writeFileSync(statusFile, JSON.stringify(initStatus, null, 2), "utf8");
        } catch (e) {}
    }

    // HUD flottante disaccoppiato (zero Notice invadenti per non intasare la UI)
    renderProgressHud(app, vaultBasePath, jobData.target_file_path, jobData.topic || jobData.title || "Nota Antigravity", childPid, jobData);
}

// Helper: Selettore interattivo unificato per fonti esterne
async function selectSourceInteractive(tp, app, vaultBasePath, promptTitle = "Passo 4/8: Seleziona la Fonte:") {
    const normalSourceOptions = [
        { label: "🧠 NotebookLM", value: "notebooklm" },
        { label: "🎥 Video YouTube", value: "youtube" },
        { label: "🌐 Sito Online", value: "web" },
        { label: "📚 Lezione / File Locali", value: "local_files" }
    ];

    const chosenSourceType = await tp.system.suggester(
        normalSourceOptions.map(o => o.label),
        normalSourceOptions.map(o => o.value),
        false,
        promptTitle
    );

    if (!chosenSourceType) {
        return null;
    }

    if (chosenSourceType === "youtube") {
        const ytUrl = await tp.system.prompt("Incolla l'URL completo del Video YouTube:", "");
        if (!ytUrl || !ytUrl.trim()) {
            return null;
        }
        return {
            type: "youtube",
            label: "Video YouTube",
            value: ytUrl.trim()
        };
    } else if (chosenSourceType === "web") {
        const webUrl = await tp.system.prompt("Incolla l'URL completo del Sito Web:", "");
        if (!webUrl || !webUrl.trim()) {
            return null;
        }
        return {
            type: "web",
            label: "Sito Online",
            value: webUrl.trim()
        };
    } else if (chosenSourceType === "local_files") {
        let pickedFiles = await pickLocalFilesWithAppleScript();

        if (!pickedFiles || pickedFiles.length === 0) {
            const vaultFiles = app.vault.getFiles().filter(f => !f.path.startsWith("."));
            const selectedFile = await tp.system.suggester(
                vaultFiles.map(f => f.path),
                vaultFiles.map(f => path.join(vaultBasePath, f.path)),
                false,
                "Fallback: seleziona un file dal vault"
            );
            if (selectedFile) {
                pickedFiles = [selectedFile];
            }
        }

        if (!pickedFiles || pickedFiles.length === 0) {
            return null;
        }

        return {
            type: "local_files",
            label: `File Locali (${pickedFiles.length} file)`,
            value: pickedFiles
        };
    } else if (chosenSourceType === "notebooklm") {
        // Passo 5: Modalità Conoscenza
        const chosenKnowledge = await promptKnowledgeMode(tp);
        if (chosenKnowledge === null || chosenKnowledge === undefined) {
            return null;
        }
        // Passo 7: Selezione Multipla NotebookLM
        return await selectNotebookLMInteractive(tp, "Passo 7/8: Seleziona i NotebookLM:", vaultBasePath, chosenKnowledge);
    }
    return null;
}

// Helper: Selezione Modalità Conoscenza per NotebookLM
async function promptKnowledgeMode(tp) {
    await new Promise(resolve => setTimeout(resolve, 80));
    const knowledgeOptions = [
        "🔒 1. Solo NotebookLM (Esclusivo — Zero conoscenza esterna)",
        "🧠+🌐 2. NotebookLM (Fonte Primaria) + Conoscenza Interna AI"
    ];
    const knowledgeValues = [false, true];

    const chosenKnowledge = await tp.system.suggester(
        knowledgeOptions,
        knowledgeValues,
        false,
        "Passo 5/8: Modalità Conoscenza per NotebookLM:"
    );

    if (chosenKnowledge === null || chosenKnowledge === undefined) {
        return null;
    }
    return chosenKnowledge;
}

// Helper: Selezione NotebookLM Multipla tramite Tendina Nativa Suggester (Tasto INVIO per selezionare)
async function selectNotebookLMInteractive(tp, promptHeadline = "Seleziona NotebookLM:", vaultBasePath = "", preselectedKnowledge = null) {
    const allNotebooks = await getNotebookLMList(vaultBasePath);
    const validNotebooks = allNotebooks.filter(nb => nb && nb.id);

    // Fallback: se nessun notebook rilevato via CLI o cache, richiedi input testuale manuale
    if (validNotebooks.length === 0) {
        const manualInput = await tp.system.prompt(
            `${promptHeadline}\nNessun notebook rilevato. Inserisci ID o Nome del NotebookLM:`,
            ""
        );
        if (!manualInput || !manualInput.trim()) {
            return null;
        }
        let chosenKnowledge = preselectedKnowledge;
        if (chosenKnowledge === null || chosenKnowledge === undefined) {
            chosenKnowledge = await promptKnowledgeMode(tp);
            if (chosenKnowledge === null || chosenKnowledge === undefined) {
                return null;
            }
        }
        const val = manualInput.trim();
        return {
            type: "notebooklm",
            label: `NotebookLM: ${val}`,
            value: [{ id: val, title: val, sources: 0 }],
            notebooks: [val],
            notebook_details: [{ id: val, title: val, sources: 0 }],
            allow_base_knowledge: chosenKnowledge
        };
    }

    const selectedNotebooks = [];

    while (true) {
        const options = [];
        const values = [];

        // 1. In cima alla tendina: Opzione di conferma attiva se ci sono selezioni
        if (selectedNotebooks.length > 0) {
            options.push(`🚀 CONFERMA E AVVIA (${selectedNotebooks.length} notebook selezionati)`);
            values.push({ action: "confirm" });
        }

        // 2. Elenco notebook: spunta ☑️ se già selezionato, ◻️ altrimenti
        for (const nb of validNotebooks) {
            const isSelected = selectedNotebooks.some(s => s.id === nb.id);
            const checkMark = isSelected ? "☑️ " : "◻️ ";
            const shortId = nb.id.length > 8 ? `${nb.id.slice(0, 8)}...` : nb.id;
            const srcCount = nb.sources ? ` [${nb.sources} fonti]` : "";
            const title = nb.title || "(Senza titolo)";

            options.push(`${checkMark}${title}${srcCount} (${shortId})`);
            values.push({ action: "toggle", notebook: nb });
        }

        // 3. Opzioni di controllo in fondo alla tendina
        options.push("✏️ Inserisci ID o Nome personalizzato...");
        values.push({ action: "manual" });

        options.push("❌ Annulla operazione");
        values.push({ action: "cancel" });

        // Pausa di 100ms tra le aperture del suggester per disaccoppiare gli eventi DOM di Obsidian
        await new Promise(resolve => setTimeout(resolve, 100));

        const countInfo = selectedNotebooks.length > 0 ? ` [${selectedNotebooks.length} selezionati]` : "";
        const choice = await tp.system.suggester(
            options,
            values,
            false,
            `${promptHeadline}${countInfo} - Premi INVIO per selezionare/deselezionare:`
        );

        // Se l'utente preme ESC (choice è null o undefined): annulla ed esci subito
        if (!choice) {
            return null;
        }

        if (choice.action === "cancel") {
            return null;
        }

        if (choice.action === "confirm") {
            break;
        }

        if (choice.action === "manual") {
            await new Promise(resolve => setTimeout(resolve, 80));
            const manualId = await tp.system.prompt("Inserisci ID o Titolo del NotebookLM:", "");
            if (manualId && manualId.trim()) {
                const trimmed = manualId.trim();
                if (!selectedNotebooks.some(s => s.id === trimmed)) {
                    selectedNotebooks.push({
                        id: trimmed,
                        title: trimmed,
                        sources: 0
                    });
                }
            }
            continue;
        }

        if (choice.action === "toggle") {
            const nb = choice.notebook;
            const existingIdx = selectedNotebooks.findIndex(s => s.id === nb.id);
            if (existingIdx >= 0) {
                selectedNotebooks.splice(existingIdx, 1);
            } else {
                selectedNotebooks.push({
                    id: nb.id,
                    title: nb.title || nb.id,
                    sources: nb.sources || 0
                });
            }
            continue;
        }
    }

    if (selectedNotebooks.length === 0) {
        return null;
    }

    let chosenKnowledge = preselectedKnowledge;
    if (chosenKnowledge === null || chosenKnowledge === undefined) {
        chosenKnowledge = await promptKnowledgeMode(tp);
        if (chosenKnowledge === null || chosenKnowledge === undefined) {
            return null;
        }
    }

    const titlesSummary = selectedNotebooks.map(n => n.title).join(" + ");
    return {
        type: "notebooklm",
        label: selectedNotebooks.length === 1
            ? `NotebookLM: ${selectedNotebooks[0].title}`
            : `NotebookLM Multiplo (${selectedNotebooks.length} fonti: ${titlesSummary})`,
        value: selectedNotebooks,
        notebooks: selectedNotebooks.map(n => n.id),
        notebook_details: selectedNotebooks,
        allow_base_knowledge: chosenKnowledge
    };
}

// =============================================================================
// BATCH MOC: creazione automatica in sequenza delle note mancanti di un MOC
// (motore in .antigravity/tools/moc_batch.py, stato in /tmp/antigravity_runtime/batch-status.json)
// =============================================================================

function readBatchStatus() {
    try {
        const p = path.join(getRuntimeDir(), "batch-status.json");
        if (fs.existsSync(p)) return JSON.parse(fs.readFileSync(p, "utf8"));
    } catch (_) {}
    return null;
}

function isBatchActive() {
    const st = readBatchStatus();
    if (!st || !["running", "waiting"].includes(st.status) || !st.pid) return false;
    try {
        process.kill(st.pid, 0);
        return true;
    } catch (_) {
        return false;
    }
}

// Ferma il batch: "after" lascia finire la nota in corso, "now" interrompe anche la nota corrente
function stopBatch(mode) {
    const runtimeDir = getRuntimeDir();
    try { fs.writeFileSync(path.join(runtimeDir, "batch-stop"), mode, "utf8"); } catch (_) {}
    if (mode !== "now") return;

    const st = readBatchStatus();
    if (st && st.pid) {
        try { process.kill(st.pid, "SIGTERM"); } catch (_) {}
    }
    const env = getMacOSPathEnv();
    for (const pattern of ["run_job.sh", "orchestrator.py", "missione operativa", "revisore accademico indipendente", "grounding-fix-prompt"]) {
        try { child_process.execSync(`pkill -f "${pattern}" || true`, { env, timeout: 2000, stdio: "ignore" }); } catch (_) {}
    }
    try {
        if (st) {
            st.status = "stopped";
            st.message = "⏹️ Batch interrotto dall'utente";
            st.current_title = "";
            st.updated_at = Date.now();
            fs.writeFileSync(path.join(runtimeDir, "batch-status.json"), JSON.stringify(st, null, 2), "utf8");
        }
        fs.writeFileSync(path.join(runtimeDir, "job-status.json"), JSON.stringify({
            status: "cancelled", percent: 0, step_number: 0, total_steps: 6,
            message: "Operazione annullata dall'utente", detail: "Batch interrotto",
            target_file: "", error: null, updated_at: Date.now()
        }, null, 2), "utf8");
    } catch (_) {}
}

function cleanupBatchHud() {
    if (window._antigravityBatchHudTimer) {
        clearInterval(window._antigravityBatchHudTimer);
        window._antigravityBatchHudTimer = null;
    }
    const el = document.getElementById("antigravity-batch-hud");
    if (el) el.remove();
}

// Pannello del batch: avanzamento complessivo, stima del tempo e fase reale di ogni nota in corso
function renderBatchHud(app) {
    cleanupBatchHud();
    injectHudStyle();
    let batchCfg = {};
    try { batchCfg = JSON.parse(fs.readFileSync(path.join(getRuntimeDir(), "batch-config.json"), "utf8")) || {}; } catch (_) {}
    const plan = phasePlanFor({ operation: "normal", notebooks: ["batch"], allow_base_knowledge: batchCfg.allow_base_knowledge === true });
    const stats = loadPhaseStats();

    const hud = document.createElement("div");
    hud.id = "antigravity-batch-hud";
    hud.className = "ag-hud";
    hud.setAttribute("role", "status");
    hud.innerHTML = `
        <div class="ag-hud-head">
            <div class="ag-hud-heading">
                <div class="ag-hud-title"></div>
                <div class="ag-hud-sub"></div>
            </div>
            <span class="ag-hud-clock">0:00</span>
            <button class="ag-hud-x" aria-label="Nascondi" title="Nascondi (il batch continua)">${HUD_CLOSE_ICON}</button>
        </div>
        <div class="ag-hud-overall" aria-hidden="true"><i></i></div>
        <div class="ag-hud-stats"></div>
        <div class="ag-hud-notes"></div>
        <div class="ag-hud-actions">
            <button class="ag-hud-btn ag-batch-report">Rapporto</button>
            <button class="ag-hud-btn ag-batch-stop-after">Ferma dopo</button>
            <span class="ag-hud-spacer"></span>
            <button class="ag-hud-btn ag-batch-stop-now is-destructive">Ferma subito</button>
        </div>`;
    document.body.appendChild(hud);
    const q = sel => hud.querySelector(sel);

    const stopAfter = q(".ag-batch-stop-after");
    const stopNow = q(".ag-batch-stop-now");
    stopAfter.addEventListener("click", () => {
        stopBatch("after");
        stopAfter.disabled = true;
        stopAfter.textContent = "In chiusura…";
    });
    stopNow.addEventListener("click", () => {
        stopBatch("now");
        stopNow.disabled = true;
    });
    q(".ag-batch-report").addEventListener("click", () => {
        const st = readBatchStatus();
        const f = st && st.report ? app.vault.getAbstractFileByPath(st.report) : null;
        if (f) app.workspace.getLeaf(true).openFile(f);
    });
    q(".ag-hud-x").addEventListener("click", () => cleanupBatchHud());

    // Una riga per nota in corso, con la sua barra a fasi; si ricostruisce solo quando cambiano le note
    const rows = {};
    const phaseTimes = {};
    const ensureRow = (title) => {
        if (rows[title]) return rows[title];
        const box = document.createElement("div");
        box.className = "ag-hud-note";
        box.innerHTML = `<div class="ag-hud-title"></div><div class="ag-hud-bar" aria-hidden="true"></div>
            <div class="ag-hud-now"><b></b><span class="ag-hud-pct"></span></div><div class="ag-hud-detail"></div>`;
        box.querySelector(".ag-hud-title").textContent = title;
        q(".ag-hud-notes").appendChild(box);
        rows[title] = { box, segs: buildPhaseBar(box.querySelector(".ag-hud-bar"), plan, stats), phase: "" };
        phaseTimes[title] = {};
        return rows[title];
    };

    let finalNotified = false;
    const tick = () => {
        const st = readBatchStatus();
        if (!st || !document.getElementById("antigravity-batch-hud")) return;
        const now = Date.now();
        const done = (st.done || []).length, failed = (st.failed || []).length, skipped = (st.skipped || []).length;
        const finished = done + failed + skipped;
        const total = st.total || 1;
        const active = ["running", "waiting"].includes(st.status);
        const started = st.started_at ? Number(st.started_at) : null;
        const activeNotes = active ? (st.active || []) : [];

        q(".ag-hud-title").textContent = `${st.moc_name || "MOC"}: note in automatico`;
        if (started) q(".ag-hud-clock").textContent = formatClock((now - started) / 1000);
        q(".ag-batch-report").style.display = st.report ? "" : "none";
        q(".ag-hud-stats").innerHTML = "";
        for (const [n, label] of [[done, done === 1 ? "creata" : "create"], [failed, failed === 1 ? "fallita" : "fallite"], [skipped, skipped === 1 ? "saltata" : "saltate"]]) {
            const span = document.createElement("span");
            const strong = document.createElement("strong");
            strong.textContent = String(n);
            span.append(strong, ` ${label}`);
            q(".ag-hud-stats").appendChild(span);
        }

        // Righe delle note in corso, ognuna letta dal job-status del proprio posto
        for (const title of Object.keys(rows)) {
            if (!activeNotes.some(a => a.title === title)) {
                rows[title].box.remove();
                delete rows[title];
                delete phaseTimes[title];
            }
        }
        let activeFraction = 0;
        const durations = (st.done || []).map(r => r.seconds).filter(x => x > 0);
        const avgSec = durations.length ? durations.reduce((a, b) => a + b, 0) / durations.length : 0;
        let runningCredit = 0;
        for (const a of activeNotes) {
            const row = ensureRow(a.title);
            let job = null;
            try { job = JSON.parse(fs.readFileSync(path.join(a.runtime || getRuntimeDir(), "job-status.json"), "utf8")); } catch (_) {}
            if (avgSec && a.started_at) runningCredit += Math.min((now - a.started_at) / 1000, avgSec * 0.95);
            if (!job || job.status !== "running") {
                row.box.querySelector(".ag-hud-now b").textContent = job && job.status === "completed" ? "Completata" : "In avvio";
                row.box.querySelector(".ag-hud-pct").textContent = "";
                continue;
            }
            let phase = phaseOfStatus(job);
            if (!plan.includes(phase)) phase = phase === "verify" ? "final" : plan[0];
            const times = phaseTimes[a.title];
            if (phase !== row.phase) {
                if (row.phase && times[row.phase]) times[row.phase].end = now;
                times[phase] = { start: now, end: null };
                row.phase = phase;
            }
            const pct = paintPhases(row.segs, null, plan, stats, phase, progressFraction(job), times, now);
            activeFraction += pct / 100;
            row.box.querySelector(".ag-hud-now b").textContent = (job.message || HUD_PHASES.find(p => p.key === phase).label)
                .replace(/^[^\p{L}\p{N}]+/u, "").replace(/\.{3}$|…$/, "");
            row.box.querySelector(".ag-hud-pct").textContent = `${pct}%`;
            row.box.querySelector(".ag-hud-detail").textContent = progressDetail(job);
        }

        // Stima: durata media reale delle note già create, divisa per le note in parallelo
        let sub = active ? `${finished} di ${total} elaborate` : (st.message || "Batch terminato").replace(/^[^\p{L}\p{N}]+/u, "");
        if (active && st.status === "waiting") sub = (st.message || "In attesa").replace(/^[^\p{L}\p{N}]+/u, "");
        else if (active && avgSec) {
            const remainingSec = Math.max(0, ((total - finished) * avgSec - runningCredit) / Math.max(1, st.parallel || 1));
            const h = Math.floor(remainingSec / 3600), m = Math.round((remainingSec % 3600) / 60);
            sub += `, circa ${h ? `${h} h ` : ""}${m} min rimanenti`;
        } else if (active) {
            sub += ", stima dopo la prima nota";
        }
        q(".ag-hud-sub").textContent = sub;

        const overall = ((finished + activeFraction) / total) * 100;
        q(".ag-hud-overall > i").style.width = `${Math.max(0, Math.min(100, overall)).toFixed(1)}%`;

        if (!active) {
            stopAfter.style.display = "none";
            stopNow.style.display = "none";
            if (!finalNotified) {
                finalNotified = true;
                hud.classList.add(st.status === "completed" ? "is-completed" : "is-cancelled");
                try { if (window.Notice) new window.Notice(st.message || "Batch terminato", 8000); } catch (_) {}
                clearInterval(window._antigravityBatchHudTimer);
                window._antigravityBatchHudTimer = null;
                // Fine lavoro: il pannello esce da solo (la pausa resta di più, il rapporto ha i dettagli)
                scheduleHudExit(hud, st.status === "paused" ? 20000 : 8000, () => {
                    if (document.getElementById("antigravity-batch-hud") === hud) hud.remove();
                });
            }
        }
    };
    tick();
    window._antigravityBatchHudTimer = setInterval(tick, 1000);
}

// Menu di controllo mostrato quando si preme la scorciatoia con un batch attivo
async function showBatchControls(tp, app) {
    const st = readBatchStatus() || {};
    const choice = await tp.system.suggester(
        ["📊 Mostra l'avanzamento del batch", "⏸️ Ferma il batch dopo le note in corso", "⏹️ Ferma subito il batch"],
        ["show", "after", "now"],
        false,
        `Batch in corso su ${st.moc_name || "un MOC"}: ${(st.done || []).length} di ${st.total || 0} create — in corso: ${st.current_title || ""}`
    );
    if (choice === "show") {
        renderBatchHud(app);
    } else if (choice === "after" || choice === "now") {
        stopBatch(choice);
        renderBatchHud(app);
    }
}

// Flusso del pulsante "Crea Note in Automatico dal MOC"
async function runMocBatchFlow(tp, app, vaultBasePath) {
    const isMoc = f => {
        const fm = app.metadataCache.getFileCache(f)?.frontmatter || {};
        const types = Array.isArray(fm.Type) ? fm.Type : (fm.Type ? [fm.Type] : []);
        return types.some(t => String(t).toLowerCase() === "moc") || /^\d+ MOC/.test(f.path) || f.basename.endsWith(" MOC");
    };
    const mocFiles = app.vault.getMarkdownFiles().filter(f => !f.path.startsWith(".") && isMoc(f));
    if (mocFiles.length === 0) {
        if (window.Notice) new window.Notice("Nessun MOC trovato nel vault.", 4000);
        return;
    }
    const activeFile = app.workspace.getActiveFile();
    mocFiles.sort((a, b) => (activeFile && a.path === activeFile.path ? -1 : activeFile && b.path === activeFile.path ? 1 : a.basename.localeCompare(b.basename)));

    const mocFile = await tp.system.suggester(
        mocFiles.map(f => (activeFile && f.path === activeFile.path ? `⭐ [MOC ATTIVO] ${f.basename}` : `🗺️ ${f.basename}`)),
        mocFiles,
        false,
        "Batch 1/4: Scegli il MOC di cui creare le note mancanti"
    );
    if (!mocFile) return;

    // NotebookLM del MOC: letti dal frontmatter, altrimenti scelti ora e salvati nel MOC
    const fm = app.metadataCache.getFileCache(mocFile)?.frontmatter || {};
    let mocIds = Array.isArray(fm.notebooklm_ids) ? fm.notebooklm_ids : (fm.notebooklm_ids ? [fm.notebooklm_ids] : []);
    if (mocIds.length === 0) {
        const nlm = await selectNotebookLMInteractive(tp, `Batch 2/4: Associa i NotebookLM a "${mocFile.basename}"`, vaultBasePath, false);
        if (!nlm) return;
        await app.fileManager.processFrontMatter(mocFile, front => {
            front.notebooklm_ids = nlm.notebook_details.map(n => n.id);
            front.NotebookLM = nlm.notebook_details.map(n => n.title);
        });
        // Attende che il file sia scritto su disco prima di calcolare il piano
        await new Promise(resolve => setTimeout(resolve, 600));
    }

    const allowBase = await promptKnowledgeMode(tp);
    if (allowBase === null || allowBase === undefined) return;

    const batchScript = path.join(vaultBasePath, ".antigravity", "tools", "moc_batch.py");
    const computePlan = () => new Promise((resolve, reject) => {
        child_process.execFile("python3", [batchScript, "--plan", "--moc", mocFile.path], { env: getMacOSPathEnv(), timeout: 60000, maxBuffer: 20 * 1024 * 1024 }, (err, stdout) => {
            if (err) reject(err); else resolve(JSON.parse(stdout));
        });
    });
    let plan = null;
    try {
        plan = await computePlan();
        // Le note collegate anche ad altri MOC interrogano i NotebookLM di tutti i MOC: se un MOC non li ha
        // (e non si ricavano dalla sua riga "Fonti Ufficiali"), si scelgono ora e si salvano nel MOC
        const skipped = [];
        for (const other of plan.unmapped_mocs || []) {
            const otherFile = app.vault.getAbstractFileByPath(other.path);
            if (!otherFile) continue;
            const nlm = await selectNotebookLMInteractive(tp, `Alcune note sono collegate anche a "${other.name}": scegli i suoi NotebookLM (Esc per ignorarlo)`, vaultBasePath, false);
            if (!nlm || !nlm.notebook_details || !nlm.notebook_details.length) {
                skipped.push(other.name);
                continue;
            }
            await app.fileManager.processFrontMatter(otherFile, front => {
                front.notebooklm_ids = nlm.notebook_details.map(n => n.id);
                front.NotebookLM = nlm.notebook_details.map(n => n.title);
            });
        }
        if ((plan.unmapped_mocs || []).length > skipped.length) {
            await new Promise(resolve => setTimeout(resolve, 600));
            plan = await computePlan();
        }
        for (const name of skipped) {
            if (window.Notice) new window.Notice(`⚠️ ${name} non ha NotebookLM: le note collegate useranno solo gli altri`, 7000);
        }
    } catch (err) {
        if (window.Notice) new window.Notice(`❌ Impossibile calcolare le note del MOC: ${err?.message || err}`, 6000);
        return;
    }
    if (plan.error) {
        if (window.Notice) new window.Notice(`❌ ${plan.error}`, 6000);
        return;
    }

    let discipline = plan.discipline;
    if (!discipline) {
        const d = await tp.system.suggester(
            ["Matematica", "Informatica", "Fisica", "Intelligenza Artificiale", "Neuroscienze", "Biologia", "Bodybuilding", "Nutrizione e Salute", "Chimica", "Droghe", "Tecnologia ed Elettronica", "Musica e Industria Musicale", "Arte e Storia dell'Arte", "Filosofia", "Letteratura", "Analisi Narrativa", "Storia", "Politica e Geopolitica", "Economia e Finanza", "Psicologia"],
            ["Matematica", "Informatica", "Fisica", "Intelligenza Artificiale", "Neuroscienze", "Biologia", "Bodybuilding", "Nutrizione e Salute", "Chimica", "Droghe", "Tecnologia ed Elettronica", "Musica e Industria Musicale", "Arte e Storia dell'Arte", "Filosofia", "Letteratura", "Analisi Narrativa", "Storia", "Politica e Geopolitica", "Economia e Finanza", "Psicologia"],
            false,
            `Il MOC non ha la proprietà Disciplina: in quale disciplina salvare le note?`
        );
        if (!d) return;
        discipline = d;
    }

    const notes = (plan.notes || []).filter(n => n.notebooks && n.notebooks.length > 0);
    if (notes.length === 0) {
        if (window.Notice) new window.Notice(`✅ "${mocFile.basename}" non ha note mancanti da creare.`, 5000);
        return;
    }
    for (const w of plan.warnings || []) {
        if (window.Notice) new window.Notice(`⚠️ ${w}`, 7000);
    }

    const multiCount = notes.filter(n => n.notebooks.length > 1).length;
    const limitOptions = [{ label: `▶️ Crea tutte le ${notes.length} note mancanti`, value: notes.length }];
    for (const n of [5, 10, 20]) {
        if (notes.length > n) limitOptions.push({ label: `▶️ Crea solo le prime ${n}`, value: n });
    }
    const limit = await tp.system.suggester(
        limitOptions.map(o => o.label),
        limitOptions.map(o => o.value),
        false,
        `Batch 4/4: Prima nota: "${notes[0].title}"` + (multiCount ? ` · ${multiCount} note collegate a più MOC useranno tutti i loro NotebookLM` : "")
    );
    if (!limit) return;

    const cfg = {
        moc: plan.moc,
        moc_name: plan.moc_name,
        discipline,
        allow_base_knowledge: allowBase,
        parallel: 2,
        notes: notes.slice(0, limit)
    };
    const runtimeDir = getRuntimeDir();
    const cfgPath = path.join(runtimeDir, "batch-config.json");
    fs.writeFileSync(cfgPath, JSON.stringify(cfg, null, 2), "utf8");
    try { fs.writeFileSync(path.join(runtimeDir, "batch-status.json"), JSON.stringify({ status: "running", pid: null, moc_name: plan.moc_name, total: cfg.notes.length, index: 0, done: [], failed: [], skipped: [], message: "Avvio del batch...", updated_at: Date.now() }), "utf8"); } catch (_) {}

    let logFd = "ignore";
    try { logFd = fs.openSync(path.join(runtimeDir, "batch-process.log"), "w"); } catch (_) {}
    const child = child_process.spawn("python3", [batchScript, "--run", "--config", cfgPath], {
        cwd: vaultBasePath,
        detached: true,
        stdio: ["ignore", logFd, logFd],
        env: getMacOSPathEnv()
    });
    child.unref();
    renderBatchHud(app);
}

/**
 * Funzione principale esportata per Templater
 */
module.exports = async function (tp) {
    // 0. Pulizia preliminare file di lock legacy
    const runtimeDir = getRuntimeDir();
    try {
        const menuLockFile = path.join(runtimeDir, "menu.lock");
        if (fs.existsSync(menuLockFile)) fs.unlinkSync(menuLockFile);
    } catch (_) {}

    // Uccidi SOLO i nostri timer nominati (MAI brute-force clearInterval: uccide i timer di Obsidian
    // inclusi quelli delle Notice auto-dismiss, rendendole immortali e impilabili sullo schermo!)
    if (typeof window !== "undefined") {
        if (window._antigravityHudTimer) {
            clearInterval(window._antigravityHudTimer);
            window._antigravityHudTimer = null;
        }
        if (window._antigravityStopwatchTimer) {
            clearInterval(window._antigravityStopwatchTimer);
            window._antigravityStopwatchTimer = null;
        }
    }
    // Rimozione dal DOM di TUTTE le notice visibili + HUD precedente
    if (typeof document !== "undefined") {
        try {
            // Rimuovi notice dal container nativo di Obsidian
            document.querySelectorAll('.notice-container .notice').forEach(el => el.remove());
            // Rimuovi anche l'intero container se presente (Obsidian lo ricrea automaticamente)
            const nc = document.querySelector('.notice-container');
            if (nc) nc.innerHTML = '';
            // Rimuovi HUD precedente
            const existingHud = document.getElementById("antigravity-progress-hud");
            if (existingHud) existingHud.remove();
        } catch (e) {}
    }

    const app = tp?.app || window.app;

    // Bonifica iniziale una-tantum: rimozione modali orfani e chiusura tab vuote duplicate
    // (NON tocca MAI le tab con file aperto, eseguita una sola volta all'avvio e mai nei tick)
    if (typeof document !== "undefined") {
        try {
            document.querySelectorAll(".modal-container").forEach(el => el.remove());
        } catch (_) {}
    }
    if (app && app.workspace && typeof app.workspace.iterateAllLeaves === "function") {
        try {
            const leavesToDetach = [];
            app.workspace.iterateAllLeaves(leaf => {
                try {
                    const view = leaf.view;
                    if (!view) return;
                    // Protezione ferrea: non chiudere MAI tab con file aperto
                    if (view.file) return;

                    const vType = view.getViewType ? view.getViewType() : "";
                    if (vType === "empty") {
                        leavesToDetach.push(leaf);
                        return;
                    }
                    if (view.containerEl && typeof view.containerEl.querySelector === "function") {
                        const emptyEl = view.containerEl.querySelector(".system3-sync-status-empty");
                        if (emptyEl && emptyEl.textContent && emptyEl.textContent.includes("No folder selected")) {
                            leavesToDetach.push(leaf);
                            return;
                        }
                    }
                } catch (_) {}
            });
            leavesToDetach.forEach(l => {
                try { l.detach(); } catch (_) {}
            });
        } catch (_) {}
    }

    // 1a. Batch MOC attivo: la scorciatoia apre i controlli del batch invece del menu
    if (isBatchActive()) {
        await showBatchControls(tp, app);
        return "";
    }

    // 1. Controllo Job già Attivo in background (evita sovrapposizioni)
    const statusFileCheck = path.join(getRuntimeDir(), "job-status.json");
    if (fs.existsSync(statusFileCheck)) {
        try {
            const curr = JSON.parse(fs.readFileSync(statusFileCheck, "utf8"));
            if (curr && curr.status === "running") {
                const Notice = window.Notice;
                if (Notice) new Notice(`⚠️ Antigravity è già in esecuzione (${curr.percent}%) per: ${curr.target_file || "una nota"}. Premi Annulla sull'HUD per fermarlo.`, 4000);
                return "";
            }
        } catch (_) {}
    }
    window._antigravityMenuRunning = true;

    try {
        const currentApp = (typeof app !== "undefined" && app) ? app : ((typeof window !== "undefined" && window.app) ? window.app : (tp && tp.app ? tp.app : null));
        const vaultBasePath = (currentApp && currentApp.vault && currentApp.vault.adapter && currentApp.vault.adapter.basePath) 
            ? currentApp.vault.adapter.basePath 
            : path.join(require("os").homedir(), "Obsidian Vault");

        // Assicurati che l'albero delle cartelle esista
        const requiredDirs = [
            path.join(vaultBasePath, ".antigravity"),
            path.join(vaultBasePath, ".antigravity", "scripts"),
            path.join(vaultBasePath, ".antigravity", "tools"),
            path.join(vaultBasePath, ".antigravity", "disciplines"),
            path.join(vaultBasePath, ".antigravity", "backups")
        ];
        for (const dir of requiredDirs) {
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }
        }

        // Elenco delle 20 Macro-Discipline del Vault
        const disciplines = [
            // Polo #università
            { name: "Matematica", pole: "università", label: "🎓 Matematica  [Polo #università]" },
            { name: "Informatica", pole: "università", label: "🎓 Informatica  [Polo #università]" },
            { name: "Fisica", pole: "università", label: "🎓 Fisica  [Polo #università]" },
            { name: "Intelligenza Artificiale", pole: "università", label: "🎓 Intelligenza Artificiale  [Polo #università]" },
            { name: "Neuroscienze", pole: "università", label: "🎓 Neuroscienze  [Polo #università]" },
            { name: "Biologia", pole: "università", label: "🎓 Biologia  [Polo #università]" },

            // Polo #personale
            { name: "Bodybuilding", pole: "personale", label: "🏋️ Bodybuilding  [Polo #personale]" },
            { name: "Nutrizione e Salute", pole: "personale", label: "🥗 Nutrizione e Salute  [Polo #personale]" },
            { name: "Chimica", pole: "personale", label: "🧪 Chimica  [Polo #personale]" },
            { name: "Droghe", pole: "personale", label: "💊 Droghe  [Polo #personale]" },
            { name: "Tecnologia ed Elettronica", pole: "personale", label: "💻 Tecnologia ed Elettronica  [Polo #personale]" },
            { name: "Musica e Industria Musicale", pole: "personale", label: "🎵 Musica e Industria Musicale  [Polo #personale]" },
            { name: "Arte e Storia dell'Arte", pole: "personale", label: "🎨 Arte e Storia dell'Arte  [Polo #personale]" },
            { name: "Filosofia", pole: "personale", label: "🏛️ Filosofia  [Polo #personale]" },
            { name: "Letteratura", pole: "personale", label: "📚 Letteratura  [Polo #personale]" },
            { name: "Analisi Narrativa", pole: "personale", label: "✍️ Analisi Narrativa  [Polo #personale]" },
            { name: "Storia", pole: "personale", label: "📜 Storia  [Polo #personale]" },
            { name: "Politica e Geopolitica", pole: "personale", label: "🌐 Politica e Geopolitica  [Polo #personale]" },
            { name: "Economia e Finanza", pole: "personale", label: "📈 Economia e Finanza  [Polo #personale]" },
            { name: "Psicologia", pole: "personale", label: "🧠 Psicologia  [Polo #personale]" }
        ];

        // -------------------------------------------------------------
        // STEP 1: Menu a Tendina 1 (Tipo di Operazione)
        // -------------------------------------------------------------
        const operationOptions = [
            { label: "📝 Crea Nota Normale (Nuova)", value: "normal" },
            { label: "🗺️ Crea / Aggiorna MOC (Map of Content)", value: "moc" },
            { label: "🛠️ Modifica / Migliora Nota Esistente", value: "edit" },
            { label: "🤖 Crea Note in Automatico dal MOC (Batch)", value: "moc_batch" }
        ];

        const chosenOp = await tp.system.suggester(
            operationOptions.map(o => o.label),
            operationOptions.map(o => o.value),
            false,
            "Passo 1/8: Seleziona il Tipo di Operazione"
        );

        if (!chosenOp) {
            return "";
        }

        if (chosenOp === "moc_batch") {
            await runMocBatchFlow(tp, app, vaultBasePath);
            return "";
        }

        let chosenDiscipline = null;
        let topic = "";
        let sourceResult = null;
        let mocMode = null;
        let notebookInfo = null;
        let selectedFile = null;
        let chosenEditMode = null;
        let userInstructions = "";
        let syllabusText = "";
        let syllabusFiles = [];
        let syllabusIndex = { text: "", files: [] };
        let syllabusDiary = { text: "", files: [] };

        // =============================================================
        // RAMO 1: MODIFICA / MIGLIORA NOTA ESISTENTE (chosenOp === "edit")
        // =============================================================
        if (chosenOp === "edit") {
            const allMdFiles = app.vault.getMarkdownFiles()
                .filter(f => !f.path.startsWith(".antigravity/") && !f.path.startsWith(".trash/") && !f.path.startsWith(".obsidian/"));

            const activeFile = app.workspace.getActiveFile();
            const sortedFiles = [];

            if (activeFile && !activeFile.path.startsWith(".") && activeFile.extension === "md") {
                sortedFiles.push(activeFile);
            }

            for (const f of allMdFiles) {
                if (!activeFile || f.path !== activeFile.path) {
                    sortedFiles.push(f);
                }
            }

            const fileLabels = sortedFiles.map((f, idx) => {
                if (idx === 0 && activeFile && f.path === activeFile.path) {
                    return `⭐ [NOTA ATTIVA] ${f.basename} (${f.path})`;
                }
                return `📄 ${f.basename} (${f.path})`;
            });

            selectedFile = await tp.system.suggester(
                fileLabels,
                sortedFiles,
                false,
                "Seleziona la Nota da Modificare o Migliorare:"
            );

            if (!selectedFile) {
                return "";
            }

            const fileCache = app.metadataCache.getFileCache(selectedFile);
            const existingDiscName = fileCache?.frontmatter?.Disciplina || fileCache?.frontmatter?.disciplina;

            if (existingDiscName && typeof existingDiscName === "string") {
                const cleanDisc = existingDiscName.trim().toLowerCase();
                chosenDiscipline = disciplines.find(d => d.name.toLowerCase() === cleanDisc);
            }

            if (!chosenDiscipline) {
                chosenDiscipline = await tp.system.suggester(
                    disciplines.map(d => d.label),
                    disciplines,
                    false,
                    `Assegna la Disciplina a "${selectedFile.basename}":`
                );
                if (!chosenDiscipline) {
                    return "";
                }
            }

            topic = selectedFile.basename;

            const editModeOptions = [
                {
                    label: "✏️ 1. Correzione o Ampliamento Chirurgico (Prompt Libero)",
                    value: "surgical_prompt"
                },
                {
                    label: "➕ 2. Fondi Nuova Fonte nella Nota (Merge Intelligente)",
                    value: "merge_source"
                },
                {
                    label: "🔬 3. Aggiorna Studi PubMed, Immagini e Wikilink del Vault",
                    value: "refresh_enrichment"
                },
                {
                    label: "✨ 4. Riformatta e Porta allo Standard Completo della Disciplina",
                    value: "reformat_standard"
                }
            ];

            chosenEditMode = await tp.system.suggester(
                editModeOptions.map(o => o.label),
                editModeOptions.map(o => o.value),
                false,
                `Passo 3/4: Tipo di Modifica per "${selectedFile.basename}"`
            );

            if (!chosenEditMode) {
                return "";
            }

            if (chosenEditMode === "surgical_prompt") {
                let promptText = null;
                try {
                    promptText = await tp.system.prompt(
                        "Cosa vuoi correggere, chiarire o ampliare in questa nota?",
                        "",
                        true
                    );
                } catch (_) {
                    return ""; // Uscita silenziosa su annullamento prompt
                }
                if (!promptText || !promptText.trim()) {
                    return "";
                }
                userInstructions = promptText.trim();
                sourceResult = {
                    type: "vault_file",
                    label: selectedFile.basename,
                    value: selectedFile.path
                };
            } else if (chosenEditMode === "merge_source") {
                sourceResult = await selectSourceInteractive(
                    tp,
                    app,
                    vaultBasePath,
                    "Passo 4/4: Seleziona la Nuova Fonte da Fondere nella Nota"
                );
                if (!sourceResult) {
                    return "";
                }
                const mergePrompt = await tp.system.prompt(
                    "Vuoi dare un'indicazione specifica su cosa integrare? (Invio per integrare tutto ciò che è rilevante):",
                    ""
                );
                userInstructions = mergePrompt ? mergePrompt.trim() : "";
            } else if (chosenEditMode === "refresh_enrichment") {
                userInstructions = "Aggiorna studi PubMed, immagini scientifiche e collegamenti verso le note più recenti del vault.";
                sourceResult = {
                    type: "vault_file",
                    label: selectedFile.basename,
                    value: selectedFile.path
                };
            } else if (chosenEditMode === "reformat_standard") {
                const refPrompt = await tp.system.prompt(
                    "Note opzionali per la ristrutturazione (Invio per standard completo della disciplina):",
                    ""
                );
                userInstructions = refPrompt ? refPrompt.trim() : "Riformatta integralmente la nota secondo tutti i canoni del profilo di disciplina.";
                sourceResult = {
                    type: "vault_file",
                    label: selectedFile.basename,
                    value: selectedFile.path
                };
            }

        // =============================================================
        // RAMO 2: MOC (chosenOp === "moc")
        // =============================================================
        } else if (chosenOp === "moc") {
            // Passo 2/8: Disciplina
            chosenDiscipline = await tp.system.suggester(
                disciplines.map(d => d.label),
                disciplines,
                false,
                "Passo 2/8: Seleziona la Disciplina per il MOC:"
            );
            if (!chosenDiscipline) {
                return "";
            }

            // Passo 3/8: Argomento / Titolo MOC
            let mocTitle = null;
            try {
                mocTitle = await tp.system.prompt(
                    "Passo 3/8: Argomento del MOC (es. Analisi 1, Droghe):",
                    "",
                    true
                );
            } catch (_) {
                return ""; // Uscita silenziosa su annullamento prompt
            }
            if (!mocTitle || !mocTitle.trim()) {
                return "";
            }
            // Basta l'argomento: il nome del file "<Argomento> MOC.md" lo decide l'automazione
            topic = mocTitle.trim().replace(/\s*\bMOC\s*$/i, "").trim();

            // Passo 4/8: Fonte del MOC
            const mocModeOptions = [
                {
                    label: "🧠 1. Inizio Studio — Da NotebookLM",
                    value: "start_notebooklm"
                },
                {
                    label: "🌐 2. Inizio Studio — Da Conoscenza Base AI",
                    value: "start_base_knowledge"
                },
                {
                    label: "🏛️ 3. Fine Studio — Consolidamento Note del Vault",
                    value: "end_vault_consolidation"
                }
            ];

            mocMode = await tp.system.suggester(
                mocModeOptions.map(o => o.label),
                mocModeOptions.map(o => o.value),
                false,
                "Passo 4/8: Scegli la fonte / modalità del MOC:"
            );
            if (!mocMode) {
                return "";
            }

            if (mocMode === "start_notebooklm") {
                // Passo 5/8: Modalità Conoscenza (Solo se la fonte usa NotebookLM)
                const allowBase = await promptKnowledgeMode(tp);
                if (allowBase === null || allowBase === undefined) {
                    return "";
                }

                // Passo 6/8: Indice del libro (spina dorsale del MOC) e, facoltativo, diario delle lezioni
                const askTrace = async (kind) => {
                    const isIndex = kind === "index";
                    const what = isIndex ? "l'Indice del Libro" : "il Diario delle Lezioni";
                    const choice = await tp.system.suggester(
                        [`📋 Incolla ${what}`, `📄 Allega file con ${what} (.pdf, .txt, .md)`, "📋+📄 Entrambi (file + testo incollato)",
                         isIndex ? "⏭️ Non ho l'indice del libro" : "⏭️ Nessun diario delle lezioni"],
                        ["paste_text", "attach_files", "both", "none"],
                        false,
                        isIndex
                            ? "Passo 6/8: Indice del libro: decide moduli, ordine e perimetro del MOC"
                            : "Passo 6/8: Diario delle lezioni (facoltativo): aggiunge gli argomenti fatti a lezione"
                    );
                    if (!choice) return null;
                    const part = { text: "", files: [] };
                    if (choice === "attach_files" || choice === "both") {
                        const picked = await pickSyllabusFilesWithAppleScript();
                        if (picked === null) return null;
                        part.files = picked || [];
                    }
                    if (choice === "paste_text" || choice === "both") {
                        const pasted = await openMultiLineModal(app, {
                            title: isIndex ? "📋 Indice del Libro" : "📋 Diario delle Lezioni",
                            placeholder: isIndex
                                ? "Incolla qui l'indice del libro (capitoli e paragrafi). Ogni capitolo diventerà un modulo del MOC."
                                : "Incolla qui il diario delle lezioni. Gli argomenti che non sono nell'indice verranno aggiunti al modulo giusto.",
                            initialText: "",
                            confirmButtonText: "✅ Conferma"
                        });
                        if (pasted === null && choice === "paste_text") return null;
                        part.text = pasted || "";
                    }
                    return part;
                };
                const indexPart = await askTrace("index");
                if (!indexPart) return "";
                const diaryPart = await askTrace("diary");
                if (!diaryPart) return "";
                if (!indexPart.text && !indexPart.files.length && !diaryPart.text && !diaryPart.files.length) {
                    const goOn = await tp.system.suggester(
                        ["▶️ Continua: il MOC coprirà tutto il notebook", "↩️ Annulla"],
                        [true, false],
                        false,
                        "Senza indice né diario il MOC copre tutto il materiale del notebook (tutti i libri caricati)"
                    );
                    if (!goOn) return "";
                }
                syllabusIndex = indexPart;
                syllabusDiary = diaryPart;
                syllabusText = [indexPart.text, diaryPart.text].filter(Boolean).join("\n\n");
                syllabusFiles = [...indexPart.files, ...diaryPart.files];

                // Passo 7/8: Selezione Multipla NotebookLM (Solo se la fonte usa NotebookLM)
                const nlmResult = await selectNotebookLMInteractive(
                    tp,
                    "Passo 7/8: Seleziona i NotebookLM per il MOC",
                    vaultBasePath,
                    allowBase
                );

                if (!nlmResult) {
                    return "";
                }

                nlmResult.syllabus_text = syllabusText || "";
                nlmResult.syllabus_files = syllabusFiles || [];
                nlmResult.allow_base_knowledge = allowBase;

                sourceResult = nlmResult;
                notebookInfo = nlmResult.notebook_details && nlmResult.notebook_details.length > 0
                    ? nlmResult.notebook_details[0]
                    : { id: "N/D", title: nlmResult.label };
            } else if (mocMode === "start_base_knowledge") {
                sourceResult = {
                    type: "base_knowledge",
                    label: "Conoscenza Base di Antigravity (Roadmap da Zero)",
                    value: null
                };
            } else if (mocMode === "end_vault_consolidation") {
                sourceResult = {
                    type: "vault_consolidation",
                    label: "Consolidamento Note Vault (Fine Studio)",
                    value: null
                };
            }

        // =============================================================
        // RAMO 3: NOTA NORMALE (chosenOp === "normal")
        // =============================================================
        } else {
            // Passo 2/8: Disciplina
            chosenDiscipline = await tp.system.suggester(
                disciplines.map(d => d.label),
                disciplines,
                false,
                "Passo 2/8: Seleziona la Disciplina (Lista Chiusa 20 Materie)"
            );
            if (!chosenDiscipline) {
                return "";
            }

            // Passo 3/8: Argomento / Titolo Nota
            let noteTitle = null;
            try {
                noteTitle = await tp.system.prompt(
                    "Passo 3/8: Inserisci l'Argomento o il Titolo della nota:",
                    "",
                    true
                );
            } catch (_) {
                return ""; // Uscita silenziosa su annullamento prompt
            }
            if (!noteTitle || !noteTitle.trim()) {
                return "";
            }
            topic = noteTitle.trim();

            // Passo 4/8: Fonte della Nota Normale (con Passi 5 e 7 integrati se NotebookLM)
            sourceResult = await selectSourceInteractive(
                tp,
                app,
                vaultBasePath,
                "Passo 4/8: Seleziona la Fonte per la Nota Normale"
            );
            if (!sourceResult) {
                return "";
            }
        }

        // -------------------------------------------------------------
        // STEP 5: Generazione Istantanea dell'Indice del Vault
        // -------------------------------------------------------------
        const indexRecords = await generateVaultIndex(app, vaultBasePath);

        // -------------------------------------------------------------
        // STEP 6: Risoluzione Percorso Target, Pre-Run Cleanup e Avvio Job
        // -------------------------------------------------------------
        let targetRelPath = "";
        if (chosenOp === "edit") {
            targetRelPath = selectedFile.path;
        } else if (chosenOp === "moc") {
            // Unico nome possibile per i MOC: 01 MOC's/<Argomento> MOC.md (lo stesso che usa l'orchestratore)
            targetRelPath = `01 MOC's/${topic.trim()} MOC.md`;
        } else {
            targetRelPath = `${chosenDiscipline.name}/${topic.trim()}.md`;
        }

        // 1. Pulizia e reset totale dell'ambiente per idempotenza assoluta
        preRunCleanup(vaultBasePath, targetRelPath);

        // 2. Costruzione payload del job con supporto Multi-Notebook
        const isNotebookMulti = sourceResult && sourceResult.type === "notebooklm";
        const notebooksArray = isNotebookMulti
            ? (sourceResult.notebooks || (Array.isArray(sourceResult.value) ? sourceResult.value.map(v => typeof v === 'object' ? (v.id || v.title) : v) : [sourceResult.value?.id || sourceResult.value]))
            : [];
        const notebookDetailsArray = isNotebookMulti
            ? (sourceResult.notebook_details || (Array.isArray(sourceResult.value) ? sourceResult.value : []))
            : [];
        const allowBaseKnowledge = isNotebookMulti
            ? (sourceResult && sourceResult.allow_base_knowledge === true)
            : true;

        const jobData = {
            timestamp: new Date().toISOString(),
            operation: chosenOp,
            operation_type: chosenOp,
            operation_label: chosenOp === "moc"
                ? "MOC (Map of Content / Sub-MOC)"
                : (chosenOp === "edit" ? "Modifica / Migliora Nota Esistente" : "Nota Normale (Nuova)"),
            moc_mode: chosenOp === "moc" ? mocMode : null,
            allow_base_knowledge: allowBaseKnowledge,
            syllabus_text: syllabusText || "",
            syllabus_files: syllabusFiles || [],
            syllabus_index_text: syllabusIndex.text || "",
            syllabus_index_files: syllabusIndex.files || [],
            syllabus_diary_text: syllabusDiary.text || "",
            syllabus_diary_files: syllabusDiary.files || [],
            notebook_id: notebooksArray.length > 0 ? notebooksArray[0] : (chosenOp === "moc" && notebookInfo ? notebookInfo.id : null),
            notebook_title: isNotebookMulti ? sourceResult.label : (chosenOp === "moc" && notebookInfo ? notebookInfo.title : null),
            notebooks: notebooksArray,
            notebook_details: notebookDetailsArray,
            target_file_path: targetRelPath,
            target_file_abs: path.join(vaultBasePath, targetRelPath),
            title: chosenOp === "edit" ? selectedFile.basename : topic.trim(),
            edit_mode: chosenOp === "edit" ? chosenEditMode : null,
            user_instructions: chosenOp === "edit" ? userInstructions : "",
            discipline: chosenDiscipline.name,
            disciplina: chosenDiscipline.name,
            pole: chosenDiscipline.pole,
            topic: chosenOp === "edit" ? selectedFile.basename : topic.trim(),
            source: sourceResult,
            status: "pending"
        };

        // Salvataggio configurazione job in /tmp/antigravity_runtime/current-job.json (zero scritture nel Vault!)
        const currentJobPath = path.join(runtimeDir, "current-job.json");
        console.log("[Antigravity][menu] Prima del salvataggio di current-job.json...", currentJobPath);
        fs.writeFileSync(currentJobPath, JSON.stringify(jobData, null, 2), "utf8");
        console.log("[Antigravity][menu] Dopo il salvataggio di current-job.json con successo.");

        // Backup silenzioso Git (se repository presente)
        const gitCommitted = runGitBackupSnapshot(vaultBasePath);

        // Avvio del processo di background disaccoppiato + Live Progress Bar HUD (zero Notice per non intasare la UI)
        console.log("[Antigravity][menu] Prima di lanciare launchBackgroundJob (run_job.sh)...");
        launchBackgroundJob(app, vaultBasePath, jobData);

        return "";
    } finally {
        // Rilascio del singleton lock con debounce protettivo (400ms)
        setTimeout(() => {
            window._antigravityMenuRunning = false;
            try {
                const lockP = path.join(getRuntimeDir(), "menu.lock");
                if (fs.existsSync(lockP)) fs.unlinkSync(lockP);
            } catch (e) {}
        }, 400);
    }
};
