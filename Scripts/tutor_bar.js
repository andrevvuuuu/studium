/**
 * tutor_bar.js — Scheda permanente del tutor delle lezioni nella colonna sinistra, in basso, di Obsidian.
 *
 * Riprende fedelmente il design system dell'HUD di Antigravity:
 * vetro smerigliato, barra capsulare a segmenti, chip a pillola e marcatori di stato.
 * Logica pura (view) testata in .antigravity/tools/tests/js/tutor_bar.test.js.
 */
const fs = require("fs");
const path = require("path");
const child_process = require("child_process");

const VIEW_TYPE_TUTOR = "antigravity-tutor-view";
const TUTOR_ICON_ID = "ag-tutor-icon";
const TUTOR_ICON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M22 10v6M2 10l10-5 10 5-10 5z"/>
  <path d="M6 12v5c3 3 9 3 12 0v-5"/>
</svg>`;

const WEEKDAYS = ["domenica", "lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato"];
const MONTHS = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];
const EXAM_DAYS = 30;

const dayDiff = (from, to) => Math.round((Date.parse(to + "T00:00:00Z") - Date.parse(from + "T00:00:00Z")) / 86400000);
const longDate = (iso) => { const d = new Date(iso + "T00:00:00Z"); return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`; };
const weekday = (iso) => WEEKDAYS[new Date(iso + "T00:00:00Z").getUTCDay()];
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

/** Risoluzione robusta dell'API obsidian sia in ambiente plugin che Templater/script esterno */
function getObsidian(provided) {
    if (provided && provided.ItemView) return provided;
    if (typeof window !== "undefined" && window.obsidian && window.obsidian.ItemView) return window.obsidian;
    if (typeof global !== "undefined" && global.obsidian && global.obsidian.ItemView) return global.obsidian;
    try {
        const o = require("obsidian");
        if (o && o.ItemView) return o;
    } catch (_) {}
    return null;
}

/** Cosa mostrare, dallo stato del tutor: logica pura invariata */
function view(state, today) {
    if (!state || !Array.isArray(state.courses)) return { mode: "loading", pill: "Tutor · aggiorno i diari…", lessons: [], problems: [], foot: "" };
    const lessons = [];
    let toCreate = 0, toComplete = 0;
    for (const c of state.courses) {
        for (const l of c.lessons || []) {
            const open = (l.items || []).filter(it => it.status !== "coperto");
            if (!open.length) continue;
            toCreate += open.filter(it => it.status === "da_creare").length;
            toComplete += open.filter(it => it.status === "da_completare").length;
            lessons.push({ course: c.id, nome: c.nome, date: l.date, title: `${c.nome} · lezione del ${longDate(l.date)}`,
                items: open, hidden: l.items.length - open.length, all: l.items });
        }
    }
    lessons.sort((a, b) => a.date.localeCompare(b.date));
    const problems = state.courses.filter(c => c.errore).map(c => `${c.nome}: ${c.errore}`);

    const foot = [];
    for (const c of state.courses) for (const e of c.esami || []) {
        const days = dayDiff(today, e.data);
        if (days >= 0 && days <= EXAM_DAYS) foot.push(`${e.nome} (${c.nome}) tra ${plural(days, "giorno", "giorni")}`);
    }
    for (const c of state.courses) if ((c.previsione || []).length)
        foot.push(`Prossime lezioni di ${c.nome} (programma dell'anno scorso): ${c.previsione.slice(0, 3).map(t => t.split(/[.:;]/)[0].trim()).join(" · ")}`);

    let mode, pill;
    if (!lessons.length) {
        mode = "al_passo";
        const next = state.courses.filter(c => c.prossima_lezione).sort((a, b) => (a.prossima_lezione.data + a.prossima_lezione.ora).localeCompare(b.prossima_lezione.data + b.prossima_lezione.ora))[0];
        pill = "Vault al passo con le lezioni" + (next ? `. Prossima: ${next.nome}, ${weekday(next.prossima_lezione.data)} ${next.prossima_lezione.ora}` : "");
    } else if (state.recupero) {
        mode = "recupero";
        pill = `Recupero: ${toCreate} da creare, ${toComplete} da completare`;
    } else {
        mode = "lavoro";
        pill = `Tutor · ${plural(toCreate, "nota", "note")} da creare` + (toComplete ? ` · ${toComplete} da completare` : "");
    }
    return { mode, pill, lessons, problems, foot: foot.join(" · ") };
}

function el(tag, cls, text) {
    if (typeof document === "undefined") return { appendChild: () => {}, children: [], setAttribute: () => {}, addEventListener: () => {}, remove: () => {} };
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
}

function notice(msg) {
    const obs = getObsidian();
    try { if (obs?.Notice) new obs.Notice(msg, 6000); } catch (_) { console.log("[tutor]", msg); }
}

function macPathEnv(vaultBasePath) {
    let studiumBin = [];
    try { studiumBin = [path.join(vaultBasePath, ".antigravity", "bin")]; } catch (_) {}
    const extra = [...studiumBin, path.join(process.env.HOME || "", ".local/bin"), "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"];
    return Object.assign({}, process.env, { PATH: extra.join(":") + ":" + (process.env.PATH || "") });
}

function prepare(vaultBasePath, args) {
    return new Promise((resolve, reject) => {
        child_process.execFile("python3", [path.join(vaultBasePath, ".antigravity", "tools", "tutor.py"), ...args],
            { cwd: vaultBasePath, env: macPathEnv(vaultBasePath), timeout: 60000 }, (err, stdout, stderr) => {
                if (err) reject(new Error((stderr || err.message).trim().split("\n").pop()));
                else resolve(JSON.parse(fs.readFileSync(stdout.trim().split("\n").pop(), "utf8")));
            });
    });
}

async function act(app, vaultBasePath, kind, lesson, button) {
    const tp = window._agTutorTp;
    if (!tp) {
        notice("Tutor: premi Cmd+Alt+T e riprova");
        return;
    }
    const buttons = document.querySelectorAll(".ag-hud-actions button, .ag-tutor-actions button");
    buttons.forEach(b => { b.disabled = true; });
    const label = button ? button.textContent : "";
    if (button) button.textContent = "Preparo…";
    try {
        const menu = require(path.join(vaultBasePath, "Scripts", "antigravity_menu.js"));
        if (kind === "create") {
            const cfg = await prepare(vaultBasePath, ["--batch-config", lesson.course, lesson.date]);
            await menu.runTutorFlow(tp, app, vaultBasePath, { kind: "create", date: lesson.date, cfg });
        } else {
            const todo = lesson.items.filter(i => i.status === "da_completare");
            // Zero emoji nel suggester
            const it = todo.length > 1
                ? await tp.system.suggester(todo.map(i => `[Da completare] ${i.note}: ${i.missing || i.concept}`), todo, false, "Quale nota completare?")
                : todo[0];
            if (it) {
                const job = await prepare(vaultBasePath, ["--edit-config", lesson.course, lesson.date, it.note]);
                await menu.runTutorFlow(tp, app, vaultBasePath, { kind: "edit", date: lesson.date, job });
            }
        }
    } catch (e) {
        notice(`Tutor: ${e.message}`);
    } finally {
        buttons.forEach(b => { b.disabled = false; });
        if (button) button.textContent = label;
    }
}

/** Costruzione dinamica della classe ItemView nativa per Obsidian */
function createTutorViewClass(obsidianApi) {
    const obs = getObsidian(obsidianApi);
    const BaseClass = (obs && obs.ItemView) ? obs.ItemView : class DummyItemView {
        constructor(leaf) {
            this.leaf = leaf;
            this.app = leaf?.app;
            this.containerEl = leaf?.containerEl || (typeof document !== "undefined" ? document.createElement("div") : null);
            this.contentEl = leaf?.containerEl || (typeof document !== "undefined" ? document.createElement("div") : null);
        }
        async open() { await this.onOpen?.(); }
        async close() { await this.onClose?.(); }
        addAction() {}
    };

    return class TutorView extends BaseClass {
        constructor(leaf) {
            super(leaf);
            this.navigation = false; // Tassativo: la vista non viene navigata né chiusa al cambio di nota
            this.vaultBasePath = (this.app?.vault?.adapter && this.app.vault.adapter.basePath) || "";
        }

        getViewType() { return VIEW_TYPE_TUTOR; }
        getDisplayText() { return "Tutor delle lezioni"; }
        getIcon() { return TUTOR_ICON_ID; }

        async onOpen() {
            try { require(path.join(this.vaultBasePath, "Scripts", "ag_style.js"))(); } catch (_) {}
            try { this.addAction("refresh-cw", "Aggiorna tutor", () => this.renderContent()); } catch (_) {}
            try {
                this.addAction("sliders", "Menu Antigravity", async () => {
                    const tp = window._agTutorTp;
                    if (tp) {
                        const menu = require(path.join(this.vaultBasePath, "Scripts", "antigravity_menu.js"));
                        menu.runTutorFlow(tp, this.app, this.vaultBasePath, null);
                    } else {
                        notice("Tutor: premi Cmd+Alt+T e riprova");
                    }
                });
            } catch (_) {}
            this.renderContent();
        }

        async onClose() {}

        renderContent() {
            const container = this.contentEl;
            if (!container) return;
            if (typeof container.empty === "function") container.empty();
            else if (typeof container.replaceChildren === "function") container.replaceChildren();
            if (typeof container.addClass === "function") container.addClass("ag-tutor-sidebar-view");
            else if (container.classList) container.classList.add("ag-tutor-sidebar-view");

            const today = new Date().toLocaleDateString("sv-SE");
            let state = null;
            try {
                state = JSON.parse(fs.readFileSync(path.join(this.vaultBasePath, ".antigravity", "tutor", "state.json"), "utf8"));
            } catch (_) {}
            const v = view(state, today);

            // Card in stile HUD di Antigravity
            const card = el("div", "ag-hud-card");

            // Intestazione HUD
            const head = el("div", "ag-hud-head");
            const heading = el("div", "ag-hud-heading");
            heading.appendChild(el("div", "ag-hud-title", v.mode === "recupero" ? "Recupero delle lezioni" : "Tutor delle lezioni"));
            heading.appendChild(el("div", "ag-hud-sub", "Sincronizzazione corsi universitari"));
            head.appendChild(heading);

            const badgeCls = v.mode === "al_passo" ? "is-passo" : (v.mode === "lavoro" || v.mode === "recupero" ? "is-lavoro" : "");
            const badgeText = v.mode === "al_passo" ? "In pari" : (v.mode === "recupero" ? "Recupero" : (v.mode === "loading" ? "Caricamento" : "Da creare"));
            const clockBadge = el("span", "ag-hud-clock " + badgeCls, badgeText);
            head.appendChild(clockBadge);
            card.appendChild(head);

            // Chip informativi (stile Antigravity HUD)
            const chips = el("div", "ag-hud-chips");
            if (state && Array.isArray(state.courses)) {
                const next = state.courses.filter(c => c.prossima_lezione).sort((a, b) => (a.prossima_lezione.data + a.prossima_lezione.ora).localeCompare(b.prossima_lezione.data + b.prossima_lezione.ora))[0];
                if (next) {
                    chips.appendChild(el("span", "ag-hud-chip highlight", `Prossima: ${next.nome}`));
                    chips.appendChild(el("span", "ag-hud-chip", `${weekday(next.prossima_lezione.data)} ${next.prossima_lezione.ora}`));
                }
                for (const c of state.courses) {
                    if (c.errore) continue;
                    const openCount = (c.lessons || []).flatMap(l => l.items || []).filter(it => it.status !== "coperto").length;
                    if (!openCount) {
                        chips.appendChild(el("span", "ag-hud-chip", `${c.nome}: Coperta`));
                    }
                }
            }
            if (chips.children && chips.children.length) card.appendChild(chips);

            // Barra di avanzamento a segmenti capsulari (ag-hud-bar)
            const bar = el("div", "ag-hud-bar");
            bar.setAttribute("aria-label", "Stato copertura");
            if (v.mode === "al_passo") {
                for (let i = 0; i < 5; i++) {
                    const seg = el("div", "ag-hud-seg is-done");
                    seg.appendChild(el("i"));
                    bar.appendChild(seg);
                }
                const idleSeg = el("div", "ag-hud-seg is-idle");
                idleSeg.appendChild(el("i"));
                bar.appendChild(idleSeg);
            } else if (v.mode === "loading") {
                for (let i = 0; i < 5; i++) {
                    const seg = el("div", "ag-hud-seg is-idle");
                    seg.appendChild(el("i"));
                    bar.appendChild(seg);
                }
            } else {
                let totalItems = 0, coveredItems = 0;
                if (state && Array.isArray(state.courses)) {
                    for (const c of state.courses) {
                        for (const l of c.lessons || []) {
                            for (const it of l.items || []) {
                                totalItems++;
                                if (it.status === "coperto") coveredItems++;
                            }
                        }
                    }
                }
                const segCount = Math.max(5, Math.min(8, totalItems || 5));
                const doneSegs = totalItems ? Math.round((coveredItems / totalItems) * segCount) : 0;
                for (let i = 0; i < segCount; i++) {
                    const isDone = i < doneSegs;
                    const isCurrent = i === doneSegs;
                    const seg = el("div", "ag-hud-seg " + (isDone ? "is-done" : (isCurrent ? "is-idle" : "")));
                    seg.appendChild(el("i"));
                    bar.appendChild(seg);
                }
            }
            card.appendChild(bar);

            // Riga di stato (ag-hud-now)
            const nowRow = el("div", "ag-hud-now");
            nowRow.appendChild(el("b", v.mode === "al_passo" ? "green" : "", v.pill.split(".")[0]));
            nowRow.appendChild(el("span", "ag-hud-pct", v.mode === "al_passo" ? "100%" : (v.lessons.length ? `${v.lessons.length} lez.` : "")));
            card.appendChild(nowRow);

            // Dettaglio
            const detail = el("div", "ag-hud-detail", v.mode === "al_passo"
                ? "Tutti i concetti spiegati nelle ultime lezioni sono coperti da note dedicate nel vault."
                : (v.mode === "loading" ? "Caricamento dello stato dei corsi in corso…" : "Nuovi argomenti rilevati dai registri delle lezioni."));
            card.appendChild(detail);

            // Azioni rapide generali dell'HUD
            const hudActions = el("div", "ag-hud-actions");
            const refreshBtn = el("button", "ag-hud-btn secondary", "Aggiorna lezioni");
            refreshBtn.type = "button";
            refreshBtn.addEventListener("click", () => this.renderContent());
            hudActions.appendChild(refreshBtn);

            const menuBtn = el("button", "ag-hud-btn", "Menu Antigravity");
            menuBtn.type = "button";
            menuBtn.addEventListener("click", async () => {
                const tp = window._agTutorTp;
                if (tp) {
                    const menu = require(path.join(this.vaultBasePath, "Scripts", "antigravity_menu.js"));
                    menu.runTutorFlow(tp, this.app, this.vaultBasePath, null);
                } else {
                    notice("Tutor: premi Cmd+Alt+T e riprova");
                }
            });
            hudActions.appendChild(menuBtn);
            card.appendChild(hudActions);

            // Statistiche / esami imminenti (ag-hud-stats)
            if (state && Array.isArray(state.courses)) {
                const exams = [];
                for (const c of state.courses) for (const e of c.esami || []) {
                    const days = dayDiff(today, e.data);
                    if (days >= 0 && days <= EXAM_DAYS) exams.push({ name: e.nome, course: c.nome, days });
                }
                if (exams.length) {
                    const stats = el("div", "ag-hud-stats");
                    exams.slice(0, 2).forEach(ex => {
                        const span = el("span");
                        span.textContent = `${ex.name} (${ex.course}): `;
                        const str = el("strong", "", `${ex.days} gg`);
                        span.appendChild(str);
                        stats.appendChild(span);
                    });
                    card.appendChild(stats);
                }
            }

            container.appendChild(card);

            // Errori / Problemi corsi
            for (const p of v.problems) {
                container.appendChild(el("div", "ag-tutor-problem", p));
            }

            // Elenco delle lezioni aperte
            for (const l of v.lessons) {
                const box = el("div", "ag-hud-lesson");
                box.appendChild(el("div", "ag-hud-lesson-title", l.title));

                const list = el("div", "ag-hud-items");
                const fill = (items) => {
                    if (list.replaceChildren) list.replaceChildren();
                    else list.innerHTML = "";
                    for (const it of items) {
                        const row = el("div", "ag-hud-item is-" + it.status);
                        row.appendChild(el("span", "ag-hud-mark"));
                        const badge = el("span", "ag-hud-badge is-" + it.status,
                            it.status === "da_creare" ? "Da creare" : (it.status === "da_completare" ? "Da completare" : "Coperto"));
                        row.appendChild(badge);
                        row.appendChild(el("span", "ag-hud-name", it.title || it.note || it.concept));
                        if (it.status !== "coperto" && it.reason) {
                            const reasonText = it.status === "da_completare" && it.missing ? `${it.reason} Manca: ${it.missing}` : it.reason;
                            row.appendChild(el("div", "ag-tutor-reason", reasonText));
                        }
                        list.appendChild(row);
                    }
                };
                fill(l.items);
                box.appendChild(list);

                const actions = el("div", "ag-hud-actions");
                const nCreate = l.items.filter(i => i.status === "da_creare").length;
                const nComplete = l.items.filter(i => i.status === "da_completare").length;
                if (nCreate) {
                    const b = el("button", "ag-hud-btn", `Crea ${nCreate === 1 ? "1 nota" : nCreate + " note"}`);
                    b.type = "button";
                    b.addEventListener("click", () => act(this.app, this.vaultBasePath, "create", l, b));
                    actions.appendChild(b);
                }
                if (nComplete) {
                    const b = el("button", "ag-hud-btn secondary", `Completa ${nComplete === 1 ? "1 nota" : nComplete + " note"}`);
                    b.type = "button";
                    b.addEventListener("click", () => act(this.app, this.vaultBasePath, "complete", l, b));
                    actions.appendChild(b);
                }
                if (l.hidden) {
                    const b = el("button", "ag-hud-more", "mostra tutto");
                    b.type = "button";
                    b.addEventListener("click", () => { fill(l.all); b.remove(); });
                    actions.appendChild(b);
                }
                box.appendChild(actions);
                container.appendChild(box);
            }

            // Piede note aggiuntive
            if (v.foot) {
                container.appendChild(el("div", "ag-tutor-foot", v.foot));
            }
        }
    };
}

let _TutorViewClass = null;
function getTutorViewClass(obsidianApi) {
    const obs = getObsidian(obsidianApi);
    if (!_TutorViewClass || (obs && obs.ItemView && !(_TutorViewClass.prototype instanceof obs.ItemView))) {
        _TutorViewClass = createTutorViewClass(obs);
    }
    return _TutorViewClass;
}

function registerViewAndIcon(app, obsidianApi) {
    const obs = getObsidian(obsidianApi);
    if (obs?.addIcon) {
        try { obs.addIcon(TUTOR_ICON_ID, TUTOR_ICON_SVG); } catch (_) {}
    }
    if (app?.viewRegistry && !app.viewRegistry.getViewCreatorByType(VIEW_TYPE_TUTOR)) {
        const ViewClass = getTutorViewClass(obs);
        try { app.viewRegistry.registerView(VIEW_TYPE_TUTOR, (leaf) => new ViewClass(leaf)); } catch (_) {}
    }
}

function registerPluginView(plugin, obsidianApi) {
    const obs = getObsidian(obsidianApi);
    if (obs?.addIcon) {
        try { obs.addIcon(TUTOR_ICON_ID, TUTOR_ICON_SVG); } catch (_) {}
    }
    const ViewClass = getTutorViewClass(obs);
    if (plugin?.registerView) {
        try { plugin.registerView(VIEW_TYPE_TUTOR, (leaf) => new ViewClass(leaf)); } catch (_) {}
    } else {
        registerViewAndIcon(plugin?.app, obs);
    }
}

async function ensureLeftBottomLeaf(app) {
    const workspace = app?.workspace;
    if (!workspace) return null;
    const tutorLeaves = [];
    workspace.iterateAllLeaves?.((leaf) => {
        if (leaf.getViewState?.()?.type === VIEW_TYPE_TUTOR) tutorLeaves.push(leaf);
    });
    const deferredLeaves = new Map();
    for (const leaf of tutorLeaves) {
        const wasDeferred = !!leaf.isDeferred;
        if (wasDeferred) {
            try { await leaf.loadIfDeferred?.(); } catch (_) {}
        }
        deferredLeaves.set(leaf, wasDeferred);
    }
    let leftLeaf = null;
    for (const leaf of tutorLeaves) {
        if (leaf.getRoot?.() === workspace.rightSplit) {
            try { leaf.detach(); } catch (_) {}
        } else if (!leftLeaf && leaf.getRoot?.() === workspace.leftSplit &&
            (deferredLeaves.get(leaf) || (leaf.view && typeof leaf.view.renderContent === "function"))) {
            leftLeaf = leaf;
        } else {
            try { leaf.detach(); } catch (_) {}
        }
    }
    if (!leftLeaf) {
        const explorerLeaf = workspace.getLeavesOfType?.("file-explorer")?.[0];
        try {
            leftLeaf = explorerLeaf && workspace.createLeafBySplit
                ? workspace.createLeafBySplit(explorerLeaf, "horizontal")
                : workspace.getLeftLeaf?.(true);
        } catch (_) {
            leftLeaf = workspace.getLeftLeaf?.(true);
        }
        if (leftLeaf) await leftLeaf.setViewState({ type: VIEW_TYPE_TUTOR, active: false });
    }
    if (leftLeaf) {
        try { leftLeaf.setPinned(true); } catch (_) {}
    }
    return leftLeaf;
}

/**
 * Funzione principale esportata, invocata da tutor_startup.js e da Prompts/Tutor Mostra.md.
 */
async function render(app, vaultBasePath, { reveal = false } = {}) {
    if (typeof document !== "undefined") document.getElementById("ag-tutor")?.remove();

    const pluginActive = !!app?.plugins?.plugins?.["antigravity-tutor"];
    if (!pluginActive) registerViewAndIcon(app);

    const leaf = await ensureLeftBottomLeaf(app);
    if (!leaf) return;
    if (typeof leaf.view?.renderContent === "function") leaf.view.renderContent();
    if (reveal) await app?.workspace?.revealLeaf?.(leaf);

}

module.exports = render;
module.exports.view = view;
module.exports.getTutorViewClass = getTutorViewClass;
module.exports.VIEW_TYPE_TUTOR = VIEW_TYPE_TUTOR;
module.exports.TUTOR_ICON_ID = TUTOR_ICON_ID;
module.exports.TUTOR_ICON_SVG = TUTOR_ICON_SVG;
module.exports.registerViewAndIcon = registerViewAndIcon;
module.exports.registerPluginView = registerPluginView;
Object.defineProperty(module.exports, "TutorView", {
    get() { return getTutorViewClass(); },
    configurable: true,
    enumerable: true
});
