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
    const vaultBasePath = app.vault.adapter.basePath;
    const render = require(path.join(vaultBasePath, "Scripts", "tutor_bar.js"));
    const statePath = path.join(vaultBasePath, ".antigravity", "tutor", "state.json");
    const env = Object.assign({}, process.env, {
        PATH: [path.join(process.env.HOME || "", ".local/bin"), "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"].join(":") + ":" + (process.env.PATH || "")
    });
    try {
        const child = child_process.spawn("python3", [path.join(vaultBasePath, ".antigravity", "tools", "tutor.py")], {
            cwd: vaultBasePath, detached: true, stdio: "ignore", env
        });
        child.unref();
    } catch (e) {
        console.log("[tutor] avvio non riuscito", e);
    }
    render(app, vaultBasePath);
    if (window._agTutorWatching) return;
    window._agTutorWatching = true;
    fs.watchFile(statePath, { interval: 2000 }, () => render(app, vaultBasePath));
};
