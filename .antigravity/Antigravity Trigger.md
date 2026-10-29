<%*
// ==============================================================================
// Antigravity Trigger — Obsidian Automation Engine
// ==============================================================================
// 1. Azzeramento preventivo buffer Templater (protezione editor e cursore)
tR = "";

try {
    // 2. NUCLEAR DOM & NOTICE CLEANUP — disinnesca TUTTE le notifiche zombie
    // PRIMA di qualsiasi altra cosa, svuota il container visivo delle notifiche.
    // NON usare clearInterval brute-force: uccide i timer di Obsidian che servono
    // per far scomparire le Notice normali, rendendole immortali.
    if (typeof document !== "undefined") {
        try {
            // Svuota completamente il contenitore delle notifiche native Obsidian
            const nc = document.querySelector(".notice-container");
            if (nc) nc.innerHTML = "";
            // Rimuovi modali orfani che bloccano l'interfaccia (Bug 1A)
            document.querySelectorAll(".modal-container").forEach(m => m.remove());
            // Rimuovi HUD e stili di Antigravity se rimasti appesi
            const oldHud = document.getElementById("antigravity-progress-hud");
            if (oldHud) oldHud.remove();
            const oldStyle = document.getElementById("antigravity-hud-style") || document.getElementById("antigravity-hud-styles");
            if (oldStyle) oldStyle.remove();
        } catch (_) {}
    }

    // 3. Pulisci SOLO i nostri timer nominati (HUD e stopwatch)
    if (typeof window !== "undefined") {
        if (window._antigravityHudTimer) {
            clearInterval(window._antigravityHudTimer);
            window._antigravityHudTimer = null;
        }
        if (window._antigravityStopwatchTimer) {
            clearInterval(window._antigravityStopwatchTimer);
            window._antigravityStopwatchTimer = null;
        }
        
        // Controllo Singleton Lock in memoria: se già attivo e recente (< 5 min), blocca l'avvio concorrente
        if (window._antigravityMenuRunning) {
            const now = Date.now();
            const lastStart = window._antigravityMenuStartTime || 0;
            const MENU_TIMEOUT_MS = 300000; // 5 minuti max timeout
            if (now - lastStart < MENU_TIMEOUT_MS) {
                if (typeof Notice !== "undefined") new Notice("⚠️ Menu Antigravity già aperto o operazione in corso.", 2500);
                return;
            }
            // Lock scaduto, consentiamo il recupero
            window._antigravityMenuRunning = false;
        }
    }

    // 4. Controllo File Lock /tmp/antigravity_runtime/menu.lock con verifica di vivacità del PID
    const fs = require("fs");
    const path = require("path");
    const runtimeDir = "/tmp/antigravity_runtime";
    if (!fs.existsSync(runtimeDir)) fs.mkdirSync(runtimeDir, { recursive: true });
    const lockFile = path.join(runtimeDir, "menu.lock");

    if (fs.existsSync(lockFile)) {
        let lockData = null;
        try {
            lockData = JSON.parse(fs.readFileSync(lockFile, "utf8"));
        } catch (_) {}

        const now = Date.now();
        const LOCK_TIMEOUT_MS = 300000; // 5 minuti max
        let isProcessAlive = false;

        if (lockData && lockData.pid) {
            try {
                // Signal 0 verifica se il processo esiste senza ucciderlo
                process.kill(lockData.pid, 0);
                isProcessAlive = true;
            } catch (_) {
                isProcessAlive = false;
            }
        }

        const isLockFresh = lockData && lockData.time && (now - lockData.time < LOCK_TIMEOUT_MS);

        if (isProcessAlive && isLockFresh) {
            if (typeof Notice !== "undefined") {
                new Notice(`⚠️ Antigravity è già in esecuzione (PID: ${lockData.pid}).`, 2500);
            }
            return;
        } else {
            // Lock orfano o processo precedente morto: rimuovi in sicurezza
            try { fs.unlinkSync(lockFile); } catch (_) {}
        }
    }

    // Acquisisci il lock prima di caricare ed eseguire lo script
    if (typeof window !== "undefined") {
        window._antigravityMenuRunning = true;
        window._antigravityMenuStartTime = Date.now();
    }
    try {
        fs.writeFileSync(lockFile, JSON.stringify({ pid: process.pid, time: Date.now() }), "utf8");
    } catch (_) {}

    // 5. FORCE RELOAD DA DISCO (Bypassa la cache in memoria di Templater)
    const basePath = app?.vault?.adapter?.basePath || path.join(require("os").homedir(), "Obsidian Vault");
    const scriptPathPrimary = path.join(basePath, "Scripts", "antigravity_menu.js");
    const scriptPathBackup = path.join(basePath, ".antigravity", "scripts", "antigravity_menu.js");
    const chosenScript = fs.existsSync(scriptPathPrimary) ? scriptPathPrimary : scriptPathBackup;

    // Purge della cache di require per forzare la lettura dei byte freschi da disco
    try {
        const resolved = require.resolve(chosenScript);
        delete require.cache[resolved];
    } catch (_) {}

    const freshScript = require(chosenScript);

    // Sincronizza tp.user con la versione aggiornata da disco
    if (tp && tp.user) {
        tp.user.antigravity_menu = freshScript;
    }

    // 6. Esecuzione del menu nativo (versione fresca da disco)
    try {
        await freshScript(tp);
    } finally {
        if (typeof window !== "undefined") {
            window._antigravityMenuRunning = false;
        }
        try {
            const lockFile = "/tmp/antigravity_runtime/menu.lock";
            if (fs.existsSync(lockFile)) fs.unlinkSync(lockFile);
        } catch (_) {}
    }

} catch (e) {
    console.error("[Antigravity Trigger Error]", e);
    if (typeof window !== "undefined") window._antigravityMenuRunning = false;
    try {
        const lockFile = "/tmp/antigravity_runtime/menu.lock";
        if (fs.existsSync(lockFile)) fs.unlinkSync(lockFile);
    } catch (_) {}
}

// 6. Azzeramento finale di sicurezza per non lasciare stringhe o newline nell'editor
tR = "";
-%>