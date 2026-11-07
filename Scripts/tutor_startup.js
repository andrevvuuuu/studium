/**
 * tutor_startup.js — All'apertura di Obsidian (modello di avvio di Templater "Prompts/Tutor Startup.md"):
 * lancia .antigravity/tools/tutor.py in background (al massimo un'analisi al giorno, lo decide lui) e disegna
 * la barra del tutor, ridisegnandola quando state.json cambia.
 */
const fs = require("fs");
const path = require("path");
const child_process = require("child_process");

module.exports = async function (tp) {
    const app = window.app;
    // Il menu di Antigravity aperto dai pulsanti della barra ha bisogno dei prompt di Templater
    window._agTutorTp = tp;
    const vaultBasePath = app.vault.adapter.basePath;
    const render = require(path.join(vaultBasePath, "Scripts", "tutor_bar.js"));
    const statePath = path.join(vaultBasePath, ".antigravity", "tutor", "state.json");
    const env = Object.assign({}, process.env, {
        PATH: [path.join(vaultBasePath, ".antigravity", "bin"), path.join(process.env.HOME || "", ".local/bin"), "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"].join(":") + ":" + (process.env.PATH || "")
    });
    try {
        const child = child_process.spawn("python3", [path.join(vaultBasePath, ".antigravity", "tools", "tutor.py")], {
            cwd: vaultBasePath, detached: true, stdio: "ignore", env
        });
        child.on("error", (e) => console.log("[tutor] python3 non trovato", e));
        child.unref();
    } catch (e) {
        console.log("[tutor] avvio non riuscito", e);
    }
    render(app, vaultBasePath);
    if (window._agTutorWatching) return;
    window._agTutorWatching = true;
    fs.watchFile(statePath, { interval: 2000 }, () => render(app, vaultBasePath));
    // Quando un batch o una modifica di Antigravity finisce, lo stato si riallinea ai file (nessuna AI)
    const runtime = process.env.ANTIGRAVITY_RUNTIME_DIR || "/tmp/antigravity_runtime";
    for (const f of ["batch-status.json", "job-status.json"]) {
        fs.watchFile(path.join(runtime, f), { interval: 3000 }, (cur) => {
            let st = {};
            try { st = JSON.parse(fs.readFileSync(path.join(runtime, f), "utf8")); } catch (_) {}
            if (["completed", "done", "error", "cancelled", "stopped", "paused"].includes(st.status)) {
                const c = child_process.spawn("python3", [path.join(vaultBasePath, ".antigravity", "tools", "tutor.py"), "--reconcile"], { cwd: vaultBasePath, detached: true, stdio: "ignore", env });
                c.on("error", () => {});
                c.unref();
            }
        });
    }
};
