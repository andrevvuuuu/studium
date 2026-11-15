'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PHASE_LABELS = {
    prep: "Preparazione",
    sources: "Lettura fonti",
    context: "Contesto",
    writing: "Scrittura",
    verify: "Verifica",
    final: "Rifinitura"
};

function getJobControl(vbp) {
    const basePath = vbp || (window.app && window.app.vault && window.app.vault.adapter && window.app.vault.adapter.basePath) || "";
    if (!basePath) return null;
    const ctlPath = path.join(basePath, "Scripts", "ag_job_control.js");
    try {
        delete require.cache[require.resolve(ctlPath)];
        return require(ctlPath);
    } catch (_) {
        return null;
    }
}

function reopenHud(app) {
    try {
        const vbp = (app && app.vault && app.vault.adapter && app.vault.adapter.basePath)
            || (window.app && window.app.vault && window.app.vault.adapter && window.app.vault.adapter.basePath) || "";
        const menuPath = path.join(vbp, "Scripts", "antigravity_menu.js");
        delete require.cache[require.resolve(menuPath)];
        const menu = require(menuPath);
        if (menu && typeof menu.reopenProgressHud === "function") {
            menu.reopenProgressHud(app || window.app);
        }
    } catch (e) {
        console.error("[ag_job_bar] Errore riapertura HUD:", e);
    }
}

function ensureJobBar(app) {
    const currentApp = app || (typeof window !== "undefined" && window.app);
    if (typeof window === "undefined" || typeof document === "undefined") return null;

    const vbp = (currentApp && currentApp.vault && currentApp.vault.adapter && currentApp.vault.adapter.basePath)
        || (window.app && window.app.vault && window.app.vault.adapter && window.app.vault.adapter.basePath) || "";

    if (window._agJobBar) {
        if (window._agJobBar.el && document.body.contains(window._agJobBar.el)) {
            const activeCtl = getJobControl(vbp);
            if (!window._agJobBar.stopPoller && activeCtl && typeof activeCtl.onStatus === "function") {
                window._agJobBar.stopPoller = activeCtl.onStatus(window._agJobBar.update, { intervalMs: 800 });
            }
            if (activeCtl && typeof activeCtl.readStatus === "function" && typeof window._agJobBar.update === "function") {
                try { window._agJobBar.update(activeCtl.readStatus()); } catch (_) {}
            }
            return window._agJobBar;
        }
        if (typeof window._agJobBar.stopPoller === "function") {
            try { window._agJobBar.stopPoller(); } catch (_) {}
        }
    }

    const statusBar = document.querySelector(".status-bar");
    if (!statusBar) return null;

    let barEl = document.getElementById("ag-job-bar");
    if (!barEl) {
        barEl = document.createElement("div");
        barEl.id = "ag-job-bar";
        barEl.className = "status-bar-item ag-job-bar";
        barEl.style.display = "none";
        statusBar.appendChild(barEl);
    }

    barEl.innerHTML = `
        <span class="ag-job-bar-text" role="button" tabindex="0" title="Apri avanzamento"></span>
        <div class="ag-job-bar-actions">
            <button type="button" class="ag-job-bar-btn ag-job-bar-open" title="Apri avanzamento">Apri avanzamento</button>
            <button type="button" class="ag-job-bar-btn is-cancel ag-job-bar-cancel" title="Annulla operazione">Annulla</button>
        </div>
    `;

    const textEl = barEl.querySelector(".ag-job-bar-text");
    const openBtn = barEl.querySelector(".ag-job-bar-open");
    const cancelBtn = barEl.querySelector(".ag-job-bar-cancel");

    const doReopen = () => reopenHud(currentApp);
    textEl.onclick = doReopen;
    textEl.onkeydown = (e) => {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            doReopen();
        }
    };
    openBtn.onclick = doReopen;

    let isCancelling = false;

    cancelBtn.onclick = async () => {
        isCancelling = true;
        cancelBtn.disabled = true;
        cancelBtn.textContent = "Annullamento…";
        const ctl = getJobControl(vbp);
        if (ctl && typeof ctl.getJobController === "function") {
            try {
                await ctl.getJobController().abort("user");
            } catch (err) {
                console.error("[ag_job_bar] Errore abort job:", err);
            }
        }
    };

    let hideTimer = null;
    let lastStatusVal = null;
    let ctl = getJobControl(vbp);

    const updateFromStatus = (st) => {
        if (!st) {
            barEl.style.display = "none";
            return;
        }

        const activeCtl = ctl || getJobControl(vbp);
        const isActive = activeCtl ? activeCtl.isJobActive(st) : (st.status === "running" && st.pid);
        const statusVal = st.status || "idle";

        const rtDir = (activeCtl && activeCtl.RUNTIME_DIR) || process.env.ANTIGRAVITY_RUNTIME_DIR || "/tmp/antigravity_runtime";
        let cancelRequested = isCancelling;
        if (!cancelRequested) {
            try {
                const reqRaw = fs.readFileSync(path.join(rtDir, "cancel-request.json"), "utf8");
                const reqData = JSON.parse(reqRaw);
                if (reqData && (reqData.job_id === st.job_id || (!reqData.job_id && lastStatusVal === "running"))) {
                    cancelRequested = true;
                }
            } catch (_) {}
        }

        if (isActive) {
            if (hideTimer) {
                clearTimeout(hideTimer);
                hideTimer = null;
            }
            if (cancelRequested) {
                cancelBtn.disabled = true;
                cancelBtn.textContent = "Annullamento…";
            } else {
                cancelBtn.disabled = false;
                cancelBtn.textContent = "Annulla";
            }
            cancelBtn.style.display = "";

            const job = (activeCtl && typeof activeCtl.readJob === "function") ? activeCtl.readJob() : {};
            const title = (job && (job.topic || job.title)) || (st.target_file ? path.basename(st.target_file, ".md") : "Nota");
            const plan = (activeCtl && typeof activeCtl.phasePlanFor === "function") ? activeCtl.phasePlanFor(job) : [];
            let pct = (typeof st.overall_percent === "number")
                ? st.overall_percent
                : (activeCtl && typeof activeCtl.computeOverallPercent === "function" ? activeCtl.computeOverallPercent(st, plan) : (st.percent || 0));
            pct = Math.max(0, Math.min(100, Math.round(pct)));

            const jid = st.job_id || "default";
            if (typeof window !== "undefined") {
                window._agBarClamp = window._agBarClamp || { jobId: null, maxPercent: 0 };
                if (window._agBarClamp.jobId === jid) {
                    pct = Math.max(window._agBarClamp.maxPercent, pct);
                    window._agBarClamp.maxPercent = pct;
                } else {
                    window._agBarClamp.jobId = jid;
                    window._agBarClamp.maxPercent = pct;
                }
            }

            const phase = st.phase || "prep";
            const phaseLabel = PHASE_LABELS[phase] || phase;

            textEl.textContent = `✨ ${title} · ${pct}% · ${phaseLabel}`;
            textEl.title = `✨ ${title} · ${pct}% · ${phaseLabel} (clicca per aprire)`;
            barEl.style.display = "inline-flex";
            lastStatusVal = statusVal;
            return;
        }

        // Terminal or inactive status
        const isTerminal = ["completed", "error", "cancelled"].includes(statusVal);
        if (isTerminal && (lastStatusVal === "running" || isCancelling || cancelRequested)) {
            isCancelling = false;
            lastStatusVal = statusVal;
            cancelBtn.style.display = "none";
            const job = (activeCtl && typeof activeCtl.readJob === "function") ? activeCtl.readJob() : {};
            const title = (job && (job.topic || job.title)) || (st.target_file ? path.basename(st.target_file, ".md") : "Nota");

            if (statusVal === "completed") {
                textEl.textContent = `✨ ${title} · Completato!`;
            } else if (statusVal === "cancelled") {
                textEl.textContent = `✨ ${title} · Annullato`;
            } else {
                textEl.textContent = `❌ ${title} · Errore`;
            }

            barEl.style.display = "inline-flex";
            if (hideTimer) clearTimeout(hideTimer);
            hideTimer = setTimeout(() => {
                barEl.style.display = "none";
                hideTimer = null;
            }, 4000);
        } else if (!isTerminal) {
            barEl.style.display = "none";
            lastStatusVal = statusVal;
        }
    };

    let stopPoller = null;
    if (ctl && typeof ctl.onStatus === "function") {
        stopPoller = ctl.onStatus(updateFromStatus, { intervalMs: 800 });
    }

    const instance = {
        el: barEl,
        stopPoller,
        update: updateFromStatus
    };
    window._agJobBar = instance;
    return instance;
}

module.exports = { ensureJobBar };
